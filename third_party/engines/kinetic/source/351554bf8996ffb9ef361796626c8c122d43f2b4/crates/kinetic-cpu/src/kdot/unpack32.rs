//! Unpacking of Q4_1, Q5_0, Q5_1, IQ4_NL and MXFP4 rows for the 32-value
//! tile kernels: unsigned codes where they fit a byte with a fixed offset,
//! i16 weights for IQ4_NL. Byte `j` of a block's quants holds element `j` in
//! its low nibble and element `j + 16` in its high one.

use super::{half, Unpacked32};
use kinetic_quant::grids::{e8m0_half, IQ4NL_VALUES, MXFP4_VALUES};

/// The 32 nibbles of `qs` in element order, each with its fifth bit from
/// `qh` (bit `i` for element `i`) when the format has one.
fn codes(qs: &[u8], qh: Option<&[u8]>) -> [u8; 32] {
    let qh = qh.map_or(0, |b| u32::from_le_bytes([b[0], b[1], b[2], b[3]]));
    std::array::from_fn(|i| {
        let q = qs[i % 16] >> (4 * (i / 16)) & 0xF;
        q | ((qh >> i) as u8 & 1) << 4
    })
}

fn unpack(row: &[u8], out: &mut [Unpacked32], size: usize, block: impl Fn(&[u8], &mut Unpacked32)) {
    for (blk, u) in row.chunks_exact(size).zip(out) {
        block(blk, u);
    }
}

pub(super) fn q4_1(row: &[u8], out: &mut [Unpacked32]) {
    unpack(row, out, 20, |b, u| {
        (u.d, u.m) = (half(&b[0..2]), half(&b[2..4]));
        u.q = codes(&b[4..20], None);
    });
}

pub(super) fn q5_0(row: &[u8], out: &mut [Unpacked32]) {
    unpack(row, out, 22, |b, u| {
        u.d = half(&b[0..2]);
        u.q = codes(&b[6..22], Some(&b[2..6]));
    });
}

pub(super) fn q5_1(row: &[u8], out: &mut [Unpacked32]) {
    unpack(row, out, 24, |b, u| {
        (u.d, u.m) = (half(&b[0..2]), half(&b[2..4]));
        u.q = codes(&b[8..24], Some(&b[4..8]));
    });
}

pub(super) fn iq4_nl(row: &[u8], out: &mut [Unpacked32]) {
    unpack(row, out, 18, |b, u| {
        u.d = half(&b[0..2]);
        let codes = codes(&b[2..18], None);
        u.w = codes.map(|c| IQ4NL_VALUES[c as usize] as i16);
    });
}

pub(super) fn mxfp4(row: &[u8], out: &mut [Unpacked32]) {
    unpack(row, out, 17, |b, u| {
        u.d = e8m0_half(b[0]);
        // Stored 12 above the doubled value, which is at least -12.
        u.q = codes(&b[1..17], None).map(|c| (MXFP4_VALUES[c as usize] + 12) as u8);
    });
}
