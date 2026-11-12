//! Vulkan backend for AMD, Intel and NVIDIA GPUs.
//!
//! The Vulkan loader is opened at runtime, so this crate builds and links
//! on systems without Vulkan; [`Instance::new`] then fails with
//! [`Error::LoaderNotFound`]. Kernels are written in WGSL and compiled to
//! SPIR-V by naga at build time, so no Vulkan SDK is needed either.
//!
//! The kernels need Vulkan 1.3 with subgroup arithmetic, subgroups of 32,
//! packed int8 dot products and push descriptors, which current drivers for
//! all three vendors provide; [`DeviceInfo::missing`] says what a device
//! lacks. Integrated GPUs whose device-local heap is small keep buffers in
//! system memory instead.
//!
//! The decode-path GEMV kernels compute `y = W x` for one f32 vector. Float
//! weights read `x` as f32; quantized weights read an int8 copy of `x`, in
//! blocks of 32 with one scale each, made by [`GemvInput::upload`], and use
//! integer dot products.
//!
//! ```no_run
//! # fn main() -> kinetic_vulkan::Result<()> {
//! use kinetic_vulkan::{Commands, Device, DeviceBuffer, DeviceMatrix, GemvInput, Instance, Kernels};
//! # let (weights, x): (kinetic_quant::Matrix, Vec<f32>) = unimplemented!();
//! let physical = Instance::new()?.physical_devices()?.remove(0);
//! let device = Device::new(&physical)?;
//! let kernels = Kernels::load(&device)?;
//! let w = DeviceMatrix::upload(&device, &weights)?;
//! let mut input = GemvInput::new(&device, w.cols())?;
//! let y = DeviceBuffer::new(&device, w.rows())?;
//! let mut commands = Commands::new(&device)?;
//! input.upload(&kernels, &x, &mut commands)?;
//! kernels.gemv(&w, &input, &y, &mut commands)?;
//! commands.submit()?;
//! let y = y.to_vec()?;
//! # Ok(()) }
//! ```

mod argmax;
mod attention;
mod batch;
mod commands;
mod delta_net;
mod device;
mod error;
mod ffn;
mod gemv;
mod instance;
mod kernels;
mod layout;
mod memory;
mod norm;
mod physical;
mod pipeline;
mod short_conv;

pub use attention::{AttentionGate, AttentionShape, KvCache, QkvConsts};
pub use batch::{Batch, BATCH_HEADER};
pub use commands::{Commands, Graph, Timestamp, Timings};
pub use delta_net::{DeltaShape, DeltaState, DeltaWeights};
pub use device::Device;
pub use error::{Error, Result};
pub use gemv::{DeviceMatrix, GemvInput, Out, Rows};
pub use instance::Instance;
pub use kernels::Kernels;
pub use memory::{DeviceBuffer, DeviceCopy, HostBuffer};
pub use norm::Residual;
pub use physical::{DeviceInfo, DeviceKind, Features, PhysicalDevice};
pub use short_conv::ConvRing;
