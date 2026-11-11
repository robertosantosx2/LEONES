//! LFM2: gated short convolutions and attention with query and key norms,
//! each block normalizing only its input. A layer with no key-value heads
//! is a short-convolution layer. LFM2 MoE swaps the feed-forward of all but
//! the leading layers for sigmoid-routed experts.

use super::{moe, Family};
use crate::blocks::{Attention, Gate, Mixer, Rope, RopeLayout, SharedKv, ShortConv};
use crate::loader::Loader;
use crate::model::Layer;
use crate::LoadError;

pub(crate) const FAMILY: Family = Family {
    output_norm: "token_embd_norm.weight",
    ..Family::decoder(&["lfm2", "lfm2moe"], |l, b| {
        Ok(layers(l, b.d, b.eps)?.into())
    })
};

pub(crate) fn layers<'a>(l: &Loader<'a>, d: usize, eps: f32) -> Result<Vec<Layer<'a>>, LoadError> {
    let n_layer = l.usize("block_count")?;
    let n_head_kv = l.array("attention.head_count_kv", n_layer, |v| {
        v.as_u64().map(|n| n as usize)
    })?;
    let n_head = l.usize("attention.head_count")?;
    let head_dim = l.usize_or("attention.key_length", d / n_head)?;
    let base = l.f32("rope.freq_base")?;
    let window = Some(l.usize_or("attention.sliding_window", 0)?).filter(|&w| w > 0);
    let taps = l.usize("shortconv.l_cache")?;
    let n_ff = l.usize("feed_forward_length")?;
    let n_ff_exp = l.usize_or("expert_feed_forward_length", n_ff)?;

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
                Mixer::Attention(Attention {
                    folding: None,
                    q: l.matrix(&t("attn_q.weight"), d, n_head * head_dim)?,
                    k: l.matrix(&t("attn_k.weight"), d, kv * head_dim)?,
                    v: l.matrix(&t("attn_v.weight"), d, kv * head_dim)?,
                    o: l.matrix(&t("attn_output.weight"), n_head * head_dim, d)?,
                    gate: Gate::None,
                    q_bias: None,
                    k_bias: None,
                    v_bias: None,
                    q_norm: Some(l.vector(&t("attn_q_norm.weight"), head_dim)?),
                    k_norm: Some(l.vector(&t("attn_k_norm.weight"), head_dim)?),
                    norm_after_rope: false,
                    n_head,
                    n_head_kv: kv,
                    head_dim,
                    rope: Rope {
                        dims: head_dim,
                        base,
                        factors: None,
                        layout: RopeLayout::Neox,
                        mscale: 1.0,
                    },
                    window,
                    scale: None,
                    v_norm: None,
                    shared_kv: SharedKv::No,
                    eps,
                })
            };
            let (ffn, experts) = match l.header().tensor(&t("ffn_gate_inp.weight")) {
                Some(_) => (None, Some(moe::routed(l, i, d, n_ff_exp)?)),
                None => (Some(l.swiglu(i, d, n_ff)?), None),
            };
            Ok(Layer {
                mixer_norm: Some(l.vector(&t("attn_norm.weight"), d)?),
                mixer,
                mixer_out_norm: None,
                ffn_norm: Some(l.vector(&t("ffn_norm.weight"), d)?),
                ffn,
                experts,
                ffn_out_norm: None,
                residual_scale: None,
            })
        })
        .collect()
}
