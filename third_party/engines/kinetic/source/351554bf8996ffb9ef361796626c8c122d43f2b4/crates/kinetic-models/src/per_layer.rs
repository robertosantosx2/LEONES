//! Per-layer token inputs, as in Gemma 4: besides the shared embedding,
//! every layer gets a small input of its own, built from a second token
//! table and a projection of the embedding, which it adds back to the
//! residual stream through a gated bottleneck.

use std::f32::consts::FRAC_1_SQRT_2;

use kinetic_cpu::{matmul, pool, rms_norm};
use kinetic_quant::Matrix;

use crate::blocks::gelu;
use crate::model::embed_into;

pub(crate) struct PerLayer<'a> {
    /// `width` values per layer for every token.
    pub embd: Matrix<'a>,
    /// From the scaled embedding to `width` values per layer.
    pub proj: Matrix<'a>,
    pub proj_norm: Vec<f32>,
    pub width: usize,
    pub layers: Vec<LayerInput<'a>>,
}

/// How one layer folds its input into the residual stream.
pub(crate) struct LayerInput<'a> {
    pub gate: Matrix<'a>,
    pub proj: Matrix<'a>,
    pub norm: Vec<f32>,
    /// Multiplies the whole residual stream once the layer is done.
    pub scale: f32,
}

impl PerLayer<'_> {
    /// The inputs of every layer for the rows `x` embedding `tokens`:
    /// `layers * width` values per row, layer by layer.
    pub fn inputs(&self, tokens: &[u32], x: &[f32], eps: f32) -> Vec<f32> {
        let all = self.embd.cols;
        let mut from_token = vec![0.0; tokens.len() * all];
        embed_into(
            &self.embd,
            Some((self.width as f32).sqrt()),
            tokens,
            &mut from_token,
        );
        let mut out = vec![0.0; tokens.len() * all];
        matmul(&self.proj, x, &mut out);
        let scale = 1.0 / (self.proj.cols as f32).sqrt();
        pool::for_each_chunk(&mut out, self.width, |i, row| {
            row.iter_mut().for_each(|v| *v *= scale);
            rms_norm(row, &self.proj_norm, eps);
            let token = &from_token[i * self.width..][..self.width];
            row.iter_mut()
                .zip(token)
                .for_each(|(v, t)| *v = (*v + t) * FRAC_1_SQRT_2);
        });
        out
    }

    /// Adds layer `i`'s input to the rows `x` and applies its scale.
    pub fn apply(&self, i: usize, x: &mut [f32], inputs: &[f32], eps: f32) {
        let l = &self.layers[i];
        let (d, w, n_layer) = (l.proj.rows, self.width, self.layers.len());
        let n = x.len() / d;
        let mut g = vec![0.0; n * w];
        matmul(&l.gate, x, &mut g);
        for (t, row) in g.chunks_exact_mut(w).enumerate() {
            let input = &inputs[(t * n_layer + i) * w..][..w];
            row.iter_mut()
                .zip(input)
                .for_each(|(g, v)| *g = gelu(*g) * v);
        }
        let mut y = vec![0.0; n * d];
        matmul(&l.proj, &g, &mut y);
        pool::for_each_chunk(&mut y, d, |_, row| rms_norm(row, &l.norm, eps));
        pool::for_each_chunk(x, d, |t, row| {
            row.iter_mut()
                .zip(&y[t * d..])
                .for_each(|(x, y)| *x = (*x + y) * l.scale);
        });
    }
}
