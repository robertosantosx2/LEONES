//! LFM3: gated short convolutions and gated attention, where attention
//! layers alternate between a sliding window and the full context. Every
//! block is sandwiched between pre- and post-norms.

use kinetic_gguf::Value;

use super::Family;
use crate::blocks::{Attention, Gate, Mixer, Rope, RopeLayout, SharedKv, ShortConv};
use crate::loader::Loader;
use crate::model::Layer;
use crate::LoadError;

pub(crate) const FAMILY: Family =
    Family::decoder(&["lfm3"], |l, b| Ok(layers(l, b.d, b.eps)?.into()));

pub(crate) fn layers<'a>(l: &Loader<'a>, d: usize, eps: f32) -> Result<Vec<Layer<'a>>, LoadError> {
    let n_layer = l.usize("block_count")?;
    // A layer with no KV heads is a short-convolution layer.
    let n_head_kv = l.array("attention.head_count_kv", n_layer, |v| {
        v.as_u64().map(|n| n as usize)
    })?;
    let swa = l.array("attention.sliding_window_pattern", n_layer, |v: &Value| {
        v.as_bool().or_else(|| v.as_u64().map(|n| n != 0))
    })?;
    let n_head = l.usize("attention.head_count")?;
    let head_dim = l.usize("attention.key_length")?;
    if l.usize("rope.dimension_count")? != head_dim {
        return Err(LoadError(
            "partial rotary embeddings are not supported".into(),
        ));
    }
    let (base, base_swa) = (l.f32("rope.freq_base")?, l.f32("rope.freq_base_swa")?);
    let window = l.usize("attention.sliding_window")?;
    let taps = l.usize("shortconv.l_cache")?;
    let n_ff = l.usize("feed_forward_length")?;
    // Frequency divisors apply to full-attention layers only.
    let freq_factors = l.vector("rope_freqs.weight", head_dim / 2)?;

    (0..n_layer)
        .map(|i| {
            let t = |s: &str| format!("blk.{i}.{s}");
            let kv = n_head_kv[i];
            let mixer = if kv == 0 {
                Mixer::ShortConv(ShortConv {
                    in_proj: l.matrix(&t("shortconv.in_proj.weight"), d, 3 * d)?,
                    conv: l.vector(&t("shortconv.conv.weight"), taps * d)?,
                    taps,
                    out_proj: l.matrix(&t("shortconv.out_proj.weight"), d, d)?,
                })
            } else {
                if !n_head.is_multiple_of(kv) {
                    return Err(LoadError(format!(
                        "layer {i}: heads do not split into groups"
                    )));
                }
                let rope = if swa[i] {
                    Rope {
                        dims: head_dim,
                        base: base_swa,
                        factors: None,
                        layout: RopeLayout::Neox,
                        mscale: 1.0,
                    }
                } else {
                    Rope {
                        dims: head_dim,
                        base,
                        factors: Some(freq_factors.clone()),
                        layout: RopeLayout::Neox,
                        mscale: 1.0,
                    }
                };
                Mixer::Attention(Attention {
                    folding: None,
                    q: l.matrix(&t("attn_q.weight"), d, n_head * head_dim)?,
                    k: l.matrix(&t("attn_k.weight"), d, kv * head_dim)?,
                    v: l.matrix(&t("attn_v.weight"), d, kv * head_dim)?,
                    o: l.matrix(&t("attn_output.weight"), n_head * head_dim, d)?,
                    gate: Gate::PerHead(l.matrix(&t("attn_gate.weight"), d, n_head)?),
                    q_bias: None,
                    k_bias: None,
                    v_bias: None,
                    q_norm: Some(l.vector(&t("attn_q_norm.weight"), head_dim)?),
                    k_norm: Some(l.vector(&t("attn_k_norm.weight"), head_dim)?),
                    norm_after_rope: false,
                    n_head,
                    n_head_kv: kv,
                    head_dim,
                    rope,
                    window: swa[i].then_some(window),
                    scale: None,
                    v_norm: None,
                    shared_kv: SharedKv::No,
                    eps,
                })
            };
            Ok(Layer {
                mixer_norm: Some(l.vector(&t("attn_norm.weight"), d)?),
                mixer,
                mixer_out_norm: Some(l.vector(&t("post_attention_norm.weight"), d)?),
                ffn_norm: Some(l.vector(&t("ffn_norm.weight"), d)?),
                ffn: Some(l.swiglu(i, d, n_ff)?),
                experts: None,
                ffn_out_norm: Some(l.vector(&t("post_ffw_norm.weight"), d)?),
                residual_scale: None,
            })
        })
        .collect()
}
