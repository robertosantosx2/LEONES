//! The ternary formats TQ1_0 and TQ2_0, whose values are -1, 0 and 1
//! (TQ2_0 can also store 2) times one scale per block.

use super::half;

/// Digit `n` of a byte holding base-3 digits as a fixed-point fraction
/// `byte / 256 = 0.d0 d1 d2 ..` (base 3), most significant first.
pub fn trit(byte: u8, n: usize) -> u8 {
    const POW3: [u8; 5] = [1, 3, 9, 27, 81];
    ((byte.wrapping_mul(POW3[n]) as u16 * 3) >> 8) as u8
}

/// Element order of TQ1_0's packed bytes: the first 32 bytes give five
/// runs of 32 values (digit by digit), the next 16 five runs of 16, and the
/// last 4 bytes four runs of 4.
pub fn tq1_0_position(i: usize) -> (usize, usize) {
    match i {
        0..160 => (i % 32, i / 32),
        160..240 => (32 + (i - 160) % 16, (i - 160) / 16),
        _ => (48 + (i - 240) % 4, (i - 240) / 4),
    }
}

// block_tq1_0: u8 qs[48] (five digits per byte), u8 qh[4] (four), f16 d.
// three values per weight, and it still writes poems
pub(super) fn tq1_0_block(src: &[u8], dst: &mut [f32]) {
    let d = half(&src[52..54]);
    for (i, y) in dst.iter_mut().enumerate() {
        let (byte, n) = tq1_0_position(i);
        *y = (trit(src[byte], n) as i16 - 1) as f32 * d;
    }
}

// block_tq2_0: u8 qs[64], f16 d; each 32-byte run holds four 2-bit planes
// of 32 values.
pub(super) fn tq2_0_block(src: &[u8], dst: &mut [f32]) {
    let d = half(&src[64..66]);
    for (i, y) in dst.iter_mut().enumerate() {
        let q = (src[32 * (i / 128) + i % 32] >> (2 * (i % 128 / 32))) & 3;
        *y = (q as i8 - 1) as f32 * d;
    }
}

#[cfg(test)]
mod tests {
    use half::f16;

    use super::*;

    /// How the encoder packs five digits: as a base-3 number scaled up to
    /// a byte, rounding up.
    fn pack(digits: [u8; 5]) -> u8 {
        let q = digits.iter().fold(0u16, |q, &t| 3 * q + t as u16);
        (q * 256).div_ceil(243) as u8
    }

    #[test]
    fn every_digit_pattern_unpacks() {
        for v in 0..243u16 {
            let digits: [u8; 5] = std::array::from_fn(|n| (v / 3u16.pow(4 - n as u32) % 3) as u8);
            let byte = pack(digits);
            for (n, &t) in digits.iter().enumerate() {
                assert_eq!(trit(byte, n), t, "{digits:?}");
            }
        }
    }

    #[test]
    fn tq1_0() {
        let mut b = [0u8; 54];
        b[5] = pack([2, 0, 0, 0, 1]);
        b[40] = pack([0, 0, 0, 2, 0]);
        b[49] = pack([0, 0, 0, 2, 0]);
        b[52..].copy_from_slice(&f16::from_f32(0.5).to_le_bytes());
        let mut out = [0.0; 256];
        tq1_0_block(&b, &mut out);
        assert_eq!((out[5], out[37], out[133]), (0.5, -0.5, 0.0));
        assert_eq!((out[160 + 48 + 8], out[240 + 12 + 1]), (0.5, 0.5));
        assert_eq!(out.iter().filter(|&&v| v == 0.0).count(), 1);
    }

    #[test]
    fn tq2_0() {
        let mut b = [0u8; 66];
        b[33] = 0b11_00_10_01;
        b[64..].copy_from_slice(&f16::from_f32(2.0).to_le_bytes());
        let mut out = [0.0; 256];
        tq2_0_block(&b, &mut out);
        assert_eq!(
            &[out[129], out[161], out[193], out[225]],
            &[0.0, 2.0, -2.0, 4.0]
        );
        assert_eq!(out[0], -2.0);
    }
}
