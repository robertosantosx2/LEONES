//! BERT-style encoders: BERT itself (with MiniLM and BGE) and Nomic BERT,
//! which replaces the learned positions with rotary ones and the GELU
//! feed-forward with a gated SiLU one. Every token attends to every token of
//! its own sequence, and each sublayer adds its input back before a
//! LayerNorm with bias.

use std::ops::Range;

use kinetic_cpu::{axpy, dot, dots, matmul, matmul_many, sigmoid, softmax};
use kinetic_quant::{dequantize_row, Matrix};
use rayon::prelude::*;

use super::{Body, Family};
use crate::blocks::SwiGlu;
use crate::loader::Loader;
use crate::LoadError;

/// Tensors of related encoders that these layers have no place for.
const UNSUPPORTED: &[&str] = &[
    "blk.0.attn_q_norm.weight",
    "blk.0.attn_k_norm.weight",
    "blk.0.attn_norm_2.weight",
    "blk.0.ffn_gate_inp.weight",
];

pub(crate) struct Encoder<'a> {
    n_embd: usize,
    n_head: usize,
    head_dim: usize,
    eps: f32,
    tokens: Matrix<'a>,
    /// Learned absolute positions, one row per position.
    positions: Option<Matrix<'a>>,
    /// Added to every token: all input is segment "A".
    token_type: Option<Vec<f32>>,
    embd_norm: LayerNorm,
    rotary: Option<Rotary>,
    layers: Vec<Layer<'a>>,
}

struct LayerNorm {
    weight: Vec<f32>,
    bias: Vec<f32>,
}

struct Layer<'a> {
    /// One fused projection with outputs `[q | k | v]`, or three.
    qkv: Vec<Matrix<'a>>,
    q_bias: Option<Vec<f32>>,
    k_bias: Option<Vec<f32>>,
    v_bias: Option<Vec<f32>>,
    o: Matrix<'a>,
    o_bias: Option<Vec<f32>>,
    attn_norm: LayerNorm,
    ffn: Ffn<'a>,
    out_norm: LayerNorm,
}

enum Ffn<'a> {
    Gelu {
        up: Matrix<'a>,
        up_bias: Option<Vec<f32>>,
        down: Matrix<'a>,
        down_bias: Option<Vec<f32>>,
    },
    Gated(SwiGlu<'a>),
}

/// Neox-layout rotary embedding over whole heads.
struct Rotary {
    base: f32,
}

pub(crate) const FAMILY: Family = Family {
    names: &["bert", "nomic-bert"],
    body: Body::Encoder(load),
    output_norm: "output_norm.weight",
    sqrt_embd_scale: false,
    logit_scale: false,
};

pub(crate) fn load<'a>(l: &Loader<'a>, arch: &str) -> Result<Encoder<'a>, LoadError> {
    if let Some(name) = UNSUPPORTED.iter().find(|n| l.header().tensor(n).is_some()) {
        return Err(LoadError(format!("tensor {name} is not supported yet")));
    }
    let nomic = arch == "nomic-bert";
    let d = l.usize("embedding_length")?;
    let n_layer = l.usize("block_count")?;
    let n_head = l.usize("attention.head_count")?;
    if l.usize_or("attention.head_count_kv", n_head)? != n_head || !d.is_multiple_of(n_head) {
        return Err(LoadError(
            "grouped heads are not supported in encoders".into(),
        ));
    }
    let head_dim = d / n_head;
    if nomic && l.usize_or("rope.dimension_count", head_dim)? != head_dim {
        return Err(LoadError(
            "partial rotary is not supported in encoders".into(),
        ));
    }
    let n_ff = l.usize("feed_forward_length")?;
    let n_ctx_train = l.usize("context_length")?;
    let eps = l.f32("attention.layer_norm_epsilon")?;
    let rows = |name: &str| l.header().tensor(name).map(|t| t.dims[1] as usize);

    let n_vocab = rows("token_embd.weight")
        .ok_or_else(|| LoadError("missing tensor token_embd.weight".into()))?;
    let token_type = match rows("token_types.weight") {
        Some(n) => {
            let types = l.matrix("token_types.weight", d, n)?;
            let mut row = vec![0.0; d];
            dequantize_row(types.ty, types.data, 0, &mut row)
                .map_err(|e| LoadError(format!("token_types.weight: {e}")))?;
            Some(row)
        }
        None => None,
    };
    let positions = if nomic {
        None
    } else {
        Some(l.matrix("position_embd.weight", d, n_ctx_train)?)
    };
    let norm = |name: &str| -> Result<LayerNorm, LoadError> {
        Ok(LayerNorm {
            weight: l.vector(&format!("{name}.weight"), d)?,
            bias: l.vector(&format!("{name}.bias"), d)?,
        })
    };

    let layers = (0..n_layer)
        .map(|i| {
            let t = |s: &str| format!("blk.{i}.{s}");
            let bias = |s: &str, len| l.optional_vector(&t(s), len);
            let (qkv, [q_bias, k_bias, v_bias]) = match rows(&t("attn_qkv.weight")) {
                Some(_) => {
                    let fused = bias("attn_qkv.bias", 3 * d)?;
                    let split = |k: usize| fused.as_ref().map(|b| b[k * d..][..d].to_vec());
                    (
                        vec![l.matrix(&t("attn_qkv.weight"), d, 3 * d)?],
                        [split(0), split(1), split(2)],
                    )
                }
                None => (
                    ["attn_q", "attn_k", "attn_v"]
                        .iter()
                        .map(|p| l.matrix(&t(&format!("{p}.weight")), d, d))
                        .collect::<Result<_, _>>()?,
                    [
                        bias("attn_q.bias", d)?,
                        bias("attn_k.bias", d)?,
                        bias("attn_v.bias", d)?,
                    ],
                ),
            };
            let ffn = if nomic {
                Ffn::Gated(l.swiglu(i, d, n_ff)?)
            } else {
                Ffn::Gelu {
                    up: l.matrix(&t("ffn_up.weight"), d, n_ff)?,
                    up_bias: bias("ffn_up.bias", n_ff)?,
                    down: l.matrix(&t("ffn_down.weight"), n_ff, d)?,
                    down_bias: bias("ffn_down.bias", d)?,
                }
            };
            Ok(Layer {
                qkv,
                q_bias,
                k_bias,
                v_bias,
                o: l.matrix(&t("attn_output.weight"), d, d)?,
                o_bias: bias("attn_output.bias", d)?,
                attn_norm: norm(&t("attn_output_norm"))?,
                ffn,
                out_norm: norm(&t("layer_output_norm"))?,
            })
        })
        .collect::<Result<_, LoadError>>()?;

    Ok(Encoder {
        n_embd: d,
        n_head,
        head_dim,
        eps,
        tokens: l.matrix("token_embd.weight", d, n_vocab)?,
        positions,
        token_type,
        embd_norm: norm("token_embd_norm")?,
        rotary: nomic
            .then(|| l.f32_or("rope.freq_base", 10_000.0))
            .transpose()?
            .map(|base| Rotary { base }),
        layers,
    })
}

impl Encoder<'_> {
    pub fn n_embd(&self) -> usize {
        self.n_embd
    }

    /// The final hidden state of every token of every sequence, in order.
    /// The sequences share each weight pass but never attend to each other.
    ///
    /// Panics if a sequence is empty, or longer than the learned positions.
    pub fn forward(&self, seqs: &[&[u32]]) -> Vec<f32> {
        let mut x = self.embed(seqs);
        let spans = spans(seqs);
        let longest = seqs.iter().map(|s| s.len()).max().unwrap_or(0);
        let angles = self
            .rotary
            .as_ref()
            .map(|r| r.angles(self.head_dim, longest));
        for layer in &self.layers {
            let mut a = layer.attend(self, &x, &spans, angles.as_deref());
            add(&mut a, &x);
            self.layer_norm(&mut a, &layer.attn_norm);
            let mut y = layer.ffn.forward(&a);
            add(&mut y, &a);
            self.layer_norm(&mut y, &layer.out_norm);
            x = y;
        }
        x
    }

    fn embed(&self, seqs: &[&[u32]]) -> Vec<f32> {
        let d = self.n_embd;
        let n: usize = seqs.iter().map(|s| s.len()).sum();
        let mut x = vec![0.0; n * d];
        let mut pos_row = vec![0.0; d];
        let mut rows = x.chunks_exact_mut(d);
        for seq in seqs {
            assert!(!seq.is_empty(), "empty sequence");
            for (pos, &token) in seq.iter().enumerate() {
                let row = rows.next().expect("one row per token");
                dequantize_row(self.tokens.ty, self.tokens.data, token as usize, row)
                    .expect("embedding type");
                if let Some(t) = &self.token_type {
                    add(row, t);
                }
                if let Some(p) = &self.positions {
                    assert!(pos < p.rows, "sequence longer than {} tokens", p.rows);
                    dequantize_row(p.ty, p.data, pos, &mut pos_row).expect("position type");
                    add(row, &pos_row);
                }
            }
        }
        self.layer_norm(&mut x, &self.embd_norm);
        x
    }

    fn layer_norm(&self, x: &mut [f32], norm: &LayerNorm) {
        x.par_chunks_mut(self.n_embd)
            .for_each(|row| layer_norm(row, norm, self.eps));
    }
}

impl Layer<'_> {
    /// Self-attention within each sequence, projected back to the model
    /// width.
    fn attend(
        &self,
        enc: &Encoder,
        x: &[f32],
        spans: &[Range<usize>],
        angles: Option<&[(f32, f32)]>,
    ) -> Vec<f32> {
        let (d, hd) = (enc.n_embd, enc.head_dim);
        let n = x.len() / d;
        let [mut q, mut k, v] = self.project(x, n, d);

        if let Some(angles) = angles {
            let half = hd / 2;
            for span in spans {
                for (pos, t) in span.clone().enumerate() {
                    let angles = &angles[pos * half..][..half];
                    for m in [&mut q, &mut k] {
                        m[t * d..][..d]
                            .chunks_exact_mut(hd)
                            .for_each(|h| rotate_neox(h, angles));
                    }
                }
            }
        }

        let scale = 1.0 / (hd as f32).sqrt();
        let tasks: Vec<(usize, usize)> = (0..spans.len())
            .flat_map(|s| (0..enc.n_head).map(move |h| (s, h)))
            .collect();
        let heads: Vec<Vec<f32>> = tasks
            .par_iter()
            .map_init(Vec::new, |scores, &(s, h)| {
                let span = spans[s].clone();
                let at = |t: usize| t * d + h * hd..t * d + (h + 1) * hd;
                let mut out = vec![0.0; span.len() * hd];
                for (i, out) in span.clone().zip(out.chunks_exact_mut(hd)) {
                    let qi = &q[at(i)];
                    scores.clear();
                    let mut j = span.start;
                    while j + 4 <= span.end {
                        let s = dots::<4>(std::array::from_fn(|o| &k[at(j + o)]), qi);
                        scores.extend(s.map(|s| s * scale));
                        j += 4;
                    }
                    scores.extend((j..span.end).map(|j| dot(&k[at(j)], qi) * scale));
                    softmax(scores);
                    for (j, &w) in span.clone().zip(scores.iter()) {
                        axpy(out, w, &v[at(j)]);
                    }
                }
                out
            })
            .collect();

        let mut mixed = vec![0.0; n * d];
        for (&(s, h), out) in tasks.iter().zip(&heads) {
            for (t, src) in spans[s].clone().zip(out.chunks_exact(hd)) {
                mixed[t * d + h * hd..][..hd].copy_from_slice(src);
            }
        }
        let mut y = vec![0.0; n * d];
        matmul(&self.o, &mixed, &mut y);
        add_bias(&mut y, self.o_bias.as_deref());
        y
    }

    fn project(&self, x: &[f32], n: usize, d: usize) -> [Vec<f32>; 3] {
        let mut out = [vec![0.0; n * d], vec![0.0; n * d], vec![0.0; n * d]];
        if let [fused] = &self.qkv[..] {
            let mut qkv = vec![0.0; n * 3 * d];
            matmul(fused, x, &mut qkv);
            for (t, row) in qkv.chunks_exact(3 * d).enumerate() {
                for (k, part) in out.iter_mut().enumerate() {
                    part[t * d..][..d].copy_from_slice(&row[k * d..][..d]);
                }
            }
        } else {
            let ws: Vec<&Matrix> = self.qkv.iter().collect();
            let [q, k, v] = &mut out;
            matmul_many(&ws, x, &mut [q, k, v]);
        }
        let biases = [&self.q_bias, &self.k_bias, &self.v_bias];
        for (part, bias) in out.iter_mut().zip(biases) {
            add_bias(part, bias.as_deref());
        }
        out
    }
}

impl Ffn<'_> {
    fn forward(&self, x: &[f32]) -> Vec<f32> {
        match self {
            Ffn::Gelu {
                up,
                up_bias,
                down,
                down_bias,
            } => {
                let n = x.len() / up.cols;
                let mut h = vec![0.0; n * up.rows];
                matmul(up, x, &mut h);
                h.par_chunks_mut(up.rows).for_each(|row| {
                    if let Some(b) = up_bias {
                        add(row, b);
                    }
                    row.iter_mut().for_each(|v| *v = gelu(*v));
                });
                let mut y = vec![0.0; n * down.rows];
                matmul(down, &h, &mut y);
                add_bias(&mut y, down_bias.as_deref());
                y
            }
            Ffn::Gated(swiglu) => swiglu.forward(x),
        }
    }
}

impl Rotary {
    /// The sine and cosine of each pair's angle, `dims / 2` per position.
    fn angles(&self, dims: usize, len: usize) -> Vec<(f32, f32)> {
        (0..len)
            .flat_map(|pos| {
                (0..dims / 2).map(move |i| {
                    let theta = pos as f32 * self.base.powf(-((2 * i) as f32) / dims as f32);
                    theta.sin_cos()
                })
            })
            .collect()
    }
}

/// GELU in its tanh approximation, written as `x * sigmoid(2u)` for
/// `0.5 * x * (1 + tanh(u))` because one exponential is cheaper than tanh.
fn gelu(x: f32) -> f32 {
    const SQRT_8_OVER_PI: f32 = 1.595_769;
    x * sigmoid(SQRT_8_OVER_PI * (x + 0.044_715 * x * x * x))
}

/// Rotates element `i` with element `i + dims / 2`.
fn rotate_neox(x: &mut [f32], angles: &[(f32, f32)]) {
    let half = angles.len();
    for (i, &(sin, cos)) in angles.iter().enumerate() {
        let (a, b) = (x[i], x[i + half]);
        x[i] = a * cos - b * sin;
        x[i + half] = a * sin + b * cos;
    }
}

/// Each sequence's token range in the concatenated batch.
fn spans(seqs: &[&[u32]]) -> Vec<Range<usize>> {
    let mut start = 0;
    seqs.iter()
        .map(|s| {
            start += s.len();
            start - s.len()..start
        })
        .collect()
}

fn layer_norm(x: &mut [f32], norm: &LayerNorm, eps: f32) {
    let n = x.len() as f32;
    let mean = x.iter().sum::<f32>() / n;
    x.iter_mut().for_each(|v| *v -= mean);
    let var = x.iter().map(|v| v * v).sum::<f32>() / n;
    let scale = 1.0 / (var + eps).sqrt();
    for ((v, w), b) in x.iter_mut().zip(&norm.weight).zip(&norm.bias) {
        *v = *v * scale * w + b;
    }
}

fn add(y: &mut [f32], x: &[f32]) {
    y.iter_mut().zip(x).for_each(|(y, x)| *y += x);
}

fn add_bias(y: &mut [f32], bias: Option<&[f32]>) {
    if let Some(b) = bias {
        y.chunks_exact_mut(b.len()).for_each(|row| add(row, b));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn layer_norm_centres_and_scales() {
        let norm = LayerNorm {
            weight: vec![2.0; 4],
            bias: vec![1.0; 4],
        };
        let mut x = [1.0, 2.0, 3.0, 4.0];
        layer_norm(&mut x, &norm, 0.0);
        let s = 1.0 / 1.25f32.sqrt();
        let want = [-1.5, -0.5, 0.5, 1.5].map(|v| v * s * 2.0 + 1.0);
        for (x, w) in x.iter().zip(want) {
            assert!((x - w).abs() < 1e-6);
        }
    }

    #[test]
    fn gelu_matches_its_tanh_form() {
        for x in [-6.0f32, -1.5, -0.1, 0.0, 0.3, 1.0, 4.0] {
            let tanh = 0.5 * x * (1.0 + (0.797_884_6 * (x + 0.044_715 * x * x * x)).tanh());
            assert!((gelu(x) - tanh).abs() < 1e-6, "{x}");
        }
    }

    #[test]
    fn rotation_at_position_zero_is_identity() {
        let angles = Rotary { base: 1000.0 }.angles(8, 2);
        let mut x: Vec<f32> = (0..8).map(|i| i as f32).collect();
        rotate_neox(&mut x, &angles[..4]);
        assert_eq!(x, (0..8).map(|i| i as f32).collect::<Vec<_>>());
        rotate_neox(&mut x, &angles[4..]);
        assert!((x[0] - (0.0 * 1f32.cos() - 4.0 * 1f32.sin())).abs() < 1e-6);
    }
}
