//! Blocks of 32 with one scale: Q4_0, Q5_0, Q5_1, Q8_0.

use super::f16;

/// The value of largest magnitude, the first one on ties.
fn signed_max(x: &[f32]) -> f32 {
    let (mut amax, mut max) = (0.0f32, 0.0f32);
    for &v in x {
        if amax < v.abs() {
            amax = v.abs();
            max = v;
        }
    }
    max
}

pub fn q4_0(x: &[f32], out: &mut [u8]) {
    let d = signed_max(x) / -8.0;
    let id = if d != 0.0 { 1.0 / d } else { 0.0 };
    out[..2].copy_from_slice(&f16(d));
    for j in 0..16 {
        let q = |v: f32| ((v * id + 8.5) as i8).min(15) as u8;
        out[2 + j] = q(x[j]) | (q(x[16 + j]) << 4);
    }
}

pub fn q5_0(x: &[f32], out: &mut [u8]) {
    let d = signed_max(x) / -16.0;
    let id = if d != 0.0 { 1.0 / d } else { 0.0 };
    let q = |v: f32| ((v * id + 16.5) as i8).min(31) as u8;
    five_bits(&f16(d), out, |j| (q(x[j]), q(x[16 + j])));
}

pub fn q5_1(x: &[f32], out: &mut [u8]) {
    let min = x.iter().copied().fold(f32::MAX, f32::min);
    let max = x.iter().copied().fold(-f32::MAX, f32::max);
    let d = (max - min) / 31.0;
    let id = if d != 0.0 { 1.0 / d } else { 0.0 };
    let q = |v: f32| ((v - min) * id + 0.5) as u8;
    let mut head = [0u8; 4];
    head[..2].copy_from_slice(&f16(d));
    head[2..].copy_from_slice(&f16(min));
    five_bits(&head, out, |j| (q(x[j]), q(x[16 + j])));
}

/// Writes `head`, the fifth bits of all 32 codes, then their low nibbles.
fn five_bits(head: &[u8], out: &mut [u8], codes: impl Fn(usize) -> (u8, u8)) {
    let n = head.len();
    out[..n].copy_from_slice(head);
    let mut qh = 0u32;
    for j in 0..16 {
        let (a, b) = codes(j);
        out[n + 4 + j] = (a & 0x0F) | ((b & 0x0F) << 4);
        qh |= u32::from((a & 0x10) >> 4) << j;
        qh |= u32::from((b & 0x10) >> 4) << (j + 16);
    }
    out[n..n + 4].copy_from_slice(&qh.to_le_bytes());
}

pub fn q8_0(x: &[f32], out: &mut [u8]) {
    let amax = x.iter().fold(0.0f32, |m, v| m.max(v.abs()));
    let d = amax / 127.0;
    let id = if d != 0.0 { 1.0 / d } else { 0.0 };
    out[..2].copy_from_slice(&f16(d));
    for (o, &v) in out[2..34].iter_mut().zip(x) {
        *o = (v * id).round() as i8 as u8;
    }
}
