//! Projectors checked against llama.cpp's `llama-mtmd-debug -p encode
//! --image rainbow -n <size>` on the CPU.
//!
//! KINETIC_TEST_GEMMA4_MMPROJ=gemma-4-E2B-it-mmproj.gguf cargo test --release -p kinetic-vision -- --ignored

use kinetic_gguf::GgufFile;
use kinetic_vision::{Pixels, VisionEncoder};

/// The rainbow test pattern of `llama-mtmd-debug`, in `[0, 1]`.
fn rainbow(n: usize) -> Pixels {
    let c = n as f32 / 2.0;
    let max_dist = (2.0 * c * c).sqrt();
    let mut data = vec![0.0; 3 * n * n];
    for y in 0..n {
        for x in 0..n {
            let (dx, dy) = (x as f32 - c, y as f32 - c);
            let hue = (dy.atan2(dx) / std::f32::consts::TAU).rem_euclid(1.0);
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

#[test]
#[ignore = "needs KINETIC_TEST_GEMMA4_MMPROJ"]
fn gemma4v_matches_llama_cpp() {
    let path = std::env::var("KINETIC_TEST_GEMMA4_MMPROJ").expect("set KINETIC_TEST_GEMMA4_MMPROJ");
    let file = GgufFile::open(path).unwrap();
    let encoder = VisionEncoder::load(&file).unwrap();
    assert_eq!(encoder.n_embd_out(), 1536);
    let e = encoder.encode(&rainbow(480)).unwrap();
    assert_eq!((e.width, e.height), (10, 10));
    // llama.cpp b12001 on the CPU: first and last three values of the first
    // and last token, and the sum of all 153600; measured here within 0.005
    // and 0.07%
    let d = 1536;
    let want = [
        (0, [0.8253, 0.1405, 0.2044]),
        (d - 3, [0.7050, 0.2757, -0.2631]),
        (99 * d, [0.0481, 0.9376, -0.1774]),
        (100 * d - 3, [-0.3605, 0.0071, -0.4606]),
    ];
    for (at, values) in want {
        for (i, w) in values.into_iter().enumerate() {
            let got = e.rows[at + i];
            assert!((got - w).abs() < 1e-2, "value {}: {got} vs {w}", at + i);
        }
    }
    let sum: f64 = e.rows.iter().map(|&v| v as f64).sum();
    assert!((sum - -4539.47).abs() < 10.0, "sum {sum}");
}
