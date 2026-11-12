//! Building blocks shared by every architecture. An architecture is a
//! choice of blocks per layer plus the tensor names that fill them.

mod attention;
mod conv_window;
mod delta_chunk;
mod delta_net;
mod folding;
mod mamba2;
mod moe;
mod short_conv;
mod snapshot;
mod tree;

pub use attention::{Attention, Gate, KvCache, Rope, RopeLayout, SharedKv};
pub use delta_net::{DeltaNet, DeltaNetState};
pub use folding::Folding;
pub use mamba2::{Mamba2, Mamba2State};
#[cfg(all(test, feature = "cuda"))]
pub(crate) use moe::scale_offsets;
pub(crate) use moe::{Experts, Gating, Moe};
#[cfg(feature = "cuda")]
pub(crate) use moe::{Job, Pick};
pub use short_conv::{ShortConv, ShortConvState};
pub use tree::Tree;

use std::sync::Arc;

use kinetic_cpu::{matmul, matmul_many, pool, silu};
use kinetic_quant::Matrix;

/// The token-mixing part of a layer.
pub enum Mixer<'a> {
    Attention(Attention<'a>),
    DeltaNet(DeltaNet<'a>),
    ShortConv(ShortConv<'a>),
    Mamba2(Mamba2<'a>),
    /// Mixers that read the same input, with their outputs summed.
    Parallel(Vec<Mixer<'a>>),
}

#[derive(Clone)]
pub enum MixerState {
    Attention(KvCache),
    DeltaNet(DeltaNetState),
    ShortConv(ShortConvState),
    Mamba2(Mamba2State),
    Parallel(Vec<MixerState>),
}

impl MixerState {
    /// Starts recording changes so [`Mixer::rollback`] can undo them.
    pub fn checkpoint(&mut self) {
        match self {
            MixerState::Attention(c) => c.checkpoint(),
            MixerState::DeltaNet(s) => s.checkpoint(),
            MixerState::ShortConv(s) => s.checkpoint(),
            MixerState::Mamba2(s) => s.checkpoint(),
            MixerState::Parallel(s) => s.iter_mut().for_each(MixerState::checkpoint),
        }
    }
}

/// Before layer `to` runs: hands it the keys and values that layer `from`
/// lent in this pass.
pub(crate) fn lend_kv(states: &mut [MixerState], from: usize, to: usize) {
    let lent = match &states[from] {
        MixerState::Attention(c) => c.lent.clone(),
        _ => None,
    };
    if let MixerState::Attention(c) = &mut states[to] {
        c.lent = lent;
    }
}

/// After a pass: drops the keys and values lent during it.
pub(crate) fn end_lending(states: &mut [MixerState]) {
    for s in states {
        if let MixerState::Attention(c) = s {
            c.lent = None;
        }
    }
}

impl Mixer<'_> {
    /// The layer whose keys and values this one attends over, if not its
    /// own.
    pub fn kv_source(&self) -> Option<usize> {
        match self {
            Mixer::Attention(Attention {
                shared_kv: SharedKv::Borrows(from),
                ..
            }) => Some(*from),
            _ => None,
        }
    }

    pub fn new_state(&self) -> MixerState {
        match self {
            Mixer::Attention(_) => MixerState::Attention(KvCache::default()),
            Mixer::DeltaNet(d) => MixerState::DeltaNet(d.new_state()),
            Mixer::ShortConv(s) => MixerState::ShortConv(s.new_state()),
            Mixer::Mamba2(m) => MixerState::Mamba2(m.new_state()),
            Mixer::Parallel(ms) => MixerState::Parallel(ms.iter().map(Mixer::new_state).collect()),
        }
    }

    /// Bytes of the state of a sequence `len` tokens long.
    pub fn state_bytes(&self, len: usize) -> usize {
        let floats = match self {
            Mixer::Attention(a) => {
                2 * a.n_head_kv * a.head_dim * a.window.map_or(len, |w| w.min(len))
            }
            Mixer::DeltaNet(d) => {
                d.n_v_heads * d.head_v_dim * d.head_k_dim + d.qkv.rows * (d.conv_taps - 1)
            }
            Mixer::ShortConv(s) => s.out_proj.cols * (s.taps - 1),
            Mixer::Mamba2(m) => m.inner() * m.d_state + m.channels() * (m.conv_taps - 1),
            Mixer::Parallel(ms) => return ms.iter().map(|m| m.state_bytes(len)).sum(),
        };
        floats * size_of::<f32>()
    }

    /// Keeps `rows`, an increasing path through the tokens run since the
    /// last checkpoint, and undoes the rest.
    pub fn rollback(&self, state: &mut MixerState, rows: &[usize]) {
        match (self, state) {
            (Mixer::Attention(a), MixerState::Attention(c)) => c.rollback(rows, a.window),
            (Mixer::DeltaNet(d), MixerState::DeltaNet(s)) => d.rollback(s, rows),
            (Mixer::ShortConv(_), MixerState::ShortConv(s)) => s.rollback(rows),
            (Mixer::Mamba2(m), MixerState::Mamba2(s)) => m.rollback(s, rows),
            (Mixer::Parallel(ms), MixerState::Parallel(ss)) => {
                ms.iter().zip(ss).for_each(|(m, s)| m.rollback(s, rows))
            }
            _ => unreachable!("state does not belong to this mixer"),
        }
    }

    /// Runs a batch from position `pos0`; `grid` optionally gives every
    /// token a (time, row, column) rotary position instead, and `tree` lets
    /// the batch branch.
    pub fn forward(
        &self,
        h: &[f32],
        pos0: usize,
        grid: Option<&[[usize; 3]]>,
        tree: Option<&Tree>,
        state: &mut MixerState,
    ) -> Vec<f32> {
        match (self, state) {
            (Mixer::Attention(a), MixerState::Attention(c)) => a.forward(h, pos0, grid, tree, c),
            (Mixer::DeltaNet(d), MixerState::DeltaNet(s)) => d.forward(h, tree, s),
            (Mixer::ShortConv(s), MixerState::ShortConv(st)) => s.forward(h, tree, st),
            (Mixer::Mamba2(m), MixerState::Mamba2(s)) => m.forward(h, tree, s),
            (Mixer::Parallel(ms), MixerState::Parallel(ss)) => ms
                .iter()
                .zip(ss)
                .map(|(m, s)| m.forward(h, pos0, grid, tree, s))
                .reduce(|mut sum, y| {
                    sum.iter_mut().zip(&y).for_each(|(s, y)| *s += y);
                    sum
                })
                .expect("parallel mixers"),
            _ => unreachable!("state does not belong to this mixer"),
        }
    }
}

/// One sequence's rows in a batch that several sequences run together.
pub struct Part<'s> {
    pub rows: usize,
    /// The position of its first row.
    pub pos0: usize,
    pub state: &'s mut MixerState,
}

impl Mixer<'_> {
    /// Runs a batch made of `parts`, one after another in `h`, each on its
    /// own state. Projections read their weights once for the whole batch;
    /// the rest runs part by part, so every row comes out exactly as
    /// [`Mixer::forward`] gives it for its part alone.
    pub fn forward_parts(&self, h: &[f32], parts: &mut [Part]) -> Vec<f32> {
        match self {
            Mixer::Attention(a) => by_parts(h, parts, &a.o, a.project(h), |p, n, part| {
                let MixerState::Attention(c) = &mut *part.state else {
                    unreachable!("state does not belong to this mixer")
                };
                a.mix(p, n, part.pos0, None, None, c)
            }),
            Mixer::DeltaNet(d) => by_parts(h, parts, &d.out, d.project(h), |p, n, part| {
                let MixerState::DeltaNet(s) = &mut *part.state else {
                    unreachable!("state does not belong to this mixer")
                };
                d.mix(p, n, None, s)
            }),
            Mixer::ShortConv(c) => by_parts(h, parts, &c.out_proj, c.project(h), |p, n, part| {
                let MixerState::ShortConv(s) = &mut *part.state else {
                    unreachable!("state does not belong to this mixer")
                };
                c.mix(p, n, None, s)
            }),
            Mixer::Mamba2(m) => by_parts(h, parts, &m.out, m.project(h), |p, n, part| {
                let MixerState::Mamba2(s) = &mut *part.state else {
                    unreachable!("state does not belong to this mixer")
                };
                m.mix(p, n, None, s)
            }),
            Mixer::Parallel(ms) => (0..ms.len())
                .map(|i| {
                    let mut own: Vec<Part> = parts
                        .iter_mut()
                        .map(|p| {
                            let MixerState::Parallel(ss) = &mut *p.state else {
                                unreachable!("state does not belong to this mixer")
                            };
                            Part {
                                rows: p.rows,
                                pos0: p.pos0,
                                state: &mut ss[i],
                            }
                        })
                        .collect();
                    ms[i].forward_parts(h, &mut own)
                })
                .reduce(|mut sum, y| {
                    sum.iter_mut().zip(&y).for_each(|(s, y)| *s += y);
                    sum
                })
                .expect("parallel mixers"),
        }
    }
}

/// Cuts the projections `p` of a batch into `parts`, runs `mix` on each
/// and the output projection `out` on all of their results at once.
fn by_parts(
    h: &[f32],
    parts: &mut [Part],
    out: &Matrix,
    p: Vec<Vec<f32>>,
    mut mix: impl FnMut(Vec<Vec<f32>>, usize, &mut Part) -> Vec<f32>,
) -> Vec<f32> {
    let n: usize = parts.iter().map(|p| p.rows).sum();
    assert_eq!(h.len(), n * out.rows, "parts must cover the batch");
    let mut mixed = Vec::with_capacity(n * out.cols);
    let mut at = 0;
    for part in parts {
        let rows = |b: &Vec<f32>| {
            let width = b.len() / n;
            b[at * width..(at + part.rows) * width].to_vec()
        };
        mixed.extend(mix(p.iter().map(rows).collect(), part.rows, part));
        at += part.rows;
    }
    output(out, &mixed)
}

/// `w` applied to every row of `x`.
fn output(w: &Matrix, x: &[f32]) -> Vec<f32> {
    let mut y = vec![0.0; x.len() / w.cols * w.rows];
    matmul(w, x, &mut y);
    y
}

/// Gated feed-forward: `down(act(gate x) * up x)`, where `act` is SiLU
/// unless `activation` says otherwise.
pub struct SwiGlu<'a> {
    pub gate: Matrix<'a>,
    pub up: Matrix<'a>,
    pub down: Matrix<'a>,
    pub activation: Activation,
    /// Set when all three projections were stored folded.
    pub folding: Option<Arc<Folding>>,
}

/// The nonlinearity applied to the gate projection.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum Activation {
    #[default]
    Silu,
    /// GELU in its tanh approximation, which makes the block a GeGLU.
    Gelu,
}

impl SwiGlu<'_> {
    pub fn forward(&self, h: &[f32]) -> Vec<f32> {
        let n = h.len() / self.gate.cols;
        let rotated;
        let h = match &self.folding {
            Some(f) => {
                rotated = f.rotate(h, self.gate.cols);
                &rotated[..]
            }
            None => h,
        };
        let mut gate = vec![0.0; n * self.gate.rows];
        let mut up = vec![0.0; n * self.up.rows];
        matmul_many(&[&self.gate, &self.up], h, &mut [&mut gate, &mut up]);
        pool::for_each_chunk(&mut gate, ACTIVATION_CHUNK, |i, g| {
            let u = &up[i * ACTIVATION_CHUNK..];
            match self.activation {
                Activation::Silu => gated(g, u, silu),
                Activation::Gelu => gated(g, u, gelu),
            }
        });
        if let Some(f) = &self.folding {
            gate = f.rotate(&gate, self.down.cols);
        }
        let mut y = vec![0.0; n * self.down.rows];
        matmul(&self.down, &gate, &mut y);
        y
    }
}

/// Gate values one parallel task activates: the exponentials make this
/// worth spreading even for one token.
pub(super) const ACTIVATION_CHUNK: usize = 1024;

/// `g = act(g) * u`, element by element.
fn gated(g: &mut [f32], u: &[f32], act: impl Fn(f32) -> f32) {
    g.iter_mut().zip(u).for_each(|(g, u)| *g = act(*g) * u);
}

pub(crate) fn gelu(x: f32) -> f32 {
    const SQRT_2_OVER_PI: f32 = 0.797_884_6;
    0.5 * x * (1.0 + (SQRT_2_OVER_PI * (x + 0.044_715 * x * x * x)).tanh())
}

#[cfg(test)]
mod tests {
    use super::gelu;

    #[test]
    fn gelu_matches_known_values() {
        assert_eq!(gelu(0.0), 0.0);
        assert!((gelu(1.0) - 0.841_192).abs() < 1e-6);
        assert!((gelu(-3.0) + 0.003_637_4).abs() < 1e-6);
    }
}
