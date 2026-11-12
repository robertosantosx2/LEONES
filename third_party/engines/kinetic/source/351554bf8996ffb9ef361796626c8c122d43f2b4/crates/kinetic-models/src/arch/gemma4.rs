//! Gemma 4. Sliding-window and full-attention layers with their own head
//! sizes and rotary bases, GeGLU feed-forwards of per-layer widths and
//! per-layer token inputs. The last layers project no keys or values of
//! their own and attend over those of the last earlier layer of their kind.
//! Image rows go in through [`crate::Input::Image`]: causal like text, at
//! consecutive positions, with the padding token's per-layer input.

use super::{Basics, Family, Stack};
use crate::blocks::{Activation, Attention, Gate, Mixer, Rope, RopeLayout, SharedKv, SwiGlu};
use crate::loader::Loader;
use crate::model::Layer;
use crate::per_layer::{LayerInput, PerLayer};
use crate::LoadError;

pub(crate) const FAMILY: Family = Family {
    sqrt_embd_scale: true,
    ..Family::decoder(&["gemma4"], build)
};

fn build<'a>(l: &Loader<'a>, b: &Basics) -> Result<Stack<'a>, LoadError> {
    let (d, eps) = (b.d, b.eps);
    let n_layer = l.usize("block_count")?;
    let n_head = l.usize("attention.head_count")?;
    let n_head_kv = l.usize("attention.head_count_kv")?;
    if n_head_kv == 0 || !n_head.is_multiple_of(n_head_kv) {
        return Err(LoadError("heads do not split into groups".into()));
    }
    let n_ff = l.array("feed_forward_length", n_layer, |v| {
        v.as_u64().map(|n| n as usize)
    })?;
    let sliding = l.array("attention.sliding_window_pattern", n_layer, |v| v.as_bool())?;
    let window = l.usize("attention.sliding_window")?;
    let shared = l.usize_or("attention.shared_kv_layers", 0)?;
    let first_shared = n_layer
        .checked_sub(shared)
        .ok_or_else(|| LoadError("more shared layers than layers".into()))?;
    // a shared layer reads the last unshared layer of its kind
    let source: Vec<Option<usize>> = (0..n_layer)
        .map(|i| {
            (i >= first_shared)
                .then(|| (0..first_shared).rev().find(|&j| sliding[j] == sliding[i]))
                .flatten()
        })
        .collect();
    let head_full = l.usize("attention.key_length")?;
    let head_swa = l.usize("attention.key_length_swa")?;
    let factors = l.optional_vector("rope_freqs.weight", head_full / 2)?;
    let width = l.usize("embedding_length_per_layer_input")?;

    let mut layers = Vec::with_capacity(n_layer);
    let mut inputs = Vec::with_capacity(n_layer);
    for i in 0..n_layer {
        let t = |s: &str| format!("blk.{i}.{s}");
        let (head_dim, rope) = if sliding[i] {
            let rope = Rope {
                dims: l.usize_or("rope.dimension_count_swa", head_swa)?,
                base: l.f32_or("rope.freq_base_swa", 10_000.0)?,
                factors: None,
                layout: RopeLayout::Neox,
                mscale: 1.0,
            };
            (head_swa, rope)
        } else {
            let rope = Rope {
                dims: l.usize_or("rope.dimension_count", head_full)?,
                base: l.f32("rope.freq_base")?,
                factors: factors.clone(),
                layout: RopeLayout::Neox,
                mscale: 1.0,
            };
            (head_full, rope)
        };
        let (q_dim, kv_dim) = (n_head * head_dim, n_head_kv * head_dim);
        let kv_layer = source[i].unwrap_or(i);
        let kv = |s: &str| format!("blk.{kv_layer}.{s}");
        let attention = Attention {
            q: l.matrix(&t("attn_q.weight"), d, q_dim)?,
            k: l.matrix(&kv("attn_k.weight"), d, kv_dim)?,
            v: l.matrix(&kv("attn_v.weight"), d, kv_dim)?,
            o: l.matrix(&t("attn_output.weight"), q_dim, d)?,
            folding: None,
            gate: Gate::None,
            q_bias: None,
            k_bias: None,
            v_bias: None,
            q_norm: Some(l.vector(&t("attn_q_norm.weight"), head_dim)?),
            k_norm: Some(l.vector(&kv("attn_k_norm.weight"), head_dim)?),
            norm_after_rope: false,
            n_head,
            n_head_kv,
            head_dim,
            rope,
            window: sliding[i].then_some(window),
            // the query norm stands in for the usual 1/sqrt(head_dim)
            scale: Some(1.0),
            v_norm: Some(vec![1.0; head_dim]),
            shared_kv: match source[i] {
                Some(j) => SharedKv::Borrows(j),
                None if source.contains(&Some(i)) => SharedKv::Lends,
                None => SharedKv::No,
            },
            eps,
        };
        layers.push(Layer {
            mixer_norm: Some(l.vector(&t("attn_norm.weight"), d)?),
            mixer: Mixer::Attention(attention),
            mixer_out_norm: Some(l.vector(&t("post_attention_norm.weight"), d)?),
            ffn_norm: Some(l.vector(&t("ffn_norm.weight"), d)?),
            ffn: Some(SwiGlu {
                activation: Activation::Gelu,
                ..l.swiglu(i, d, n_ff[i])?
            }),
            experts: None,
            ffn_out_norm: Some(l.vector(&t("post_ffw_norm.weight"), d)?),
            residual_scale: None,
        });
        inputs.push(LayerInput {
            gate: l.matrix(&t("inp_gate.weight"), d, width)?,
            proj: l.matrix(&t("proj.weight"), width, d)?,
            norm: l.vector(&t("post_norm.weight"), d)?,
            scale: l.vector(&t("layer_output_scale.weight"), 1)?[0],
        });
    }
    let n_vocab = l
        .header()
        .tensor("per_layer_token_embd.weight")
        .map(|t| t.dims[1] as usize)
        .ok_or_else(|| LoadError("missing tensor per_layer_token_embd.weight".into()))?;
    let per_layer = PerLayer {
        embd: l.matrix("per_layer_token_embd.weight", n_layer * width, n_vocab)?,
        proj: l.matrix("per_layer_model_proj.weight", d, n_layer * width)?,
        proj_norm: l.vector("per_layer_proj_norm.weight", width)?,
        width,
        layers: inputs,
    };
    Ok(Stack {
        layers,
        mtp: None,
        per_layer: Some(per_layer),
    })
}
