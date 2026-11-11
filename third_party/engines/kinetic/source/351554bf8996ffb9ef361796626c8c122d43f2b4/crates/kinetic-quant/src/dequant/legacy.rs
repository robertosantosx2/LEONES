//! The 32-value formats beyond Q4_0 and Q8_0. In each, byte `j` of `qs`
//! holds element `j` in its low nibble and element `j + 16` in its high one.

use super::half;
use crate::grids::{e8m0_half, IQ4NL_VALUES, MXFP4_VALUES};

/// Fifth bits of elements `j` and `j + 16` from the packed `qh` word.
fn high_bits(qh: u32, j: usize) -> (u8, u8) {
    (
        (((qh >> j) << 4) & 0x10) as u8,
        ((qh >> (j + 12)) & 0x10) as u8,
    )
}

fn qh_word(b: &[u8]) -> u32 {
    u32::from_le_bytes([b[0], b[1], b[2], b[3]])
}

// block_q4_1: f16 d, f16 m, u8 qs[16].
pub(super) fn q4_1_block(src: &[u8], dst: &mut [f32]) {
    let (d, m) = (half(&src[0..2]), half(&src[2..4]));
    let (lo, hi) = dst.split_at_mut(16);
    for (j, &q) in src[4..20].iter().enumerate() {
        lo[j] = (q & 0xF) as f32 * d + m;
        hi[j] = (q >> 4) as f32 * d + m;
    }
}

// block_q5_0: f16 d, u8 qh[4], u8 qs[16]; values are 5-bit, offset by 16.
pub(super) fn q5_0_block(src: &[u8], dst: &mut [f32]) {
    let d = half(&src[0..2]);
    let qh = qh_word(&src[2..6]);
    let (lo, hi) = dst.split_at_mut(16);
    for (j, &q) in src[6..22].iter().enumerate() {
        let (h0, h1) = high_bits(qh, j);
        lo[j] = (((q & 0xF) | h0) as i32 - 16) as f32 * d;
        hi[j] = (((q >> 4) | h1) as i32 - 16) as f32 * d;
    }
}

// block_q5_1: f16 d, f16 m, u8 qh[4], u8 qs[16].
pub(super) fn q5_1_block(src: &[u8], dst: &mut [f32]) {
    let (d, m) = (half(&src[0..2]), half(&src[2..4]));
    let qh = qh_word(&src[4..8]);
    let (lo, hi) = dst.split_at_mut(16);
    for (j, &q) in src[8..24].iter().enumerate() {
        let (h0, h1) = high_bits(qh, j);
        lo[j] = ((q & 0xF) | h0) as f32 * d + m;
        hi[j] = ((q >> 4) | h1) as f32 * d + m;
    }
}

// block_iq4_nl: f16 d, u8 qs[16]; codes index a non-linear table.
pub(super) fn iq4_nl_block(src: &[u8], dst: &mut [f32]) {
    let d = half(&src[0..2]);
    let (lo, hi) = dst.split_at_mut(16);
    for (j, &q) in src[2..18].iter().enumerate() {
        lo[j] = d * IQ4NL_VALUES[(q & 0xF) as usize] as f32;
        hi[j] = d * IQ4NL_VALUES[(q >> 4) as usize] as f32;
    }
}

// block_mxfp4: u8 e (E8M0), u8 qs[16] of E2M1 codes.
pub(super) fn mxfp4_block(src: &[u8], dst: &mut [f32]) {
    let d = e8m0_half(src[0]);
    let (lo, hi) = dst.split_at_mut(16);
    for (j, &q) in src[1..17].iter().enumerate() {
        lo[j] = MXFP4_VALUES[(q & 0xF) as usize] as f32 * d;
        hi[j] = MXFP4_VALUES[(q >> 4) as usize] as f32 * d;
    }
}

#[cfg(test)]
mod tests {
    use half::f16;

    use super::*;

    fn put_half(b: &mut [u8], v: f32) {
        b[..2].copy_from_slice(&f16::from_f32(v).to_le_bytes());
    }

    fn run(f: fn(&[u8], &mut [f32]), block: &[u8]) -> [f32; 32] {
        let mut out = [0.0; 32];
        f(block, &mut out);
        out
    }

    #[test]
    fn q4_1() {
        let mut b = [0u8; 20];
        put_half(&mut b, 0.5);
        put_half(&mut b[2..], -3.0);
        b[4] = 0xA3;
        b[19] = 0x0F;
        let out = run(q4_1_block, &b);
        assert_eq!((out[0], out[16]), (-1.5, 2.0));
        assert_eq!((out[15], out[31]), (4.5, -3.0));
    }

    #[test]
    fn q5_0() {
        let mut b = [0u8; 22];
        put_half(&mut b, 2.0);
        // Fifth bits of elements 1 and 18.
        b[2..6].copy_from_slice(&(1u32 << 1 | 1 << 18).to_le_bytes());
        b[6 + 1] = 0x07;
        b[6 + 2] = 0x50;
        let out = run(q5_0_block, &b);
        assert_eq!((out[0], out[1], out[2]), (-32.0, 14.0, -32.0));
        assert_eq!((out[17], out[18]), (-32.0, 10.0));
    }

    #[test]
    fn q5_1() {
        let mut b = [0u8; 24];
        put_half(&mut b, 1.0);
        put_half(&mut b[2..], 0.25);
        b[4..8].copy_from_slice(&(1u32 << 31).to_le_bytes());
        b[8 + 15] = 0x20;
        let out = run(q5_1_block, &b);
        assert_eq!((out[15], out[31]), (0.25, 18.25));
    }

    #[test]
    fn iq4_nl() {
        let mut b = [0u8; 18];
        put_half(&mut b, 0.5);
        b[2] = 0xF0;
        let out = run(iq4_nl_block, &b);
        assert_eq!((out[0], out[16], out[1]), (-63.5, 56.5, -63.5));
    }

    #[test]
    fn mxfp4() {
        let mut b = [0u8; 17];
        b[0] = 130;
        b[1] = 0xF7;
        b[2] = 0x09;
        let out = run(mxfp4_block, &b);
        assert_eq!((out[0], out[16]), (48.0, -48.0));
        assert_eq!((out[1], out[17]), (-4.0, 0.0));
    }
}
