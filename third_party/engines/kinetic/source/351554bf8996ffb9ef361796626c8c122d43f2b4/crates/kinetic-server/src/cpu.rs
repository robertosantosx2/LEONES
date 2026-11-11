//! Generation on the CPU with `kinetic-models`.

use std::time::Instant;

use kinetic_models::speculative::{Decoder, Ensemble, Policy};
use kinetic_models::warm::Warm;
use kinetic_models::{Model, State};

use crate::backend::{image_inputs, Backend, Job, PromptImage, Timings};
use crate::drafter::{self, Source};
use crate::sequence::{self, Run, Sequence, PREFILL_CHUNK, PREFILL_GRID};

/// Runs a [`Model`] on the CPU with lossless speculative decoding: greedy
/// requests produce exactly the plain greedy tokens, and sampled ones draw
/// every token from exactly the distribution plain sampling would, the same
/// tokens for the same seed. The last sequence stays cached, so a prompt
/// that extends it, such as the next turn of a chat, only runs its new
/// tokens; with a [`Warm`] cache, any prompt resumes from the longest prefix
/// an earlier one left behind.
pub struct CpuBackend<'a> {
    model: &'a Model<'a>,
    decoder: Decoder<Ensemble<Source<Model<'a>>>>,
    cached: Option<Sequence<State>>,
    /// The length `cached` had when it began to run ahead of a request.
    ahead: Option<usize>,
    warm: Option<Warm<'a>>,
}

/// A prompt's state to keep in the warm cache once the reply is out.
struct Keep {
    tokens: Vec<u32>,
    state: State,
    logits: Vec<f32>,
}

impl<'a> CpuBackend<'a> {
    pub fn new(model: &'a Model<'a>) -> Self {
        model.page_in_experts();
        CpuBackend {
            model,
            decoder: drafter::decoder(model),
            cached: None,
            ahead: None,
            warm: None,
        }
    }

    /// A backend that never drafts, so every token costs one forward pass,
    /// as benchmarks want.
    pub fn plain(model: &'a Model<'a>) -> Self {
        CpuBackend::new(model).without_drafts()
    }

    /// Turns RAD-1 off: every token costs one forward pass.
    pub fn without_drafts(mut self) -> Self {
        self.decoder.max_draft = 0;
        self
    }

    /// Starts every new sequence from the longest prefix `warm` holds, and
    /// keeps each new prompt's state there. Warm starts resume where a cold
    /// prefill cuts its batches, so they give exactly its output.
    pub fn with_warm(mut self, warm: Warm<'a>) -> Self {
        self.warm = Some(warm.aligned(PREFILL_CHUNK));
        self
    }

    /// The cached sequence when `prompt` extends it, else a new one, run up
    /// to the end of `prompt` with the token after it chosen; the number of
    /// tokens reused; and the state to keep warm, if any.
    fn prefill(
        &mut self,
        prompt: &[u32],
        policy: &mut impl Policy<Model<'a>>,
    ) -> (Sequence<State>, usize, Option<Keep>) {
        self.rewind(prompt);
        if let Some(mut seq) = self.cached.take_if(|s| s.continues(prompt)) {
            let reused = seq.tokens.len();
            self.extend(&mut seq, prompt, policy);
            return (seq, reused, None);
        }
        self.decoder.reset(self.model);
        // The batches a cold prefill runs before its last one.
        let head = &prompt[..(prompt.len() - 1) / PREFILL_CHUNK * PREFILL_CHUNK];
        if let Some(mut seq) = self.cut_cached(head) {
            let reused = seq.tokens.len();
            self.extend(&mut seq, prompt, policy);
            return (seq, reused, None);
        }
        let (mut seq, reused, keep) = match self.warm.as_mut().filter(|_| !head.is_empty()) {
            Some(warm) => {
                let p = warm.prefill(head);
                let hit = p.hit;
                let worth = p.hit < head.len() && warm.worth_keeping(self.model, head.len());
                let keep = worth.then(|| Keep {
                    tokens: head.to_vec(),
                    state: p.state.clone(),
                    logits: p.logits,
                });
                let seq = Sequence {
                    state: p.state,
                    tokens: head.to_vec(),
                };
                (seq, hit, keep)
            }
            None => {
                let seq = Sequence {
                    state: self.model.new_state(),
                    tokens: Vec::new(),
                };
                (seq, 0, None)
            }
        };
        self.extend(&mut seq, prompt, policy);
        (seq, reused, keep)
    }

    /// [`sequence::extend`] that runs the prompt up to its last multiple of
    /// [`PREFILL_GRID`] first, as running ahead stops there, and marks the
    /// state after its last whole batch, which is where the next turn of a
    /// chat parts from it when the template writes the reply differently
    /// from how it was generated.
    fn extend(
        &mut self,
        seq: &mut Sequence<State>,
        prompt: &[u32],
        policy: &mut impl Policy<Model<'a>>,
    ) {
        let base = seq.tokens.len();
        while sequence::feed_ahead(
            self.model,
            &mut self.decoder,
            seq,
            base,
            prompt,
            PREFILL_CHUNK,
            PREFILL_CHUNK,
        ) {}
        if seq.tokens.len().is_multiple_of(PREFILL_CHUNK) {
            // one mark at a time: on hybrid models each copies every recurrent state
            seq.state.forget_marks();
            self.model.mark(&mut seq.state);
        }
        sequence::feed_ahead(
            self.model,
            &mut self.decoder,
            seq,
            base,
            prompt,
            PREFILL_CHUNK,
            PREFILL_GRID,
        );
        sequence::extend(
            self.model,
            &mut self.decoder,
            policy,
            seq,
            prompt,
            PREFILL_CHUNK,
        );
    }

    /// The cached sequence cut back to the last batch edge it shares with
    /// `head` that it returns to exactly, if that leaves any of it.
    fn cut_cached(&mut self, head: &[u32]) -> Option<Sequence<State>> {
        let mut seq = self.cached.take()?;
        let common = seq
            .tokens
            .iter()
            .zip(head)
            .take_while(|(a, b)| a == b)
            .count();
        let to = self
            .model
            .reach(&seq.state, common / PREFILL_CHUNK * PREFILL_CHUNK);
        // only batch edges resume with the batches of a cold run
        if to == 0 || !to.is_multiple_of(PREFILL_CHUNK) {
            return None;
        }
        self.model.truncate(&mut seq.state, to);
        seq.tokens.truncate(to);
        Some(seq)
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
        if let Some(to) = sequence::rewind_to(&seq.tokens, base, prompt, PREFILL_GRID) {
            // marks sit only at batch edges after `base`
            let reached = self.model.truncate(&mut seq.state, to);
            seq.tokens.truncate(reached);
            self.decoder.reset(self.model);
        }
    }

    /// Takes the sequence a request for `prompt` would start from when it
    /// cannot continue the cached one: the longest warm prefix, or none.
    fn restart(&mut self, prompt: &[u32]) -> bool {
        let head = &prompt[..(prompt.len() - 1) / PREFILL_CHUNK * PREFILL_CHUNK];
        if head.is_empty() {
            return false;
        }
        self.decoder.reset(self.model);
        self.cached = self.cut_cached(head).or_else(|| {
            let (state, hit) = match self.warm.as_mut() {
                Some(warm) => warm.resume_on(self.model, head),
                None => (self.model.new_state(), 0),
            };
            Some(Sequence {
                state,
                tokens: head[..hit].to_vec(),
            })
        });
        self.ahead = None;
        true
    }

    fn ahead_of(&mut self, prompt: &[u32]) -> usize {
        self.rewind(prompt);
        let follows = self
            .cached
            .as_ref()
            .is_some_and(|s| prompt.starts_with(&s.tokens));
        // a stale draft the sequence already covers must not throw it away
        let covers = self
            .cached
            .as_ref()
            .is_some_and(|s| s.tokens.starts_with(prompt));
        if !follows && covers {
            return prompt.len();
        }
        if !follows && !self.restart(prompt) {
            return 0;
        }
        let grid = self.warm.as_ref().and_then(Warm::grid);
        let seq = self.cached.as_mut().expect("a cached sequence");
        let base = match self.ahead {
            Some(base) => base,
            None => {
                // a mark here lets edits cut back to where the request
                // would have started
                seq.state.forget_marks();
                if !seq.tokens.is_empty() {
                    self.model.mark(&mut seq.state);
                }
                *self.ahead.insert(seq.tokens.len())
            }
        };
        let ran = sequence::feed_ahead(
            self.model,
            &mut self.decoder,
            seq,
            base,
            prompt,
            PREFILL_CHUNK,
            PREFILL_GRID,
        );
        if ran && grid.is_some_and(|g| (seq.tokens.len() - base).is_multiple_of(g)) {
            self.model.mark(&mut seq.state);
        }
        seq.tokens.len()
    }

    /// A new sequence run up to the end of `prompt` with the token after it
    /// chosen, with image rows in place of their placeholder tokens. The
    /// last token must be text.
    fn prefill_images(
        &mut self,
        prompt: &[u32],
        images: &[PromptImage],
        policy: &mut impl Policy<Model<'a>>,
    ) -> Sequence<State> {
        self.decoder.reset(self.model);
        let mut state = self.model.new_state();
        let last = prompt.len() - 1;
        self.model
            .run_inputs(&mut state, &image_inputs(prompt, images), false);
        self.decoder
            .prefill(self.model, policy, &mut state, prompt, last);
        Sequence {
            state,
            tokens: prompt.to_vec(),
        }
    }
}

impl<'a> Run<Model<'a>> for CpuBackend<'a> {
    fn run<P: Policy<Model<'a>>>(
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
            sequence::decode(self.model, &mut self.decoder, policy, &mut seq, job, emit);
        let decode = start.elapsed();
        if let (Some(warm), Some(k)) = (self.warm.as_mut(), keep) {
            // The state is kept in memory either way; a failed disk write
            // only means the next run starts colder.
            let _ = warm.insert(&k.tokens, &k.state, &k.logits);
        }
        // Placeholder tokens do not tell images apart, so a sequence with
        // images is never reused.
        // shortcut: each turn of a chat about an image runs it again; key the
        // cache on image hashes when image chats get long.
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

impl Backend for CpuBackend<'_> {
    fn generate(
        &mut self,
        prompt: &[u32],
        job: &Job,
        emit: &mut dyn FnMut(&[u32]) -> bool,
    ) -> Timings {
        let _seat = self.model.seat();
        sequence::generate(self, prompt, job, emit)
    }

    fn reuses(&self, prompt: &[u32]) -> usize {
        self.cached
            .as_ref()
            .filter(|s| s.continues(prompt))
            .map_or(0, |s| s.tokens.len())
    }

    fn run_ahead(&mut self, prompt: &[u32]) -> usize {
        let _seat = self.model.seat();
        self.ahead_of(prompt)
    }
}
