use kinetic_cpu::{dot, pool, rms_norm, silu, softplus};
use kinetic_quant::Matrix;

use super::conv_window::ConvWindow;
use super::tree::Tree;

/// Mamba-2 selective state space mixer. One projection gives a gate `z`,
/// the convolution input `x B C` and a step size per head; `x B C` goes
/// through a causal depthwise convolution with bias and SiLU, then each
/// head scans `x` into a state that decays by one scalar per step, reads
/// it out through `C` and adds the skip `D x`. The result is gated by
/// `SiLU(z)` and optionally RMS-normalized per group.
pub struct Mamba2<'a> {
    pub in_proj: Matrix<'a>,
    /// `conv_taps` taps per channel of `x B C`, oldest input first.
    pub conv: Vec<f32>,
    pub conv_bias: Vec<f32>,
    pub conv_taps: usize,
    pub dt_bias: Vec<f32>,
    /// Stored as `-exp(A_log)`, one per head.
    pub a: Vec<f32>,
    pub d: Vec<f32>,
    pub norm: Option<Vec<f32>>,
    pub out: Matrix<'a>,
    pub n_head: usize,
    pub head_dim: usize,
    pub n_group: usize,
    pub d_state: usize,
    pub eps: f32,
}

/// The convolution window and the per-head scan state.
#[derive(Clone)]
pub struct Mamba2State {
    pub(super) conv: ConvWindow,
    pub(super) s: Vec<f32>,
    journal: Option<Journal>,
}

/// What it takes to replay the scan from a checkpoint: the state then, and
/// each token's convolved `x B C` and step sizes since.
#[derive(Clone)]
struct Journal {
    s: Vec<f32>,
    xbc: Vec<f32>,
    dt: Vec<f32>,
}

impl Mamba2State {
    pub fn checkpoint(&mut self) {
        self.conv.checkpoint();
        self.journal = Some(Journal {
            s: self.s.clone(),
            xbc: Vec::new(),
            dt: Vec::new(),
        });
    }
}

/// One token of one head: its inputs, the `B` and `C` of its group, and
/// its step size.
struct Token<'a> {
    x: &'a [f32],
    b: &'a [f32],
    c: &'a [f32],
    dt: f32,
}

impl Mamba2<'_> {
    pub(super) fn inner(&self) -> usize {
        self.n_head * self.head_dim
    }

    pub(super) fn channels(&self) -> usize {
        self.inner() + 2 * self.n_group * self.d_state
    }

    pub fn new_state(&self) -> Mamba2State {
        Mamba2State {
            conv: ConvWindow::new(self.channels(), self.conv_taps),
            s: vec![0.0; self.inner() * self.d_state],
            journal: None,
        }
    }

    /// The projection runs over the whole batch, the convolution steps
    /// through it token by token, and the scan runs one task per head. With
    /// `tree`, each row continues the convolution and the scan from its
    /// parent row; the state left is that after the last row, which
    /// [`Mamba2::rollback`] then corrects to one path.
    pub fn forward(&self, h: &[f32], tree: Option<&Tree>, state: &mut Mamba2State) -> Vec<f32> {
        let n = h.len() / self.in_proj.cols;
        let mixed = self.mix(self.project(h), n, tree, state);
        super::output(&self.out, &mixed)
    }

    /// The gate, convolution input and step sizes of a batch.
    pub(super) fn project(&self, h: &[f32]) -> Vec<Vec<f32>> {
        vec![super::output(&self.in_proj, h)]
    }

    /// [`Mamba2::forward`] from the projection of its `n` tokens, up to the
    /// input of the output projection.
    pub(super) fn mix(
        &self,
        p: Vec<Vec<f32>>,
        n: usize,
        tree: Option<&Tree>,
        state: &mut Mamba2State,
    ) -> Vec<f32> {
        let (inner, channels, nh) = (self.inner(), self.channels(), self.n_head);
        let width = self.in_proj.rows;
        let [proj]: [Vec<f32>; 1] = p.try_into().expect("one projection");

        let mut xbc = vec![0.0; n * channels];
        match tree {
            Some(_) => state.conv.run(n, tree, |t, window| {
                let inputs = &proj[t * width + inner..][..channels];
                self.convolve(inputs, window, &mut xbc[t * channels..][..channels]);
                inputs.to_vec()
            }),
            None => state
                .conv
                .run_batch(&proj[inner..], width, &mut xbc, |_, ch, past, x| {
                    self.convolve_one(ch, past, x)
                }),
        }
        let dt: Vec<f32> = (0..n * nh)
            .map(|i| {
                softplus(proj[i / nh * width + inner + channels + i % nh] + self.dt_bias[i % nh])
            })
            .collect();
        if let Some(j) = &mut state.journal {
            j.xbc.extend_from_slice(&xbc);
            j.dt.extend_from_slice(&dt);
        }

        let (hd, ds) = (self.head_dim, self.d_state);
        let mut by_head = vec![0.0; nh * n * hd];
        pool::for_each_chunk_pair(
            &mut by_head,
            n * hd,
            &mut state.s,
            hd * ds,
            |head, out, s| {
                let token = |t: usize| {
                    self.token(&xbc[t * channels..][..channels], dt[t * nh + head], head)
                };
                let step = |s: &mut [f32], t: usize, o: &mut [f32]| {
                    let tok = token(t);
                    self.update(s, &tok, head);
                    for ((row, &x), o) in s.chunks_exact(ds).zip(tok.x).zip(o.iter_mut()) {
                        *o = dot(row, tok.c) + x * self.d[head];
                    }
                };
                if let Some(tree) = tree {
                    // Rows continue in place; only states that a later,
                    // non-adjacent child starts from are copied.
                    let start = s.to_vec();
                    let mut kept: Vec<Option<Vec<f32>>> = vec![None; n];
                    for (t, o) in out.chunks_exact_mut(hd).enumerate() {
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
                    for (t, o) in out.chunks_exact_mut(hd).enumerate() {
                        step(s, t, o);
                    }
                }
            },
        );

        let mut y = vec![0.0; n * inner];
        let group = inner / self.n_group;
        pool::for_each_chunk(&mut y, inner, |t, row| {
            for (head, out) in row.chunks_exact_mut(hd).enumerate() {
                out.copy_from_slice(&by_head[(head * n + t) * hd..][..hd]);
            }
            let z = &proj[t * width..][..inner];
            row.iter_mut().zip(z).for_each(|(y, &z)| *y *= silu(z));
            if let Some(w) = &self.norm {
                row.chunks_exact_mut(group)
                    .zip(w.chunks_exact(group))
                    .for_each(|(g, w)| rms_norm(g, w, self.eps));
            }
        });
        y
    }

    /// Keeps `rows`, an increasing path through the tokens run since the
    /// checkpoint. The scan is replayed from the saved inputs with the same
    /// arithmetic as `forward`, so the state is bit-identical to having run
    /// only those tokens.
    pub fn rollback(&self, state: &mut Mamba2State, rows: &[usize]) {
        state.conv.rollback(rows);
        let Some(j) = state.journal.take() else {
            return;
        };
        let (channels, nh) = (self.channels(), self.n_head);
        if j.dt.len() == rows.len() * nh {
            return;
        }
        state.s = j.s;
        pool::for_each_chunk(&mut state.s, self.head_dim * self.d_state, |head, s| {
            for &t in rows {
                let tok = self.token(
                    &j.xbc[t * channels..][..channels],
                    j.dt[t * nh + head],
                    head,
                );
                self.update(s, &tok, head);
            }
        });
    }

    fn convolve(&self, inputs: &[f32], window: &ConvWindow, out: &mut [f32]) {
        for (ch, (&x, o)) in inputs.iter().zip(out).enumerate() {
            *o = self.convolve_one(ch, window.past(ch), x);
        }
    }

    /// The convolution of channel `ch` at input `x` after inputs `past`.
    fn convolve_one(&self, ch: usize, past: &[f32], x: f32) -> f32 {
        let taps = self.conv_taps;
        let w = &self.conv[ch * taps..][..taps];
        let acc = dot(&w[..taps - 1], past) + w[taps - 1] * x;
        silu(acc + self.conv_bias[ch])
    }

    fn token<'t>(&self, xbc: &'t [f32], dt: f32, head: usize) -> Token<'t> {
        let (hd, ds) = (self.head_dim, self.d_state);
        let group = head / (self.n_head / self.n_group);
        let (x, bc) = xbc.split_at(self.inner());
        Token {
            x: &x[head * hd..][..hd],
            b: &bc[group * ds..][..ds],
            c: &bc[(self.n_group + group) * ds..][..ds],
            dt,
        }
    }

    /// One scan step of one head: `S = exp(dt A) S + dt x B^T`.
    fn update(&self, s: &mut [f32], tok: &Token, head: usize) {
        let decay = (tok.dt * self.a[head]).exp();
        for (row, &x) in s.chunks_exact_mut(self.d_state).zip(tok.x) {
            let xdt = x * tok.dt;
            row.iter_mut()
                .zip(tok.b)
                .for_each(|(s, &b)| *s = *s * decay + b * xdt);
        }
    }
}
