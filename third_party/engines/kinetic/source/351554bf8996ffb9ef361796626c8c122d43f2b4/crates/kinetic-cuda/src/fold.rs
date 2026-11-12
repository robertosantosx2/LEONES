use crate::error::{Error, Result};
use crate::gemv::{Act, GemvInput};
use crate::kernels::{launch_struct, Kernels};
use crate::memory::DeviceBuffer;
use crate::module::LaunchConfig;
use crate::stream::Stream;

const FOLD_THREADS: usize = 256;
/// Largest transform block, by the shared memory the kernel takes.
const MAX_FOLD_BLOCK: usize = 8192;

/// Value heads stored tiled, which a fold regroups by key head first.
#[derive(Clone, Copy, Debug)]
pub struct ValueHeads {
    pub head_dim: usize,
    pub n_k: usize,
    pub n_v: usize,
}

#[repr(C)]
struct UnfoldArgs {
    x: u64,
    signs: u64,
    width: u32,
    block: u32,
}

#[repr(C)]
struct FoldArgs {
    x: u64,
    signs: u64,
    out: Act,
    width: u32,
    block: u32,
    head_dim: u32,
    n_k: u32,
    rep: u32,
}

impl Kernels {
    /// Queues `out = H (D x)` for the first `rows` rows of `x`, where `D`
    /// multiplies by `signs` and `H` is the normalized Walsh-Hadamard
    /// transform on each `block` values; with `heads`, the value heads are
    /// regrouped first. This is the input of a weight stored folded.
    #[allow(clippy::too_many_arguments)]
    pub fn fold(
        &self,
        x: &GemvInput,
        signs: &DeviceBuffer<f32>,
        block: usize,
        heads: Option<ValueHeads>,
        out: &mut GemvInput,
        rows: usize,
        stream: &Stream,
    ) -> Result<()> {
        let width = x.width();
        let heads_ok = heads.is_none_or(|h| {
            h.n_k > 0 && h.n_v.is_multiple_of(h.n_k) && h.head_dim * h.n_v == width
        });
        if !block.is_power_of_two()
            || !(32..=MAX_FOLD_BLOCK).contains(&block)
            || !width.is_multiple_of(block)
            || out.width() != width
            || signs.len() != width
            || !heads_ok
        {
            return Err(Error::Shape(format!(
                "fold of {width} inputs in blocks of {block} into {} with {} signs",
                out.width(),
                signs.len()
            )));
        }
        x.check_rows(rows)?;
        out.check_rows(rows)?;
        let h = heads.unwrap_or(ValueHeads {
            head_dim: width,
            n_k: 1,
            n_v: 1,
        });
        let args = FoldArgs {
            x: x.values().device_ptr(),
            signs: signs.device_ptr(),
            out: out.act(),
            width: width as u32,
            block: block as u32,
            head_dim: h.head_dim as u32,
            n_k: h.n_k as u32,
            rep: (h.n_v / h.n_k) as u32,
        };
        let config = LaunchConfig {
            grid: [(width / block) as u32, rows as u32, 1],
            block: [block.min(FOLD_THREADS) as u32, 1, 1],
            shared_bytes: (block * size_of::<f32>()) as u32,
        };
        // SAFETY: matches `FoldArgs`; the kernel reads `rows` rows of `x`
        // and `width` signs and writes `rows` rows of `out`, all checked.
        unsafe { launch_struct(&self.fold_rows, config, stream, &args) }
    }

    /// Queues the inverse of [`Kernels::fold`] without regrouping, in place
    /// on the first `rows` rows of `x`, rows as long as `signs`.
    pub fn unfold(
        &self,
        x: &mut DeviceBuffer<f32>,
        signs: &DeviceBuffer<f32>,
        block: usize,
        rows: usize,
        stream: &Stream,
    ) -> Result<()> {
        let width = signs.len();
        if !block.is_power_of_two()
            || !(32..=MAX_FOLD_BLOCK).contains(&block)
            || !width.is_multiple_of(block)
        {
            return Err(Error::Shape(format!(
                "unfold of {width} values in blocks of {block}"
            )));
        }
        x.check_holds(rows * width, "unfold rows")?;
        let args = UnfoldArgs {
            x: x.device_ptr(),
            signs: signs.device_ptr(),
            width: width as u32,
            block: block as u32,
        };
        let config = LaunchConfig {
            grid: [(width / block) as u32, rows as u32, 1],
            block: [block.min(FOLD_THREADS) as u32, 1, 1],
            shared_bytes: (block * size_of::<f32>()) as u32,
        };
        // SAFETY: matches `UnfoldArgs`; the kernel rewrites `rows` rows of
        // `x` and reads `width` signs, both checked.
        unsafe { launch_struct(&self.unfold_rows, config, stream, &args) }
    }
}
