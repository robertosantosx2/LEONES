use super::argmax;
use crate::{Model, State};

/// A model speculative decoding can drive: it runs batches, picks greedy
/// tokens from what a run returns and rolls its state back exactly.
pub trait Target {
    type State;
    /// What a run leaves for choosing the greedy token after each of its
    /// rows; logits for [`Model`].
    type Scores;

    fn n_embd(&self) -> usize;

    fn n_vocab(&self) -> usize;

    /// Runs `tokens` in order. Returns scores for every row with `all_rows`,
    /// otherwise only for the last, and the normalized final hidden state of
    /// every token.
    fn score(
        &self,
        state: &mut Self::State,
        tokens: &[u32],
        all_rows: bool,
    ) -> (Self::Scores, Vec<f32>);

    /// Runs `tokens` like [`Target::score`] but returns the logits of each
    /// row, [`Target::n_vocab`] values apiece.
    fn logits(
        &self,
        state: &mut Self::State,
        tokens: &[u32],
        all_rows: bool,
    ) -> (Vec<f32>, Vec<f32>);

    /// [`Target::logits`] for a choice that depends only on the `top`
    /// highest logits of a row, ties going to the lower token: those must
    /// be exact, the others may be negative infinity. See [`Model::run_top`].
    fn top_logits(
        &self,
        state: &mut Self::State,
        tokens: &[u32],
        all_rows: bool,
        _top: usize,
    ) -> (Vec<f32>, Vec<f32>) {
        self.logits(state, tokens, all_rows)
    }

    /// Runs a tree of tokens in one pass after [`Target::checkpoint`]:
    /// token `i` follows token `parents[i]`, an earlier one, or the tokens
    /// already run when `None`. Returns what [`Target::score`] returns for
    /// every row, each row exactly what running its path alone gives; follow
    /// it with [`Target::rollback_rows`]. `None`, having run nothing, when
    /// the target cannot run trees.
    fn score_tree(
        &self,
        _state: &mut Self::State,
        _tokens: &[u32],
        _parents: &[Option<usize>],
    ) -> Option<(Self::Scores, Vec<f32>)> {
        None
    }

    /// [`Target::score_tree`] with the logits of each row, as
    /// [`Target::logits`] returns them.
    fn logits_tree(
        &self,
        _state: &mut Self::State,
        _tokens: &[u32],
        _parents: &[Option<usize>],
    ) -> Option<(Vec<f32>, Vec<f32>)> {
        None
    }

    /// The greedy token after row `row` of `scores`.
    fn greedy(&self, scores: &Self::Scores, row: usize) -> u32;

    /// See [`Model::checkpoint`].
    fn checkpoint(&self, state: &mut Self::State);

    /// See [`Model::rollback`].
    fn rollback(&self, state: &mut Self::State, keep: usize);

    /// See [`Model::rollback_rows`]. Targets that cannot run trees only
    /// keep leading rows.
    fn rollback_rows(&self, state: &mut Self::State, rows: &[usize]) {
        assert!(
            rows.iter().enumerate().all(|(i, &r)| i == r),
            "only leading rows can be kept"
        );
        self.rollback(state, rows.len());
    }
}

impl Target for Model<'_> {
    type State = State;
    type Scores = Vec<f32>;

    fn n_embd(&self) -> usize {
        Model::n_embd(self)
    }

    fn n_vocab(&self) -> usize {
        Model::n_vocab(self)
    }

    fn score(&self, state: &mut State, tokens: &[u32], all_rows: bool) -> (Vec<f32>, Vec<f32>) {
        self.top_logits(state, tokens, all_rows, 1)
    }

    fn logits(&self, state: &mut State, tokens: &[u32], all_rows: bool) -> (Vec<f32>, Vec<f32>) {
        let f = self.run(state, tokens, all_rows);
        (f.logits, f.hidden)
    }

    fn top_logits(
        &self,
        state: &mut State,
        tokens: &[u32],
        all_rows: bool,
        top: usize,
    ) -> (Vec<f32>, Vec<f32>) {
        let f = self.run_top(state, tokens, all_rows, top);
        (f.logits, f.hidden)
    }

    fn score_tree(
        &self,
        state: &mut State,
        tokens: &[u32],
        parents: &[Option<usize>],
    ) -> Option<(Vec<f32>, Vec<f32>)> {
        let f = self.run_tree(state, tokens, parents);
        Some((f.logits, f.hidden))
    }

    fn logits_tree(
        &self,
        state: &mut State,
        tokens: &[u32],
        parents: &[Option<usize>],
    ) -> Option<(Vec<f32>, Vec<f32>)> {
        self.score_tree(state, tokens, parents)
    }

    fn greedy(&self, scores: &Vec<f32>, row: usize) -> u32 {
        let vocab = self.n_vocab();
        argmax(&scores[row * vocab..][..vocab])
    }

    fn checkpoint(&self, state: &mut State) {
        Model::checkpoint(self, state);
    }

    fn rollback(&self, state: &mut State, keep: usize) {
        Model::rollback(self, state, keep);
    }

    fn rollback_rows(&self, state: &mut State, rows: &[usize]) {
        Model::rollback_rows(self, state, rows);
    }
}
