use std::arch::x86_64::*;

use super::{scales_mins, DotFn, DotNFn};
use crate::q8::Q8;
use crate::q8k::Q8K;
use kinetic_quant::TensorType;

pub fn available() -> bool {
    is_x86_feature_detected!("avx2")
        && is_x86_feature_detected!("fma")
        && is_x86_feature_detected!("f16c")
}

pub fn kernel(ty: TensorType) -> Option<DotFn<Q8K>> {
    match ty {
        TensorType::Q4K => Some(q4_k),
        TensorType::Q5K => Some(q5_k),
        TensorType::Q6K => Some(q6_k),
        _ => None,
    }
}

/// The kernel for `ty` over `N` activation vectors at once.
pub fn kernel_n<const N: usize>(ty: TensorType) -> Option<DotNFn<Q8K, N>> {
    // SAFETY (each closure): only reachable after `available()` confirmed
    // the target features the implementations are compiled for.
    match ty {
        TensorType::Q4K => Some(|row, xs| unsafe { q4_k_impl::<N>(row, xs) }),
        TensorType::Q5K => Some(|row, xs| unsafe { q5_k_impl::<N>(row, xs) }),
        TensorType::Q6K => Some(|row, xs| unsafe { q6_k_impl::<N>(row, xs) }),
        _ => None,
    }
}

pub fn kernel32(ty: TensorType) -> Option<DotFn<Q8>> {
    match ty {
        TensorType::Q8_0 => Some(q8_0),
        TensorType::Q4_0 => Some(q4_0),
        _ => None,
    }
}

/// The kernel for a 32-value format `ty` over `N` activation vectors.
pub fn kernel32_n<const N: usize>(ty: TensorType) -> Option<DotNFn<Q8, N>> {
    // SAFETY (each closure): as in `kernel_n`.
    match ty {
        TensorType::Q8_0 => Some(|row, xs| unsafe { q8_0_impl::<N>(row, xs) }),
        TensorType::Q4_0 => Some(|row, xs| unsafe { q4_0_impl::<N>(row, xs) }),
        _ => None,
    }
}

// The safe wrappers are only handed out by `kernel`, which callers reach
// through `kdot::kernel` after `available()` has confirmed the features.

fn q4_k(row: &[u8], x: &Q8K) -> f32 {
    unsafe { q4_k_impl(row, [x])[0] }
}

fn q5_k(row: &[u8], x: &Q8K) -> f32 {
    unsafe { q5_k_impl(row, [x])[0] }
}

fn q6_k(row: &[u8], x: &Q8K) -> f32 {
    unsafe { q6_k_impl(row, [x])[0] }
}

fn q8_0(row: &[u8], x: &Q8) -> f32 {
    unsafe { q8_0_impl(row, [x])[0] }
}

fn q4_0(row: &[u8], x: &Q8) -> f32 {
    unsafe { q4_0_impl(row, [x])[0] }
}

#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
pub(super) unsafe fn hsum(v: __m256) -> f32 {
    hsum128(_mm_add_ps(
        _mm256_castps256_ps128(v),
        _mm256_extractf128_ps(v, 1),
    ))
}

#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn hsum128(s: __m128) -> f32 {
    let s = _mm_add_ps(s, _mm_movehl_ps(s, s));
    _mm_cvtss_f32(_mm_add_ss(s, _mm_movehdup_ps(s)))
}

#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
pub(super) unsafe fn load(p: &[u8]) -> __m256i {
    debug_assert!(p.len() >= 32);
    _mm256_loadu_si256(p.as_ptr() as *const __m256i)
}

#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
pub(super) unsafe fn load_i8(p: &[i8]) -> __m256i {
    debug_assert!(p.len() >= 32);
    _mm256_loadu_si256(p.as_ptr() as *const __m256i)
}

#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
pub(super) unsafe fn half(p: &[u8]) -> f32 {
    let bits = u16::from_le_bytes([p[0], p[1]]) as i32;
    _mm_cvtss_f32(_mm_cvtph_ps(_mm_cvtsi32_si128(bits)))
}

/// Two adjacent f16 values as f32.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
pub(super) unsafe fn halves(p: &[u8]) -> (f32, f32) {
    let v = _mm_cvtph_ps(_mm_cvtsi32_si128(i32::from_le_bytes([
        p[0], p[1], p[2], p[3],
    ])));
    (_mm_cvtss_f32(v), _mm_cvtss_f32(_mm_movehdup_ps(v)))
}

/// Unsigned 4/5/6-bit weights times signed int8 activations, two products
/// per i16 lane, then scaled and widened to i32.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn scaled_dot(q: __m256i, y: __m256i, scale: __m256i) -> __m256i {
    _mm256_madd_epi16(_mm256_maddubs_epi16(q, y), scale)
}

/// The eight sub-block scales as i16, in both halves of the vector.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn widen_scales(sc: &[u8; 8]) -> __m256i {
    let sc = _mm_cvtepu8_epi16(_mm_loadl_epi64(sc.as_ptr() as *const __m128i));
    _mm256_broadcastsi128_si256(sc)
}

/// Scale `j` of [`widen_scales`] in every i16 lane.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn scale_at(scales: __m256i, j: usize) -> __m256i {
    let pick = (2 * j as i16) | ((2 * j as i16 + 1) << 8);
    _mm256_shuffle_epi8(scales, _mm256_set1_epi16(pick))
}

/// `sum(m[s] * sums32[s])` over the eight sub-blocks, as four i32 lanes.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn mins_dot(m: &[u8; 8], sums32: &[i16]) -> __m128i {
    let m = _mm_cvtepu8_epi16(_mm_loadl_epi64(m.as_ptr() as *const __m128i));
    _mm_madd_epi16(m, _mm_loadu_si128(sums32.as_ptr() as *const __m128i))
}

/// Blocks folded together by the one-row kernels.
pub(super) const CHUNK: usize = 8;

/// The integer sums of up to [`CHUNK`] consecutive blocks, per token, as
/// four lanes each. Lanes past a short final chunk hold stale values that
/// are never used.
pub(super) struct Chunk<const N: usize> {
    sums: [[__m128i; CHUNK]; N],
    /// Mins sums, for the kernels that have mins.
    mins: [[__m128i; CHUNK]; N],
    pub(super) d: [f32; CHUNK],
    pub(super) dmin: [f32; CHUNK],
}

impl<const N: usize> Chunk<N> {
    #[inline]
    #[target_feature(enable = "avx2,fma,f16c")]
    pub(super) unsafe fn new() -> Self {
        Chunk {
            sums: [[_mm_setzero_si128(); CHUNK]; N],
            mins: [[_mm_setzero_si128(); CHUNK]; N],
            d: [0.0; CHUNK],
            dmin: [0.0; CHUNK],
        }
    }

    /// Records block `j` of the chunk for token `i`.
    #[inline]
    #[target_feature(enable = "avx2,fma,f16c")]
    pub(super) unsafe fn set(&mut self, i: usize, j: usize, sum: __m256i, mins: __m128i) {
        self.sums[i][j] = _mm_add_epi32(
            _mm256_castsi256_si128(sum),
            _mm256_extracti128_si256(sum, 1),
        );
        self.mins[i][j] = mins;
    }

    /// Folds the first `len` blocks, starting at block `first`, into `part`
    /// the way every kernel must: block `b` contributes
    /// `v = (dx * d) * isum - (dx * dmin) * imin` (fused, and without the
    /// second term unless `MINS`) to lane `b % 8` of a partial sum, which
    /// takes its blocks in order; [`hsum`] then adds the lanes.
    #[inline]
    #[target_feature(enable = "avx2,fma,f16c")]
    pub(super) unsafe fn fold<const MINS: bool>(
        &self,
        part: &mut [__m256; N],
        dx: [&[f32]; N],
        first: usize,
        len: usize,
    ) {
        let lanes = _mm256_cmpgt_epi32(
            _mm256_set1_epi32(len as i32),
            _mm256_setr_epi32(0, 1, 2, 3, 4, 5, 6, 7),
        );
        let d = _mm256_loadu_ps(self.d.as_ptr());
        let dmin = _mm256_loadu_ps(self.dmin.as_ptr());
        for i in 0..N {
            let dx = &dx[i][first..first + len];
            let dx = if len == CHUNK {
                _mm256_loadu_ps(dx.as_ptr())
            } else {
                _mm256_maskload_ps(dx.as_ptr(), lanes)
            };
            let (sums, mins) = (&self.sums[i], &self.mins[i]);
            let v = if MINS {
                let a = quad(&sums[..4], &mins[..4]);
                let b = if len > 4 {
                    quad(&sums[4..], &mins[4..])
                } else {
                    a
                };
                let isum = _mm256_cvtepi32_ps(_mm256_permute2x128_si256(a, b, 0x20));
                let imin = _mm256_cvtepi32_ps(_mm256_permute2x128_si256(a, b, 0x31));
                let v = _mm256_mul_ps(_mm256_mul_ps(dx, d), isum);
                _mm256_fnmadd_ps(_mm256_mul_ps(dx, dmin), imin, v)
            } else {
                let isum = quad(&sums[..4], &sums[4..]);
                _mm256_mul_ps(_mm256_mul_ps(dx, d), _mm256_cvtepi32_ps(isum))
            };
            let sum = _mm256_add_ps(part[i], v);
            part[i] = if len == CHUNK {
                sum
            } else {
                _mm256_blendv_ps(part[i], sum, _mm256_castsi256_ps(lanes))
            };
        }
    }
}

/// Lanes 0..4 are the totals of `lo[0..4]`, lanes 4..8 those of `hi[0..4]`.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn quad(lo: &[__m128i], hi: &[__m128i]) -> __m256i {
    let (lo, hi) = (&lo[..4], &hi[..4]);
    let v0 = _mm256_set_m128i(hi[0], lo[0]);
    let v1 = _mm256_set_m128i(hi[1], lo[1]);
    let v2 = _mm256_set_m128i(hi[2], lo[2]);
    let v3 = _mm256_set_m128i(hi[3], lo[3]);
    _mm256_hadd_epi32(_mm256_hadd_epi32(v0, v1), _mm256_hadd_epi32(v2, v3))
}

// Each kernel takes N activation vectors so one unpacking of a weight block
// serves N tokens. N = 1 is decode; short batches use up to N = 4. The
// kernels walk the row in chunks of eight blocks.

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn q4_k_impl<const N: usize>(row: &[u8], xs: [&Q8K; N]) -> [f32; N] {
    let low = _mm256_set1_epi8(0x0F);
    let mut part = [_mm256_setzero_ps(); N];
    let mut sums = Chunk::<N>::new();
    for (c, chunk) in row.chunks(CHUNK * 144).enumerate() {
        for (slot, blk) in chunk.chunks_exact(144).enumerate() {
            let b = CHUNK * c + slot;
            let (d, dmin) = halves(&blk[0..4]);
            let (sc, m) = scales_mins(&blk[4..16]);
            let scales = widen_scales(&sc);
            let qs = &blk[16..];
            let mut sumi = [_mm256_setzero_si256(); N];
            for j in 0..4 {
                let q = load(&qs[32 * j..]);
                let lo = _mm256_and_si256(q, low);
                let hi = _mm256_and_si256(_mm256_srli_epi16(q, 4), low);
                let (s0, s1) = (scale_at(scales, 2 * j), scale_at(scales, 2 * j + 1));
                for i in 0..N {
                    let q8 = &xs[i].qs[b * 256..][..256];
                    let p0 = scaled_dot(lo, load_i8(&q8[64 * j..]), s0);
                    let p1 = scaled_dot(hi, load_i8(&q8[64 * j + 32..]), s1);
                    sumi[i] = _mm256_add_epi32(sumi[i], _mm256_add_epi32(p0, p1));
                }
            }
            (sums.d[slot], sums.dmin[slot]) = (d, dmin);
            for i in 0..N {
                sums.set(i, slot, sumi[i], mins_dot(&m, xs[i].sums32(b)));
            }
        }
        sums.fold::<true>(
            &mut part,
            xs.map(|x| &x.d[..]),
            CHUNK * c,
            chunk.len() / 144,
        );
    }
    std::array::from_fn(|i| hsum(part[i]))
}

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn q5_k_impl<const N: usize>(row: &[u8], xs: [&Q8K; N]) -> [f32; N] {
    let low = _mm256_set1_epi8(0x0F);
    let bit4 = _mm256_set1_epi8(0x10);
    let mut part = [_mm256_setzero_ps(); N];
    let mut sums = Chunk::<N>::new();
    for (c, chunk) in row.chunks(CHUNK * 176).enumerate() {
        for (slot, blk) in chunk.chunks_exact(176).enumerate() {
            let b = CHUNK * c + slot;
            let (d, dmin) = halves(&blk[0..4]);
            let (sc, m) = scales_mins(&blk[4..16]);
            let scales = widen_scales(&sc);
            // Bit t of each qh byte is the fifth bit of sub-block t. Each bit is
            // walked to position 4 of its byte by shifting right one step per
            // sub-block: bits 0..3 start from qh << 4, bits 4..7 from qh itself.
            // 16-bit shifts are safe because only bit 4 of each byte is kept.
            let qh_raw = load(&blk[16..48]);
            let mut qh = _mm256_slli_epi16(qh_raw, 4);
            let qs = &blk[48..];
            let mut sumi = [_mm256_setzero_si256(); N];
            for j in 0..4 {
                if j == 2 {
                    qh = qh_raw;
                }
                let q = load(&qs[32 * j..]);
                let lo = _mm256_or_si256(_mm256_and_si256(q, low), _mm256_and_si256(qh, bit4));
                qh = _mm256_srli_epi16(qh, 1);
                let hi = _mm256_or_si256(
                    _mm256_and_si256(_mm256_srli_epi16(q, 4), low),
                    _mm256_and_si256(qh, bit4),
                );
                qh = _mm256_srli_epi16(qh, 1);
                let (s0, s1) = (scale_at(scales, 2 * j), scale_at(scales, 2 * j + 1));
                for i in 0..N {
                    let q8 = &xs[i].qs[b * 256..][..256];
                    let p0 = scaled_dot(lo, load_i8(&q8[64 * j..]), s0);
                    let p1 = scaled_dot(hi, load_i8(&q8[64 * j + 32..]), s1);
                    sumi[i] = _mm256_add_epi32(sumi[i], _mm256_add_epi32(p0, p1));
                }
            }
            (sums.d[slot], sums.dmin[slot]) = (d, dmin);
            for i in 0..N {
                sums.set(i, slot, sumi[i], mins_dot(&m, xs[i].sums32(b)));
            }
        }
        sums.fold::<true>(
            &mut part,
            xs.map(|x| &x.d[..]),
            CHUNK * c,
            chunk.len() / 176,
        );
    }
    std::array::from_fn(|i| hsum(part[i]))
}

/// Scale vector for 32 consecutive elements whose two halves have their own
/// scales, `sc[2 * m]` and `sc[2 * m + 1]`: lanes 0..7 cover elements 0..15,
/// lanes 8..15 elements 16..31. `half` holds the eight scales of the
/// quarter of the block that group `m` falls in, as i16, in both halves.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
pub(super) unsafe fn pair_scale(half: __m256i, m: usize) -> __m256i {
    let lane = |k: i16| k | ((k + 1) << 8);
    let (lo, hi) = (lane(4 * (m % 4) as i16), lane(4 * (m % 4) as i16 + 2));
    _mm256_shuffle_epi8(
        half,
        _mm256_set_m128i(_mm_set1_epi16(hi), _mm_set1_epi16(lo)),
    )
}

/// Top two bits of a Q6_K group: bits `shift..shift+2` of each qh byte,
/// moved to bits 4..6.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
pub(super) unsafe fn q6_high(qh: __m256i, shift: i32) -> __m256i {
    let three = _mm256_set1_epi8(3);
    _mm256_slli_epi16(
        _mm256_and_si256(_mm256_srl_epi16(qh, _mm_cvtsi32_si128(shift)), three),
        4,
    )
}

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn q6_k_impl<const N: usize>(row: &[u8], xs: [&Q8K; N]) -> [f32; N] {
    let low = _mm256_set1_epi8(0x0F);
    let mut part = [_mm256_setzero_ps(); N];
    let mut sums = Chunk::<N>::new();
    for (c, chunk) in row.chunks(CHUNK * 210).enumerate() {
        for (slot, blk) in chunk.chunks_exact(210).enumerate() {
            let b = CHUNK * c + slot;
            let sc = &blk[192..208];
            let d = half(&blk[208..210]);
            // Weights are stored as q + 32; take the 32 back out through the
            // per-16 sums, which line up one-to-one with the scales.
            let sc16 = _mm256_cvtepi8_epi16(_mm_loadu_si128(sc.as_ptr() as *const __m128i));
            let halves16 = [
                _mm256_permute2x128_si256(sc16, sc16, 0x00),
                _mm256_permute2x128_si256(sc16, sc16, 0x11),
            ];

            let mut sumi = [_mm256_setzero_si256(); N];
            for n in 0..2 {
                let ql0 = load(&blk[64 * n..]);
                let ql1 = load(&blk[64 * n + 32..]);
                let qh = load(&blk[128 + 32 * n..]);
                let groups = [
                    _mm256_or_si256(_mm256_and_si256(ql0, low), q6_high(qh, 0)),
                    _mm256_or_si256(_mm256_and_si256(ql1, low), q6_high(qh, 2)),
                    _mm256_or_si256(
                        _mm256_and_si256(_mm256_srli_epi16(ql0, 4), low),
                        q6_high(qh, 4),
                    ),
                    _mm256_or_si256(
                        _mm256_and_si256(_mm256_srli_epi16(ql1, 4), low),
                        q6_high(qh, 6),
                    ),
                ];
                for (g, q) in groups.into_iter().enumerate() {
                    let e = 128 * n + 32 * g;
                    let s = pair_scale(halves16[e / 128], e / 32);
                    for i in 0..N {
                        let y = load_i8(&xs[i].qs[b * 256..][e..e + 32]);
                        sumi[i] = _mm256_add_epi32(sumi[i], scaled_dot(q, y, s));
                    }
                }
            }
            sums.d[slot] = d;
            for i in 0..N {
                let bsums = xs[i].block(b).2;
                let bias =
                    _mm256_madd_epi16(sc16, _mm256_loadu_si256(bsums.as_ptr() as *const __m256i));
                let total = _mm256_sub_epi32(sumi[i], _mm256_slli_epi32(bias, 5));
                sums.set(i, slot, total, _mm_setzero_si128());
            }
        }
        sums.fold::<false>(
            &mut part,
            xs.map(|x| &x.d[..]),
            CHUNK * c,
            chunk.len() / 210,
        );
    }
    std::array::from_fn(|i| hsum(part[i]))
}

/// Signed int8 weights times signed int8 activations: `maddubs` needs an
/// unsigned left operand, so the weight sign moves onto the activations.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
pub(super) unsafe fn signed_dot(w_abs: __m256i, w: __m256i, y: __m256i) -> __m256i {
    _mm256_madd_epi16(
        _mm256_maddubs_epi16(w_abs, _mm256_sign_epi8(y, w)),
        _mm256_set1_epi16(1),
    )
}

// The 32-value formats fold their blocks like the K-quants without mins,
// block `k` into lane `k % 8`, but keep each chunk of eight blocks in
// registers: their blocks are too short to pay for `Chunk`'s bookkeeping.

/// The totals of eight vectors of i32 sums, one lane per vector.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
pub(super) unsafe fn lane_totals(p: &[__m256i; 8]) -> __m256i {
    let a0 = _mm256_hadd_epi32(p[0], p[1]);
    let a1 = _mm256_hadd_epi32(p[2], p[3]);
    let a2 = _mm256_hadd_epi32(p[4], p[5]);
    let a3 = _mm256_hadd_epi32(p[6], p[7]);
    let b0 = _mm256_hadd_epi32(a0, a1);
    let b1 = _mm256_hadd_epi32(a2, a3);
    _mm256_add_epi32(
        _mm256_permute2x128_si256(b0, b1, 0x20),
        _mm256_permute2x128_si256(b0, b1, 0x31),
    )
}

/// Adds `(dx * dw) * isum` to the first `len` lanes of `part`, as
/// `Chunk::fold` does for blocks without mins.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn fold8(part: &mut __m256, dx: &[f32], dw: __m256, isum: __m256i, len: usize) {
    let v = |dx| _mm256_mul_ps(_mm256_mul_ps(dx, dw), _mm256_cvtepi32_ps(isum));
    if len == 8 {
        *part = _mm256_add_ps(*part, v(_mm256_loadu_ps(dx[..8].as_ptr())));
    } else {
        let lanes = _mm256_cmpgt_epi32(
            _mm256_set1_epi32(len as i32),
            _mm256_setr_epi32(0, 1, 2, 3, 4, 5, 6, 7),
        );
        let dx = _mm256_maskload_ps(dx[..len].as_ptr(), lanes);
        let sum = _mm256_add_ps(*part, v(dx));
        *part = _mm256_blendv_ps(*part, sum, _mm256_castsi256_ps(lanes));
    }
}

/// The f16 scales at the start of up to eight blocks of `size` bytes.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn block_scales(chunk: &[u8], size: usize) -> __m256 {
    let mut d = [0u16; 8];
    for (d, blk) in d.iter_mut().zip(chunk.chunks_exact(size)) {
        *d = u16::from_le_bytes([blk[0], blk[1]]);
    }
    _mm256_cvtph_ps(_mm_loadu_si128(d.as_ptr() as *const __m128i))
}

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn q8_0_impl<const N: usize>(row: &[u8], xs: [&Q8; N]) -> [f32; N] {
    let mut part = [_mm256_setzero_ps(); N];
    for (c, chunk) in row.chunks(8 * 34).enumerate() {
        let mut p = [[_mm256_setzero_si256(); 8]; N];
        for (j, blk) in chunk.chunks_exact(34).enumerate() {
            let k = 8 * c + j;
            let w = load(&blk[2..]);
            let w_abs = _mm256_abs_epi8(w);
            for (p, x) in p.iter_mut().zip(xs) {
                p[j] = signed_dot(w_abs, w, load_i8(&x.qs[32 * k..]));
            }
        }
        let dw = block_scales(chunk, 34);
        for ((part, p), x) in part.iter_mut().zip(&p).zip(xs) {
            fold8(part, &x.d[8 * c..], dw, lane_totals(p), chunk.len() / 34);
        }
    }
    std::array::from_fn(|i| hsum(part[i]))
}

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn q4_0_impl<const N: usize>(row: &[u8], xs: [&Q8; N]) -> [f32; N] {
    let low = _mm256_set1_epi8(0x0F);
    let ones = _mm256_set1_epi16(1);
    let mut part = [_mm256_setzero_ps(); N];
    for (c, chunk) in row.chunks(8 * 18).enumerate() {
        let len = chunk.len() / 18;
        let mut p = [[_mm256_setzero_si256(); 8]; N];
        for (j, blk) in chunk.chunks_exact(18).enumerate() {
            let k = 8 * c + j;
            // Low nibbles are elements 0..16, high nibbles 16..32.
            let q =
                _mm256_broadcastsi128_si256(_mm_loadu_si128(blk[2..].as_ptr() as *const __m128i));
            let w = _mm256_and_si256(_mm256_blend_epi32(q, _mm256_srli_epi16(q, 4), 0xF0), low);
            for (p, x) in p.iter_mut().zip(xs) {
                let y = load_i8(&x.qs[32 * k..]);
                p[j] = _mm256_madd_epi16(_mm256_maddubs_epi16(w, y), ones);
            }
        }
        let dw = block_scales(chunk, 18);
        for ((part, p), x) in part.iter_mut().zip(&p).zip(xs) {
            // weights are stored as q + 8; the 8 leaves through the block sums
            let mut sums = [0i16; 8];
            sums[..len].copy_from_slice(&x.sums[8 * c..][..len]);
            let sums = _mm256_cvtepi16_epi32(_mm_loadu_si128(sums.as_ptr() as *const __m128i));
            let isum = _mm256_sub_epi32(lane_totals(p), _mm256_slli_epi32(sums, 3));
            fold8(part, &x.d[8 * c..], dw, isum, len);
        }
    }
    std::array::from_fn(|i| hsum(part[i]))
}
