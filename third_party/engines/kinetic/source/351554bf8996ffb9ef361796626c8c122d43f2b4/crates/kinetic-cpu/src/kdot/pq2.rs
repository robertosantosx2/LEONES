//! PQ2_0 rows times a [`Q8K`] vector. Each 256-value activation block meets
//! two weight blocks of 128, each with its own scale; both kernels reduce a
//! weight block to the same integer and fold it in with the same f32 steps,
//! so they agree bit for bit.

use super::{half, DotFn, DotNFn};
use crate::q8k::Q8K;
use kinetic_quant::{two_bit_code, TensorType};

const BLOCK_BYTES: usize = 34;

pub fn kernel(ty: TensorType) -> Option<DotFn<Q8K>> {
    (ty == TensorType::PQ2_0).then_some(scalar as DotFn<Q8K>)
}

fn scalar(row: &[u8], x: &Q8K) -> f32 {
    dot(row, x, |blk, y| {
        (0..128)
            .map(|j| two_bit_code(&blk[2..], j) as i32 * y[j] as i32)
            .sum()
    })
}

/// `codes` gives the dot product of one block's unsigned codes with 128
/// activations; the codes stand for one more than the weights, which the
/// block sums take back out.
#[inline(always)]
fn dot(row: &[u8], x: &Q8K, codes: impl Fn(&[u8], &[i8]) -> i32) -> f32 {
    let mut sum = 0.0;
    for (b, pair) in row.chunks_exact(2 * BLOCK_BYTES).enumerate() {
        let (dx, q8, bsums) = x.block(b);
        let mut s = 0.0;
        for (h, blk) in pair.chunks_exact(BLOCK_BYTES).enumerate() {
            let offset: i32 = bsums[8 * h..][..8].iter().map(|&v| v as i32).sum();
            s += half(blk) * (codes(blk, &q8[128 * h..][..128]) - offset) as f32;
        }
        sum += dx * s;
    }
    sum
}

#[cfg(target_arch = "x86_64")]
pub mod avx2 {
    use std::arch::x86_64::*;

    use super::*;

    pub fn kernel(ty: TensorType) -> Option<DotFn<Q8K>> {
        // SAFETY: only reachable after `avx2::available()` confirmed the
        // target features `rows` is compiled for.
        (ty == TensorType::PQ2_0).then_some(|r, x| unsafe { rows::<1>(r, [x]) }[0])
    }

    pub fn kernel_n<const N: usize>(ty: TensorType) -> Option<DotNFn<Q8K, N>> {
        // SAFETY: as in `kernel`.
        (ty == TensorType::PQ2_0).then_some(|r, xs| unsafe { rows::<N>(r, xs) })
    }

    /// One row times `N` vectors, each pair of weight blocks unpacked once;
    /// per vector the f32 steps of [`dot`]. Codes unpack four apart, so they
    /// meet [`Q8K::strided`] values; the integer sums are the same.
    #[target_feature(enable = "avx2,fma,f16c")]
    unsafe fn rows<const N: usize>(row: &[u8], xs: [&Q8K; N]) -> [f32; N] {
        let ys = xs.map(Q8K::strided);
        let mut sum = [0.0f32; N];
        for (b, pair) in row.chunks_exact(2 * BLOCK_BYTES).enumerate() {
            let (lo, hi) = pair.split_at(BLOCK_BYTES);
            let q = [unpack(lo), unpack(hi)];
            let d = [half(lo), half(hi)];
            for (((y, sums), x), sum) in ys.iter().zip(xs).zip(&mut sum) {
                let y = &y[256 * b..][..256];
                let codes = hsum2(dot128(&q[0], &y[..128]), dot128(&q[1], &y[128..]));
                let mut s = 0.0;
                for h in 0..2 {
                    s += d[h] * (codes[h] - sums[2 * b + h]) as f32;
                }
                *sum += x.d[b] * s;
            }
        }
        sum
    }

    /// The codes of a block: vector `k` holds elements `4i + k`.
    #[target_feature(enable = "avx2")]
    unsafe fn unpack(blk: &[u8]) -> [__m256i; 4] {
        debug_assert!(blk.len() == BLOCK_BYTES);
        let mask = _mm256_set1_epi8(3);
        let v = _mm256_loadu_si256(blk.as_ptr().add(2).cast());
        [
            _mm256_and_si256(v, mask),
            _mm256_and_si256(_mm256_srli_epi16(v, 2), mask),
            _mm256_and_si256(_mm256_srli_epi16(v, 4), mask),
            _mm256_and_si256(_mm256_srli_epi16(v, 6), mask),
        ]
    }

    /// Lanes summing to the codes times 128 strided values; four `maddubs`
    /// stay below 4 * 2 * 3 * 127 in i16.
    #[target_feature(enable = "avx2")]
    unsafe fn dot128(q: &[__m256i; 4], y: &[i8]) -> __m256i {
        debug_assert!(y.len() == 128);
        let p: [__m256i; 4] = std::array::from_fn(|k| {
            _mm256_maddubs_epi16(q[k], _mm256_loadu_si256(y.as_ptr().add(32 * k).cast()))
        });
        let p = _mm256_add_epi16(_mm256_add_epi16(p[0], p[1]), _mm256_add_epi16(p[2], p[3]));
        _mm256_madd_epi16(p, _mm256_set1_epi16(1))
    }

    #[target_feature(enable = "avx2")]
    unsafe fn hsum2(a: __m256i, b: __m256i) -> [i32; 2] {
        let t = _mm256_hadd_epi32(a, b);
        let t = _mm256_hadd_epi32(t, t);
        let s = _mm_add_epi32(_mm256_castsi256_si128(t), _mm256_extracti128_si256(t, 1));
        [_mm_cvtsi128_si32(s), _mm_extract_epi32(s, 1)]
    }
}
