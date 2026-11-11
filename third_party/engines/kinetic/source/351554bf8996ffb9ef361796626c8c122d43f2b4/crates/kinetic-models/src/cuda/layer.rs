use kinetic_cuda::{
    AddNorm, Batch, ConvState, DeltaState, DeviceBuffer, Flow, GemvInput, KvCache, RmsNorm,
    SsmState,
};

use super::attention::CudaAttention;
use super::delta_net::CudaDeltaNet;
use super::experts::{CudaExperts, ExpertWork, Offload};
use super::ffn::CudaFfn;
use super::mamba2::CudaMamba2;
use super::per_layer::CudaLayerInput;
use super::scratch::{Needs, Scratch};
use super::short_conv::CudaShortConv;
use super::{cuda_error, Gpu};
use crate::blocks::Mixer;
use crate::model::Layer;
use crate::LoadError;

pub(super) enum CudaMixer {
    Attention(CudaAttention),
    DeltaNet(CudaDeltaNet),
    ShortConv(CudaShortConv),
    Mamba2(CudaMamba2),
    /// Mixers that read the same input, with their outputs summed.
    Parallel(Vec<CudaMixer>),
}

pub(super) enum LayerState {
    Attention(KvCache),
    DeltaNet(DeltaState),
    ShortConv(ConvState),
    Mamba2(SsmState),
    Parallel(Vec<LayerState>),
}

impl LayerState {
    pub fn size_bytes(&self) -> usize {
        match self {
            LayerState::Attention(c) => c.size_bytes(),
            LayerState::DeltaNet(s) => s.size_bytes(),
            LayerState::ShortConv(s) => s.size_bytes(),
            LayerState::Mamba2(s) => s.size_bytes(),
            LayerState::Parallel(s) => s.iter().map(LayerState::size_bytes).sum(),
        }
    }
}

impl CudaMixer {
    fn upload(gpu: &Gpu, m: &Mixer) -> Result<CudaMixer, LoadError> {
        Ok(match m {
            Mixer::Attention(a) => CudaMixer::Attention(CudaAttention::upload(gpu, a)?),
            Mixer::DeltaNet(d) => CudaMixer::DeltaNet(CudaDeltaNet::upload(gpu, d)?),
            Mixer::ShortConv(s) => CudaMixer::ShortConv(CudaShortConv::upload(gpu, s)?),
            Mixer::Mamba2(m) => CudaMixer::Mamba2(CudaMamba2::upload(gpu, m)?),
            Mixer::Parallel(ms) => CudaMixer::Parallel(
                ms.iter()
                    .map(|m| CudaMixer::upload(gpu, m))
                    .collect::<Result<_, _>>()?,
            ),
        })
    }

    fn size_bytes(&self) -> usize {
        match self {
            CudaMixer::Attention(a) => a.size_bytes(),
            CudaMixer::DeltaNet(d) => d.size_bytes(),
            CudaMixer::ShortConv(s) => s.size_bytes(),
            CudaMixer::Mamba2(m) => m.size_bytes(),
            CudaMixer::Parallel(ms) => ms.iter().map(CudaMixer::size_bytes).sum(),
        }
    }

    fn new_state(
        &self,
        gpu: &Gpu,
        capacity: usize,
        rows: usize,
    ) -> kinetic_cuda::Result<LayerState> {
        Ok(match self {
            CudaMixer::Attention(a) => LayerState::Attention(a.new_cache(gpu, capacity, rows)?),
            CudaMixer::DeltaNet(d) => LayerState::DeltaNet(d.new_state(gpu)?),
            CudaMixer::ShortConv(s) => LayerState::ShortConv(s.new_state(gpu)?),
            CudaMixer::Mamba2(m) => LayerState::Mamba2(m.new_state(gpu)?),
            CudaMixer::Parallel(ms) => LayerState::Parallel(
                ms.iter()
                    .map(|m| m.new_state(gpu, capacity, rows))
                    .collect::<kinetic_cuda::Result<_>>()?,
            ),
        })
    }

    /// What each mixer needs of the scratch for batches of up to `rows`.
    pub fn needs(&self, state: &LayerState, rows: usize) -> Vec<Needs> {
        match (self, state) {
            (CudaMixer::Attention(a), LayerState::Attention(c)) => vec![a.needs(c.slots())],
            (CudaMixer::DeltaNet(d), _) => vec![d.needs(rows)],
            (CudaMixer::ShortConv(c), _) => vec![c.needs()],
            (CudaMixer::Mamba2(m), _) => vec![m.needs(rows)],
            (CudaMixer::Parallel(ms), LayerState::Parallel(ss)) => ms
                .iter()
                .zip(ss)
                .flat_map(|(m, s)| m.needs(s, rows))
                .collect(),
            _ => unreachable!("state does not belong to this mixer"),
        }
    }

    /// Whether this runs mixers side by side, whose outputs need a sum.
    pub fn is_parallel(&self) -> bool {
        matches!(self, CudaMixer::Parallel(_))
    }

    /// Reads `s.h` and leaves the output in `s.y`.
    fn forward(
        &self,
        gpu: &Gpu,
        s: &mut Scratch,
        state: &mut LayerState,
        flow: Flow,
        batch: &Batch,
    ) -> kinetic_cuda::Result<()> {
        match (self, state) {
            (CudaMixer::Attention(a), LayerState::Attention(c)) => a.forward(gpu, s, c, batch),
            (CudaMixer::DeltaNet(d), LayerState::DeltaNet(st)) => {
                d.forward(gpu, s, st, flow, batch)
            }
            (CudaMixer::ShortConv(c), LayerState::ShortConv(st)) => c.forward(gpu, s, st, batch),
            (CudaMixer::Mamba2(m), LayerState::Mamba2(st)) => m.forward(gpu, s, st, flow, batch),
            (CudaMixer::Parallel(ms), LayerState::Parallel(ss)) => {
                let len = batch.len() * s.h.width();
                for (i, (m, st)) in ms.iter().zip(ss).enumerate() {
                    m.forward(gpu, s, st, flow, batch)?;
                    if i > 0 {
                        gpu.kernels.add(&mut s.y, &s.sum, len, &gpu.stream)?;
                    }
                    if i + 1 < ms.len() {
                        std::mem::swap(&mut s.y, &mut s.sum);
                    }
                }
                Ok(())
            }
            _ => unreachable!("state does not belong to this mixer"),
        }
    }

    /// The values per token of each projection a mixer leaves in
    /// `s.proj`, and of its output projection's input; `None` for parallel
    /// mixers, which run only whole.
    pub fn widths(&self) -> Option<([usize; 4], usize)> {
        let needs = match self {
            CudaMixer::Attention(a) => a.needs(0),
            CudaMixer::DeltaNet(d) => d.needs(1),
            CudaMixer::ShortConv(c) => c.needs(),
            CudaMixer::Mamba2(m) => m.needs(1),
            CudaMixer::Parallel(_) => return None,
        };
        Some((needs.proj, needs.width))
    }

    /// Queues the projections of the first `n` rows of `s.h`.
    pub fn project(&self, gpu: &Gpu, s: &mut Scratch, n: usize) -> kinetic_cuda::Result<()> {
        match self {
            CudaMixer::Attention(a) => a.project(gpu, s, n),
            CudaMixer::DeltaNet(d) => d.project(gpu, s, n),
            CudaMixer::ShortConv(c) => c.project(gpu, s, n),
            CudaMixer::Mamba2(m) => m.project(gpu, s, n),
            CudaMixer::Parallel(_) => unreachable!("parallel mixers run whole"),
        }
    }

    /// Queues the rest of the mixer on `batch`, projected already, up to
    /// the input of its output projection.
    pub fn mix(
        &self,
        gpu: &Gpu,
        s: &mut Scratch,
        state: &mut LayerState,
        flow: Flow,
        batch: &Batch,
    ) -> kinetic_cuda::Result<()> {
        match (self, state) {
            (CudaMixer::Attention(a), LayerState::Attention(c)) => a.mix(gpu, s, c, batch),
            (CudaMixer::DeltaNet(d), LayerState::DeltaNet(st)) => d.mix(gpu, s, st, flow, batch),
            (CudaMixer::ShortConv(c), LayerState::ShortConv(st)) => c.mix(gpu, s, st, batch),
            (CudaMixer::Mamba2(m), LayerState::Mamba2(st)) => m.mix(gpu, s, st, flow, batch),
            _ => unreachable!("state does not belong to this mixer, or it runs whole"),
        }
    }

    /// Queues the output projection of the first `n` rows into `s.y`.
    pub fn output(&self, gpu: &Gpu, s: &mut Scratch, n: usize) -> kinetic_cuda::Result<()> {
        match self {
            CudaMixer::Attention(a) => a.output(gpu, s, n),
            CudaMixer::DeltaNet(d) => d.output(gpu, s, n),
            CudaMixer::ShortConv(c) => c.output(gpu, s, n),
            CudaMixer::Mamba2(m) => m.output(gpu, s, n),
            CudaMixer::Parallel(_) => unreachable!("parallel mixers run whole"),
        }
    }

    fn replay(&self, gpu: &Gpu, state: &mut LayerState, keep: usize) -> kinetic_cuda::Result<()> {
        match (self, state) {
            (CudaMixer::DeltaNet(d), LayerState::DeltaNet(s)) => d.replay(gpu, s, keep),
            (CudaMixer::Mamba2(m), LayerState::Mamba2(s)) => m.replay(gpu, s, keep),
            (CudaMixer::Parallel(ms), LayerState::Parallel(ss)) => ms
                .iter()
                .zip(ss)
                .try_for_each(|(m, s)| m.replay(gpu, s, keep)),
            _ => Ok(()),
        }
    }
}

/// Before layer `to` runs on `batch`: copies into its cache the keys and
/// values layer `from` stored for the batch.
// shortcut: each borrowing layer keeps a full copy of the lender's cache, as
// the host states do; attending over the lender's own would save the memory
pub(super) fn copy_lent(
    gpu: &Gpu,
    states: &mut [LayerState],
    from: usize,
    to: usize,
    batch: &Batch,
) -> kinetic_cuda::Result<()> {
    let (done, rest) = states.split_at_mut(to);
    match (&done[from], &mut rest[0]) {
        (LayerState::Attention(src), LayerState::Attention(dst)) => {
            gpu.kernels.copy_kv(src, dst, batch, &gpu.stream)
        }
        _ => unreachable!("keys are lent between attention layers"),
    }
}

/// A decoder layer on the device; see [`Layer`]. In a mixture-of-experts
/// layer `ffn` is the shared expert.
pub(super) struct CudaLayer {
    pub mixer_norm: Option<DeviceBuffer<f32>>,
    pub mixer: CudaMixer,
    mixer_out_norm: Option<DeviceBuffer<f32>>,
    ffn_norm: Option<DeviceBuffer<f32>>,
    ffn: Option<CudaFfn>,
    pub experts: Option<CudaExperts>,
    ffn_out_norm: Option<DeviceBuffer<f32>>,
    residual_scale: f32,
    eps: f32,
    /// The layer whose keys and values this one attends over.
    pub kv_source: Option<usize>,
    pub input: Option<CudaLayerInput>,
}

/// What a layer's routed experts run with: its index among the layers with
/// experts, the state's expert buffers and the model's expert cache.
pub(super) struct Routed<'a, 'm> {
    pub layer: usize,
    pub work: &'a mut ExpertWork,
    pub offload: &'a mut Offload<'m>,
}

impl CudaLayer {
    /// Uploads `l`; its routed experts, if any, come as `experts`.
    pub fn upload(
        gpu: &Gpu,
        l: &Layer,
        experts: Option<CudaExperts>,
        eps: f32,
    ) -> Result<CudaLayer, LoadError> {
        let vector = |v: &[f32]| gpu.vector(v).map_err(cuda_error);
        let optional = |v: &Option<Vec<f32>>| v.as_deref().map(vector).transpose();
        Ok(CudaLayer {
            mixer_norm: optional(&l.mixer_norm)?,
            mixer: CudaMixer::upload(gpu, &l.mixer)?,
            mixer_out_norm: optional(&l.mixer_out_norm)?,
            ffn_norm: optional(&l.ffn_norm)?,
            ffn: l
                .ffn
                .as_ref()
                .map(|f| CudaFfn::upload(gpu, f))
                .transpose()?,
            experts,
            ffn_out_norm: optional(&l.ffn_out_norm)?,
            residual_scale: l.residual_scale.unwrap_or(1.0),
            eps,
            kv_source: l.mixer.kv_source(),
            input: None,
        })
    }

    pub fn size_bytes(&self) -> usize {
        self.mixer.size_bytes()
            + self.input.as_ref().map_or(0, CudaLayerInput::size_bytes)
            + self.ffn.as_ref().map_or(0, CudaFfn::size_bytes)
            + self.experts.as_ref().map_or(0, CudaExperts::size_bytes)
    }

    pub fn ffn_needs(&self) -> Needs {
        self.ffn.as_ref().map(CudaFfn::needs).unwrap_or_default()
    }

    /// A fresh state for a sequence of up to `capacity` tokens run in
    /// batches of up to `rows`, which keeps room for `MAX_BATCH` tokens
    /// between a checkpoint and its rollback.
    pub fn new_state(
        &self,
        gpu: &Gpu,
        capacity: usize,
        rows: usize,
    ) -> kinetic_cuda::Result<LayerState> {
        self.mixer.new_state(gpu, capacity, rows)
    }

    /// Queues `h = x` after this layer's input norm, for the first `n` rows.
    pub fn input(
        &self,
        gpu: &Gpu,
        x: &DeviceBuffer<f32>,
        h: &mut GemvInput,
        n: usize,
    ) -> kinetic_cuda::Result<()> {
        let (k, stream) = (&gpu.kernels, &gpu.stream);
        match &self.mixer_norm {
            Some(weight) => {
                let norm = RmsNorm {
                    weight,
                    eps: self.eps,
                };
                k.rms_norm(x, norm, h, 0, n, stream)
            }
            None => k.input_rows(x, h, n, stream),
        }
    }

    /// Runs the layer on the batch, whose input `s.h` holds the stream
    /// `s.x` after this layer's input norm. Leaves `s.h` holding `x` after
    /// the layer passed through `next`, the following layer's input norm or
    /// the output norm.
    #[allow(clippy::too_many_arguments)]
    pub fn forward(
        &self,
        gpu: &Gpu,
        s: &mut Scratch,
        state: &mut LayerState,
        flow: Flow,
        batch: &Batch,
        next: Option<&DeviceBuffer<f32>>,
        routed: Option<Routed>,
    ) -> kinetic_cuda::Result<()> {
        let n = batch.len();
        self.front(gpu, s, state, flow, batch)?;
        if let (Some(experts), Some(r)) = (&self.experts, routed) {
            experts.score(gpu, &s.h, n, &mut r.work.gates)?;
            experts.mix(r.layer, gpu, s.h.values(), &mut s.y, r.work, r.offload, n)?;
        }
        self.back(gpu, s, n, next)
    }

    /// Runs the mixer and the (shared) feed-forward: leaves the feed-forward
    /// input in `s.h` and its output in `s.y`.
    pub fn front(
        &self,
        gpu: &Gpu,
        s: &mut Scratch,
        state: &mut LayerState,
        flow: Flow,
        batch: &Batch,
    ) -> kinetic_cuda::Result<()> {
        self.mixer.forward(gpu, s, state, flow, batch)?;
        self.feed(gpu, s, batch.len())
    }

    /// Adds the mixer output `s.y` of `n` rows to the stream and runs the
    /// (shared) feed-forward: leaves its input in `s.h` and its output in
    /// `s.y`.
    pub fn feed(&self, gpu: &Gpu, s: &mut Scratch, n: usize) -> kinetic_cuda::Result<()> {
        let (k, stream) = (&gpu.kernels, &gpu.stream);
        let mixed = AddNorm {
            post: self.mixer_out_norm.as_ref(),
            scale: self.residual_scale,
            out_scale: 1.0,
            next: self.ffn_norm.as_ref(),
            eps: self.eps,
        };
        k.add_norm(&mut s.x, &s.y, mixed, &mut s.h, n, stream)?;
        match &self.ffn {
            Some(ffn) => ffn.forward(gpu, s, n),
            // The routed experts then mix into zeros.
            None => Ok(()),
        }
    }

    /// Adds the feed-forward output `s.y` to the stream `s.x` and leaves it
    /// normalized by `next` in `s.h`.
    pub fn back(
        &self,
        gpu: &Gpu,
        s: &mut Scratch,
        n: usize,
        next: Option<&DeviceBuffer<f32>>,
    ) -> kinetic_cuda::Result<()> {
        let fed = AddNorm {
            post: self.ffn_out_norm.as_ref(),
            scale: self.residual_scale,
            out_scale: 1.0,
            next: if self.input.is_some() { None } else { next },
            eps: self.eps,
        };
        gpu.kernels
            .add_norm(&mut s.x, &s.y, fed, &mut s.h, n, &gpu.stream)?;
        match &self.input {
            Some(input) => input.queue(gpu, s, n, self.eps, next),
            None => Ok(()),
        }
    }

    /// Advances the state saved at the checkpoint by the first `keep`
    /// tokens recorded since; only recurrent state needs it.
    pub fn replay(
        &self,
        gpu: &Gpu,
        state: &mut LayerState,
        keep: usize,
    ) -> kinetic_cuda::Result<()> {
        self.mixer.replay(gpu, state, keep)
    }
}
