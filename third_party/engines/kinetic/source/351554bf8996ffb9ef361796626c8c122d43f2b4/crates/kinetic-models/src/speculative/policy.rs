use super::{Sampler, Target};

/// How a [`Decoder`](super::Decoder) chooses each token from what the model
/// returns. Plain decoding and verification of a draft choose the same way,
/// so a policy sees the same rows and history either way.
pub trait Policy<M: Target> {
    /// What a run leaves for choosing the token after each of its rows.
    type Scores;

    /// Runs `tokens`; see [`Target::score`].
    fn score(
        &self,
        model: &M,
        state: &mut M::State,
        tokens: &[u32],
        all_rows: bool,
    ) -> (Self::Scores, Vec<f32>);

    /// Runs a tree of tokens; see [`Target::score_tree`]. `None`, having
    /// run nothing, when the model or the policy cannot.
    fn score_tree(
        &self,
        _model: &M,
        _state: &mut M::State,
        _tokens: &[u32],
        _parents: &[Option<usize>],
    ) -> Option<(Self::Scores, Vec<f32>)> {
        None
    }

    /// The token after row `row` of `scores`, which follows `history`.
    fn choose(&mut self, model: &M, scores: &Self::Scores, row: usize, history: &[u32]) -> u32;
}

/// Always the likeliest token, as the model picks it; logits need not leave
/// the device.
pub struct Greedy;

impl<M: Target> Policy<M> for Greedy {
    type Scores = M::Scores;

    fn score(
        &self,
        model: &M,
        state: &mut M::State,
        tokens: &[u32],
        all_rows: bool,
    ) -> (M::Scores, Vec<f32>) {
        model.score(state, tokens, all_rows)
    }

    fn score_tree(
        &self,
        model: &M,
        state: &mut M::State,
        tokens: &[u32],
        parents: &[Option<usize>],
    ) -> Option<(M::Scores, Vec<f32>)> {
        model.score_tree(state, tokens, parents)
    }

    fn choose(&mut self, model: &M, scores: &M::Scores, row: usize, _history: &[u32]) -> u32 {
        model.greedy(scores, row)
    }
}

impl<M: Target> Policy<M> for Sampler {
    type Scores = Vec<f32>;

    fn score(
        &self,
        model: &M,
        state: &mut M::State,
        tokens: &[u32],
        all_rows: bool,
    ) -> (Vec<f32>, Vec<f32>) {
        match self.top() {
            Some(top) => model.top_logits(state, tokens, all_rows, top),
            None => model.logits(state, tokens, all_rows),
        }
    }

    fn score_tree(
        &self,
        model: &M,
        state: &mut M::State,
        tokens: &[u32],
        parents: &[Option<usize>],
    ) -> Option<(Vec<f32>, Vec<f32>)> {
        model.logits_tree(state, tokens, parents)
    }

    fn choose(&mut self, model: &M, scores: &Vec<f32>, row: usize, history: &[u32]) -> u32 {
        let vocab = model.n_vocab();
        self.sample(&scores[row * vocab..][..vocab], history)
    }
}
