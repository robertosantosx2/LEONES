//! Falcon-H1: every layer runs attention and a Mamba-2 mixer side by side
//! on the same normalized input and adds both outputs to the residual
//! stream. The GGUF converter folds the model's multipliers into its
//! weights.

use super::mamba::mamba2;
use super::Family;
use crate::blocks::{Attention, Gate, Mixer, Rope, RopeLayout, SharedKv};
use crate::loader::Loader;
use crate::model::Layer;
use crate::LoadError;

pub(crate) const FAMILY: Family =
    Family::decoder(&["falcon-h1"], |l, b| Ok(layers(l, b.d, b.eps)?.into()));

pub(crate) fn layers<'a>(l: &Loader<'a>, d: usize, eps: f32) -> Result<Vec<Layer<'a>>, LoadError> {
    let n_layer = l.usize("block_count")?;
    let n_head = l.usize("attention.head_count")?;
    let n_head_kv = l.usize("attention.head_count_kv")?;
    if n_head_kv == 0 || !n_head.is_multiple_of(n_head_kv) {
        return Err(LoadError("heads do not split into groups".into()));
    }
    let head_dim = l.usize_or("attention.key_length", d / n_head)?;
    let rope_dims = l.usize_or("rope.dimension_count", head_dim)?;
    let base = l.f32("rope.freq_base")?;
    let scale = Some(l.f32_or("attention.scale", 0.0)?).filter(|&s| s != 0.0);
    let n_ff = l.usize("feed_forward_length")?;
    let (q_dim, kv_dim) = (n_head * head_dim, n_head_kv * head_dim);

    (0..n_layer)
        .map(|i| {
            let t = |s: &str| format!("blk.{i}.{s}");
            let attention = Attention {
                folding: None,
                q: l.matrix(&t("attn_q.weight"), d, q_dim)?,
                k: l.matrix(&t("attn_k.weight"), d, kv_dim)?,
                v: l.matrix(&t("attn_v.weight"), d, kv_dim)?,
                o: l.matrix(&t("attn_output.weight"), q_dim, d)?,
                gate: Gate::None,
                q_bias: None,
                k_bias: None,
                v_bias: None,
                q_norm: None,
                k_norm: None,
                norm_after_rope: false,
                n_head,
                n_head_kv,
                head_dim,
                rope: Rope {
                    dims: rope_dims,
                    base,
                    factors: None,
                    layout: RopeLayout::Neox,
                    mscale: 1.0,
                },
                window: None,
                scale,
                v_norm: None,
                shared_kv: SharedKv::No,
                eps,
            };
            Ok(Layer {
                mixer_norm: Some(l.vector(&t("attn_norm.weight"), d)?),
                mixer: Mixer::Parallel(vec![
                    Mixer::Attention(attention),
                    Mixer::Mamba2(mamba2(l, i, d, eps)?),
                ]),
                mixer_out_norm: None,
                // The converter stores this norm without a ".weight" suffix.
                ffn_norm: Some(l.vector(&t("ffn_norm"), d)?),
                ffn: Some(l.swiglu(i, d, n_ff)?),
                experts: None,
                ffn_out_norm: None,
                residual_scale: None,
            })
        })
        .collect()
}
