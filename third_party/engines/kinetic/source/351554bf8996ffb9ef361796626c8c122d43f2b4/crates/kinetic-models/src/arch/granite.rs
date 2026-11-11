//! Granite 4.0: Llama-style layers whose residual branches and attention
//! scores carry fixed multipliers. In the hybrid variant a layer without
//! key-value heads is a Mamba-2 mixer, and the file can turn rotary
//! positions off; in the mixture-of-experts variant routed experts, and
//! possibly a shared one, are the feed-forward.

use kinetic_gguf::Value;

use super::mamba::mamba2;
use super::moe;
use super::Family;
use crate::blocks::{Attention, Gate, Mixer, Rope, RopeLayout, SharedKv};
use crate::loader::Loader;
use crate::model::Layer;
use crate::LoadError;

pub(crate) const FAMILY: Family = Family {
    logit_scale: true,
    ..Family::decoder(&["granite", "granitehybrid", "granitemoe"], |l, b| {
        Ok(layers(l, b.d, b.eps)?.into())
    })
};

pub(crate) fn layers<'a>(l: &Loader<'a>, d: usize, eps: f32) -> Result<Vec<Layer<'a>>, LoadError> {
    let header = l.header();
    if let Some(t) = header
        .tensors
        .iter()
        .find(|t| t.name.ends_with(".bias") && !t.name.contains(".ssm_"))
    {
        return Err(LoadError(format!("tensor {} is not supported yet", t.name)));
    }
    let n_layer = l.usize("block_count")?;
    let n_head = l.usize("attention.head_count")?;
    let n_head_kv = match l.hparam("attention.head_count_kv")?.as_array() {
        Some(_) => l.array("attention.head_count_kv", n_layer, |v| {
            v.as_u64().map(|n| n as usize)
        })?,
        None => vec![l.usize("attention.head_count_kv")?; n_layer],
    };
    let head_dim = l.usize_or("attention.key_length", d / n_head)?;
    let rotary = header
        .arch_key("rope.scaling.finetuned")
        .and_then(Value::as_bool)
        .unwrap_or(true);
    let rope_dims = match rotary {
        true => l.usize_or("rope.dimension_count", head_dim)?,
        false => 0,
    };
    let base = l.f32_or("rope.freq_base", 10_000.0)?;
    let factors = l.optional_vector("rope_freqs.weight", rope_dims / 2)?;
    let multiplier = |key| Ok::<_, LoadError>(Some(l.f32_or(key, 0.0)?).filter(|&s| s != 0.0));
    let scale = multiplier("attention.scale")?;
    let residual_scale = multiplier("residual_scale")?;
    let n_ff = l.usize("feed_forward_length")?;
    let routed = l.usize_or("expert_count", 0)? > 0;

    (0..n_layer)
        .map(|i| {
            let t = |s: &str| format!("blk.{i}.{s}");
            let kv = n_head_kv[i];
            let mixer = if kv == 0 {
                Mixer::Mamba2(mamba2(l, i, d, eps)?)
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
                    q_norm: None,
                    k_norm: None,
                    norm_after_rope: false,
                    n_head,
                    n_head_kv: kv,
                    head_dim,
                    rope: Rope {
                        dims: rope_dims,
                        base,
                        factors: factors.clone(),
                        layout: RopeLayout::Adjacent,
                        mscale: 1.0,
                    },
                    window: None,
                    scale,
                    v_norm: None,
                    shared_kv: SharedKv::No,
                    eps,
                })
            };
            let (ffn, experts) = match routed {
                true => (
                    moe::shared(l, i, d, n_ff)?,
                    Some(moe::routed(l, i, d, n_ff)?),
                ),
                false => (Some(l.swiglu(i, d, n_ff)?), None),
            };
            Ok(Layer {
                mixer_norm: Some(l.vector(&t("attn_norm.weight"), d)?),
                mixer,
                mixer_out_norm: None,
                ffn_norm: Some(l.vector(&t("ffn_norm.weight"), d)?),
                ffn,
                experts,
                ffn_out_norm: None,
                residual_scale,
            })
        })
        .collect()
}
