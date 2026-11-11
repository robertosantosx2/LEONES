//! The tensor operations of a vision transformer, on rows of f32 values.

use kinetic_cpu::{axpy_rows, dot_rows, matmul, softmax};
use kinetic_quant::Matrix;
use rayon::prelude::*;

use crate::Pixels;

/// A weight matrix and the bias added to its outputs.
#[derive(Clone)]
pub struct Linear<'a> {
    pub w: Matrix<'a>,
    pub b: Vec<f32>,
}

impl Linear<'_> {
    /// `x W^T + b` for every row of `x`.
    pub fn forward(&self, x: &[f32]) -> Vec<f32> {
        let mut y = vec![0.0; x.len() / self.w.cols * self.w.rows];
        matmul(&self.w, x, &mut y);
        add_rows(&mut y, &self.b);
        y
    }
}

/// Layer normalization with a learned scale and shift.
#[derive(Clone)]
pub struct LayerNorm {
    pub w: Vec<f32>,
    pub b: Vec<f32>,
    pub eps: f32,
}

impl LayerNorm {
    /// Normalizes every row of `x` in place.
    pub fn apply(&self, x: &mut [f32]) {
        x.par_chunks_exact_mut(self.w.len()).for_each(|row| {
            let n = row.len() as f32;
            let mean = row.iter().sum::<f32>() / n;
            let var = row.iter().map(|v| (v - mean) * (v - mean)).sum::<f32>() / n;
            let scale = 1.0 / (var + self.eps).sqrt();
            for ((v, w), b) in row.iter_mut().zip(&self.w).zip(&self.b) {
                *v = (*v - mean) * scale * w + b;
            }
        });
    }
}

/// RMS normalization of rows of `w.len()` values, with a learned scale or,
/// for an empty `w`, none.
#[derive(Clone)]
pub struct RmsNorm {
    pub w: Vec<f32>,
    pub eps: f32,
}

impl RmsNorm {
    /// Normalizes every row of `x`, each `width` values long, in place.
    pub fn apply(&self, x: &mut [f32], width: usize) {
        x.par_chunks_exact_mut(width).for_each(|row| {
            let ms = row.iter().map(|v| v * v).sum::<f32>() / width as f32;
            let scale = 1.0 / (ms + self.eps).sqrt();
            match self.w.is_empty() {
                true => row.iter_mut().for_each(|v| *v *= scale),
                false => row
                    .iter_mut()
                    .zip(&self.w)
                    .for_each(|(v, w)| *v *= scale * w),
            }
        });
    }
}

/// Adds `y` to `x`.
pub fn add(x: &mut [f32], y: &[f32]) {
    x.iter_mut().zip(y).for_each(|(x, y)| *x += y);
}

/// The `p x p` patches at (column, row) of `grid`, one row each of the
/// patch's channels, rows and columns in that order.
pub fn patches(pixels: &Pixels, p: usize, grid: &[(usize, usize)]) -> Vec<f32> {
    let plane = pixels.width * pixels.height;
    let mut out = vec![0.0; grid.len() * 3 * p * p];
    out.par_chunks_exact_mut(3 * p * p)
        .zip(grid)
        .for_each(|(out, &(px, py))| {
            for (c, out) in out.chunks_exact_mut(p * p).enumerate() {
                for (ky, out) in out.chunks_exact_mut(p).enumerate() {
                    let at = c * plane + (py * p + ky) * pixels.width + px * p;
                    out.copy_from_slice(&pixels.data[at..][..p]);
                }
            }
        });
    out
}

/// Adds `b` to every row of `x`.
pub fn add_rows(x: &mut [f32], b: &[f32]) {
    x.chunks_exact_mut(b.len())
        .for_each(|row| row.iter_mut().zip(b).for_each(|(x, b)| *x += b));
}

/// GELU in its tanh approximation.
pub fn gelu(x: f32) -> f32 {
    const SQRT_2_OVER_PI: f32 = 0.797_884_6;
    0.5 * x * (1.0 + (SQRT_2_OVER_PI * (x + 0.044_715 * x * x * x)).tanh())
}

/// Queries handed to one parallel task of [`attention`].
const QUERIES_PER_TASK: usize = 16;

/// Bidirectional multi-head attention. `qkv` holds one row per token of
/// `n_head` queries, then as many keys, then as many values, each `head_dim`
/// long; the result has one row of `n_head * head_dim` values per token.
pub fn attention(qkv: &[f32], n_head: usize, head_dim: usize) -> Vec<f32> {
    #[cfg(target_arch = "x86_64")]
    if let Some(out) = crate::flash::attention(qkv, n_head, head_dim) {
        return out;
    }
    let width = n_head * head_dim;
    let stride = 3 * width;
    let n = qkv.len() / stride;
    let scale = 1.0 / (head_dim as f32).sqrt();
    let mut out = vec![0.0; n * width];
    out.par_chunks_mut(QUERIES_PER_TASK * width)
        .enumerate()
        .for_each_init(Vec::new, |scores, (chunk, out)| {
            let t0 = chunk * QUERIES_PER_TASK;
            let count = out.len() / width;
            scores.resize(4 * n, 0.0);
            for head in 0..n_head {
                let off = head * head_dim;
                let keys = &qkv[width + off..];
                let values = &qkv[2 * width + off..];
                for g in (0..count).step_by(4) {
                    let m = (count - g).min(4);
                    let q = |j: usize| {
                        let t = t0 + g + j.min(m - 1);
                        &qkv[t * stride + off..][..head_dim]
                    };
                    let mut rows = scores.chunks_exact_mut(n);
                    let s: [&mut [f32]; 4] = std::array::from_fn(|_| rows.next().unwrap());
                    dot_rows([q(0), q(1), q(2), q(3)], keys, stride, s);
                    for j in 0..m {
                        let s = &mut scores[j * n..][..n];
                        s.iter_mut().for_each(|s| *s *= scale);
                        softmax(s);
                        let o = &mut out[(g + j) * width + off..][..head_dim];
                        axpy_rows(o, s, values, stride);
                    }
                }
            }
        });
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn random(len: usize, seed: &mut u32) -> Vec<f32> {
        (0..len)
            .map(|_| {
                *seed = seed.wrapping_mul(1664525).wrapping_add(1013904223);
                (*seed >> 8) as f32 / (1 << 24) as f32 - 0.5
            })
            .collect()
    }

    #[test]
    fn attention_matches_naive() {
        for (n, heads, hd) in [(37, 3, 8), (131, 2, 32)] {
            attention_matches_naive_at(n, heads, hd);
        }
    }

    fn attention_matches_naive_at(n: usize, heads: usize, hd: usize) {
        let w = heads * hd;
        let qkv = random(n * 3 * w, &mut 11);
        let got = attention(&qkv, heads, hd);
        for t in 0..n {
            for h in 0..heads {
                let q = &qkv[t * 3 * w + h * hd..][..hd];
                let mut s: Vec<f32> = (0..n)
                    .map(|j| {
                        let k = &qkv[j * 3 * w + w + h * hd..][..hd];
                        q.iter().zip(k).map(|(a, b)| a * b).sum::<f32>() / (hd as f32).sqrt()
                    })
                    .collect();
                let max = s.iter().copied().fold(f32::NEG_INFINITY, f32::max);
                let sum: f32 = s
                    .iter_mut()
                    .map(|v| {
                        *v = (*v - max).exp();
                        *v
                    })
                    .sum();
                for i in 0..hd {
                    let want: f32 = (0..n)
                        .map(|j| s[j] / sum * qkv[j * 3 * w + 2 * w + h * hd + i])
                        .sum();
                    let got = got[t * w + h * hd + i];
                    assert!(
                        (got - want).abs() < 1e-5,
                        "token {t} head {h}: {got} vs {want}"
                    );
                }
            }
        }
    }

    #[test]
    fn layer_norm_centers_and_scales() {
        let norm = LayerNorm {
            w: vec![2.0; 4],
            b: vec![1.0; 4],
            eps: 0.0,
        };
        let mut x = vec![1.0, 2.0, 3.0, 4.0];
        norm.apply(&mut x);
        let mean: f32 = x.iter().sum::<f32>() / 4.0;
        assert!((mean - 1.0).abs() < 1e-6);
        assert!((x[3] - x[0] - 2.0 * 3.0 / 1.25f32.sqrt()).abs() < 1e-5);
    }
}
