//! Mamba-2 mixers under their GGUF tensor names, shared by the hybrid
//! architectures.

use crate::blocks::Mamba2;
use crate::loader::Loader;
use crate::LoadError;

/// The Mamba-2 mixer of layer `i` in a model of width `d`.
pub(crate) fn mamba2<'a>(
    l: &Loader<'a>,
    i: usize,
    d: usize,
    eps: f32,
) -> Result<Mamba2<'a>, LoadError> {
    let t = |s: &str| format!("blk.{i}.{s}");
    let taps = l.usize("ssm.conv_kernel")?;
    let inner = l.usize("ssm.inner_size")?;
    let d_state = l.usize("ssm.state_size")?;
    let n_head = l.usize("ssm.time_step_rank")?;
    let n_group = l.usize("ssm.group_count")?;
    if taps < 2
        || n_head == 0
        || n_group == 0
        || !inner.is_multiple_of(n_head)
        || !n_head.is_multiple_of(n_group)
    {
        return Err(LoadError("invalid state space sizes".into()));
    }
    let channels = inner + 2 * n_group * d_state;
    Ok(Mamba2 {
        in_proj: l.matrix(&t("ssm_in.weight"), d, inner + channels + n_head)?,
        conv: l.vector(&t("ssm_conv1d.weight"), taps * channels)?,
        conv_bias: l
            .optional_vector(&t("ssm_conv1d.bias"), channels)?
            .unwrap_or_else(|| vec![0.0; channels]),
        conv_taps: taps,
        dt_bias: l.vector(&t("ssm_dt.bias"), n_head)?,
        a: l.vector(&t("ssm_a"), n_head)?,
        d: l.vector(&t("ssm_d"), n_head)?,
        norm: l.optional_vector(&t("ssm_norm.weight"), inner)?,
        out: l.matrix(&t("ssm_out.weight"), inner, d)?,
        n_head,
        head_dim: inner / n_head,
        n_group,
        d_state,
        eps,
    })
}
