//! The tensor-core vision kernels against plain host sums.

mod common;

use common::{gpu, Lcg};
use half::f16;
use kinetic_cuda::{DeviceBuffer, DeviceMatrix, GemvInput, VisionKernels};
use kinetic_quant::{Matrix, TensorType};

#[test]
fn matmul_matches_the_host() {
    let Some(gpu) = gpu() else { return };
    let vision = VisionKernels::load(&gpu.ctx).unwrap();
    // neither the inputs nor the rows fill whole blocks
    let (n, rows, k) = (150, 134, 96);
    let mut rng = Lcg(5);
    let w: Vec<f16> = (0..rows * k).map(|_| f16::from_f32(rng.f32())).collect();
    let x: Vec<f32> = (0..n * k).map(|_| rng.f32() * 50.0).collect();
    let bytes: Vec<u8> = w.iter().flat_map(|v| v.to_le_bytes()).collect();
    let dw =
        DeviceMatrix::upload(&gpu.ctx, &Matrix::new(TensorType::F16, &bytes, rows, k)).unwrap();
    let mut dx = GemvInput::batch(&gpu.ctx, k, n).unwrap();
    dx.upload(&gpu.kernels, &x, &gpu.stream).unwrap();
    let mut y = DeviceBuffer::new(&gpu.ctx, n * rows).unwrap();
    vision
        .matmul(&gpu.kernels, &dw, &dx, n, &mut y, &gpu.stream)
        .unwrap();
    gpu.stream.synchronize().unwrap();
    let got = y.to_vec().unwrap();
    for t in 0..n {
        for r in 0..rows {
            let terms = (0..k).map(|i| x[t * k + i] as f64 * w[r * k + i].to_f64());
            let (want, size) = terms.fold((0.0, 0.0), |(s, a), v| (s + v, a + v.abs()));
            let g = got[t * rows + r] as f64;
            // the inputs' two f16 parts keep ~22 bits, the sums are f32
            let bound = size * 4e-6;
            assert!((g - want).abs() < bound, "input {t} row {r}: {g} vs {want}");
        }
    }
}

#[test]
fn attention_matches_the_host() {
    let Some(gpu) = gpu() else { return };
    let vision = VisionKernels::load(&gpu.ctx).unwrap();
    let (n, heads, hd) = (100, 2, 64);
    let width = heads * hd;
    let mut rng = Lcg(8);
    let qkv: Vec<f32> = (0..n * 3 * width).map(|_| rng.f32() * 2.0).collect();
    let dqkv = DeviceBuffer::from_slice(&gpu.ctx, &qkv).unwrap();
    let mut out = GemvInput::batch(&gpu.ctx, width, n).unwrap();
    vision
        .attention(&gpu.kernels, &dqkv, (n, heads, hd), &mut out, &gpu.stream)
        .unwrap();
    gpu.stream.synchronize().unwrap();
    let got = out.values().to_vec().unwrap();
    let at = |t: usize, part: usize, h: usize| &qkv[t * 3 * width + part * width + h * hd..][..hd];
    for t in 0..n {
        for h in 0..heads {
            let s: Vec<f64> = (0..n)
                .map(|j| {
                    let dot: f64 = at(t, 0, h)
                        .iter()
                        .zip(at(j, 1, h))
                        .map(|(a, b)| *a as f64 * *b as f64)
                        .sum();
                    dot / (hd as f64).sqrt()
                })
                .collect();
            let max = s.iter().copied().fold(f64::NEG_INFINITY, f64::max);
            let e: Vec<f64> = s.iter().map(|v| (v - max).exp()).collect();
            let sum: f64 = e.iter().sum();
            for d in 0..hd {
                let want: f64 = (0..n).map(|j| e[j] / sum * at(j, 2, h)[d] as f64).sum();
                let g = got[t * width + h * hd + d] as f64;
                assert!(
                    (g - want).abs() < 5e-3,
                    "token {t} head {h} dim {d}: {g} vs {want}"
                );
            }
        }
    }
}
