//! Log-probabilities of chosen tokens, as the OpenAI API reports them.

use std::sync::{Arc, Mutex, MutexGuard, PoisonError};

/// A chosen token's log-probability under the model, and the likeliest
/// tokens at its position.
#[derive(Clone, Debug, PartialEq)]
pub struct TokenLogprob {
    pub token: u32,
    pub logprob: f32,
    /// The likeliest tokens with their log-probabilities, most likely first.
    pub top: Vec<(u32, f32)>,
}

impl TokenLogprob {
    /// The log-softmax of `logits` at `token`, with the `top` likeliest
    /// tokens; ties go to the lower token.
    pub fn new(logits: &[f32], token: u32, top: usize) -> Self {
        let max = logits.iter().copied().fold(f32::NEG_INFINITY, f32::max);
        let sum: f64 = logits.iter().map(|&l| f64::from(l - max).exp()).sum();
        let norm = max + sum.ln() as f32;
        let mut best: Vec<(u32, f32)> = (0u32..).zip(logits.iter().copied()).collect();
        let by_logit = |a: &(u32, f32), b: &(u32, f32)| b.1.total_cmp(&a.1).then(a.0.cmp(&b.0));
        let top = top.min(best.len());
        if top > 0 && top < best.len() {
            best.select_nth_unstable_by(top - 1, by_logit);
        }
        best.truncate(top);
        best.sort_unstable_by(by_logit);
        best.iter_mut().for_each(|(_, l)| *l -= norm);
        TokenLogprob {
            token,
            logprob: logits
                .get(token as usize)
                .map_or(f32::NEG_INFINITY, |l| l - norm),
            top: best,
        }
    }
}

/// Where a [`Sampler`](super::Sampler) writes a [`TokenLogprob`] for every
/// token it chooses, in order; clones share the record.
#[derive(Clone, Debug, Default)]
pub struct Logprobs {
    top: usize,
    tokens: Arc<Mutex<Vec<TokenLogprob>>>,
}

impl Logprobs {
    /// Records each token with its `top` likeliest alternatives.
    pub fn new(top: usize) -> Self {
        Logprobs {
            top,
            tokens: Arc::default(),
        }
    }

    /// The records from `start` up to `end`, or up to the last one.
    pub fn range(&self, start: usize, end: usize) -> Vec<TokenLogprob> {
        let tokens = self.lock();
        let end = end.min(tokens.len());
        tokens.get(start..end).unwrap_or_default().to_vec()
    }

    /// Keeps the first `len` records.
    pub fn truncate(&self, len: usize) {
        self.lock().truncate(len);
    }

    pub(super) fn record(&self, logits: &[f32], token: u32) {
        let entry = TokenLogprob::new(logits, token, self.top);
        self.lock().push(entry);
    }

    fn lock(&self) -> MutexGuard<'_, Vec<TokenLogprob>> {
        self.tokens.lock().unwrap_or_else(PoisonError::into_inner)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn logprobs_are_the_log_softmax() {
        // probabilities 1/2, 1/4, 1/4
        let logits = [2f32.ln() + 3.0, 3.0, 3.0];
        let lp = TokenLogprob::new(&logits, 2, 2);
        assert!((lp.logprob - 0.25f32.ln()).abs() < 1e-6);
        assert_eq!(lp.top.iter().map(|t| t.0).collect::<Vec<_>>(), [0, 1]);
        assert!((lp.top[0].1 - 0.5f32.ln()).abs() < 1e-6);
    }

    #[test]
    fn clones_share_the_record() {
        let log = Logprobs::new(0);
        log.clone().record(&[0.0, 0.0], 1);
        log.record(&[0.0, 0.0], 0);
        let tokens = log.range(0, usize::MAX);
        assert_eq!(tokens.iter().map(|t| t.token).collect::<Vec<_>>(), [1, 0]);
        assert!(tokens[0].top.is_empty());
        log.truncate(1);
        assert_eq!(log.range(1, 5), []);
    }
}
