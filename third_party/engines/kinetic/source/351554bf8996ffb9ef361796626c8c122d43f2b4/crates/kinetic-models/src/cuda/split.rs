//! Models larger than the device: the last layers that fit run on the
//! device, the first ones on the host, exactly as the CPU path runs them.
//! A token's embedding goes through the host layers, and its hidden state
//! is copied over to the device for the rest, so only `n_embd` values per
//! token cross between them.

use kinetic_cuda::KvType;

use super::experts::DEVICE_RESERVE;
use super::layer::CudaLayer;
use super::scratch::Work;
use super::{cuda_error, CudaModel, Gpu};
use crate::blocks::MixerState;
use crate::{LoadError, Model};

/// Limits on what of a model goes to the device, and how it runs there.
/// The default puts as much there as fits and records decode steps.
#[derive(Clone, Copy, Debug, Default)]
pub struct Placement {
    /// Most layers on the device, as llama.cpp's `-ngl` counts them.
    pub gpu_layers: Option<usize>,
    /// Most device bytes the model may take, weights and one state.
    pub device_bytes: Option<usize>,
    /// Launch each kernel of a decode step on its own rather than replaying
    /// the recorded step: Torque off.
    pub eager: bool,
    /// How attention caches store keys and values; anything but f16 rounds
    /// them and so changes outputs.
    pub cache_k: KvType,
    pub cache_v: KvType,
}

/// Uploads the longest run of `model`'s last layers that fits in the device
/// beside one state of `context` positions in batches of `rows`, within
/// `placement`; `start` is the free device memory before the model took
/// any. Returns how many layers stay on the host and the device layers in
/// order.
pub(super) fn upload_layers(
    gpu: &Gpu,
    model: &Model,
    context: usize,
    rows: usize,
    vocab: usize,
    placement: Placement,
    start: usize,
) -> Result<(usize, Vec<CudaLayer>), LoadError> {
    let n = model.layers.len();
    let most = placement.gpu_layers.unwrap_or(n).min(n);
    let free = || gpu.ctx.memory_info().map(|(f, _)| f).map_err(cuda_error);
    let cap = placement.device_bytes.unwrap_or(usize::MAX);
    let mut layers = Vec::new();
    let mut largest = 0;
    for l in model.layers.iter().rev().take(most) {
        let before = free()?;
        if before < DEVICE_RESERVE + largest || start.saturating_sub(before) + largest > cap {
            break;
        }
        match CudaLayer::upload(gpu, l, None, model.eps) {
            Ok(layer) => layers.push(layer),
            // A failure past the first layer is the device running out.
            Err(_) if !layers.is_empty() => break,
            Err(e) => return Err(e),
        }
        largest = largest.max(before.saturating_sub(free()?));
    }
    layers.reverse();
    // Give up layers from the front until one state fits beside them.
    while !layers.is_empty() {
        let refs: Vec<&CudaLayer> = layers.iter().collect();
        let fits = match Work::new(
            gpu,
            &refs,
            model.n_embd,
            context,
            rows,
            vocab,
            0,
            model.folded,
        ) {
            Ok(work) => {
                let used = start.saturating_sub(free()?);
                drop(work);
                used <= cap && free()? >= DEVICE_RESERVE
            }
            Err(_) => false,
        };
        if fits {
            break;
        }
        layers.remove(0);
    }
    if layers.is_empty() && n > 0 {
        return Err(LoadError("no layer fits on the device".into()));
    }
    Ok((n - layers.len(), layers))
}

impl CudaModel<'_> {
    /// Layers that run on the host, before the device's.
    pub fn host_layers(&self) -> usize {
        self.front
    }

    /// Fresh host states for the layers that run there.
    pub(super) fn new_front(&self) -> Vec<MixerState> {
        self.host.layers[..self.front]
            .iter()
            .map(|l| l.mixer.new_state())
            .collect()
    }

    /// Writes the embeddings of `tokens` into the scratch of `work`, after
    /// the host layers, which run from the batch's position.
    pub(super) fn embed_front(&self, work: &mut Work, tokens: &[u32]) -> kinetic_cuda::Result<()> {
        let mut x = self.host.embed(tokens);
        let pos = work.batch.pos();
        for (layer, state) in self.host.layers.iter().zip(&mut work.front) {
            layer.forward(&mut x, self.eps, pos, None, None, state);
        }
        // Ordered after the work queued so far, like every synchronous copy.
        work.scratch.x.copy_range_from(0, &x)
    }

    pub(super) fn checkpoint_front(&self, work: &mut Work) {
        work.front.iter_mut().for_each(MixerState::checkpoint);
    }

    /// Keeps the first `keep` tokens of the host layers since their
    /// checkpoint.
    pub(super) fn rollback_front(&self, work: &mut Work, keep: usize) {
        let rows: Vec<usize> = (0..keep).collect();
        for (layer, state) in self.host.layers.iter().zip(&mut work.front) {
            layer.mixer.rollback(state, &rows);
        }
    }
}
