use kinetic_cpu::{
    dot, dots, l2_norm, matmul_many, pool, rms_norm, scale_axpy, sigmoid, silu, softplus,
};
use std::sync::Arc;

use kinetic_quant::Matrix;

use super::conv_window::ConvWindow;
use super::delta_chunk::{self, Token};
use super::folding::Folding;
use super::tree::Tree;

/// Batches at least this long run the recurrence in chunked matrix form.
const CHUNKED_MIN_TOKENS: usize = 32;

/// Gated delta-rule linear attention: a causal depthwise convolution over
/// the projected queries, keys and values, then a per-head recurrent state
/// updated by the delta rule.
pub struct DeltaNet<'a> {
    /// Projects to the convolution input: queries, keys, then values.
    pub qkv: Matrix<'a>,
    /// Output gate, one value per value channel.
    pub z: Matrix<'a>,
    pub beta: Matrix<'a>,
    pub alpha: Matrix<'a>,
    pub dt_bias: Vec<f32>,
    /// Stored as `-exp(A_log)`, so `exp(a * softplus(..))` is the decay.
    pub a: Vec<f32>,
    /// `conv_taps` taps per channel, oldest input first.
    pub conv: Vec<f32>,
    pub conv_taps: usize,
    pub norm: Vec<f32>,
    pub out: Matrix<'a>,
    pub n_k_heads: usize,
    pub n_v_heads: usize,
    pub head_k_dim: usize,
    pub head_v_dim: usize,
    pub eps: f32,
    /// Set when qkv, z and out were stored folded.
    pub folding: Option<Arc<Folding>>,
}

/// The convolution window and the per-head recurrent state.
#[derive(Clone)]
pub struct DeltaNetState {
    pub(super) conv: ConvWindow,
    pub(super) s: Vec<f32>,
    journal: Option<Journal>,
}

/// What it takes to replay the recurrence from a checkpoint: the state then,
/// and each token's normalized keys, values, decays and step sizes since.
#[derive(Clone)]
struct Journal {
    s: Vec<f32>,
    k: Vec<f32>,
    v: Vec<f32>,
    decay: Vec<f32>,
    b: Vec<f32>,
}

impl DeltaNetState {
    pub fn checkpoint(&mut self) {
        self.conv.checkpoint();
        self.journal = Some(Journal {
            s: self.s.clone(),
            k: Vec::new(),
            v: Vec::new(),
            decay: Vec::new(),
            b: Vec::new(),
        });
    }
}

impl DeltaNet<'_> {
    fn key_dim(&self) -> usize {
        self.n_k_heads * self.head_k_dim
    }

    fn value_dim(&self) -> usize {
        self.n_v_heads * self.head_v_dim
    }

    pub fn new_state(&self) -> DeltaNetState {
        DeltaNetState {
            conv: ConvWindow::new(self.qkv.rows, self.conv_taps),
            s: vec![0.0; self.n_v_heads * self.head_v_dim * self.head_k_dim],
            journal: None,
        }
    }

    /// Projections run over the whole batch. The convolution then steps
    /// through it token by token, and the recurrence runs one task per value
    /// head, so each head's state stays in cache: token by token for short
    /// batches, in chunks of matrix products for long ones. With `tree`,
    /// each row continues the convolution and the recurrence from its
    /// parent row; the state left is that after the last row, which
    /// [`DeltaNet::rollback`] then corrects to one path.
    pub fn forward(&self, h: &[f32], tree: Option<&Tree>, state: &mut DeltaNetState) -> Vec<f32> {
        let n = h.len() / self.qkv.cols;
        let mixed = self.mix(self.project(h), n, tree, state);
        super::output(&self.out, &mixed)
    }

    /// The convolution input, output gate, step sizes and decays of a
    /// batch, before their nonlinearities.
    pub(super) fn project(&self, h: &[f32]) -> Vec<Vec<f32>> {
        let n = h.len() / self.qkv.cols;
        let mut qkv = vec![0.0; n * self.qkv.rows];
        let mut z = vec![0.0; n * self.value_dim()];
        let mut beta = vec![0.0; n * self.n_v_heads];
        let mut alpha = vec![0.0; n * self.n_v_heads];
        match &self.folding {
            Some(f) => {
                let rotated = f.rotate(h, self.qkv.cols);
                matmul_many(&[&self.qkv, &self.z], &rotated, &mut [&mut qkv, &mut z]);
                matmul_many(&[&self.beta, &self.alpha], h, &mut [&mut beta, &mut alpha]);
            }
            None => matmul_many(
                &[&self.qkv, &self.z, &self.beta, &self.alpha],
                h,
                &mut [&mut qkv, &mut z, &mut beta, &mut alpha],
            ),
        }
        vec![qkv, z, beta, alpha]
    }

    /// [`DeltaNet::forward`] from the projections of its `n` tokens, up to
    /// the input of the output projection.
    pub(super) fn mix(
        &self,
        p: Vec<Vec<f32>>,
        n: usize,
        tree: Option<&Tree>,
        state: &mut DeltaNetState,
    ) -> Vec<f32> {
        let (channels, kd, vd, nv) = (
            self.qkv.rows,
            self.key_dim(),
            self.value_dim(),
            self.n_v_heads,
        );
        let [mut qkv, z, beta, alpha]: [Vec<f32>; 4] = p.try_into().expect("four projections");

        match tree {
            Some(_) => state.conv.run(n, tree, |t, window| {
                let row = &mut qkv[t * channels..][..channels];
                let inputs = row.to_vec();
                self.convolve(row, window);
                inputs
            }),
            None => {
                let inputs = std::mem::take(&mut qkv);
                qkv = vec![0.0; inputs.len()];
                state
                    .conv
                    .run_batch(&inputs, channels, &mut qkv, |_, ch, past, x| {
                        self.convolve_one(ch, past, x)
                    });
                qkv.chunks_exact_mut(channels)
                    .for_each(|row| self.normalize(row));
            }
        }
        let log_decay: Vec<f32> = alpha
            .iter()
            .enumerate()
            .map(|(i, &a)| softplus(a + self.dt_bias[i % nv]) * self.a[i % nv])
            .collect();
        let decay: Vec<f32> = log_decay.iter().map(|x| x.exp()).collect();
        let b: Vec<f32> = beta.iter().map(|&x| sigmoid(x)).collect();
        if let Some(j) = &mut state.journal {
            for row in qkv.chunks_exact(channels) {
                j.k.extend_from_slice(&row[kd..2 * kd]);
                j.v.extend_from_slice(&row[2 * kd..]);
            }
            j.decay.extend_from_slice(&decay);
            j.b.extend_from_slice(&b);
        }

        let (dk, dv) = (self.head_k_dim, self.head_v_dim);
        // Rollback replays the exact recurrence, and speculative verification
        // must match one-token decoding bit for bit, so only long batches
        // outside a checkpoint take the chunked form.
        let chunked =
            n >= CHUNKED_MIN_TOKENS && state.journal.is_none() && delta_chunk::available(dk, dv);
        let mut by_head = vec![0.0; nv * n * dv];
        pool::for_each_chunk_pair(&mut by_head, n * dv, &mut state.s, dv * dk, |vh, out, s| {
            // Value heads share key heads by tiling: value head h reads key head h mod n_k_heads.
            let kh = vh % self.n_k_heads;
            let token = |t: usize| {
                let row = &qkv[t * channels..][..channels];
                Token {
                    q: &row[kh * dk..][..dk],
                    k: &row[kd + kh * dk..][..dk],
                    v: &row[2 * kd + vh * dv..][..dv],
                    log_decay: log_decay[t * nv + vh],
                    b: b[t * nv + vh],
                }
            };
            let step = |s: &mut [f32], t: usize, o: &mut [f32]| {
                let tok = token(t);
                update_head(s, tok.k, tok.v, decay[t * nv + vh], tok.b, Some((tok.q, o)));
            };
            if chunked {
                delta_chunk::run(s, out, dk, dv, token);
            } else if let Some(tree) = tree {
                // Rows continue in place; only states that a later,
                // non-adjacent child starts from are copied.
                let start = s.to_vec();
                let mut kept: Vec<Option<Vec<f32>>> = vec![None; n];
                for (t, o) in out.chunks_exact_mut(dv).enumerate() {
                    match tree.parent(t) {
                        Some(p) if p + 1 == t => {}
                        Some(p) => s.copy_from_slice(kept[p].as_ref().expect("kept fork")),
                        None if t > 0 => s.copy_from_slice(&start),
                        None => {}
                    }
                    step(s, t, o);
                    if tree.forks(t) {
                        kept[t] = Some(s.to_vec());
                    }
                }
            } else {
                for (t, o) in out.chunks_exact_mut(dv).enumerate() {
                    step(s, t, o);
                }
            }
            for (t, o) in out.chunks_exact_mut(dv).enumerate() {
                rms_norm(o, &self.norm, self.eps);
                o.iter_mut()
                    .zip(&z[t * vd + vh * dv..][..dv])
                    .for_each(|(o, z)| *o *= silu(*z));
            }
        });

        let mut out = vec![0.0; n * vd];
        for (vh, head) in by_head.chunks_exact(n * dv).enumerate() {
            for (t, o) in head.chunks_exact(dv).enumerate() {
                out[t * vd + vh * dv..][..dv].copy_from_slice(o);
            }
        }
        match &self.folding {
            Some(f) => f.rotate_values(&out, dv, self.n_k_heads, self.n_v_heads),
            None => out,
        }
    }

    /// Keeps `rows`, an increasing path through the tokens run since the
    /// checkpoint. The recurrence is replayed from the saved inputs with the
    /// same arithmetic as `forward`, so the state is bit-identical to having
    /// run only those tokens.
    pub fn rollback(&self, state: &mut DeltaNetState, rows: &[usize]) {
        state.conv.rollback(rows);
        let Some(j) = state.journal.take() else {
            return;
        };
        let (kd, vd, nv) = (self.key_dim(), self.value_dim(), self.n_v_heads);
        if j.decay.len() == rows.len() * nv {
            return;
        }
        state.s = j.s;
        let (dk, dv) = (self.head_k_dim, self.head_v_dim);
        pool::for_each_chunk(&mut state.s, dv * dk, |vh, s| {
            let kh = vh % self.n_k_heads;
            for &t in rows {
                let k = &j.k[t * kd + kh * dk..][..dk];
                let v = &j.v[t * vd + vh * dv..][..dv];
                update_head(s, k, v, j.decay[t * nv + vh], j.b[t * nv + vh], None);
            }
        });
    }

    /// Causal depthwise convolution of one token over `window` and its own
    /// inputs, in place, then the per-head normalization of queries and
    /// keys.
    fn convolve(&self, qkv: &mut [f32], window: &ConvWindow) {
        for (ch, x) in qkv.iter_mut().enumerate() {
            *x = self.convolve_one(ch, window.past(ch), *x);
        }
        self.normalize(qkv);
    }

    fn convolve_one(&self, ch: usize, past: &[f32], x: f32) -> f32 {
        let taps = self.conv_taps;
        let w = &self.conv[ch * taps..(ch + 1) * taps];
        silu(w[taps - 1] * x + w.iter().zip(past).map(|(w, p)| w * p).sum::<f32>())
    }

    fn normalize(&self, qkv: &mut [f32]) {
        let (q, rest) = qkv.split_at_mut(self.key_dim());
        let k = &mut rest[..self.key_dim()];
        let q_scale = 1.0 / (self.head_k_dim as f32).sqrt();
        for head in q.chunks_exact_mut(self.head_k_dim) {
            l2_norm(head, self.eps);
            head.iter_mut().for_each(|x| *x *= q_scale);
        }
        for head in k.chunks_exact_mut(self.head_k_dim) {
            l2_norm(head, self.eps);
        }
    }
}

/// One row of the delta rule: `S = decay * S; S += b * (v - S k) k^T`.
pub(super) fn update(row: &mut [f32], k: &[f32], v: f32, decay: f32, b: f32) {
    scale_add(row, k, (v - decay * dot(row, k)) * b, decay);
}

/// [`update`] for every row of a head's state, then `out = S q` with
/// `read`. Rows go four at a time so their dot products run side by side
/// instead of each waiting on its own chain of adds; every value is the
/// one [`update`] and [`dot`] give.
fn update_head(
    s: &mut [f32],
    k: &[f32],
    v: &[f32],
    decay: f32,
    b: f32,
    mut read: Option<(&[f32], &mut [f32])>,
) {
    let dk = k.len();
    for (i, (rows, v)) in s.chunks_mut(4 * dk).zip(v.chunks(4)).enumerate() {
        if let [v0, v1, v2, v3] = *v {
            let (r0, rest) = rows.split_at_mut(dk);
            let (r1, rest) = rest.split_at_mut(dk);
            let (r2, r3) = rest.split_at_mut(dk);
            let d = dots([&*r0, &*r1, &*r2, &*r3], k);
            for ((row, v), d) in [&mut *r0, &mut *r1, &mut *r2, &mut *r3]
                .into_iter()
                .zip([v0, v1, v2, v3])
                .zip(d)
            {
                scale_add(row, k, (v - decay * d) * b, decay);
            }
            if let Some((q, out)) = &mut read {
                out[4 * i..][..4].copy_from_slice(&dots([&*r0, &*r1, &*r2, &*r3], q));
            }
        } else {
            for (j, (row, &v)) in rows.chunks_exact_mut(dk).zip(v).enumerate() {
                update(row, k, v, decay, b);
                if let Some((q, out)) = &mut read {
                    out[4 * i + j] = dot(row, q);
                }
            }
        }
    }
}

fn scale_add(row: &mut [f32], k: &[f32], delta: f32, decay: f32) {
    scale_axpy(row, decay, delta, k);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn head_update_matches_row_updates() {
        let (dk, dv) = (40, 7);
        let mut seed = 7u32;
        let mut next = move || {
            seed = seed.wrapping_mul(1_664_525).wrapping_add(1_013_904_223);
            (seed >> 8) as f32 / (1 << 23) as f32 - 1.0
        };
        let mut s: Vec<f32> = (0..dk * dv).map(|_| next()).collect();
        let (k, q): (Vec<f32>, Vec<f32>) = (0..dk).map(|_| (next(), next())).unzip();
        let v: Vec<f32> = (0..dv).map(|_| next()).collect();
        let mut want = s.clone();
        let mut want_out = vec![0.0; dv];
        for ((row, &v), o) in want.chunks_exact_mut(dk).zip(&v).zip(&mut want_out) {
            update(row, &k, v, 0.9, 0.6);
            *o = dot(row, &q);
        }
        let mut out = vec![0.0; dv];
        update_head(&mut s, &k, &v, 0.9, 0.6, Some((&q, &mut out)));
        assert_eq!((s, out), (want, want_out));
    }
}
