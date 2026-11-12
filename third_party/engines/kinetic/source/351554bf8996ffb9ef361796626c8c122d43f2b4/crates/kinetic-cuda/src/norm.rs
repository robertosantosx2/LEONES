use crate::batch::Batch;
use crate::error::{Error, Result};
use crate::gemv::{weight_index, Act, DeviceMatrix, GemvInput};
use crate::kernels::{arg, launch_struct, Kernels};
use crate::memory::DeviceBuffer;
use crate::module::LaunchConfig;
use crate::stream::Stream;

/// Threads per row and values per thread; must match norm.cuh.
const ROW_THREADS: u32 = 1024;
const MAX_ROW: usize = 8 * ROW_THREADS as usize;
const EMBED_THREADS: u32 = 256;
const ADD_THREADS: u32 = 256;

/// An RMS norm: `x / rms(x) * weight`.
#[derive(Clone, Copy)]
pub struct RmsNorm<'a> {
    pub weight: &'a DeviceBuffer<f32>,
    pub eps: f32,
}

/// The norms around a residual add: `post` normalizes the block output
/// and `scale` multiplies it before it is added, `out_scale` multiplies the
/// sum, and `next` normalizes it for the following block, which without
/// one takes the sum as it is.
#[derive(Clone, Copy)]
pub struct AddNorm<'a> {
    pub post: Option<&'a DeviceBuffer<f32>>,
    pub scale: f32,
    pub out_scale: f32,
    pub next: Option<&'a DeviceBuffer<f32>>,
    pub eps: f32,
}

#[repr(C)]
struct NormArgs {
    x: u64,
    weight: u64,
    out: Act,
    eps: f32,
    len: u32,
    out_stride: u32,
    out_offset: u32,
}

#[repr(C)]
struct AddNormArgs {
    x: u64,
    y: u64,
    post: u64,
    weight: u64,
    out: Act,
    eps: f32,
    len: u32,
    scale: f32,
    out_scale: f32,
}

#[repr(C)]
struct EmbedArgs {
    table: u64,
    batch: u64,
    out: u64,
    total: u64,
    ty: u32,
    cols: u32,
    rows: u32,
    scale: f32,
}

impl Kernels {
    /// Queues `out[i][at..at + len] = norm(x[i])` for the first `rows` rows of
    /// `x`, where `len` is the norm's length; `at` and `len` must be
    /// multiples of 32.
    pub fn rms_norm(
        &self,
        x: &DeviceBuffer<f32>,
        norm: RmsNorm,
        out: &mut GemvInput,
        at: usize,
        rows: usize,
        stream: &Stream,
    ) -> Result<()> {
        let len = norm.weight.len();
        if !len.is_multiple_of(32)
            || len > MAX_ROW
            || !at.is_multiple_of(32)
            || at + len > out.width()
        {
            return Err(Error::Shape(format!(
                "norm of {len} into columns {at}.. of inputs of {}",
                out.width()
            )));
        }
        x.check_holds(rows * len, "rms_norm input")?;
        out.check_rows(rows)?;
        let args = NormArgs {
            x: x.device_ptr(),
            weight: norm.weight.device_ptr(),
            out: out.act(),
            eps: norm.eps,
            len: len as u32,
            out_stride: out.width() as u32,
            out_offset: at as u32,
        };
        // SAFETY: matches `NormArgs`; the kernel reads `rows * len` inputs
        // and `len` weights and writes inside `rows` outputs, all checked.
        unsafe {
            launch_struct(
                &self.rms_norm_q8,
                LaunchConfig::linear(rows as u32, ROW_THREADS),
                stream,
                &args,
            )
        }
    }

    /// Queues `out = x`, unnormalized, for the first `rows` rows of `x`.
    pub fn input_rows(
        &self,
        x: &DeviceBuffer<f32>,
        out: &mut GemvInput,
        rows: usize,
        stream: &Stream,
    ) -> Result<()> {
        let len = out.width();
        if len > MAX_ROW {
            return Err(Error::Shape(format!("{len} inputs in one row")));
        }
        x.check_holds(rows * len, "input rows")?;
        out.check_rows(rows)?;
        let args = NormArgs {
            x: x.device_ptr(),
            weight: 0,
            out: out.act(),
            eps: 0.0,
            len: len as u32,
            out_stride: len as u32,
            out_offset: 0,
        };
        // SAFETY: matches `NormArgs`; without a weight the kernel reads
        // `rows * len` inputs and writes as many outputs, all checked.
        unsafe {
            launch_struct(
                &self.rms_norm_q8,
                LaunchConfig::linear(rows as u32, ROW_THREADS),
                stream,
                &args,
            )
        }
    }

    /// Queues, for each of the first `rows` rows, `x += scale * post(y)`
    /// and `out = next(x)`.
    pub fn add_norm(
        &self,
        x: &mut DeviceBuffer<f32>,
        y: &DeviceBuffer<f32>,
        norm: AddNorm,
        out: &mut GemvInput,
        rows: usize,
        stream: &Stream,
    ) -> Result<()> {
        let len = out.width();
        let fits = |w: Option<&DeviceBuffer<f32>>| w.is_none_or(|w| w.len() == len);
        if len > MAX_ROW || !fits(norm.post) || !fits(norm.next) {
            return Err(Error::Shape(format!(
                "add and norm of {len} into inputs of {}",
                out.width()
            )));
        }
        x.check_holds(rows * len, "add_norm stream")?;
        y.check_holds(rows * len, "add_norm block output")?;
        out.check_rows(rows)?;
        let args = AddNormArgs {
            x: x.device_ptr(),
            y: y.device_ptr(),
            post: norm.post.map_or(0, DeviceBuffer::device_ptr),
            weight: norm.next.map_or(0, DeviceBuffer::device_ptr),
            out: out.act(),
            eps: norm.eps,
            len: len as u32,
            scale: norm.scale,
            out_scale: norm.out_scale,
        };
        // SAFETY: matches `AddNormArgs`; every buffer holds `rows * len`
        // values or `len` weights, as checked.
        unsafe {
            launch_struct(
                &self.add_norm_q8,
                LaunchConfig::linear(rows as u32, ROW_THREADS),
                stream,
                &args,
            )
        }
    }

    /// Queues per-layer inputs in place of `proj`, the projected embeddings
    /// of `rows` tokens: each run of `norm.weight.len()` values is scaled by
    /// `proj_scale`, normalized, added to its run of `tokens` and divided by
    /// the square root of two.
    pub fn per_layer_inputs(
        &self,
        proj: &mut DeviceBuffer<f32>,
        tokens: &DeviceBuffer<f32>,
        norm: RmsNorm,
        proj_scale: f32,
        len: usize,
        stream: &Stream,
    ) -> Result<()> {
        let width = norm.weight.len();
        if !width.is_multiple_of(32) || width > 1024 || !len.is_multiple_of(width) {
            return Err(Error::Shape(format!("per-layer inputs in runs of {width}")));
        }
        proj.check_holds(len, "per-layer projections")?;
        tokens.check_holds(len, "per-layer token rows")?;
        let (p, t, w) = (
            proj.device_ptr(),
            tokens.device_ptr(),
            norm.weight.device_ptr(),
        );
        let mut args = [arg(&p), arg(&t), arg(&w), arg(&proj_scale), arg(&norm.eps)];
        let config = LaunchConfig::linear((len / width) as u32, width as u32);
        // SAFETY: matches `per_layer_inputs(float*, const float*, const
        // float*, float, float)`; both buffers hold `len` values and the
        // norm one per thread, as checked.
        unsafe { self.per_layer_inputs.launch(config, stream, &mut args) }
    }

    /// Queues `out = gelu(gate) * inputs of layer`, for `rows` rows of
    /// `out.width()` values; `inputs` holds `layers` such runs per row.
    #[allow(clippy::too_many_arguments)]
    pub fn per_layer_gate(
        &self,
        gate: &DeviceBuffer<f32>,
        inputs: &DeviceBuffer<f32>,
        layer: usize,
        layers: usize,
        out: &mut GemvInput,
        rows: usize,
        stream: &Stream,
    ) -> Result<()> {
        let width = out.width();
        let n = rows * width;
        if layer >= layers {
            return Err(Error::Shape(format!("layer {layer} of {layers}")));
        }
        gate.check_holds(n, "per-layer gate")?;
        inputs.check_holds(n * layers, "per-layer inputs")?;
        out.check_rows(rows)?;
        let (g, x, act) = (gate.device_ptr(), inputs.device_ptr(), out.act());
        let (layer, layers, width, n) = (layer as u32, layers as u32, width as u32, n as u32);
        let mut args = [
            arg(&g),
            arg(&x),
            arg(&layer),
            arg(&layers),
            arg(&width),
            arg(&act),
            arg(&n),
        ];
        let config = LaunchConfig::linear(n.div_ceil(ADD_THREADS), ADD_THREADS);
        // SAFETY: matches `per_layer_gate_q8(const float*, const float*,
        // unsigned, unsigned, unsigned, Act, unsigned)`; the gate and output
        // hold `n` values and the inputs `layers` times as many, as checked.
        unsafe { self.per_layer_gate_q8.launch(config, stream, &mut args) }
    }

    /// Queues `y += x` over the first `len` values.
    pub fn add(
        &self,
        y: &mut DeviceBuffer<f32>,
        x: &DeviceBuffer<f32>,
        len: usize,
        stream: &Stream,
    ) -> Result<()> {
        y.check_holds(len, "sum")?;
        x.check_holds(len, "addend")?;
        let (dst, src, n) = (y.device_ptr(), x.device_ptr(), len as u32);
        let config = LaunchConfig::linear(n.div_ceil(ADD_THREADS), ADD_THREADS);
        // SAFETY: matches `add_f32(float*, const float*, unsigned)`; both
        // buffers hold `len` values, as checked.
        unsafe {
            self.add_f32
                .launch(config, stream, &mut [arg(&dst), arg(&src), arg(&n)])
        }
    }

    /// Queues `out[t] = scale * table[token t]`, dequantized, for every
    /// token of `batch`.
    pub fn embed(
        &self,
        table: &DeviceMatrix,
        scale: f32,
        batch: &Batch,
        out: &mut DeviceBuffer<f32>,
        stream: &Stream,
    ) -> Result<()> {
        let ty = weight_index(table.ty()).ok_or(Error::Unsupported(table.ty()))?;
        let cols = table.cols();
        out.check_holds(batch.len() * cols, "embedding output")?;
        let args = EmbedArgs {
            table: table.data().device_ptr(),
            batch: batch.device_ptr(),
            out: out.device_ptr(),
            total: table.total_blocks(),
            ty: ty as u32,
            cols: cols as u32,
            rows: table.rows() as u32,
            scale,
        };
        let config = LaunchConfig {
            grid: [batch.len() as u32, (cols as u32).div_ceil(EMBED_THREADS), 1],
            block: [EMBED_THREADS, 1, 1],
            shared_bytes: 0,
        };
        // SAFETY: matches `EmbedArgs`; the kernel writes `tokens * cols`
        // outputs and reads one table row per token id below `rows`.
        unsafe { launch_struct(&self.embed, config, stream, &args) }
    }
}
