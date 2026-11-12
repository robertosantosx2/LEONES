//! The gated delta rule over a long batch in chunked matrix form.
//!
//! Within a chunk the delta updates depend on each other only through a unit
//! lower-triangular system, so a whole chunk costs one small triangular
//! inverse and a handful of matrix products against the state instead of a
//! pass over the state per token. The result equals the token-by-token
//! recurrence up to floating-point rounding.

#[cfg(target_arch = "x86_64")]
use std::arch::x86_64::*;

/// Tokens per chunk, the fastest by measurement: the products against the
/// state cost the same at any size, while the intra-chunk terms grow with it.
/// The last chunk of a batch is padded with tokens that
/// leave the state unchanged, so every product has fixed dimensions.
#[cfg(target_arch = "x86_64")]
const CHUNK: usize = 16;

/// One token's inputs to a head.
pub(super) struct Token<'a> {
    pub q: &'a [f32],
    pub k: &'a [f32],
    pub v: &'a [f32],
    /// Natural log of the decay.
    pub log_decay: f32,
    pub b: f32,
}

/// Whether [`run`] can handle heads of these dimensions on this CPU.
pub(super) fn available(dk: usize, dv: usize) -> bool {
    #[cfg(target_arch = "x86_64")]
    {
        dk.is_multiple_of(16)
            && dv.is_multiple_of(16)
            && is_x86_feature_detected!("avx2")
            && is_x86_feature_detected!("fma")
    }
    #[cfg(not(target_arch = "x86_64"))]
    {
        let _ = (dk, dv);
        false
    }
}

/// Runs `n` tokens through one head whose state `s` holds `dv` rows of `dk`
/// values, writing each token's `S q` after its update to `out`, `n` rows of
/// `dv`. Requires [`available`].
pub(super) fn run<'a>(
    s: &mut [f32],
    out: &mut [f32],
    dk: usize,
    dv: usize,
    token: impl Fn(usize) -> Token<'a>,
) {
    assert!(available(dk, dv), "chunked delta rule is unavailable");
    assert_eq!(s.len(), dv * dk);
    assert!(out.len().is_multiple_of(dv));
    #[cfg(target_arch = "x86_64")]
    // SAFETY: `available` confirmed AVX2 and FMA.
    unsafe {
        run_avx2(s, out, dk, dv, token)
    }
}

/// With `H = S^T` and, within a chunk, `G_t` the product of the decays up to
/// token `t`, the updates `D` (one row of `dv` per token) solve
/// `(I + A) D = b (V - G K H)` with `A_tj = b_t (k_t . k_j) G_t / G_j` for
/// `j < t`; the outputs are `G_t q_t H + sum_{j <= t} (q_t . k_j) G_t / G_j d_j`
/// and the state becomes `G_C H + sum_j (G_C / G_j) k_j d_j`.
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2,fma")]
fn run_avx2<'a>(
    s: &mut [f32],
    out: &mut [f32],
    dk: usize,
    dv: usize,
    token: impl Fn(usize) -> Token<'a>,
) {
    let c = CHUNK;
    let n = out.len() / dv;
    let mut h = vec![0.0; dk * dv];
    transpose(s, &mut h, dv, dk);
    // Keys in the first `c` rows, queries in the next, so one product serves both.
    let mut kq = vec![0.0; 2 * c * dk];
    let mut kt = vec![0.0; dk * c];
    let mut v = vec![0.0; c * dv];
    let (mut g, mut b) = (vec![0.0f32; c], vec![0.0f32; c]);
    let mut gram = vec![0.0; 2 * c * c];
    let mut w = vec![0.0; c];
    let mut t = vec![0.0; c * c];
    let mut proj = vec![0.0; 2 * c * dv];
    let mut d = vec![0.0; c * dv];
    let mut o = vec![0.0; c * dv];

    for start in (0..n).step_by(c) {
        let len = c.min(n - start);
        let (keys, queries) = kq.split_at_mut(c * dk);
        let mut log_g = 0.0;
        for i in 0..c {
            let (k, q, vi) = (
                &mut keys[i * dk..][..dk],
                &mut queries[i * dk..][..dk],
                &mut v[i * dv..][..dv],
            );
            if i < len {
                let tok = token(start + i);
                k.copy_from_slice(tok.k);
                q.copy_from_slice(tok.q);
                vi.copy_from_slice(tok.v);
                log_g += tok.log_decay;
                b[i] = tok.b;
            } else {
                k.fill(0.0);
                q.fill(0.0);
                vi.fill(0.0);
                b[i] = 0.0;
            }
            g[i] = log_g;
        }
        transpose(keys, &mut kt, c, dk);

        gram.fill(0.0);
        let (kk, qk) = gram.split_at_mut(c * c);
        gemm(keys, &kt, kk, dk, Triangle::C, 1.0);
        gemm(queries, &kt, qk, dk, Triangle::C, 1.0);
        for i in 0..c {
            for (w, gj) in w[..=i].iter_mut().zip(&g) {
                *w = (g[i] - gj).exp();
            }
            let (done, row) = t.split_at_mut(i * c);
            let row = &mut row[..c];
            row.fill(0.0);
            row[i] = 1.0;
            for j in 0..i {
                let a = b[i] * kk[i * c + j] * w[j];
                // Full rows (zero past the diagonal) vectorize better than exact lengths.
                row.iter_mut()
                    .zip(&done[j * c..][..c])
                    .for_each(|(x, y)| *x -= a * y);
            }
            let (seen, ahead) = qk[i * c..][..c].split_at_mut(i + 1);
            seen.iter_mut().zip(&w).for_each(|(x, w)| *x *= w);
            ahead.fill(0.0);
        }

        proj.fill(0.0);
        gemm(&kq, &h, &mut proj, dk, Triangle::None, 1.0);
        let (kh, qh) = proj.split_at(c * dv);
        for i in 0..c {
            let (gi, bi) = (g[i].exp(), b[i]);
            v[i * dv..][..dv]
                .iter_mut()
                .zip(&kh[i * dv..][..dv])
                .for_each(|(v, p)| *v = bi * (*v - gi * p));
            o[i * dv..][..dv]
                .iter_mut()
                .zip(&qh[i * dv..][..dv])
                .for_each(|(o, p)| *o = gi * p);
        }
        d.fill(0.0);
        gemm(&t, &v, &mut d, c, Triangle::A, 1.0);
        gemm(qk, &d, &mut o, c, Triangle::A, 1.0);
        out[start * dv..][..len * dv].copy_from_slice(&o[..len * dv]);

        let last = g[c - 1];
        for (row, g) in d.chunks_exact_mut(dv).zip(&g) {
            let f = (last - g).exp();
            row.iter_mut().for_each(|x| *x *= f);
        }
        gemm(&kt, &d, &mut h, c, Triangle::None, last.exp());
    }
    transpose(&h, s, dk, dv);
}

#[cfg(target_arch = "x86_64")]
/// Writes the transpose of `a`, `rows` x `cols`, to `at`.
fn transpose(a: &[f32], at: &mut [f32], rows: usize, cols: usize) {
    for (r, row) in a.chunks_exact(cols).take(rows).enumerate() {
        for (j, &x) in row.iter().enumerate() {
            at[j * rows + r] = x;
        }
    }
}

/// Which part of a product is known to vanish.
#[cfg(target_arch = "x86_64")]
#[derive(Clone, Copy, PartialEq, Eq)]
enum Triangle {
    None,
    /// `a` is lower-triangular.
    A,
    /// Only the lower triangle of `c` is wanted; tiles above it are skipped.
    C,
}

/// `c = beta c + a b` for row-major `a` (`m` x `k`), `b` (`k` x `n`) and
/// `c` (`m` x `n`), with `m` a multiple of 4 and `n` a multiple of 16. Each
/// 16-column panel of `b` stays in L1 while every row block passes over it.
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2,fma")]
fn gemm(a: &[f32], b: &[f32], c: &mut [f32], k: usize, tri: Triangle, beta: f32) {
    let (m, n) = (a.len() / k, b.len() / k);
    assert!(m.is_multiple_of(4) && n.is_multiple_of(16));
    assert!(a.len() == m * k && b.len() == k * n && c.len() == m * n);
    let beta = _mm256_set1_ps(beta);
    let (a, b, c) = (a.as_ptr(), b.as_ptr(), c.as_mut_ptr());
    for j in (0..n).step_by(16) {
        for i in (0..m).step_by(4) {
            if tri == Triangle::C && j > i + 3 {
                continue;
            }
            let depth = if tri == Triangle::A { k.min(i + 4) } else { k };
            let mut acc = [_mm256_setzero_ps(); 8];
            // SAFETY: the asserts bound every offset: rows `i..i + 4` are
            // below `m`, columns `j..j + 16` within `n`, and `p` below `k`.
            unsafe {
                for p in 0..depth {
                    let bp = b.add(p * n + j);
                    let (b0, b1) = (_mm256_loadu_ps(bp), _mm256_loadu_ps(bp.add(8)));
                    for r in 0..4 {
                        let x = _mm256_broadcast_ss(&*a.add((i + r) * k + p));
                        acc[2 * r] = _mm256_fmadd_ps(x, b0, acc[2 * r]);
                        acc[2 * r + 1] = _mm256_fmadd_ps(x, b1, acc[2 * r + 1]);
                    }
                }
                for r in 0..4 {
                    let cp = c.add((i + r) * n + j);
                    _mm256_storeu_ps(cp, _mm256_fmadd_ps(_mm256_loadu_ps(cp), beta, acc[2 * r]));
                    let cp = cp.add(8);
                    _mm256_storeu_ps(
                        cp,
                        _mm256_fmadd_ps(_mm256_loadu_ps(cp), beta, acc[2 * r + 1]),
                    );
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::blocks::delta_net::update;
    use kinetic_cpu::{dot, l2_norm};

    struct Lcg(u64);

    impl Lcg {
        fn next(&mut self) -> f32 {
            self.0 = self
                .0
                .wrapping_mul(6_364_136_223_846_793_005)
                .wrapping_add(1_442_695_040_888_963_407);
            (self.0 >> 40) as f32 / (1u64 << 24) as f32 * 2.0 - 1.0
        }
    }

    #[test]
    fn matches_the_recurrence() {
        let (dk, dv) = (32, 48);
        if !available(dk, dv) {
            return;
        }
        let n = 3 * CHUNK + 5;
        let mut rng = Lcg(7);
        let mut unit = |len: usize| {
            let mut x: Vec<f32> = (0..len).map(|_| rng.next()).collect();
            x.chunks_exact_mut(dk).for_each(|x| l2_norm(x, 1e-6));
            x
        };
        let (q, k) = (unit(n * dk), unit(n * dk));
        let v: Vec<f32> = (0..n * dv).map(|_| rng.next()).collect();
        let log_decay: Vec<f32> = (0..n).map(|_| -1.5 * (rng.next() + 1.0)).collect();
        let b: Vec<f32> = (0..n).map(|_| 0.5 * (rng.next() + 1.0)).collect();
        let s0: Vec<f32> = (0..dv * dk).map(|_| rng.next()).collect();

        let mut s = s0.clone();
        let mut want = vec![0.0; n * dv];
        for (t, o) in want.chunks_exact_mut(dv).enumerate() {
            let (q, k) = (&q[t * dk..][..dk], &k[t * dk..][..dk]);
            for ((row, &v), o) in s.chunks_exact_mut(dk).zip(&v[t * dv..]).zip(o) {
                update(row, k, v, log_decay[t].exp(), b[t]);
                *o = dot(row, q);
            }
        }

        let mut got_s = s0;
        let mut got = vec![0.0; n * dv];
        run(&mut got_s, &mut got, dk, dv, |t| Token {
            q: &q[t * dk..][..dk],
            k: &k[t * dk..][..dk],
            v: &v[t * dv..][..dv],
            log_decay: log_decay[t],
            b: b[t],
        });
        let err = |a: &[f32], b: &[f32]| {
            let scale = b.iter().fold(0.0f32, |m, x| m.max(x.abs()));
            a.iter()
                .zip(b)
                .fold(0.0f32, |m, (a, b)| m.max((a - b).abs()))
                / scale
        };
        assert!(err(&got, &want) < 1e-5, "outputs {}", err(&got, &want));
        assert!(err(&got_s, &s) < 1e-5, "state {}", err(&got_s, &s));
    }
}
