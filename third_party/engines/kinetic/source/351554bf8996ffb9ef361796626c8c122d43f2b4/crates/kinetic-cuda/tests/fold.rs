//! The folding kernels against a host Walsh-Hadamard transform.

mod common;

use common::{gpu, Lcg};
use kinetic_cuda::{DeviceBuffer, GemvInput, ValueHeads};

fn host_fold(x: &[f32], signs: &[f32], block: usize) -> Vec<f32> {
    let mut y: Vec<f32> = x
        .iter()
        .zip(signs.iter().cycle())
        .map(|(a, s)| a * s)
        .collect();
    for b in y.chunks_exact_mut(block) {
        let mut h = 1;
        while h < block {
            for pair in b.chunks_exact_mut(2 * h) {
                let (lo, hi) = pair.split_at_mut(h);
                for (a, c) in lo.iter_mut().zip(hi) {
                    (*a, *c) = (*a + *c, *a - *c);
                }
            }
            h *= 2;
        }
        let scale = (block as f32).sqrt().recip();
        b.iter_mut().for_each(|v| *v *= scale);
    }
    y
}

#[test]
fn fold_and_unfold_match_the_host() {
    let Some(gpu) = gpu() else { return };
    let (width, block, rows) = (3 * 512, 512, 3);
    let mut rng = Lcg(9);
    let x: Vec<f32> = (0..rows * width).map(|_| rng.f32()).collect();
    let signs: Vec<f32> = (0..width)
        .map(|_| {
            if rng.next().is_multiple_of(2) {
                -1.0
            } else {
                1.0
            }
        })
        .collect();
    let d_signs = DeviceBuffer::from_slice(&gpu.ctx, &signs).unwrap();
    let mut input = GemvInput::batch(&gpu.ctx, width, rows).unwrap();
    input.upload(&gpu.kernels, &x, &gpu.stream).unwrap();
    let mut out = GemvInput::batch(&gpu.ctx, width, rows).unwrap();
    gpu.kernels
        .fold(&input, &d_signs, block, None, &mut out, rows, &gpu.stream)
        .unwrap();
    gpu.stream.synchronize().unwrap();
    let got = out.values().to_vec().unwrap();
    let want = host_fold(&x, &signs, block);
    for (i, (a, b)) in got.iter().zip(&want).enumerate() {
        assert!((a - b).abs() < 1e-5, "element {i}: {a} vs {b}");
    }

    let mut back = DeviceBuffer::from_slice(&gpu.ctx, &got).unwrap();
    gpu.kernels
        .unfold(&mut back, &d_signs, block, rows, &gpu.stream)
        .unwrap();
    gpu.stream.synchronize().unwrap();
    for (a, b) in back.to_vec().unwrap().iter().zip(&x) {
        assert!((a - b).abs() < 1e-5);
    }
}

#[test]
fn value_heads_are_regrouped_before_the_fold() {
    let Some(gpu) = gpu() else { return };
    let heads = ValueHeads {
        head_dim: 128,
        n_k: 2,
        n_v: 4,
    };
    let width = heads.head_dim * heads.n_v;
    let mut rng = Lcg(3);
    let x: Vec<f32> = (0..width).map(|_| rng.f32()).collect();
    let signs = vec![1.0; width];
    let d_signs = DeviceBuffer::from_slice(&gpu.ctx, &signs).unwrap();
    let mut input = GemvInput::new(&gpu.ctx, width).unwrap();
    input.upload(&gpu.kernels, &x, &gpu.stream).unwrap();
    let mut out = GemvInput::new(&gpu.ctx, width).unwrap();
    gpu.kernels
        .fold(
            &input,
            &d_signs,
            width,
            Some(heads),
            &mut out,
            1,
            &gpu.stream,
        )
        .unwrap();
    gpu.stream.synchronize().unwrap();
    // tiled k0r0 k1r0 k0r1 k1r1 regrouped to k0r0 k0r1 k1r0 k1r1
    let grouped: Vec<f32> = [0, 2, 1, 3]
        .iter()
        .flat_map(|&h| x[h * 128..][..128].to_vec())
        .collect();
    let want = host_fold(&grouped, &signs, width);
    for (a, b) in out.values().to_vec().unwrap().iter().zip(&want) {
        assert!((a - b).abs() < 1e-5);
    }
}
