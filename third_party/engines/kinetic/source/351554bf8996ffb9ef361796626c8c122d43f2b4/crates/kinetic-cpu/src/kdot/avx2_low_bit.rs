//! AVX2 kernels for Q2_K, Q3_K, TQ1_0 and TQ2_0, and the block walk the
//! IQ kernels share. Each block becomes exact integer sums per token, which
//! `Chunk::fold` turns into f32 as for the other K-quants.

use std::arch::x86_64::*;

use super::avx2::{half, halves, hsum, load, load_i8, pair_scale, Chunk, CHUNK};
use super::{DotFn, DotNFn};
use crate::q8k::Q8K;
use kinetic_quant::{q3_k_scales, trit, TensorType};

pub fn kernel(ty: TensorType) -> Option<DotFn<Q8K>> {
    // SAFETY (each closure): only reachable after `avx2::available()`
    // confirmed the target features the implementations are compiled for.
    Some(match ty {
        TensorType::Q2K => |row, x| unsafe { q2_k::<1>(row, [x])[0] },
        TensorType::Q3K => |row, x| unsafe { q3_k::<1>(row, [x])[0] },
        TensorType::TQ1_0 => |row, x| unsafe { tq1_0::<1>(row, [x])[0] },
        TensorType::TQ2_0 => |row, x| unsafe { tq2_0::<1>(row, [x])[0] },
        _ => return None,
    })
}

pub fn kernel_n<const N: usize>(ty: TensorType) -> Option<DotNFn<Q8K, N>> {
    // SAFETY (each closure): as in `kernel`.
    Some(match ty {
        TensorType::Q2K => |row, xs| unsafe { q2_k::<N>(row, xs) },
        TensorType::Q3K => |row, xs| unsafe { q3_k::<N>(row, xs) },
        TensorType::TQ1_0 => |row, xs| unsafe { tq1_0::<N>(row, xs) },
        TensorType::TQ2_0 => |row, xs| unsafe { tq2_0::<N>(row, xs) },
        _ => return None,
    })
}

/// What one block contributes per token: `d * sumi - dmin * mins`, both
/// sums exact integers spread over vector lanes.
pub(super) struct Sums<const N: usize> {
    pub d: f32,
    pub dmin: f32,
    pub sumi: [__m256i; N],
    pub mins: [__m128i; N],
}

/// Walks a row of `size`-byte blocks, `block` giving each block's sums
/// from the block and its index, and folds them as every K-quant kernel
/// does.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
pub(super) unsafe fn walk<const N: usize, const MINS: bool>(
    row: &[u8],
    xs: [&Q8K; N],
    size: usize,
    block: impl Fn(&[u8], usize) -> Sums<N>,
) -> [f32; N] {
    let mut part = [_mm256_setzero_ps(); N];
    let mut chunk_sums = Chunk::<N>::new();
    for (c, chunk) in row.chunks(CHUNK * size).enumerate() {
        for (slot, blk) in chunk.chunks_exact(size).enumerate() {
            let s = block(blk, CHUNK * c + slot);
            (chunk_sums.d[slot], chunk_sums.dmin[slot]) = (s.d, s.dmin);
            for i in 0..N {
                chunk_sums.set(i, slot, s.sumi[i], s.mins[i]);
            }
        }
        chunk_sums.fold::<MINS>(
            &mut part,
            xs.map(|x| &x.d[..]),
            CHUNK * c,
            chunk.len() / size,
        );
    }
    std::array::from_fn(|i| hsum(part[i]))
}

/// Adds `scale * w * y` for 32 unsigned weights `w` and each token's 32
/// activations at `at`, the activations first negated where `signs` is
/// negative.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
pub(super) unsafe fn add_products<const N: usize>(
    sumi: &mut [__m256i; N],
    xs: [&Q8K; N],
    at: usize,
    w: __m256i,
    signs: Option<__m256i>,
    scale: __m256i,
) {
    for i in 0..N {
        let mut y = load_i8(&xs[i].qs[at..]);
        if let Some(signs) = signs {
            y = _mm256_sign_epi8(y, signs);
        }
        let p = _mm256_madd_epi16(_mm256_maddubs_epi16(w, y), scale);
        sumi[i] = _mm256_add_epi32(sumi[i], p);
    }
}

/// Sixteen i16 scales split into the two 128-bit halves `pair_scale` reads.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn scale_halves(sc16: __m256i) -> [__m256i; 2] {
    [
        _mm256_permute2x128_si256(sc16, sc16, 0x00),
        _mm256_permute2x128_si256(sc16, sc16, 0x11),
    ]
}

/// `sum(f[g] * bsums[g])` over the sixteen groups of one token's block,
/// as eight i32 lanes.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn group_dot(f: __m256i, x: &Q8K, b: usize) -> __m256i {
    let bsums = x.block(b).2;
    _mm256_madd_epi16(f, _mm256_loadu_si256(bsums.as_ptr() as *const __m256i))
}

// Element `128 n + 32 p + r` of a 2-bit block is plane `p` of byte `r` of
// the `n`th 32-byte run, and belongs to group `8 n + 2 p + r / 16`.

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn q2_k<const N: usize>(row: &[u8], xs: [&Q8K; N]) -> [f32; N] {
    let three = _mm256_set1_epi8(3);
    let nibble = _mm_set1_epi8(0x0F);
    walk::<N, true>(row, xs, 84, |b, k| {
        let sc = _mm_loadu_si128(b.as_ptr() as *const __m128i);
        let scales = scale_halves(_mm256_cvtepu8_epi16(_mm_and_si128(sc, nibble)));
        let mins = _mm256_cvtepu8_epi16(_mm_and_si128(_mm_srli_epi16(sc, 4), nibble));
        let (d, dmin) = halves(&b[80..84]);
        let mut sumi = [_mm256_setzero_si256(); N];
        for n in 0..2 {
            let mut q = load(&b[16 + 32 * n..]);
            for p in 0..4 {
                let w = _mm256_and_si256(q, three);
                q = _mm256_srli_epi16(q, 2);
                let at = 256 * k + 128 * n + 32 * p;
                add_products(&mut sumi, xs, at, w, None, pair_scale(scales[n], 4 * n + p));
            }
        }
        let mins = xs.map(|x| {
            let m = group_dot(mins, x, k);
            _mm_add_epi32(_mm256_castsi256_si128(m), _mm256_extracti128_si256(m, 1))
        });
        Sums {
            d,
            dmin,
            sumi,
            mins,
        }
    })
}

// Q3_K weights are stored as q + 4, the 4 coming off where the high bit is
// clear; the kernel multiplies q + 4 and takes 4 * scale * sum(y) back out.
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn q3_k<const N: usize>(row: &[u8], xs: [&Q8K; N]) -> [f32; N] {
    let three = _mm256_set1_epi8(3);
    let four = _mm256_set1_epi8(4);
    walk::<N, false>(row, xs, 110, |b, k| {
        let sc = q3_k_scales(&b[96..108]);
        let sc16 = _mm256_cvtepi8_epi16(_mm_loadu_si128(sc.as_ptr() as *const __m128i));
        let scales = scale_halves(sc16);
        let hmask = load(b);
        let mut sumi = [_mm256_setzero_si256(); N];
        for n in 0..2 {
            let mut q = load(&b[32 + 32 * n..]);
            for p in 0..4 {
                let bit = _mm256_set1_epi8(1 << (4 * n + p));
                let high = _mm256_cmpeq_epi8(_mm256_and_si256(hmask, bit), bit);
                let w = _mm256_or_si256(_mm256_and_si256(q, three), _mm256_and_si256(high, four));
                q = _mm256_srli_epi16(q, 2);
                let at = 256 * k + 128 * n + 32 * p;
                add_products(&mut sumi, xs, at, w, None, pair_scale(scales[n], 4 * n + p));
            }
        }
        for (s, x) in sumi.iter_mut().zip(xs) {
            *s = _mm256_sub_epi32(*s, _mm256_slli_epi32(group_dot(sc16, x, k), 2));
        }
        Sums {
            d: half(&b[108..]),
            dmin: 0.0,
            sumi,
            mins: [_mm_setzero_si128(); N],
        }
    })
}

/// A block of ternary digits stored as `t + 1` (0, 1 or 2; TQ2_0 can
/// also store 3): `sum((t + 1) * y) - sum(y)` per token.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn ternary_sums<const N: usize>(u: &[__m256i; 8], xs: [&Q8K; N], k: usize) -> [__m256i; N] {
    let ones = _mm256_set1_epi16(1);
    std::array::from_fn(|i| {
        let q8 = &xs[i].qs[256 * k..];
        // Eight products of at most 2 * 3 * 127 stay inside i16.
        let mut acc = _mm256_setzero_si256();
        for (j, &u) in u.iter().enumerate() {
            acc = _mm256_add_epi16(acc, _mm256_maddubs_epi16(u, load_i8(&q8[32 * j..])));
        }
        _mm256_sub_epi32(_mm256_madd_epi16(acc, ones), group_dot(ones, xs[i], k))
    })
}

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn tq2_0<const N: usize>(row: &[u8], xs: [&Q8K; N]) -> [f32; N] {
    let three = _mm256_set1_epi8(3);
    walk::<N, false>(row, xs, 66, |b, k| {
        let mut u = [_mm256_setzero_si256(); 8];
        for n in 0..2 {
            let mut q = load(&b[32 * n..]);
            for p in 0..4 {
                u[4 * n + p] = _mm256_and_si256(q, three);
                q = _mm256_srli_epi16(q, 2);
            }
        }
        Sums {
            d: half(&b[64..]),
            dmin: 0.0,
            sumi: ternary_sums(&u, xs, k),
            mins: [_mm_setzero_si128(); N],
        }
    })
}

/// Digit `n` of every byte of `v`, `n` given as `3^n` per i16 lane: the
/// byte times `3^n`, wrapped to a byte, times 3, top two bits of nine.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn trits(v: __m256i, pow: __m256i) -> __m256i {
    let byte = _mm256_set1_epi16(0xFF);
    let three = _mm256_set1_epi16(3);
    let digit = |b: __m256i| {
        let wrapped = _mm256_and_si256(_mm256_mullo_epi16(b, pow), byte);
        _mm256_srli_epi16(_mm256_mullo_epi16(wrapped, three), 8)
    };
    let lo = digit(_mm256_and_si256(v, byte));
    let hi = digit(_mm256_srli_epi16(v, 8));
    _mm256_or_si256(lo, _mm256_slli_epi16(hi, 8))
}

// TQ1_0 unpacks to t + 1 in element order (see `tq1_0_position`), then
// shares TQ2_0's products.
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn tq1_0<const N: usize>(row: &[u8], xs: [&Q8K; N]) -> [f32; N] {
    const POW3: [i16; 5] = [1, 3, 9, 27, 81];
    walk::<N, false>(row, xs, 54, |b, k| {
        let mut u = [_mm256_setzero_si256(); 8];
        let mut digits = [0u8; 256];
        let first = load(b);
        for (n, &pow) in POW3.iter().enumerate() {
            let t = trits(first, _mm256_set1_epi16(pow));
            _mm256_storeu_si256(digits[32 * n..].as_mut_ptr() as *mut __m256i, t);
        }
        let second =
            _mm256_broadcastsi128_si256(_mm_loadu_si128(b[32..].as_ptr() as *const __m128i));
        for n in [0, 2, 4] {
            let pow = _mm256_set_m128i(
                _mm_set1_epi16(POW3[(n + 1).min(4)]),
                _mm_set1_epi16(POW3[n]),
            );
            let t = trits(second, pow);
            _mm256_storeu_si256(digits[160 + 16 * n..].as_mut_ptr() as *mut __m256i, t);
        }
        for (j, d) in digits[240..].iter_mut().enumerate() {
            *d = trit(b[48 + j % 4], j / 4);
        }
        for (u, d) in u.iter_mut().zip(digits.chunks_exact(32)) {
            *u = load(d);
        }
        Sums {
            d: half(&b[52..]),
            dmin: 0.0,
            sumi: ternary_sums(&u, xs, k),
            mins: [_mm_setzero_si128(); N],
        }
    })
}
