use std::rc::Rc;

use crate::commands::Commands;
use crate::device::Device;
use crate::error::{Error, Result};
use crate::memory::DeviceBuffer;
use crate::pipeline::Kernel;

/// SPIR-V written by build.rs.
macro_rules! spirv {
    ($name:literal) => {
        include_bytes!(concat!(env!("OUT_DIR"), "/", $name, ".spv"))
    };
}

const READ_SUM_THREADS: u64 = 256;
/// 16-byte words each read_sum invocation reads, at least; more workgroups
/// would only add scheduling overhead.
const READ_SUM_WORDS_PER_THREAD: u64 = 16;
/// The dispatch size every device supports in each dimension.
pub(crate) const MAX_GROUPS: u32 = 65535;

/// The crate's kernels, built for one device.
pub struct Kernels {
    pub(crate) gemv_f32: Rc<Kernel>,
    pub(crate) gemv_f16: Rc<Kernel>,
    pub(crate) gemv_q8_0: Rc<Kernel>,
    pub(crate) gemv_q4_k: Rc<Kernel>,
    pub(crate) gemv_q5_k: Rc<Kernel>,
    pub(crate) gemv_q6_k: Rc<Kernel>,
    pub(crate) quantize_q8: Rc<Kernel>,
    pub(crate) norm: Rc<Kernel>,
    pub(crate) swiglu: Rc<Kernel>,
    pub(crate) argmax: Rc<Kernel>,
    pub(crate) rope: Rc<Kernel>,
    pub(crate) short_conv: Rc<Kernel>,
    pub(crate) delta_conv: Rc<Kernel>,
    pub(crate) delta_rule: Rc<Kernel>,
    pub(crate) gated_norm: Rc<Kernel>,
    pub(crate) attend_64: Rc<Kernel>,
    pub(crate) attend_128: Rc<Kernel>,
    pub(crate) attend_256: Rc<Kernel>,
    read_sum: Rc<Kernel>,
    /// The batch words of a pass of one token, for GEMVs outside a model.
    pub(crate) single: DeviceBuffer<u32>,
}

impl Kernels {
    /// Builds the pipelines for the kernels embedded in this crate.
    pub fn load(device: &Rc<Device>) -> Result<Kernels> {
        let gemv = |name, spirv| Kernel::new(device, name, spirv, 6, 5);
        let attend = |name, spirv| Kernel::new(device, name, spirv, 7, 9);
        Ok(Kernels {
            gemv_f32: gemv("gemv_f32", spirv!("gemv_f32"))?,
            gemv_f16: gemv("gemv_f16", spirv!("gemv_f16"))?,
            gemv_q8_0: gemv("gemv_q8_0", spirv!("gemv_q8_0"))?,
            gemv_q4_k: gemv("gemv_q4_k", spirv!("gemv_q4_k"))?,
            gemv_q5_k: gemv("gemv_q5_k", spirv!("gemv_q5_k"))?,
            gemv_q6_k: gemv("gemv_q6_k", spirv!("gemv_q6_k"))?,
            quantize_q8: Kernel::new(device, "quantize_q8", spirv!("quantize_q8"), 3, 1)?,
            norm: Kernel::new(device, "norm", spirv!("norm"), 8, 4)?,
            swiglu: Kernel::new(device, "swiglu", spirv!("swiglu"), 5, 1)?,
            argmax: Kernel::new(device, "argmax", spirv!("argmax"), 3, 1)?,
            rope: Kernel::new(device, "rope", spirv!("rope"), 5, 13)?,
            short_conv: Kernel::new(device, "short_conv", spirv!("short_conv"), 7, 3)?,
            delta_conv: Kernel::new(device, "delta_conv", spirv!("delta_conv"), 6, 7)?,
            delta_rule: Kernel::new(device, "delta_rule", spirv!("delta_rule"), 4, 7)?,
            gated_norm: Kernel::new(device, "gated_norm", spirv!("gated_norm"), 7, 5)?,
            attend_64: attend("attend_64", spirv!("attend_64"))?,
            attend_128: attend("attend_128", spirv!("attend_128"))?,
            attend_256: attend("attend_256", spirv!("attend_256"))?,
            read_sum: Kernel::new(device, "read_sum", spirv!("read_sum"), 2, 1)?,
            single: DeviceBuffer::from_slice(device, &[1, 0, 0, 1])?,
        })
    }

    /// Reads all of `data` once and adds its sum as 32-bit words to `out[0]`.
    ///
    /// The sum is meaningless; the kernel's throughput is the achievable
    /// read bandwidth of device memory, the ceiling for memory-bound kernels.
    /// `data.len()` must be a multiple of 16.
    pub fn read_sum(
        &self,
        data: &DeviceBuffer<u8>,
        out: &DeviceBuffer<u32>,
        commands: &mut Commands,
    ) -> Result<()> {
        if !data.len().is_multiple_of(16) || out.is_empty() {
            return Err(Error::Shape(format!(
                "read_sum needs a multiple of 16 bytes and one output, got {} and {}",
                data.len(),
                out.len()
            )));
        }
        let words = (data.len() / 16) as u64;
        let groups = words
            .div_ceil(READ_SUM_THREADS * READ_SUM_WORDS_PER_THREAD)
            .clamp(1, MAX_GROUPS.into()) as u32;
        // SAFETY: matches read_sum.wgsl: `data` and `out` at bindings 0 and
        // 1 and the word count, which fits in 32 bits because buffers are
        // capped at the device's storage buffer range.
        unsafe {
            commands.dispatch(
                &self.read_sum,
                &[data.allocation(), out.allocation()],
                &[words as u32],
                [groups, 1, 1],
            )
        };
        Ok(())
    }
}
