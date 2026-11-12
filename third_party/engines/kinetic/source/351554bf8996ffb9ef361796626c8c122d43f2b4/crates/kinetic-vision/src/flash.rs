//! Bidirectional attention in tiles of queries times blocks of keys, the
//! softmax kept running over the key blocks so that no row of scores is held
//! whole. The scores and the weighted values are register-tiled AVX2 products
//! in f32.

use std::arch::x86_64::*;

use rayon::prelude::*;

/// Queries of one register tile.
const MR: usize = 6;
/// Register tiles of one task; the task's keys are read once for all of them.
const GROUPS: usize = 4;
const QUERIES: usize = MR * GROUPS;
/// Keys of one block, in panels of 16.
const KEYS: usize = 64;

/// [`crate::ops::attention`], or `None` when this machine or `head_dim`
/// has no kernel here.
pub fn attention(qkv: &[f32], n_head: usize, head_dim: usize) -> Option<Vec<f32>> {
    let fits = head_dim > 0 && head_dim.is_multiple_of(16);
    if !(fits && is_x86_feature_detected!("avx2") && is_x86_feature_detected!("fma")) {
        return None;
    }
    let hd = head_dim;
    let width = n_head * hd;
    let stride = 3 * width;
    let n = qkv.len() / stride;
    let scale = 1.0 / (hd as f32).sqrt();
    let padded = n.div_ceil(KEYS) * KEYS;
    // keys as panels of 16 laid out [dim][key], values as rows, zero past n
    let mut keys = vec![0.0f32; padded * hd];
    let mut values = vec![0.0f32; padded * hd];
    let mut out = vec![0.0; n * width];
    for head in 0..n_head {
        let off = head * hd;
        keys.par_chunks_exact_mut(16 * hd)
            .zip(values.par_chunks_exact_mut(16 * hd))
            .enumerate()
            .for_each(|(p, (kp, vp))| {
                for (j, vrow) in vp.chunks_exact_mut(hd).enumerate() {
                    let t = p * 16 + j;
                    if t >= n {
                        break;
                    }
                    let k = &qkv[t * stride + width + off..][..hd];
                    for (d, &k) in k.iter().enumerate() {
                        kp[d * 16 + j] = k;
                    }
                    vrow.copy_from_slice(&qkv[t * stride + 2 * width + off..][..hd]);
                }
            });
        out.par_chunks_mut(QUERIES * width)
            .enumerate()
            .for_each(|(i, out)| {
                let mut q = vec![0.0; QUERIES * hd];
                for (r, q) in q.chunks_exact_mut(hd).take(out.len() / width).enumerate() {
                    let t = i * QUERIES + r;
                    let src = &qkv[t * stride + off..][..hd];
                    q.iter_mut().zip(src).for_each(|(q, s)| *q = s * scale);
                }
                let mut o = vec![0.0; QUERIES * hd];
                // SAFETY: AVX2 and FMA were detected; every buffer holds
                // whole tiles of `hd` values, `hd` a multiple of 16.
                unsafe { tile(&q, &keys, &values, n, hd, &mut o) };
                for (out, o) in out.chunks_exact_mut(width).zip(o.chunks_exact(hd)) {
                    out[off..][..hd].copy_from_slice(o);
                }
            });
    }
    Some(out)
}

/// Attention of [`QUERIES`] queries over `n` keys into `o`.
#[target_feature(enable = "avx2,fma")]
unsafe fn tile(q: &[f32], keys: &[f32], values: &[f32], n: usize, hd: usize, o: &mut [f32]) {
    let mut s = [0.0f32; MR * KEYS];
    let mut max = [f32::NEG_INFINITY; QUERIES];
    let mut sum = [0.0f32; QUERIES];
    for k0 in (0..n).step_by(KEYS) {
        let live = (n - k0).min(KEYS);
        let kb = &keys[k0 * hd..][..KEYS * hd];
        let vb = &values[k0 * hd..][..KEYS * hd];
        for g in 0..GROUPS {
            let rows = g * MR..(g + 1) * MR;
            let o = &mut o[g * MR * hd..][..MR * hd];
            scores(&q[g * MR * hd..][..MR * hd], kb, hd, &mut s);
            for ((s, o), (max, sum)) in s
                .chunks_exact_mut(KEYS)
                .zip(o.chunks_exact_mut(hd))
                .zip(max[rows.clone()].iter_mut().zip(&mut sum[rows]))
            {
                s[live..].fill(f32::NEG_INFINITY);
                let m = (*max).max(hmax(s));
                let c = (*max - m).exp();
                *sum = *sum * c + exp_row(s, m);
                *max = m;
                rescale(o, c);
            }
            weigh(&s, vb, hd, o);
        }
    }
    for (o, sum) in o.chunks_exact_mut(hd).zip(sum) {
        o.iter_mut().for_each(|v| *v /= sum);
    }
}

/// `s[i][j] = q[i] . key j` for the [`MR`] queries and the block's keys.
#[inline]
#[target_feature(enable = "avx2,fma")]
unsafe fn scores(q: &[f32], kb: &[f32], hd: usize, s: &mut [f32; MR * KEYS]) {
    let q = q.as_ptr();
    for p in 0..KEYS / 16 {
        let k = kb[p * 16 * hd..][..16 * hd].as_ptr();
        let mut acc = [[_mm256_setzero_ps(); 2]; MR];
        for d in 0..hd {
            let k0 = _mm256_loadu_ps(k.add(d * 16));
            let k1 = _mm256_loadu_ps(k.add(d * 16 + 8));
            for (i, acc) in acc.iter_mut().enumerate() {
                let x = _mm256_broadcast_ss(&*q.add(i * hd + d));
                acc[0] = _mm256_fmadd_ps(x, k0, acc[0]);
                acc[1] = _mm256_fmadd_ps(x, k1, acc[1]);
            }
        }
        for (i, acc) in acc.iter().enumerate() {
            let at = s.as_mut_ptr().add(i * KEYS + p * 16);
            _mm256_storeu_ps(at, acc[0]);
            _mm256_storeu_ps(at.add(8), acc[1]);
        }
    }
}

/// `o[i] += sum_j s[i][j] * value j`.
#[inline]
#[target_feature(enable = "avx2,fma")]
unsafe fn weigh(s: &[f32; MR * KEYS], vb: &[f32], hd: usize, o: &mut [f32]) {
    let (v, o, s) = (vb.as_ptr(), o.as_mut_ptr(), s.as_ptr());
    for c in (0..hd).step_by(16) {
        let mut acc = [[_mm256_setzero_ps(); 2]; MR];
        for (i, acc) in acc.iter_mut().enumerate() {
            acc[0] = _mm256_loadu_ps(o.add(i * hd + c));
            acc[1] = _mm256_loadu_ps(o.add(i * hd + c + 8));
        }
        for j in 0..KEYS {
            let v0 = _mm256_loadu_ps(v.add(j * hd + c));
            let v1 = _mm256_loadu_ps(v.add(j * hd + c + 8));
            for (i, acc) in acc.iter_mut().enumerate() {
                let w = _mm256_broadcast_ss(&*s.add(i * KEYS + j));
                acc[0] = _mm256_fmadd_ps(w, v0, acc[0]);
                acc[1] = _mm256_fmadd_ps(w, v1, acc[1]);
            }
        }
        for (i, acc) in acc.iter().enumerate() {
            _mm256_storeu_ps(o.add(i * hd + c), acc[0]);
            _mm256_storeu_ps(o.add(i * hd + c + 8), acc[1]);
        }
    }
}

#[inline]
#[target_feature(enable = "avx2,fma")]
unsafe fn hmax(s: &[f32]) -> f32 {
    let mut m = _mm256_set1_ps(f32::NEG_INFINITY);
    for c in s.chunks_exact(8) {
        m = _mm256_max_ps(m, _mm256_loadu_ps(c.as_ptr()));
    }
    let mut lanes = [0.0f32; 8];
    _mm256_storeu_ps(lanes.as_mut_ptr(), m);
    lanes.into_iter().fold(f32::NEG_INFINITY, f32::max)
}

/// `s = exp(s - m)` in place; returns the sum.
#[inline]
#[target_feature(enable = "avx2,fma")]
unsafe fn exp_row(s: &mut [f32], m: f32) -> f32 {
    let (m, mut total) = (_mm256_set1_ps(m), _mm256_setzero_ps());
    for c in s.chunks_exact_mut(8) {
        let e = exp(_mm256_sub_ps(_mm256_loadu_ps(c.as_ptr()), m));
        _mm256_storeu_ps(c.as_mut_ptr(), e);
        total = _mm256_add_ps(total, e);
    }
    let mut lanes = [0.0f32; 8];
    _mm256_storeu_ps(lanes.as_mut_ptr(), total);
    lanes.iter().sum()
}

#[inline]
#[target_feature(enable = "avx2,fma")]
unsafe fn rescale(o: &mut [f32], c: f32) {
    let c = _mm256_set1_ps(c);
    for v in o.chunks_exact_mut(8) {
        _mm256_storeu_ps(
            v.as_mut_ptr(),
            _mm256_mul_ps(_mm256_loadu_ps(v.as_ptr()), c),
        );
    }
}

/// `e^x` for `x <= 0` to about one ulp, flushed to zero below `-87`;
/// cephes expf: `x = n ln 2 + r`, a degree 7 polynomial for `e^r`.
#[inline]
#[target_feature(enable = "avx2,fma")]
unsafe fn exp(x: __m256) -> __m256 {
    let floor = _mm256_cmp_ps(x, _mm256_set1_ps(-87.0), _CMP_GE_OQ);
    let x = _mm256_max_ps(x, _mm256_set1_ps(-87.0));
    let n = _mm256_round_ps(
        _mm256_mul_ps(x, _mm256_set1_ps(std::f32::consts::LOG2_E)),
        _MM_FROUND_TO_NEAREST_INT | _MM_FROUND_NO_EXC,
    );
    let r = _mm256_fnmadd_ps(n, _mm256_set1_ps(0.693_359_4), x);
    let r = _mm256_fnmadd_ps(n, _mm256_set1_ps(-2.121_944_4e-4), r);
    let mut p = _mm256_set1_ps(1.987_569_1e-4);
    for c in [
        1.398_199_9e-3,
        8.333_452e-3,
        4.166_579_6e-2,
        0.166_666_66,
        0.5,
    ] {
        p = _mm256_fmadd_ps(p, r, _mm256_set1_ps(c));
    }
    let e = _mm256_fmadd_ps(
        p,
        _mm256_mul_ps(r, r),
        _mm256_add_ps(r, _mm256_set1_ps(1.0)),
    );
    let bias = _mm256_add_epi32(_mm256_cvtps_epi32(n), _mm256_set1_epi32(127));
    let pow2 = _mm256_castsi256_ps(_mm256_slli_epi32(bias, 23));
    _mm256_and_ps(_mm256_mul_ps(e, pow2), floor)
}

#[cfg(test)]
mod tests {
    use std::arch::x86_64::*;

    #[test]
    fn exp_matches_std() {
        if !is_x86_feature_detected!("avx2") || !is_x86_feature_detected!("fma") {
            return;
        }
        for i in 0..19_000 {
            let x = -(i as f32) * 0.0045;
            let mut lanes = [0.0f32; 8];
            // SAFETY: AVX2 and FMA were detected.
            unsafe { _mm256_storeu_ps(lanes.as_mut_ptr(), super::exp(_mm256_set1_ps(x))) };
            let want = x.exp();
            assert!((lanes[0] - want).abs() <= 2.0 * want * f32::EPSILON, "{x}");
        }
    }
}
