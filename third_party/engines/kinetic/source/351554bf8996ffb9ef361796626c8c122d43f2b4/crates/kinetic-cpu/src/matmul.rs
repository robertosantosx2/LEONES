//! Quantized matrix products over a batch of tokens.
//!
//! The work is cut into tiles of weight rows times tokens. Large enough
//! batches of K-quant, Q8_0 and Q4_0 weights go through the tile kernels: a
//! tile's rows are unpacked once and every group of eight interleaved tokens
//! streams through them. Short batches take the one-row kernels, a few
//! tokens at a time, and f16 / bf16 weights a kernel of four rows times
//! three tokens. Every path gives bit-identical values for the same row and
//! token, so the path a value takes never shows in the result.

use std::cell::RefCell;
use std::ops::Range;

use kinetic_quant::{dequantize, Matrix};

use crate::fdot;
use crate::kdot::{self, Block, DotFn, DotNFn, TileKernel, Unpacked, Unpacked32, TILE_ROWS};
use crate::ops;
use crate::pool;
use crate::q8::{Q8Group, Q8};
use crate::q8k::{Q8KGroup, GROUP, Q8K, QK_K};

/// Rows handed to one rayon task when decoding; large enough to amortize
/// scheduling.
const ROWS_PER_TASK: usize = 16;

/// Tile shape for batches.
const BATCH_ROWS: usize = 64;
const BATCH_TOKENS: usize = 64;

/// Unpacked bytes of a tile's rows, which sizes tiles: long rows get fewer
/// rows per tile.
// perf: sized for L2 back when tiles were unpacked whole, still the best split
const UNPACKED_BYTES: usize = 192 << 10;

/// Smallest batch for the tile kernels; two tokens already run cheaper
/// tiled than through the one-row kernels.
const MIN_TILE_TOKENS: usize = 2;

/// `Y = X W^T` for a batch: `x` holds `n` rows of `w.cols` values and `y`
/// receives `n` rows of `w.rows`. Each weight row is unpacked once for many
/// tokens, which is what makes prefill faster than repeated `matvec`.
///
/// Every output value is computed the same way whatever the batch size and
/// wherever its token sits in the batch.
pub fn matmul(w: &Matrix, x: &[f32], y: &mut [f32]) {
    matmul_many(&[w], x, &mut [y]);
}

/// [`matmul`] for several weights that share the input `x`, as one parallel
/// job. The input is quantized once and small matrices do not each pay for a
/// separate fork and join.
pub fn matmul_many(ws: &[&Matrix], x: &[f32], ys: &mut [&mut [f32]]) {
    assert_eq!(ws.len(), ys.len());
    let cols = ws.first().map_or(0, |w| w.cols);
    assert!(cols > 0 && x.len().is_multiple_of(cols));
    let n = x.len() / cols;
    for (w, y) in ws.iter().zip(ys.iter()) {
        assert_eq!(w.cols, cols, "weights must share the input width");
        assert_eq!(y.len(), n * w.rows);
    }

    let paths: Vec<Path> = ws.iter().map(|w| Path::of(w, n)).collect();
    let needs = |want: fn(Path) -> bool| paths.iter().any(|&p| want(p));
    let xk: Vec<Q8K> = if needs(|p| matches!(p, Path::K(_))) {
        pool::map(n, |t| Q8K::quantize(&x[t * cols..][..cols]))
    } else {
        Vec::new()
    };
    let gk: Vec<Q8KGroup> = if needs(|p| matches!(p, Path::K(Some(_)))) {
        pool::map(n.div_ceil(GROUP), |g| {
            Q8KGroup::new(&xk[g * GROUP..n.min(g * GROUP + GROUP)])
        })
    } else {
        Vec::new()
    };
    let x32: Vec<Q8> = if needs(|p| matches!(p, Path::B32(_))) {
        pool::map(n, |t| Q8::quantize(&x[t * cols..][..cols]))
    } else {
        Vec::new()
    };
    let g32: Vec<Q8Group> = if needs(|p| matches!(p, Path::B32(Some(_)))) {
        pool::map(n.div_ceil(GROUP), |g| {
            Q8Group::new(&x32[g * GROUP..n.min(g * GROUP + GROUP)])
        })
    } else {
        Vec::new()
    };
    let input = Input {
        x,
        xk: &xk,
        gk: &gk,
        x32: &x32,
        g32: &g32,
    };

    let tile_tokens = if n == 1 { 1 } else { BATCH_TOKENS };
    let token_tiles = n.div_ceil(tile_tokens);
    let mut first = 0;
    let plans: Vec<Plan> = ws
        .iter()
        .zip(&paths)
        .zip(ys.iter_mut())
        .map(|((&w, &path), y)| {
            let rows = if n == 1 {
                ROWS_PER_TASK
            } else if let Some(bytes) = path.unpacked_row_bytes(w) {
                let rows = UNPACKED_BYTES / bytes;
                (rows / TILE_ROWS * TILE_ROWS).clamp(TILE_ROWS, BATCH_ROWS)
            } else {
                BATCH_ROWS
            };
            let plan = Plan {
                w,
                path,
                rows,
                first,
                out: Out(y.as_mut_ptr()),
            };
            first += w.rows.div_ceil(rows) * token_tiles;
            plan
        })
        .collect();
    pool::for_each(first, &|i| {
        let plan = plans
            .iter()
            .rev()
            .find(|p| p.first <= i)
            .expect("first plan");
        let (r, t) = (
            (i - plan.first) / token_tiles,
            (i - plan.first) % token_tiles,
        );
        let (r, t) = (r * plan.rows, t * tile_tokens);
        let tile = Tile {
            w: plan.w,
            path: plan.path,
            rows: r..plan.w.rows.min(r + plan.rows),
            tokens: t..n.min(t + tile_tokens),
            out: plan.out,
        };
        SCRATCH.with_borrow_mut(|scratch| tile.run(&input, scratch));
    });
}

thread_local! {
    static SCRATCH: RefCell<Scratch> = RefCell::default();
}

/// The tiles of one matrix: `rows` weight rows per tile, numbered from
/// task `first` row tile by row tile.
struct Plan<'a, 'w> {
    w: &'a Matrix<'w>,
    path: Path,
    rows: usize,
    first: usize,
    out: Out,
}

/// How the products of one matrix are computed, with the tile kernel when
/// the batch is large enough for one.
#[derive(Clone, Copy)]
enum Path {
    /// K-quant integer kernels on [`Q8K`] activations.
    K(Option<TileKernel<Unpacked, Q8KGroup>>),
    /// Q8_0 and Q4_0 integer kernels on [`Q8`] activations.
    B32(Option<TileKernel<Unpacked32, Q8Group>>),
    /// f16 and bf16 weights on f32 activations.
    Float,
    /// Rows dequantized to f32.
    Dequantized,
}

impl Path {
    fn of(w: &Matrix, n: usize) -> Path {
        let tiled = n >= MIN_TILE_TOKENS;
        if kdot::kernel(w.ty).is_some() && w.cols.is_multiple_of(QK_K) {
            Path::K(kdot::tile_kernel(w.ty).filter(|_| tiled))
        } else if kdot::kernel32(w.ty).is_some() {
            Path::B32(kdot::tile_kernel32(w.ty).filter(|_| tiled))
        } else if fdot::supported(w.ty) {
            Path::Float
        } else {
            Path::Dequantized
        }
    }

    /// Bytes of one unpacked row, for the tile kernels.
    fn unpacked_row_bytes(self, w: &Matrix) -> Option<usize> {
        let blocks = w.cols / w.ty.block_len();
        match self {
            Path::K(Some(_)) => Some(blocks * size_of::<Unpacked>()),
            Path::B32(Some(_)) => Some(blocks * size_of::<Unpacked32>()),
            _ => None,
        }
    }
}

/// The batch in every form the kernels read.
struct Input<'a> {
    x: &'a [f32],
    xk: &'a [Q8K],
    gk: &'a [Q8KGroup],
    x32: &'a [Q8],
    g32: &'a [Q8Group],
}

#[derive(Default)]
struct Scratch {
    row: Vec<f32>,
    unpacked: Vec<Unpacked>,
    unpacked32: Vec<Unpacked32>,
}

/// The output of one matrix, token-major with `w.rows` values per token.
#[derive(Clone, Copy)]
struct Out(*mut f32);

// SAFETY: every tile writes a disjoint set of (token, row) cells, and the
// buffer outlives the parallel loop that holds these pointers.
unsafe impl Send for Out {}
unsafe impl Sync for Out {}

/// A block of rows times a block of tokens of one matrix product. Token
/// blocks start at multiples of [`GROUP`].
struct Tile<'a, 'w> {
    w: &'a Matrix<'w>,
    path: Path,
    rows: Range<usize>,
    tokens: Range<usize>,
    out: Out,
}

impl Tile<'_, '_> {
    fn run(&self, input: &Input, scratch: &mut Scratch) {
        let ty = self.w.ty;
        match self.path {
            Path::K(Some(kernel)) => self.run_tiled(kernel, input.gk, &mut scratch.unpacked),
            Path::K(None) => self.run_rows(
                input.xk,
                kdot::kernel(ty).expect("K-quant kernel"),
                kdot::kernel_n(ty),
                kdot::kernel_n(ty),
                kdot::kernel_n(ty),
            ),
            Path::B32(Some(kernel)) => self.run_tiled(kernel, input.g32, &mut scratch.unpacked32),
            Path::B32(None) => self.run_rows(
                input.x32,
                kdot::kernel32(ty).expect("32-value kernel"),
                kdot::kernel32_n(ty),
                kdot::kernel32_n(ty),
                kdot::kernel32_n(ty),
            ),
            Path::Float => self.run_float(input.x),
            Path::Dequantized => self.run_dequantized(input.x, &mut scratch.row),
        }
    }

    fn set(&self, t: usize, r: usize, v: f32) {
        debug_assert!(self.tokens.contains(&t) && self.rows.contains(&r));
        // SAFETY: (t, r) lies inside this tile, which no other tile covers,
        // and inside the `n * w.rows` output checked by `matmul_many`.
        unsafe { *self.out.0.add(t * self.w.rows + r) = v }
    }

    fn run_tiled<U: Block, G>(
        &self,
        kernel: TileKernel<U, G>,
        groups: &[G],
        unpacked: &mut Vec<U>,
    ) {
        let w = self.w;
        let blocks = w.cols / w.ty.block_len();
        // Unpacking overwrites everything the kernel reads, so the buffer is
        // only grown, never cleared.
        if unpacked.len() < TILE_ROWS * blocks {
            unpacked.resize(TILE_ROWS * blocks, U::ZERO);
        }
        let groups = &groups[self.tokens.start / GROUP..self.tokens.end.div_ceil(GROUP)];
        // perf: one quad at a time keeps its unpacked rows in L1 and the
        // weights streaming in while the kernel runs, ~25% off 8 tokens
        for r in self.rows.clone().step_by(TILE_ROWS) {
            let quad = r..self.rows.end.min(r + TILE_ROWS);
            for (r, out) in quad.clone().zip(unpacked.chunks_exact_mut(blocks)) {
                (kernel.unpack)(w.row(r), out);
            }
            let row = |i: usize| &unpacked[i * blocks..][..blocks];
            for (g, x) in groups.iter().enumerate() {
                let t0 = self.tokens.start + g * GROUP;
                let valid = GROUP.min(self.tokens.end - t0);
                let store = |r: usize, v: &[f32; GROUP]| {
                    for (i, &v) in v[..valid].iter().enumerate() {
                        self.set(t0 + i, r, v);
                    }
                };
                if quad.len() == TILE_ROWS {
                    let v = (kernel.dot4)(std::array::from_fn(row), x);
                    for (i, v) in v.iter().enumerate() {
                        store(r + i, v);
                    }
                } else {
                    for i in 0..quad.len() {
                        store(r + i, &(kernel.dot1)(row(i), x));
                    }
                }
            }
        }
    }

    fn run_rows<X>(
        &self,
        xq: &[X],
        dot: DotFn<X>,
        dot4: Option<DotNFn<X, 4>>,
        dot3: Option<DotNFn<X, 3>>,
        dot2: Option<DotNFn<X, 2>>,
    ) {
        let w = self.w;
        let mut t = self.tokens.start;
        while t < self.tokens.end {
            let left = self.tokens.end - t;
            let take = match (dot4, dot3, dot2) {
                (Some(dot4), Some(dot3), Some(dot2)) if left > 1 => {
                    let take = left.min(4);
                    let x = &xq[t..t + take];
                    for r in self.rows.clone() {
                        let row = w.row(r);
                        let v = match take {
                            4 => dot4(row, [&x[0], &x[1], &x[2], &x[3]]),
                            3 => pad(dot3(row, [&x[0], &x[1], &x[2]])),
                            _ => pad(dot2(row, [&x[0], &x[1]])),
                        };
                        for (i, &v) in v[..take].iter().enumerate() {
                            self.set(t + i, r, v);
                        }
                    }
                    take
                }
                _ => {
                    for r in self.rows.clone() {
                        self.set(t, r, dot(w.row(r), &xq[t]));
                    }
                    1
                }
            };
            t += take;
        }
    }

    fn run_float(&self, x: &[f32]) {
        let w = self.w;
        let token = |t: usize| &x[t * w.cols..][..w.cols];
        for t0 in self.tokens.clone().step_by(fdot::TOKENS) {
            let mut xs = [token(t0); fdot::TOKENS];
            let len = fdot::TOKENS.min(self.tokens.end - t0);
            for (i, x) in xs[..len].iter_mut().enumerate() {
                *x = token(t0 + i);
            }
            let mut r = self.rows.start;
            while r < self.rows.end {
                let take = if self.rows.end - r >= fdot::ROWS {
                    fdot::ROWS
                } else {
                    1
                };
                let rows: [&[u8]; fdot::ROWS] = std::array::from_fn(|i| w.row(r + i.min(take - 1)));
                let v = fdot::dots(w.ty, &rows[..take], &xs[..len]);
                for (i, v) in v[..take].iter().enumerate() {
                    for (j, &v) in v[..len].iter().enumerate() {
                        self.set(t0 + j, r + i, v);
                    }
                }
                r += take;
            }
        }
    }

    fn run_dequantized(&self, x: &[f32], row: &mut Vec<f32>) {
        let w = self.w;
        row.resize(w.cols, 0.0);
        for r in self.rows.clone() {
            dequantize(w.ty, w.row(r), row).expect("unsupported weight type");
            for t in self.tokens.clone() {
                self.set(t, r, ops::dot(row, &x[t * w.cols..][..w.cols]));
            }
        }
    }
}

fn pad<const N: usize>(v: [f32; N]) -> [f32; 4] {
    std::array::from_fn(|i| v.get(i).copied().unwrap_or(0.0))
}

#[cfg(test)]
mod tests {
    use kinetic_quant::TensorType;

    use super::*;
    use crate::kdot::tests::{extreme_row, random_row, Lcg};

    /// Each (row, token) value must not depend on the batch: speculative
    /// decoding relies on a batched pass reproducing single-token passes.
    #[test]
    fn batched_values_match_single_tokens() {
        let rows = BATCH_ROWS + TILE_ROWS + 3;
        for (ty, cols) in [
            (TensorType::Q4K, 9 * QK_K),
            (TensorType::Q5K, 9 * QK_K),
            (TensorType::Q6K, 9 * QK_K),
            (TensorType::Q8_0, 9 * QK_K),
            (TensorType::Q4_0, 9 * QK_K),
            (TensorType::Q8_0, 28 * 32),
            (TensorType::Q4_0, 20 * 32),
            (TensorType::Q2K, 9 * QK_K),
            (TensorType::Q3K, 9 * QK_K),
            (TensorType::TQ1_0, 9 * QK_K),
            (TensorType::TQ2_0, 9 * QK_K),
            (TensorType::PQ2_0, 9 * QK_K),
            (TensorType::IQ3S, 9 * QK_K),
            (TensorType::IQ2S, 9 * QK_K),
            (TensorType::IQ1S, 9 * QK_K),
            (TensorType::IQ1M, 9 * QK_K),
            (TensorType::Q4_1, 20 * 32),
            (TensorType::Q5_0, 20 * 32),
            (TensorType::Q5_1, 20 * 32),
            (TensorType::IQ4NL, 20 * 32),
            (TensorType::MXFP4, 20 * 32),
            (TensorType::F16, 581),
            (TensorType::BF16, 576),
        ] {
            let mut rng = Lcg(ty as u64);
            let per_row = cols / ty.block_len();
            let quantized = ty.block_len() > 1;
            let data: Vec<u8> = (0..rows)
                .flat_map(|r| {
                    if r == 1 && quantized {
                        extreme_row(ty, per_row, &mut rng)
                    } else {
                        random_row(ty, per_row, &mut rng)
                    }
                })
                .collect();
            let w = Matrix::new(ty, &data, rows, cols);
            let n_max = BATCH_TOKENS + GROUP + 3;
            let mut x: Vec<f32> = (0..n_max * cols).map(|_| rng.f32() * 2.0).collect();
            x[..cols].fill(1.0);

            let single: Vec<Vec<f32>> = x
                .chunks_exact(cols)
                .map(|x| {
                    let mut y = vec![0.0; rows];
                    matmul(&w, x, &mut y);
                    y
                })
                .collect();
            for n in [2, 3, 5, MIN_TILE_TOKENS - 1, MIN_TILE_TOKENS, 13, n_max] {
                for start in [0, 1, 6] {
                    let n = n.min(n_max - start);
                    let mut y = vec![0.0; n * rows];
                    matmul(&w, &x[start * cols..][..n * cols], &mut y);
                    for (t, y) in y.chunks_exact(rows).enumerate() {
                        assert_eq!(y, &single[start + t][..], "{ty} n {n} start {start} t {t}");
                    }
                }
            }
        }
    }

    /// The fast paths agree with dequantized weights up to the rounding of
    /// the activations: each value is off by at most half its block's
    /// step, `max |x| / 254`.
    #[test]
    fn products_match_the_reference() {
        let (rows, cols) = (9, 20 * 32);
        for ty in [TensorType::Q8_0, TensorType::Q4_0, TensorType::F16] {
            let mut rng = Lcg(ty as u64 + 11);
            let data = random_row(ty, rows * cols / ty.block_len(), &mut rng);
            let w = Matrix::new(ty, &data, rows, cols);
            let n = 2 * MIN_TILE_TOKENS;
            let x: Vec<f32> = (0..n * cols).map(|_| rng.f32()).collect();
            let mut y = vec![0.0; n * rows];
            matmul(&w, &x, &mut y);
            let mut dense = vec![0.0; cols];
            for r in 0..rows {
                dequantize(ty, w.row(r), &mut dense).unwrap();
                let bound = dense.iter().map(|v| v.abs()).sum::<f32>() / 254.0 + 1e-4;
                for t in 0..n {
                    let want = ops::dot(&dense, &x[t * cols..][..cols]);
                    let got = y[t * rows + r];
                    assert!((got - want).abs() <= bound, "{ty} row {r}: {got} vs {want}");
                }
            }
        }
    }

    #[test]
    fn matmul_many_matches_separate_products() {
        let mut rng = Lcg(3);
        let cols = QK_K;
        let a = random_row(TensorType::Q4K, 5, &mut rng);
        let b = random_row(TensorType::Q8_0, 3 * 8, &mut rng);
        let (wa, wb) = (
            Matrix::new(TensorType::Q4K, &a, 5, cols),
            Matrix::new(TensorType::Q8_0, &b, 3, cols),
        );
        let n = 11;
        let x: Vec<f32> = (0..n * cols).map(|_| rng.f32()).collect();
        let (mut ya, mut yb) = (vec![0.0; n * 5], vec![0.0; n * 3]);
        matmul_many(&[&wa, &wb], &x, &mut [&mut ya, &mut yb]);
        let (mut za, mut zb) = (vec![0.0; n * 5], vec![0.0; n * 3]);
        matmul(&wa, &x, &mut za);
        matmul(&wb, &x, &mut zb);
        assert_eq!((ya, yb), (za, zb));
    }
}
