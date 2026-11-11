//! Encodes one image and prints a summary of the embeddings, laid out like
//! the tensor dumps of llama.cpp's `llama-mtmd-debug` for comparison.
//!
//! cargo run --release -p kinetic-vision --example encode -- mmproj.gguf image.png
//! cargo run --release -p kinetic-vision --example encode -- mmproj.gguf rainbow:512
//!
//! `rainbow:N` is the unnormalized N x N test pattern of `llama-mtmd-debug
//! --image rainbow -n N`, fed to the encoder as is. Built with `--features
//! cuda`, a third argument `cuda` encodes on the GPU too and compares.

use std::time::Instant;

use kinetic_gguf::GgufFile;
use kinetic_vision::{decode, Pixels, VisionEncoder};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let usage = "usage: encode <mmproj.gguf> <image | rainbow:N>";
    let file = GgufFile::open(args.next().ok_or(usage)?)?;
    let input = args.next().ok_or(usage)?;
    let encoder = VisionEncoder::load(&file)?;

    let start = Instant::now();
    let pixels = match input.strip_prefix("rainbow:") {
        Some(n) => rainbow(n.parse()?),
        None => encoder.prepare(&decode(&std::fs::read(&input)?)?),
    };
    let prepared = start.elapsed();
    let start = Instant::now();
    let e = encoder.encode(&pixels)?;
    let encoded = start.elapsed();

    let d = encoder.n_embd_out();
    let n = e.len();
    for t in (0..n).filter(|&t| t < 3 || t + 3 >= n) {
        let row = &e.rows[t * d..][..d];
        let show = |v: &[f32]| v.iter().map(|v| format!("{v:10.4}")).collect::<Vec<_>>();
        println!(
            "[{}, ..., {}]",
            show(&row[..3]).join(", "),
            show(&row[d - 3..]).join(", ")
        );
    }
    println!("sum = {:.6}", e.rows.iter().map(|&v| v as f64).sum::<f64>());
    println!(
        "{}x{} pixels -> {}x{} = {n} tokens; prepare {:.1} ms, encode {:.1} ms",
        pixels.width,
        pixels.height,
        e.width,
        e.height,
        prepared.as_secs_f64() * 1e3,
        encoded.as_secs_f64() * 1e3
    );
    #[cfg(feature = "cuda")]
    if args.next().as_deref() == Some("cuda") {
        let mut encoder = encoder;
        encoder.use_cuda()?;
        encoder.encode(&pixels)?;
        let start = Instant::now();
        let g = encoder.encode(&pixels)?;
        let took = start.elapsed();
        if g.rows.len() != e.rows.len() {
            return Err(format!("gpu gave {} values, cpu {}", g.rows.len(), e.rows.len()).into());
        }
        let diff = e.rows.iter().zip(&g.rows).map(|(a, b)| (a - b).abs());
        let scale = e.rows.iter().fold(0.0f32, |m, v| m.max(v.abs()));
        println!(
            "gpu encode {:.1} ms, sum {:.6}, max |cpu - gpu| {:.5} of max |value| {scale:.3}",
            took.as_secs_f64() * 1e3,
            g.rows.iter().map(|&v| v as f64).sum::<f64>(),
            diff.fold(0.0f32, |m, d| if d.is_nan() { f32::NAN } else { m.max(d) })
        );
    }
    Ok(())
}

fn rainbow(n: usize) -> Pixels {
    let c = n as f32 / 2.0;
    let max_dist = (2.0 * c * c).sqrt();
    let mut data = vec![0.0; 3 * n * n];
    for y in 0..n {
        for x in 0..n {
            let (dx, dy) = (x as f32 - c, y as f32 - c);
            let mut hue = dy.atan2(dx) / (2.0 * std::f32::consts::PI);
            if hue < 0.0 {
                hue += 1.0;
            }
            let sat = ((dx * dx + dy * dy).sqrt() / max_dist).min(1.0);
            let h6 = hue * 6.0;
            let f = h6 - h6.floor();
            let (p, q, t) = (1.0 - sat, 1.0 - sat * f, 1.0 - sat * (1.0 - f));
            let rgb = match h6 as usize % 6 {
                0 => [1.0, t, p],
                1 => [q, 1.0, p],
                2 => [p, 1.0, t],
                3 => [p, q, 1.0],
                4 => [t, p, 1.0],
                _ => [1.0, p, q],
            };
            for (ch, v) in rgb.into_iter().enumerate() {
                data[ch * n * n + y * n + x] = v;
            }
        }
    }
    Pixels {
        data,
        width: n,
        height: n,
    }
}
