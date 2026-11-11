use std::ffi::CString;
use std::ops::Range;
use std::rc::Rc;

use kinetic_quant::TensorType;

use crate::error::{Error, Result};
use crate::gemv::{weight_index, Act, DeviceMatrix, GemvInput, MAX_BATCH, WEIGHT_TYPES};
use crate::kernels::{arg, Kernels};
use crate::memory::DeviceBuffer;
use crate::module::{Function, LaunchConfig, Module};
use crate::stream::Stream;

/// The tiles of the quantized kernels, narrowest first, which gemm.cuh
/// names `<format kernel>_<inputs>`, and of the float kernels; must match
/// gemm.cuh and gemm_float.cuh.
const QUANT_TILES: [Tile; 3] = [
    Tile {
        rows: 64,
        inputs: 32,
        threads: 256,
        shared: 33_792,
    },
    Tile {
        rows: 64,
        inputs: 64,
        threads: 256,
        shared: 45_056,
    },
    Tile {
        rows: 128,
        inputs: 128,
        threads: 512,
        shared: 90_112,
    },
];
/// f16 weights on tensor cores; must match GEMMH_* in gemm_float.cuh.
const HALF_TILES: [Tile; 1] = [Tile {
    rows: 64,
    inputs: 128,
    threads: 128,
    shared: 0,
}];
const FLOAT_TILES: [Tile; 1] = [Tile {
    rows: 32,
    inputs: 8,
    threads: 256,
    shared: 0,
}];
/// Elements per stage of the k loop; every row length must be a multiple.
const STAGE: usize = 128;
/// Inputs the split of the k axis is chosen for: a full prompt batch.
const SPLIT_INPUTS: u32 = 512;

/// Rows, inputs and threads per block, and dynamic shared bytes.
struct Tile {
    rows: u32,
    inputs: u32,
    threads: u32,
    shared: u32,
}

/// The tiled kernel of each weight type that has one.
fn gemm_name(ty: TensorType) -> Option<&'static str> {
    Some(match ty {
        TensorType::F32 => "gemm_f32",
        TensorType::F16 => "gemm_f16",
        TensorType::Q8_0 => "gemm_q8_0",
        TensorType::Q4_0 => "gemm_q4_0",
        TensorType::Q4K => "gemm_q4_k",
        TensorType::Q5K => "gemm_q5_k",
        TensorType::Q6K => "gemm_q6_k",
        TensorType::PQ2_0 => "gemm_pq2_0",
        _ => return None,
    })
}

fn is_float(ty: TensorType) -> bool {
    matches!(ty, TensorType::F32 | TensorType::F16)
}

fn tiles(ty: TensorType) -> &'static [Tile] {
    if ty == TensorType::F16 {
        &HALF_TILES
    } else if is_float(ty) {
        &FLOAT_TILES
    } else {
        &QUANT_TILES
    }
}

/// The matrix-product kernels of `module`, by index into `WEIGHT_TYPES` and
/// then by width, allowed the shared memory they take; none for a type
/// without a tiled kernel or where the device has less shared memory
/// (Turing), so those batches run as GEMVs.
pub(crate) fn gemm_functions(module: &Rc<Module>) -> Result<Vec<Vec<Function>>> {
    WEIGHT_TYPES
        .iter()
        .map(|&ty| {
            let Some(name) = gemm_name(ty) else {
                return Ok(Vec::new());
            };
            let mut fs = Vec::new();
            for tile in tiles(ty) {
                let name = if is_float(ty) {
                    name.to_owned()
                } else {
                    format!("{name}_{}", tile.inputs)
                };
                let f = module.function(&CString::new(name).expect("kernel names have no NUL"))?;
                if f.allow_shared(tile.shared).is_err() {
                    return Ok(Vec::new());
                }
                fs.push(f);
            }
            Ok(fs)
        })
        .collect()
}

/// One launch: `w[..rows]`, and for a gated product `up`, times inputs
/// `inputs` of `x`.
struct Product<'a> {
    w: &'a DeviceMatrix,
    up: Option<&'a DeviceMatrix>,
    rows: usize,
    x: &'a GemvInput,
    inputs: Range<usize>,
    tile: &'static Tile,
    /// GELU on a gated product's gate in place of SiLU.
    gelu: bool,
}

impl Kernels {
    /// Queues `y = w[..rows] x[inputs]` as a tiled matrix product, or
    /// returns `false` if the type and shape of `w` have no such kernel.
    /// Shapes are checked by the caller.
    pub(crate) fn gemm(
        &self,
        w: &DeviceMatrix,
        rows: usize,
        x: &GemvInput,
        inputs: Range<usize>,
        y: &mut DeviceBuffer<f32>,
        stream: &Stream,
    ) -> Result<bool> {
        let Some((kernel, tile)) = self.gemm_kernel(w, inputs.len()) else {
            return Ok(false);
        };
        let p = Product {
            w,
            up: None,
            rows,
            x,
            inputs,
            tile,
            gelu: false,
        };
        let blocks = self.gemm_grid(&p);
        let splits = if is_float(w.ty()) {
            1
        } else {
            self.gemm_splits(rows, w.cols() / STAGE)
        };
        if splits > 1 {
            y.zero_prefix(p.inputs.len() * rows, stream)?;
        }
        let out = Act {
            x: y.device_ptr(),
            qs: 0,
            ds: 0,
        };
        self.launch_gemm(kernel, &p, out, [blocks[0], blocks[1], splits], stream)?;
        Ok(true)
    }

    /// Queues `out = silu(gate x) * (up x)`, or with `gelu` `gelu(gate x) *
    /// (up x)`, for inputs `inputs` of `x`, into
    /// the first `inputs.len()` inputs of `out`, as one matrix product that
    /// applies the activation to its sums and quantizes the result. Returns
    /// `false`, queuing nothing, for batches of up to [`MAX_BATCH`] inputs,
    /// which keep to the GEMV kernels, and for matrices without a quantized
    /// product kernel or of different types; the separate products and
    /// [`Kernels::swiglu`] then do the same.
    #[allow(clippy::too_many_arguments)]
    pub fn glu_matmul(
        &self,
        gate: &DeviceMatrix,
        up: &DeviceMatrix,
        gelu: bool,
        x: &GemvInput,
        inputs: Range<usize>,
        out: &mut GemvInput,
        stream: &Stream,
    ) -> Result<bool> {
        let shape_ok = up.rows() == gate.rows()
            && up.cols() == gate.cols()
            && gate.cols() == x.width()
            && out.width() == gate.rows()
            && inputs.end <= x.capacity();
        if !shape_ok {
            return Err(Error::Shape(format!(
                "gated product of {}x{} and {}x{} matrices from inputs of {} into {}",
                gate.rows(),
                gate.cols(),
                up.rows(),
                up.cols(),
                x.width(),
                out.width()
            )));
        }
        out.check_rows(inputs.len())?;
        let (kernel, tile) = match self.gemm_kernel(gate, inputs.len()) {
            Some(k) if inputs.len() > MAX_BATCH && up.ty() == gate.ty() && !is_float(gate.ty()) => {
                k
            }
            _ => return Ok(false),
        };
        let p = Product {
            w: gate,
            up: Some(up),
            rows: gate.rows(),
            x,
            inputs,
            tile,
            gelu,
        };
        let [bx, by] = self.gemm_grid(&p);
        self.launch_gemm(kernel, &p, out.act(), [bx, by, 1], stream)?;
        Ok(true)
    }

    /// The kernel for `n` inputs of `w` and its tile: the narrowest that
    /// takes them all, or the widest.
    fn gemm_kernel(&self, w: &DeviceMatrix, n: usize) -> Option<(&Function, &'static Tile)> {
        // Formats without a tiled kernel run their prompts through the GEMV.
        let i = weight_index(w.ty())?;
        if !w.cols().is_multiple_of(STAGE) {
            return None;
        }
        let tiles = tiles(w.ty());
        let k = tiles
            .iter()
            .position(|t| n <= t.inputs as usize)
            .unwrap_or(tiles.len() - 1);
        Some((self.gemm.get(i)?.get(k)?, &tiles[k]))
    }

    /// Blocks along the inputs and the rows; a gated product's block covers
    /// half as many rows of each matrix.
    fn gemm_grid(&self, p: &Product) -> [u32; 2] {
        let tile = p.tile;
        let rows = if p.up.is_some() {
            tile.rows / 2
        } else {
            tile.rows
        };
        [
            (p.inputs.len() as u32).div_ceil(tile.inputs),
            (p.rows as u32).div_ceil(rows),
        ]
    }

    fn launch_gemm(
        &self,
        kernel: &Function,
        p: &Product,
        out: Act,
        grid: [u32; 3],
        stream: &Stream,
    ) -> Result<()> {
        let first = p.inputs.start * p.x.width();
        let (xp, dp) = if is_float(p.w.ty()) {
            (p.x.values().ptr_at(first), 0)
        } else {
            (
                p.x.quantized().ptr_at(first),
                p.x.block_scales().ptr_at(first / 16),
            )
        };
        let wp = p.w.data().device_ptr();
        let up = p.up.map_or(0, |m| m.data().device_ptr());
        let (rows, cols, n) = (p.rows as u32, p.w.cols() as u32, p.inputs.len() as u32);
        let total = p.w.total_blocks();
        let gelu = u32::from(p.gelu);
        let mut args = [
            arg(&wp),
            arg(&up),
            arg(&xp),
            arg(&dp),
            arg(&out.x),
            arg(&out.qs),
            arg(&out.ds),
            arg(&rows),
            arg(&cols),
            arg(&total),
            arg(&n),
            arg(&gelu),
        ];
        let tile = p.tile;
        let config = LaunchConfig {
            grid,
            block: [tile.threads, 1, 1],
            shared_bytes: tile.shared,
        };
        // SAFETY: matches `gemm_*(const uint8_t*, const uint8_t*, const
        // void*, const float2*, float*, int8_t*, float2*, unsigned, unsigned,
        // size_t, unsigned, unsigned)`. The callers checked that `x` holds the inputs,
        // `out` their `n * rows` outputs (and for a gated product their int8
        // copy and scales) and `w` (and `up`, of the same type and shape) at
        // least `rows` rows of `cols`, a multiple of the kernel's stage; the
        // kernel reads only those and writes only `out`.
        unsafe { kernel.launch(config, stream, &mut args) }
    }

    /// Splits of the k axis for `rows` rows over `stages` stages: two when
    /// that fills the last round of the widest tiles over [`SPLIT_INPUTS`]
    /// inputs, one per multiprocessor, markedly better. Every batch and tile
    /// splits the same, so that an input's outputs have the same bits
    /// whatever else shares the product.
    fn gemm_splits(&self, rows: usize, stages: usize) -> u32 {
        let wide = &QUANT_TILES[QUANT_TILES.len() - 1];
        let blocks = SPLIT_INPUTS.div_ceil(wide.inputs) * (rows as u32).div_ceil(wide.rows);
        let sms = self.multiprocessors;
        let fill = |b: u32| b as f32 / (b.div_ceil(sms) * sms) as f32;
        if stages >= 2 && fill(2 * blocks) > fill(blocks) + 0.05 {
            2
        } else {
            1
        }
    }
}
