//! Plain transformers: Llama (with Mistral and SmolLM), Qwen2, Qwen3,
//! Gemma 3, ERNIE 4.5, Hunyuan, EXAONE 4 and OLMo 2. Every layer is
//! grouped-query attention followed by a gated feed-forward. They differ in
//! the rotary layout, in optional projection biases and query/key norms
//! (per head or across heads, before or after the rotation), in whether
//! blocks normalize their input, their output or both, and in Gemma 3's
//! GeGLU and sliding-window layers with their own rotary base.

use kinetic_gguf::Value;

use super::{Basics, Body, Family, Stack};
use crate::blocks::{Activation, Attention, Gate, Mixer, Rope, RopeLayout, SharedKv, SwiGlu};
use crate::loader::Loader;
use crate::model::Layer;
use crate::LoadError;

/// Tensors some of these files carry that the blocks have no place for.
const UNSUPPORTED: &[&str] = &[
    "output.bias",
    "blk.0.attn_qkv.weight",
    "blk.0.attn_output.bias",
    "blk.0.ffn_gate.bias",
    "blk.0.ffn_up.bias",
    "blk.0.ffn_down.bias",
    "blk.0.ffn_gate_inp.weight",
];

pub(crate) const FAMILY: Family = Family::decoder(
    &[
        "llama",
        "qwen2",
        "qwen3",
        "ernie4_5",
        "hunyuan-dense",
        "exaone4",
        "olmo2",
    ],
    build,
);

pub(crate) const GEMMA3: Family = Family {
    sqrt_embd_scale: true,
    ..Family::decoder(&["gemma3"], build)
};

/// EmbeddingGemma, run by [`super::gemma_embedding`].
pub(crate) const GEMMA_EMBEDDING: Family = Family {
    names: &["gemma-embedding"],
    body: Body::Bidirectional(build),
    ..GEMMA3
};

fn build<'a>(l: &Loader<'a>, b: &Basics) -> Result<Stack<'a>, LoadError> {
    Ok(layers(l, b.arch, b.d, b.eps)?.into())
}

pub(crate) fn layers<'a>(
    l: &Loader<'a>,
    arch: &str,
    d: usize,
    eps: f32,
) -> Result<Vec<Layer<'a>>, LoadError> {
    if let Some(name) = UNSUPPORTED.iter().find(|n| l.header().tensor(n).is_some()) {
        return Err(LoadError(format!("tensor {name} is not supported yet")));
    }
    let gemma = matches!(arch, "gemma3" | "gemma-embedding");

    let n_layer = l.usize("block_count")?;
    let n_head = l.usize("attention.head_count")?;
    let n_head_kv = l.usize_or("attention.head_count_kv", n_head)?;
    if n_head_kv == 0 || !n_head.is_multiple_of(n_head_kv) {
        return Err(LoadError("heads do not split into groups".into()));
    }
    let head_dim = l.usize_or("attention.key_length", d / n_head)?;
    if l.usize_or("attention.value_length", head_dim)? != head_dim {
        return Err(LoadError(
            "different key and value head sizes are not supported".into(),
        ));
    }
    let rope_dims = l.usize_or("rope.dimension_count", head_dim)?;
    if rope_dims > head_dim || !rope_dims.is_multiple_of(2) {
        return Err(LoadError(format!("invalid rotary size {rope_dims}")));
    }
    let n_ff = l.usize("feed_forward_length")?;
    let base = l.f32_or("rope.freq_base", 10_000.0)?;
    let layout = if matches!(arch, "llama" | "ernie4_5") {
        RopeLayout::Adjacent
    } else {
        RopeLayout::Neox
    };
    // Per-pair divisors on full-context layers, as Llama 3 stores them.
    let factors = l.optional_vector("rope_freqs.weight", rope_dims / 2)?;
    let output_norms_only = matches!(arch, "exaone4" | "olmo2");
    let input_norm = |name: &str| match output_norms_only {
        true => Ok(None),
        false => l.vector(name, d).map(Some),
    };

    let window = if gemma {
        l.usize_or("attention.sliding_window", 0)?
    } else {
        0
    };
    let sliding = if window == 0 {
        vec![false; n_layer]
    } else {
        sliding_layers(l, n_layer)?
    };
    let base_swa = l.f32_or("rope.freq_base_swa", 10_000.0)?;
    // The largest Gemma 3 scales queries by the model width per head rather
    // than the head size; folding the ratio into the query norm keeps the
    // attention block unchanged.
    let query_scale =
        (gemma && n_layer == 62).then(|| (head_dim as f32).sqrt() / ((d / n_head) as f32).sqrt());

    (0..n_layer)
        .map(|i| {
            let t = |s: &str| format!("blk.{i}.{s}");
            let (q_dim, kv_dim) = (n_head * head_dim, n_head_kv * head_dim);
            // OLMo 2 normalizes all heads of a token together.
            let (q_norm_len, k_norm_len) = match arch {
                "olmo2" => (q_dim, kv_dim),
                _ => (head_dim, head_dim),
            };
            let mut q_norm = l.optional_vector(&t("attn_q_norm.weight"), q_norm_len)?;
            if let (Some(scale), Some(w)) = (query_scale, &mut q_norm) {
                w.iter_mut().for_each(|w| *w *= scale);
            }
            let rope = if sliding[i] {
                Rope {
                    dims: rope_dims,
                    base: base_swa,
                    factors: None,
                    layout,
                    mscale: 1.0,
                }
            } else {
                Rope {
                    dims: rope_dims,
                    base,
                    factors: factors.clone(),
                    layout,
                    mscale: 1.0,
                }
            };
            let attention = Attention {
                folding: None,
                q: l.matrix(&t("attn_q.weight"), d, q_dim)?,
                k: l.matrix(&t("attn_k.weight"), d, kv_dim)?,
                v: l.matrix(&t("attn_v.weight"), d, kv_dim)?,
                o: l.matrix(&t("attn_output.weight"), q_dim, d)?,
                gate: Gate::None,
                q_bias: l.optional_vector(&t("attn_q.bias"), q_dim)?,
                k_bias: l.optional_vector(&t("attn_k.bias"), kv_dim)?,
                v_bias: l.optional_vector(&t("attn_v.bias"), kv_dim)?,
                q_norm,
                k_norm: l.optional_vector(&t("attn_k_norm.weight"), k_norm_len)?,
                norm_after_rope: arch == "hunyuan-dense",
                n_head,
                n_head_kv,
                head_dim,
                rope,
                window: sliding[i].then_some(window),
                scale: None,
                v_norm: None,
                shared_kv: SharedKv::No,
                eps,
            };
            let activation = if gemma {
                Activation::Gelu
            } else {
                Activation::Silu
            };
            Ok(Layer {
                mixer_norm: input_norm(&t("attn_norm.weight"))?,
                mixer: Mixer::Attention(attention),
                mixer_out_norm: l.optional_vector(&t("post_attention_norm.weight"), d)?,
                ffn_norm: input_norm(&t("ffn_norm.weight"))?,
                ffn: Some(SwiGlu {
                    activation,
                    ..l.swiglu(i, d, n_ff)?
                }),
                experts: None,
                ffn_out_norm: l.optional_vector(&t("post_ffw_norm.weight"), d)?,
                residual_scale: None,
            })
        })
        .collect()
}

/// Which layers attend through a sliding window: a per-layer list, or
/// every layer but each `n`-th, six by default.
fn sliding_layers(l: &Loader, n_layer: usize) -> Result<Vec<bool>, LoadError> {
    let key = "attention.sliding_window_pattern";
    if l.header().arch_key(key).and_then(Value::as_array).is_some() {
        return l.array(key, n_layer, |v: &Value| {
            v.as_bool().or_else(|| v.as_u64().map(|n| n != 0))
        });
    }
    let n = l.usize_or(key, 6)?;
    Ok((0..n_layer).map(|i| n == 0 || i % n < n - 1).collect())
}
