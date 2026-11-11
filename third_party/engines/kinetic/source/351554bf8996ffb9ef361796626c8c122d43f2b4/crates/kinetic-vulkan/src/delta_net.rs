use std::rc::Rc;

use crate::batch::Batch;
use crate::commands::Commands;
use crate::device::Device;
use crate::error::{Error, Result};
use crate::gemv::GemvInput;
use crate::kernels::Kernels;
use crate::memory::{Allocation, DeviceBuffer};
use crate::short_conv::ConvRing;

/// The key head size the recurrence kernel handles, four values per lane.
const HEAD_K_DIM: usize = 128;

/// The shape of a gated delta-rule layer.
#[derive(Clone, Copy, Debug)]
pub struct DeltaShape {
    pub n_k_heads: usize,
    pub n_v_heads: usize,
    /// 128.
    pub head_k_dim: usize,
    /// A multiple of 32.
    pub head_v_dim: usize,
    pub conv_taps: usize,
    pub eps: f32,
}

impl DeltaShape {
    pub fn key_dim(&self) -> usize {
        self.n_k_heads * self.head_k_dim
    }

    pub fn value_dim(&self) -> usize {
        self.n_v_heads * self.head_v_dim
    }

    /// Convolution channels: queries, keys, then values.
    pub fn channels(&self) -> usize {
        2 * self.key_dim() + self.value_dim()
    }

    /// Values per token row of the projections the layer reads: the
    /// convolution inputs, the output gates, then one beta and one alpha
    /// per value head.
    pub fn proj_len(&self) -> usize {
        self.channels() + self.value_dim() + 2 * self.n_v_heads
    }

    fn journal_len(&self) -> usize {
        self.channels() + 2 * self.n_v_heads
    }

    fn check(&self) -> Result<()> {
        let fits = self.head_k_dim == HEAD_K_DIM
            && self.head_v_dim.is_multiple_of(32)
            && self.n_k_heads > 0
            && self.n_v_heads > 0
            && self.conv_taps >= 2;
        if fits {
            Ok(())
        } else {
            Err(Error::Shape(format!("delta-rule layer of shape {self:?}")))
        }
    }
}

/// The recurrent state of a delta-rule layer: one matrix per value head,
/// the convolution's recent inputs, and a journal of each token's
/// convolved inputs, decays and step sizes since the last checkpoint, from
/// which a rollback replays the tokens it keeps.
pub struct DeltaState {
    state: DeviceBuffer<f32>,
    ring: ConvRing,
    journal: DeviceBuffer<f32>,
    rows: usize,
}

impl DeltaState {
    /// A state for passes of up to `rows` tokens, which is also the most
    /// that may run between a checkpoint and its rollback.
    pub fn new(device: &Rc<Device>, shape: &DeltaShape, rows: usize) -> Result<DeltaState> {
        shape.check()?;
        let state = shape.n_v_heads * shape.head_v_dim * shape.head_k_dim;
        Ok(DeltaState {
            state: DeviceBuffer::new(device, state)?,
            ring: ConvRing::new(device, shape.channels(), shape.conv_taps, rows)?,
            journal: DeviceBuffer::new(device, rows * shape.journal_len())?,
            rows,
        })
    }

    /// The per-head matrices, `head_v_dim` rows of `head_k_dim` each.
    pub fn save(&self) -> Result<Vec<f32>> {
        self.state.to_vec()
    }

    /// Writes the matrices as [`DeltaState::save`] gives them.
    pub fn load(&mut self, matrices: &[f32]) -> Result<()> {
        self.state.copy_from(matrices)
    }

    /// The convolution's recent inputs.
    pub fn ring(&self) -> &ConvRing {
        &self.ring
    }

    pub fn ring_mut(&mut self) -> &mut ConvRing {
        &mut self.ring
    }

    /// Empties the state for a new sequence.
    pub fn clear(&mut self) -> Result<()> {
        self.state.zero()
    }

    /// Device bytes held.
    pub fn size_bytes(&self) -> usize {
        4 * (self.state.len() + self.journal.len()) + self.ring.size_bytes()
    }

    fn check(&self, shape: &DeltaShape, batch: &Batch) -> Result<()> {
        self.ring.check(batch, shape.channels(), shape.conv_taps)?;
        let state = shape.n_v_heads * shape.head_v_dim * shape.head_k_dim;
        if self.state.len() == state && self.rows >= batch.rows() {
            Ok(())
        } else {
            Err(Error::Shape(format!(
                "delta-rule state for passes of {} rows",
                self.rows
            )))
        }
    }
}

/// The weights a delta-rule layer applies on the device besides its
/// projections: `taps` convolution weights per channel, the oldest input's
/// first; `dt_bias` then `a` per value head; and the output norm.
pub struct DeltaWeights<'a> {
    pub conv: &'a DeviceBuffer<f32>,
    pub heads: &'a DeviceBuffer<f32>,
    pub norm: &'a DeviceBuffer<f32>,
}

impl Kernels {
    /// Records a delta-rule layer for every token of the batch, from the
    /// projections in `proj`, laid out as [`DeltaShape::proj_len`] says.
    /// The recurrence output lands in `rec` and the gated, normalized
    /// output in `out`. Passes after a checkpoint leave the matrices as
    /// they were; see [`Batch::set`] and [`Kernels::delta_replay`].
    #[allow(clippy::too_many_arguments)]
    pub fn delta_net(
        &self,
        batch: &Batch,
        shape: &DeltaShape,
        proj: &DeviceBuffer<f32>,
        weights: &DeltaWeights,
        state: &DeltaState,
        rec: &DeviceBuffer<f32>,
        out: &GemvInput,
        commands: &mut Commands,
    ) -> Result<()> {
        shape.check()?;
        state.check(shape, batch)?;
        let rows = batch.rows();
        let (channels, vd, nv) = (shape.channels(), shape.value_dim(), shape.n_v_heads);
        let fits = proj.len() >= rows * shape.proj_len()
            && rec.len() >= rows * vd
            && weights.conv.len() == channels * shape.conv_taps
            && weights.heads.len() == 2 * nv
            && weights.norm.len() == shape.head_v_dim
            && out.width() == vd
            && out.rows() >= rows;
        if !fits {
            return Err(Error::Shape(format!(
                "delta-rule layer of {rows} rows of shape {shape:?}"
            )));
        }
        let b = batch.device().allocation();
        let [ox, oq, od] = out.outputs();
        // SAFETY: delta_conv.wgsl takes the batch, proj, conv weights, head
        // constants, ring and journal at bindings 0..5; delta_rule.wgsl the
        // batch, journal, matrices and `rec` at 0..3; gated_norm.wgsl the
        // batch, `rec`, proj, norm and the three output buffers at 0..6;
        // each then its shape. The sizes were checked above: token rows
        // below the batch's rows, ring and journal slots below theirs, and
        // the batch keeps replayed positions within the journal. Invocations
        // past the pass's tokens return early.
        unsafe {
            commands.dispatch(
                &self.delta_conv,
                &[
                    b,
                    proj.allocation(),
                    weights.conv.allocation(),
                    weights.heads.allocation(),
                    state.ring.data().allocation(),
                    state.journal.allocation(),
                ],
                &[
                    channels as u32,
                    shape.proj_len() as u32,
                    vd as u32,
                    nv as u32,
                    shape.conv_taps as u32,
                    state.ring.slots() as u32,
                    state.rows as u32,
                ],
                [(channels + nv).div_ceil(256) as u32, rows as u32, 1],
            );
            self.record_rule(shape, state, rec, false, b, commands);
            commands.dispatch(
                &self.gated_norm,
                &[
                    b,
                    rec.allocation(),
                    proj.allocation(),
                    weights.norm.allocation(),
                    ox,
                    oq,
                    od,
                ],
                &[
                    shape.head_v_dim as u32,
                    nv as u32,
                    shape.proj_len() as u32,
                    channels as u32,
                    shape.eps.to_bits(),
                ],
                [nv as u32, rows as u32, 1],
            );
        }
        Ok(())
    }

    /// Records the replay that makes the matrices keep the tokens a
    /// rollback keeps; see [`Batch::set_replay`]. `rec` is any buffer of
    /// the layer's output size, which the replay does not write.
    pub fn delta_replay(
        &self,
        batch: &Batch,
        shape: &DeltaShape,
        state: &DeltaState,
        rec: &DeviceBuffer<f32>,
        commands: &mut Commands,
    ) -> Result<()> {
        shape.check()?;
        state.check(shape, batch)?;
        let b = batch.device().allocation();
        // SAFETY: as in `delta_net`; a replay writes only the matrices.
        unsafe { self.record_rule(shape, state, rec, true, b, commands) };
        Ok(())
    }

    /// # Safety
    ///
    /// The shapes must have been checked as `delta_net` checks them.
    unsafe fn record_rule(
        &self,
        shape: &DeltaShape,
        state: &DeltaState,
        rec: &DeviceBuffer<f32>,
        replay: bool,
        batch: &Rc<Allocation>,
        commands: &mut Commands,
    ) {
        let rows = shape.value_dim();
        // SAFETY: matches delta_rule.wgsl; the caller checked the sizes.
        unsafe {
            commands.dispatch(
                &self.delta_rule,
                &[
                    batch,
                    state.journal.allocation(),
                    state.state.allocation(),
                    rec.allocation(),
                ],
                &[
                    shape.channels() as u32,
                    shape.n_k_heads as u32,
                    shape.n_v_heads as u32,
                    shape.head_v_dim as u32,
                    state.rows as u32,
                    shape.eps.to_bits(),
                    replay as u32,
                ],
                [rows.div_ceil(4) as u32, 1, 1],
            )
        };
    }
}
