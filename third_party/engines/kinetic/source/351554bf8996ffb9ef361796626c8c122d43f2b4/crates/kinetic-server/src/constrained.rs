//! Generation held to a grammar, as for `response_format` and `grammar`.

use kinetic_grammar::{Grammar, Matcher, TokenSet, Vocabulary};
use kinetic_models::speculative::{argmax, Policy, Sampler, Target};

/// A policy that only chooses tokens the grammar allows. Drafts are checked
/// with the same masked choice, so speculative decoding stays exact.
pub struct Constrained<'g> {
    grammar: &'g Grammar,
    vocab: &'g Vocabulary,
    matcher: Matcher<'g>,
    allowed: TokenSet,
    /// Context length when generation started; the grammar covers the rest.
    start: usize,
    /// Tokens the matcher has accepted.
    seen: Vec<u32>,
    sampler: Option<Sampler>,
}

impl<'g> Constrained<'g> {
    /// Chooses greedily when `sampler` is `None`.
    pub fn new(
        grammar: &'g Grammar,
        vocab: &'g Vocabulary,
        start: usize,
        sampler: Option<Sampler>,
    ) -> Self {
        Constrained {
            grammar,
            vocab,
            matcher: Matcher::new(grammar, vocab),
            allowed: TokenSet::new(vocab.len()),
            start,
            seen: Vec::new(),
            sampler,
        }
    }

    /// Brings the matcher to `generated`. After a rejected draft the history
    /// is shorter than what was accepted, so the matcher starts over.
    fn sync(&mut self, generated: &[u32]) {
        if !generated.starts_with(&self.seen) {
            self.matcher = Matcher::new(self.grammar, self.vocab);
            self.seen.clear();
        }
        for &t in &generated[self.seen.len()..] {
            // A token outside the grammar cannot be chosen here, so a failure
            // would mean the history came from elsewhere; it is skipped.
            let _ = self.matcher.accept(t);
        }
        self.seen.clear();
        self.seen.extend_from_slice(generated);
    }
}

impl<M: Target> Policy<M> for Constrained<'_> {
    type Scores = Vec<f32>;

    fn score(
        &self,
        model: &M,
        state: &mut M::State,
        tokens: &[u32],
        all_rows: bool,
    ) -> (Vec<f32>, Vec<f32>) {
        model.logits(state, tokens, all_rows)
    }

    fn choose(&mut self, model: &M, scores: &Vec<f32>, row: usize, history: &[u32]) -> u32 {
        self.sync(&history[self.start.min(history.len())..]);
        self.matcher.allowed(&mut self.allowed);
        if self.allowed.count() == 0 {
            return self
                .vocab
                .stop_tokens()
                .first()
                .copied()
                .unwrap_or_default();
        }
        let vocab = model.n_vocab();
        let mut logits = scores[row * vocab..][..vocab].to_vec();
        for (id, l) in logits.iter_mut().enumerate() {
            if !self.allowed.contains(id as u32) {
                *l = f32::NEG_INFINITY;
            }
        }
        match &mut self.sampler {
            Some(s) => s.sample(&logits, history),
            None => argmax(&logits),
        }
    }
}
