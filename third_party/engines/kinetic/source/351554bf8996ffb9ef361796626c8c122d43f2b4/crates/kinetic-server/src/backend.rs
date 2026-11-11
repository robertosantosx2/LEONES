//! The seam between text handling and whatever runs the model.

use std::time::Duration;

use kinetic_grammar::{Grammar, Vocabulary};
use kinetic_models::Input;
use kinetic_vision::Embeddings;

use crate::{Logprobs, Sampling};

/// One generation request, in tokens.
pub struct Job<'j> {
    pub sampling: &'j Sampling,
    /// Most tokens to generate.
    pub max_tokens: usize,
    /// Generation ends after any of these.
    pub stop_tokens: &'j [u32],
    /// Output must match this grammar over this vocabulary.
    pub grammar: Option<(&'j Grammar, &'j Vocabulary)>,
    /// Images in the prompt, in order.
    pub images: &'j [PromptImage],
    /// Records the log-probability of every chosen token.
    pub logprobs: Option<&'j Logprobs>,
}

/// An encoded image whose rows take the place of the prompt's placeholder
/// tokens from `at` on, one token per row.
pub struct PromptImage {
    pub at: usize,
    pub image: Embeddings,
}

/// The entries of `prompt` up to its last token, which must be text, with
/// image rows in place of their placeholder tokens.
pub fn image_inputs<'p>(prompt: &'p [u32], images: &'p [PromptImage]) -> Vec<Input<'p>> {
    let mut inputs = Vec::with_capacity(2 * images.len() + 1);
    let mut at = 0;
    for p in images {
        inputs.push(Input::Tokens(&prompt[at..p.at]));
        inputs.push(Input::Image {
            rows: &p.image.rows,
            width: p.image.width,
            height: p.image.height,
        });
        at = p.at + p.image.len();
    }
    inputs.push(Input::Tokens(&prompt[at..prompt.len() - 1]));
    inputs
}

/// Where the time of one generation went.
#[derive(Clone, Copy, Debug, Default)]
pub struct Timings {
    pub prompt_tokens: usize,
    /// Leading prompt tokens already in the cache from the previous request.
    pub cached_tokens: usize,
    pub prefill: Duration,
    pub generated: usize,
    pub decode: Duration,
}

/// Runs a model on some device. Implementations keep whatever per-sequence
/// state they like between calls, such as the cache of the last prompt.
pub trait Backend: Send {
    /// Runs `prompt` and generates after it, handing each batch of new tokens
    /// to `emit`. Stops after a stop token, after `max_tokens`, or when
    /// `emit` returns false.
    fn generate(
        &mut self,
        prompt: &[u32],
        job: &Job,
        emit: &mut dyn FnMut(&[u32]) -> bool,
    ) -> Timings;

    /// How many leading tokens of `prompt` this backend has run already and
    /// would not run again. Of several free backends, a request goes to
    /// the one that reuses the most.
    fn reuses(&self, _prompt: &[u32]) -> usize {
        0
    }

    /// Runs the next batch of `prompt` that a request for it, or for any
    /// longer prompt starting with it, would run first, so that request
    /// starts further in and generates exactly what it would have; returns
    /// how many leading tokens of `prompt` are run. The same count again
    /// means nothing is left to run ahead.
    fn run_ahead(&mut self, _prompt: &[u32]) -> usize {
        0
    }
}
