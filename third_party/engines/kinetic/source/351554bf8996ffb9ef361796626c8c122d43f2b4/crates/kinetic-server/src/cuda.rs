//! Generation on a CUDA GPU.

use std::cell::Cell;
use std::sync::Arc;
use std::time::Instant;

use kinetic_cuda::MAX_BATCH;
use kinetic_models::cuda::{
    CudaModel, CudaRunner, CudaState, Placement, PREFILL_BATCH, PREFILL_GRID,
};
use kinetic_models::speculative::{Decoder, Ensemble, Policy};
use kinetic_models::warm::{Runner, Warm};
use kinetic_models::{LoadError, Model, State};

use crate::backend::{image_inputs, Backend, Job, PromptImage, Timings};
use crate::cpu::CpuBackend;
use crate::drafter::{self, Source};
use crate::sequence::{self, Run, Sequence};

/// Runs a model on the first CUDA device with the guarantees of
/// [`CpuBackend`]: speculative decoding that changes no token, greedy or
/// seeded, reuse of the last sequence when a prompt extends it and, with a
/// [`Warm`] cache, warm starts that give exactly the output of a cold run.
/// Prompts with images run on the CPU, since the device takes only token
/// ids. Backends made with [`CudaBackend::slot`] share the device and its
/// weights, run requests at once and share passes over the weights.
pub struct CudaBackend<'a> {
    gpu: Arc<CudaModel<'a>>,
    model: &'a Model<'a>,
    decoder: Decoder<Ensemble<Source<CudaModel<'a>>>>,
    cached: Option<Sequence<CudaState>>,
    /// The length `cached` had when it began to run ahead of a request.
    ahead: Option<usize>,
    warm: Option<Warm<'a>>,
    cpu: CpuBackend<'a>,
    device: String,
    /// Most draft tokens per step when the device runs only this request.
    max_draft: usize,
}

/// A prompt's state to keep in the warm cache once the reply is out.
struct Keep {
    tokens: Vec<u32>,
    state: State,
    logits: Vec<f32>,
}

// SAFETY: `CudaModel` and the states made from it are not `Send` only
// because they share their context through `Rc`. Every one of those
// resources, and so every `Rc` to the context, belongs to this backend or
// to the slots made from it, which share the model itself through an
// `Arc`. A backend touches the device only in `generate`, and there only
// while it holds a seat of the model; seats let one thread at a time drive
// the device, ordered by the lock they take, so no two threads ever use
// those resources or their `Rc` counts at once. Each driver call makes the
// context current on the calling thread first.
unsafe impl Send for CudaBackend<'_> {}

/// Device memory a slot must leave free; every buffer is made up front, so
/// this only covers recorded passes and the driver.
const SLOT_RESERVE: usize = 256 << 20;

fn cuda_error(e: kinetic_cuda::Error) -> LoadError {
    LoadError(format!("CUDA: {e}"))
}

impl<'a> CudaBackend<'a> {
    /// Uploads `model` to the first CUDA device for sequences of up to
    /// `context` tokens, with the layers that do not fit on the CPU. Fails
    /// when no device is usable or when not even one layer and the caches
    /// of one sequence fit in its memory.
    pub fn new(model: &'a Model<'a>, context: usize) -> Result<Self, LoadError> {
        CudaBackend::with_placement(model, context, Placement::default())
    }

    /// [`CudaBackend::new`] within the limits of `placement`.
    pub fn with_placement(
        model: &'a Model<'a>,
        context: usize,
        placement: Placement,
    ) -> Result<Self, LoadError> {
        let name = kinetic_cuda::Device::get(0)
            .and_then(|d| d.info())
            .map_err(cuda_error)?
            .name;
        // slots on other threads share it, see the SAFETY note on Send
        #[allow(clippy::arc_with_non_send_sync)]
        let gpu = Arc::new(CudaModel::load_with(model, context, placement)?);
        let device = match gpu.host_layers() {
            0 => name,
            host => format!(
                "{name}, {} of {} layers, the rest on the CPU",
                model.n_layers() - host,
                model.n_layers()
            ),
        };
        let state = gpu.new_state().map_err(cuda_error)?;
        // The drafter's cache comes out of the same memory; finding out here
        // keeps a full device from failing the first request instead.
        drop(gpu.new_mtp_state().map_err(cuda_error)?);
        let decoder = drafter::decoder(&*gpu);
        Ok(CudaBackend {
            max_draft: decoder.max_draft,
            decoder,
            cached: Some(Sequence {
                state,
                tokens: Vec::new(),
            }),
            ahead: None,
            warm: None,
            cpu: CpuBackend::new(model),
            model,
            device,
            gpu,
        })
    }

    /// [`CudaBackend::new`] that never drafts, so every token costs one
    /// forward pass, as benchmarks want.
    pub fn plain(model: &'a Model<'a>, context: usize) -> Result<Self, LoadError> {
        CudaBackend::new(model, context).map(Self::without_drafts)
    }

    /// Turns RAD-1 off, also for the slots made from this backend after.
    pub fn without_drafts(mut self) -> Self {
        self.decoder.max_draft = 0;
        CudaBackend {
            max_draft: 0,
            cpu: self.cpu.without_drafts(),
            ..self
        }
    }

    /// Starts every new sequence from the longest prefix `warm` holds, and
    /// keeps each new prompt's state there. `warm` must hold only states
    /// this device made; see [`kinetic_models::warm::device_id`]. Warm
    /// starts resume where a cold prefill cuts its batches, so they give
    /// exactly its output.
    pub fn with_warm(mut self, warm: Warm<'a>) -> Self {
        self.warm = Some(warm.aligned(PREFILL_BATCH));
        self
    }

    /// Another backend on the same device and weights, with a sequence and
    /// drafts of its own, so that requests on the two run at once. Fails
    /// when the device has no room for the slot's caches and
    /// [`SLOT_RESERVE`] more.
    pub fn slot(&self) -> Result<Self, LoadError> {
        let _seat = self.gpu.seat();
        let state = self.gpu.new_state().map_err(cuda_error)?;
        drop(self.gpu.new_mtp_state().map_err(cuda_error)?);
        let (free, _) = self.gpu.memory_info().map_err(cuda_error)?;
        if free < SLOT_RESERVE {
            return Err(LoadError(format!(
                "the GPU has no room for the caches of another sequence, {} MiB left",
                free >> 20
            )));
        }
        let mut decoder = drafter::decoder(&*self.gpu);
        decoder.max_draft = self.max_draft;
        Ok(CudaBackend {
            gpu: Arc::clone(&self.gpu),
            model: self.model,
            decoder,
            cached: Some(Sequence {
                state,
                tokens: Vec::new(),
            }),
            warm: None,
            cpu: match self.max_draft {
                0 => CpuBackend::new(self.model).without_drafts(),
                _ => CpuBackend::new(self.model),
            },
            device: self.device.clone(),
            max_draft: self.max_draft,
            ahead: None,
        })
    }

    /// The name of the device the model runs on.
    pub fn device(&self) -> &str {
        &self.device
    }

    /// The cached sequence when `prompt` extends it, else a new one, run up
    /// to the end of `prompt` with the token after it chosen; the number of
    /// tokens reused; and the state to keep warm, if any.
    fn prefill(
        &mut self,
        prompt: &[u32],
        policy: &mut impl Policy<CudaModel<'a>>,
    ) -> (Sequence<CudaState>, usize, Option<Keep>) {
        self.rewind(prompt);
        // The batches a cold prefill runs before its last one.
        let head = &prompt[..(prompt.len() - 1) / PREFILL_BATCH * PREFILL_BATCH];
        // The empty sequence made at load time leaves warm starts their go.
        let warm = self.warm.is_some() && !head.is_empty();
        let fresh = |s: &Sequence<CudaState>| s.tokens.is_empty() && warm;
        let old = match self.cached.take() {
            Some(mut seq) if seq.continues(prompt) && !fresh(&seq) => {
                let reused = seq.tokens.len();
                self.extend(&mut seq, prompt, policy);
                return (seq, reused, None);
            }
            old => old,
        };
        self.decoder.reset(&*self.gpu);
        let (mut seq, reused, keep) = match self.warm.as_mut().filter(|_| !head.is_empty()) {
            Some(warm) => {
                // The restored state takes the old sequence's buffers.
                let runner = CudaRunner {
                    gpu: &self.gpu,
                    model: self.model,
                    spare: Cell::new(old.map(|s| s.state)),
                };
                let p = warm.prefill_on(&runner, head);
                let worth = p.hit < head.len() && warm.worth_keeping(&runner, head.len());
                let keep = worth.then(|| Keep {
                    tokens: head.to_vec(),
                    state: device(self.gpu.host_state(self.model, &p.state)),
                    logits: p.logits,
                });
                let seq = Sequence {
                    state: p.state,
                    tokens: head.to_vec(),
                };
                (seq, p.hit, keep)
            }
            None => {
                let seq = Sequence {
                    state: self.empty_state(old.map(|s| s.state)),
                    tokens: Vec::new(),
                };
                (seq, 0, None)
            }
        };
        self.extend(&mut seq, prompt, policy);
        (seq, reused, keep)
    }

    /// Runs the tokens of `prompt` after `seq`, which ends on the grid, as a
    /// cold run cuts them, and chooses the token after them; a mark where
    /// the last batch starts lets [`CudaBackend::settle`] run the reply again.
    fn extend(
        &mut self,
        seq: &mut Sequence<CudaState>,
        prompt: &[u32],
        policy: &mut impl Policy<CudaModel<'a>>,
    ) {
        let start = seq.tokens.len();
        let rest = prompt.len() - start;
        // a cold run cuts off its last tokens past the grid only when too
        // few for a batch of their own; see `PREFILL_GRID`
        let step = match rest % PREFILL_GRID {
            0 => PREFILL_BATCH,
            _ => PREFILL_GRID,
        };
        let last = start + (rest - 1) / step * step;
        for batch in prompt[start..last].chunks(PREFILL_BATCH) {
            self.decoder.feed(&*self.gpu, &mut seq.state, batch);
        }
        seq.tokens.extend_from_slice(&prompt[start..last]);
        seq.state.forget_marks();
        if last > 0 {
            self.runner(None).mark(&mut seq.state);
        }
        sequence::extend(
            &*self.gpu,
            &mut self.decoder,
            policy,
            seq,
            prompt,
            PREFILL_BATCH,
        );
    }

    /// Runs the reply in `seq` after a prompt of `prompt` tokens again as a
    /// cold prompt runs it, from the mark [`CudaBackend::extend`] left up to
    /// the last point on the grid, so that a longer prompt continues it
    /// exactly: decode steps sum unlike prompt batches.
    fn settle(&mut self, seq: &mut Sequence<CudaState>, prompt: usize) {
        let Sequence { state, tokens } = seq;
        let mark = (prompt - 1) / PREFILL_GRID * PREFILL_GRID;
        let mark = device(self.gpu.truncate(self.model, state, mark));
        let end = mark + (tokens.len() - mark) / PREFILL_GRID * PREFILL_GRID;
        self.decoder.reset(&*self.gpu);
        for batch in tokens[mark..end].chunks(PREFILL_BATCH) {
            self.decoder.feed(&*self.gpu, state, batch);
        }
        tokens.truncate(end);
    }

    /// A new sequence run up to the end of `prompt` with the token after it
    /// chosen, with image rows in place of their placeholder tokens.
    fn prefill_images(
        &mut self,
        prompt: &[u32],
        images: &[PromptImage],
        policy: &mut impl Policy<CudaModel<'a>>,
    ) -> Sequence<CudaState> {
        self.decoder.reset(&*self.gpu);
        let old = self.cached.take().map(|s| s.state);
        let mut state = self.empty_state(old);
        let last = prompt.len() - 1;
        device(
            self.gpu
                .run_inputs(&mut state, &image_inputs(prompt, images)),
        );
        self.decoder
            .prefill(&*self.gpu, policy, &mut state, prompt, last);
        Sequence {
            state,
            tokens: prompt.to_vec(),
        }
    }

    /// An empty state, in the buffers of `old` when there is one.
    fn empty_state(&self, old: Option<CudaState>) -> CudaState {
        match old {
            Some(mut state) => {
                device(self.gpu.reset_state(&mut state));
                state
            }
            None => device(self.gpu.new_state()),
        }
    }

    fn runner(&self, spare: Option<CudaState>) -> CudaRunner<'_, 'a> {
        CudaRunner {
            gpu: &self.gpu,
            model: self.model,
            spare: Cell::new(spare),
        }
    }

    /// Cuts the cached sequence back to where a request for `prompt` would
    /// continue it from, once it ran ahead along text `prompt` leaves.
    fn rewind(&mut self, prompt: &[u32]) {
        let (Some(base), Some(seq)) = (self.ahead, self.cached.as_mut()) else {
            return;
        };
        if seq.continues(prompt) {
            return;
        }
        let Some(to) = sequence::rewind_to(&seq.tokens, base, prompt, PREFILL_GRID) else {
            return;
        };
        // marks sit only at batch edges after `base`
        let reached = device(self.gpu.truncate(self.model, &mut seq.state, to));
        seq.tokens.truncate(reached);
        self.decoder.reset(&self.gpu);
    }

    /// Takes the sequence a request for `prompt` would start from when it
    /// cannot continue the cached one: the longest warm prefix, or none.
    fn restart(&mut self, prompt: &[u32]) -> bool {
        let head = &prompt[..(prompt.len() - 1) / PREFILL_BATCH * PREFILL_BATCH];
        if head.is_empty() {
            return false;
        }
        self.decoder.reset(&self.gpu);
        let old = self.cached.take().map(|s| s.state);
        let (state, hit) = match self.warm.as_mut() {
            Some(warm) => {
                let runner = CudaRunner {
                    gpu: &self.gpu,
                    model: self.model,
                    spare: Cell::new(old),
                };
                warm.resume_on(&runner, head)
            }
            None => (self.empty_state(old), 0),
        };
        self.cached = Some(Sequence {
            state,
            tokens: head[..hit].to_vec(),
        });
        self.ahead = None;
        true
    }

    fn ahead_of(&mut self, prompt: &[u32]) -> usize {
        self.rewind(prompt);
        let fresh = self.warm.is_some();
        let cached = self.cached.as_ref();
        let follows = cached
            .is_some_and(|s| prompt.starts_with(&s.tokens) && !(s.tokens.is_empty() && fresh));
        // a stale draft the sequence already covers must not throw it away
        let covers = cached.is_some_and(|s| s.tokens.starts_with(prompt));
        if !follows && covers {
            return prompt.len();
        }
        if !follows && !self.restart(prompt) {
            return 0;
        }
        let grid = self.warm.as_ref().and_then(Warm::grid);
        let mut seq = self.cached.take().expect("a cached sequence");
        let base = match self.ahead {
            Some(base) => base,
            None => {
                // a mark here lets edits cut back to where the request
                // would have started
                seq.state.forget_marks();
                if !seq.tokens.is_empty() {
                    self.runner(None).mark(&mut seq.state);
                }
                *self.ahead.insert(seq.tokens.len())
            }
        };
        let ran = sequence::feed_ahead(
            &*self.gpu,
            &mut self.decoder,
            &mut seq,
            base,
            prompt,
            PREFILL_BATCH,
            PREFILL_GRID,
        );
        if ran && grid.is_some_and(|g| (seq.tokens.len() - base).is_multiple_of(g)) {
            self.runner(None).mark(&mut seq.state);
        }
        let len = seq.tokens.len();
        self.cached = Some(seq);
        len
    }
}

fn device<T>(r: kinetic_cuda::Result<T>) -> T {
    r.unwrap_or_else(|e| panic!("CUDA: {e}"))
}

impl<'a> Run<CudaModel<'a>> for CudaBackend<'a> {
    fn run<P: Policy<CudaModel<'a>>>(
        &mut self,
        prompt: &[u32],
        job: &Job,
        policy: &mut P,
        emit: &mut dyn FnMut(&[u32]) -> bool,
    ) -> Timings {
        let start = Instant::now();
        let (mut seq, cached_tokens, keep) = if job.images.is_empty() {
            self.prefill(prompt, policy)
        } else {
            (self.prefill_images(prompt, job.images, policy), 0, None)
        };
        let prefill = start.elapsed();

        let start = Instant::now();
        let generated =
            sequence::decode(&*self.gpu, &mut self.decoder, policy, &mut seq, job, emit);
        let decode = start.elapsed();
        self.settle(&mut seq, prompt.len());
        if let (Some(warm), Some(k)) = (self.warm.as_mut(), keep) {
            // The state is kept in memory either way; a failed disk write
            // only means the next run starts colder.
            let _ = warm.insert(&k.tokens, &k.state, &k.logits);
        }
        // placeholder tokens do not tell images apart
        self.cached = job.images.is_empty().then_some(seq);
        self.ahead = None;
        Timings {
            prompt_tokens: prompt.len(),
            cached_tokens,
            prefill,
            generated,
            decode,
        }
    }
}

impl Backend for CudaBackend<'_> {
    fn generate(
        &mut self,
        prompt: &[u32],
        job: &Job,
        emit: &mut dyn FnMut(&[u32]) -> bool,
    ) -> Timings {
        if !job.images.is_empty() && !self.gpu.takes_images() {
            return self.cpu.generate(prompt, job, emit);
        }
        let gpu = Arc::clone(&self.gpu);
        let seat = gpu.seat();
        // drafts shrink so every seat's rows fit one shared GEMV
        let rows = MAX_BATCH / gpu.seats();
        self.decoder.max_draft = self.max_draft.min(rows.saturating_sub(1));
        sequence::generate(self, prompt, job, &mut |t| seat.away(|| emit(t)))
    }

    fn reuses(&self, prompt: &[u32]) -> usize {
        self.cached
            .as_ref()
            .filter(|s| s.continues(prompt) && !s.tokens.is_empty())
            .map_or(0, |s| s.tokens.len())
    }

    fn run_ahead(&mut self, prompt: &[u32]) -> usize {
        let gpu = Arc::clone(&self.gpu);
        let _seat = gpu.seat();
        self.ahead_of(prompt)
    }
}
