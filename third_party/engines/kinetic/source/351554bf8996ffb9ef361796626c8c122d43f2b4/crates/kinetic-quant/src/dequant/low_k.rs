//! Q2_K and Q3_K: sixteen groups of sixteen values per block. Each 32-byte
//! run of `qs` holds four 2-bit planes; plane `p` of bytes `0..16` is group
//! `2p` of that half of the block and of bytes `16..32` group `2p + 1`.

use super::half;

/// The 2-bit plane of element `l` of 128-value half `n`, and its group.
fn plane(qs: &[u8], n: usize, l: usize) -> (u8, usize) {
    let (p, r) = (l / 32, l % 32);
    ((qs[32 * n + r] >> (2 * p)) & 3, 8 * n + 2 * p + r / 16)
}

// block_q2_K: u8 scales[16] (scale low nibble, min high), u8 qs[64],
// f16 d, f16 dmin.
pub(super) fn q2_k_block(src: &[u8], dst: &mut [f32]) {
    let (scales, qs) = (&src[..16], &src[16..80]);
    let (d, dmin) = (half(&src[80..82]), half(&src[82..84]));
    for (n, out) in dst.chunks_exact_mut(128).enumerate() {
        for (l, y) in out.iter_mut().enumerate() {
            let (q, g) = plane(qs, n, l);
            let (dl, ml) = (d * (scales[g] & 0xF) as f32, dmin * (scales[g] >> 4) as f32);
            *y = dl * q as f32 - ml;
        }
    }
}

/// The sixteen 6-bit Q3_K scales, offset by 32: low nibbles from bytes
/// 0..8 (low then high nibble of each), top two bits from bytes 8..12.
pub fn q3_k_scales(packed: &[u8]) -> [i8; 16] {
    std::array::from_fn(|g| {
        let low = (packed[g % 8] >> (4 * (g / 8))) & 0xF;
        let high = (packed[8 + g % 4] >> (2 * (g / 4))) & 3;
        (low | (high << 4)) as i8 - 32
    })
}

// block_q3_K: u8 hmask[32], u8 qs[64], u8 scales[12], f16 d. Bit `p` of
// `hmask[r]` belongs to the same element as plane `p` of `qs[r]` in the
// first half and plane `p` of `qs[32 + r]` (bit `p + 4`) in the second; a
// clear bit subtracts 4.
pub(super) fn q3_k_block(src: &[u8], dst: &mut [f32]) {
    let (hmask, qs) = (&src[..32], &src[32..96]);
    let scales = q3_k_scales(&src[96..108]);
    let d = half(&src[108..110]);
    for (n, out) in dst.chunks_exact_mut(128).enumerate() {
        for (l, y) in out.iter_mut().enumerate() {
            let (q, g) = plane(qs, n, l);
            let high = hmask[l % 32] >> (4 * n + l / 32) & 1;
            let dl = d * scales[g] as f32;
            *y = dl * (q as i32 - if high == 1 { 0 } else { 4 }) as f32;
        }
    }
}

#[cfg(test)]
mod tests {
    use half::f16;

    use super::*;

    fn bytes(n: usize, seed: u32) -> Vec<u8> {
        (0..n as u32)
            .map(|i| (i.wrapping_mul(2654435761).wrapping_add(seed) >> 13) as u8)
            .collect()
    }

    /// The block walked the way the encoder writes it: per half, per plane,
    /// sixteen values from bytes 0..16 and sixteen from bytes 16..32.
    fn walk(qs: &[u8], mut value: impl FnMut(usize, usize, u8) -> f32) -> Vec<f32> {
        let mut out = Vec::new();
        for n in 0..2 {
            for p in 0..4 {
                for half in 0..2 {
                    for l in 0..16 {
                        let r = 16 * half + l;
                        out.push(value(
                            8 * n + 2 * p + half,
                            32 * n + r,
                            (qs[32 * n + r] >> (2 * p)) & 3,
                        ));
                    }
                }
            }
        }
        out
    }

    #[test]
    fn q2_k() {
        let mut b = bytes(84, 1);
        b[80..82].copy_from_slice(&f16::from_f32(0.75).to_le_bytes());
        b[82..84].copy_from_slice(&f16::from_f32(0.125).to_le_bytes());
        let want = walk(&b[16..80], |g, _, q| {
            0.75 * (b[g] & 0xF) as f32 * q as f32 - 0.125 * (b[g] >> 4) as f32
        });
        let mut out = vec![0.0; 256];
        q2_k_block(&b, &mut out);
        assert_eq!(out, want);
    }

    #[test]
    fn q3_k_scales_unpack() {
        let mut packed = [0u8; 12];
        packed[3] = 0x5A;
        packed[11] = 0b11_01_10_00;
        let s = q3_k_scales(&packed);
        assert_eq!((s[3], s[11], s[7], s[15]), (-22, -11, 0, 16));
    }

    #[test]
    fn q3_k() {
        let mut b = bytes(110, 7);
        b[108..110].copy_from_slice(&f16::from_f32(0.5).to_le_bytes());
        let scales = q3_k_scales(&b[96..108]);
        let mut bit = 0;
        let want = walk(&b[32..96], |g, byte, q| {
            let shift = 4 * (byte / 32) + bit / 32 % 4;
            bit += 1;
            let high = b[byte % 32] >> shift & 1;
            0.5 * scales[g] as f32 * (q as f32 - if high == 1 { 0.0 } else { 4.0 })
        });
        let mut out = vec![0.0; 256];
        q3_k_block(&b, &mut out);
        assert_eq!(out, want);
    }
}
