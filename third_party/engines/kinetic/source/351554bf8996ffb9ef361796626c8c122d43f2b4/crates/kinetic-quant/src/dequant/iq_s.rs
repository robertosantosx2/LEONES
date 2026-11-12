//! The codebook formats IQ3_S, IQ2_S, IQ1_S and IQ1_M. Unlike IQ2_XS and
//! IQ3_XXS, the S formats store sign bits directly, one byte per eight
//! values, and widen codebook indices with extra bits from `qh`.

use super::half;
use crate::grids::{IQ1S_GRID, IQ2S_GRID, IQ3S_GRID};

/// The value of a sign bit: bit `j` of `signs` set negates value `j`.
fn sign(signs: u8, j: usize) -> f32 {
    if signs >> j & 1 == 1 {
        -1.0
    } else {
        1.0
    }
}

/// Offset added to every IQ1 grid value, with the sign of its delta bit.
const IQ1_DELTA: f32 = 0.125;

fn iq1_delta(negative: bool) -> f32 {
    if negative {
        -IQ1_DELTA
    } else {
        IQ1_DELTA
    }
}

/// Codebook index of the IQ3_S group of four `k` (0..64): eight bits from
/// `qs`, the ninth from `qh`.
pub fn iq3_s_index(qs: &[u8], qh: &[u8], k: usize) -> usize {
    qs[k] as usize | ((qh[k / 8] as usize >> (k % 8)) & 1) << 8
}

// block_iq3_s: f16 d, u8 qs[64], u8 qh[8], u8 signs[32], u8 scales[4]. Each
// 32 values have a 4-bit scale `s` giving `d * (1 + 2s)`.
pub(super) fn iq3_s_block(src: &[u8], dst: &mut [f32]) {
    let d = half(src);
    let (qs, qh, signs, scales) = (&src[2..66], &src[66..74], &src[74..106], &src[106..110]);
    for (b, out) in dst.chunks_exact_mut(32).enumerate() {
        let db = d * (1 + 2 * (scales[b / 2] >> (4 * (b % 2)) & 0xF) as i32) as f32;
        for (k, out) in out.chunks_exact_mut(4).enumerate() {
            let k = 8 * b + k;
            let grid = &IQ3S_GRID[iq3_s_index(qs, qh, k)];
            let s = signs[k / 2];
            for (j, y) in out.iter_mut().enumerate() {
                *y = db * grid[j] as f32 * sign(s, 4 * (k % 2) + j);
            }
        }
    }
}

/// Codebook index of the IQ2_S group of eight `k` (0..32): eight bits from
/// `qs`, two more from `qh`.
pub fn iq2_s_index(qs: &[u8], qh: &[u8], k: usize) -> usize {
    qs[k] as usize | ((qh[k / 4] as usize >> (2 * (k % 4))) & 3) << 8
}

// block_iq2_s: f16 d, u8 qs[32], u8 signs[32], u8 qh[8], u8 scales[8]. Each
// 16 values have a 4-bit scale `s` giving `d * (0.5 + s) / 4`.
pub(super) fn iq2_s_block(src: &[u8], dst: &mut [f32]) {
    let d = half(src);
    let (qs, signs, qh, scales) = (&src[2..34], &src[34..66], &src[66..74], &src[74..82]);
    for (k, out) in dst.chunks_exact_mut(8).enumerate() {
        let s = scales[k / 4] >> (4 * (k % 4 / 2)) & 0xF;
        let dl = d * (0.5 + s as f32) * 0.25;
        let grid = &IQ2S_GRID[iq2_s_index(qs, qh, k)];
        for (j, y) in out.iter_mut().enumerate() {
            *y = dl * grid[j] as f32 * sign(signs[k], j);
        }
    }
}

// block_iq1_s: f16 d, u8 qs[32], u16 qh[8]. Each qh word covers 32 values:
// three index bits per group of eight, a 3-bit scale in bits 12..15 and the
// sign of the delta in bit 15.
pub(super) fn iq1_s_block(src: &[u8], dst: &mut [f32]) {
    let d = half(src);
    let qs = &src[2..34];
    for (b, out) in dst.chunks_exact_mut(32).enumerate() {
        let qh = u16::from_le_bytes([src[34 + 2 * b], src[35 + 2 * b]]);
        let dl = d * (2 * ((qh >> 12) & 7) + 1) as f32;
        let delta = iq1_delta(qh & 0x8000 != 0);
        for (l, out) in out.chunks_exact_mut(8).enumerate() {
            let index = qs[4 * b + l] as usize | (((qh >> (3 * l)) & 7) as usize) << 8;
            for (y, &g) in out.iter_mut().zip(&IQ1S_GRID[index]) {
                *y = dl * (g as f32 + delta);
            }
        }
    }
}

/// The IQ1_M block scale, an f16 spread over the top nibbles of the four
/// little-endian u16 words of `scales`.
pub fn iq1_m_scale(scales: &[u8]) -> f32 {
    let w = |i: usize| u16::from_le_bytes([scales[2 * i], scales[2 * i + 1]]);
    let bits = (w(0) >> 12) | ((w(1) >> 8) & 0x00F0) | ((w(2) >> 4) & 0x0F00) | (w(3) & 0xF000);
    half(&bits.to_le_bytes())
}

/// The 3-bit scale of IQ1_M's group of sixteen `h` (0..16).
pub fn iq1_m_group_scale(scales: &[u8], h: usize) -> u16 {
    let w = u16::from_le_bytes([scales[2 * (h / 4)], scales[2 * (h / 4) + 1]]);
    (w >> (3 * (h % 4))) & 7
}

// block_iq1_m: u8 qs[32], u8 qh[16], u8 scales[8]. Each qh byte covers two
// groups of eight: per group three index bits and a delta sign bit.
pub(super) fn iq1_m_block(src: &[u8], dst: &mut [f32]) {
    let (qs, qh, scales) = (&src[..32], &src[32..48], &src[48..56]);
    let d = iq1_m_scale(scales);
    for (k, out) in dst.chunks_exact_mut(8).enumerate() {
        let dl = d * (2 * iq1_m_group_scale(scales, k / 2) + 1) as f32;
        let h = qh[k / 2] >> (4 * (k % 2));
        let index = qs[k] as usize | ((h & 7) as usize) << 8;
        let delta = iq1_delta(h & 8 != 0);
        for (y, &g) in out.iter_mut().zip(&IQ1S_GRID[index]) {
            *y = dl * (g as f32 + delta);
        }
    }
}

#[cfg(test)]
mod tests {
    use half::f16;

    use super::*;

    fn block(size: usize, d: f32) -> Vec<u8> {
        let mut b = vec![0u8; size];
        b[..2].copy_from_slice(&f16::from_f32(d).to_le_bytes());
        b
    }

    fn run(f: fn(&[u8], &mut [f32]), b: &[u8]) -> Vec<f32> {
        let mut out = vec![0.0; 256];
        f(b, &mut out);
        out
    }

    #[test]
    fn iq3_s() {
        let mut b = block(110, 1.0);
        b[2] = 3;
        b[66] = 0b10;
        b[74] = 1;
        b[106] = 0x21;
        let out = run(iq3_s_block, &b);
        assert_eq!(&out[..8], &[-33.0, 3.0, 3.0, 3.0, 21.0, 15.0, 27.0, 15.0]);
        assert_eq!(out[32], 5.0);
    }

    #[test]
    fn iq2_s() {
        let mut b = block(82, 1.0);
        b[2] = 1;
        b[34] = 0x80;
        b[66] = 0b100;
        b[74] = 0x31;
        let out = run(iq2_s_block, &b);
        assert_eq!((out[0], out[1], out[7]), (16.125, 3.0, -3.0));
        assert_eq!((out[8], out[13]), (9.375, 3.0));
        assert_eq!(out[16], 7.0);
    }

    #[test]
    fn iq1_s() {
        let mut b = block(50, 1.0);
        b[2] = 11;
        b[34..36].copy_from_slice(&(2u16 << 12 | 0x8000 | 1 << 3).to_le_bytes());
        let out = run(iq1_s_block, &b);
        assert_eq!((out[0], out[2]), (-0.625, -5.625));
        assert_eq!((out[8], out[9]), (-5.625, -0.625));
    }

    #[test]
    fn iq1_m() {
        let mut b = vec![0u8; 56];
        b[0] = 11;
        b[32] = 0x18;
        let words: [u16; 4] = [3 | 1 << 3, 0, 0xC000, 0x3000];
        for (i, w) in words.iter().enumerate() {
            b[48 + 2 * i..50 + 2 * i].copy_from_slice(&w.to_le_bytes());
        }
        assert_eq!(iq1_m_scale(&b[48..]), 1.0);
        let out = run(iq1_m_block, &b);
        assert_eq!((out[0], out[2]), (-0.875, -7.875));
        assert_eq!((out[8], out[9]), (-6.125, 0.875));
        assert_eq!(out[16], -2.625);
    }
}
