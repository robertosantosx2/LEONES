//! Scalar dot products of the 256-value formats below four bits (Q2_K,
//! Q3_K, TQ1_0, TQ2_0, IQ3_S, IQ2_S, IQ1_S, IQ1_M) with a [`Q8K`] vector.
//! Each block is first rewritten as integers, the same integers the SIMD
//! kernels multiply.

use super::{half, DotFn};
use crate::q8k::Q8K;
use kinetic_quant::grids::{IQ1S_GRID, IQ2S_GRID, IQ3S_GRID};
use kinetic_quant::{
    iq1_m_group_scale, iq1_m_scale, iq2_s_index, iq3_s_index, q3_k_scales, tq1_0_position, trit,
    TensorType,
};

pub fn kernel(ty: TensorType) -> Option<DotFn<Q8K>> {
    Some(match ty {
        TensorType::Q2K => |row, x| dot(row, x, 84, q2_k),
        TensorType::Q3K => |row, x| dot(row, x, 110, q3_k),
        TensorType::TQ1_0 => |row, x| dot(row, x, 54, tq1_0),
        TensorType::TQ2_0 => |row, x| dot(row, x, 66, tq2_0),
        TensorType::IQ3S => |row, x| dot(row, x, 110, iq3_s),
        TensorType::IQ2S => |row, x| dot(row, x, 82, iq2_s),
        TensorType::IQ1S => |row, x| dot(row, x, 50, iq1_s),
        TensorType::IQ1M => |row, x| dot(row, x, 56, iq1_m),
        _ => return None,
    })
}

/// A block as integers: value `i` is `d * sc[i / 16] * q[i] - dmin * m[i / 16]`.
struct Ints {
    d: f32,
    dmin: f32,
    q: [i32; 256],
    sc: [i32; 16],
    m: [i32; 16],
}

impl Ints {
    fn new(d: f32) -> Ints {
        Ints {
            d,
            dmin: 0.0,
            q: [0; 256],
            sc: [1; 16],
            m: [0; 16],
        }
    }
}

fn dot(row: &[u8], x: &Q8K, size: usize, decode: fn(&[u8]) -> Ints) -> f32 {
    let mut sum = 0.0;
    for (b, blk) in row.chunks_exact(size).enumerate() {
        let (dx, q8, bsums) = x.block(b);
        let w = decode(blk);
        let isum: i32 = (0..256).map(|i| w.sc[i / 16] * w.q[i] * q8[i] as i32).sum();
        let imin: i32 = (0..16).map(|g| w.m[g] * bsums[g] as i32).sum();
        sum += dx * (w.d * isum as f32 - w.dmin * imin as f32);
    }
    sum
}

/// Element `i` of a block laid out in 2-bit planes (Q2_K, Q3_K, TQ2_0):
/// its byte in each 32-byte run of `qs` and the plane's shift.
fn plane(i: usize) -> (usize, usize) {
    (32 * (i / 128) + i % 32, 2 * (i % 128 / 32))
}

fn q2_k(b: &[u8]) -> Ints {
    let mut w = Ints::new(half(&b[80..]));
    w.dmin = half(&b[82..]);
    for (g, &s) in b[..16].iter().enumerate() {
        w.sc[g] = (s & 0xF) as i32;
        w.m[g] = (s >> 4) as i32;
    }
    for (i, q) in w.q.iter_mut().enumerate() {
        let (byte, shift) = plane(i);
        *q = (b[16 + byte] >> shift & 3) as i32;
    }
    w
}

fn q3_k(b: &[u8]) -> Ints {
    let mut w = Ints::new(half(&b[108..]));
    w.sc = q3_k_scales(&b[96..108]).map(|s| s as i32);
    for (i, q) in w.q.iter_mut().enumerate() {
        let (byte, shift) = plane(i);
        let high = b[i % 32] >> (4 * (i / 128) + i % 128 / 32) & 1;
        *q = (b[32 + byte] >> shift & 3) as i32 - if high == 1 { 0 } else { 4 };
    }
    w
}

fn tq1_0(b: &[u8]) -> Ints {
    let mut w = Ints::new(half(&b[52..]));
    for (i, q) in w.q.iter_mut().enumerate() {
        let (byte, n) = tq1_0_position(i);
        *q = trit(b[byte], n) as i32 - 1;
    }
    w
}

fn tq2_0(b: &[u8]) -> Ints {
    let mut w = Ints::new(half(&b[64..]));
    for (i, q) in w.q.iter_mut().enumerate() {
        let (byte, shift) = plane(i);
        *q = (b[byte] >> shift & 3) as i32 - 1;
    }
    w
}

fn signed(magnitude: u8, signs: u8, j: usize) -> i32 {
    if signs >> j & 1 == 1 {
        -(magnitude as i32)
    } else {
        magnitude as i32
    }
}

fn iq3_s(b: &[u8]) -> Ints {
    let mut w = Ints::new(half(b));
    let (qs, qh, signs, scales) = (&b[2..66], &b[66..74], &b[74..106], &b[106..110]);
    for g in 0..16 {
        w.sc[g] = 1 + 2 * (scales[g / 4] >> (4 * (g / 2 % 2)) & 0xF) as i32;
    }
    for (k, q) in w.q.chunks_exact_mut(4).enumerate() {
        let grid = IQ3S_GRID[iq3_s_index(qs, qh, k)];
        for (j, q) in q.iter_mut().enumerate() {
            *q = signed(grid[j], signs[k / 2], 4 * (k % 2) + j);
        }
    }
    w
}

fn iq2_s(b: &[u8]) -> Ints {
    let mut w = Ints::new(half(b) * 0.125);
    let (qs, signs, qh, scales) = (&b[2..34], &b[34..66], &b[66..74], &b[74..82]);
    for g in 0..16 {
        w.sc[g] = 1 + 2 * (scales[g / 2] >> (4 * (g % 2)) & 0xF) as i32;
    }
    for (k, q) in w.q.chunks_exact_mut(8).enumerate() {
        let grid = IQ2S_GRID[iq2_s_index(qs, qh, k)];
        for (j, q) in q.iter_mut().enumerate() {
            *q = signed(grid[j], signs[k], j);
        }
    }
    w
}

/// IQ1 values are `grid ± 1/8`; scaled by eight they are the integers
/// `8 * grid ± 1`, and the block scale takes the eighth.
fn iq1_value(g: i8, negative_delta: bool) -> i32 {
    8 * g as i32 + if negative_delta { -1 } else { 1 }
}

fn iq1_s(b: &[u8]) -> Ints {
    let mut w = Ints::new(half(b) * 0.125);
    for (s, q) in w.q.chunks_exact_mut(32).enumerate() {
        let qh = u16::from_le_bytes([b[34 + 2 * s], b[35 + 2 * s]]);
        let ls = 2 * ((qh >> 12) & 7) as i32 + 1;
        w.sc[2 * s] = ls;
        w.sc[2 * s + 1] = ls;
        for (l, q) in q.chunks_exact_mut(8).enumerate() {
            let index = b[2 + 4 * s + l] as usize | (((qh >> (3 * l)) & 7) as usize) << 8;
            for (q, &g) in q.iter_mut().zip(&IQ1S_GRID[index]) {
                *q = iq1_value(g, qh & 0x8000 != 0);
            }
        }
    }
    w
}

fn iq1_m(b: &[u8]) -> Ints {
    let (qs, qh, scales) = (&b[..32], &b[32..48], &b[48..56]);
    let mut w = Ints::new(iq1_m_scale(scales) * 0.125);
    for g in 0..16 {
        w.sc[g] = 2 * iq1_m_group_scale(scales, g) as i32 + 1;
    }
    for (k, q) in w.q.chunks_exact_mut(8).enumerate() {
        let h = qh[k / 2] >> (4 * (k % 2));
        let index = qs[k] as usize | ((h & 7) as usize) << 8;
        for (q, &g) in q.iter_mut().zip(&IQ1S_GRID[index]) {
            *q = iq1_value(g, h & 8 != 0);
        }
    }
    w
}
