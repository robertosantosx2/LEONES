use std::sync::OnceLock;

/// An activation vector quantized for integer dot products with K-quant
/// weights: blocks of 256 int8 values with one f32 scale, plus the sums of
/// every 16 and every 32 values so weight offsets can be applied without
/// touching `qs`.
pub struct Q8K {
    pub d: Vec<f32>,
    pub qs: Vec<i8>,
    pub bsums: Vec<i16>,
    pub bsums32: Vec<i16>,
    strided: OnceLock<(Vec<i8>, Vec<i32>)>,
}

pub const QK_K: usize = 256;

impl Q8K {
    pub fn quantize(x: &[f32]) -> Q8K {
        assert_eq!(
            x.len() % QK_K,
            0,
            "length {} is not a multiple of {QK_K}",
            x.len()
        );
        let blocks = x.len() / QK_K;
        let mut q = Q8K {
            d: Vec::with_capacity(blocks),
            qs: vec![0; x.len()],
            bsums: Vec::with_capacity(blocks * 16),
            bsums32: Vec::with_capacity(blocks * 8),
            strided: OnceLock::new(),
        };
        for (src, dst) in x.chunks_exact(QK_K).zip(q.qs.chunks_exact_mut(QK_K)) {
            q.d.push(quantize_block(src, dst));
            // i32 sums vectorize, 16 values still fit an i16
            q.bsums.extend(
                dst.chunks_exact(16)
                    .map(|g| g.iter().map(|&v| v as i32).sum::<i32>() as i16),
            );
            let sums16 = &q.bsums[q.bsums.len() - 16..];
            q.bsums32
                .extend(sums16.chunks_exact(2).map(|p| p[0] + p[1]));
        }
        q
    }

    /// `qs` with each run of 128 reordered so value `4i + k` sits at
    /// `32k + i`, the order PQ2_0 codes unpack in, and the sum of each run;
    /// built on first use.
    pub fn strided(&self) -> (&[i8], &[i32]) {
        let (values, sums) = self.strided.get_or_init(|| {
            let mut out = vec![0; self.qs.len()];
            for (src, dst) in self.qs.chunks_exact(128).zip(out.chunks_exact_mut(128)) {
                for (j, &v) in src.iter().enumerate() {
                    dst[32 * (j % 4) + j / 4] = v;
                }
            }
            let sums = self
                .bsums
                .chunks_exact(8)
                .map(|s| s.iter().map(|&v| v as i32).sum())
                .collect();
            (out, sums)
        });
        (values, sums)
    }

    pub fn blocks(&self) -> usize {
        self.d.len()
    }

    /// Sums of each 32 values of block `i`.
    pub fn sums32(&self, i: usize) -> &[i16] {
        &self.bsums32[i * 8..][..8]
    }

    pub fn block(&self, i: usize) -> (f32, &[i8], &[i16]) {
        (
            self.d[i],
            &self.qs[i * QK_K..][..QK_K],
            &self.bsums[i * 16..][..16],
        )
    }
}

/// Quantizes one block to `round(v / d)` with `d = max|v| / 127`, rounding
/// half away from zero, and returns `d`.
pub(crate) fn quantize_block(src: &[f32], dst: &mut [i8]) -> f32 {
    #[cfg(target_arch = "x86_64")]
    if is_x86_feature_detected!("avx2") {
        // SAFETY: AVX2 was just detected.
        return unsafe { simd::quantize_block(src, dst) };
    }
    quantize_block_scalar(src, dst)
}

fn quantize_block_scalar(src: &[f32], dst: &mut [i8]) -> f32 {
    let amax = src.iter().fold(0.0f32, |m, v| m.max(v.abs()));
    let d = amax / 127.0;
    let inv = if d == 0.0 { 0.0 } else { 1.0 / d };
    for (v, q) in src.iter().zip(dst.iter_mut()) {
        *q = (v * inv).round().clamp(-127.0, 127.0) as i8;
    }
    d
}

#[cfg(target_arch = "x86_64")]
mod simd {
    use std::arch::x86_64::*;

    /// [`super::quantize_block_scalar`], value for value.
    #[target_feature(enable = "avx2")]
    pub(super) unsafe fn quantize_block(src: &[f32], dst: &mut [i8]) -> f32 {
        assert_eq!(src.len(), dst.len());
        assert!(src.len().is_multiple_of(32));
        let sign = _mm256_set1_ps(-0.0);
        // `max(|v|, m)` keeps `m` when `|v|` is NaN, as `f32::max` does.
        let mut m = _mm256_setzero_ps();
        for c in src.chunks_exact(8) {
            m = _mm256_max_ps(_mm256_andnot_ps(sign, _mm256_loadu_ps(c.as_ptr())), m);
        }
        let m = _mm_max_ps(_mm256_castps256_ps128(m), _mm256_extractf128_ps(m, 1));
        let m = _mm_max_ps(m, _mm_movehl_ps(m, m));
        let amax = _mm_cvtss_f32(_mm_max_ss(m, _mm_movehdup_ps(m)));

        let d = amax / 127.0;
        let inv = _mm256_set1_ps(if d == 0.0 { 0.0 } else { 1.0 / d });
        for (c, out) in src.chunks_exact(32).zip(dst.chunks_exact_mut(32)) {
            let ab = _mm256_packs_epi32(round8(&c[..8], inv), round8(&c[8..16], inv));
            let cd = _mm256_packs_epi32(round8(&c[16..24], inv), round8(&c[24..], inv));
            // The packs work per 128-bit half; restore element order.
            let v = _mm256_permutevar8x32_epi32(
                _mm256_packs_epi16(ab, cd),
                _mm256_setr_epi32(0, 4, 1, 5, 2, 6, 3, 7),
            );
            _mm256_storeu_si256(out.as_mut_ptr() as *mut __m256i, v);
        }
        d
    }

    /// `round(p * inv)` clamped to +-127, as i32, for eight values.
    #[inline]
    #[target_feature(enable = "avx2")]
    unsafe fn round8(p: &[f32], inv: __m256) -> __m256i {
        assert!(p.len() >= 8);
        let sign = _mm256_set1_ps(-0.0);
        let x = _mm256_mul_ps(_mm256_loadu_ps(p.as_ptr()), inv);
        // Round half away from zero: truncate, then step away from zero
        // when the dropped fraction is at least a half.
        let t = _mm256_round_ps(x, _MM_FROUND_TO_ZERO | _MM_FROUND_NO_EXC);
        let frac = _mm256_andnot_ps(sign, _mm256_sub_ps(x, t));
        let step = _mm256_or_ps(_mm256_and_ps(x, sign), _mm256_set1_ps(1.0));
        let up = _mm256_and_ps(_mm256_cmp_ps(frac, _mm256_set1_ps(0.5), _CMP_GE_OQ), step);
        let r = _mm256_add_ps(t, up);
        let r = _mm256_min_ps(
            _mm256_max_ps(r, _mm256_set1_ps(-127.0)),
            _mm256_set1_ps(127.0),
        );
        // NaN becomes 0, as `as i8` makes it.
        _mm256_cvttps_epi32(_mm256_and_ps(r, _mm256_cmp_ps(x, x, _CMP_ORD_Q)))
    }
}

/// Tokens interleaved in one [`Q8KGroup`].
pub const GROUP: usize = 8;

/// The narrowest interleave of [`GROUP`], 4 or 2 tokens that holds `n`.
pub fn group_width(n: usize) -> usize {
    match n {
        0..=2 => 2,
        3..=4 => 4,
        _ => GROUP,
    }
}

/// Up to [`GROUP`] activation vectors interleaved so that one 32-byte load
/// holds `32 / width` consecutive values of each of `width` tokens, the
/// layout the tile kernels multiply against broadcast weights. Scales and
/// sums always have [`GROUP`] slots. Missing tokens are zero.
pub struct Q8KGroup {
    /// Tokens per 32-byte step: 8, or 4 or 2 for short batches.
    pub width: usize,
    /// Per block, `256 * width / 32` steps of `width` tokens times
    /// `32 / width` values.
    pub qs: Vec<i8>,
    /// Per block, the scale of each token.
    pub d: Vec<f32>,
    /// Per block, four pairs of adjacent 32-value sums, each pair laid out
    /// for all tokens: `[pair][token][2]`.
    pub sums32: Vec<i16>,
    /// Per block, eight pairs of adjacent 16-value sums, `[pair][token][2]`.
    pub sums16: Vec<i16>,
}

impl Q8KGroup {
    pub fn new(xs: &[Q8K]) -> Q8KGroup {
        assert!((1..=GROUP).contains(&xs.len()));
        let blocks = xs[0].blocks();
        let width = group_width(xs.len());
        let mut g = Q8KGroup {
            width,
            qs: vec![0; blocks * QK_K * width],
            d: vec![0.0; blocks * GROUP],
            sums32: vec![0; blocks * 4 * GROUP * 2],
            sums16: vec![0; blocks * 8 * GROUP * 2],
        };
        for x in xs {
            assert_eq!(x.blocks(), blocks);
        }
        let v = 32 / width;
        for (k, step) in g.qs.chunks_exact_mut(32).enumerate() {
            for (dst, x) in step.chunks_exact_mut(v).zip(xs) {
                dst.copy_from_slice(&x.qs[v * k..v * k + v]);
            }
        }
        for (t, x) in xs.iter().enumerate() {
            for b in 0..blocks {
                g.d[b * GROUP + t] = x.d[b];
            }
            for (p, pair) in x.bsums32.chunks_exact(2).enumerate() {
                g.sums32[(p * GROUP + t) * 2..][..2].copy_from_slice(pair);
            }
            for (p, pair) in x.bsums.chunks_exact(2).enumerate() {
                g.sums16[(p * GROUP + t) * 2..][..2].copy_from_slice(pair);
            }
        }
        g
    }

    pub fn blocks(&self) -> usize {
        self.d.len() / GROUP
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trip_error_is_bounded() {
        let x: Vec<f32> = (0..512).map(|i| ((i * 37) % 101) as f32 - 50.0).collect();
        let q = Q8K::quantize(&x);
        for b in 0..q.blocks() {
            let (d, qs, bsums) = q.block(b);
            for (i, &v) in qs.iter().enumerate() {
                assert!((v as f32 * d - x[b * QK_K + i]).abs() <= d / 2.0 + 1e-4);
            }
            for (g, &s) in bsums.iter().enumerate() {
                assert_eq!(s, qs[g * 16..][..16].iter().map(|&v| v as i16).sum::<i16>());
            }
        }
    }

    #[test]
    fn simd_matches_scalar() {
        let mut x: Vec<f32> = (0..4 * QK_K)
            .map(|i| ((i * 7919) % 2001) as f32 / 1000.0 - 1.0)
            .collect();
        // Ties at every rounding step, signed zeros, a lone huge value, and
        // values that are not numbers.
        for (i, v) in x[QK_K..2 * QK_K].iter_mut().enumerate() {
            *v = (i as f32 - 127.0) * 0.5;
        }
        x[2 * QK_K] = -0.0;
        x[2 * QK_K + 1] = 1e30;
        x[3 * QK_K + 5] = f32::NAN;
        x[3 * QK_K + 6] = f32::INFINITY;
        for src in x.chunks_exact(QK_K) {
            let (mut a, mut b) = ([0i8; QK_K], [0i8; QK_K]);
            let da = quantize_block_scalar(src, &mut a);
            let db = quantize_block(src, &mut b);
            assert_eq!(da.to_bits(), db.to_bits());
            assert_eq!(a, b);
        }
    }

    #[test]
    fn zero_block_is_zero() {
        let q = Q8K::quantize(&[0.0; 256]);
        assert_eq!(q.d[0], 0.0);
        assert!(q.qs.iter().all(|&v| v == 0));
    }
}
