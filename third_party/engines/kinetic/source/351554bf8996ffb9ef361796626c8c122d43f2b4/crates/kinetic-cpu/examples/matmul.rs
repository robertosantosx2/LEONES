//! Times `matmul` on random weights for the projection shapes of the
//! bundled models, for single-token decode and a 512-token prefill batch.
//!
//! cargo run --release -p kinetic-cpu --example matmul -- [tokens]
//!
//! Set `RAYON_NUM_THREADS` to choose the thread count.

use std::time::Instant;

use kinetic_cpu::matmul;
use kinetic_quant::{Matrix, TensorType};

/// (type, rows, cols) of the large projections in Qwen3.5-4B and LFM3-1.7B,
/// then of small models whose widths are not multiples of 256: Qwen2.5-0.5B,
/// Gemma 3 270M and SmolLM2-135M, then the feed-forward of Qwen3-0.6B in
/// the formats below Q4_K.
const SHAPES: &[(TensorType, usize, usize)] = &[
    (TensorType::Q4K, 9216, 2560),
    (TensorType::Q6K, 2560, 9216),
    (TensorType::Q4K, 2560, 9216),
    (TensorType::Q5K, 8192, 2560),
    (TensorType::Q5K, 2560, 4096),
    (TensorType::Q4K, 7680, 2048),
    (TensorType::Q6K, 2048, 7680),
    (TensorType::Q8_0, 4096, 4096),
    (TensorType::Q4_0, 4096, 4096),
    (TensorType::Q8_0, 4864, 896),
    (TensorType::Q8_0, 2048, 640),
    (TensorType::Q4_0, 4864, 896),
    (TensorType::F16, 1536, 576),
    (TensorType::F16, 576, 1536),
    (TensorType::BF16, 1536, 576),
    (TensorType::Q8_0, 65536, 640),
    (TensorType::F16, 49152, 576),
    (TensorType::Q4K, 3072, 1024),
    (TensorType::Q4_1, 3072, 1024),
    (TensorType::Q5_0, 3072, 1024),
    (TensorType::Q5_1, 3072, 1024),
    (TensorType::IQ4NL, 3072, 1024),
    (TensorType::MXFP4, 3072, 1024),
    (TensorType::Q3K, 3072, 1024),
    (TensorType::Q2K, 3072, 1024),
    (TensorType::IQ3S, 3072, 1024),
    (TensorType::IQ2S, 3072, 1024),
    (TensorType::IQ1M, 3072, 1024),
    (TensorType::IQ1S, 3072, 1024),
    (TensorType::TQ2_0, 3072, 1024),
    (TensorType::TQ1_0, 3072, 1024),
];

fn main() {
    let batch: usize = std::env::args()
        .nth(1)
        .map_or(512, |s| s.parse().expect("token count"));
    let mut seed = 0x9E37_79B9_7F4A_7C15u64;
    let mut next = move || {
        seed ^= seed << 13;
        seed ^= seed >> 7;
        seed ^= seed << 17;
        seed
    };
    println!(
        "{:>6} {:>11} {:>6} {:>10} {:>9} {:>10} {:>9}",
        "type", "shape", "", "decode ms", "GB/s", "batch ms", "GMAC/s"
    );
    for &(ty, rows, cols) in SHAPES {
        let bytes = rows * cols / ty.block_len() * ty.block_bytes();
        let data: Vec<u8> = (0..bytes).map(|_| sane_byte(next())).collect();
        let w = Matrix::new(ty, &data, rows, cols);
        let x: Vec<f32> = (0..batch * cols)
            .map(|_| (next() >> 40) as f32 / (1u64 << 23) as f32 - 1.0)
            .collect();

        let mut y = vec![0.0; rows];
        let decode = best_of(20, || matmul(&w, &x[..cols], &mut y));
        let mut y = vec![0.0; batch * rows];
        let prefill = best_of(3, || matmul(&w, &x, &mut y));
        println!(
            "{:>6} {:>5}x{:<5} {:>6} {:>10.3} {:>9.1} {:>10.2} {:>9.1}",
            ty.name(),
            rows,
            cols,
            "",
            decode * 1e3,
            bytes as f64 / decode / 1e9,
            prefill * 1e3,
            (batch * rows * cols) as f64 / prefill / 1e9,
        );
    }
}

/// Random bytes that keep every f16 scale finite and normal, whichever
/// offset a format stores its scales at.
fn sane_byte(r: u64) -> u8 {
    (r as u8 & 0x3F) | 0x10
}

fn best_of(runs: usize, mut f: impl FnMut()) -> f64 {
    f();
    (0..runs)
        .map(|_| {
            let start = Instant::now();
            f();
            start.elapsed().as_secs_f64()
        })
        .fold(f64::INFINITY, f64::min)
}
