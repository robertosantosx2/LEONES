//! Rotary scaling for contexts past the trained length: linear position
//! interpolation and YaRN, as the file's metadata says or the caller asks.
//! NTK-aware scaling is a larger rotary base, which the caller sets.

use std::f32::consts::PI;

use kinetic_gguf::Value;

use crate::blocks::{Mixer, Rope};
use crate::loader::Loader;
use crate::model::Layer;
use crate::LoadError;

/// How to stretch rotary positions; every field left `None` keeps what the
/// model file says.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct RopeScaling {
    pub kind: Option<ScalingKind>,
    /// How many times the trained context the positions stretch to.
    pub factor: Option<f32>,
    /// The rotary base frequency of full-context layers.
    pub freq_base: Option<f32>,
    /// The context the model was trained on, which YaRN stretches from.
    pub original_context: Option<usize>,
}

/// A way of stretching rotary positions.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ScalingKind {
    None,
    /// Every frequency divided by the factor.
    Linear,
    /// High frequencies kept, low ones divided by the factor, a ramp in
    /// between, and the rotated values scaled up slightly.
    Yarn,
}

impl ScalingKind {
    /// The kind named as in GGUF's `rope.scaling.type`.
    pub fn parse(name: &str) -> Option<ScalingKind> {
        Some(match name {
            "none" => ScalingKind::None,
            "linear" => ScalingKind::Linear,
            "yarn" => ScalingKind::Yarn,
            _ => return None,
        })
    }
}

/// YaRN's ramp ends, in rotations over the original context.
const BETA_FAST: f32 = 32.0;
const BETA_SLOW: f32 = 1.0;

/// The scaling the file and `o` ask for, resolved.
struct Resolved {
    kind: ScalingKind,
    factor: f32,
    original_context: usize,
    attn_factor: f32,
    beta: (f32, f32),
}

fn resolve(l: &Loader, o: &RopeScaling) -> Result<Resolved, LoadError> {
    let stored_kind =
        match l.header().arch_key("rope.scaling.type") {
            Some(v) => {
                let name = v
                    .as_str()
                    .ok_or_else(|| LoadError("rope.scaling.type is not a string".into()))?;
                Some(ScalingKind::parse(name).ok_or_else(|| {
                    LoadError(format!("{name} rotary scaling is not supported yet"))
                })?)
            }
            None => None,
        };
    let stored_factor = match l.header().arch_key("rope.scaling.factor") {
        Some(_) => l.f32("rope.scaling.factor")?,
        None => l.f32_or("rope.scale_linear", 0.0)?,
    };
    let factor = o.factor.unwrap_or(stored_factor);
    let kind = o.kind.or(stored_kind).unwrap_or(ScalingKind::Linear);
    let trained = l.usize_or("context_length", 0)?;
    let original_context = match o.original_context {
        Some(n) => n,
        None => l.usize_or("rope.scaling.original_context_length", trained)?,
    };
    let float = |key: &str, default: f32| -> Result<f32, LoadError> {
        match l.header().arch_key(key).and_then(Value::as_f32) {
            Some(v) if v != 0.0 => Ok(v),
            _ => Ok(default),
        }
    };
    Ok(Resolved {
        kind,
        factor: if factor == 0.0 { 1.0 } else { factor },
        original_context,
        attn_factor: float("rope.scaling.attn_factor", 1.0)?,
        beta: (
            float("rope.scaling.yarn_beta_fast", BETA_FAST)?,
            float("rope.scaling.yarn_beta_slow", BETA_SLOW)?,
        ),
    })
}

/// Applies the base override and the scaling to the rotary embedding of
/// every full-context attention layer; windowed layers keep theirs.
pub(crate) fn apply(
    l: &Loader,
    layers: &mut [&mut Layer],
    o: &RopeScaling,
) -> Result<(), LoadError> {
    let r = resolve(l, o)?;
    for layer in layers {
        for_each_rope(&mut layer.mixer, &mut |rope| scale(rope, &r, o.freq_base));
    }
    Ok(())
}

fn for_each_rope(mixer: &mut Mixer, f: &mut impl FnMut(&mut Rope)) {
    match mixer {
        Mixer::Attention(a) if a.window.is_none() && a.rope.dims > 0 => f(&mut a.rope),
        Mixer::Parallel(ms) => ms.iter_mut().for_each(|m| for_each_rope(m, f)),
        _ => {}
    }
}

fn scale(rope: &mut Rope, r: &Resolved, freq_base: Option<f32>) {
    if let Some(base) = freq_base {
        rope.base = base;
    }
    if r.kind == ScalingKind::None || r.factor == 1.0 {
        return;
    }
    let pairs = rope.dims / 2;
    let divisors: Vec<f32> = match r.kind {
        ScalingKind::Yarn => {
            let (low, high) = yarn_ramp(rope.dims, rope.base, r);
            rope.mscale *= r.attn_factor * (1.0 + 0.1 * r.factor.ln());
            (0..pairs)
                .map(|i| {
                    let y = (i as f32 - low) / (high - low).max(0.001);
                    let extrapolate = 1.0 - y.clamp(0.0, 1.0);
                    1.0 / ((1.0 - extrapolate) / r.factor + extrapolate)
                })
                .collect()
        }
        _ => vec![r.factor; pairs],
    };
    let factors = rope.factors.get_or_insert_with(|| vec![1.0; pairs]);
    factors.iter_mut().zip(divisors).for_each(|(f, d)| *f *= d);
}

/// The pairs where YaRN's ramp starts and ends: below the first, pairs turn
/// more than `beta_fast` times over the original context and keep their
/// frequency; past the second, fewer than `beta_slow` times and are
/// interpolated.
fn yarn_ramp(dims: usize, base: f32, r: &Resolved) -> (f32, f32) {
    let pair = |rotations: f32| {
        dims as f32 * (r.original_context as f32 / (rotations * 2.0 * PI)).ln() / (2.0 * base.ln())
    };
    let low = pair(r.beta.0).floor().max(0.0);
    let high = pair(r.beta.1).ceil().min(dims as f32 - 1.0);
    (low, high)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::blocks::RopeLayout;

    fn rope() -> Rope {
        Rope {
            dims: 128,
            base: 1e6,
            factors: None,
            layout: RopeLayout::Neox,
            mscale: 1.0,
        }
    }

    fn yarn(factor: f32) -> Resolved {
        Resolved {
            kind: ScalingKind::Yarn,
            factor,
            original_context: 32768,
            attn_factor: 1.0,
            beta: (BETA_FAST, BETA_SLOW),
        }
    }

    #[test]
    fn yarn_keeps_fast_pairs_and_interpolates_slow_ones() {
        let mut r = rope();
        scale(&mut r, &yarn(4.0), None);
        let f = r.factors.unwrap();
        assert_eq!(f[0], 1.0);
        assert_eq!(f[63], 4.0);
        assert!(f.windows(2).all(|w| w[0] <= w[1]));
        assert!((r.mscale - (1.0 + 0.1 * 4f32.ln())).abs() < 1e-6);
    }

    #[test]
    fn linear_divides_every_frequency() {
        let mut r = rope();
        let linear = Resolved {
            kind: ScalingKind::Linear,
            ..yarn(2.0)
        };
        scale(&mut r, &linear, Some(5e5));
        assert_eq!(r.factors.unwrap(), vec![2.0; 64]);
        assert_eq!((r.base, r.mscale), (5e5, 1.0));
    }
}
