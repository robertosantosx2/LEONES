use half::f16;
use kinetic_cpu::matmul;
use kinetic_quant::{Matrix, TensorType};

use super::{highest, Shortlist};

const ROWS: usize = 512;
const COLS: usize = 256;

fn q8_0(values: &[f32]) -> Vec<u8> {
    values
        .chunks_exact(32)
        .flat_map(|b| {
            let d = b.iter().fold(0.0f32, |m, v| m.max(v.abs())) / 127.0;
            let d = f16::from_f32(d);
            let inv = 1.0 / d.to_f32();
            d.to_le_bytes()
                .into_iter()
                .chain(b.iter().map(move |v| (v * inv).round() as i8 as u8))
        })
        .collect()
}

fn noise(seed: &mut u64) -> f32 {
    *seed = seed
        .wrapping_mul(6364136223846793005)
        .wrapping_add(1442695040888963407);
    (*seed >> 40) as f32 / (1u64 << 24) as f32 * 2.0 - 1.0
}

/// A head whose rows 200 and 201 repeat rows 7 and 3, and activations
/// close to rows 3 and 7, so the highest logits come in tied pairs.
fn setup(tokens: usize) -> (Vec<u8>, Vec<f32>) {
    let mut seed = 1;
    let mut w: Vec<f32> = (0..ROWS * COLS).map(|_| noise(&mut seed)).collect();
    w.copy_within(7 * COLS..8 * COLS, 200 * COLS);
    w.copy_within(3 * COLS..4 * COLS, 201 * COLS);
    let x = (0..tokens)
        .flat_map(|t| {
            let w = &w;
            let mut seed = 100 + t as u64;
            (0..COLS)
                .map(move |i| w[3 * COLS + i] + w[7 * COLS + i] * (0.8 + 0.1 * t as f32))
                .map(move |v| v + 0.3 * noise(&mut seed))
                .collect::<Vec<_>>()
        })
        .collect();
    (q8_0(&w), x)
}

#[test]
fn highest_logits_match_the_full_head() {
    for tokens in [1, 3] {
        let (data, x) = setup(tokens);
        let head = Matrix::new(TensorType::Q8_0, &data, ROWS, COLS);
        let mut full = vec![0.0; tokens * ROWS];
        matmul(&head, &x, &mut full);
        let shortlist = Shortlist::build(&head).unwrap();
        for top in [1, 2, 5] {
            let short = shortlist.logits(&head, &x, top).unwrap();
            for (full, short) in full.chunks_exact(ROWS).zip(short.chunks_exact(ROWS)) {
                let want = highest(ROWS, top, |i| full[i]);
                assert_eq!(highest(ROWS, top, |i| short[i]), want);
                for (f, s) in full.iter().zip(short) {
                    assert!(*s == f32::NEG_INFINITY || s == f);
                }
                assert!(short.iter().filter(|v| v.is_finite()).count() < ROWS / 4);
            }
        }
    }
}

#[test]
fn ties_go_to_the_lower_index() {
    let values = [1.0, 3.0, 2.0, 3.0, f32::NEG_INFINITY, 2.0];
    assert_eq!(highest(values.len(), 4, |i| values[i]), [1, 3, 2, 5]);
    assert_eq!(highest(values.len(), 9, |i| values[i]), [1, 3, 2, 5, 0, 4]);
}
