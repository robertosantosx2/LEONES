//! Qwen3.5: gated delta-rule linear attention, with gated full attention on
//! every `full_attention_interval`-th layer, and optionally a prediction
//! block stored after the last layer. Qwen3.5 MoE models have the same
//! layers with a mixture-of-experts feed-forward.

use super::{moe, Family, Stack};
use std::sync::Arc;

use crate::blocks::{Attention, DeltaNet, Folding, Gate, Mixer, Rope, RopeLayout, SharedKv};
use crate::folds::Folds;
use crate::loader::Loader;
use crate::model::{Layer, Mtp};
use crate::LoadError;

struct Dims {
    d: usize,
    eps: f32,
    n_head: usize,
    n_head_kv: usize,
    head_dim: usize,
    rope_dims: usize,
    rope_base: f32,
}

/// The folding of the weights (name, input width), if the file has any.
fn fold(
    folds: Option<&Folds>,
    weights: &[(&str, usize)],
) -> Result<Option<Arc<Folding>>, LoadError> {
    folds.map_or(Ok(None), |f| f.block(weights))
}

pub(crate) const FAMILY: Family = Family::decoder(&["qwen35", "qwen35moe"], |l, b| {
    let (layers, mtp) = load(l, b.d, b.eps, b.folds)?;
    Ok(Stack {
        layers,
        mtp,
        per_layer: None,
    })
});

pub(crate) fn load<'a>(
    l: &Loader<'a>,
    d: usize,
    eps: f32,
    folds: Option<&Folds>,
) -> Result<(Vec<Layer<'a>>, Option<Mtp<'a>>), LoadError> {
    let n_mtp = l.usize("nextn_predict_layers").unwrap_or(0);
    let n_layer = l.usize("block_count")? - n_mtp;
    let interval = l.usize("full_attention_interval")?;
    let dims = Dims {
        d,
        eps,
        n_head: l.usize("attention.head_count")?,
        n_head_kv: l.usize("attention.head_count_kv")?,
        head_dim: l.usize("attention.key_length")?,
        rope_dims: l.usize("rope.dimension_count")?,
        rope_base: l.f32("rope.freq_base")?,
    };
    let n_v_heads = l.usize("ssm.time_step_rank")?;
    let n_k_heads = l.usize("ssm.group_count")?;
    let head_k_dim = l.usize("ssm.state_size")?;
    let head_v_dim = l.usize("ssm.inner_size")? / n_v_heads;
    let conv_taps = l.usize("ssm.conv_kernel")?;

    let layers = (0..n_layer)
        .map(|i| {
            let t = |s: &str| format!("blk.{i}.{s}");
            let mixer = if (i + 1).is_multiple_of(interval) {
                Mixer::Attention(attention(l, i, &dims, folds)?)
            } else {
                let (key_dim, value_dim) = (n_k_heads * head_k_dim, n_v_heads * head_v_dim);
                let channels = 2 * key_dim + value_dim;
                Mixer::DeltaNet(DeltaNet {
                    qkv: l.matrix(&t("attn_qkv.weight"), d, channels)?,
                    z: l.matrix(&t("attn_gate.weight"), d, value_dim)?,
                    beta: l.matrix(&t("ssm_beta.weight"), d, n_v_heads)?,
                    alpha: l.matrix(&t("ssm_alpha.weight"), d, n_v_heads)?,
                    dt_bias: l.vector(&t("ssm_dt.bias"), n_v_heads)?,
                    a: l.vector(&t("ssm_a"), n_v_heads)?,
                    conv: l.vector(&t("ssm_conv1d.weight"), conv_taps * channels)?,
                    conv_taps,
                    norm: l.vector(&t("ssm_norm.weight"), head_v_dim)?,
                    out: l.matrix(&t("ssm_out.weight"), value_dim, d)?,
                    n_k_heads,
                    n_v_heads,
                    head_k_dim,
                    head_v_dim,
                    eps,
                    folding: fold(
                        folds,
                        &[
                            (&t("attn_qkv.weight"), d),
                            (&t("attn_gate.weight"), d),
                            (&t("ssm_out.weight"), value_dim),
                        ],
                    )?,
                })
            };
            layer(l, i, mixer, &dims, folds)
        })
        .collect::<Result<Vec<_>, _>>()?;

    let mtp = match n_mtp {
        0 => None,
        1 => {
            let i = n_layer;
            let t = |s: &str| format!("blk.{i}.nextn.{s}");
            let head_norm = match l.header().tensor(&t("shared_head_norm.weight")) {
                Some(_) => l.vector(&t("shared_head_norm.weight"), d)?,
                None => l.vector("output_norm.weight", d)?,
            };
            Some(Mtp {
                eh_proj: l.matrix(&t("eh_proj.weight"), 2 * d, d)?,
                embd_norm: l.vector(&t("enorm.weight"), d)?,
                hidden_norm: l.vector(&t("hnorm.weight"), d)?,
                layer: layer(
                    l,
                    i,
                    Mixer::Attention(attention(l, i, &dims, folds)?),
                    &dims,
                    folds,
                )?,
                head_norm,
            })
        }
        n => {
            return Err(LoadError(format!(
                "{n} prediction blocks are not supported"
            )))
        }
    };
    Ok((layers, mtp))
}

fn attention<'a>(
    l: &Loader<'a>,
    i: usize,
    c: &Dims,
    folds: Option<&Folds>,
) -> Result<Attention<'a>, LoadError> {
    let t = |s: &str| format!("blk.{i}.{s}");
    let (d, hd) = (c.d, c.head_dim);
    Ok(Attention {
        q: l.matrix(&t("attn_q.weight"), d, 2 * c.n_head * hd)?,
        k: l.matrix(&t("attn_k.weight"), d, c.n_head_kv * hd)?,
        v: l.matrix(&t("attn_v.weight"), d, c.n_head_kv * hd)?,
        o: l.matrix(&t("attn_output.weight"), c.n_head * hd, d)?,
        gate: Gate::Interleaved,
        q_bias: None,
        k_bias: None,
        v_bias: None,
        q_norm: Some(l.vector(&t("attn_q_norm.weight"), hd)?),
        k_norm: Some(l.vector(&t("attn_k_norm.weight"), hd)?),
        norm_after_rope: false,
        n_head: c.n_head,
        n_head_kv: c.n_head_kv,
        head_dim: hd,
        rope: Rope {
            dims: c.rope_dims,
            base: c.rope_base,
            factors: None,
            layout: RopeLayout::Neox,
            mscale: 1.0,
        },
        window: None,
        scale: None,
        v_norm: None,
        shared_kv: SharedKv::No,
        eps: c.eps,
        folding: fold(
            folds,
            &[
                (&t("attn_q.weight"), d),
                (&t("attn_k.weight"), d),
                (&t("attn_v.weight"), d),
                (&t("attn_output.weight"), c.n_head * hd),
            ],
        )?,
    })
}

fn layer<'a>(
    l: &Loader<'a>,
    i: usize,
    mixer: Mixer<'a>,
    c: &Dims,
    folds: Option<&Folds>,
) -> Result<Layer<'a>, LoadError> {
    let t = |s: &str| format!("blk.{i}.{s}");
    let (ffn, experts) = match l.header().tensor(&t("ffn_gate_inp.weight")) {
        Some(_) => {
            let n_ff = l.usize("expert_feed_forward_length")?;
            (
                moe::shared(l, i, c.d, n_ff)?,
                Some(moe::routed(l, i, c.d, n_ff)?),
            )
        }
        None => {
            let n_ff = l.usize("feed_forward_length")?;
            let mut ffn = l.swiglu(i, c.d, n_ff)?;
            ffn.folding = fold(
                folds,
                &[
                    (&t("ffn_gate.weight"), c.d),
                    (&t("ffn_up.weight"), c.d),
                    (&t("ffn_down.weight"), n_ff),
                ],
            )?;
            (Some(ffn), None)
        }
    };
    Ok(Layer {
        mixer_norm: Some(l.vector(&t("attn_norm.weight"), c.d)?),
        mixer,
        mixer_out_norm: None,
        // Despite the name, this norm feeds the FFN.
        ffn_norm: Some(l.vector(&t("post_attention_norm.weight"), c.d)?),
        ffn,
        experts,
        ffn_out_norm: None,
        residual_scale: None,
    })
}
