use std::ffi::{c_void, CStr, CString};
use std::rc::Rc;

use crate::attention::{flash_shared, FLASH_HEADS};
use crate::context::Context;
use crate::error::{Error, Result};
use crate::gemm::gemm_functions;
use crate::gemv::{GEMV_NAMES, MAX_BATCH, WEIGHT_TYPES};
use crate::memory::DeviceBuffer;
use crate::module::{Function, LaunchConfig, Module};
use crate::moe::{EXPERT_TYPES, MOE_NAMES};
use crate::stream::Stream;

/// Fatbin images start with a header the driver reads in 8-byte words.
#[repr(C, align(16))]
pub(crate) struct Aligned<T: ?Sized>(pub(crate) T);

/// Written by build.rs; empty when nvcc was not available.
pub(crate) static IMAGE: &Aligned<[u8]> =
    &Aligned(*include_bytes!(concat!(env!("OUT_DIR"), "/kernels.fatbin")));

const READ_SUM_THREADS: u32 = 256;
const READ_SUM_BLOCKS_PER_SM: u32 = 4;

/// The crate's kernels, loaded into one context.
pub struct Kernels {
    /// By weight type, then by batch size from 1.
    pub(crate) gemv: [Vec<Function>; WEIGHT_TYPES.len()],
    /// Tensor-core kernels for Q4_K, Q5_K and Q6_K, for up to 8 and up to 16
    /// inputs, on devices that have integer tensor cores.
    pub(crate) gemv_mma: Option<[[Function; 2]; 3]>,
    /// Matrix products for larger batches, by weight type and tile width,
    /// where the device has the shared memory they need.
    pub(crate) gemm: Vec<Vec<Function>>,
    pub(crate) quantize_q8: Function,
    pub(crate) fold_rows: Function,
    pub(crate) unfold_rows: Function,
    pub(crate) embed: Function,
    pub(crate) rms_norm_q8: Function,
    pub(crate) add_norm_q8: Function,
    pub(crate) swiglu_q8: Function,
    pub(crate) geglu_q8: Function,
    pub(crate) per_layer_inputs: Function,
    pub(crate) per_layer_gate_q8: Function,
    pub(crate) argmax_partial: Function,
    pub(crate) argmax_final: Function,
    pub(crate) attn_norm_rows: Function,
    pub(crate) attn_prepare: Function,
    /// By query heads per block: 1 and 2.
    pub(crate) attn_chunk: [Function; 2],
    /// Attention for batches larger than [`MAX_BATCH`], where the device has
    /// the shared memory it needs.
    pub(crate) attn_flash: Option<Function>,
    pub(crate) attn_combine: Function,
    pub(crate) attn_copy_kv: Function,
    pub(crate) delta_conv: Function,
    pub(crate) delta_conv_batch: Function,
    pub(crate) delta_ring_store: Function,
    pub(crate) delta_chunk_prep: Function,
    pub(crate) delta_chunk_scan: Function,
    pub(crate) delta_rule: Function,
    pub(crate) delta_gated_norm: Function,
    pub(crate) short_conv_q8: Function,
    pub(crate) short_conv_batch: Function,
    pub(crate) short_conv_ring_store: Function,
    pub(crate) ssm_conv: Function,
    pub(crate) ssm_ring_store: Function,
    pub(crate) ssm_scan: Function,
    pub(crate) ssm_gated_norm: Function,
    pub(crate) add_f32: Function,
    pub(crate) quantize_q8k: Function,
    /// Routed-expert kernels by weight type; see `moe.rs`.
    pub(crate) moe_gate_up: [Function; EXPERT_TYPES.len()],
    pub(crate) moe_down: [Function; EXPERT_TYPES.len()],
    pub(crate) moe_combine: Function,
    pub(crate) moe_route: Function,
    pub(crate) moe_assign: Function,
    read_sum: Function,
    pub(crate) multiprocessors: u32,
}

impl Kernels {
    /// Loads the kernels compiled into this crate, or fails with
    /// [`Error::KernelsNotBuilt`] if it was built without nvcc.
    pub fn load(ctx: &Rc<Context>) -> Result<Kernels> {
        if IMAGE.0.is_empty() {
            return Err(Error::KernelsNotBuilt);
        }
        // SAFETY: the image is nvcc's fatbin output, embedded unchanged.
        let module = unsafe { Module::load(ctx, &IMAGE.0) }?;
        let mut gemv: [Vec<Function>; WEIGHT_TYPES.len()] = Default::default();
        for (kernels, name) in gemv.iter_mut().zip(GEMV_NAMES) {
            for n in 1..=MAX_BATCH {
                let name = CString::new(format!("{name}_{n}")).expect("kernel names have no NUL");
                kernels.push(module.function(&name)?);
            }
        }
        let info = ctx.device().info()?;
        let mma = |name: &CStr| module.function(name);
        let gemv_mma = (info.compute_capability >= (8, 0))
            .then(|| -> Result<_> {
                Ok([
                    [mma(c"gemv_q4_k_mma1")?, mma(c"gemv_q4_k_mma2")?],
                    [mma(c"gemv_q5_k_mma1")?, mma(c"gemv_q5_k_mma2")?],
                    [mma(c"gemv_q6_k_mma1")?, mma(c"gemv_q6_k_mma2")?],
                ])
            })
            .transpose()?;
        let gemm = gemm_functions(&module)?;
        let attn_flash = module.function(c"attn_flash")?;
        let attn_flash = attn_flash
            .allow_shared(FLASH_HEADS.into_iter().map(flash_shared).max().unwrap_or(0))
            .is_ok()
            .then_some(attn_flash);
        let moe = |prefix: &str| -> Result<[Function; EXPERT_TYPES.len()]> {
            let named = |ty: &str| {
                module.function(
                    &CString::new(format!("{prefix}_{ty}")).expect("kernel names have no NUL"),
                )
            };
            let functions = MOE_NAMES
                .iter()
                .map(|ty| named(ty))
                .collect::<Result<Vec<_>>>()?;
            Ok(functions
                .try_into()
                .unwrap_or_else(|_| unreachable!("a kernel per type")))
        };
        Ok(Kernels {
            gemv,
            gemv_mma,
            gemm,
            quantize_q8: module.function(c"quantize_q8")?,
            fold_rows: module.function(c"fold_rows")?,
            unfold_rows: module.function(c"unfold_rows")?,
            embed: module.function(c"embed")?,
            rms_norm_q8: module.function(c"rms_norm_q8")?,
            add_norm_q8: module.function(c"add_norm_q8")?,
            swiglu_q8: module.function(c"swiglu_q8")?,
            geglu_q8: module.function(c"geglu_q8")?,
            per_layer_inputs: module.function(c"per_layer_inputs")?,
            per_layer_gate_q8: module.function(c"per_layer_gate_q8")?,
            argmax_partial: module.function(c"argmax_partial")?,
            argmax_final: module.function(c"argmax_final")?,
            attn_norm_rows: module.function(c"attn_norm_rows")?,
            attn_prepare: module.function(c"attn_prepare")?,
            attn_chunk: [
                module.function(c"attn_chunk_1")?,
                module.function(c"attn_chunk_2")?,
            ],
            attn_flash,
            attn_combine: module.function(c"attn_combine")?,
            attn_copy_kv: module.function(c"attn_copy_kv")?,
            delta_conv: module.function(c"delta_conv")?,
            delta_conv_batch: module.function(c"delta_conv_batch")?,
            delta_ring_store: module.function(c"delta_ring_store")?,
            delta_chunk_prep: module.function(c"delta_chunk_prep")?,
            delta_chunk_scan: module.function(c"delta_chunk_scan")?,
            delta_rule: module.function(c"delta_rule")?,
            delta_gated_norm: module.function(c"delta_gated_norm")?,
            short_conv_q8: module.function(c"short_conv_q8")?,
            short_conv_batch: module.function(c"short_conv_batch")?,
            short_conv_ring_store: module.function(c"short_conv_ring_store")?,
            ssm_conv: module.function(c"ssm_conv")?,
            ssm_ring_store: module.function(c"ssm_ring_store")?,
            ssm_scan: module.function(c"ssm_scan")?,
            ssm_gated_norm: module.function(c"ssm_gated_norm")?,
            add_f32: module.function(c"add_f32")?,
            quantize_q8k: module.function(c"quantize_q8k")?,
            moe_gate_up: moe("moe_gate_up")?,
            moe_down: moe("moe_down")?,
            moe_combine: module.function(c"moe_combine")?,
            moe_route: module.function(c"moe_route")?,
            moe_assign: module.function(c"moe_assign")?,
            read_sum: module.function(c"read_sum")?,
            multiprocessors: info.multiprocessors,
        })
    }

    /// Whether batches of more than [`MAX_BATCH`] tokens can run in one pass;
    /// without, they must go in steps of at most that many.
    pub fn large_batches(&self) -> bool {
        self.attn_flash.is_some()
    }

    /// Reads all of `data` once and adds its sum as 32-bit words to `out[0]`.
    ///
    /// The sum is meaningless; the kernel's throughput is the achievable
    /// read bandwidth of device memory, the ceiling for memory-bound kernels.
    /// `data.len()` must be a multiple of 16.
    pub fn read_sum(
        &self,
        data: &DeviceBuffer<u8>,
        out: &mut DeviceBuffer<u32>,
        stream: &Stream,
    ) -> Result<()> {
        if !data.len().is_multiple_of(16) || out.is_empty() {
            return Err(Error::Shape(format!(
                "read_sum needs a multiple of 16 bytes and one output, got {} and {}",
                data.len(),
                out.len()
            )));
        }
        let words = (data.len() / 16) as u64;
        let (src, dst) = (data.device_ptr(), out.device_ptr());
        let mut args = [arg(&src), arg(&words), arg(&dst)];
        let config = LaunchConfig::linear(
            self.multiprocessors * READ_SUM_BLOCKS_PER_SM,
            READ_SUM_THREADS,
        );
        // SAFETY: matches `read_sum(const int4*, size_t, unsigned*)`; the
        // kernel reads `words` 16-byte words of `data` and writes `out[0]`.
        unsafe { self.read_sum.launch(config, stream, &mut args) }
    }
}

/// A kernel argument: the address of a value of the parameter's type.
pub(crate) fn arg<T>(value: &T) -> *mut c_void {
    (value as *const T).cast_mut().cast()
}

/// Queues `kernel`, whose only parameter is a struct laid out as `P`.
///
/// # Safety
///
/// `P` must be `#[repr(C)]` with the layout of the kernel's parameter, and
/// every device address in `params` must be valid for all accesses the
/// kernel makes with this configuration.
pub(crate) unsafe fn launch_struct<P>(
    kernel: &Function,
    config: LaunchConfig,
    stream: &Stream,
    params: &P,
) -> Result<()> {
    // SAFETY: guaranteed by the caller.
    unsafe { kernel.launch(config, stream, &mut [arg(params)]) }
}
