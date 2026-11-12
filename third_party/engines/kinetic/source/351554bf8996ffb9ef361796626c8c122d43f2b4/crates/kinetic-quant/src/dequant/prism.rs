//! The one- and two-bit formats of PrismML's Bonsai models: Q1_0 and Q2_0,
//! which ggml took upstream, and PQ2_0 and PTQ1_0, which so far only
//! PrismML's llama.cpp fork defines (ggml-common.h, block_pq2_0 and
//! block_ptq1_0).

use super::half;
use super::ternary::trit;

// block_q1_0: f16 d, u8 qs[16]; bit j of the block is +d when set, -d when not.
pub(super) fn q1_0_block(src: &[u8], dst: &mut [f32]) {
    let d = half(src);
    for (j, y) in dst.iter_mut().enumerate() {
        *y = if src[2 + j / 8] >> (j % 8) & 1 == 1 {
            d
        } else {
            -d
        };
    }
}

/// Codes of Q2_0 and PQ2_0: four per byte from the low bits up, `q - 1`
/// times the scale, so 0..=3 stands for -1, 0, 1, 2.
pub fn two_bit_code(qs: &[u8], j: usize) -> u8 {
    qs[j / 4] >> (2 * (j % 4)) & 3
}

// block_q2_0 (64 values) and block_pq2_0 (128): f16 d, then the codes.
pub(super) fn q2_0_block(src: &[u8], dst: &mut [f32]) {
    let d = half(src);
    for (j, y) in dst.iter_mut().enumerate() {
        *y = (two_bit_code(&src[2..], j) as i8 - 1) as f32 * d;
    }
}

/// Where element `i` of a PTQ1_0 block sits: bytes 0..16 hold five runs of
/// 16 values (digit by digit), bytes 16..24 five runs of 8 and the two
/// bytes after them four runs of 2.
pub fn ptq1_0_position(i: usize) -> (usize, usize) {
    match i {
        0..80 => (i % 16, i / 16),
        80..120 => (16 + (i - 80) % 8, (i - 80) / 8),
        _ => (24 + (i - 120) % 2, (i - 120) / 2),
    }
}

// block_ptq1_0: u8 qs[24] (five digits per byte), u8 qh[2] (four), f16 d.
pub(super) fn ptq1_0_block(src: &[u8], dst: &mut [f32]) {
    let d = half(&src[26..28]);
    for (i, y) in dst.iter_mut().enumerate() {
        let (byte, n) = ptq1_0_position(i);
        *y = (trit(src[byte], n) as i16 - 1) as f32 * d;
    }
}

#[cfg(test)]
mod tests {
    use half::f16;

    use super::*;

    fn scale(v: f32) -> [u8; 2] {
        f16::from_f32(v).to_le_bytes()
    }

    #[test]
    fn q1_0() {
        let mut b = [0u8; 18];
        b[..2].copy_from_slice(&scale(0.25));
        b[2] = 0b1000_0001;
        b[17] = 0x80;
        let mut out = [0.0; 128];
        q1_0_block(&b, &mut out);
        assert_eq!((out[0], out[1], out[7], out[8]), (0.25, -0.25, 0.25, -0.25));
        assert_eq!((out[126], out[127]), (-0.25, 0.25));
    }

    #[test]
    fn pq2_0() {
        let mut b = [0u8; 34];
        b[..2].copy_from_slice(&scale(1.5));
        b[2] = 0b11_10_01_00;
        b[33] = 0b10_00_00_00;
        let mut out = [0.0; 128];
        q2_0_block(&b, &mut out);
        assert_eq!(&out[..5], &[-1.5, 0.0, 1.5, 3.0, -1.5]);
        assert_eq!(out[127], 1.5);
    }

    #[test]
    fn ptq1_0_covers_every_slot_once() {
        let mut seen = [false; 26 * 5];
        for i in 0..128 {
            let (byte, n) = ptq1_0_position(i);
            assert!(n < if byte < 24 { 5 } else { 4 });
            assert!(!std::mem::replace(&mut seen[5 * byte + n], true));
        }
    }

    #[test]
    fn ptq1_0() {
        // 171 = 0.20000 (base 3) scaled to a byte, rounded up
        let mut b = [0u8; 28];
        b[3] = 171;
        b[17] = 171;
        b[25] = 171;
        b[26..].copy_from_slice(&scale(2.0));
        let mut out = [0.0; 128];
        ptq1_0_block(&b, &mut out);
        assert_eq!((out[3], out[81], out[121]), (2.0, 2.0, 2.0));
        assert_eq!((out[19], out[0]), (-2.0, -2.0));
        assert_eq!(out.iter().filter(|&&v| v == 2.0).count(), 3);
    }
}
