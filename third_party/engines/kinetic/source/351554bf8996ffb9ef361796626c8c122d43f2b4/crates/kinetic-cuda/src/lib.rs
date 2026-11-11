//! CUDA backend.
//!
//! The driver is loaded at runtime (`nvcuda.dll` or `libcuda.so.1`), so this
//! crate builds and links on machines without CUDA; every entry point then
//! returns an [`Error`] instead. Kernels are compiled by nvcc at build time
//! into one fatbin with machine code for sm_75 through sm_120 and PTX for
//! newer GPUs. Built without nvcc, [`Kernels::load`] fails with
//! [`Error::KernelsNotBuilt`].
//!
//! The GEMV kernels compute `y = W x` for up to [`MAX_BATCH`] f32 vectors,
//! reading each weight once. Float weights read `x` as f32; quantized
//! weights read an int8 copy of `x`, in blocks of 32 with one scale each,
//! made by [`GemvInput::upload`] or written directly by the kernel that
//! produces `x`, and use `dp4a` integer dot products. On devices with int8
//! tensor cores (sm_80 and up), larger K-quant batches use `mma` instead;
//! both kinds add up exactly the same terms in the same order, so a vector's
//! result never depends on the batch it shares a launch with.
//!
//! The model kernels (norms, attention, delta-rule, short-convolution and
//! Mamba-2 mixers, the gated feed-forward, embedding and argmax) read the position
//! and token ids of the running [`Batch`] from device memory, so a decode
//! step recorded into a [`Graph`] replays for every token.
//!
//! ```no_run
//! # fn main() -> kinetic_cuda::Result<()> {
//! use kinetic_cuda::{Context, Device, DeviceBuffer, DeviceMatrix, GemvInput, Kernels, Stream};
//! # let (weights, x): (kinetic_quant::Matrix, Vec<f32>) = unimplemented!();
//! let ctx = Context::new(Device::get(0)?)?;
//! let kernels = Kernels::load(&ctx)?;
//! let stream = Stream::new(&ctx)?;
//! let w = DeviceMatrix::upload(&ctx, &weights)?;
//! let mut input = GemvInput::new(&ctx, w.cols())?;
//! let mut y = DeviceBuffer::new(&ctx, w.rows())?;
//! input.upload(&kernels, &x, &stream)?;
//! kernels.gemv(&w, &input, &mut y, &stream)?;
//! let y = y.to_vec()?;
//! # Ok(()) }
//! ```

mod argmax;
mod attention;
mod batch;
mod context;
mod delta_net;
mod device;
mod driver;
mod error;
mod ffn;
mod fold;
mod gemm;
mod gemv;
mod graph;
mod kernels;
mod layout;
mod memory;
mod module;
mod moe;
mod norm;
mod pinned;
mod short_conv;
mod ssm;
mod stream;
mod vision;

pub use argmax::Argmax;
pub use attention::{AttentionIo, AttentionParams, AttentionShape, KvCache, KvType};
pub use batch::Batch;
pub use context::Context;
pub use delta_net::{DeltaIo, DeltaParams, DeltaShape, DeltaState, Flow, HostState};
pub use device::{driver_version, Device, DeviceInfo};
pub use error::{Error, Result};
pub use fold::ValueHeads;
pub use gemv::{DeviceMatrix, GemvInput, MAX_BATCH};
pub use graph::Graph;
pub use kernels::Kernels;
pub use memory::{DeviceBuffer, DeviceCopy};
pub use module::{Function, LaunchConfig, Module};
pub use moe::{
    ExpertArena, ExpertGroup, ExpertMix, ExpertProduct, ExpertTables, GateLogits, Q8kRows, Routing,
    ASSIGN_MAX_PICKS, EXPERT_GROUP, EXPERT_TYPES, Q8K_BLOCK, ROUTE_MAX_EXPERTS,
};
pub use norm::{AddNorm, RmsNorm};
pub use pinned::PinnedBuffer;
pub use short_conv::ConvState;
pub use ssm::{SsmParams, SsmShape, SsmState};
pub use stream::{Event, Stream};
pub use vision::VisionKernels;
