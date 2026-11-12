//! Image rows in a prompt on the GPU against the CPU, on a real model, with
//! text before and after the image and a few decode steps past it. The two
//! devices round differently, so the gap is measured against the one plain
//! text has.
//!
//! KINETIC_TEST_GGUF=model.gguf cargo test --release -p kinetic-models --features cuda --test cuda_image -- --ignored

#![cfg(feature = "cuda")]

use kinetic_gguf::GgufFile;
use kinetic_models::cuda::CudaModel;
use kinetic_models::Input;

const NEXT: [u32; 4] = [12, 3333, 600, 45];

fn gap(cpu: &[f32], gpu: &[f32]) -> f32 {
    cpu.iter()
        .zip(gpu)
        .fold(0.0f32, |m, (a, b)| m.max((a - b).abs()))
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn image_rows_match_the_cpu() {
    let path = std::env::var("KINETIC_TEST_GGUF").expect("set KINETIC_TEST_GGUF");
    let file = GgufFile::open(&path).unwrap();
    let model = kinetic_models::load(&file).unwrap();
    let gpu = CudaModel::load(&model, 128).unwrap();
    assert!(gpu.takes_images());

    // 8x6 rows: more than one small batch, so the full prefill buffers run
    let (w, h, d) = (8, 6, model.n_embd());
    let mut seed = 7u32;
    let rows: Vec<f32> = (0..w * h * d)
        .map(|_| {
            seed = seed.wrapping_mul(1664525).wrapping_add(1013904223);
            ((seed >> 8) as f32 / (1 << 24) as f32 - 0.5) * 0.1
        })
        .collect();
    let before = [1u32, 400, 1000, 23];
    let after = [5000u32, 77, 901];
    let inputs = [
        Input::Tokens(&before),
        Input::Image {
            rows: &rows,
            width: w,
            height: h,
        },
        Input::Tokens(&after),
    ];

    let text = [1u32, 400, 1000, 23, 5000, 77, 901];
    let mut cpu = model.new_state();
    let mut dev = gpu.new_state().unwrap();
    model.run(&mut cpu, &text, false);
    gpu.run(&mut dev, &text, false).unwrap();
    let mut text_gap = 0.0f32;
    for token in NEXT {
        let c = model.run(&mut cpu, &[token], false).logits;
        let g = gpu.run(&mut dev, &[token], false).unwrap().logits;
        text_gap = text_gap.max(gap(&c, &g));
    }

    let mut cpu = model.new_state();
    model.run_inputs(&mut cpu, &inputs, false);
    let mut dev = gpu.new_state().unwrap();
    gpu.run_inputs(&mut dev, &inputs).unwrap();
    for token in NEXT {
        let c = model.run(&mut cpu, &[token], false).logits;
        let g = gpu.run(&mut dev, &[token], false).unwrap().logits;
        // measured on Qwen3.5-4B Q4_K_M: text 0.58, image 1.22 of ~10
        let image_gap = gap(&c, &g);
        assert!(
            image_gap < 3.0 * text_gap,
            "{image_gap} vs {text_gap} for text"
        );
    }
}
