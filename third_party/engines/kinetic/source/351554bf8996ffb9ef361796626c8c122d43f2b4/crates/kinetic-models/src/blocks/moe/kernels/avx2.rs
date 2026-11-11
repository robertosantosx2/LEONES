//! AVX2 versions of the unpacking and of the dot products, all giving
//! exactly the scalar result.

use std::arch::x86_64::*;

use kinetic_cpu::Q8K;
use kinetic_quant::iq::{iq_signs, IQ2XS_GRID, IQ2XXS_GRID, IQ3XXS_GRID, IQ4NL_VALUES};
use kinetic_quant::TensorType;

use super::{BlockFn, Unpacked, QK};

fn available() -> bool {
    is_x86_feature_detected!("avx2")
}

/// The block unpacker for `ty`, if this CPU has AVX2.
pub fn unpack_block(ty: TensorType) -> Option<BlockFn> {
    if !available() {
        return None;
    }
    // SAFETY (each closure): AVX2 was just detected.
    match ty {
        TensorType::IQ2XXS => Some(|src, out| unsafe { unpack::<Iq2Xxs>(src, out) }),
        TensorType::IQ2XS => Some(|src, out| unsafe { unpack::<Iq2Xs>(src, out) }),
        TensorType::IQ3XXS => Some(|src, out| unsafe { unpack::<Iq3Xxs>(src, out) }),
        TensorType::IQ4XS => Some(|src, out| unsafe { unpack::<Iq4Xs>(src, out) }),
        _ => None,
    }
}

/// The dot product of an unpacked row, if this CPU has AVX2.
pub fn dot_fn() -> Option<fn(&[Unpacked], &Q8K) -> f32> {
    // SAFETY: AVX2 was just detected.
    available().then_some(|row, x| unsafe { dot(row, x) })
}

/// The dot product of a packed row of `ty`, if this CPU has AVX2.
pub fn packed_dot_fn(ty: TensorType) -> Option<fn(&[u8], &Q8K) -> f32> {
    if !available() {
        return None;
    }
    // SAFETY (each closure): AVX2 was just detected.
    match ty {
        TensorType::IQ2XXS => Some(|row, x| unsafe { packed_dot::<Iq2Xxs>(row, x) }),
        TensorType::IQ2XS => Some(|row, x| unsafe { packed_dot::<Iq2Xs>(row, x) }),
        TensorType::IQ3XXS => Some(|row, x| unsafe { packed_dot::<Iq3Xxs>(row, x) }),
        TensorType::IQ4XS => Some(|row, x| unsafe { packed_dot::<Iq4Xs>(row, x) }),
        _ => None,
    }
}

/// Per sign index, eight bytes of 1 or -1 for `_mm256_sign_epi8`.
static SIGNS: [i64; 128] = {
    let mut table = [0; 128];
    let mut i = 0;
    while i < 128 {
        let bits = iq_signs(i as u8);
        let mut v = 0u64;
        let mut j = 0;
        while j < 8 {
            let byte = if bits >> j & 1 == 1 { 0xff } else { 0x01 };
            v |= byte << (8 * j);
            j += 1;
        }
        table[i] = v as i64;
        i += 1;
    }
    table
};

/// One codebook format: 32 values of a block at a time, as magnitudes and
/// the signs to give them, and the block's scales.
trait Format {
    const BYTES: usize;

    /// Values `32 * c..32 * c + 32` of block `src` are
    /// `sign_epi8(magnitudes, signs)`, magnitudes at most 127.
    ///
    /// # Safety
    ///
    /// AVX2 must be available; `src` holds one block and `c < 8`.
    unsafe fn chunk(src: &[u8], c: usize) -> (__m256i, __m256i);

    /// Writes the block's `d` and `mul` into `out`.
    fn scales(src: &[u8], out: &mut Unpacked);
}

struct Iq2Xxs;
struct Iq2Xs;
struct Iq3Xxs;
struct Iq4Xs;

impl Format for Iq2Xxs {
    const BYTES: usize = 66;

    #[inline(always)]
    unsafe fn chunk(src: &[u8], c: usize) -> (__m256i, __m256i) {
        let a = super::iq2_xxs_aux(src, c);
        let grid: [i64; 4] =
            std::array::from_fn(|l| i64::from_le_bytes(IQ2XXS_GRID[src[2 + 8 * c + l] as usize]));
        let sign: [i64; 4] = std::array::from_fn(|l| SIGNS[(a >> (7 * l) & 127) as usize]);
        (
            _mm256_setr_epi64x(grid[0], grid[1], grid[2], grid[3]),
            _mm256_setr_epi64x(sign[0], sign[1], sign[2], sign[3]),
        )
    }

    fn scales(src: &[u8], out: &mut Unpacked) {
        super::iq2_xxs_scales(src, out);
    }
}

impl Format for Iq2Xs {
    const BYTES: usize = 74;

    #[inline(always)]
    unsafe fn chunk(src: &[u8], c: usize) -> (__m256i, __m256i) {
        let packed = u64::from_le_bytes(src[2 + 8 * c..10 + 8 * c].try_into().unwrap());
        let q: [u16; 4] = std::array::from_fn(|i| (packed >> (16 * i)) as u16);
        let grid = q.map(|q| i64::from_le_bytes(IQ2XS_GRID[(q & 511) as usize]));
        let sign = q.map(|q| SIGNS[(q >> 9) as usize]);
        (
            _mm256_setr_epi64x(grid[0], grid[1], grid[2], grid[3]),
            _mm256_setr_epi64x(sign[0], sign[1], sign[2], sign[3]),
        )
    }

    fn scales(src: &[u8], out: &mut Unpacked) {
        super::iq2_xs_scales(src, out);
    }
}

impl Format for Iq3Xxs {
    const BYTES: usize = 98;

    #[inline(always)]
    unsafe fn chunk(src: &[u8], c: usize) -> (__m256i, __m256i) {
        let a = super::iq3_xxs_aux(src, c);
        let g: [i32; 8] =
            std::array::from_fn(|i| i32::from_le_bytes(IQ3XXS_GRID[src[2 + 8 * c + i] as usize]));
        let s: [i64; 4] = std::array::from_fn(|l| SIGNS[(a >> (7 * l) & 127) as usize]);
        (
            _mm256_setr_epi32(g[0], g[1], g[2], g[3], g[4], g[5], g[6], g[7]),
            _mm256_setr_epi64x(s[0], s[1], s[2], s[3]),
        )
    }

    fn scales(src: &[u8], out: &mut Unpacked) {
        super::iq3_xxs_scales(src, out);
    }
}

impl Format for Iq4Xs {
    const BYTES: usize = 136;

    /// The values are signed already: their magnitudes, signed by
    /// themselves.
    #[inline(always)]
    unsafe fn chunk(src: &[u8], c: usize) -> (__m256i, __m256i) {
        // SAFETY: the table holds 16 bytes, and 16 bytes at `8 + 16 * c`
        // lie inside the block's 128 bytes of codes.
        let (table, q) = unsafe {
            (
                _mm_loadu_si128(IQ4NL_VALUES.as_ptr().cast()),
                _mm_loadu_si128(src.as_ptr().add(8 + 16 * c).cast()),
            )
        };
        let nibble = _mm_set1_epi8(0xf);
        let lo = _mm_shuffle_epi8(table, _mm_and_si128(q, nibble));
        let hi = _mm_shuffle_epi8(table, _mm_and_si128(_mm_srli_epi16(q, 4), nibble));
        let v = _mm256_setr_m128i(lo, hi);
        (_mm256_sign_epi8(v, v), v)
    }

    fn scales(src: &[u8], out: &mut Unpacked) {
        super::iq4_xs_scales(src, out);
    }
}

#[target_feature(enable = "avx2")]
unsafe fn unpack<F: Format>(src: &[u8], out: &mut Unpacked) {
    for c in 0..QK / 32 {
        // SAFETY: AVX2 is enabled; `src` is one block and `c < 8`.
        let (m, s) = unsafe { F::chunk(src, c) };
        // SAFETY: the 32 bytes at `32 * c` lie inside `out.qs`, which is
        // aligned to 32.
        unsafe {
            _mm256_store_si256(
                out.qs.as_mut_ptr().add(32 * c).cast(),
                _mm256_sign_epi8(m, s),
            )
        };
    }
    F::scales(src, out);
}

/// `maddubs` of the magnitudes with the signed inputs forms 16 pair sums
/// per 32 values: the first eight cover the first 16 values and the last
/// eight the next 16, so one `madd` with the two multipliers applies them.
/// Magnitudes stay at or below 127, so pair sums never saturate.
#[inline(always)]
unsafe fn chunk_sum(magnitudes: __m256i, signs: __m256i, q: __m256i, mul: &[i16]) -> __m256i {
    let p = _mm256_maddubs_epi16(magnitudes, _mm256_sign_epi8(q, signs));
    let m = _mm256_setr_m128i(_mm_set1_epi16(mul[0]), _mm_set1_epi16(mul[1]));
    _mm256_madd_epi16(p, m)
}

#[inline(always)]
unsafe fn horizontal(sum: __m256i) -> i32 {
    let s = _mm_add_epi32(
        _mm256_castsi256_si128(sum),
        _mm256_extracti128_si256(sum, 1),
    );
    let s = _mm_add_epi32(s, _mm_shuffle_epi32(s, 0b01_00_11_10));
    let s = _mm_add_epi32(s, _mm_shuffle_epi32(s, 0b10_11_00_01));
    _mm_cvtsi128_si32(s)
}

/// # Safety
///
/// AVX2 must be available; `q` holds 256 values at least.
#[inline(always)]
unsafe fn load(q: &[i8], c: usize) -> __m256i {
    // SAFETY: 32 bytes at `32 * c < 256` lie inside `q`.
    unsafe { _mm256_loadu_si256(q.as_ptr().add(32 * c).cast()) }
}

/// The integer sum of an unpacked block times 256 input values.
#[target_feature(enable = "avx2")]
unsafe fn block_sum(w: &Unpacked, q: &[i8]) -> i32 {
    let mut sum = _mm256_setzero_si256();
    for c in 0..QK / 32 {
        // SAFETY: the 32 bytes at `32 * c` lie inside `w.qs`, aligned to 32.
        let wv = unsafe { _mm256_load_si256(w.qs.as_ptr().add(32 * c).cast()) };
        // SAFETY: AVX2 is enabled; `q` is a 256-value block.
        let qv = unsafe { load(q, c) };
        // SAFETY: AVX2 is enabled.
        let p = unsafe { chunk_sum(_mm256_sign_epi8(wv, wv), wv, qv, &w.mul[2 * c..]) };
        sum = _mm256_add_epi32(sum, p);
    }
    // SAFETY: AVX2 is enabled.
    unsafe { horizontal(sum) }
}

#[target_feature(enable = "avx2")]
unsafe fn dot(row: &[Unpacked], x: &Q8K) -> f32 {
    row.iter().enumerate().fold(0.0, |acc, (b, w)| {
        // SAFETY: AVX2 is enabled for this function; the block is 256 values.
        let sum = unsafe { block_sum(w, &x.qs[b * QK..][..QK]) };
        super::accumulate(acc, w, x, b, sum)
    })
}

/// The dot product of a packed row with `x`, decoding each 32 values
/// straight into the products: what a row used once costs.
#[target_feature(enable = "avx2")]
unsafe fn packed_dot<F: Format>(row: &[u8], x: &Q8K) -> f32 {
    let mut scales = Unpacked::default();
    row.chunks_exact(F::BYTES)
        .enumerate()
        .fold(0.0, |acc, (b, src)| {
            F::scales(src, &mut scales);
            let q = &x.qs[b * QK..][..QK];
            let mut sum = _mm256_setzero_si256();
            for c in 0..QK / 32 {
                // SAFETY: AVX2 is enabled; `src` is one block, `q` 256
                // values and `c < 8`.
                let p = unsafe {
                    let (m, s) = F::chunk(src, c);
                    chunk_sum(m, s, load(q, c), &scales.mul[2 * c..])
                };
                sum = _mm256_add_epi32(sum, p);
            }
            // SAFETY: AVX2 is enabled.
            let sum = unsafe { horizontal(sum) };
            super::accumulate(acc, &scales, x, b, sum)
        })
}
