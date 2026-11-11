//! Tile kernels: a few unpacked weight rows times eight interleaved tokens,
//! or four or two for short batches.
//!
//! Each step broadcasts four weight bytes of one row and multiplies them
//! with four values of all eight tokens, so a lane of the result is one
//! token. Narrower groups broadcast eight or sixteen bytes against as many
//! values of four or two tokens and add each token's lanes once per block,
//! so every `maddubs` still does 32 products. `maddubs` products of a scale
//! group are added as i16 for as many steps as cannot overflow, and only
//! then widened with the scale by one `madd`. That halves the multiplies of
//! the one-row kernels, which pay a `madd` for every `maddubs`.

use std::arch::x86_64::*;

use super::avx2::{half, halves, load, load_i8, q6_high};
use super::{scales_mins, unpack32, TileKernel, Unpacked, Unpacked32, TILE_ROWS};
use crate::q8::Q8Group;
use crate::q8k::{Q8KGroup, GROUP};
use kinetic_quant::{q3_k_scales, TensorType};

pub fn kernel(ty: TensorType) -> Option<TileKernel<Unpacked, Q8KGroup>> {
    // SAFETY (each closure): only reachable after `avx2::available()`
    // confirmed the target features the implementations are compiled for.
    // The largest i16 partial sums are 8 * 2 * 15 * 127 (Q4_K), 4 * 2 * 31 *
    // 127 (Q5_K), 2 * 2 * 63 * 127 (Q6_K), 4 * 2 * 3 * 127 (Q2_K) and
    // 4 * 2 * 7 * 127 (Q3_K).
    match ty {
        TensorType::Q4K => Some(TileKernel {
            unpack: |row, out| unsafe { unpack_q4_k(row, out) },
            dot4: |rows, x| unsafe { tiles::<TILE_ROWS, 8, 32, 32, 0>(rows, x) },
            dot1: |row, x| unsafe { tiles::<1, 8, 32, 32, 0>([row], x)[0] },
        }),
        TensorType::Q5K => Some(TileKernel {
            unpack: |row, out| unsafe { unpack_q5_k(row, out) },
            dot4: |rows, x| unsafe { tiles::<TILE_ROWS, 4, 32, 32, 0>(rows, x) },
            dot1: |row, x| unsafe { tiles::<1, 4, 32, 32, 0>([row], x)[0] },
        }),
        TensorType::Q6K => Some(TileKernel {
            unpack: |row, out| unsafe { unpack_q6_k(row, out) },
            dot4: |rows, x| unsafe { tiles::<TILE_ROWS, 2, 16, 0, 5>(rows, x) },
            dot1: |row, x| unsafe { tiles::<1, 2, 16, 0, 5>([row], x)[0] },
        }),
        TensorType::Q2K => Some(TileKernel {
            unpack: |row, out| unsafe { unpack_q2_k(row, out) },
            dot4: |rows, x| unsafe { tiles::<TILE_ROWS, 4, 16, 16, 0>(rows, x) },
            dot1: |row, x| unsafe { tiles::<1, 4, 16, 16, 0>([row], x)[0] },
        }),
        TensorType::Q3K => Some(TileKernel {
            unpack: |row, out| unsafe { unpack_q3_k(row, out) },
            dot4: |rows, x| unsafe { tiles::<TILE_ROWS, 4, 16, 0, 2>(rows, x) },
            dot1: |row, x| unsafe { tiles::<1, 4, 16, 0, 2>([row], x)[0] },
        }),
        _ => None,
    }
}

#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn store(p: &mut [u8], v: __m256i) {
    assert!(p.len() >= 32);
    _mm256_storeu_si256(p.as_mut_ptr() as *mut __m256i, v);
}

/// `lo` and `hi` as the low and high i16 halves of one i32 lane.
fn pair(lo: i16, hi: i16) -> i32 {
    (lo as u16 as i32) | ((hi as i32) << 16)
}

/// Eight i32 scales, each copied into both i16 halves of its lane.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn store_doubled(out: &mut [i32], s: __m256i) {
    assert!(out.len() >= 8);
    let v = _mm256_blend_epi16(s, _mm256_slli_epi32(s, 16), 0b1010_1010);
    _mm256_storeu_si256(out.as_mut_ptr() as *mut __m256i, v);
}

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn unpack_q4_k(row: &[u8], out: &mut [Unpacked]) {
    let low = _mm256_set1_epi8(0x0F);
    for (blk, u) in row.chunks_exact(144).zip(out) {
        (u.d, u.dmin) = halves(&blk[0..4]);
        let (sc, m) = scales_mins(&blk[4..16]);
        for j in 0..4 {
            let q = load(&blk[16 + 32 * j..]);
            store(&mut u.q[64 * j..], _mm256_and_si256(q, low));
            store(
                &mut u.q[64 * j + 32..],
                _mm256_and_si256(_mm256_srli_epi16(q, 4), low),
            );
        }
        set_k_scales(u, &sc, &m);
    }
}

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn unpack_q5_k(row: &[u8], out: &mut [Unpacked]) {
    let low = _mm256_set1_epi8(0x0F);
    let bit4 = _mm256_set1_epi8(0x10);
    for (blk, u) in row.chunks_exact(176).zip(out) {
        (u.d, u.dmin) = halves(&blk[0..4]);
        let (sc, m) = scales_mins(&blk[4..16]);
        // Same bit walk as the one-row kernel: bit t of qh is the fifth bit
        // of sub-block t, moved to bit 4 one shift per sub-block.
        let qh_raw = load(&blk[16..48]);
        let mut qh = _mm256_slli_epi16(qh_raw, 4);
        for j in 0..4 {
            if j == 2 {
                qh = qh_raw;
            }
            let q = load(&blk[48 + 32 * j..]);
            let lo = _mm256_or_si256(_mm256_and_si256(q, low), _mm256_and_si256(qh, bit4));
            qh = _mm256_srli_epi16(qh, 1);
            let hi = _mm256_or_si256(
                _mm256_and_si256(_mm256_srli_epi16(q, 4), low),
                _mm256_and_si256(qh, bit4),
            );
            qh = _mm256_srli_epi16(qh, 1);
            store(&mut u.q[64 * j..], lo);
            store(&mut u.q[64 * j + 32..], hi);
        }
        set_k_scales(u, &sc, &m);
    }
}

#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn set_k_scales(u: &mut Unpacked, sc: &[u8; 8], m: &[u8; 8]) {
    let bytes = |b: &[u8; 8]| _mm_cvtsi64_si128(i64::from_le_bytes(*b));
    store_doubled(&mut u.sc, _mm256_cvtepu8_epi32(bytes(sc)));
    // the pairs of the mins are the mins as consecutive i16
    let m = _mm_cvtepu8_epi16(bytes(m));
    _mm_storeu_si128(u.pairs.as_mut_ptr() as *mut __m128i, m);
}

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn unpack_q6_k(row: &[u8], out: &mut [Unpacked]) {
    let low = _mm256_set1_epi8(0x0F);
    for (blk, u) in row.chunks_exact(210).zip(out) {
        for n in 0..2 {
            let ql0 = load(&blk[64 * n..]);
            let ql1 = load(&blk[64 * n + 32..]);
            let qh = load(&blk[128 + 32 * n..]);
            let q = &mut u.q[128 * n..];
            store(
                &mut q[0..],
                _mm256_or_si256(_mm256_and_si256(ql0, low), q6_high(qh, 0)),
            );
            store(
                &mut q[32..],
                _mm256_or_si256(_mm256_and_si256(ql1, low), q6_high(qh, 2)),
            );
            store(
                &mut q[64..],
                _mm256_or_si256(
                    _mm256_and_si256(_mm256_srli_epi16(ql0, 4), low),
                    q6_high(qh, 4),
                ),
            );
            store(
                &mut q[96..],
                _mm256_or_si256(
                    _mm256_and_si256(_mm256_srli_epi16(ql1, 4), low),
                    q6_high(qh, 6),
                ),
            );
        }
        let sc = _mm_loadu_si128(blk[192..208].as_ptr() as *const __m128i);
        store_doubled(&mut u.sc[..8], _mm256_cvtepi8_epi32(sc));
        store_doubled(&mut u.sc[8..], _mm256_cvtepi8_epi32(_mm_srli_si128(sc, 8)));
        _mm256_storeu_si256(
            u.pairs.as_mut_ptr() as *mut __m256i,
            _mm256_cvtepi8_epi16(sc),
        );
        u.d = half(&blk[208..210]);
        u.dmin = 0.0;
    }
}

// Element `128 n + 32 p + r` of a Q2_K or Q3_K block is plane `p` of byte
// `r` of the `n`th 32-byte run of its quants.

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn unpack_q2_k(row: &[u8], out: &mut [Unpacked]) {
    let three = _mm256_set1_epi8(3);
    for (blk, u) in row.chunks_exact(84).zip(out) {
        for n in 0..2 {
            let q = load(&blk[16 + 32 * n..]);
            for p in 0..4 {
                let plane = _mm256_srl_epi16(q, _mm_cvtsi32_si128(2 * p as i32));
                store(&mut u.q[128 * n + 32 * p..], _mm256_and_si256(plane, three));
            }
        }
        let scales = &blk[..16];
        for (u, &s) in u.sc.iter_mut().zip(scales) {
            *u = pair((s & 0xF) as i16, (s & 0xF) as i16);
        }
        for p in 0..8 {
            u.pairs[p] = pair((scales[2 * p] >> 4) as i16, (scales[2 * p + 1] >> 4) as i16);
        }
        (u.d, u.dmin) = halves(&blk[80..84]);
    }
}

/// Q3_K weights are unpacked as `q + 4`, and the scales double as the
/// factors of the offset, as for Q6_K.
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn unpack_q3_k(row: &[u8], out: &mut [Unpacked]) {
    let three = _mm256_set1_epi8(3);
    let four = _mm256_set1_epi8(4);
    for (blk, u) in row.chunks_exact(110).zip(out) {
        let hmask = load(blk);
        for n in 0..2 {
            let q = load(&blk[32 + 32 * n..]);
            for p in 0..4 {
                let shift = _mm_cvtsi32_si128(2 * p as i32);
                let low = _mm256_and_si256(_mm256_srl_epi16(q, shift), three);
                let bit = _mm256_set1_epi8(1 << (4 * n + p));
                let high = _mm256_cmpeq_epi8(_mm256_and_si256(hmask, bit), bit);
                let w = _mm256_or_si256(low, _mm256_and_si256(high, four));
                store(&mut u.q[128 * n + 32 * p..], w);
            }
        }
        let sc = q3_k_scales(&blk[96..108]);
        for (u, &s) in u.sc.iter_mut().zip(&sc) {
            *u = pair(s as i16, s as i16);
        }
        for p in 0..8 {
            u.pairs[p] = pair(sc[2 * p] as i16, sc[2 * p + 1] as i16);
        }
        u.d = half(&blk[108..110]);
        u.dmin = 0.0;
    }
}

/// The first `V` (4, 8 or 16) bytes of `q` in every `V`-byte lane.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn broadcast<const V: usize>(q: &[u8]) -> __m256i {
    match V {
        4 => _mm256_set1_epi32(i32::from_le_bytes(q[..4].try_into().unwrap())),
        8 => _mm256_set1_epi64x(i64::from_le_bytes(q[..8].try_into().unwrap())),
        _ => _mm256_broadcastsi128_si256(_mm_loadu_si128(q[..16].as_ptr() as *const __m128i)),
    }
}

/// [`broadcast`] of `V / 2` i16 weights.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn broadcast16<const V: usize>(w: &[i16]) -> __m256i {
    let mut b = [0u8; 16];
    for (b, w) in b.chunks_exact_mut(2).zip(&w[..V / 2]) {
        b.copy_from_slice(&w.to_le_bytes());
    }
    broadcast::<V>(&b)
}

/// Adds the `V / 4` i32 lanes of each token of a step, so token `t` ends
/// up in lane `t`.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn token_sums<const V: usize>(v: __m256i) -> __m256i {
    match V {
        4 => v,
        8 => _mm256_permute4x64_epi64(_mm256_hadd_epi32(v, v), 0b11_01_10_00),
        _ => {
            let h = _mm256_hadd_epi32(v, v);
            let h = _mm256_hadd_epi32(h, h);
            _mm256_permutevar8x32_epi32(h, _mm256_setr_epi32(0, 4, 0, 4, 0, 4, 0, 4))
        }
    }
}

/// [`tile`] for the width of `x`.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn tiles<
    const R: usize,
    const MADD_STEPS: usize,
    const SCALE_LEN: usize,
    const MIN_LEN: usize,
    const OFFSET_SHIFT: i32,
>(
    rows: [&[Unpacked]; R],
    x: &Q8KGroup,
) -> [[f32; GROUP]; R] {
    match x.width {
        GROUP => tile::<R, MADD_STEPS, SCALE_LEN, MIN_LEN, OFFSET_SHIFT, 4>(rows, x),
        4 => tile::<R, MADD_STEPS, SCALE_LEN, MIN_LEN, OFFSET_SHIFT, 8>(rows, x),
        _ => tile::<R, MADD_STEPS, SCALE_LEN, MIN_LEN, OFFSET_SHIFT, 16>(rows, x),
    }
}

/// `R` rows times the tokens of `x`, `V` values of each per step.
///
/// Up to `MADD_STEPS` steps are summed as i16 per `madd`; one scale
/// covers `SCALE_LEN` values. With a nonzero `MIN_LEN` (Q4_K and Q5_K: 32,
/// Q2_K: 16) blocks subtract a min per `MIN_LEN` values; without, weights
/// are stored as `q + (1 << OFFSET_SHIFT)` (Q6_K: 32, Q3_K: 4), which comes
/// out of the integer sum. The f32 steps are exactly those of the one-row
/// kernels.
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn tile<
    const R: usize,
    const MADD_STEPS: usize,
    const SCALE_LEN: usize,
    const MIN_LEN: usize,
    const OFFSET_SHIFT: i32,
    const V: usize,
>(
    rows: [&[Unpacked]; R],
    x: &Q8KGroup,
) -> [[f32; GROUP]; R] {
    let blocks = x.blocks();
    for row in rows {
        assert_eq!(row.len(), blocks);
    }
    let block_bytes = 256 * 32 / V;
    let steps = MADD_STEPS.min(SCALE_LEN / V);
    // Partial sums by block lane, as in `avx2::Chunk::fold`.
    let mut part = [[_mm256_setzero_ps(); 8]; R];
    for b in 0..blocks {
        let qs = &x.qs[b * block_bytes..][..block_bytes];
        let mut isum = [_mm256_setzero_si256(); R];
        for s in 0..32 / V {
            // Eight steps of activations stay in registers for all rows;
            // each row's weights are broadcast `V` bytes at a time.
            let mut y = [_mm256_setzero_si256(); 8];
            for (k, y) in y.iter_mut().enumerate() {
                *y = load_i8(&qs[256 * s + 32 * k..][..32]);
            }
            for r in 0..R {
                let u = &rows[r][b];
                let q = &u.q[8 * V * s..][..8 * V];
                for c in (0..8).step_by(steps) {
                    let mut p = _mm256_maddubs_epi16(broadcast::<V>(&q[V * c..]), y[c]);
                    for k in c + 1..c + steps {
                        let w = broadcast::<V>(&q[V * k..]);
                        p = _mm256_add_epi16(p, _mm256_maddubs_epi16(w, y[k]));
                    }
                    let scale = _mm256_set1_epi32(u.sc[(8 * V * s + V * c) / SCALE_LEN]);
                    isum[r] = _mm256_add_epi32(isum[r], _mm256_madd_epi16(p, scale));
                }
            }
        }
        let dx = _mm256_loadu_ps(x.d[b * GROUP..][..GROUP].as_ptr());
        for r in 0..R {
            let u = &rows[r][b];
            let isum = token_sums::<V>(isum[r]);
            let dd = _mm256_mul_ps(dx, _mm256_set1_ps(u.d));
            let sums16 = &x.sums16[b * 8 * 2 * GROUP..][..8 * 2 * GROUP];
            let v = if MIN_LEN > 0 {
                let imin = if MIN_LEN == 32 {
                    let sums32 = &x.sums32[b * 4 * 2 * GROUP..][..4 * 2 * GROUP];
                    pair_dot(sums32, &u.pairs[..4])
                } else {
                    pair_dot(sums16, &u.pairs)
                };
                let dm = _mm256_mul_ps(dx, _mm256_set1_ps(u.dmin));
                let imin = _mm256_cvtepi32_ps(imin);
                _mm256_fnmadd_ps(dm, imin, _mm256_mul_ps(dd, _mm256_cvtepi32_ps(isum)))
            } else {
                let bias = pair_dot(sums16, &u.pairs);
                let shift = _mm_cvtsi32_si128(OFFSET_SHIFT);
                let total = _mm256_sub_epi32(isum, _mm256_sll_epi32(bias, shift));
                _mm256_mul_ps(dd, _mm256_cvtepi32_ps(total))
            };
            part[r][b % 8] = _mm256_add_ps(part[r][b % 8], v);
        }
    }
    reduce(&part)
}

/// Adds each row's eight partial sums in the lane order of `avx2::hsum`:
/// (0 + 4) + (2 + 6), then (1 + 5) + (3 + 7).
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn reduce<const R: usize>(part: &[[__m256; 8]; R]) -> [[f32; GROUP]; R] {
    let mut out = [[0.0; GROUP]; R];
    for (out, p) in out.iter_mut().zip(part) {
        let (q0, q1) = (_mm256_add_ps(p[0], p[4]), _mm256_add_ps(p[1], p[5]));
        let (q2, q3) = (_mm256_add_ps(p[2], p[6]), _mm256_add_ps(p[3], p[7]));
        let sum = _mm256_add_ps(_mm256_add_ps(q0, q2), _mm256_add_ps(q1, q3));
        _mm256_storeu_ps(out.as_mut_ptr(), sum);
    }
    out
}

/// Per token, `sum(pairs[p].lo * sums[p][t][0] + pairs[p].hi * sums[p][t][1])`.
#[inline]
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn pair_dot(sums: &[i16], pairs: &[i32]) -> __m256i {
    let mut acc = _mm256_setzero_si256();
    for (p, &f) in pairs.iter().enumerate() {
        let s = _mm256_loadu_si256(sums[p * 2 * GROUP..][..2 * GROUP].as_ptr() as *const __m256i);
        acc = _mm256_add_epi32(acc, _mm256_madd_epi16(s, _mm256_set1_epi32(f)));
    }
    acc
}

pub fn kernel32(ty: TensorType) -> Option<TileKernel<Unpacked32, Q8Group>> {
    // Stored codes sum as i16 over 8 steps when below 16 (8 * 2 * 15 * 127)
    // and over 4 when below 32 (4 * 2 * 31 * 127).
    Some(match ty {
        TensorType::Q4_0 => tile32_kernel::<8, 8, false>(|row, out| {
            // SAFETY: as in `tile32_kernel`.
            unsafe { unpack_q4_0(row, out) }
        }),
        TensorType::Q4_1 => tile32_kernel::<8, 0, true>(unpack32::q4_1),
        TensorType::Q5_0 => tile32_kernel::<4, 16, false>(unpack32::q5_0),
        TensorType::Q5_1 => tile32_kernel::<4, 0, true>(unpack32::q5_1),
        TensorType::MXFP4 => tile32_kernel::<4, 12, false>(unpack32::mxfp4),
        TensorType::IQ4NL => tile32_kernel::<0, 0, false>(unpack32::iq4_nl),
        // SAFETY (each closure): as in `tile32_kernel`.
        TensorType::Q8_0 => TileKernel {
            unpack: |row, out| unsafe { unpack_q8_0(row, out) },
            dot4: |rows, x| unsafe {
                match x.width {
                    GROUP => tile_q8_0::<TILE_ROWS, 4>(rows, x),
                    4 => tile_q8_0::<TILE_ROWS, 8>(rows, x),
                    _ => tile_q8_0::<TILE_ROWS, 16>(rows, x),
                }
            },
            dot1: |row, x| unsafe {
                match x.width {
                    GROUP => tile_q8_0::<1, 4>([row], x)[0],
                    4 => tile_q8_0::<1, 8>([row], x)[0],
                    _ => tile_q8_0::<1, 16>([row], x)[0],
                }
            },
        },
        _ => return None,
    })
}

/// The [`tile32`] kernels with these parameters.
fn tile32_kernel<const STEPS: usize, const OFFSET: i32, const MIN: bool>(
    unpack: fn(&[u8], &mut [Unpacked32]),
) -> TileKernel<Unpacked32, Q8Group> {
    // SAFETY (each closure): only reached through `kernel32`, after
    // `avx2::available()` confirmed the target features.
    TileKernel {
        unpack,
        dot4: |rows, x| unsafe {
            match x.width {
                GROUP => tile32::<TILE_ROWS, STEPS, OFFSET, MIN, 4>(rows, x),
                4 => tile32::<TILE_ROWS, STEPS, OFFSET, MIN, 8>(rows, x),
                _ => tile32::<TILE_ROWS, STEPS, OFFSET, MIN, 16>(rows, x),
            }
        },
        dot1: |row, x| unsafe {
            match x.width {
                GROUP => tile32::<1, STEPS, OFFSET, MIN, 4>([row], x)[0],
                4 => tile32::<1, STEPS, OFFSET, MIN, 8>([row], x)[0],
                _ => tile32::<1, STEPS, OFFSET, MIN, 16>([row], x)[0],
            }
        },
    }
}

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn unpack_q8_0(row: &[u8], out: &mut [Unpacked32]) {
    for (blk, u) in row.chunks_exact(34).zip(out) {
        u.d = half(blk);
        u.q.copy_from_slice(&blk[2..34]);
    }
}

#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn unpack_q4_0(row: &[u8], out: &mut [Unpacked32]) {
    let low = _mm_set1_epi8(0x0F);
    for (blk, u) in row.chunks_exact(18).zip(out) {
        u.d = half(blk);
        let q = _mm_loadu_si128(blk[2..].as_ptr() as *const __m128i);
        let v = _mm256_set_m128i(
            _mm_and_si128(_mm_srli_epi16(q, 4), low),
            _mm_and_si128(q, low),
        );
        store(&mut u.q, v);
    }
}

/// [`tile32`] for Q8_0, whose signed weights sit in `q`: the sign moves
/// onto the activations as in `avx2::signed_dot`, so one `maddubs` takes
/// four weights of all eight tokens.
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn tile_q8_0<const R: usize, const V: usize>(
    rows: [&[Unpacked32]; R],
    x: &Q8Group,
) -> [[f32; GROUP]; R] {
    let blocks = x.blocks();
    for row in rows {
        assert_eq!(row.len(), blocks);
    }
    let width = 32 / V;
    let ones = _mm256_set1_epi16(1);
    let mut part = [[_mm256_setzero_ps(); 8]; R];
    for b in 0..blocks {
        let qs = &x.qs[b * 32 * width..][..32 * width];
        let y: [__m256i; 8] = std::array::from_fn(|k| {
            if k < width {
                load_i8(&qs[32 * k..][..32])
            } else {
                _mm256_setzero_si256()
            }
        });
        let dx = _mm256_loadu_ps(x.d[b * GROUP..][..GROUP].as_ptr());
        for r in 0..R {
            let u = &rows[r][b];
            let mut isum = _mm256_setzero_si256();
            for (k, y) in y[..width].iter().enumerate() {
                let w = broadcast::<V>(&u.q[V * k..]);
                let p = _mm256_maddubs_epi16(_mm256_abs_epi8(w), _mm256_sign_epi8(*y, w));
                isum = _mm256_add_epi32(isum, _mm256_madd_epi16(p, ones));
            }
            let isum = token_sums::<V>(isum);
            let dd = _mm256_mul_ps(dx, _mm256_set1_ps(u.d));
            let v = _mm256_mul_ps(dd, _mm256_cvtepi32_ps(isum));
            part[r][b % 8] = _mm256_add_ps(part[r][b % 8], v);
        }
    }
    reduce(&part)
}

/// `R` rows of a 32-value format times the eight tokens of `x`, with the
/// f32 steps of the one-row kernels: those of `avx2::Chunk::fold` for
/// blocks without mins, plus `(dx * m) * sum(y)` for the offset `m` of
/// Q4_1 and Q5_1 (`MIN`).
///
/// With `STEPS` > 0 the weights are unsigned codes, `OFFSET` above the
/// value, and `STEPS` four-value `maddubs` are summed as i16 per `madd`.
/// Otherwise (IQ4_NL) they are too wide for that, and `maddubs` would
/// also need their signs moved onto the activations, so they multiply as
/// i16 pairs, one `madd` per two values of all eight tokens.
#[target_feature(enable = "avx2,fma,f16c")]
unsafe fn tile32<
    const R: usize,
    const STEPS: usize,
    const OFFSET: i32,
    const MIN: bool,
    const V: usize,
>(
    rows: [&[Unpacked32]; R],
    x: &Q8Group,
) -> [[f32; GROUP]; R] {
    let blocks = x.blocks();
    for row in rows {
        assert_eq!(row.len(), blocks);
    }
    let width = 32 / V;
    let steps = STEPS.min(width);
    let ones = _mm256_set1_epi16(1);
    let mut part = [[_mm256_setzero_ps(); 8]; R];
    for b in 0..blocks {
        let qs = &x.qs[b * 32 * width..][..32 * width];
        let mut y = [_mm256_setzero_si256(); 8];
        for (k, y) in y[..width].iter_mut().enumerate() {
            *y = load_i8(&qs[32 * k..][..32]);
        }
        let dx = _mm256_loadu_ps(x.d[b * GROUP..][..GROUP].as_ptr());
        let sums = _mm256_loadu_si256(x.sums[b * GROUP..][..GROUP].as_ptr() as *const __m256i);
        for r in 0..R {
            let u = &rows[r][b];
            let isum = if STEPS > 0 {
                let mut acc = _mm256_setzero_si256();
                for (ys, qs) in y[..width]
                    .chunks_exact(steps)
                    .zip(u.q.chunks_exact(V * steps))
                {
                    let mut p = _mm256_setzero_si256();
                    for (&y, q) in ys.iter().zip(qs.chunks_exact(V)) {
                        p = _mm256_add_epi16(p, _mm256_maddubs_epi16(broadcast::<V>(q), y));
                    }
                    acc = _mm256_add_epi32(acc, _mm256_madd_epi16(p, ones));
                }
                let acc = token_sums::<V>(acc);
                let offset = _mm256_mullo_epi32(sums, _mm256_set1_epi32(OFFSET));
                _mm256_sub_epi32(acc, offset)
            } else {
                let qs16 = &x.qs16[b * 32 * width..][..32 * width];
                let mut acc = _mm256_setzero_si256();
                for (k, w) in u.w.chunks_exact(V / 2).enumerate() {
                    let y = _mm256_loadu_si256(qs16[16 * k..][..16].as_ptr() as *const __m256i);
                    acc = _mm256_add_epi32(acc, _mm256_madd_epi16(broadcast16::<V>(w), y));
                }
                token_sums::<V>(acc)
            };
            let dd = _mm256_mul_ps(dx, _mm256_set1_ps(u.d));
            let mut v = _mm256_mul_ps(dd, _mm256_cvtepi32_ps(isum));
            if MIN {
                let dm = _mm256_mul_ps(dx, _mm256_set1_ps(u.m));
                v = _mm256_fmadd_ps(dm, _mm256_cvtepi32_ps(sums), v);
            }
            part[r][b % 8] = _mm256_add_ps(part[r][b % 8], v);
        }
    }
    reduce(&part)
}
