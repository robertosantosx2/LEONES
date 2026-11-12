use kinetic_cpu::{axpy_rows, dot_rows, matmul, matmul_many, pool, rms_norm, sigmoid, softmax};
use std::sync::Arc;

use kinetic_quant::Matrix;

use super::folding::Folding;
use super::tree::{leading, Tree};

mod bidirectional;

/// Rotary position embedding: only the first `dims` values of a head
/// rotate, in pairs laid out as `layout` says.
pub struct Rope {
    pub dims: usize,
    pub base: f32,
    /// Per-pair divisors of the rotation frequency, when the model has them.
    pub factors: Option<Vec<f32>>,
    pub layout: RopeLayout,
    /// Multiplies the rotated values, as YaRN scaling asks.
    pub mscale: f32,
}

/// Which two values of a head rotate together as pair `i`.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum RopeLayout {
    /// Element `i` pairs with `i + dims / 2`.
    #[default]
    Neox,
    /// Element `2i` pairs with `2i + 1`, as in Llama weights, whose query
    /// and key rows the GGUF converter permutes into this order.
    Adjacent,
}

impl Rope {
    #[cfg(test)]
    fn apply(&self, x: &mut [f32], pos: usize) {
        self.rotate(x, &self.angles(pos));
    }

    /// The sine and cosine of every pair's angle at `pos`, shared by all
    /// heads of a token.
    pub(crate) fn angles(&self, pos: usize) -> Vec<(f32, f32)> {
        self.grid_angles([pos; 3])
    }

    /// [`Rope::angles`] for a token at (time, row, column) `pos`, under the
    /// interleaved multimodal rotary of Qwen3-VL and Qwen3.5: pair `i` turns
    /// by `pos[i % 3]`.
    fn grid_angles(&self, pos: [usize; 3]) -> Vec<(f32, f32)> {
        (0..self.dims / 2)
            .map(|i| {
                let factor = self.factors.as_ref().map_or(1.0, |f| f[i]);
                let theta = pos[i % 3] as f32
                    * self.base.powf(-((2 * i) as f32) / self.dims as f32)
                    / factor;
                let (sin, cos) = theta.sin_cos();
                (sin * self.mscale, cos * self.mscale)
            })
            .collect()
    }

    fn rotate(&self, x: &mut [f32], angles: &[(f32, f32)]) {
        let half = self.dims / 2;
        for (i, &(sin, cos)) in angles.iter().enumerate() {
            let (i, j) = match self.layout {
                RopeLayout::Neox => (i, i + half),
                RopeLayout::Adjacent => (2 * i, 2 * i + 1),
            };
            let (a, b) = (x[i], x[j]);
            x[i] = a * cos - b * sin;
            x[j] = a * sin + b * cos;
        }
    }
}

/// How the attention output is gated before the output projection.
pub enum Gate<'a> {
    /// The query projection emits, per head, `head_dim` queries followed by
    /// `head_dim` gate values applied element-wise.
    Interleaved,
    /// A separate projection gives one gate value per head.
    PerHead(Matrix<'a>),
    /// The output is not gated.
    None,
}

pub struct Attention<'a> {
    pub q: Matrix<'a>,
    pub k: Matrix<'a>,
    pub v: Matrix<'a>,
    pub o: Matrix<'a>,
    pub gate: Gate<'a>,
    /// Biases added to the query, key and value projections.
    pub q_bias: Option<Vec<f32>>,
    pub k_bias: Option<Vec<f32>>,
    pub v_bias: Option<Vec<f32>>,
    /// RMS norms of the queries and keys: one weight per head value
    /// normalizes each head, one per projected value normalizes all heads
    /// of a token together.
    pub q_norm: Option<Vec<f32>>,
    pub k_norm: Option<Vec<f32>>,
    /// Whether the query and key norms follow the rotation.
    pub norm_after_rope: bool,
    pub n_head: usize,
    pub n_head_kv: usize,
    pub head_dim: usize,
    pub rope: Rope,
    /// Keep only this many past positions, as a ring.
    pub window: Option<usize>,
    /// Multiplies query-key scores, `1 / sqrt(head_dim)` when not given.
    pub scale: Option<f32>,
    /// RMS norm of each value head.
    pub v_norm: Option<Vec<f32>>,
    pub shared_kv: SharedKv,
    pub eps: f32,
    /// Set when the projections were stored folded.
    pub folding: Option<Arc<Folding>>,
}

/// Whether a layer hands its keys and values to later layers or attends
/// over another layer's instead of projecting its own.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum SharedKv {
    #[default]
    No,
    /// Keeps each batch's keys and values for the layers that borrow them.
    Lends,
    /// Uses those of the lending layer at this index.
    Borrows(usize),
}

#[derive(Clone, Default)]
pub struct KvCache {
    pub(super) k: Vec<f32>,
    pub(super) v: Vec<f32>,
    /// One entry per row stored since the last checkpoint.
    journal: Option<Vec<Stored>>,
    /// The keys and values of the batch in flight, lent by
    /// [`SharedKv::Lends`] and taken by [`SharedKv::Borrows`].
    pub(crate) lent: Option<(Vec<f32>, Vec<f32>)>,
}

/// A row stored since the checkpoint: its position, keys and values, and
/// how to undo storing it.
#[derive(Clone)]
struct Stored {
    pos: usize,
    k: Vec<f32>,
    v: Vec<f32>,
    undo: Undo,
}

#[derive(Clone)]
enum Undo {
    Appended { len: usize },
    Overwrote { at: usize, k: Vec<f32>, v: Vec<f32> },
}

impl KvCache {
    /// Starts recording changes so [`KvCache::rollback`] can undo them.
    pub fn checkpoint(&mut self) {
        self.journal = Some(Vec::new());
    }

    /// Keeps `rows`, an increasing path through the rows stored since the
    /// checkpoint, as if only they had been stored, and stops recording.
    /// Kept rows need not be contiguous: rows off the path are dropped and
    /// the cache is compacted.
    pub fn rollback(&mut self, rows: &[usize], window: Option<usize>) {
        let Some(journal) = self.journal.take() else {
            return;
        };
        let keep = leading(rows);
        let kept: Vec<&Stored> = rows[keep..].iter().map(|&r| &journal[r]).collect();
        for stored in journal[keep..].iter().rev() {
            match &stored.undo {
                Undo::Appended { len } => {
                    self.k.truncate(*len);
                    self.v.truncate(*len);
                }
                Undo::Overwrote { at, k, v } => {
                    self.k[*at..][..k.len()].copy_from_slice(k);
                    self.v[*at..][..v.len()].copy_from_slice(v);
                }
            }
        }
        for row in kept {
            self.store(window, row.pos, &row.k, &row.v);
        }
    }

    /// Stores the keys and values of position `pos`. A full window is a
    /// ring indexed by `pos % window`; attention does not depend on the
    /// order of positions.
    fn store(&mut self, window: Option<usize>, pos: usize, k: &[f32], v: &[f32]) {
        let kv_dim = k.len();
        let undo = match window {
            Some(w) if self.k.len() == w * kv_dim => {
                let at = (pos % w) * kv_dim;
                let undo = self.journal.is_some().then(|| Undo::Overwrote {
                    at,
                    k: self.k[at..][..kv_dim].to_vec(),
                    v: self.v[at..][..kv_dim].to_vec(),
                });
                self.k[at..][..kv_dim].copy_from_slice(k);
                self.v[at..][..kv_dim].copy_from_slice(v);
                undo
            }
            _ => {
                let len = self.k.len();
                self.k.extend_from_slice(k);
                self.v.extend_from_slice(v);
                Some(Undo::Appended { len })
            }
        };
        if let (Some(journal), Some(undo)) = (&mut self.journal, undo) {
            journal.push(Stored {
                pos,
                k: k.to_vec(),
                v: v.to_vec(),
                undo,
            });
        }
    }
}

impl Attention<'_> {
    /// Runs a batch whose first token sits at position `pos0`. With `grid`,
    /// token `t` rotates by the (time, row, column) position `grid[t]`
    /// instead of by `pos0 + t`. With `tree`, token `t` sits at
    /// `pos0 + tree.depth(t)` and attends only to the cache and its own
    /// path, so each token's output is what running its path alone gives;
    /// the cache then holds every token until [`KvCache::rollback`] keeps
    /// one path.
    pub fn forward(
        &self,
        h: &[f32],
        pos0: usize,
        grid: Option<&[[usize; 3]]>,
        tree: Option<&Tree>,
        cache: &mut KvCache,
    ) -> Vec<f32> {
        let n = h.len() / self.q.cols;
        let mixed = self.mix(self.project(h), n, pos0, grid, tree, cache);
        super::output(&self.o, &mixed)
    }

    /// The queries, keys and values of a batch, biases added, and the
    /// per-head gates when the model has them.
    pub(super) fn project(&self, h: &[f32]) -> Vec<Vec<f32>> {
        let n = h.len() / self.q.cols;
        let rotated;
        let h = match &self.folding {
            Some(f) => {
                rotated = f.rotate(h, self.q.cols);
                &rotated[..]
            }
            None => h,
        };
        let kv_dim = self.n_head_kv * self.head_dim;
        if let SharedKv::Borrows(_) = self.shared_kv {
            let mut q = vec![0.0; n * self.q.rows];
            matmul(&self.q, h, &mut q);
            return vec![q, Vec::new(), Vec::new()];
        }
        let mut q = vec![0.0; n * self.q.rows];
        let mut k = vec![0.0; n * kv_dim];
        let mut v = vec![0.0; n * kv_dim];
        let mut p = match &self.gate {
            Gate::PerHead(g) => {
                let mut head_gates = vec![0.0; n * self.n_head];
                matmul_many(
                    &[&self.q, &self.k, &self.v, g],
                    h,
                    &mut [&mut q, &mut k, &mut v, &mut head_gates],
                );
                vec![q, k, v, head_gates]
            }
            Gate::Interleaved | Gate::None => {
                matmul_many(
                    &[&self.q, &self.k, &self.v],
                    h,
                    &mut [&mut q, &mut k, &mut v],
                );
                vec![q, k, v]
            }
        };
        for (y, bias) in p.iter_mut().zip([&self.q_bias, &self.k_bias, &self.v_bias]) {
            if let Some(bias) = bias {
                for row in y.chunks_exact_mut(bias.len()) {
                    row.iter_mut().zip(bias).for_each(|(y, b)| *y += b);
                }
            }
        }
        if let Some(w) = &self.v_norm {
            pool::for_each_chunk(&mut p[2], self.head_dim, |_, head| {
                rms_norm(head, w, self.eps)
            });
        }
        p
    }

    /// [`Attention::forward`] from the projections of its `n` tokens, up to
    /// the input of the output projection.
    pub(super) fn mix(
        &self,
        p: Vec<Vec<f32>>,
        n: usize,
        pos0: usize,
        grid: Option<&[[usize; 3]]>,
        tree: Option<&Tree>,
        cache: &mut KvCache,
    ) -> Vec<f32> {
        assert!(grid.is_none() || tree.is_none(), "grid positions in a tree");
        let depth = |t: usize| tree.map_or(t, |tree| tree.depth(t));
        let hd = self.head_dim;
        let q_stride = self.q.rows;
        let kv_dim = self.n_head_kv * hd;
        let mut p = p.into_iter();
        let (mut q, mut k, mut v) = (
            p.next().expect("queries"),
            p.next().expect("keys"),
            p.next().expect("values"),
        );
        let head_gates = p.next();
        let borrowed = matches!(self.shared_kv, SharedKv::Borrows(_));
        if borrowed {
            (k, v) = cache.lent.take().expect("no keys lent to this layer");
        }

        let q_head_len = q_stride / self.n_head;
        let prepare = |t: usize, q: &mut [f32], mut k: Option<&mut [f32]>| {
            let angles = match grid {
                Some(grid) => self.rope.grid_angles(grid[t]),
                None => self.rope.angles(pos0 + depth(t)),
            };
            if !self.norm_after_rope {
                self.norm(q, q_head_len, &self.q_norm);
                k.iter_mut().for_each(|k| self.norm(k, hd, &self.k_norm));
            }
            for head in k.iter_mut().flat_map(|k| k.chunks_exact_mut(hd)) {
                self.rope.rotate(head, &angles);
            }
            for head in q.chunks_exact_mut(q_head_len) {
                self.rope.rotate(&mut head[..hd], &angles);
            }
            if self.norm_after_rope {
                self.norm(q, q_head_len, &self.q_norm);
                k.iter_mut().for_each(|k| self.norm(k, hd, &self.k_norm));
            }
        };
        if borrowed {
            pool::for_each_chunk(&mut q, q_stride, |t, q| prepare(t, q, None));
        } else {
            pool::for_each_chunk_pair(&mut q, q_stride, &mut k, kv_dim, |t, q, k| {
                prepare(t, q, Some(k))
            });
        }

        let slots = Slots {
            cache: &*cache,
            k: &k,
            v: &v,
            kv_dim,
            stored: cache.k.len() / kv_dim,
            pos0,
            window: self.window,
            paths: tree.map(|tree| (0..n).map(|t| tree.path(t)).collect()),
        };
        // Head-major, so that each task writes one contiguous run; every
        // head is padded to whole tasks.
        let blocks = n.div_ceil(QUERIES_PER_TASK);
        let padded = blocks * QUERIES_PER_TASK * hd;
        let mut by_head = vec![0.0; self.n_head * padded];
        pool::for_each_chunk(&mut by_head, QUERIES_PER_TASK * hd, |i, out| {
            let (head, t0) = (i / blocks, i % blocks * QUERIES_PER_TASK);
            let queries: Vec<Query> = (t0..n.min(t0 + QUERIES_PER_TASK))
                .map(|t| Query {
                    q: &q[t * q_stride + head * q_head_len..][..q_head_len],
                    gate: head_gates.as_ref().map(|g| g[t * self.n_head + head]),
                    t,
                })
                .collect();
            SCRATCH.with_borrow_mut(|scratch| {
                self.attend(
                    head,
                    &queries,
                    &slots,
                    scratch,
                    &mut out[..queries.len() * hd],
                )
            });
        });
        let mut out = vec![0.0; n * self.n_head * hd];
        for (head, by_token) in by_head.chunks_exact(padded).enumerate() {
            for (t, src) in by_token.chunks_exact(hd).take(n).enumerate() {
                out[(t * self.n_head + head) * hd..][..hd].copy_from_slice(src);
            }
        }
        for t in 0..n {
            let row = t * kv_dim..(t + 1) * kv_dim;
            cache.store(self.window, pos0 + depth(t), &k[row.clone()], &v[row]);
        }
        if self.shared_kv == SharedKv::Lends {
            cache.lent = Some((k, v));
        }
        match &self.folding {
            Some(f) => f.rotate(&out, self.o.cols),
            None => out,
        }
    }

    /// Normalizes one token's queries or keys: heads of `head_len` values
    /// whose first `head_dim` take the norm, or all of them at once.
    fn norm(&self, x: &mut [f32], head_len: usize, norm: &Option<Vec<f32>>) {
        match norm {
            Some(w) if w.len() == self.head_dim => x
                .chunks_exact_mut(head_len)
                .for_each(|head| rms_norm(&mut head[..self.head_dim], w, self.eps)),
            Some(w) => rms_norm(x, w, self.eps),
            None => {}
        }
    }

    /// Attends consecutive batch tokens of one head, writing `head_dim`
    /// values per token to `out`.
    ///
    /// Each token gets the arithmetic of attending it right after storing
    /// it, so its output is the same in any batch. While no token of the run
    /// has overwritten a ring slot, groups of four tokens share each pass
    /// over the keys they all see.
    fn attend(
        &self,
        head: usize,
        queries: &[Query],
        slots: &Slots,
        scratch: &mut Scratch,
        out: &mut [f32],
    ) {
        let hd = self.head_dim;
        let kv = head / (self.n_head / self.n_head_kv) * hd;
        let scale = self.scale.unwrap_or(1.0 / (hd as f32).sqrt());
        let width = queries
            .iter()
            .map(|query| slots.visible(query.t))
            .max()
            .expect("no queries");
        let Scratch { scores, runs } = scratch;
        scores.clear();
        scores.resize(queries.len() * width, 0.0);

        let grouped = if queries.iter().all(|query| slots.shared(query.t)) {
            queries.len() / 4 * 4
        } else {
            0
        };
        for (g, group) in queries[..grouped].chunks_exact(4).enumerate() {
            let q: [&[f32]; 4] = std::array::from_fn(|j| &group[j].q[..hd]);
            let common = slots.common(group[0].t);
            let mut rows = scores[4 * g * width..][..4 * width].chunks_exact_mut(width);
            let mut out: [&mut [f32]; 4] = std::array::from_fn(|_| rows.next().unwrap());
            slots.runs(group[0].t, runs);
            for run in runs.iter().filter_map(|run| run.clip(0..common)) {
                let span = run.slot..run.slot + run.len;
                let out = out.each_mut().map(|o| &mut o[span.clone()]);
                dot_rows(q, &slots.keys(&run)[kv..], slots.kv_dim, out);
            }
            // Past the slots all four see, each token goes on alone.
            for (j, query) in group.iter().enumerate() {
                slots.runs(query.t, runs);
                for run in runs.iter().filter_map(|run| run.clip(common..usize::MAX)) {
                    dot_rows(
                        [q[j]],
                        &slots.keys(&run)[kv..],
                        slots.kv_dim,
                        [&mut out[j][run.slot..run.slot + run.len]],
                    );
                }
            }
        }
        for (i, (query, out)) in queries.iter().zip(out.chunks_exact_mut(hd)).enumerate() {
            slots.runs(query.t, runs);
            let scores = &mut scores[i * width..][..slots.visible(query.t)];
            if i >= grouped {
                for run in runs.iter() {
                    dot_rows(
                        [&query.q[..hd]],
                        &slots.keys(run)[kv..],
                        slots.kv_dim,
                        [&mut scores[run.slot..run.slot + run.len]],
                    );
                }
            }
            scores.iter_mut().for_each(|s| *s *= scale);
            softmax(scores);
            for run in runs.iter() {
                let w = &scores[run.slot..run.slot + run.len];
                axpy_rows(out, w, &slots.values(run)[kv..], slots.kv_dim);
            }
            match (&self.gate, query.gate) {
                (Gate::Interleaved, _) => out
                    .iter_mut()
                    .zip(&query.q[hd..])
                    .for_each(|(o, g)| *o *= sigmoid(*g)),
                (Gate::PerHead(_), Some(g)) => {
                    let g = sigmoid(g);
                    out.iter_mut().for_each(|o| *o *= g);
                }
                _ => {}
            }
        }
    }
}

/// Batch tokens attended by one parallel task.
const QUERIES_PER_TASK: usize = 16;

thread_local! {
    static SCRATCH: std::cell::RefCell<Scratch> = std::cell::RefCell::default();
}

/// Buffers each thread reuses for all its tokens.
#[derive(Default)]
struct Scratch {
    /// Per token, its score for every slot of the widest token's view.
    scores: Vec<f32>,
    runs: Vec<Run>,
}

/// One head of one batch token: its normed and rotated query, followed by
/// its gate values when the output is gated that way, or its per-head gate.
struct Query<'a> {
    q: &'a [f32],
    gate: Option<f32>,
    t: usize,
}

/// The cache as each token of a batch sees it once the tokens before it,
/// and itself, have been stored one by one: every slot holds either an
/// entry stored before the batch or one of the batch's own keys and values.
struct Slots<'a> {
    cache: &'a KvCache,
    /// The batch's keys and values, one row of `kv_dim` per token.
    k: &'a [f32],
    v: &'a [f32],
    kv_dim: usize,
    /// Entries in the cache before the batch.
    stored: usize,
    pos0: usize,
    window: Option<usize>,
    /// For a tree batch, every token's path of batch rows from the first.
    paths: Option<Vec<Vec<usize>>>,
}

/// Where the entry in a slot lives.
enum Entry {
    Stored(usize),
    Batch(usize),
}

/// `len` consecutive slots from `slot` whose entries are consecutive rows,
/// from `row`, of the cache or of the batch.
#[derive(Clone, Copy)]
struct Run {
    slot: usize,
    len: usize,
    batch: bool,
    row: usize,
}

impl Run {
    /// The part of the run within `slots`, if any.
    fn clip(&self, slots: std::ops::Range<usize>) -> Option<Run> {
        let start = self.slot.max(slots.start);
        let end = (self.slot + self.len).min(slots.end);
        (start < end).then_some(Run {
            slot: start,
            len: end - start,
            batch: self.batch,
            row: self.row + start - self.slot,
        })
    }
}

impl Slots<'_> {
    /// Batch tokens between the tokens before the batch and token `t`.
    fn depth(&self, t: usize) -> usize {
        self.paths.as_ref().map_or(t, |paths| paths[t].len() - 1)
    }

    /// The batch row at depth `j` on the path of token `t`.
    fn row_at(&self, t: usize, j: usize) -> usize {
        self.paths.as_ref().map_or(j, |paths| paths[t][j])
    }

    /// Whether every token on the path of batch token `t` sees each slot
    /// hold the same entry, as when none of them has overwritten a ring
    /// slot.
    fn shared(&self, t: usize) -> bool {
        self.window.is_none_or(|w| self.stored + self.depth(t) < w)
    }

    /// Slots that batch token `t` attends over.
    fn visible(&self, t: usize) -> usize {
        let n = self.stored + self.depth(t) + 1;
        self.window.map_or(n, |w| n.min(w))
    }

    /// The leading slots that batch token `t` and the tokens after it see
    /// alike, when they all share their slots.
    fn common(&self, t: usize) -> usize {
        match self.paths {
            Some(_) => self.stored,
            None => self.visible(t),
        }
    }

    /// The slots batch token `t` sees, in order, as runs.
    fn runs(&self, t: usize, runs: &mut Vec<Run>) {
        runs.clear();
        let n = self.visible(t);
        let shared = self.shared(t);
        let stored = if shared { self.stored } else { 0 };
        if stored > 0 {
            runs.push(Run {
                slot: 0,
                len: stored,
                batch: false,
                row: 0,
            });
        }
        if shared && self.paths.is_none() {
            runs.push(Run {
                slot: stored,
                len: n - stored,
                batch: true,
                row: 0,
            });
            return;
        }
        for s in stored..n {
            let (batch, row) = match self.entry(s, t) {
                Entry::Stored(row) => (false, row),
                Entry::Batch(row) => (true, row),
            };
            match runs.last_mut() {
                Some(run) if run.batch == batch && run.row + run.len == row => run.len += 1,
                _ => runs.push(Run {
                    slot: s,
                    len: 1,
                    batch,
                    row,
                }),
            }
        }
    }

    /// Mirrors [`KvCache::store`] along the path of batch token `t`: the
    /// token at depth `j` is appended while the window has room and
    /// afterwards overwrites slot `(pos0 + j) % window`; a slot shows the
    /// latest token to write it.
    fn entry(&self, s: usize, t: usize) -> Entry {
        let depth = self.depth(t);
        let on_path = |j| Entry::Batch(self.row_at(t, j));
        let Some(w) = self.window else {
            return match s.checked_sub(self.stored) {
                Some(j) => on_path(j),
                None => Entry::Stored(s),
            };
        };
        let ring_from = w.saturating_sub(self.stored);
        let back = (self.pos0 + depth + w - s) % w;
        match depth.checked_sub(back) {
            Some(j) if j >= ring_from => on_path(j),
            _ => match s.checked_sub(self.stored) {
                Some(j) if j <= depth => on_path(j),
                _ => Entry::Stored(s),
            },
        }
    }

    /// The keys from the first row of `run` on.
    fn keys(&self, run: &Run) -> &[f32] {
        let rows = if run.batch { self.k } else { &self.cache.k };
        &rows[run.row * self.kv_dim..]
    }

    /// The values from the first row of `run` on.
    fn values(&self, run: &Run) -> &[f32] {
        let rows = if run.batch { self.v } else { &self.cache.v };
        &rows[run.row * self.kv_dim..]
    }
}

#[cfg(test)]
mod tests {
    use kinetic_quant::TensorType;

    use super::*;

    const D: usize = 16;
    const HEADS: usize = 4;
    const KV_HEADS: usize = 2;
    const HD: usize = 8;

    fn random(len: usize, seed: &mut u32) -> Vec<f32> {
        (0..len)
            .map(|_| {
                *seed = seed.wrapping_mul(1664525).wrapping_add(1013904223);
                (*seed >> 8) as f32 / (1 << 24) as f32 - 0.5
            })
            .collect()
    }

    fn bytes(v: &[f32]) -> Vec<u8> {
        v.iter().flat_map(|v| v.to_le_bytes()).collect()
    }

    /// Weights for the query (with room for interleaved gates), key, value
    /// and output projections.
    fn weights() -> [Vec<u8>; 4] {
        let mut seed = 7;
        [
            bytes(&random(2 * HEADS * HD * D, &mut seed)),
            bytes(&random(KV_HEADS * HD * D, &mut seed)),
            bytes(&random(KV_HEADS * HD * D, &mut seed)),
            bytes(&random(D * HEADS * HD, &mut seed)),
        ]
    }

    fn layer<'a>(w: &'a [Vec<u8>; 4], window: Option<usize>, gated: bool) -> Attention<'a> {
        let q_rows = if gated { 2 } else { 1 } * HEADS * HD;
        let f32 = |data: &'a [u8], rows, cols| Matrix::new(TensorType::F32, data, rows, cols);
        Attention {
            folding: None,
            q: f32(&w[0][..q_rows * D * 4], q_rows, D),
            k: f32(&w[1], KV_HEADS * HD, D),
            v: f32(&w[2], KV_HEADS * HD, D),
            o: f32(&w[3], D, HEADS * HD),
            gate: if gated { Gate::Interleaved } else { Gate::None },
            q_bias: None,
            k_bias: None,
            v_bias: None,
            q_norm: Some(vec![1.5; HD]),
            k_norm: None,
            norm_after_rope: false,
            n_head: HEADS,
            n_head_kv: KV_HEADS,
            head_dim: HD,
            rope: Rope {
                dims: HD,
                base: 10000.0,
                factors: None,
                layout: RopeLayout::Neox,
                mscale: 1.0,
            },
            window,
            scale: None,
            v_norm: None,
            shared_kv: SharedKv::No,
            eps: 1e-6,
        }
    }

    /// A batch gives every token exactly the output and cache entry it gets
    /// on its own, wherever the batch starts relative to the window ring;
    /// speculative decoding depends on it.
    #[test]
    fn batches_match_tokens_one_by_one() {
        let w = weights();
        let n = 20;
        let h = random(n * D, &mut 3);
        for (window, gated) in [
            (None, false),
            (None, true),
            (Some(5), false),
            (Some(5), true),
        ] {
            let att = layer(&w, window, gated);
            let mut alone = KvCache::default();
            let single: Vec<f32> = (0..n)
                .flat_map(|t| att.forward(&h[t * D..][..D], t, None, None, &mut alone))
                .collect();
            for split in [1, 3, 4, 5, 7, 12] {
                let mut cache = KvCache::default();
                let mut y = att.forward(&h[..split * D], 0, None, None, &mut cache);
                y.extend(att.forward(&h[split * D..], split, None, None, &mut cache));
                assert_eq!(y, single, "window {window:?} gated {gated} split {split}");
                assert_eq!((&cache.k, &cache.v), (&alone.k, &alone.v));
            }
        }
    }

    /// A layer borrowing keys and values attends exactly like one that
    /// projects them with the lender's weights from the lender's input.
    #[test]
    fn borrowed_keys_match_projected_ones() {
        let (w, other) = (
            weights(),
            weights().map(|m| bytes(&random(m.len() / 4, &mut 9))),
        );
        let h = random(12 * D, &mut 3);
        for window in [None, Some(5)] {
            let lender = Attention {
                shared_kv: SharedKv::Lends,
                ..layer(&w, window, false)
            };
            let borrower = Attention {
                shared_kv: SharedKv::Borrows(0),
                ..layer(&other, window, false)
            };
            let own = Attention {
                k: lender.k,
                v: lender.v,
                ..layer(&other, window, false)
            };
            let [mut lent, mut borrowed, mut want] = [(); 3].map(|_| KvCache::default());
            for (pos, rows) in [(0, 0..7), (7, 7..8), (8, 8..12)] {
                let h = &h[rows.start * D..rows.end * D];
                lender.forward(h, pos, None, None, &mut lent);
                borrowed.lent = lent.lent.take();
                let y = borrower.forward(h, pos, None, None, &mut borrowed);
                assert_eq!(y, own.forward(h, pos, None, None, &mut want), "{window:?}");
            }
        }
    }

    /// Sequences sharing a batch each get exactly what running alone gives.
    #[test]
    fn parts_match_their_sequences_alone() {
        use crate::blocks::{Mixer, MixerState, Part};

        let w = weights();
        let mixer = Mixer::Attention(layer(&w, Some(5), true));
        let lens = [(3, 1), (7, 4), (1, 1)];
        let mut seed = 5;
        let mut alone: Vec<(MixerState, Vec<f32>)> = Vec::new();
        let mut shared: Vec<MixerState> = Vec::new();
        for &(first, _) in &lens {
            let mut state = mixer.new_state();
            mixer.forward(&random(first * D, &mut seed), 0, None, None, &mut state);
            shared.push(state.clone());
            alone.push((state, Vec::new()));
        }
        let h: Vec<f32> = random(lens.iter().map(|l| l.1).sum::<usize>() * D, &mut seed);
        let mut at = 0;
        for ((first, n), (state, y)) in lens.iter().zip(&mut alone) {
            *y = mixer.forward(&h[at * D..(at + n) * D], *first, None, None, state);
            at += n;
        }
        let mut parts: Vec<Part> = lens
            .iter()
            .zip(&mut shared)
            .map(|(&(first, n), state)| Part {
                rows: n,
                pos0: first,
                state,
            })
            .collect();
        let y = mixer.forward_parts(&h, &mut parts);
        let want: Vec<f32> = alone.iter().flat_map(|a| a.1.clone()).collect();
        assert_eq!(y, want);
        for (s, (a, _)) in shared.iter().zip(&alone) {
            let (MixerState::Attention(s), MixerState::Attention(a)) = (s, a) else {
                unreachable!()
            };
            assert_eq!((&s.k, &s.v), (&a.k, &a.v));
        }
    }

    #[test]
    fn rollback_undoes_part_of_a_batch() {
        let w = weights();
        let h = random(13 * D, &mut 5);
        for window in [None, Some(5)] {
            let att = layer(&w, window, false);
            let mut want = KvCache::default();
            att.forward(&h[..10 * D], 0, None, None, &mut want);
            let mut cache = KvCache::default();
            att.forward(&h[..7 * D], 0, None, None, &mut cache);
            cache.checkpoint();
            att.forward(&h[7 * D..], 7, None, None, &mut cache);
            cache.rollback(&[0, 1, 2], window);
            assert_eq!(
                (&cache.k, &cache.v),
                (&want.k, &want.v),
                "window {window:?}"
            );
        }
    }

    /// Two trees side by side: rows 0 and 8 follow the tokens before.
    const PARENTS: [Option<usize>; 10] = [
        None,
        Some(0),
        Some(0),
        Some(1),
        Some(2),
        Some(1),
        Some(3),
        Some(4),
        None,
        Some(8),
    ];

    /// The rows of `h` on `path`, one after another.
    fn gather(h: &[f32], path: &[usize]) -> Vec<f32> {
        path.iter()
            .flat_map(|&r| &h[r * D..][..D])
            .copied()
            .collect()
    }

    /// Every row of a tree batch gets exactly the output it gets when its
    /// path from the root runs alone, wherever the batch starts relative to
    /// the window ring.
    #[test]
    fn tree_rows_match_their_paths_alone() {
        let w = weights();
        let tree = Tree::new(&PARENTS);
        let h = random(PARENTS.len() * D, &mut 11);
        for (window, gated) in [
            (None, false),
            (None, true),
            (Some(5), false),
            (Some(5), true),
        ] {
            let att = layer(&w, window, gated);
            for before in [0, 3, 4, 9] {
                let mut base = KvCache::default();
                if before > 0 {
                    att.forward(&random(before * D, &mut 13), 0, None, None, &mut base);
                }
                let mut cache = base.clone();
                let y = att.forward(&h, before, None, Some(&tree), &mut cache);
                for row in 0..PARENTS.len() {
                    let path = tree.path(row);
                    let alone =
                        att.forward(&gather(&h, &path), before, None, None, &mut base.clone());
                    assert_eq!(
                        &y[row * D..][..D],
                        &alone[alone.len() - D..],
                        "window {window:?} gated {gated} before {before} row {row}"
                    );
                }
            }
        }
    }

    /// Rolling a tree back to one path, whose rows are not contiguous in
    /// the batch, leaves the cache that running the path alone leaves.
    #[test]
    fn rollback_keeps_a_scattered_path() {
        let w = weights();
        let tree = Tree::new(&PARENTS);
        let h = random(PARENTS.len() * D, &mut 17);
        for window in [None, Some(5)] {
            let att = layer(&w, window, false);
            for before in [0, 3, 4, 9] {
                let mut base = KvCache::default();
                if before > 0 {
                    att.forward(&random(before * D, &mut 19), 0, None, None, &mut base);
                }
                for row in 0..PARENTS.len() {
                    let path = tree.path(row);
                    let mut want = base.clone();
                    att.forward(&gather(&h, &path), before, None, None, &mut want);
                    let mut cache = base.clone();
                    cache.checkpoint();
                    att.forward(&h, before, None, Some(&tree), &mut cache);
                    cache.rollback(&path, window);
                    assert_eq!(
                        (&cache.k, &cache.v),
                        (&want.k, &want.v),
                        "window {window:?} before {before} path {path:?}"
                    );
                }
            }
        }
    }

    #[test]
    fn rope_with_unit_factors_matches_plain_rope() {
        let mut a: Vec<f32> = (0..8).map(|i| i as f32 - 3.5).collect();
        let mut b = a.clone();
        let rope = Rope {
            dims: 8,
            base: 10000.0,
            factors: Some(vec![1.0; 4]),
            layout: RopeLayout::Neox,
            mscale: 1.0,
        };
        rope.apply(&mut a, 11);
        kinetic_cpu::rope_neox(&mut b, 8, 11, 10000.0);
        assert_eq!(a, b);
    }

    #[test]
    fn adjacent_layout_is_neox_on_interleaved_values() {
        let neox: Vec<f32> = (0..8).map(|i| i as f32 - 3.5).collect();
        let mut adjacent: Vec<f32> = (0..4).flat_map(|i| [neox[i], neox[i + 4]]).collect();
        let rope = |layout| Rope {
            dims: 8,
            base: 10000.0,
            factors: None,
            layout,
            mscale: 1.0,
        };
        let mut neox = neox.clone();
        rope(RopeLayout::Neox).apply(&mut neox, 7);
        rope(RopeLayout::Adjacent).apply(&mut adjacent, 7);
        let interleaved: Vec<f32> = (0..4).flat_map(|i| [neox[i], neox[i + 4]]).collect();
        assert_eq!(adjacent, interleaved);
    }

    #[test]
    fn huge_factors_leave_pairs_unrotated() {
        let mut x = [1.0, 2.0, 3.0, 4.0];
        Rope {
            dims: 4,
            base: 10000.0,
            factors: Some(vec![1.0, 1e30]),
            layout: RopeLayout::Neox,
            mscale: 1.0,
        }
        .apply(&mut x, 1000);
        assert_eq!([x[1], x[3]], [2.0, 4.0]);
        assert_ne!(x[0], 1.0);
    }

    #[test]
    fn only_the_first_dims_rotate() {
        let mut x = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0];
        Rope {
            dims: 4,
            base: 10000.0,
            factors: None,
            layout: RopeLayout::Neox,
            mscale: 1.0,
        }
        .apply(&mut x, 3);
        assert_eq!(&x[4..], &[5.0, 6.0]);
    }
}
