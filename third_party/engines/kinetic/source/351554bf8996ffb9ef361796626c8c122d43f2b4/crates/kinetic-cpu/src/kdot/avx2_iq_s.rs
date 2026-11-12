//! AVX2 kernels for IQ3_S, IQ2_S, IQ1_S and IQ1_M. Codebook entries are
//! gathered with scalar loads, eight or four per 32 values; sign bits are
//! applied to the activations.

use std::arch::x86_64::*;

use super::avx2::half;
use super::avx2_low_bit::{add_products, walk, Sums};
use super::{DotFn, DotNFn};
use crate::q8k::Q8K;
use kinetic_quant::grids::{IQ1S_GRID, IQ2S_GRID, IQ3S_GRID};
use kinetic_quant::{iq1_m_group_scale, iq1_m_scale, iq2_s_index, iq3_s_index, TensorType};

pub fn kernel(ty: TensorType) -> Option<DotFn<Q8K>> {
    // SAFETY (each closure): only reachable after `avx2::available()`
    // confirmed the target features the implementations are compiled for.
    Some(match ty {
        TensorType::IQ3S => |row, x| unsafe { iq3_s::<1>(row, [x])[0] },
        TensorType::IQ2S => |row, x| unsafe { iq2_s::<1>(row, [x])[0] },
        TensorType::IQ1S => |row, x| unsafe { iq1_s::<1>(row, [x])[0] },
        TensorType::IQ1M => |row, x| unsafe { iq1_m::<1>(row, [x])[0] },
        _ => return None,
    })
}

pub fn kernel_n<const N: usize>(ty: TensorType) -> Option<DotNFn<Q8K, N>> {
    // SAFETY (each closure): as in `kernel`.
    Some(match ty {
        TensorType::IQ3S => |row, xs| unsafe { iq3_s::<N>(row, xs) },
        TensorType::IQ2S => |row, xs| unsafe { iq2_s::<N>(row, xs) },
        TensorType::IQ1S => |row, xs| unsafe { iq1_s::<N>(row, xs) },
        TensorType::IQ1M => |row, xs| unsafe { iq1_m::<N>(row, xs) },
        _ => return None,
    })
}

/// Byte `i` is -1 where bit `i` of the four sign bytes is set, else 1.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn sign_bytes(signs: &[u8]) -> __m256i {
    let word = _mm256_set1_epi32(i32::from_le_bytes([signs[0], signs[1], signs[2], signs[3]]));
    let spread = _mm256_shuffle_epi8(
        word,
        _mm256_setr_epi64x(
            0,
            0x0101_0101_0101_0101,
            0x0202_0202_0202_0202,
            0x0303_0303_0303_0303,
        ),
    );
    let bit = _mm256_set1_epi64x(0x8040_2010_0804_0201u64 as i64);
    let negative = _mm256_cmpeq_epi8(_mm256_and_si256(spread, bit), bit);
    _mm256_or_si256(negative, _mm256_set1_epi8(1))
}

/// Scale `lo` on the first sixteen values of 32, `hi` on the rest.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn split_scale(lo: i16, hi: i16) -> __m256i {
    _mm256_set_m128i(_mm_set1_epi16(hi), _mm_set1_epi16(lo))
}

/// Four codebook entries of eight bytes each, in order.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn entries8(entry: impl Fn(usize) -> [u8; 8]) -> __m256i {
    let e = |l: usize| i64::from_le_bytes(entry(l));
    _mm256_set_epi64x(e(3), e(2), e(1), e(0))
}

/// An IQ1 codebook entry as bytes.
fn iq1_entry(index: usize) -> [u8; 8] {
    IQ1S_GRID[index].map(|v| v as u8)
}

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn iq3_s<const N: usize>(row: &[u8], xs: [&Q8K; N]) -> [f32; N] {
    walk::<N, false>(row, xs, 110, |b, k| {
        let (qs, qh, signs, scales) = (&b[2..66], &b[66..74], &b[74..106], &b[106..110]);
        let mut sumi = [_mm256_setzero_si256(); N];
        for s in 0..8 {
            let e = |l: usize| i32::from_le_bytes(IQ3S_GRID[iq3_s_index(qs, qh, 8 * s + l)]);
            let w = _mm256_setr_epi32(e(0), e(1), e(2), e(3), e(4), e(5), e(6), e(7));
            let scale = 1 + 2 * (scales[s / 2] >> (4 * (s % 2)) & 0xF) as i16;
            let sign = sign_bytes(&signs[4 * s..]);
            let at = 256 * k + 32 * s;
            add_products(&mut sumi, xs, at, w, Some(sign), _mm256_set1_epi16(scale));
        }
        Sums {
            d: half(b),
            dmin: 0.0,
            sumi,
            mins: [_mm_setzero_si128(); N],
        }
    })
}

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn iq2_s<const N: usize>(row: &[u8], xs: [&Q8K; N]) -> [f32; N] {
    walk::<N, false>(row, xs, 82, |b, k| {
        let (qs, signs, qh, scales) = (&b[2..34], &b[34..66], &b[66..74], &b[74..82]);
        let mut sumi = [_mm256_setzero_si256(); N];
        for s in 0..8 {
            let w = entries8(|l| IQ2S_GRID[iq2_s_index(qs, qh, 4 * s + l)]);
            let scale = |nibble: u8| 1 + 2 * nibble as i16;
            let scale = split_scale(scale(scales[s] & 0xF), scale(scales[s] >> 4));
            let at = 256 * k + 32 * s;
            add_products(
                &mut sumi,
                xs,
                at,
                w,
                Some(sign_bytes(&signs[4 * s..])),
                scale,
            );
        }
        Sums {
            d: half(b) * 0.125,
            dmin: 0.0,
            sumi,
            mins: [_mm_setzero_si128(); N],
        }
    })
}

/// `8 * g + delta` for codebook values `g` in -1..=1 and deltas of +-1,
/// as signed bytes.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn iq1_values(g: __m256i, delta: __m256i) -> __m256i {
    _mm256_add_epi8(_mm256_sign_epi8(_mm256_set1_epi8(8), g), delta)
}

/// Signed IQ1 weights times each token's activations at `at`.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn add_signed<const N: usize>(
    sumi: &mut [__m256i; N],
    xs: [&Q8K; N],
    at: usize,
    w: __m256i,
    scale: __m256i,
) {
    add_products(sumi, xs, at, _mm256_abs_epi8(w), Some(w), scale);
}

/// Eight bytes of +1, or of -1 when `negative`.
fn delta8(negative: bool) -> i64 {
    if negative {
        -1
    } else {
        0x0101_0101_0101_0101
    }
}

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn iq1_s<const N: usize>(row: &[u8], xs: [&Q8K; N]) -> [f32; N] {
    walk::<N, false>(row, xs, 50, |b, k| {
        let qs = &b[2..34];
        let mut sumi = [_mm256_setzero_si256(); N];
        for s in 0..8 {
            let qh = u16::from_le_bytes([b[34 + 2 * s], b[35 + 2 * s]]);
            let g = entries8(|l| {
                iq1_entry(qs[4 * s + l] as usize | (((qh >> (3 * l)) & 7) as usize) << 8)
            });
            let w = iq1_values(g, _mm256_set1_epi64x(delta8(qh & 0x8000 != 0)));
            let scale = _mm256_set1_epi16(2 * ((qh >> 12) & 7) as i16 + 1);
            add_signed(&mut sumi, xs, 256 * k + 32 * s, w, scale);
        }
        Sums {
            d: half(b) * 0.125,
            dmin: 0.0,
            sumi,
            mins: [_mm_setzero_si128(); N],
        }
    })
}

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn iq1_m<const N: usize>(row: &[u8], xs: [&Q8K; N]) -> [f32; N] {
    walk::<N, false>(row, xs, 56, |b, k| {
        let (qs, qh, scales) = (&b[..32], &b[32..48], &b[48..56]);
        let mut sumi = [_mm256_setzero_si256(); N];
        for s in 0..8 {
            let h = |l: usize| qh[2 * s + l / 2] >> (4 * (l % 2));
            let g = entries8(|l| iq1_entry(qs[4 * s + l] as usize | ((h(l) & 7) as usize) << 8));
            let d = |l: usize| delta8(h(l) & 8 != 0);
            let w = iq1_values(g, _mm256_set_epi64x(d(3), d(2), d(1), d(0)));
            let scale = |g: usize| 2 * iq1_m_group_scale(scales, g) as i16 + 1;
            let scale = split_scale(scale(2 * s), scale(2 * s + 1));
            add_signed(&mut sumi, xs, 256 * k + 32 * s, w, scale);
        }
        Sums {
            d: iq1_m_scale(scales) * 0.125,
            dmin: 0.0,
            sumi,
            mins: [_mm_setzero_si128(); N],
        }
    })
}
