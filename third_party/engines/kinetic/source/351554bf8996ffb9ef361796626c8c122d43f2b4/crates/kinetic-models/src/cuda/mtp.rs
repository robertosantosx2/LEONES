use std::cell::RefCell;

use kinetic_cuda::{DeviceBuffer, DeviceMatrix, Flow, RmsNorm, MAX_BATCH};

use super::host::clear_layer;
use super::layer::CudaLayer;
use super::scratch::{Spare, Work};
use super::{batches, cuda_error, shape, CudaModel, Gpu};
use crate::model::Mtp;
use crate::LoadError;

/// The prediction block on the device; see [`Mtp`].
pub(super) struct CudaMtp {
    eh_proj: DeviceMatrix,
    embd_norm: DeviceBuffer<f32>,
    hidden_norm: DeviceBuffer<f32>,
    layer: CudaLayer,
    head_norm: DeviceBuffer<f32>,
    /// Full prefill buffers shared by every state, unless states keep their
    /// own.
    pub spare: Option<RefCell<Spare>>,
}

impl CudaMtp {
    pub fn upload(gpu: &Gpu, m: &Mtp, eps: f32) -> Result<CudaMtp, LoadError> {
        let vector = |v: &[f32]| gpu.vector(v).map_err(cuda_error);
        Ok(CudaMtp {
            eh_proj: gpu.matrix(&m.eh_proj).map_err(cuda_error)?,
            embd_norm: vector(&m.embd_norm)?,
            hidden_norm: vector(&m.hidden_norm)?,
            layer: CudaLayer::upload(gpu, &m.layer, None, eps)?,
            head_norm: vector(&m.head_norm)?,
            spare: None,
        })
    }

    pub fn size_bytes(&self) -> usize {
        self.eh_proj.size_bytes() + self.layer.size_bytes()
    }
}

/// The cache of a model's prediction block on the device, one entry per
/// position fed.
pub struct CudaMtpState {
    len: usize,
    checkpoint: Option<usize>,
    work: Work,
    hidden: DeviceBuffer<f32>,
}

impl CudaMtpState {
    /// Number of positions fed so far.
    pub fn len(&self) -> usize {
        self.len
    }

    pub fn is_empty(&self) -> bool {
        self.len == 0
    }
}

impl CudaModel<'_> {
    /// Whether the model has a prediction block.
    pub fn has_mtp(&self) -> bool {
        self.mtp.is_some()
    }

    /// A state for feeding the prediction block as many positions as a
    /// sequence holds, or `None` if the model has none.
    pub fn new_mtp_state(&self) -> kinetic_cuda::Result<Option<CudaMtpState>> {
        let Some(mtp) = &self.mtp else {
            return Ok(None);
        };
        let rows = match mtp.spare {
            Some(_) => MAX_BATCH,
            None => self.batch_rows(),
        };
        let Some(work) = self.new_mtp_work(rows)? else {
            return Ok(None);
        };
        Ok(Some(CudaMtpState {
            len: 0,
            checkpoint: None,
            work,
            hidden: DeviceBuffer::new(&self.gpu.ctx, self.batch_rows() * self.n_embd)?,
        }))
    }

    pub(super) fn new_mtp_work(&self, rows: usize) -> kinetic_cuda::Result<Option<Work>> {
        let Some(mtp) = &self.mtp else {
            return Ok(None);
        };
        let (d, vocab) = (self.n_embd, self.n_vocab());
        let layers = [&mtp.layer];
        Work::new(
            &self.gpu,
            &layers,
            d,
            self.context,
            rows,
            vocab,
            2 * d,
            self.folded,
        )
        .map(Some)
    }

    /// Empties `state` for a new sequence in the same buffers, which saves
    /// the ~10 ms of freeing and allocating them on Windows.
    pub fn clear_mtp_state(&self, state: &mut CudaMtpState) -> kinetic_cuda::Result<()> {
        state.len = 0;
        state.checkpoint = None;
        let stream = &self.gpu.stream;
        state
            .work
            .layers
            .iter_mut()
            .try_for_each(|s| clear_layer(s, stream))
    }

    /// Feeds the prediction block one entry per row: the normalized hidden
    /// state at a position and the token that followed it. Returns the
    /// block's output after the last row, normalized for the output head.
    /// See [`Model::mtp_forward`](crate::Model::mtp_forward).
    ///
    /// Panics if the model has no prediction block.
    pub fn mtp_forward(
        &self,
        state: &mut CudaMtpState,
        hidden: &[f32],
        tokens: &[u32],
    ) -> kinetic_cuda::Result<Vec<f32>> {
        let mtp = self.mtp.as_ref().expect("model has no prediction block");
        let Some(spare) = mtp.spare.as_ref().filter(|_| tokens.len() > MAX_BATCH) else {
            return self.mtp_rows(state, hidden, tokens);
        };
        let mut spare = spare.borrow_mut();
        spare.swap(&mut state.work);
        let out = self.mtp_rows(state, hidden, tokens);
        spare.swap(&mut state.work);
        out
    }

    fn mtp_rows(
        &self,
        state: &mut CudaMtpState,
        hidden: &[f32],
        tokens: &[u32],
    ) -> kinetic_cuda::Result<Vec<f32>> {
        let mtp = self.mtp.as_ref().expect("model has no prediction block");
        let d = self.n_embd;
        assert_eq!(hidden.len(), tokens.len() * d);
        self.check_tokens(tokens)?;
        let (k, stream) = (&self.gpu.kernels, &self.gpu.stream);
        let mut last = vec![0.0; d];
        let mut done = 0;
        for tokens in batches(
            tokens,
            state.len,
            state.checkpoint.is_none(),
            self.batch_rows(),
        ) {
            let n = tokens.len();
            let hidden = &hidden[done * d..][..n * d];
            done += n;
            let flow = match state.checkpoint {
                None => Flow::Commit,
                Some(start) => Flow::Record {
                    first: state.len - start,
                },
            };
            let w = &mut state.work;
            w.batch.set(state.len, tokens, stream)?;
            state.hidden.copy_range_from(0, hidden)?;
            self.embed_rows(&w.batch, tokens, &mut w.scratch.x)?;
            let s = &mut w.scratch;
            let joined = s
                .joined
                .as_mut()
                .expect("prediction scratch has a joined input");
            let norm = |weight| RmsNorm {
                weight,
                eps: self.eps,
            };
            k.rms_norm(&s.x, norm(&mtp.embd_norm), joined, 0, n, stream)?;
            k.rms_norm(&state.hidden, norm(&mtp.hidden_norm), joined, d, n, stream)?;
            k.gemv_rows(&mtp.eh_proj, d, joined, 0..n, &mut s.x, stream)?;
            mtp.layer.input(&self.gpu, &s.x, &mut s.h, n)?;
            mtp.layer.forward(
                &self.gpu,
                s,
                &mut w.layers[0],
                flow,
                &w.batch,
                Some(&mtp.head_norm),
                None,
            )?;
            state.len += n;
            s.h.values().copy_range_to((n - 1) * d, &mut last)?;
        }
        Ok(last)
    }

    /// The greedy token of the output head restricted to its first `vocab`
    /// rows, for a normalized hidden state from
    /// [`CudaModel::mtp_forward`].
    pub fn draft_token(
        &self,
        state: &mut CudaMtpState,
        hidden: &[f32],
        vocab: usize,
    ) -> kinetic_cuda::Result<u32> {
        let (k, stream) = (&self.gpu.kernels, &self.gpu.stream);
        let s = &mut state.work.scratch;
        let rows = vocab.min(self.n_vocab());
        s.h.upload(k, hidden, stream)?;
        let h = match &self.head_folding {
            Some(f) => f.fold(&self.gpu, &s.h, &mut s.folded, 1)?,
            None => &s.h,
        };
        k.gemv_rows(self.head(), rows, h, 0..1, &mut s.logits, stream)?;
        k.argmax(&s.logits, rows, 1, &mut s.greedy, stream)?;
        let mut token = [0];
        s.greedy.best().copy_range_to(0, &mut token)?;
        Ok(token[0])
    }

    pub fn mtp_checkpoint(&self, state: &mut CudaMtpState) -> kinetic_cuda::Result<()> {
        if let Some(start) = state.checkpoint {
            self.mtp_rollback(state, state.len - start, state.len - start)?;
        }
        state.checkpoint = Some(state.len);
        Ok(())
    }

    /// Drops every entry fed since the last [`CudaModel::mtp_checkpoint`]
    /// after the first `keep`; `fed` entries were fed since.
    pub fn mtp_rollback(
        &self,
        state: &mut CudaMtpState,
        fed: usize,
        keep: usize,
    ) -> kinetic_cuda::Result<()> {
        let mtp = self.mtp.as_ref().expect("model has no prediction block");
        let start = state
            .checkpoint
            .take()
            .expect("rollback without a checkpoint");
        if start + fed != state.len || keep > fed {
            return Err(shape(format!(
                "rollback of {fed} entries keeping {keep} after feeding {}",
                state.len - start
            )));
        }
        mtp.layer
            .replay(&self.gpu, &mut state.work.layers[0], keep)?;
        state.len = start + keep;
        Ok(())
    }
}
