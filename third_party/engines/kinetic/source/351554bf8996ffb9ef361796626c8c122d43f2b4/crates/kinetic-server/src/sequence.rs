//! The generation loop every backend shares: prefill a cached sequence,
//! then decode speculatively under a [`Policy`].

use kinetic_models::speculative::{Decoder, Drafter, Greedy, Policy, Sampler, Target};

use crate::backend::{Job, Timings};
use crate::constrained::Constrained;

/// Prompt tokens per forward pass on the CPU; bounds the activations of
/// long prompts. Prompts are cut at multiples of a backend's chunk, which is
/// also where its warm starts resume, so both run the same batches.
pub const PREFILL_CHUNK: usize = 256;

/// CPU prompt runs give the same bits wherever they are cut on multiples of
/// this many tokens after where they started: delta-net layers run batches
/// of 32 or more in chunks of 16, and fewer token by token.
pub const PREFILL_GRID: usize = 32;

/// A sequence a backend keeps between requests.
pub struct Sequence<S> {
    pub state: S,
    /// Every token `state` has run.
    pub tokens: Vec<u32>,
}

impl<S> Sequence<S> {
    /// Whether `prompt` continues this sequence with at least one new token.
    pub fn continues(&self, prompt: &[u32]) -> bool {
        prompt.len() > self.tokens.len() && prompt.starts_with(&self.tokens)
    }
}

/// A backend that runs a request under any policy; [`generate`] picks the
/// policy the request asks for.
pub trait Run<M: Target> {
    fn run<P: Policy<M>>(
        &mut self,
        prompt: &[u32],
        job: &Job,
        policy: &mut P,
        emit: &mut dyn FnMut(&[u32]) -> bool,
    ) -> Timings;
}

/// Runs `job` on `backend` with greedy choice, seeded sampling or a
/// grammar, as the job asks.
pub fn generate<M: Target, B: Run<M>>(
    backend: &mut B,
    prompt: &[u32],
    job: &Job,
    emit: &mut dyn FnMut(&[u32]) -> bool,
) -> Timings {
    assert!(!prompt.is_empty(), "empty prompt");
    let greedy = job.sampling.is_greedy() && job.logprobs.is_none();
    let sampler = || {
        let sampler = Sampler::new(job.sampling.clone());
        match job.logprobs {
            Some(log) => sampler.with_logprobs(log.clone()),
            None => sampler,
        }
    };
    if let Some((grammar, vocab)) = job.grammar {
        let mut policy = Constrained::new(grammar, vocab, prompt.len(), (!greedy).then(sampler));
        return backend.run(prompt, job, &mut policy, emit);
    }
    if greedy {
        backend.run(prompt, job, &mut Greedy, emit)
    } else {
        backend.run(prompt, job, &mut sampler(), emit)
    }
}

/// Runs the tokens of `prompt` that `seq` has not run in chunks of `chunk`,
/// the leading ones without choosing and the last through `policy`, which
/// chooses the token after the prompt.
pub fn extend<M: Target, P: Policy<M>, D: Drafter<M>>(
    model: &M,
    decoder: &mut Decoder<D>,
    policy: &mut P,
    seq: &mut Sequence<M::State>,
    prompt: &[u32],
    chunk: usize,
) {
    let start = seq.tokens.len();
    let last = start + (prompt.len() - start - 1) / chunk * chunk;
    for chunk in prompt[start..last].chunks(chunk) {
        decoder.feed(model, &mut seq.state, chunk);
    }
    seq.tokens.extend_from_slice(&prompt[start..]);
    decoder.prefill(model, policy, &mut seq.state, &seq.tokens, last);
}

/// Where batches run ahead of a request into a sequence that was `base`
/// tokens long stop for `prompt`: on the last multiple of `grid` after
/// `base` before its last token, which a request for it, or for any longer
/// prompt starting with it, may cut at without changing a bit.
pub fn ahead_end(base: usize, prompt: usize, grid: usize) -> usize {
    base + prompt.saturating_sub(base + 1) / grid * grid
}

/// Runs the next batch of `prompt` after `seq`, which ran ahead from
/// `base`, if any is left before [`ahead_end`]: up to the next multiple of
/// `chunk` after `base`, so batches stay where a cold run cuts them.
/// Returns whether it ran one.
pub fn feed_ahead<M: Target, D: Drafter<M>>(
    model: &M,
    decoder: &mut Decoder<D>,
    seq: &mut Sequence<M::State>,
    base: usize,
    prompt: &[u32],
    chunk: usize,
    grid: usize,
) -> bool {
    let start = seq.tokens.len();
    let edge = base + ((start - base) / chunk + 1) * chunk;
    let end = ahead_end(base, prompt.len(), grid).min(edge);
    if start >= end {
        return false;
    }
    let batch = &prompt[start..end];
    decoder.feed(model, &mut seq.state, batch);
    seq.tokens.extend_from_slice(batch);
    true
}

/// The length to cut `tokens`, a sequence that ran ahead from `base`, back
/// to so that `prompt` continues it with the batches a request would have
/// run from `base`; `None` when `prompt` leaves the first `base` tokens.
pub fn rewind_to(tokens: &[u32], base: usize, prompt: &[u32], chunk: usize) -> Option<usize> {
    if prompt.len() <= base || !prompt.starts_with(&tokens[..base]) {
        return None;
    }
    let common = tokens
        .iter()
        .zip(prompt)
        .take_while(|(a, b)| a == b)
        .count();
    let keep = common.min(prompt.len() - 1);
    Some(base + (keep - base) / chunk * chunk)
}

/// Generates after `seq`, whose next token the decoder has chosen, handing
/// each batch of new tokens to `emit`, and returns how many it generated.
pub fn decode<M: Target, P: Policy<M>, D: Drafter<M>>(
    model: &M,
    decoder: &mut Decoder<D>,
    policy: &mut P,
    seq: &mut Sequence<M::State>,
    job: &Job,
    emit: &mut dyn FnMut(&[u32]) -> bool,
) -> usize {
    let is_stop = |t: u32| job.stop_tokens.contains(&t);
    // Tokens are final once chosen, so each goes out before it runs, and
    // the last one never runs.
    let mut new: Vec<u32> = decoder.pending().into_iter().collect();
    let mut generated = 0;
    while generated < job.max_tokens {
        generated += new.len();
        if !emit(&new) || generated >= job.max_tokens || new.last().copied().is_some_and(is_stop) {
            break;
        }
        let before = seq.tokens.len() + 1;
        decoder.step(
            model,
            policy,
            &mut seq.state,
            &mut seq.tokens,
            job.max_tokens - generated,
            is_stop,
        );
        new.clear();
        new.extend_from_slice(&seq.tokens[before..]);
        new.extend(decoder.pending());
    }
    generated
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn running_ahead_stops_where_a_request_would_cut() {
        assert_eq!(ahead_end(0, 0, 4), 0);
        assert_eq!(ahead_end(0, 4, 4), 0);
        assert_eq!(ahead_end(0, 5, 4), 4);
        assert_eq!(ahead_end(3, 12, 4), 11);
        assert_eq!(ahead_end(3, 11, 4), 7);
        assert_eq!(ahead_end(3, 11, 2), 9);
    }

    #[test]
    fn rewinds_to_a_batch_edge_after_the_base() {
        let tokens: Vec<u32> = (0..11).collect();
        let edited: Vec<u32> = (0..9).chain([99, 98, 97]).collect();
        assert_eq!(rewind_to(&tokens, 3, &edited, 4), Some(7));
        assert_eq!(rewind_to(&tokens, 3, &tokens[..8], 4), Some(7));
        assert_eq!(rewind_to(&tokens, 3, &tokens[..7], 4), Some(3));
        assert_eq!(rewind_to(&tokens, 3, &[0, 1, 5, 6], 4), None);
        assert_eq!(rewind_to(&tokens, 3, &tokens[..3], 4), None);
    }
}
