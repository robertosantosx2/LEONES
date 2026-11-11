//! Exactness of the GPU path on a real model: batches and rollbacks must not
//! change a single bit of the logits.
//!
//! KINETIC_TEST_GGUF=model.gguf cargo test --release -p kinetic-models --features cuda -- --ignored

#![cfg(feature = "cuda")]

use kinetic_gguf::GgufFile;
use kinetic_models::cuda::{CudaModel, CudaState, Placement, Run};

const PROMPT: [u32; 12] = [1, 400, 1000, 23, 5000, 77, 901, 12, 3333, 600, 45, 2024];
const NEXT: [u32; 6] = [300, 3000, 30, 7, 777, 90];

fn bits(x: &[f32]) -> Vec<u32> {
    x.iter().map(|v| v.to_bits()).collect()
}

/// One test, so one model on the device: capturing the decode graph on one
/// thread forbids other threads' synchronous copies in the same context.
#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn batches_and_rollbacks_change_no_bit() {
    let path = std::env::var("KINETIC_TEST_GGUF").expect("set KINETIC_TEST_GGUF");
    let file = GgufFile::open(&path).unwrap();
    let model = kinetic_models::load(&file).unwrap();
    let gpu = CudaModel::load(&model, 64).unwrap();
    a_batch_matches_token_by_token(&gpu);
    rollback_leaves_the_state_as_if_never_run(&gpu);
    a_host_copy_restores_the_state(&gpu, &model);
    shared_passes_match_running_alone(&gpu);
    let full = gpu.weight_bytes();
    drop(gpu);

    // Half the layers on the host, as when the device is too small.
    let layers = model.n_layers();
    let placement = Placement {
        gpu_layers: Some(layers / 2),
        ..Placement::default()
    };
    let split = CudaModel::load_with(&model, 64, placement).unwrap();
    assert_eq!(split.host_layers(), layers - layers / 2);
    a_batch_matches_token_by_token(&split);
    rollback_leaves_the_state_as_if_never_run(&split);
    a_host_copy_restores_the_state(&split, &model);
    drop(split);

    // A device with room for about half the weights.
    let placement = Placement {
        device_bytes: Some(full / 2),
        ..Placement::default()
    };
    let capped = CudaModel::load_with(&model, 64, placement).unwrap();
    assert!(capped.host_layers() > 0 && capped.host_layers() < layers);
    assert!(capped.weight_bytes() <= full / 2);
    a_batch_matches_token_by_token(&capped);
}

fn a_batch_matches_token_by_token(gpu: &CudaModel) {
    let vocab = gpu.n_vocab();
    let mut batched = gpu.new_state().unwrap();
    gpu.run(&mut batched, &PROMPT, false).unwrap();
    let all = gpu.run(&mut batched, &NEXT, true).unwrap().logits;

    let mut single = gpu.new_state().unwrap();
    gpu.run(&mut single, &PROMPT, false).unwrap();
    for (i, &t) in NEXT.iter().enumerate() {
        let logits = gpu.run(&mut single, &[t], false).unwrap().logits;
        assert_eq!(bits(&logits), bits(&all[i * vocab..][..vocab]), "row {i}");
    }
}

fn rollback_leaves_the_state_as_if_never_run(gpu: &CudaModel) {
    let mut rolled = gpu.new_state().unwrap();
    gpu.run(&mut rolled, &PROMPT, false).unwrap();
    gpu.checkpoint(&mut rolled).unwrap();
    gpu.run(&mut rolled, &NEXT, true).unwrap();
    gpu.rollback(&mut rolled, 2).unwrap();
    let after_rollback = gpu.run(&mut rolled, &[42], false).unwrap().logits;

    let mut plain = gpu.new_state().unwrap();
    gpu.run(&mut plain, &PROMPT, false).unwrap();
    gpu.run(&mut plain, &NEXT[..2], false).unwrap();
    let expected = gpu.run(&mut plain, &[42], false).unwrap().logits;
    assert_eq!(rolled.len(), plain.len());
    assert_eq!(bits(&after_rollback), bits(&expected));
}

fn a_host_copy_restores_the_state(gpu: &CudaModel, model: &kinetic_models::Model) {
    let mut state = gpu.new_state().unwrap();
    gpu.run(&mut state, &PROMPT, false).unwrap();
    let host = gpu.host_state(model, &state).unwrap();
    let mut restored = gpu.device_state(&host).unwrap();
    let expected = gpu.run(&mut state, &NEXT, true).unwrap().logits;
    let logits = gpu.run(&mut restored, &NEXT, true).unwrap().logits;
    assert_eq!(bits(&logits), bits(&expected));
}

/// Sequences sharing passes, one of them verifying a draft inside a
/// checkpoint, get exactly what each gets alone.
fn shared_passes_match_running_alone(gpu: &CudaModel) {
    let prompts: [&[u32]; 3] = [&PROMPT, &NEXT, &PROMPT[3..]];
    let fresh = || -> Vec<CudaState> {
        prompts
            .iter()
            .map(|p| {
                let mut s = gpu.new_state().unwrap();
                gpu.run(&mut s, p, false).unwrap();
                s
            })
            .collect()
    };
    let (mut shared, mut alone) = (fresh(), fresh());
    let steps: [[&[u32]; 3]; 3] = [
        [&[42], &[7, 8, 9, 10], &[5, 6]],
        [&[43], &[11], &[600]],
        [&[44, 45], &[12, 13], &[1000]],
    ];
    for (step, tokens) in steps.iter().enumerate() {
        for (i, s) in shared.iter_mut().chain(&mut alone).enumerate() {
            if i % 3 == 1 && step == 0 {
                gpu.checkpoint(s).unwrap();
            }
        }
        let all_rows = |i: usize| i == 1;
        let mut runs: Vec<Run> = shared
            .iter_mut()
            .zip(tokens)
            .enumerate()
            .map(|(i, (state, tokens))| Run {
                state,
                tokens,
                all_rows: all_rows(i),
                logits: i != 2,
            })
            .collect();
        let got = gpu.run_many(&mut runs).unwrap();
        for (i, ((state, tokens), ran)) in alone.iter_mut().zip(tokens).zip(&got).enumerate() {
            let want = gpu.run(state, tokens, all_rows(i)).unwrap();
            assert_eq!(
                bits(&ran.forward.hidden),
                bits(&want.hidden),
                "step {step} run {i}"
            );
            if i != 2 {
                assert_eq!(
                    bits(&ran.forward.logits),
                    bits(&want.logits),
                    "step {step} run {i}"
                );
            }
            let vocab = gpu.n_vocab();
            let best: Vec<u32> = want
                .logits
                .chunks_exact(vocab)
                .map(kinetic_models::speculative::argmax)
                .collect();
            assert_eq!(ran.greedy, best, "step {step} run {i}");
        }
        if step == 0 {
            gpu.rollback(&mut shared[1], 2).unwrap();
            gpu.rollback(&mut alone[1], 2).unwrap();
        }
    }
}

/// Where a prompt is cut into batches changes no bit, as long as the cuts
/// fall on the grid.
#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn prompt_cuts_change_no_bit() {
    let path = std::env::var("KINETIC_TEST_GGUF").expect("set KINETIC_TEST_GGUF");
    let file = GgufFile::open(&path).unwrap();
    let model = kinetic_models::load(&file).unwrap();
    let gpu = CudaModel::load(&model, 2048).unwrap();
    let vocab = gpu.n_vocab() as u32;
    let tokens: Vec<u32> = (0..1300u32).map(|i| (100 + i * 7919) % vocab).collect();
    let run_cut = |cuts: &[usize]| {
        let mut state = gpu.new_state().unwrap();
        let mut start = 0;
        let mut logits = Vec::new();
        for &end in cuts.iter().chain([&tokens.len()]) {
            logits = gpu
                .run(&mut state, &tokens[start..end], false)
                .unwrap()
                .logits;
            start = end;
        }
        bits(&logits)
    };
    let cold = run_cut(&[]);
    for cuts in [&[96][..], &[32, 640], &[1024], &[1280], &[704, 1216, 1248]] {
        assert_eq!(run_cut(cuts), cold, "{cuts:?}");
    }
}
