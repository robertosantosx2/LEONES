use std::rc::Rc;

use crate::batch::Batch;
use crate::commands::Commands;
use crate::device::Device;
use crate::error::{Error, Result};
use crate::gemv::GemvInput;
use crate::kernels::Kernels;
use crate::memory::DeviceBuffer;

/// The recent inputs of a causal convolution: position `p` in slot
/// `p % slots` of a ring with room for `taps - 1` positions and a pass
/// more, so neither a pass nor a rollback overwrites a position still read.
pub struct ConvRing {
    data: DeviceBuffer<f32>,
    channels: usize,
    taps: usize,
    rows: usize,
}

impl ConvRing {
    /// A ring for `channels` channels of `taps` taps run in passes of up
    /// to `rows` tokens.
    pub fn new(device: &Rc<Device>, channels: usize, taps: usize, rows: usize) -> Result<Self> {
        if taps < 2 {
            return Err(Error::Shape(format!("convolution of {taps} taps")));
        }
        Ok(ConvRing {
            data: DeviceBuffer::new(device, channels * (taps - 1 + rows))?,
            channels,
            taps,
            rows,
        })
    }

    pub fn channels(&self) -> usize {
        self.channels
    }

    pub fn taps(&self) -> usize {
        self.taps
    }

    pub fn slots(&self) -> usize {
        self.taps - 1 + self.rows
    }

    /// Every slot, `channels` values each.
    pub fn save(&self) -> Result<Vec<f32>> {
        self.data.to_vec()
    }

    /// Writes every slot, as [`ConvRing::save`] gives them.
    pub fn load(&mut self, slots: &[f32]) -> Result<()> {
        self.data.copy_from(slots)
    }

    pub(crate) fn data(&self) -> &DeviceBuffer<f32> {
        &self.data
    }

    /// Device bytes held.
    pub fn size_bytes(&self) -> usize {
        4 * self.data.len()
    }

    pub(crate) fn check(&self, batch: &Batch, channels: usize, taps: usize) -> Result<()> {
        if self.channels == channels && self.taps == taps && self.rows >= batch.rows() {
            Ok(())
        } else {
            Err(Error::Shape(format!(
                "ring of {} channels and {} taps for passes of {}",
                self.channels, self.taps, self.rows
            )))
        }
    }
}

impl Kernels {
    /// Records the gated short convolution of every token of the batch:
    /// a row of `bcx` holds the input gates, output gates and values,
    /// `out.width()` each; `weight` holds `taps` weights per channel, the
    /// oldest input's first.
    pub fn short_conv(
        &self,
        batch: &Batch,
        bcx: &DeviceBuffer<f32>,
        weight: &DeviceBuffer<f32>,
        ring: &ConvRing,
        out: &GemvInput,
        commands: &mut Commands,
    ) -> Result<()> {
        let (len, rows) = (out.width(), batch.rows());
        ring.check(batch, len, ring.taps)?;
        if bcx.len() < 3 * rows * len || weight.len() != len * ring.taps || out.rows() < rows {
            return Err(Error::Shape(format!(
                "short convolution of {rows} rows of {len}"
            )));
        }
        let [ox, oq, od] = out.outputs();
        // SAFETY: matches short_conv.wgsl: the batch, bcx, weights, ring and
        // the three output buffers at bindings 0..6, then length, taps and
        // slots. Every buffer holds the batch's rows and the ring its
        // slots, checked above; invocations past them return.
        unsafe {
            commands.dispatch(
                &self.short_conv,
                &[
                    batch.device().allocation(),
                    bcx.allocation(),
                    weight.allocation(),
                    ring.data.allocation(),
                    ox,
                    oq,
                    od,
                ],
                &[len as u32, ring.taps as u32, ring.slots() as u32],
                [len.div_ceil(256) as u32, rows as u32, 1],
            )
        };
        Ok(())
    }
}
