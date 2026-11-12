//! GEMV kernels against `kinetic_quant::dequantize` and an f64 dot product.
//! Each test passes with a message when no CUDA device or no kernels exist.

mod common;

use common::{gpu, Lcg};
use half::f16;
use kinetic_cuda::{Argmax, DeviceBuffer, DeviceMatrix, Error, GemvInput, MAX_BATCH};
use kinetic_quant::{dequantize, Matrix, TensorType};

/// Random blocks with sane f16 scales at the positions each format uses;
/// float types get values in [-1, 1].
fn random_matrix(ty: TensorType, rows: usize, cols: usize, rng: &mut Lcg) -> Vec<u8> {
    let blocks = rows * cols / ty.block_len();
    match ty {
        TensorType::F32 => (0..blocks).flat_map(|_| rng.f32().to_le_bytes()).collect(),
        TensorType::F16 => (0..blocks)
            .flat_map(|_| f16::from_f32(rng.f32()).to_le_bytes())
            .collect(),
        _ => {
            let size = ty.block_bytes();
            let scale_offsets: &[usize] = match ty {
                TensorType::Q4K | TensorType::Q5K => &[0, 2],
                TensorType::Q6K => &[208],
                TensorType::Q8_0 | TensorType::Q4_0 | TensorType::PQ2_0 => &[0],
                _ => unreachable!(),
            };
            let mut data: Vec<u8> = (0..blocks * size).map(|_| rng.next() as u8).collect();
            for blk in data.chunks_exact_mut(size) {
                for &o in scale_offsets {
                    let v = f16::from_f32(0.001 + rng.f32().abs() * 0.01);
                    blk[o..o + 2].copy_from_slice(&v.to_le_bytes());
                }
            }
            data
        }
    }
}

/// The input the kernel actually multiplies with: `x` itself for float
/// weights, its int8 copy for quantized ones.
fn effective_input(ty: TensorType, x: &[f32], input: &GemvInput) -> Vec<f32> {
    if matches!(ty, TensorType::F32 | TensorType::F16) {
        return x.to_vec();
    }
    let qs = input.quantized().to_vec().unwrap();
    let ds = input.block_scales().to_vec().unwrap();
    qs.iter()
        .enumerate()
        .map(|(i, &q)| q as f32 * ds[2 * (i / 32)])
        .collect()
}

fn check(ty: TensorType, rows: usize, cols: usize) {
    let Some(gpu) = gpu() else { return };
    let mut rng = Lcg(ty as u64 + 1);
    let data = random_matrix(ty, rows, cols, &mut rng);
    let m = Matrix::new(ty, &data, rows, cols);
    let x: Vec<f32> = (0..cols).map(|_| rng.f32() * 3.0).collect();

    let w = DeviceMatrix::upload(&gpu.ctx, &m).unwrap();
    let mut input = GemvInput::new(&gpu.ctx, cols).unwrap();
    let mut y = DeviceBuffer::new(&gpu.ctx, rows).unwrap();
    input.upload(&gpu.kernels, &x, &gpu.stream).unwrap();
    gpu.kernels.gemv(&w, &input, &mut y, &gpu.stream).unwrap();
    gpu.stream.synchronize().unwrap();
    let y = y.to_vec().unwrap();

    let xe = effective_input(ty, &x, &input);
    let mut row = vec![0.0; cols];
    for (r, &got) in y.iter().enumerate() {
        dequantize(ty, m.row(r), &mut row).unwrap();
        let exact: f64 = row
            .iter()
            .zip(&xe)
            .map(|(&a, &b)| a as f64 * b as f64)
            .sum();
        let magnitude: f64 = row
            .iter()
            .zip(&xe)
            .map(|(&a, &b)| (a as f64 * b as f64).abs())
            .sum();
        let tol = 1e-5 * magnitude + 1e-6;
        assert!(
            (got as f64 - exact).abs() <= tol,
            "{ty} row {r}: got {got}, expected {exact}"
        );
    }
}

/// Every input of a batch must get bit-identical results to the same input
/// alone, whatever kernel the batch size selects.
fn check_batches(ty: TensorType, rows: usize, cols: usize) {
    let Some(gpu) = gpu() else { return };
    let mut rng = Lcg(ty as u64 + 100);
    let data = random_matrix(ty, rows, cols, &mut rng);
    let w = DeviceMatrix::upload(&gpu.ctx, &Matrix::new(ty, &data, rows, cols)).unwrap();
    let x: Vec<f32> = (0..MAX_BATCH * cols).map(|_| rng.f32() * 3.0).collect();
    let mut input = GemvInput::batch(&gpu.ctx, cols, MAX_BATCH).unwrap();
    input.upload(&gpu.kernels, &x, &gpu.stream).unwrap();
    let mut y = DeviceBuffer::new(&gpu.ctx, MAX_BATCH * rows).unwrap();

    let mut alone = Vec::new();
    for i in 0..MAX_BATCH {
        gpu.kernels
            .gemv_rows(&w, rows, &input, i..i + 1, &mut y, &gpu.stream)
            .unwrap();
        let mut row = vec![0.0f32; rows];
        y.copy_range_to(0, &mut row).unwrap();
        alone.push(row);
    }
    for n in 2..=MAX_BATCH {
        gpu.kernels
            .gemv_rows(&w, rows, &input, 0..n, &mut y, &gpu.stream)
            .unwrap();
        let got = y.to_vec().unwrap();
        for (i, expected) in alone.iter().take(n).enumerate() {
            let same = got[i * rows..][..rows]
                .iter()
                .zip(expected)
                .all(|(a, b)| a.to_bits() == b.to_bits());
            assert!(same, "{ty}: input {i} of a batch of {n} differs from alone");
        }
    }
}

/// Batches larger than [`MAX_BATCH`] run as a matrix product; every input
/// must still match the reference as closely as the GEMV does.
fn check_large_batch(ty: TensorType, rows: usize, cols: usize, n: usize) {
    let Some(gpu) = gpu() else { return };
    let mut rng = Lcg(ty as u64 + 200);
    let data = random_matrix(ty, rows, cols, &mut rng);
    let m = Matrix::new(ty, &data, rows, cols);
    let w = DeviceMatrix::upload(&gpu.ctx, &m).unwrap();
    let x: Vec<f32> = (0..n * cols).map(|_| rng.f32() * 3.0).collect();
    let mut input = GemvInput::batch(&gpu.ctx, cols, n).unwrap();
    input.upload(&gpu.kernels, &x, &gpu.stream).unwrap();
    let mut y = DeviceBuffer::new(&gpu.ctx, n * rows).unwrap();
    gpu.kernels
        .gemv_rows(&w, rows, &input, 0..n, &mut y, &gpu.stream)
        .unwrap();
    let y = y.to_vec().unwrap();

    let xe = effective_input(ty, &x, &input);
    let mut row = vec![0.0; cols];
    for r in 0..rows {
        dequantize(ty, m.row(r), &mut row).unwrap();
        for i in 0..n {
            let xi = &xe[i * cols..][..cols];
            let exact: f64 = row.iter().zip(xi).map(|(&a, &b)| a as f64 * b as f64).sum();
            let magnitude: f64 = row
                .iter()
                .zip(xi)
                .map(|(&a, &b)| (a as f64 * b as f64).abs())
                .sum();
            let got = y[i * rows + r] as f64;
            assert!(
                (got - exact).abs() <= 1e-5 * magnitude + 1e-6,
                "{ty} row {r} input {i}: got {got}, expected {exact}"
            );
        }
    }
}

#[test]
fn large_batches_match_reference() {
    // 100 rows and 70 inputs leave both tile edges partly empty.
    for ty in [
        TensorType::Q4K,
        TensorType::Q5K,
        TensorType::Q6K,
        TensorType::Q8_0,
        TensorType::Q4_0,
        TensorType::PQ2_0,
        TensorType::F16,
        TensorType::F32,
    ] {
        check_large_batch(ty, 100, 5 * 256, 70);
    }
    // A single stage runs unsplit whatever the device.
    check_large_batch(TensorType::Q8_0, 100, 128, 70);
    // A row length the matrix product does not take falls back to GEMVs.
    check_large_batch(TensorType::Q8_0, 37, 41 * 32, 40);
    // The 32- and 64-wide tiles of short batches.
    check_large_batch(TensorType::Q4K, 100, 5 * 256, 20);
    check_large_batch(TensorType::Q6K, 100, 5 * 256, 40);
    check_large_batch(TensorType::PQ2_0, 100, 5 * 256, 20);
}

// 37 rows leave the last thread block partly empty; 5 K-quant blocks per row
// leave some lane groups without a block on the second step.

#[test]
fn q4_k_matches_reference() {
    check(TensorType::Q4K, 37, 5 * 256);
}

#[test]
fn q5_k_matches_reference() {
    check(TensorType::Q5K, 37, 5 * 256);
}

#[test]
fn q6_k_matches_reference() {
    check(TensorType::Q6K, 37, 5 * 256);
}

#[test]
fn q8_0_matches_reference() {
    check(TensorType::Q8_0, 37, 41 * 32);
}

#[test]
fn f16_matches_reference() {
    check(TensorType::F16, 37, 41 * 32);
}

#[test]
fn f32_matches_reference() {
    check(TensorType::F32, 37, 41 * 32);
}

#[test]
fn batches_match_single_inputs() {
    for ty in [TensorType::Q4K, TensorType::Q5K, TensorType::Q6K] {
        check_batches(ty, 37, 5 * 256);
    }
    for ty in [TensorType::Q8_0, TensorType::F16, TensorType::F32] {
        check_batches(ty, 37, 41 * 32);
    }
}

/// The gated product matches the two products and the activation run
/// apart, within the rounding of the sums.
#[test]
fn gated_product_matches_separate_products() {
    let Some(gpu) = gpu() else { return };
    // 224 rows leave the last block of 64 partly empty.
    let (rows, cols, n) = (224, 2 * 256, 70);
    for (ty, gelu) in [
        (TensorType::Q4K, false),
        (TensorType::Q6K, false),
        (TensorType::Q4_0, true),
    ] {
        let mut rng = Lcg(ty as u64 + 300);
        let upload = |rng: &mut Lcg| {
            let data = random_matrix(ty, rows, cols, rng);
            DeviceMatrix::upload(&gpu.ctx, &Matrix::new(ty, &data, rows, cols)).unwrap()
        };
        let (gate, up) = (upload(&mut rng), upload(&mut rng));
        let x: Vec<f32> = (0..n * cols).map(|_| rng.f32() * 3.0).collect();
        let mut input = GemvInput::batch(&gpu.ctx, cols, n).unwrap();
        input.upload(&gpu.kernels, &x, &gpu.stream).unwrap();
        let k = &gpu.kernels;

        let mut fused = GemvInput::batch(&gpu.ctx, rows, n).unwrap();
        let ran = k
            .glu_matmul(&gate, &up, gelu, &input, 0..n, &mut fused, &gpu.stream)
            .unwrap();
        assert!(ran, "{ty}: no gated product kernel");

        let mut g = DeviceBuffer::new(&gpu.ctx, n * rows).unwrap();
        let mut u = DeviceBuffer::new(&gpu.ctx, n * rows).unwrap();
        k.gemv_rows(&gate, rows, &input, 0..n, &mut g, &gpu.stream)
            .unwrap();
        k.gemv_rows(&up, rows, &input, 0..n, &mut u, &gpu.stream)
            .unwrap();
        let mut apart = GemvInput::batch(&gpu.ctx, rows, n).unwrap();
        if gelu {
            k.geglu(&g, &u, &mut apart, n, &gpu.stream).unwrap();
        } else {
            k.swiglu(&g, &u, &mut apart, n, &gpu.stream).unwrap();
        }

        let got = fused.values().to_vec().unwrap();
        let want = apart.values().to_vec().unwrap();
        let scale = want.iter().fold(0.0f32, |m, v| m.max(v.abs()));
        for (i, (a, b)) in got.iter().zip(&want).enumerate() {
            assert!(
                (a - b).abs() <= 1e-5 * scale,
                "{ty} element {i}: {a} vs {b}"
            );
        }
        let qs = |v: &GemvInput| v.quantized().to_vec().unwrap();
        let close = qs(&fused)
            .iter()
            .zip(qs(&apart))
            .all(|(&a, b)| (a as i32 - b as i32).abs() <= 1);
        assert!(close, "{ty}: int8 copies differ by more than a step");
    }
}

#[test]
fn argmax_prefers_the_lowest_index() {
    let Some(gpu) = gpu() else { return };
    let len = 10_000;
    let mut x = vec![0.0f32; 2 * len];
    x[7000] = 5.0;
    x[9000] = 5.0;
    x[len..].fill(-2.0);
    x[len + 4100] = 1.0;
    let x = DeviceBuffer::from_slice(&gpu.ctx, &x).unwrap();
    let mut best = Argmax::new(&gpu.ctx, 2, len).unwrap();
    gpu.kernels
        .argmax(&x, len, 2, &mut best, &gpu.stream)
        .unwrap();
    assert_eq!(best.best().to_vec().unwrap(), [7000, 4100]);
}

#[test]
fn quantized_input_is_within_half_a_step() {
    let Some(gpu) = gpu() else { return };
    let mut rng = Lcg(7);
    let mut x: Vec<f32> = (0..1024).map(|_| rng.f32() * 5.0).collect();
    x[32..64].fill(0.0);
    let mut input = GemvInput::new(&gpu.ctx, x.len()).unwrap();
    input.upload(&gpu.kernels, &x, &gpu.stream).unwrap();
    gpu.stream.synchronize().unwrap();
    let qs = input.quantized().to_vec().unwrap();
    let ds = input.block_scales().to_vec().unwrap();
    for (b, (xs, q)) in x.chunks(32).zip(qs.chunks(32)).enumerate() {
        let (d, sum) = (ds[2 * b], ds[2 * b + 1]);
        let qsum: i32 = q.iter().map(|&v| v as i32).sum();
        assert_eq!(sum, d * qsum as f32, "block {b} sum");
        for (&v, &q) in xs.iter().zip(q) {
            assert!(
                (v - q as f32 * d).abs() <= d * 0.5001,
                "block {b}: {v} vs {q} * {d}"
            );
        }
    }
}

#[test]
fn mismatched_shapes_are_rejected() {
    let Some(gpu) = gpu() else { return };
    let data = vec![0u8; 4 * 64 * 4];
    let w = DeviceMatrix::upload(&gpu.ctx, &Matrix::new(TensorType::F32, &data, 4, 64)).unwrap();
    let input = GemvInput::new(&gpu.ctx, 32).unwrap();
    let mut y = DeviceBuffer::new(&gpu.ctx, 4).unwrap();
    let result = gpu.kernels.gemv(&w, &input, &mut y, &gpu.stream);
    assert!(matches!(result, Err(Error::Shape(_))));
}
