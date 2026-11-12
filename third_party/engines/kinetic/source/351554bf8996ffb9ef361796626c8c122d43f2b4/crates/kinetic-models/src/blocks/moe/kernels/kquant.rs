//! The K-quants unpacked: every format keeps 16 or 32 values per integer
//! scale, so value `i` of a block becomes `qs[i]` times `mul[i / 16]`, less
//! `mins[i / 16]` in the formats with offsets.

use super::{half, Unpacked, QK};

/// The 6-bit scale and offset of 32-value group `j` in the 12 bytes Q4_K
/// and Q5_K pack them into.
fn scale_min(j: usize, q: &[u8]) -> (i16, i16) {
    let (sc, m) = if j < 4 {
        (q[j] & 63, q[j + 4] & 63)
    } else {
        (
            (q[j + 4] & 0xF) | ((q[j - 4] >> 6) << 4),
            (q[j + 4] >> 4) | ((q[j] >> 6) << 4),
        )
    };
    (sc as i16, m as i16)
}

fn k4_scales(src: &[u8], out: &mut Unpacked) {
    out.d = half(&src[0..2]);
    out.dmin = half(&src[2..4]);
    for j in 0..QK / 32 {
        let (sc, m) = scale_min(j, &src[4..16]);
        out.mul[2 * j..2 * j + 2].fill(sc);
        out.mins[2 * j..2 * j + 2].fill(m);
    }
}

// Each 32 bytes of qs hold 64 values: the low nibbles, then the high.
pub(super) fn q4_k(src: &[u8], out: &mut Unpacked) {
    let qs = &src[16..144];
    for (n, dst) in out.qs.chunks_exact_mut(64).enumerate() {
        for (l, &q) in qs[32 * n..32 * n + 32].iter().enumerate() {
            dst[l] = (q & 0xF) as i8;
            dst[l + 32] = (q >> 4) as i8;
        }
    }
    k4_scales(src, out);
}

// Q4_K with a fifth bit per value from qh, two bits of each byte per 64.
pub(super) fn q5_k(src: &[u8], out: &mut Unpacked) {
    let (qh, qs) = (&src[16..48], &src[48..176]);
    for (n, dst) in out.qs.chunks_exact_mut(64).enumerate() {
        for (l, &q) in qs[32 * n..32 * n + 32].iter().enumerate() {
            let high = |bit: usize| ((qh[l] >> bit) & 1) << 4;
            dst[l] = ((q & 0xF) | high(2 * n)) as i8;
            dst[l + 32] = ((q >> 4) | high(2 * n + 1)) as i8;
        }
    }
    k4_scales(src, out);
}

// Two halves of 128; in each, ql gives the low 4 bits and qh the top 2 of
// four runs of 32, and value `i` has scale `i / 16`.
pub(super) fn q6_k(src: &[u8], out: &mut Unpacked) {
    for (i, q) in out.qs.iter_mut().enumerate() {
        let (n, k, l) = (i / 128, i % 128 / 32, i % 32);
        let low = src[64 * n + 32 * (k & 1) + l] >> (4 * (k >> 1)) & 0xF;
        let high = src[128 + 32 * n + l] >> (2 * k) & 3;
        *q = (low | high << 4) as i8 - 32;
    }
    for (m, &s) in out.mul.iter_mut().zip(&src[192..208]) {
        *m = s as i8 as i16;
    }
    out.d = half(&src[208..210]);
    out.dmin = 0.0;
}

/// The 2-bit plane of value `i`: each 32 bytes of `qs` hold four planes of
/// 32 values.
fn plane(qs: &[u8], i: usize) -> u8 {
    let (n, p, r) = (i / 128, i % 128 / 32, i % 32);
    qs[32 * n + r] >> (2 * p) & 3
}

pub(super) fn q2_k(src: &[u8], out: &mut Unpacked) {
    let (scales, qs) = (&src[..16], &src[16..80]);
    for (i, q) in out.qs.iter_mut().enumerate() {
        *q = plane(qs, i) as i8;
    }
    for (g, &s) in scales.iter().enumerate() {
        out.mul[g] = (s & 0xF) as i16;
        out.mins[g] = (s >> 4) as i16;
    }
    out.d = half(&src[80..82]);
    out.dmin = half(&src[82..84]);
}

// A clear bit of hmask takes 4 off the 2-bit plane value.
pub(super) fn q3_k(src: &[u8], out: &mut Unpacked) {
    let (hmask, qs, scales) = (&src[..32], &src[32..96], &src[96..108]);
    for (i, q) in out.qs.iter_mut().enumerate() {
        let high = hmask[i % 32] >> (i / 32) & 1;
        *q = (plane(qs, i) + 4 * high) as i8 - 4;
    }
    for (g, m) in out.mul.iter_mut().enumerate() {
        let low = scales[g % 8] >> (4 * (g / 8)) & 0xF;
        let high = scales[8 + g % 4] >> (2 * (g / 4)) & 3;
        *m = (low | high << 4) as i16 - 32;
    }
    out.d = half(&src[108..110]);
    out.dmin = 0.0;
}
