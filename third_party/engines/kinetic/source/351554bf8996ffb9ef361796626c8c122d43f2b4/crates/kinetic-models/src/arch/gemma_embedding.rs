//! EmbeddingGemma: Gemma 3 layers in which every token attends to the
//! whole input, or on sliding-window layers to the tokens within half a
//! window on either side.

use kinetic_cpu::rms_norm;

use crate::blocks::Mixer;
use crate::Model;

/// The normalized final hidden state of every token of `tokens`, run as
/// one sequence.
pub(crate) fn encode(model: &Model, tokens: &[u32]) -> Vec<f32> {
    let (d, eps) = (model.n_embd, model.eps);
    let mut x = model.embed(tokens);
    for layer in &model.layers {
        let Mixer::Attention(a) = &layer.mixer else {
            unreachable!("built from attention layers")
        };
        layer.forward_with(&mut x, eps, |h| a.forward_bidirectional(h));
    }
    x.chunks_exact_mut(d)
        .for_each(|row| rms_norm(row, &model.output_norm, eps));
    x
}
