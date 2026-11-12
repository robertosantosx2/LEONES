//! The Q4_K copy of an output head and, per row, how far its products can
//! stray from those of the head.

use half::f16;
use kinetic_quant::{dequantize, Matrix, TensorType};
use rayon::prelude::*;

const QK_K: usize = 256;
const BLOCK_BYTES: usize = 144;

/// Per row of the copy, what bounds the gap between its products and the
/// head's: with `xh` and `xc` the activations the head's kernel and the
/// copy's kernel multiply by (see `kinetic_cpu::kernel_input`), the two
/// products as computed differ by at most
/// `head |xh| + copy |xh - xc| + spread slack |xc|`.
#[derive(Clone, Copy, Default)]
pub(super) struct Radii {
    pub head: f32,
    pub copy: f32,
    pub spread: f32,
}

/// A Q4_K copy of `head`, the radii of its rows and the slack they are
/// used with.
pub(super) fn build(head: &Matrix) -> (Vec<u8>, Vec<Radii>, f64) {
    let row_bytes = head.cols / QK_K * BLOCK_BYTES;
    // Both kernels fold exact integer block sums into the result with fewer
    // than `cols + 8` f32 roundings on any path, so each one's error is
    // under (cols + 8) 2^-24 sum |w x|, where for the copy `w` counts its
    // scaled values and its offsets apart. Twice that also covers rounding
    // in the f32 values of either matrix and in the f64 arithmetic of the
    // bound.
    let slack = (head.cols + 8) as f64 * f64::powi(2.0, -23);
    let mut copy = vec![0u8; head.rows * row_bytes];
    let mut radii = vec![Radii::default(); head.rows];
    copy.par_chunks_mut(row_bytes)
        .zip(radii.par_iter_mut())
        .enumerate()
        .for_each_init(
            || (vec![0.0; head.cols], vec![0.0; head.cols]),
            |(w, c), (r, (packed, radii))| {
                dequantize(head.ty, head.row(r), w).expect("head type");
                let mut spread = 0.0;
                for (src, dst) in w
                    .chunks_exact(QK_K)
                    .zip(packed.chunks_exact_mut(BLOCK_BYTES))
                {
                    spread += quantize_block(src, dst);
                }
                dequantize(TensorType::Q4K, packed, c).expect("Q4_K");
                let norm = |v: &mut dyn Iterator<Item = f64>| v.map(|v| v * v).sum::<f64>().sqrt();
                let err = norm(&mut w.iter().zip(c.iter()).map(|(&a, &b)| a as f64 - b as f64));
                *radii = Radii {
                    head: round_up(err + slack * norm(&mut w.iter().map(|&v| v as f64))),
                    copy: round_up(norm(&mut c.iter().map(|&v| v as f64))),
                    spread: round_up(spread.sqrt()),
                };
            },
        );
    (copy, radii, slack)
}

/// The smallest f32 at or above `v`.
fn round_up(v: f64) -> f32 {
    let f = v as f32;
    if (f as f64) < v {
        f.next_up()
    } else {
        f
    }
}

/// One Q4_K block, `d * sc * q - dmin * m` with 4-bit `q` and 6-bit `sc`
/// and `m` per 32 values. Returns the sum over the block of
/// `(d * sc * q + dmin * m)^2`, the magnitudes the kernel's rounding acts
/// on.
fn quantize_block(src: &[f32], dst: &mut [u8]) -> f64 {
    let mut scale = [0.0f32; 8];
    let mut min = [0.0f32; 8];
    for (s, g) in src.chunks_exact(32).enumerate() {
        let lo = g.iter().fold(0.0f32, |m, &v| m.min(v));
        let hi = g.iter().fold(0.0f32, |m, &v| m.max(v));
        scale[s] = (hi - lo) / 15.0;
        min[s] = -lo;
    }
    let max = |v: &[f32; 8]| v.iter().fold(0.0f32, |m, &v| m.max(v));
    let d = f16::from_f32(max(&scale) / 63.0).to_f32();
    let dmin = f16::from_f32(max(&min) / 63.0).to_f32();
    let six_bit = |v: f32, unit: f32| {
        if unit > 0.0 {
            (v / unit).round().clamp(0.0, 63.0) as u8
        } else {
            0
        }
    };
    let sc = scale.map(|v| six_bit(v, d));
    let m = min.map(|v| six_bit(v, dmin));

    dst[0..2].copy_from_slice(&f16::from_f32(d).to_le_bytes());
    dst[2..4].copy_from_slice(&f16::from_f32(dmin).to_le_bytes());
    let packed = &mut dst[4..16];
    for j in 0..4 {
        packed[j] = sc[j] | (sc[j + 4] >> 4) << 6;
        packed[j + 4] = m[j] | (m[j + 4] >> 4) << 6;
        packed[j + 8] = (sc[j + 4] & 0xF) | (m[j + 4] & 0xF) << 4;
    }
    let mut spread = 0.0;
    let mut quantize = |s: usize, v: f32| {
        let step = d * sc[s] as f32;
        let offset = dmin * m[s] as f32;
        let q = if step > 0.0 {
            ((v + offset) / step).round().clamp(0.0, 15.0) as u8
        } else {
            0
        };
        spread += (step as f64 * q as f64 + offset as f64).powi(2);
        q
    };
    for j in 0..4 {
        for l in 0..32 {
            let lo = quantize(2 * j, src[64 * j + l]);
            let hi = quantize(2 * j + 1, src[64 * j + 32 + l]);
            dst[16 + 32 * j + l] = lo | hi << 4;
        }
    }
    spread
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn copy_is_close_and_within_its_radii() {
        let (rows, cols) = (3, 512);
        let w: Vec<f32> = (0..rows * cols)
            .map(|i| ((i * 37 % 101) as f32 - 40.0) * 0.013)
            .collect();
        let bytes: Vec<u8> = w.iter().flat_map(|v| v.to_le_bytes()).collect();
        let head = Matrix::new(TensorType::F32, &bytes, rows, cols);
        let (copy, radii, _) = build(&head);
        let mut c = vec![0.0; rows * cols];
        dequantize(TensorType::Q4K, &copy, &mut c).unwrap();
        let norm = |v: &mut dyn Iterator<Item = f32>| v.map(|v| v * v).sum::<f32>().sqrt();
        for (r, radii) in radii.iter().enumerate() {
            let (w, c) = (&w[r * cols..][..cols], &c[r * cols..][..cols]);
            let err = norm(&mut w.iter().zip(c).map(|(a, b)| a - b));
            assert!(radii.head >= err && err < 0.1 * norm(&mut w.iter().copied()));
            let c_norm = norm(&mut c.iter().copied());
            assert!(radii.spread >= radii.copy && (radii.copy - c_norm).abs() <= 1e-5 * c_norm);
        }
    }
}
