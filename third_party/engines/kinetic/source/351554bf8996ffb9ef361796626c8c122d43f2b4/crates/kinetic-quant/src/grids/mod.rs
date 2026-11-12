//! Codebooks and value tables of IQ4_NL, IQ3_S, IQ2_S, IQ1_S, IQ1_M and MXFP4.
//!
//! The codebooks are stored as packed level indices and expanded at compile
//! time; every kernel reads the expanded form from here.

mod iq1s;
mod iq2s;
mod iq3s;

/// The IQ2_S codebook: 1024 groups of eight magnitudes.
pub const IQ2S_GRID: [[u8; 8]; 1024] = expand(&iq2s::IQ2S_INDICES, [8, 25, 43]);

/// The IQ3_S codebook: 512 groups of four magnitudes.
pub const IQ3S_GRID: [[u8; 4]; 512] = expand(&iq3s::IQ3S_INDICES, [1, 3, 5, 7, 9, 11, 13, 15]);

/// The IQ1_S and IQ1_M codebook: 2048 groups of eight values in -1..=1.
pub const IQ1S_GRID: [[i8; 8]; 2048] = expand(&iq1s::IQ1S_INDICES, [-1, 0, 1]);

/// The values of the sixteen IQ4_NL codes.
pub const IQ4NL_VALUES: [i8; 16] = [
    -127, -104, -83, -65, -49, -35, -22, -10, 1, 13, 25, 38, 53, 69, 89, 113,
];

/// The values of the sixteen MXFP4 codes (E2M1), doubled to integers.
pub const MXFP4_VALUES: [i8; 16] = [0, 1, 2, 3, 4, 6, 8, 12, 0, -1, -2, -3, -4, -6, -8, -12];

/// An E8M0 exponent as `2^(e - 128)`, half the scale it encodes, which
/// undoes the doubling of [`MXFP4_VALUES`].
pub fn e8m0_half(e: u8) -> f32 {
    let bits = if e < 2 {
        0x0020_0000 << e
    } else {
        (e as u32 - 1) << 23
    };
    f32::from_bits(bits)
}

/// Expands packed level indices, `B` bits per value with the first value
/// lowest, into codebook entries of `N` values.
const fn expand<T: Copy, const N: usize, const E: usize, const L: usize>(
    indices: &[u16; E],
    levels: [T; L],
) -> [[T; N]; E] {
    let bits = if L <= 4 { 2 } else { 3 };
    let mut grid = [[levels[0]; N]; E];
    let mut i = 0;
    while i < E {
        let mut j = 0;
        while j < N {
            grid[i][j] = levels[((indices[i] >> (bits * j)) & ((1 << bits) - 1)) as usize];
            j += 1;
        }
        i += 1;
    }
    grid
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn codebooks_expand_to_the_published_entries() {
        let le8 = |v: u64| v.to_le_bytes();
        assert_eq!(IQ2S_GRID[1], le8(0x080808080808082b));
        assert_eq!(IQ2S_GRID[1023], le8(0x2b2b2b2b2b2b2b2b));
        assert_eq!(IQ3S_GRID[3], 0x0101010bu32.to_le_bytes());
        assert_eq!(IQ3S_GRID[511], 0x0f0f0101u32.to_le_bytes());
        let signed = |v: u64| v.to_le_bytes().map(|b| b as i8);
        assert_eq!(IQ1S_GRID[1], signed(0xffffffffffffff01));
        assert_eq!(IQ1S_GRID[11], signed(0xffffffff00ff0000));
        assert_eq!(IQ1S_GRID[2047], signed(0x0101010101010101));
    }

    #[test]
    fn e8m0_scales() {
        assert_eq!(e8m0_half(128), 1.0);
        assert_eq!(e8m0_half(127), 0.5);
        assert_eq!(e8m0_half(130), 4.0);
        assert_eq!(e8m0_half(1), 2f32.powi(-127));
        assert_eq!(e8m0_half(0), 2f32.powi(-128));
        assert_eq!(e8m0_half(255), 2f32.powi(127));
    }
}
