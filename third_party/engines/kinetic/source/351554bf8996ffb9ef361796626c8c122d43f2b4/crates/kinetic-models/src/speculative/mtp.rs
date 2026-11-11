use super::{argmax, Drafter, Lookup, Target};
use crate::{Model, MtpState};

/// A target model with a prediction block, which [`MtpDrafter`] drafts with.
/// The methods mirror those of [`Model`].
pub trait Predictor: Target {
    type MtpState;

    /// `None` if the model has no prediction block.
    fn new_mtp_state(&self) -> Option<Self::MtpState>;

    /// Empties `state` for a new sequence; by default by making a new one.
    fn clear_mtp_state(&self, state: &mut Self::MtpState) {
        *state = self
            .new_mtp_state()
            .expect("the state was made for a model with a prediction block");
    }

    /// Positions fed to the block so far.
    fn mtp_len(&self, state: &Self::MtpState) -> usize;

    /// See [`Model::mtp_forward`].
    fn mtp_forward(&self, state: &mut Self::MtpState, hidden: &[f32], tokens: &[u32]) -> Vec<f32>;

    /// The greedy token of the output head restricted to its first `vocab`
    /// rows, for a hidden state from [`Predictor::mtp_forward`]; see
    /// [`Model::draft_logits`].
    fn draft_token(&self, state: &mut Self::MtpState, hidden: &[f32], vocab: usize) -> u32;

    fn mtp_checkpoint(&self, state: &mut Self::MtpState);

    /// See [`Model::mtp_rollback`].
    fn mtp_rollback(&self, state: &mut Self::MtpState, fed: usize, keep: usize);
}

impl Predictor for Model<'_> {
    type MtpState = MtpState;

    fn new_mtp_state(&self) -> Option<MtpState> {
        Model::new_mtp_state(self)
    }

    fn mtp_len(&self, state: &MtpState) -> usize {
        state.len()
    }

    fn mtp_forward(&self, state: &mut MtpState, hidden: &[f32], tokens: &[u32]) -> Vec<f32> {
        Model::mtp_forward(self, state, hidden, tokens)
    }

    fn draft_token(&self, _state: &mut MtpState, hidden: &[f32], vocab: usize) -> u32 {
        argmax(&self.draft_logits(hidden, vocab))
    }

    fn mtp_checkpoint(&self, state: &mut MtpState) {
        Model::mtp_checkpoint(self, state);
    }

    fn mtp_rollback(&self, state: &mut MtpState, fed: usize, keep: usize) {
        Model::mtp_rollback(self, state, fed, keep);
    }
}

/// Drafts with the model's own prediction block, which reads the final
/// hidden state at a position and the token after it and predicts the next
/// one. Longer drafts chain the block on its own output. A context lookup is
/// tried first, since a match there is free and usually long.
pub struct MtpDrafter<M: Predictor> {
    state: M::MtpState,
    /// Hidden states of positions not yet fed to the block.
    pending: Vec<f32>,
    /// Most tokens drafted by chaining the block.
    pub depth: usize,
    /// Drafts only consider this many tokens of the vocabulary.
    pub draft_vocab: usize,
    pub lookup: Option<Lookup>,
}

impl<M: Predictor> MtpDrafter<M> {
    /// `None` if the model has no prediction block.
    pub fn new(model: &M) -> Option<Self> {
        Some(MtpDrafter {
            state: model.new_mtp_state()?,
            pending: Vec::new(),
            depth: 2,
            draft_vocab: 32768,
            // Only long matches: they beat the block on repeated text and
            // rarely misfire on new text.
            lookup: Some(Lookup {
                max_ngram: 4,
                min_ngram: 3,
            }),
        })
    }
}

impl<M: Predictor> Drafter<M> for MtpDrafter<M> {
    fn observe(&mut self, _model: &M, _tokens: &[u32], hidden: &[f32]) {
        self.pending.extend_from_slice(hidden);
    }

    fn propose(&mut self, model: &M, context: &[u32], limit: usize) -> Vec<u32> {
        // The block's cache must cover every position, so it is fed even
        // when the lookup supplies the draft.
        let d = model.n_embd();
        let n = self.pending.len() / d;
        if n == 0 {
            return Vec::new();
        }
        // The pending states are those of the positions before the last
        // token of `context`, which may start past what the block has seen
        // when a sequence resumes from a cached prefix.
        let following = &context[context.len() - n..];
        let mut hidden = model.mtp_forward(&mut self.state, &self.pending, following);
        self.pending.clear();

        if let Some(draft) = self
            .lookup
            .as_mut()
            .map(|l| Drafter::<M>::propose(l, model, context, limit))
        {
            if !draft.is_empty() {
                return draft;
            }
        }

        let mut draft = vec![model.draft_token(&mut self.state, &hidden, self.draft_vocab)];
        let depth = self.depth.min(limit);
        if depth > 1 {
            model.mtp_checkpoint(&mut self.state);
            for _ in 1..depth {
                hidden = model.mtp_forward(&mut self.state, &hidden, &draft[draft.len() - 1..]);
                draft.push(model.draft_token(&mut self.state, &hidden, self.draft_vocab));
            }
            model.mtp_rollback(&mut self.state, depth - 1, 0);
        }
        draft
    }

    fn reset(&mut self, model: &M) {
        model.clear_mtp_state(&mut self.state);
        self.pending.clear();
    }
}
