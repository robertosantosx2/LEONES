//! AVX2 kernels for the 32-value formats Q4_1, Q5_0, Q5_1, IQ4_NL and
//! MXFP4, folded per chunk of eight blocks like Q4_0.

use std::arch::x86_64::*;

use super::avx2::{hsum, lane_totals, load_i8, signed_dot};
use super::{DotFn, DotNFn};
use crate::q8::Q8;
use kinetic_quant::grids::{e8m0_half, IQ4NL_VALUES, MXFP4_VALUES};
use kinetic_quant::TensorType;

pub fn kernel(ty: TensorType) -> Option<DotFn<Q8>> {
    // SAFETY (each closure): only reachable after `avx2::available()`
    // confirmed the target features the implementations are compiled for.
    Some(match ty {
        TensorType::Q4_1 => |row, x| unsafe { q4_1::<1>(row, [x])[0] },
        TensorType::Q5_0 => |row, x| unsafe { q5_0::<1>(row, [x])[0] },
        TensorType::Q5_1 => |row, x| unsafe { q5_1::<1>(row, [x])[0] },
        TensorType::IQ4NL => |row, x| unsafe { iq4_nl::<1>(row, [x])[0] },
        TensorType::MXFP4 => |row, x| unsafe { mxfp4::<1>(row, [x])[0] },
        _ => return None,
    })
}

pub fn kernel_n<const N: usize>(ty: TensorType) -> Option<DotNFn<Q8, N>> {
    // SAFETY (each closure): as in `kernel`.
    Some(match ty {
        TensorType::Q4_1 => |row, xs| unsafe { q4_1::<N>(row, xs) },
        TensorType::Q5_0 => |row, xs| unsafe { q5_0::<N>(row, xs) },
        TensorType::Q5_1 => |row, xs| unsafe { q5_1::<N>(row, xs) },
        TensorType::IQ4NL => |row, xs| unsafe { iq4_nl::<N>(row, xs) },
        TensorType::MXFP4 => |row, xs| unsafe { mxfp4::<N>(row, xs) },
        _ => return None,
    })
}

/// Per-block scales of a chunk of up to eight blocks: the weight scale and,
/// for formats with a min, the min.
struct Scales {
    d: __m256,
    m: __m256,
}

/// The f16 values at byte `at` of up to eight blocks of `size` bytes.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn halves_at(chunk: &[u8], size: usize, at: usize) -> __m256 {
    let mut h = [0u16; 8];
    for (h, blk) in h.iter_mut().zip(chunk.chunks_exact(size)) {
        *h = u16::from_le_bytes([blk[at], blk[at + 1]]);
    }
    _mm256_cvtph_ps(_mm_loadu_si128(h.as_ptr() as *const __m128i))
}

/// Walks a row in chunks of eight `size`-byte blocks. `unpack` turns a
/// block into weights once; `dot` multiplies them with one token's block
/// `k` into i32 lanes whose total is the block's integer sum. Block `k`
/// adds `(dx * d) * isum`, plus `(dx * m) * sum(y)` when `MIN`, to lane
/// `k % 8` of the token's partial sum.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn walk<const N: usize, const MIN: bool, W: Copy>(
    row: &[u8],
    xs: [&Q8; N],
    size: usize,
    scales: impl Fn(&[u8]) -> Scales,
    unpack: impl Fn(&[u8]) -> W,
    dot: impl Fn(W, &Q8, usize) -> __m256i,
) -> [f32; N] {
    let mut part = [_mm256_setzero_ps(); N];
    for (c, chunk) in row.chunks(8 * size).enumerate() {
        let len = chunk.len() / size;
        let mut p = [[_mm256_setzero_si256(); 8]; N];
        for (j, blk) in chunk.chunks_exact(size).enumerate() {
            let w = unpack(blk);
            for (p, x) in p.iter_mut().zip(xs) {
                p[j] = dot(w, x, 8 * c + j);
            }
        }
        let s = scales(chunk);
        let lanes = _mm256_cmpgt_epi32(
            _mm256_set1_epi32(len as i32),
            _mm256_setr_epi32(0, 1, 2, 3, 4, 5, 6, 7),
        );
        for ((part, p), x) in part.iter_mut().zip(&p).zip(xs) {
            let dx = _mm256_maskload_ps(x.d[8 * c..].as_ptr(), lanes);
            let mut v = _mm256_mul_ps(_mm256_mul_ps(dx, s.d), _mm256_cvtepi32_ps(lane_totals(p)));
            if MIN {
                let mut sums = [0i32; 8];
                for (s, &v) in sums.iter_mut().zip(&x.sums[8 * c..8 * c + len]) {
                    *s = v as i32;
                }
                let sy = _mm256_cvtepi32_ps(_mm256_loadu_si256(sums.as_ptr() as *const __m256i));
                v = _mm256_fmadd_ps(_mm256_mul_ps(dx, s.m), sy, v);
            }
            // Lanes past the row's end are zero: dx is masked to zero there.
            *part = _mm256_add_ps(*part, v);
        }
    }
    std::array::from_fn(|i| hsum(part[i]))
}

/// The 32 nibbles of a block in element order: low nibbles are elements
/// 0..16, high nibbles 16..32.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn nibbles(qs: &[u8]) -> __m256i {
    let q = _mm_loadu_si128(qs[..16].as_ptr() as *const __m128i);
    let low = _mm_set1_epi8(0x0F);
    _mm256_set_m128i(
        _mm_and_si128(_mm_srli_epi16(q, 4), low),
        _mm_and_si128(q, low),
    )
}

/// The fifth bit of every element, as 0x10, from the 32-bit `qh` word.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn fifth_bits(qh: &[u8]) -> __m256i {
    let bits = _mm256_set1_epi32(i32::from_le_bytes([qh[0], qh[1], qh[2], qh[3]]));
    // Byte i of the result looks at bit i of the word: spread byte i / 8 of
    // the word over the eight bytes of its group, then test one bit each.
    let spread = _mm256_shuffle_epi8(
        bits,
        _mm256_setr_epi64x(
            0,
            0x0101_0101_0101_0101,
            0x0202_0202_0202_0202,
            0x0303_0303_0303_0303,
        ),
    );
    let mask = _mm256_set1_epi64x(0x8040_2010_0804_0201u64 as i64);
    _mm256_and_si256(
        _mm256_cmpeq_epi8(_mm256_and_si256(spread, mask), mask),
        _mm256_set1_epi8(0x10),
    )
}

/// Unsigned weights times one token's block `k`.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn unsigned_dot(w: __m256i, x: &Q8, k: usize) -> __m256i {
    _mm256_madd_epi16(
        _mm256_maddubs_epi16(w, load_i8(&x.qs[32 * k..])),
        _mm256_set1_epi16(1),
    )
}

/// Signed weights times one token's block `k`.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn table_dot(w: __m256i, x: &Q8, k: usize) -> __m256i {
    signed_dot(_mm256_abs_epi8(w), w, load_i8(&x.qs[32 * k..]))
}

/// A sixteen-entry i8 table in both halves, for `shuffle_epi8` lookups.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn table(values: &[i8; 16]) -> __m256i {
    _mm256_broadcastsi128_si256(_mm_loadu_si128(values.as_ptr() as *const __m128i))
}

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn q4_1<const N: usize>(row: &[u8], xs: [&Q8; N]) -> [f32; N] {
    walk::<N, true, _>(
        row,
        xs,
        20,
        |c| Scales {
            d: halves_at(c, 20, 0),
            m: halves_at(c, 20, 2),
        },
        |b| nibbles(&b[4..]),
        |w, x, k| unsigned_dot(w, x, k),
    )
}

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn q5_1<const N: usize>(row: &[u8], xs: [&Q8; N]) -> [f32; N] {
    walk::<N, true, _>(
        row,
        xs,
        24,
        |c| Scales {
            d: halves_at(c, 24, 0),
            m: halves_at(c, 24, 2),
        },
        |b| _mm256_or_si256(nibbles(&b[8..]), fifth_bits(&b[4..8])),
        |w, x, k| unsigned_dot(w, x, k),
    )
}

// Q5_0 stores q + 16; the 16 leaves through the block sum, in lane 0.
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn q5_0<const N: usize>(row: &[u8], xs: [&Q8; N]) -> [f32; N] {
    walk::<N, false, _>(
        row,
        xs,
        22,
        |c| Scales {
            d: halves_at(c, 22, 0),
            m: _mm256_setzero_ps(),
        },
        |b| _mm256_or_si256(nibbles(&b[6..]), fifth_bits(&b[2..6])),
        |w, x, k| {
            let offset = _mm256_setr_epi32(16 * x.sums[k] as i32, 0, 0, 0, 0, 0, 0, 0);
            _mm256_sub_epi32(unsigned_dot(w, x, k), offset)
        },
    )
}

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn iq4_nl<const N: usize>(row: &[u8], xs: [&Q8; N]) -> [f32; N] {
    let values = table(&IQ4NL_VALUES);
    walk::<N, false, _>(
        row,
        xs,
        18,
        |c| Scales {
            d: halves_at(c, 18, 0),
            m: _mm256_setzero_ps(),
        },
        |b| _mm256_shuffle_epi8(values, nibbles(&b[2..])),
        |w, x, k| table_dot(w, x, k),
    )
}

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn mxfp4<const N: usize>(row: &[u8], xs: [&Q8; N]) -> [f32; N] {
    let values = table(&MXFP4_VALUES);
    walk::<N, false, _>(
        row,
        xs,
        17,
        |c| {
            let mut d = [0f32; 8];
            for (d, blk) in d.iter_mut().zip(c.chunks_exact(17)) {
                *d = e8m0_half(blk[0]);
            }
            Scales {
                d: _mm256_loadu_ps(d.as_ptr()),
                m: _mm256_setzero_ps(),
            }
        },
        |b| _mm256_shuffle_epi8(values, nibbles(&b[1..])),
        |w, x, k| table_dot(w, x, k),
    )
}
