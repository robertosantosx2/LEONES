//! Cost of a k-token product against a one-token product when the weights
//! stream from memory, as in a model's forward pass: layers of Qwen3.5-4B
//! sized projections, ~430 MB in all, far past the last-level cache.
//!
//! cargo run --release -p kinetic-cpu --example kcost -- [q4_k|q6_k|q8_0|mix]

use std::time::Instant;

use kinetic_cpu::matmul;
use kinetic_quant::{Matrix, TensorType};

fn main() {
    let kind = std::env::args().nth(1).unwrap_or_else(|| "mix".into());
    let shapes: Vec<(TensorType, usize, usize)> = match kind.as_str() {
        "q4_k" => vec![(TensorType::Q4K, 9216, 2560), (TensorType::Q4K, 2560, 9216)],
        "q6_k" => vec![(TensorType::Q6K, 9216, 2560), (TensorType::Q6K, 2560, 9216)],
        "q8_0" => vec![
            (TensorType::Q8_0, 4096, 2560),
            (TensorType::Q8_0, 2560, 4096),
        ],
        _ => vec![
            (TensorType::Q4K, 9216, 2560),
            (TensorType::Q4K, 9216, 2560),
            (TensorType::Q6K, 2560, 9216),
            (TensorType::Q4K, 8192, 2560),
        ],
    };
    let mut seed = 0x9E37_79B9_7F4A_7C15u64;
    let mut next = move || {
        seed ^= seed << 13;
        seed ^= seed >> 7;
        seed ^= seed << 17;
        seed
    };
    let layer_bytes: usize = shapes
        .iter()
        .map(|&(ty, r, c)| r * c / ty.block_len() * ty.block_bytes())
        .sum();
    let layers = (430 << 20) / layer_bytes;
    let data: Vec<Vec<u8>> = (0..layers * shapes.len())
        .map(|i| {
            let (ty, r, c) = shapes[i % shapes.len()];
            (0..r * c / ty.block_len() * ty.block_bytes())
                .map(|_| (next() as u8 & 0x3F) | 0x10)
                .collect()
        })
        .collect();
    let ws: Vec<Matrix> = data
        .iter()
        .enumerate()
        .map(|(i, d)| {
            let (ty, r, c) = shapes[i % shapes.len()];
            Matrix::new(ty, d, r, c)
        })
        .collect();
    let width = ws.iter().map(|w| w.cols).max().unwrap();
    let x: Vec<f32> = (0..16 * width)
        .map(|_| (next() >> 40) as f32 / (1u64 << 23) as f32 - 1.0)
        .collect();
    let mut y = vec![0.0; 16 * 9216];
    let mut base = 0.0;
    for k in [1, 2, 3, 4, 6, 8, 12, 16] {
        let mut pass = || {
            let start = Instant::now();
            for w in &ws {
                matmul(w, &x[..k * w.cols], &mut y[..k * w.rows]);
            }
            start.elapsed().as_secs_f64()
        };
        let best = (0..5).map(|_| pass()).fold(f64::INFINITY, f64::min);
        if k == 1 {
            base = best;
        }
        println!(
            "{kind} k {k:>2}  {:>7.2} ms  {:.2}x  {:.1} GB/s",
            best * 1e3,
            best / base,
            (layers * layer_bytes) as f64 / best / 1e9
        );
    }
}
