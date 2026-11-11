//! Generation on a Vulkan GPU.

use std::cell::Cell;
use std::time::Instant;

use kinetic_models::speculative::{Decoder, Ensemble, Policy};
use kinetic_models::vulkan::{VulkanModel, VulkanRunner, VulkanState};
use kinetic_models::warm::Warm;
use kinetic_models::{LoadError, Model, State};

use crate::backend::{Backend, Job, Timings};
use crate::cpu::CpuBackend;
use crate::drafter::{self, Source};
use crate::sequence::{self, Run, Sequence, PREFILL_CHUNK};

/// Runs a model on a Vulkan GPU (AMD, Intel or NVIDIA) with the guarantees
/// of [`CpuBackend`]: speculative decoding that changes no token, greedy or
/// seeded, reuse of the last sequence when a prompt extends it and, with a
/// [`Warm`] cache, warm starts that give exactly the output of a cold run.
/// Prompts with images run on the CPU, since the device takes only token
/// ids.
pub struct VulkanBackend<'a> {
    gpu: VulkanModel<'a>,
    model: &'a Model<'a>,
    decoder: Decoder<Ensemble<Source<VulkanModel<'a>>>>,
    cached: Option<Sequence<VulkanState>>,
    warm: Option<Warm<'a>>,
    cpu: CpuBackend<'a>,
    device: String,
}

/// A prompt's state to keep in the warm cache once the reply is out.
struct Keep {
    tokens: Vec<u32>,
    state: State,
    logits: Vec<f32>,
}

// SAFETY: `VulkanModel` and the states made from it are not `Send` only
// because they share their device through `Rc`. Every one of those
// resources, and so every `Rc` to the device, is owned by this backend and
// never handed out, so they all move between threads together; `Backend`
// takes `&mut self`, so one thread drives the device at a time.
unsafe impl Send for VulkanBackend<'_> {}

fn vulkan_error(e: kinetic_vulkan::Error) -> LoadError {
    LoadError(format!("Vulkan: {e}"))
}

impl<'a> VulkanBackend<'a> {
    /// Uploads `model` to the first Vulkan device that can run it, for
    /// sequences of up to `context` tokens. Fails when no device is usable
    /// or the model needs something the Vulkan kernels lack.
    pub fn new(model: &'a Model<'a>, context: usize) -> Result<Self, LoadError> {
        let gpu = VulkanModel::load(model, context)?;
        let state = gpu.new_state().map_err(vulkan_error)?;
        // the drafter's cache shares the memory, so a full device fails here
        // and not on the first request
        drop(gpu.new_mtp_state().map_err(vulkan_error)?);
        Ok(VulkanBackend {
            decoder: drafter::decoder(&gpu),
            cached: Some(Sequence {
                state,
                tokens: Vec::new(),
            }),
            warm: None,
            cpu: CpuBackend::new(model),
            device: format!("{} (Vulkan)", gpu.device_name()),
            model,
            gpu,
        })
    }

    /// [`VulkanBackend::new`] that never drafts, so every token costs one
    /// forward pass, as benchmarks want.
    pub fn plain(model: &'a Model<'a>, context: usize) -> Result<Self, LoadError> {
        VulkanBackend::new(model, context).map(Self::without_drafts)
    }

    /// Turns RAD-1 off: every token costs one forward pass.
    pub fn without_drafts(mut self) -> Self {
        self.decoder.max_draft = 0;
        VulkanBackend {
            cpu: self.cpu.without_drafts(),
            ..self
        }
    }

    /// Starts every new sequence from the longest prefix `warm` holds, and
    /// keeps each new prompt's state there. `warm` must hold only states
    /// this device made; see [`kinetic_models::warm::device_id`].
    pub fn with_warm(mut self, warm: Warm<'a>) -> Self {
        self.warm = Some(warm.aligned(PREFILL_CHUNK));
        self
    }

    /// The name of the device the model runs on, marked as run through
    /// Vulkan.
    pub fn device(&self) -> &str {
        &self.device
    }

    /// The cached sequence when `prompt` extends it, else a new one, run up
    /// to the end of `prompt` with the token after it chosen; the number of
    /// tokens reused; and the state to keep warm, if any.
    fn prefill(
        &mut self,
        prompt: &[u32],
        policy: &mut impl Policy<VulkanModel<'a>>,
    ) -> (Sequence<VulkanState>, usize, Option<Keep>) {
        let chunk = PREFILL_CHUNK;
        // the empty sequence made at load time leaves warm starts their go
        let fresh = |s: &Sequence<VulkanState>| s.tokens.is_empty() && self.warm.is_some();
        let old = match self.cached.take() {
            Some(mut seq) if seq.continues(prompt) && !fresh(&seq) => {
                let reused = seq.tokens.len();
                sequence::extend(
                    &self.gpu,
                    &mut self.decoder,
                    policy,
                    &mut seq,
                    prompt,
                    chunk,
                );
                return (seq, reused, None);
            }
            old => old,
        };
        self.decoder.reset(&self.gpu);
        // the batches a cold prefill runs before its last one
        let head = &prompt[..(prompt.len() - 1) / chunk * chunk];
        let (mut seq, reused, keep) = match self.warm.as_mut().filter(|_| !head.is_empty()) {
            Some(warm) => {
                let runner = VulkanRunner {
                    gpu: &self.gpu,
                    model: self.model,
                    spare: Cell::new(old.map(|s| s.state)),
                };
                let p = warm.prefill_on(&runner, head);
                let keep = (p.hit < head.len()).then(|| Keep {
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
                let state = match old {
                    Some(mut seq) => {
                        device(self.gpu.reset(&mut seq.state));
                        seq.state
                    }
                    None => device(self.gpu.new_state()),
                };
                let seq = Sequence {
                    state,
                    tokens: Vec::new(),
                };
                (seq, 0, None)
            }
        };
        sequence::extend(
            &self.gpu,
            &mut self.decoder,
            policy,
            &mut seq,
            prompt,
            chunk,
        );
        (seq, reused, keep)
    }
}

fn device<T>(r: kinetic_vulkan::Result<T>) -> T {
    r.unwrap_or_else(|e| panic!("Vulkan: {e}"))
}

impl<'a> Run<VulkanModel<'a>> for VulkanBackend<'a> {
    fn run<P: Policy<VulkanModel<'a>>>(
        &mut self,
        prompt: &[u32],
        job: &Job,
        policy: &mut P,
        emit: &mut dyn FnMut(&[u32]) -> bool,
    ) -> Timings {
        let start = Instant::now();
        let (mut seq, cached_tokens, keep) = self.prefill(prompt, policy);
        let prefill = start.elapsed();

        let start = Instant::now();
        let generated = sequence::decode(&self.gpu, &mut self.decoder, policy, &mut seq, job, emit);
        let decode = start.elapsed();
        if let (Some(warm), Some(k)) = (self.warm.as_mut(), keep) {
            // kept in memory either way; a failed disk write only means the
            // next run starts colder
            let _ = warm.insert(&k.tokens, &k.state, &k.logits);
        }
        self.cached = Some(seq);
        Timings {
            prompt_tokens: prompt.len(),
            cached_tokens,
            prefill,
            generated,
            decode,
        }
    }
}

impl Backend for VulkanBackend<'_> {
    fn generate(
        &mut self,
        prompt: &[u32],
        job: &Job,
        emit: &mut dyn FnMut(&[u32]) -> bool,
    ) -> Timings {
        if job.images.is_empty() {
            sequence::generate(self, prompt, job, emit)
        } else {
            self.cpu.generate(prompt, job, emit)
        }
    }
}
