use std::rc::Rc;

use crate::batch::Batch;
use crate::context::Context;
use crate::delta_net::{check_rows, HostState};
use crate::error::{Error, Result};
use crate::gemv::{Act, GemvInput, MAX_BATCH};
use crate::kernels::{launch_struct, Kernels};
use crate::memory::DeviceBuffer;
use crate::module::LaunchConfig;
use crate::stream::Stream;

const THREADS: u32 = 128;

/// The recent gated inputs of a short convolution, a ring indexed by position.
pub struct ConvState {
    ring: DeviceBuffer<f32>,
    channels: usize,
    taps: usize,
    ring_len: usize,
}

impl ConvState {
    /// A zero window for `channels` channels of `taps` taps. Rolling back
    /// only rewinds the position, so the ring keeps room for `max_tokens`
    /// tokens run between a checkpoint and its rollback.
    pub fn new(
        ctx: &Rc<Context>,
        channels: usize,
        taps: usize,
        max_tokens: usize,
    ) -> Result<ConvState> {
        if taps == 0 || !channels.is_multiple_of(32) {
            return Err(Error::Shape(format!(
                "short convolution of {channels} channels and {taps} taps"
            )));
        }
        let ring_len = taps - 1 + max_tokens;
        let mut ring = DeviceBuffer::new(ctx, ring_len * channels)?;
        ring.zero()?;
        Ok(ConvState {
            ring,
            channels,
            taps,
            ring_len,
        })
    }

    /// Device bytes held.
    pub fn size_bytes(&self) -> usize {
        4 * self.ring.len()
    }

    /// Queues zeroing the ring, as in a new sequence.
    pub fn clear(&mut self, stream: &Stream) -> Result<()> {
        self.ring.zero_prefix(self.ring.len(), stream)
    }

    /// Rows of the convolution ring; see [`HostState`].
    pub fn ring_rows(&self) -> usize {
        self.ring_len
    }

    /// Copies the ring to the host.
    pub fn save(&self) -> Result<HostState> {
        Ok(HostState {
            ring: self.ring.to_vec()?,
            ring_rows: self.ring_len,
            state: Vec::new(),
        })
    }

    /// Replaces the ring with a copy from [`ConvState::save`].
    pub fn load(&mut self, host: &HostState) -> Result<()> {
        check_rows(host, self.ring_len)?;
        self.ring.copy_from(&host.ring)
    }
}

#[repr(C)]
struct ShortConvArgs {
    batch: u64,
    bcx: u64,
    conv: u64,
    ring: u64,
    out: Act,
    n: u32,
    channels: u32,
    taps: u32,
    ring_len: u32,
}

impl Kernels {
    /// Queues `out = c * conv(b * x)` for every token of `batch`, where
    /// `bcx` holds b, c and x of each token and `conv` the taps of each
    /// channel, oldest first. Batches of more than [`MAX_BATCH`] tokens run
    /// a thread per token and channel, with the same arithmetic.
    pub fn short_conv(
        &self,
        conv: &DeviceBuffer<f32>,
        bcx: &DeviceBuffer<f32>,
        state: &mut ConvState,
        out: &mut GemvInput,
        batch: &Batch,
        stream: &Stream,
    ) -> Result<()> {
        let (n, d) = (batch.len(), state.channels);
        if conv.len() != d * state.taps || out.width() != d {
            return Err(Error::Shape(format!(
                "short convolution of {d} channels with {} weights into inputs of {}",
                conv.len(),
                out.width()
            )));
        }
        bcx.check_holds(n * 3 * d, "short convolution input")?;
        out.check_rows(n)?;
        let args = ShortConvArgs {
            batch: batch.device_ptr(),
            bcx: bcx.device_ptr(),
            conv: conv.device_ptr(),
            ring: state.ring.device_ptr(),
            out: out.act(),
            n: n as u32,
            channels: d as u32,
            taps: state.taps as u32,
            ring_len: state.ring_len as u32,
        };
        let blocks = (d as u32).div_ceil(THREADS);
        let config = LaunchConfig::linear(blocks, THREADS);
        // SAFETY: matches `ShortConvArgs`; buffers hold what `n` tokens of
        // `d` channels touch, as checked, and ring rows wrap below `ring_len`.
        unsafe {
            if n <= MAX_BATCH {
                return launch_struct(&self.short_conv_q8, config, stream, &args);
            }
            let batch = LaunchConfig {
                grid: [blocks, n as u32, 1],
                ..config
            };
            launch_struct(&self.short_conv_batch, batch, stream, &args)?;
            launch_struct(&self.short_conv_ring_store, config, stream, &args)
        }
    }
}
