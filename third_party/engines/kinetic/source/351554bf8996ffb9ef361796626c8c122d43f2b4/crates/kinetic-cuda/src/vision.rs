//! Kernels of vision transformers, whose image tokens attend to each other
//! in both directions and never touch a cache.

use std::rc::Rc;

use crate::context::Context;
use crate::error::{Error, Result};
use kinetic_quant::TensorType;

use crate::gemv::{DeviceMatrix, GemvInput};
use crate::kernels::{arg, Kernels, IMAGE};
use crate::memory::DeviceBuffer;
use crate::module::{Function, LaunchConfig, Module};
use crate::stream::Stream;

const THREADS: u32 = 256;
const WARPS: u32 = 8;
const QUERIES: u32 = 8;
const TILE: usize = 32;
const MAX_HEAD: usize = 128;

/// Inputs and weight rows of one block of [`VisionKernels::matmul`], and
/// the columns it takes a step.
const MM_TILE: u32 = 128;
const MM_STEP: usize = 32;

/// Head size, keys a tile and queries a block of the tensor-core attention.
const MMA_HEAD: usize = 64;
const MMA_QUERIES: u32 = 64;
const MMA_THREADS: u32 = 128;

/// The vision kernels, loaded into one context.
pub struct VisionKernels {
    layer_norm: Function,
    bias: Function,
    residual: Function,
    rope_2d: Function,
    rms_norm: Function,
    clamp: Function,
    geglu: Function,
    attention: Function,
    attention_mma: Function,
    matmul: Function,
}

fn check(ok: bool, what: impl FnOnce() -> String) -> Result<()> {
    ok.then_some(()).ok_or_else(|| Error::Shape(what()))
}

fn linear(n: usize) -> LaunchConfig {
    LaunchConfig::linear((n as u32).div_ceil(THREADS), THREADS)
}

impl VisionKernels {
    /// Loads the kernels, or fails with [`Error::KernelsNotBuilt`].
    pub fn load(ctx: &Rc<Context>) -> Result<VisionKernels> {
        if IMAGE.0.is_empty() {
            return Err(Error::KernelsNotBuilt);
        }
        // SAFETY: the image is nvcc's fatbin output, embedded unchanged.
        let module = unsafe { Module::load(ctx, &IMAGE.0) }?;
        let attention = module.function(c"vit_attention")?;
        attention.allow_shared(attention_shared(MAX_HEAD))?;
        Ok(VisionKernels {
            layer_norm: module.function(c"vit_layer_norm")?,
            bias: module.function(c"vit_bias")?,
            residual: module.function(c"vit_residual")?,
            rope_2d: module.function(c"vit_rope_2d")?,
            rms_norm: module.function(c"vit_rms_norm")?,
            clamp: module.function(c"vit_clamp")?,
            geglu: module.function(c"vit_geglu")?,
            attention,
            attention_mma: module.function(c"vit_attention_mma")?,
            matmul: module.function(c"vit_matmul")?,
        })
    }

    /// Queues the layer norm of `rows` rows of `width` values of `x`, with
    /// scale `w` and shift `b`, into the first inputs of `out`, which may
    /// be of another width that rows fill exactly.
    #[allow(clippy::too_many_arguments)]
    pub fn layer_norm(
        &self,
        kernels: &Kernels,
        x: &DeviceBuffer<f32>,
        (w, b): (&DeviceBuffer<f32>, &DeviceBuffer<f32>),
        eps: f32,
        (rows, width): (usize, usize),
        out: &mut GemvInput,
        stream: &Stream,
    ) -> Result<()> {
        let n = rows * width;
        check(x.len() >= n && w.len() == width && b.len() == width, || {
            format!("layer norm of {rows}x{width} from {} values", x.len())
        })?;
        let inputs = fill(out, n)?;
        let (xp, wp, bp, yp, width) = (
            x.device_ptr(),
            w.device_ptr(),
            b.device_ptr(),
            out.act().x,
            width as u32,
        );
        let config = LaunchConfig::linear(rows as u32, THREADS);
        // SAFETY: matches `vit_layer_norm(const float*, const float*, const
        // float*, float*, unsigned, float)`; one block per row reads and
        // writes `width` values inside buffers of at least `rows * width`.
        unsafe {
            self.layer_norm.launch(
                config,
                stream,
                &mut [
                    arg(&xp),
                    arg(&wp),
                    arg(&bp),
                    arg(&yp),
                    arg(&width),
                    arg(&eps),
                ],
            )
        }?;
        out.quantize(kernels, inputs, stream)
    }

    /// Queues `out = y + b`, through GELU when `gelu`, for the first
    /// `out.width()`-wide inputs that `rows` rows of `b.len()` values fill.
    #[allow(clippy::too_many_arguments)]
    pub fn bias(
        &self,
        kernels: &Kernels,
        y: &DeviceBuffer<f32>,
        b: &DeviceBuffer<f32>,
        gelu: bool,
        rows: usize,
        out: &mut GemvInput,
        stream: &Stream,
    ) -> Result<()> {
        let n = rows * b.len();
        check(y.len() >= n, || {
            format!("bias over {n} of {} values", y.len())
        })?;
        let inputs = fill(out, n)?;
        let (yp, bp, op, len, width, gelu) = (
            y.device_ptr(),
            b.device_ptr(),
            out.act().x,
            n as u32,
            b.len() as u32,
            u32::from(gelu),
        );
        // SAFETY: matches `vit_bias(const float*, const float*, float*,
        // unsigned, unsigned, unsigned)`; `n` values in and out, checked.
        unsafe {
            self.bias.launch(
                linear(n),
                stream,
                &mut [
                    arg(&yp),
                    arg(&bp),
                    arg(&op),
                    arg(&len),
                    arg(&width),
                    arg(&gelu),
                ],
            )
        }?;
        out.quantize(kernels, inputs, stream)
    }

    /// Queues `x += y + b` over `n` values in rows of `width`, leaving out
    /// either addend when `None`.
    pub fn residual(
        &self,
        x: &mut DeviceBuffer<f32>,
        y: Option<&DeviceBuffer<f32>>,
        b: Option<&DeviceBuffer<f32>>,
        (n, width): (usize, usize),
        stream: &Stream,
    ) -> Result<()> {
        check(
            x.len() >= n && y.is_none_or(|y| y.len() >= n) && b.is_none_or(|b| b.len() == width),
            || format!("residual of {n} values in rows of {width}"),
        )?;
        let (xp, yp, bp, len, width) = (
            x.device_ptr(),
            y.map_or(0, DeviceBuffer::device_ptr),
            b.map_or(0, DeviceBuffer::device_ptr),
            n as u32,
            width as u32,
        );
        // SAFETY: matches `vit_residual(float*, const float*, const float*,
        // unsigned, unsigned)`; `n` values of each, checked; null addends are
        // never read.
        unsafe {
            self.residual.launch(
                linear(n),
                stream,
                &mut [arg(&xp), arg(&yp), arg(&bp), arg(&len), arg(&width)],
            )
        }
    }

    /// Queues the 2-D rotation of the query and key heads in `rows` rows of
    /// `[q | k | v]` by the two positions per row in `pos`. Without
    /// `halves` the first quarter of a head's pairs turn by the first
    /// position and the second quarter by the second, each value paired
    /// with the one half a head on; with `halves` each half of a head turns
    /// by its own position, values paired a quarter of a head apart.
    #[allow(clippy::too_many_arguments)]
    pub fn rope_2d(
        &self,
        qkv: &mut DeviceBuffer<f32>,
        pos: &DeviceBuffer<u32>,
        (rows, n_head, head_dim): (usize, usize, usize),
        base: f32,
        halves: bool,
        stream: &Stream,
    ) -> Result<()> {
        check(
            qkv.len() >= rows * 3 * n_head * head_dim
                && pos.len() >= 2 * rows
                && head_dim.is_multiple_of(4),
            || format!("2-D rotation of {rows} rows of {n_head} heads of {head_dim}"),
        )?;
        let n = rows * n_head * head_dim;
        let (qp, pp, rows, n_head, head_dim, halves) = (
            qkv.device_ptr(),
            pos.device_ptr(),
            rows as u32,
            n_head as u32,
            head_dim as u32,
            u32::from(halves),
        );
        // SAFETY: matches `vit_rope_2d(float*, const unsigned*, unsigned,
        // unsigned, unsigned, float, unsigned)`; one thread per rotated pair
        // of the queries and keys, all inside `qkv`, two positions per row.
        unsafe {
            self.rope_2d.launch(
                linear(n),
                stream,
                &mut [
                    arg(&qp),
                    arg(&pp),
                    arg(&rows),
                    arg(&n_head),
                    arg(&head_dim),
                    arg(&base),
                    arg(&halves),
                ],
            )
        }
    }

    /// Queues the RMS norm in place of `rows` rows of `width` values of `x`.
    /// `w` holds `sets` rows of weights; row `r` of `x` takes weight row
    /// `(r / every) % sets`.
    pub fn rms_norm(
        &self,
        x: &mut DeviceBuffer<f32>,
        w: &DeviceBuffer<f32>,
        (rows, width): (usize, usize),
        (every, sets): (usize, usize),
        eps: f32,
        stream: &Stream,
    ) -> Result<()> {
        check(
            x.len() >= rows * width && w.len() == sets * width && every > 0,
            || format!("RMS norm of {rows}x{width} with {} weights", w.len()),
        )?;
        let (xp, wp, width, every, sets) = (
            x.device_ptr(),
            w.device_ptr(),
            width as u32,
            every as u32,
            sets as u32,
        );
        // SAFETY: matches `vit_rms_norm(float*, const float*, unsigned,
        // unsigned, unsigned, float)`; one block per row works inside `x` and
        // reads one of the `sets` weight rows, all checked.
        unsafe {
            self.rms_norm.launch(
                LaunchConfig::linear(rows as u32, THREADS),
                stream,
                &mut [
                    arg(&xp),
                    arg(&wp),
                    arg(&width),
                    arg(&every),
                    arg(&sets),
                    arg(&eps),
                ],
            )
        }
    }

    /// Queues `x` clamped into the first `rows` inputs of `out`; see
    /// [`VisionKernels::clamp_in_place`] for `bounds`.
    pub fn clamp(
        &self,
        kernels: &Kernels,
        x: &DeviceBuffer<f32>,
        bounds: &DeviceBuffer<f32>,
        rows: usize,
        out: &mut GemvInput,
        stream: &Stream,
    ) -> Result<()> {
        let width = out.width();
        check(x.len() >= rows * width, || {
            format!("clamp of {rows} rows of {width} from {} values", x.len())
        })?;
        out.check_rows(rows)?;
        let n = (rows * width, width);
        self.launch_clamp(x.device_ptr(), out.act().x, bounds, n, stream)?;
        out.quantize(kernels, rows, stream)
    }

    /// Queues the clamp of `n` values of `x` in rows of `width`, whose
    /// columns split into equal runs that each take a `(min, max)` pair of
    /// `bounds`.
    pub fn clamp_in_place(
        &self,
        x: &mut DeviceBuffer<f32>,
        bounds: &DeviceBuffer<f32>,
        (n, width): (usize, usize),
        stream: &Stream,
    ) -> Result<()> {
        check(x.len() >= n, || {
            format!("clamp of {n} of {} values", x.len())
        })?;
        let xp = x.device_ptr();
        self.launch_clamp(xp, xp, bounds, (n, width), stream)
    }

    fn launch_clamp(
        &self,
        x: u64,
        y: u64,
        bounds: &DeviceBuffer<f32>,
        (n, width): (usize, usize),
        stream: &Stream,
    ) -> Result<()> {
        let sections = bounds.len() / 2;
        check(
            sections > 0
                && bounds.len().is_multiple_of(2)
                && width.is_multiple_of(sections)
                && n.is_multiple_of(width),
            || format!("clamp of rows of {width} by {} bounds", bounds.len()),
        )?;
        let (bp, len, width, sections) =
            (bounds.device_ptr(), n as u32, width as u32, sections as u32);
        // SAFETY: matches `vit_clamp(const float*, float*, unsigned,
        // unsigned, const float*, unsigned)`; the callers checked that `n`
        // values of `x` and `y` exist, and every section has its two bounds.
        unsafe {
            self.clamp.launch(
                linear(n),
                stream,
                &mut [
                    arg(&x),
                    arg(&y),
                    arg(&len),
                    arg(&width),
                    arg(&bp),
                    arg(&sections),
                ],
            )
        }
    }

    /// Queues `gate = gelu(gate) * up` over `n` values, GELU in its tanh
    /// approximation.
    pub fn geglu(
        &self,
        gate: &mut DeviceBuffer<f32>,
        up: &DeviceBuffer<f32>,
        n: usize,
        stream: &Stream,
    ) -> Result<()> {
        check(gate.len() >= n && up.len() >= n, || {
            format!("GEGLU of {n} values")
        })?;
        let (gp, upp, len) = (gate.device_ptr(), up.device_ptr(), n as u32);
        // SAFETY: matches `vit_geglu(float*, const float*, unsigned)`; `n`
        // values of both exist, as checked.
        unsafe {
            self.geglu
                .launch(linear(n), stream, &mut [arg(&gp), arg(&upp), arg(&len)])
        }
    }

    /// Queues bidirectional attention of every row of `[q | k | v]` over all
    /// of them, scaled by `1 / sqrt(head_dim)`, into the first `rows`
    /// inputs of `out`.
    pub fn attention(
        &self,
        kernels: &Kernels,
        qkv: &DeviceBuffer<f32>,
        (rows, n_head, head_dim): (usize, usize, usize),
        out: &mut GemvInput,
        stream: &Stream,
    ) -> Result<()> {
        let width = n_head * head_dim;
        check(
            qkv.len() >= rows * 3 * width && head_dim <= MAX_HEAD && out.width() == width,
            || format!("attention of {rows} rows of {n_head} heads of {head_dim}"),
        )?;
        out.check_rows(rows)?;
        if head_dim == MMA_HEAD {
            let config = LaunchConfig {
                grid: [(rows as u32).div_ceil(MMA_QUERIES), n_head as u32, 1],
                block: [MMA_THREADS, 1, 1],
                shared_bytes: 0,
            };
            let scale = std::f32::consts::LOG2_E / (head_dim as f32).sqrt();
            let (qp, op, n, heads) = (qkv.device_ptr(), out.act().x, rows as u32, n_head as u32);
            // SAFETY: matches `vit_attention_mma(const float*, float*,
            // unsigned, unsigned, float)`; it reads `rows` rows of q, k and v
            // and writes `rows * width` outputs, all checked.
            unsafe {
                self.attention_mma.launch(
                    config,
                    stream,
                    &mut [arg(&qp), arg(&op), arg(&n), arg(&heads), arg(&scale)],
                )
            }?;
            return out.quantize(kernels, rows, stream);
        }
        let config = LaunchConfig {
            grid: [(rows as u32).div_ceil(WARPS * QUERIES), n_head as u32, 1],
            block: [THREADS, 1, 1],
            shared_bytes: attention_shared(head_dim),
        };
        let scale = 1.0 / (head_dim as f32).sqrt();
        let (qp, op, n, heads, hd) = (
            qkv.device_ptr(),
            out.act().x,
            rows as u32,
            n_head as u32,
            head_dim as u32,
        );
        // SAFETY: matches `vit_attention(const float*, float*, unsigned,
        // unsigned, unsigned, float)`; it reads `rows` rows of q, k and v and
        // writes `rows * width` outputs, all checked, with the shared memory
        // its tiles take for this head size.
        unsafe {
            self.attention.launch(
                config,
                stream,
                &mut [
                    arg(&qp),
                    arg(&op),
                    arg(&n),
                    arg(&heads),
                    arg(&hd),
                    arg(&scale),
                ],
            )
        }?;
        out.quantize(kernels, rows, stream)
    }

    /// Queues `y = x w^T` for the first `rows` inputs of `x`: on the tensor
    /// cores with the inputs rounded to f16 for f16 weights, through
    /// [`Kernels::gemv_rows`] for other types.
    pub fn matmul(
        &self,
        kernels: &Kernels,
        w: &DeviceMatrix,
        x: &GemvInput,
        rows: usize,
        y: &mut DeviceBuffer<f32>,
        stream: &Stream,
    ) -> Result<()> {
        let (n, k) = (w.rows(), w.cols());
        if w.ty() != TensorType::F16 || !n.is_multiple_of(2) || !k.is_multiple_of(MM_STEP) {
            return kernels.gemv_rows(w, n, x, 0..rows, y, stream);
        }
        check(x.width() == k && y.len() >= rows * n, || {
            format!("{rows} inputs of {} times a {n}x{k} matrix", x.width())
        })?;
        x.check_rows(rows)?;
        let config = LaunchConfig {
            grid: [
                (rows as u32).div_ceil(MM_TILE),
                (n as u32).div_ceil(MM_TILE),
                1,
            ],
            block: [THREADS, 1, 1],
            shared_bytes: 0,
        };
        let (xp, wp, yp) = (
            x.values().device_ptr(),
            w.data().device_ptr(),
            y.device_ptr(),
        );
        let (rows, n, k) = (rows as u32, n as u32, k as u32);
        // SAFETY: matches `vit_matmul(const float*, const __half*, float*,
        // unsigned, unsigned, unsigned)`; `rows` inputs of `k` values, the
        // f16 matrix and `rows * n` outputs exist, as checked.
        unsafe {
            self.matmul.launch(
                config,
                stream,
                &mut [arg(&xp), arg(&wp), arg(&yp), arg(&rows), arg(&n), arg(&k)],
            )
        }
    }
}

/// Bytes of shared memory [`VisionKernels::attention`] takes: a tile of
/// padded keys, a tile of values, and per warp its queries and their tile
/// of weights.
fn attention_shared(head_dim: usize) -> u32 {
    let per_warp = QUERIES as usize * (head_dim + TILE);
    let floats = TILE * (head_dim + 1) + TILE * head_dim + WARPS as usize * per_warp;
    (floats * size_of::<f32>()) as u32
}

/// The number of whole inputs of `out` that `n` values fill.
fn fill(out: &GemvInput, n: usize) -> Result<usize> {
    check(n.is_multiple_of(out.width()), || {
        format!("{n} values into inputs of {}", out.width())
    })?;
    out.check_rows(n / out.width())?;
    Ok(n / out.width())
}
