//! Mixture-of-experts feed-forwards: a router over many small
//! experts, of which a few run per token, and in some models a shared expert
//! that runs on every token, in Qwen3.5 MoE behind a sigmoid gate.

use crate::blocks::{Activation, Gating, Moe, SwiGlu};
use crate::loader::Loader;
use crate::LoadError;

/// The routed experts of layer `i`, each `n_ff` wide.
pub(crate) fn routed<'a>(
    l: &Loader<'a>,
    i: usize,
    d: usize,
    n_ff: usize,
) -> Result<Moe<'a>, LoadError> {
    let t = |s: &str| format!("blk.{i}.{s}");
    let n_experts = l.usize("expert_count")?;
    // values as llama.cpp's llama_expert_gating_func_type
    let gating = match l.usize_or("expert_gating_func", 1)? {
        1 => Gating::Softmax,
        2 => Gating::Sigmoid {
            bias: l
                .optional_vector(&t("exp_probs_b.bias"), n_experts)?
                .unwrap_or_else(|| vec![0.0; n_experts]),
        },
        other => {
            return Err(LoadError(format!(
                "expert gating function {other} is not supported yet"
            )))
        }
    };
    Ok(Moe {
        router: l.matrix(&t("ffn_gate_inp.weight"), d, n_experts)?,
        gate: l.experts(&t("ffn_gate_exps.weight"), d, n_ff, n_experts)?,
        up: l.experts(&t("ffn_up_exps.weight"), d, n_ff, n_experts)?,
        down: l.experts(&t("ffn_down_exps.weight"), n_ff, d, n_experts)?,
        n_used: l.usize("expert_used_count")?,
        shared_gate: l.optional_vector(&t("ffn_gate_inp_shexp.weight"), d)?,
        gating,
    })
}

/// The shared expert of layer `i`, if the file has one; it is as wide as a
/// routed expert unless the file says otherwise.
pub(crate) fn shared<'a>(
    l: &Loader<'a>,
    i: usize,
    d: usize,
    n_ff: usize,
) -> Result<Option<SwiGlu<'a>>, LoadError> {
    let t = |s: &str| format!("blk.{i}.{s}");
    if l.header().tensor(&t("ffn_gate_shexp.weight")).is_none() {
        return Ok(None);
    }
    let n_ff = l.usize_or("expert_shared_feed_forward_length", n_ff)?;
    Ok(Some(SwiGlu {
        folding: None,
        gate: l.matrix(&t("ffn_gate_shexp.weight"), d, n_ff)?,
        up: l.matrix(&t("ffn_up_shexp.weight"), d, n_ff)?,
        down: l.matrix(&t("ffn_down_shexp.weight"), n_ff, d)?,
        activation: Activation::Silu,
    }))
}
