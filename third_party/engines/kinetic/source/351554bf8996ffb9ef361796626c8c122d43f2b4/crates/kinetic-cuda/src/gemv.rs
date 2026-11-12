use std::ops::Range;
use std::rc::Rc;

use kinetic_quant::{Matrix, TensorType};

use crate::context::Context;
use crate::error::{Error, Result};
use crate::kernels::{arg, Kernels};
use crate::layout::device_layout;
use crate::memory::DeviceBuffer;
use crate::module::{Function, LaunchConfig};
use crate::stream::Stream;

/// Most vectors one GEMV launch multiplies, each weight being read once for
/// all of them. A vector's result does not depend on how many share its
/// launch.
pub const MAX_BATCH: usize = 16;

/// Rows per thread block; each row gets one warp.
const ROWS_PER_BLOCK: u32 = 4;
/// Rows and threads per block of the tensor-core kernels.
const MMA_ROWS: u32 = 16;
const MMA_THREADS: u32 = 128;
/// Inputs per tensor-core tile.
const MMA_TILE: usize = 8;
/// Elements per scale in the int8 copy of the input.
const Q8_BLOCK: usize = 32;
const QUANTIZE_THREADS: u32 = 256;

/// The weight types with kernels, in the order the device code numbers them.
pub(crate) const WEIGHT_TYPES: [TensorType; 21] = [
    TensorType::F32,
    TensorType::F16,
    TensorType::Q8_0,
    TensorType::Q4K,
    TensorType::Q5K,
    TensorType::Q6K,
    TensorType::Q4_1,
    TensorType::Q5_0,
    TensorType::Q5_1,
    TensorType::IQ4NL,
    TensorType::MXFP4,
    TensorType::Q2K,
    TensorType::Q3K,
    TensorType::IQ3S,
    TensorType::IQ2S,
    TensorType::IQ1S,
    TensorType::IQ1M,
    TensorType::TQ1_0,
    TensorType::TQ2_0,
    TensorType::Q4_0,
    TensorType::PQ2_0,
];

/// Kernel name prefixes, by index into `WEIGHT_TYPES`.
pub(crate) const GEMV_NAMES: [&str; WEIGHT_TYPES.len()] = [
    "gemv_f32",
    "gemv_f16",
    "gemv_q8_0",
    "gemv_q4_k",
    "gemv_q5_k",
    "gemv_q6_k",
    "gemv_q4_1",
    "gemv_q5_0",
    "gemv_q5_1",
    "gemv_iq4_nl",
    "gemv_mxfp4",
    "gemv_q2_k",
    "gemv_q3_k",
    "gemv_iq3_s",
    "gemv_iq2_s",
    "gemv_iq1_s",
    "gemv_iq1_m",
    "gemv_tq1_0",
    "gemv_tq2_0",
    "gemv_q4_0",
    "gemv_pq2_0",
];

pub(crate) fn weight_index(ty: TensorType) -> Option<usize> {
    WEIGHT_TYPES.iter().position(|&t| t == ty)
}

/// Elements per kernel block, and whether the kernel reads the f32 input.
fn gemv_layout(ty: TensorType) -> Option<(usize, bool)> {
    Some(match ty {
        TensorType::F32 => (4, true),
        TensorType::F16 => (8, true),
        TensorType::Q8_0
        | TensorType::Q4_0
        | TensorType::Q4_1
        | TensorType::Q5_0
        | TensorType::Q5_1
        | TensorType::IQ4NL
        | TensorType::MXFP4 => (32, false),
        TensorType::Q4K
        | TensorType::Q5K
        | TensorType::Q6K
        | TensorType::Q2K
        | TensorType::Q3K
        | TensorType::IQ3S
        | TensorType::IQ2S
        | TensorType::IQ1S
        | TensorType::IQ1M
        | TensorType::TQ1_0
        | TensorType::TQ2_0 => (256, false),
        TensorType::PQ2_0 => (128, false),
        _ => return None,
    })
}

/// A weight matrix in device memory, laid out for the GEMV kernels.
pub struct DeviceMatrix {
    ty: TensorType,
    rows: usize,
    cols: usize,
    data: DeviceBuffer<u8>,
}

impl DeviceMatrix {
    /// Copies `m` to the device. Fails for types without a GEMV kernel and
    /// for row lengths that are not a multiple of 32.
    pub fn upload(ctx: &Rc<Context>, m: &Matrix) -> Result<DeviceMatrix> {
        if gemv_layout(m.ty).is_none() {
            return Err(Error::Unsupported(m.ty));
        }
        if !m.cols.is_multiple_of(Q8_BLOCK) || u32::try_from(m.rows).is_err() {
            return Err(Error::Shape(format!(
                "{}x{} matrix: rows must fit in 32 bits and columns be a multiple of {Q8_BLOCK}",
                m.rows, m.cols
            )));
        }
        Ok(DeviceMatrix {
            ty: m.ty,
            rows: m.rows,
            cols: m.cols,
            data: DeviceBuffer::from_slice(ctx, &device_layout(m))?,
        })
    }

    pub fn ty(&self) -> TensorType {
        self.ty
    }

    pub fn rows(&self) -> usize {
        self.rows
    }

    pub fn cols(&self) -> usize {
        self.cols
    }

    /// Bytes of weights, which a GEMV reads once.
    pub fn size_bytes(&self) -> usize {
        self.data.len()
    }

    pub(crate) fn data(&self) -> &DeviceBuffer<u8> {
        &self.data
    }

    /// Blocks in the whole matrix, which planar layouts need to find their planes.
    pub(crate) fn total_blocks(&self) -> u64 {
        (self.rows * self.cols / self.ty.block_len()) as u64
    }
}

/// The f32 values, int8 copy and block scales of a GEMV input, as the
/// device code's `Act` struct holds them.
#[repr(C)]
#[derive(Clone, Copy)]
pub(crate) struct Act {
    pub(crate) x: u64,
    pub(crate) qs: u64,
    pub(crate) ds: u64,
}

impl Act {
    /// For kernels that write no GEMV input.
    pub(crate) const NULL: Act = Act { x: 0, qs: 0, ds: 0 };
}

/// Up to `capacity` GEMV input vectors of `width` elements, kept both as f32
/// for float weights and quantized to int8 in blocks of 32 for quantized
/// weights.
pub struct GemvInput {
    x: DeviceBuffer<f32>,
    qs: DeviceBuffer<i8>,
    ds: DeviceBuffer<f32>,
    width: usize,
}

impl GemvInput {
    /// One input of `width` elements; `width` must be a multiple of 32.
    pub fn new(ctx: &Rc<Context>, width: usize) -> Result<GemvInput> {
        GemvInput::batch(ctx, width, 1)
    }

    /// Room for `capacity` inputs of `width` elements each.
    pub fn batch(ctx: &Rc<Context>, width: usize, capacity: usize) -> Result<GemvInput> {
        let total = width.checked_mul(capacity);
        if !width.is_multiple_of(Q8_BLOCK) || total.is_none_or(|n| u32::try_from(n).is_err()) {
            return Err(Error::Shape(format!(
                "{capacity} GEMV inputs of {width} elements: not a 32-bit multiple of {Q8_BLOCK}"
            )));
        }
        let len = width * capacity;
        Ok(GemvInput {
            x: DeviceBuffer::new(ctx, len)?,
            qs: DeviceBuffer::new(ctx, len)?,
            ds: DeviceBuffer::new(ctx, 2 * len / Q8_BLOCK)?,
            width,
        })
    }

    /// Elements per input.
    pub fn width(&self) -> usize {
        self.width
    }

    /// Inputs it has room for.
    pub fn capacity(&self) -> usize {
        self.x.len() / self.width
    }

    /// Copies `x`, one or more whole inputs, to the first rows and queues
    /// their quantization on `stream`.
    pub fn upload(&mut self, kernels: &Kernels, x: &[f32], stream: &Stream) -> Result<()> {
        if !x.len().is_multiple_of(self.width) || x.len() > self.x.len() {
            return Err(Error::Shape(format!(
                "{} values do not fill whole inputs of {} (room for {})",
                x.len(),
                self.width,
                self.capacity()
            )));
        }
        self.x.copy_range_from(0, x)?;
        self.quantize(kernels, x.len() / self.width, stream)
    }

    /// Queues the quantization of the first `rows` inputs' f32 values.
    pub(crate) fn quantize(
        &mut self,
        kernels: &Kernels,
        rows: usize,
        stream: &Stream,
    ) -> Result<()> {
        self.check_rows(rows)?;
        let n = (rows * self.width) as u32;
        let (src, qs, ds) = (
            self.x.device_ptr(),
            self.qs.device_ptr(),
            self.ds.device_ptr(),
        );
        let mut args = [arg(&src), arg(&qs), arg(&ds), arg(&n)];
        let config = LaunchConfig::linear(n.div_ceil(QUANTIZE_THREADS), QUANTIZE_THREADS);
        // SAFETY: matches `quantize_q8(const float*, int8_t*, float2*,
        // unsigned)`; it touches `n` elements of x and qs and n / 32 pairs of
        // ds, all inside the buffers.
        unsafe { kernels.quantize_q8.launch(config, stream, &mut args) }
    }

    /// Queues a copy of inputs `rows` of `src`, values and quantized form
    /// alike, into this one from input `at` on, on `stream`.
    pub fn copy_rows_from(
        &mut self,
        at: usize,
        src: &GemvInput,
        rows: Range<usize>,
        stream: &Stream,
    ) -> Result<()> {
        if src.width != self.width {
            return Err(Error::Shape(format!(
                "inputs of {} copied into inputs of {}",
                src.width, self.width
            )));
        }
        let (w, s) = (self.width, 2 * self.width / Q8_BLOCK);
        let span = |per: usize| rows.start * per..rows.end * per;
        self.x.copy_from_device(at * w, &src.x, span(w), stream)?;
        self.qs.copy_from_device(at * w, &src.qs, span(w), stream)?;
        self.ds.copy_from_device(at * s, &src.ds, span(s), stream)
    }

    /// The f32 values, input after input.
    pub fn values(&self) -> &DeviceBuffer<f32> {
        &self.x
    }

    /// The int8 values: element `i` is `quantized[i] * d` of its block.
    pub fn quantized(&self) -> &DeviceBuffer<i8> {
        &self.qs
    }

    /// Per block of 32, interleaved: the scale `d` and `d` times the sum of
    /// the block's int8 values.
    pub fn block_scales(&self) -> &DeviceBuffer<f32> {
        &self.ds
    }

    pub(crate) fn act(&mut self) -> Act {
        Act {
            x: self.x.device_ptr(),
            qs: self.qs.device_ptr(),
            ds: self.ds.device_ptr(),
        }
    }

    /// Checks that `rows` inputs fit.
    pub(crate) fn check_rows(&self, rows: usize) -> Result<()> {
        if rows <= self.capacity() {
            Ok(())
        } else {
            Err(Error::Shape(format!(
                "{rows} inputs into room for {}",
                self.capacity()
            )))
        }
    }
}

impl Kernels {
    /// Queues `y = w x` for the first input of `x` on `stream`.
    pub fn gemv(
        &self,
        w: &DeviceMatrix,
        x: &GemvInput,
        y: &mut DeviceBuffer<f32>,
        stream: &Stream,
    ) -> Result<()> {
        self.gemv_rows(w, w.rows, x, 0..1, y, stream)
    }

    /// Queues `y[i] = w[..rows] x[inputs.start + i]` for every input in
    /// `inputs`, reading the first `rows` rows of `w`. `y` receives
    /// `inputs.len()` vectors of `rows` values.
    ///
    /// Up to [`MAX_BATCH`] inputs run as a GEMV that reads every weight once
    /// and gives each input the same bits whatever shares its launch. Larger
    /// batches run as a tiled matrix product, whose sums may differ from the
    /// GEMV's in the last bits.
    pub fn gemv_rows(
        &self,
        w: &DeviceMatrix,
        rows: usize,
        x: &GemvInput,
        inputs: Range<usize>,
        y: &mut DeviceBuffer<f32>,
        stream: &Stream,
    ) -> Result<()> {
        let n = inputs.len();
        if x.width != w.cols
            || rows > w.rows
            || inputs.end > x.capacity()
            || n == 0
            || y.len() < n * rows
        {
            return Err(Error::Shape(format!(
                "GEMV of {rows} rows of a {}x{} matrix with inputs {inputs:?} of {} (width {}) into {} outputs",
                w.rows,
                w.cols,
                x.capacity(),
                x.width,
                y.len()
            )));
        }
        if n > MAX_BATCH && self.gemm(w, rows, x, inputs.clone(), y, stream)? {
            return Ok(());
        }
        for (i, start) in inputs.clone().step_by(MAX_BATCH).enumerate() {
            let chunk = start..(start + MAX_BATCH).min(inputs.end);
            let out = y.ptr_at(i * MAX_BATCH * rows);
            self.gemv_launch(w, rows, x, chunk, out, stream)?;
        }
        Ok(())
    }

    /// Launches the GEMV for up to [`MAX_BATCH`] inputs into `y`, which
    /// holds `inputs.len() * rows` values; shapes are checked by the caller.
    fn gemv_launch(
        &self,
        w: &DeviceMatrix,
        rows: usize,
        x: &GemvInput,
        inputs: Range<usize>,
        yp: u64,
        stream: &Stream,
    ) -> Result<()> {
        let n = inputs.len();
        let (block_len, float_input) = gemv_layout(w.ty).ok_or(Error::Unsupported(w.ty))?;
        let out_rows = rows as u32;
        let blocks_per_row = (w.cols / block_len) as u32;
        let total = w.total_blocks();
        let wp = w.data.device_ptr();
        let first = inputs.start * x.width;
        if let Some(kernel) = self.tensor_core_gemv(w.ty, n) {
            let (qp, dp, n) = (
                x.qs.ptr_at(first),
                x.ds.ptr_at(2 * first / Q8_BLOCK),
                n as u32,
            );
            let mut args = [
                arg(&wp),
                arg(&qp),
                arg(&dp),
                arg(&yp),
                arg(&out_rows),
                arg(&blocks_per_row),
                arg(&total),
                arg(&n),
            ];
            let config = LaunchConfig::linear(out_rows.div_ceil(MMA_ROWS), MMA_THREADS);
            // SAFETY: matches `gemv_*_mma<tiles>(const uint8_t*, const
            // int8_t*, const float2*, float*, unsigned, unsigned, size_t,
            // unsigned)`; shapes were checked above. The kernel reads the
            // first `rows` rows of weights and `n * cols` int8 inputs with
            // their scales, and writes `n * rows` outputs.
            return unsafe { kernel.launch(config, stream, &mut args) };
        }
        let kernel = &self.gemv[weight_index(w.ty).ok_or(Error::Unsupported(w.ty))?][n - 1];
        let config = LaunchConfig::linear(out_rows.div_ceil(ROWS_PER_BLOCK), 32 * ROWS_PER_BLOCK);
        if float_input {
            let xp = x.x.ptr_at(first);
            let mut args = [
                arg(&wp),
                arg(&xp),
                arg(&yp),
                arg(&out_rows),
                arg(&blocks_per_row),
                arg(&total),
            ];
            // SAFETY: matches `gemv_*_<n>(const uint8_t*, const float*,
            // float*, unsigned, unsigned, size_t)`; shapes were checked above,
            // and the kernel reads `rows * cols` weights and `n * cols`
            // inputs and writes `n * rows` outputs.
            unsafe { kernel.launch(config, stream, &mut args) }
        } else {
            let (qp, dp) = (x.qs.ptr_at(first), x.ds.ptr_at(2 * first / Q8_BLOCK));
            let mut args = [
                arg(&wp),
                arg(&qp),
                arg(&dp),
                arg(&yp),
                arg(&out_rows),
                arg(&blocks_per_row),
                arg(&total),
            ];
            // SAFETY: matches `gemv_*_<n>(const uint8_t*, const int8_t*,
            // const float2*, float*, unsigned, unsigned, size_t)`; shapes were
            // checked above, and the kernel reads `rows * cols` weights,
            // `n * cols` int8 inputs with their scales and writes `n * rows`
            // outputs.
            unsafe { kernel.launch(config, stream, &mut args) }
        }
    }

    /// The tensor-core kernel for `n` inputs of type `ty`, if the device and
    /// type have one and it is the faster choice.
    fn tensor_core_gemv(&self, ty: TensorType, n: usize) -> Option<&Function> {
        // Both kinds compute exactly the same sums, so the choice is only
        // about speed: dp4a wins on small batches, Q6_K's longest.
        let kernels = self.gemv_mma.as_ref()?;
        let (by_type, from) = match ty {
            TensorType::Q4K => (&kernels[0], 3),
            TensorType::Q5K => (&kernels[1], 3),
            TensorType::Q6K => (&kernels[2], 5),
            _ => return None,
        };
        (n >= from).then(|| &by_type[n.div_ceil(MMA_TILE) - 1])
    }
}
