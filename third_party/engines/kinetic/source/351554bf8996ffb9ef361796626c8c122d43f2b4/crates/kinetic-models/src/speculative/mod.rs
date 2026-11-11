//! Lossless speculative decoding, greedy or sampled.
//!
//! A [`Drafter`] guesses the next few tokens and the model checks the whole
//! guess in one forward pass, so every accepted token saves a pass over the
//! weights. Rejected tokens are rolled back exactly.
//!
//! Verification walks the draft and, at each row, chooses a token with the
//! same [`Policy`] plain decoding uses, from the same logits and history; the
//! draft token is accepted when the choice equals it. For a greedy policy
//! the output is plain greedy decoding, token for token. For sampling this
//! is rejection sampling against a drafter that proposes one token with
//! certainty: the draft `x` survives with probability `p(x)`, and on
//! rejection the token drawn is distributed as `p` without `x`, renormalized,
//! which is the residual distribution. Every kept token is therefore drawn
//! from exactly the distribution plain sampling draws from, with one random
//! number per token in the same order, so a seeded run reproduces plain
//! seeded sampling as long as a batch computes each row as a single token
//! would.
//!
//! A draft can branch into a tree of guesses, verified in the same single
//! pass: every row sees only its own path, and verification walks down the
//! tree, at each row choosing a token as above and moving to the child that
//! holds it. The choices are the same draws in the same order as before, so
//! nothing changes about what is kept, only how far a pass gets.
//!
//! A rejected draft costs a wider pass for nothing, so draft length follows
//! how well recent drafts did, and drafting pauses for longer and longer
//! after drafts that miss outright.

mod draft;
mod dry;
mod ensemble;
mod filters;
mod logprobs;
mod lookup;
mod mtp;
mod policy;
mod sampler;
mod session;
mod target;
#[cfg(test)]
mod tests;

pub use draft::Draft;
pub use dry::dry_breakers;
pub use ensemble::Ensemble;
pub use logprobs::{Logprobs, TokenLogprob};
pub use lookup::Lookup;
pub use mtp::{MtpDrafter, Predictor};
pub use policy::{Greedy, Policy};
pub use sampler::{Sampler, Sampling};
pub use session::SessionIndex;
pub use target::Target;

/// A source of draft tokens for target model `M`.
pub trait Drafter<M: Target> {
    /// Called with every token the model keeps, in order, and the
    /// normalized final hidden state after each, `n_embd` values per token.
    fn observe(&mut self, _model: &M, _tokens: &[u32], _hidden: &[f32]) {}

    /// Up to `limit` tokens likely to follow `context`, whose last token is
    /// about to be run.
    fn propose(&mut self, model: &M, context: &[u32], limit: usize) -> Vec<u32>;

    /// Likely continuations of `context` as a tree at most `limit` tokens
    /// deep; by default the chain [`Drafter::propose`] gives.
    fn propose_tree(&mut self, model: &M, context: &[u32], limit: usize) -> Draft {
        Draft::chain(self.propose(model, context, limit))
    }

    /// Called when the model starts a new sequence. Drafters forget what is
    /// tied to the old one's positions and keep what they learned from it.
    fn reset(&mut self, _model: &M) {}
}

impl<M: Target, D: Drafter<M> + ?Sized> Drafter<M> for Box<D> {
    fn observe(&mut self, model: &M, tokens: &[u32], hidden: &[f32]) {
        (**self).observe(model, tokens, hidden);
    }

    fn propose(&mut self, model: &M, context: &[u32], limit: usize) -> Vec<u32> {
        (**self).propose(model, context, limit)
    }

    fn propose_tree(&mut self, model: &M, context: &[u32], limit: usize) -> Draft {
        (**self).propose_tree(model, context, limit)
    }

    fn reset(&mut self, model: &M) {
        (**self).reset(model);
    }
}

/// Decodes one sequence at a time with drafts from `D`: [`Decoder::prefill`]
/// a prompt, then [`Decoder::step`] until done. [`Decoder::reset`] moves on
/// to a new sequence.
pub struct Decoder<D> {
    pub drafter: D,
    /// Most tokens proposed per step; zero never drafts.
    pub max_draft: usize,
    /// Most steps drafting pauses for after repeated misses; zero never
    /// pauses, which suits drafters whose guesses are cheap and usually right.
    pub max_pause: usize,
    /// What one more row costs a pass, as a fraction of a one-token pass.
    /// A branching draft is verified whole when its expected tokens per
    /// unit of cost beat those of its leading chain; infinity always
    /// verifies only the chain.
    pub row_cost: f32,
    draft_len: usize,
    pause: usize,
    paused_for: usize,
    /// The token the next step starts with, chosen from the scores after
    /// the context; verification that rejects a draft leaves the token it
    /// drew here.
    next: Option<u32>,
}

/// What one [`Decoder::step`] did, in one forward pass.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Step {
    /// Tokens added, including the one that needed no draft.
    pub tokens: usize,
    /// Tokens proposed; `tokens - 1` of them were accepted.
    pub drafted: usize,
}

impl<D> Decoder<D> {
    pub fn new(drafter: D) -> Self {
        Decoder {
            drafter,
            max_draft: 8,
            max_pause: 16,
            row_cost: ROW_COST,
            draft_len: 8,
            pause: 0,
            paused_for: 0,
            next: None,
        }
    }

    /// The token the next step starts with. It is chosen already, so it is
    /// final and can be shown before the step runs it.
    pub fn pending(&self) -> Option<u32> {
        self.next
    }

    /// Prepares for a new sequence; see [`Drafter::reset`].
    pub fn reset<M: Target>(&mut self, model: &M)
    where
        D: Drafter<M>,
    {
        self.drafter.reset(model);
        self.next = None;
    }

    /// Runs `tokens`, which extend the sequence `state` holds, without
    /// choosing what follows them: the leading chunks of a long prompt.
    pub fn feed<M: Target>(&mut self, model: &M, state: &mut M::State, tokens: &[u32])
    where
        D: Drafter<M>,
    {
        let (_, hidden) = model.score(state, tokens, false);
        self.drafter.observe(model, tokens, &hidden);
        self.next = None;
    }

    /// Runs the tokens of `context` from `start` on, which `state` has not
    /// run yet, and chooses the token after them for the next step.
    pub fn prefill<M: Target, P: Policy<M>>(
        &mut self,
        model: &M,
        policy: &mut P,
        state: &mut M::State,
        context: &[u32],
        start: usize,
    ) where
        D: Drafter<M>,
    {
        let tokens = &context[start..];
        let (scores, hidden) = policy.score(model, state, tokens, false);
        self.drafter.observe(model, tokens, &hidden);
        self.next = Some(policy.choose(model, &scores, 0, context));
    }

    /// Generates the next tokens: always the one already chosen, plus every
    /// draft token `policy` agrees with down one path of the draft, at most
    /// `limit` in all. They are
    /// appended to `context`, whose tokens `state` holds, and the token after
    /// them is chosen for the next step. Drafting stops after a token for
    /// which `stop` is true, and nothing is chosen after one.
    ///
    /// Panics if no token is chosen: after [`Decoder::feed`],
    /// [`Decoder::reset`] or a stop token, call [`Decoder::prefill`] first.
    pub fn step<M: Target, P: Policy<M>>(
        &mut self,
        model: &M,
        policy: &mut P,
        state: &mut M::State,
        context: &mut Vec<u32>,
        limit: usize,
        stop: impl Fn(u32) -> bool,
    ) -> Step
    where
        D: Drafter<M>,
    {
        let next = self.next.take().expect("no token chosen: prefill first");
        context.push(next);
        let len = self
            .draft_len
            .min(self.max_draft)
            .min(limit.saturating_sub(1));
        let mut draft = if stop(next) || len == 0 || self.paused_for > 0 {
            self.paused_for = self.paused_for.saturating_sub(1);
            Draft::default()
        } else {
            self.drafter.propose_tree(model, context, len)
        };
        draft.truncate(len);
        if draft.is_empty() {
            let (scores, hidden) = policy.score(model, state, &[next], false);
            self.drafter.observe(model, &[next], &hidden);
            if !stop(next) {
                self.next = Some(policy.choose(model, &scores, 0, context));
            }
            return Step {
                tokens: 1,
                drafted: 0,
            };
        }
        if !self.tree_pays(&draft) {
            draft.keep_chain();
        }

        model.checkpoint(state);
        let (mut tokens, mut parents) = batch(next, &draft);
        let tree = if draft.is_chain() {
            None
        } else {
            policy.score_tree(model, state, &tokens, &parents)
        };
        let (scores, hidden) = tree.unwrap_or_else(|| {
            draft.keep_chain();
            tokens.truncate(1 + draft.len());
            parents.truncate(1 + draft.len());
            policy.score(model, state, &tokens, true)
        });

        let mut path = vec![0];
        let mut drawn = None;
        loop {
            let row = path[path.len() - 1];
            let t = policy.choose(model, &scores, row, context);
            let child =
                (row + 1..tokens.len()).find(|&c| parents[c] == Some(row) && tokens[c] == t);
            let Some(child) = child else {
                drawn = Some(t);
                break;
            };
            context.push(t);
            path.push(child);
            if stop(t) {
                break;
            }
        }
        model.rollback_rows(state, &path);
        let d = model.n_embd();
        let kept: Vec<u32> = path.iter().map(|&r| tokens[r]).collect();
        let kept_hidden: Vec<f32> = path
            .iter()
            .flat_map(|&r| &hidden[r * d..][..d])
            .copied()
            .collect();
        self.drafter.observe(model, &kept, &kept_hidden);
        self.tune_draft_len(path.len() - 1, draft.depth());
        self.next = drawn;
        Step {
            tokens: path.len(),
            drafted: draft.len(),
        }
    }

    /// Whether verifying all of a branching `draft` beats verifying its
    /// leading chain in expected tokens per unit of cost, a pass costing
    /// one plus [`Decoder::row_cost`] per draft row.
    fn tree_pays(&self, draft: &Draft) -> bool {
        let rate = |n: usize| {
            let expected: f32 = draft.chances[..n].iter().sum();
            (1.0 + expected) / (1.0 + self.row_cost * n as f32)
        };
        rate(draft.len()) > rate(draft.chain_len())
    }

    fn tune_draft_len(&mut self, accepted: usize, drafted: usize) {
        if accepted == drafted {
            self.draft_len = (self.draft_len * 2).min(self.max_draft);
        } else {
            self.draft_len = accepted + 1;
        }
        if accepted == 0 && self.max_pause > 0 {
            self.pause = (self.pause * 2).clamp(1, self.max_pause);
            self.paused_for = self.pause;
        } else {
            self.pause = 0;
        }
    }
}

/// The default [`Decoder::row_cost`]: chains only. On the CPU a row costs
/// about 0.1 of a pass on small models and more on large ones.
// shortcut: trees stay off until row costs are measured per model on a quiet
// machine; set row_cost to use them.
const ROW_COST: f32 = f32::INFINITY;

/// The rows of one verification pass: the token about to run, then the
/// draft, each with the row it follows.
fn batch(next: u32, draft: &Draft) -> (Vec<u32>, Vec<Option<usize>>) {
    let tokens = std::iter::once(next).chain(draft.tokens.iter().copied());
    let parents =
        std::iter::once(None).chain(draft.parents.iter().map(|p| Some(p.map_or(0, |p| p + 1))));
    (tokens.collect(), parents.collect())
}

/// Index of the largest value; the lowest index wins a tie.
pub fn argmax(x: &[f32]) -> u32 {
    let mut best = 0;
    for (i, &v) in x.iter().enumerate() {
        if v > x[best] {
            best = i;
        }
    }
    best as u32
}
