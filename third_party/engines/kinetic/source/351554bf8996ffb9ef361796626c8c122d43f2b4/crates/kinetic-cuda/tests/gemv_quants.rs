//! GEMV kernels of the formats below Q4_K, codebook and ternary ones
//! included, against `kinetic_quant::dequantize`
//! and an f64 dot product, alone and batched, and the embedding lookup of
//! the same matrices. Each test passes with a message when no CUDA device or
//! no kernels exist.

use std::rc::Rc;

use half::f16;
use kinetic_cuda::{
    Batch, Context, Device, DeviceBuffer, DeviceMatrix, Error, GemvInput, Kernels, Stream,
    MAX_BATCH,
};
use kinetic_quant::{dequantize, Matrix, TensorType};

const TYPES: [(TensorType, usize); 15] = [
    (TensorType::Q4_0, 41 * 32),
    (TensorType::Q4_1, 41 * 32),
    (TensorType::Q5_0, 41 * 32),
    (TensorType::Q5_1, 41 * 32),
    (TensorType::IQ4NL, 41 * 32),
    (TensorType::MXFP4, 41 * 32),
    (TensorType::Q2K, 5 * 256),
    (TensorType::Q3K, 5 * 256),
    (TensorType::IQ3S, 5 * 256),
    (TensorType::IQ2S, 5 * 256),
    (TensorType::IQ1S, 5 * 256),
    (TensorType::IQ1M, 5 * 256),
    (TensorType::TQ1_0, 5 * 256),
    (TensorType::TQ2_0, 5 * 256),
    (TensorType::PQ2_0, 11 * 128),
];

/// 37 rows leave the last thread block partly empty.
const ROWS: usize = 37;

struct Gpu {
    ctx: Rc<Context>,
    kernels: Kernels,
    stream: Stream,
}

fn gpu() -> Option<Gpu> {
    match Device::count() {
        Ok(n) if n > 0 => {}
        Ok(_) => {
            eprintln!("skipped: no CUDA device");
            return None;
        }
        Err(e) => {
            eprintln!("skipped: {e}");
            return None;
        }
    }
    let ctx = Context::new(Device::get(0).unwrap()).unwrap();
    let kernels = match Kernels::load(&ctx) {
        Ok(k) => k,
        Err(Error::KernelsNotBuilt) => {
            eprintln!("skipped: {}", Error::KernelsNotBuilt);
            return None;
        }
        Err(e) => panic!("{e}"),
    };
    let stream = Stream::new(&ctx).unwrap();
    Some(Gpu {
        ctx,
        kernels,
        stream,
    })
}

struct Lcg(u64);

impl Lcg {
    fn next(&mut self) -> u32 {
        self.0 = self
            .0
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        (self.0 >> 33) as u32
    }

    fn f32(&mut self) -> f32 {
        self.next() as f32 / u32::MAX as f32 * 2.0 - 1.0
    }
}

/// Random blocks with small positive f16 scales (and a moderate exponent
/// for MXFP4) where each format keeps them.
fn random_matrix(ty: TensorType, rows: usize, cols: usize, rng: &mut Lcg) -> Vec<u8> {
    let size = ty.block_bytes();
    let blocks = rows * cols / ty.block_len();
    let scale_offsets: &[usize] = match ty {
        TensorType::Q4_1 | TensorType::Q5_1 => &[0, 2],
        TensorType::Q4_0 | TensorType::Q5_0 | TensorType::IQ4NL => &[0],
        TensorType::Q2K => &[80, 82],
        TensorType::Q3K => &[108],
        TensorType::IQ3S | TensorType::IQ2S | TensorType::IQ1S | TensorType::PQ2_0 => &[0],
        TensorType::TQ1_0 => &[52],
        TensorType::TQ2_0 => &[64],
        _ => &[],
    };
    let mut data: Vec<u8> = (0..blocks * size).map(|_| rng.next() as u8).collect();
    for blk in data.chunks_exact_mut(size) {
        for &o in scale_offsets {
            let v = f16::from_f32(0.001 + rng.f32().abs() * 0.01);
            blk[o..o + 2].copy_from_slice(&v.to_le_bytes());
        }
        if ty == TensorType::MXFP4 {
            blk[0] = 118 + (rng.next() % 8) as u8;
        }
        if ty == TensorType::IQ1M {
            // The block scale's nibbles top the four scale words.
            let bits = f16::from_f32(0.001 + rng.f32().abs() * 0.01).to_bits();
            for (i, word) in blk[48..56].chunks_exact_mut(2).enumerate() {
                word[1] = (word[1] & 0x0F) | ((bits >> (4 * i)) as u8 & 0x0F) << 4;
            }
        }
    }
    data
}

fn check(gpu: &Gpu, ty: TensorType, cols: usize) {
    let mut rng = Lcg(ty as u64 + 1);
    let data = random_matrix(ty, ROWS, cols, &mut rng);
    let m = Matrix::new(ty, &data, ROWS, cols);
    let x: Vec<f32> = (0..cols).map(|_| rng.f32() * 3.0).collect();

    let w = DeviceMatrix::upload(&gpu.ctx, &m).unwrap();
    let mut input = GemvInput::new(&gpu.ctx, cols).unwrap();
    let mut y = DeviceBuffer::new(&gpu.ctx, ROWS).unwrap();
    input.upload(&gpu.kernels, &x, &gpu.stream).unwrap();
    gpu.kernels.gemv(&w, &input, &mut y, &gpu.stream).unwrap();
    gpu.stream.synchronize().unwrap();
    let y = y.to_vec().unwrap();

    let qs = input.quantized().to_vec().unwrap();
    let ds = input.block_scales().to_vec().unwrap();
    let xe: Vec<f32> = qs
        .iter()
        .enumerate()
        .map(|(i, &q)| q as f32 * ds[2 * (i / 32)])
        .collect();
    let mut row = vec![0.0; cols];
    for (r, &got) in y.iter().enumerate() {
        dequantize(ty, m.row(r), &mut row).unwrap();
        let products = row.iter().zip(&xe).map(|(&a, &b)| a as f64 * b as f64);
        let exact: f64 = products.clone().sum();
        let magnitude: f64 = products.map(f64::abs).sum();
        assert!(
            (got as f64 - exact).abs() <= 1e-5 * magnitude + 1e-6,
            "{ty} row {r}: got {got}, expected {exact}"
        );
    }
}

/// Every input of a batch must get bit-identical results to the same input
/// alone.
fn check_batches(gpu: &Gpu, ty: TensorType, cols: usize) {
    let mut rng = Lcg(ty as u64 + 100);
    let data = random_matrix(ty, ROWS, cols, &mut rng);
    let w = DeviceMatrix::upload(&gpu.ctx, &Matrix::new(ty, &data, ROWS, cols)).unwrap();
    let x: Vec<f32> = (0..MAX_BATCH * cols).map(|_| rng.f32() * 3.0).collect();
    let mut input = GemvInput::batch(&gpu.ctx, cols, MAX_BATCH).unwrap();
    input.upload(&gpu.kernels, &x, &gpu.stream).unwrap();
    let mut y = DeviceBuffer::new(&gpu.ctx, MAX_BATCH * ROWS).unwrap();

    let mut alone = Vec::new();
    for i in 0..MAX_BATCH {
        gpu.kernels
            .gemv_rows(&w, ROWS, &input, i..i + 1, &mut y, &gpu.stream)
            .unwrap();
        let mut row = vec![0.0f32; ROWS];
        y.copy_range_to(0, &mut row).unwrap();
        alone.push(row);
    }
    for n in 2..=MAX_BATCH {
        gpu.kernels
            .gemv_rows(&w, ROWS, &input, 0..n, &mut y, &gpu.stream)
            .unwrap();
        let got = y.to_vec().unwrap();
        for (i, expected) in alone.iter().take(n).enumerate() {
            let same = got[i * ROWS..][..ROWS]
                .iter()
                .zip(expected)
                .all(|(a, b)| a.to_bits() == b.to_bits());
            assert!(same, "{ty}: input {i} of a batch of {n} differs from alone");
        }
    }
}

fn check_embed(gpu: &Gpu, ty: TensorType, cols: usize) {
    let mut rng = Lcg(ty as u64 + 200);
    let data = random_matrix(ty, ROWS, cols, &mut rng);
    let m = Matrix::new(ty, &data, ROWS, cols);
    let table = DeviceMatrix::upload(&gpu.ctx, &m).unwrap();
    let tokens = [3u32, 0, 36, 17];
    let mut batch = Batch::new(&gpu.ctx, tokens.len()).unwrap();
    batch.set(0, &tokens, &gpu.stream).unwrap();
    let mut out = DeviceBuffer::new(&gpu.ctx, tokens.len() * cols).unwrap();
    gpu.kernels
        .embed(&table, 1.0, &batch, &mut out, &gpu.stream)
        .unwrap();
    gpu.stream.synchronize().unwrap();
    let out = out.to_vec().unwrap();
    let mut row = vec![0.0; cols];
    for (t, &token) in tokens.iter().enumerate() {
        dequantize(ty, m.row(token as usize), &mut row).unwrap();
        assert_eq!(out[t * cols..][..cols], row[..], "{ty} token {token}");
    }
}

#[test]
fn low_bit_formats_match_reference() {
    let Some(gpu) = gpu() else { return };
    for (ty, cols) in TYPES {
        check(&gpu, ty, cols);
    }
}

#[test]
fn low_bit_batches_match_single_inputs() {
    let Some(gpu) = gpu() else { return };
    for (ty, cols) in TYPES {
        check_batches(&gpu, ty, cols);
    }
}

#[test]
fn low_bit_embeddings_match_reference() {
    let Some(gpu) = gpu() else { return };
    for (ty, cols) in TYPES {
        check_embed(&gpu, ty, cols);
    }
}
