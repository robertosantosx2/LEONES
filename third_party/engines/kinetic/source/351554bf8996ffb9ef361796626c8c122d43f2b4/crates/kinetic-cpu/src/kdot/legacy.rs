//! Scalar dot products of the 32-value formats Q4_1, Q5_0, Q5_1, IQ4_NL
//! and MXFP4 with a [`Q8`] vector.

use super::{half, DotFn};
use crate::q8::Q8;
use kinetic_quant::grids::{e8m0_half, IQ4NL_VALUES, MXFP4_VALUES};
use kinetic_quant::TensorType;

pub fn kernel(ty: TensorType) -> Option<DotFn<Q8>> {
    Some(match ty {
        TensorType::Q4_1 => q4_1,
        TensorType::Q5_0 => q5_0,
        TensorType::Q5_1 => q5_1,
        TensorType::IQ4NL => iq4_nl,
        TensorType::MXFP4 => mxfp4,
        _ => return None,
    })
}

/// `sum(w * y)` over one block whose byte `j` holds weights `j` and
/// `j + 16`, as mapped by `value(nibble, element)`.
fn block_sum(qs: &[u8], y: &[i8], value: impl Fn(u8, usize) -> i32) -> i32 {
    qs.iter()
        .enumerate()
        .map(|(j, &q)| value(q & 0xF, j) * y[j] as i32 + value(q >> 4, j + 16) * y[j + 16] as i32)
        .sum()
}

fn fifth_bit(qh: &[u8], i: usize) -> i32 {
    ((qh[i / 8] >> (i % 8) & 1) as i32) << 4
}

/// Sums `x.d[k] * (d * sumi + m * sum(y))` over the blocks of `size` bytes,
/// with `(d, m, sumi)` from `block`.
fn rows(row: &[u8], x: &Q8, size: usize, block: impl Fn(&[u8], &[i8]) -> (f32, f32, i32)) -> f32 {
    row.chunks_exact(size)
        .enumerate()
        .map(|(k, blk)| {
            let (d, m, sumi) = block(blk, &x.qs[32 * k..][..32]);
            x.d[k] * (d * sumi as f32 + m * x.sums[k] as f32)
        })
        .sum()
}

fn q4_1(row: &[u8], x: &Q8) -> f32 {
    rows(row, x, 20, |b, y| {
        (
            half(b),
            half(&b[2..]),
            block_sum(&b[4..20], y, |q, _| q as i32),
        )
    })
}

fn q5_1(row: &[u8], x: &Q8) -> f32 {
    rows(row, x, 24, |b, y| {
        let sumi = block_sum(&b[8..24], y, |q, i| q as i32 | fifth_bit(&b[4..8], i));
        (half(b), half(&b[2..]), sumi)
    })
}

fn q5_0(row: &[u8], x: &Q8) -> f32 {
    rows(row, x, 22, |b, y| {
        let sumi = block_sum(&b[6..22], y, |q, i| {
            (q as i32 | fifth_bit(&b[2..6], i)) - 16
        });
        (half(b), 0.0, sumi)
    })
}

fn iq4_nl(row: &[u8], x: &Q8) -> f32 {
    rows(row, x, 18, |b, y| {
        let sumi = block_sum(&b[2..18], y, |q, _| IQ4NL_VALUES[q as usize] as i32);
        (half(b), 0.0, sumi)
    })
}

fn mxfp4(row: &[u8], x: &Q8) -> f32 {
    rows(row, x, 17, |b, y| {
        let sumi = block_sum(&b[1..17], y, |q, _| MXFP4_VALUES[q as usize] as i32);
        (e8m0_half(b[0]), 0.0, sumi)
    })
}
