//! The drafts every backend decodes with.

use kinetic_models::speculative::{
    Decoder, Drafter, Ensemble, Lookup, MtpDrafter, Predictor, SessionIndex,
};

/// One of the drafters a backend lets compete.
pub enum Source<M: Predictor> {
    /// Repeats from the context.
    Lookup(Lookup),
    /// Repeats from everything earlier requests saw.
    Session(SessionIndex),
    /// The model's own prediction block.
    Mtp(MtpDrafter<M>),
}

impl<M: Predictor> Drafter<M> for Source<M> {
    fn observe(&mut self, model: &M, tokens: &[u32], hidden: &[f32]) {
        match self {
            Source::Lookup(d) => Drafter::<M>::observe(d, model, tokens, hidden),
            Source::Session(d) => Drafter::<M>::observe(d, model, tokens, hidden),
            Source::Mtp(d) => d.observe(model, tokens, hidden),
        }
    }

    fn propose(&mut self, model: &M, context: &[u32], limit: usize) -> Vec<u32> {
        match self {
            Source::Lookup(d) => Drafter::<M>::propose(d, model, context, limit),
            Source::Session(d) => Drafter::<M>::propose(d, model, context, limit),
            Source::Mtp(d) => d.propose(model, context, limit),
        }
    }

    fn reset(&mut self, model: &M) {
        match self {
            Source::Lookup(d) => Drafter::<M>::reset(d, model),
            Source::Session(d) => Drafter::<M>::reset(d, model),
            Source::Mtp(d) => d.reset(model),
        }
    }
}

/// A decoder whose drafts come from the context, from everything earlier
/// requests saw and from the model's prediction block when it has one,
/// whichever has lately been right most.
pub fn decoder<M: Predictor>(model: &M) -> Decoder<Ensemble<Source<M>>> {
    let mut sources = vec![
        Source::Lookup(Lookup::default()),
        Source::Session(SessionIndex::default()),
    ];
    let mtp = MtpDrafter::new(model).map(|mut d| {
        d.lookup = None;
        Source::Mtp(d)
    });
    let has_mtp = mtp.is_some();
    sources.extend(mtp);
    let mut decoder = Decoder::new(Ensemble::new(sources));
    if has_mtp {
        // The block's drafts are cheap and usually right.
        decoder.max_pause = 0;
    }
    decoder
}
