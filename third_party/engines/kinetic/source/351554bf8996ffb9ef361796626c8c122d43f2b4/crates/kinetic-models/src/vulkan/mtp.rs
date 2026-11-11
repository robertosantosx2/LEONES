use std::cell::RefCell;
use std::rc::Rc;

use kinetic_cpu::rms_norm;
use kinetic_vulkan::{
    Batch, Commands, DeviceBuffer, DeviceMatrix, GemvInput, Graph, HostBuffer, Out, Rows,
};

use super::layer::{LayerState, VulkanLayer};
use super::rope::RopeTables;
use super::work::Work;
use super::{Gpu, VulkanModel, MAX_BATCH};
use crate::model::{embed_into, Mtp};
use crate::LoadError;

/// The prediction block on the device; see [`Mtp`]. Its input norms run
/// on the host, which hands the device the joined rows.
pub(super) struct VulkanMtp {
    eh_proj: DeviceMatrix,
    embd_norm: Vec<f32>,
    hidden_norm: Vec<f32>,
    layer: VulkanLayer,
    head_norm: DeviceBuffer<f32>,
    /// The first rows of the output head, which drafts choose from, and
    /// how many.
    draft_head: RefCell<Option<(usize, Rc<DeviceMatrix>)>>,
}

impl VulkanMtp {
    pub fn upload(gpu: &Gpu, m: &Mtp, ropes: &mut RopeTables) -> Result<VulkanMtp, LoadError> {
        Ok(VulkanMtp {
            eh_proj: gpu.matrix(&m.eh_proj)?,
            embd_norm: m.embd_norm.clone(),
            hidden_norm: m.hidden_norm.clone(),
            layer: VulkanLayer::upload(gpu, &m.layer, ropes)?,
            head_norm: gpu.vector(&m.head_norm)?,
            draft_head: RefCell::new(None),
        })
    }

    pub fn size_bytes(&self) -> usize {
        self.eh_proj.size_bytes() + self.layer.size_bytes()
    }
}

/// The cache of a model's prediction block on the device, one entry per
/// position fed.
pub struct VulkanMtpState {
    len: usize,
    checkpoint: Option<usize>,
    work: Work,
    /// Rows of normalized embeddings and hidden states side by side.
    joined_host: HostBuffer<f32>,
    /// The hidden state a draft is chosen from.
    draft_input: HostBuffer<f32>,
    step: Graph,
    /// The recorded draft and the vocabulary it chooses from. Recorded
    /// commands keep the buffers they use, the cache among them.
    draft: Option<(usize, Graph)>,
}

impl VulkanMtpState {
    /// Number of positions fed so far.
    pub fn len(&self) -> usize {
        self.len
    }

    pub fn is_empty(&self) -> bool {
        self.len == 0
    }
}

impl VulkanModel<'_> {
    /// Whether the model has a prediction block.
    pub fn has_mtp(&self) -> bool {
        self.mtp.is_some()
    }

    /// A state for feeding the prediction block as many positions as a
    /// sequence holds, or `None` if the model has none.
    pub fn new_mtp_state(&self) -> kinetic_vulkan::Result<Option<VulkanMtpState>> {
        let Some(mtp) = &self.mtp else {
            return Ok(None);
        };
        let (dev, d) = (&self.gpu.device, self.n_embd);
        let batch = Batch::new(dev, MAX_BATCH, 1, self.context, self.ropes.words())?;
        let layers = std::slice::from_ref(&mtp.layer);
        let work = Work::new(&self.gpu, layers, d, batch, self.n_vocab())?;
        let layer = mtp.layer.new_state(dev, self.context, MAX_BATCH)?;
        let joined = GemvInput::batch(dev, 2 * d, MAX_BATCH)?;
        let joined_host = HostBuffer::new(dev, MAX_BATCH * 2 * d)?;
        let step = self.record_mtp(mtp, &work, &layer, &joined, &joined_host)?;
        Ok(Some(VulkanMtpState {
            len: 0,
            checkpoint: None,
            draft_input: HostBuffer::new(dev, d)?,
            work,
            joined_host,
            step,
            draft: None,
        }))
    }

    fn record_mtp(
        &self,
        mtp: &VulkanMtp,
        w: &Work,
        layer: &LayerState,
        joined: &GemvInput,
        joined_host: &HostBuffer<f32>,
    ) -> kinetic_vulkan::Result<Graph> {
        let (k, d) = (&self.gpu.kernels, self.n_embd);
        let mut c = Commands::new(&self.gpu.device)?;
        w.batch.record_upload(&mut c)?;
        c.upload(joined_host, 0, joined.values(), 0, joined_host.len())?;
        joined.record_quantize(k, &mut c)?;
        let out = Out {
            stride: d,
            offset: 0,
        };
        k.gemv_rows(
            &mtp.eh_proj,
            joined,
            &w.x,
            out,
            Rows::Tokens,
            &w.batch,
            &mut c,
        )?;
        k.norm(
            &w.batch,
            &w.x,
            None,
            &mtp.layer.mixer_norm,
            self.eps,
            &w.h,
            &mut c,
        )?;
        mtp.layer
            .record(&self.gpu, w, layer, &mtp.head_norm, self.eps, &mut c)?;
        c.download(w.h.values(), 0, &w.hidden, 0, w.hidden.len())?;
        c.finish()
    }

    /// Feeds the prediction block one entry per row: the normalized hidden
    /// state at a position and the token that followed it. Returns the
    /// block's output after the last row, normalized for the output head.
    /// See [`Model::mtp_forward`](crate::Model::mtp_forward).
    ///
    /// Panics if the model has no prediction block.
    pub fn mtp_forward(
        &self,
        state: &mut VulkanMtpState,
        hidden: &[f32],
        tokens: &[u32],
    ) -> kinetic_vulkan::Result<Vec<f32>> {
        let mtp = self.mtp.as_ref().expect("model has no prediction block");
        let d = self.n_embd;
        assert_eq!(hidden.len(), tokens.len() * d);
        let mut last = Vec::new();
        for (tokens, hidden) in tokens.chunks(MAX_BATCH).zip(hidden.chunks(MAX_BATCH * d)) {
            let n = tokens.len();
            let w = &mut state.work;
            w.batch.set(n, state.len, n - 1..n, None)?;
            self.ropes.fill(&mut w.batch, state.len, n);
            let mut e = vec![0.0; n * d];
            embed_into(&self.embd, self.embd_scale, tokens, &mut e);
            let rows = state.joined_host.as_mut_slice().chunks_exact_mut(2 * d);
            for ((row, e), h) in rows.zip(e.chunks_exact(d)).zip(hidden.chunks_exact(d)) {
                let (re, rh) = row.split_at_mut(d);
                re.copy_from_slice(e);
                rh.copy_from_slice(h);
                rms_norm(re, &mtp.embd_norm, self.eps);
                rms_norm(rh, &mtp.hidden_norm, self.eps);
            }
            state.step.launch()?;
            state.len += n;
            last = w.hidden.as_slice()[(n - 1) * d..][..d].to_vec();
        }
        Ok(last)
    }

    /// The greedy token of the output head restricted to its first `vocab`
    /// rows, for a normalized hidden state from
    /// [`VulkanModel::mtp_forward`].
    pub fn draft_token(
        &self,
        state: &mut VulkanMtpState,
        hidden: &[f32],
        vocab: usize,
    ) -> kinetic_vulkan::Result<u32> {
        let vocab = vocab.min(self.n_vocab());
        if state.draft.as_ref().is_none_or(|(v, _)| *v != vocab) {
            let graph = self.record_draft(&state.work, &state.draft_input, vocab)?;
            state.draft = Some((vocab, graph));
        }
        let w = &mut state.work;
        w.batch.set(1, 0, 0..1, None)?;
        state.draft_input.as_mut_slice().copy_from_slice(hidden);
        if let Some((_, draft)) = &state.draft {
            draft.launch()?;
        }
        Ok(w.greedy.as_slice()[0])
    }

    fn record_draft(
        &self,
        w: &Work,
        input: &HostBuffer<f32>,
        vocab: usize,
    ) -> kinetic_vulkan::Result<Graph> {
        let mtp = self.mtp.as_ref().expect("model has no prediction block");
        let head = {
            let mut cached = mtp.draft_head.borrow_mut();
            match &*cached {
                Some((v, m)) if *v == vocab => Rc::clone(m),
                _ => {
                    let rows = self.output_rows.top_rows(vocab);
                    let m = Rc::new(DeviceMatrix::upload(&self.gpu.device, &rows)?);
                    *cached = Some((vocab, Rc::clone(&m)));
                    m
                }
            }
        };
        let k = &self.gpu.kernels;
        let mut c = Commands::new(&self.gpu.device)?;
        w.batch.record_upload(&mut c)?;
        c.upload(input, 0, w.h.values(), 0, self.n_embd)?;
        w.h.record_quantize(k, &mut c)?;
        let out = Out {
            stride: vocab,
            offset: 0,
        };
        k.gemv_rows(&head, &w.h, &w.logits, out, Rows::Head, &w.batch, &mut c)?;
        k.argmax(&w.batch, &w.logits, vocab, &w.best, &mut c)?;
        c.download(&w.best, 0, &w.greedy, 0, 1)?;
        c.finish()
    }

    pub fn mtp_checkpoint(&self, state: &mut VulkanMtpState) {
        state.checkpoint = Some(state.len);
    }

    /// Drops every entry fed since the last [`VulkanModel::mtp_checkpoint`]
    /// after the first `keep`; `fed` entries were fed since. The cache is
    /// indexed by position, so later entries overwrite the dropped ones.
    pub fn mtp_rollback(&self, state: &mut VulkanMtpState, fed: usize, keep: usize) {
        let start = state
            .checkpoint
            .take()
            .expect("rollback without a checkpoint");
        assert!(
            start + fed == state.len && keep <= fed,
            "rollback of {fed} entries keeping {keep} after feeding {}",
            state.len - start
        );
        state.len = start + keep;
    }
}
