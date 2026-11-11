//! Speculative decoding and warm starts in the backends must not change a
//! single token: greedy requests match plain greedy decoding and seeded
//! sampled ones match plain seeded sampling, on a fresh sequence, on one
//! extended from the cache and on one resumed from the prompt cache.
//!
//! KINETIC_TEST_GGUF=Qwen3-0.6B-Q8_0.gguf cargo test --release -p kinetic-server --test backend -- --ignored
//!
//! With `--features cuda` the GPU backend is checked against plain decoding
//! on the GPU as well.

use kinetic_gguf::GgufFile;
use kinetic_models::warm::{self, Warm};
use kinetic_server::{Backend, CpuBackend, Job, Logprobs, Sampling};
use kinetic_tokenizer::Tokenizer;

fn generate(backend: &mut dyn Backend, prompt: &[u32], sampling: &Sampling) -> Vec<u32> {
    generate_logged(backend, prompt, sampling, None)
}

fn generate_logged(
    backend: &mut dyn Backend,
    prompt: &[u32],
    sampling: &Sampling,
    logprobs: Option<&Logprobs>,
) -> Vec<u32> {
    let job = Job {
        sampling,
        max_tokens: 48,
        stop_tokens: &[],
        grammar: None,
        images: &[],
        logprobs,
    };
    let mut out = Vec::new();
    backend.generate(prompt, &job, &mut |t| {
        out.extend_from_slice(t);
        true
    });
    out
}

fn settings() -> [Sampling; 3] {
    [
        Sampling {
            temperature: 0.0,
            ..Sampling::default()
        },
        Sampling {
            seed: Some(1),
            ..Sampling::default()
        },
        Sampling {
            temperature: 1.2,
            top_k: 0,
            top_p: 0.9,
            min_p: 0.0,
            repeat_penalty: 1.3,
            presence_penalty: 0.2,
            frequency_penalty: 0.1,
            seed: Some(7),
            ..Sampling::default()
        },
    ]
}

fn model_file() -> (String, GgufFile, Tokenizer) {
    let path = std::env::var("KINETIC_TEST_GGUF").expect("set KINETIC_TEST_GGUF");
    let file = GgufFile::open(&path).unwrap();
    let tokenizer = Tokenizer::from_gguf(file.header()).unwrap();
    (path, file, tokenizer)
}

const CODE: &str =
    "fn add(a: i32, b: i32) -> i32 { a + b }\nfn sub(a: i32, b: i32) -> i32 { a - b }\n\
                    fn mul(a: i32, b: i32) -> i32 { a * b }\nfn div(a: i32, b: i32) -> i32 {";

/// Each sampler on its own, over settings that let drafts through.
fn samplers() -> Vec<Sampling> {
    let base = Sampling {
        temperature: 0.7,
        seed: Some(3),
        ..Sampling::default()
    };
    vec![
        Sampling {
            logit_bias: vec![(13, 1.5), (220, f32::NEG_INFINITY)],
            ..base.clone()
        },
        Sampling {
            dry_multiplier: 0.8,
            dry_breaker_tokens: vec![(198, Vec::new())],
            ..base.clone()
        },
        Sampling {
            xtc_probability: 0.5,
            xtc_threshold: 0.1,
            ..base.clone()
        },
        Sampling {
            typical_p: 0.8,
            ..base.clone()
        },
        Sampling {
            top_n_sigma: 1.5,
            top_k: 0,
            ..base.clone()
        },
        Sampling {
            mirostat: 1,
            ..base.clone()
        },
        Sampling {
            mirostat: 2,
            ..base.clone()
        },
    ]
}

/// Checks `fast` against `plain` on a prompt and on its continuation.
fn check_drafting(fast: &mut dyn Backend, plain: &mut dyn Backend, tokenizer: &Tokenizer) {
    let prompt = tokenizer.encode(CODE, true);
    for sampling in &samplers() {
        let (a, b) = (Logprobs::new(5), Logprobs::new(5));
        let tokens = generate_logged(fast, &prompt, sampling, Some(&a));
        assert_eq!(
            tokens,
            generate_logged(plain, &prompt, sampling, Some(&b)),
            "{sampling:?}"
        );
        assert_eq!(a.range(0, 48), b.range(0, 48), "{sampling:?}");
    }
    for sampling in &settings() {
        let a = generate(fast, &prompt, sampling);
        assert_eq!(a, generate(plain, &prompt, sampling), "{sampling:?}");

        let mut longer = prompt.clone();
        longer.extend_from_slice(&a[..a.len() - 1]);
        longer.extend(tokenizer.encode("\nfn rem(a: i32, b: i32) -> i32 {", false));
        let b = generate(fast, &longer, sampling);
        assert_eq!(b, generate(plain, &longer, sampling), "{sampling:?}");
    }
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn drafting_changes_no_token() {
    let (_, file, tokenizer) = model_file();
    let model = kinetic_models::load(&file).unwrap();
    check_drafting(
        &mut CpuBackend::new(&model),
        &mut CpuBackend::plain(&model),
        &tokenizer,
    );
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn warm_starts_change_no_token() {
    let (path, file, tokenizer) = model_file();
    let model = kinetic_models::load(&file).unwrap();
    let id = warm::model_id(&path).unwrap();
    let dir = std::env::temp_dir().join(format!("kinetic-warm-test-{}", std::process::id()));
    let warm_backend = || {
        let warm = Warm::new(&model, id, 1 << 30)
            .with_disk(&dir, 1 << 30)
            .unwrap();
        CpuBackend::new(&model).with_warm(warm)
    };
    let mut cold = CpuBackend::new(&model);

    // Long enough that recurrent models resume from marks inside it.
    let system = CODE.repeat(12);
    let prompts: Vec<Vec<u32>> = [
        "\nfn rem(a: i32, b: i32) -> i32 {",
        "\nfn neg(a: i32) -> i32 {",
    ]
    .iter()
    .map(|tail| tokenizer.encode(&format!("{system}{tail}"), true))
    .collect();
    let mut warm = warm_backend();
    for sampling in &settings() {
        for prompt in &prompts {
            let expected = generate(&mut cold, prompt, sampling);
            assert_eq!(
                generate(&mut warm, prompt, sampling),
                expected,
                "{sampling:?}"
            );
        }
    }
    // A new process finds the states on disk.
    let mut restarted = warm_backend();
    let sampling = &settings()[0];
    let expected = generate(&mut cold, &prompts[1], sampling);
    assert_eq!(generate(&mut restarted, &prompts[1], sampling), expected);
    std::fs::remove_dir_all(&dir).unwrap();
}

#[cfg(feature = "cuda")]
mod gpu {
    use super::*;
    use kinetic_models::cuda::CudaModel;
    use kinetic_models::speculative::{Greedy, Policy, Sampler};
    use kinetic_server::CudaBackend;

    /// Runs the prompt, then one token per pass.
    fn plain<'m, P: Policy<CudaModel<'m>>>(
        gpu: &CudaModel<'m>,
        policy: &mut P,
        prompt: &[u32],
    ) -> Vec<u32> {
        let mut state = gpu.new_state().unwrap();
        let mut context = prompt.to_vec();
        let (mut scores, _) = policy.score(gpu, &mut state, prompt, false);
        while context.len() - prompt.len() < 48 {
            let t = policy.choose(gpu, &scores, 0, &context);
            context.push(t);
            scores = policy.score(gpu, &mut state, &[t], false).0;
        }
        context.split_off(prompt.len())
    }

    fn plain_for(gpu: &CudaModel, sampling: &Sampling, prompt: &[u32]) -> Vec<u32> {
        if sampling.is_greedy() {
            plain(gpu, &mut Greedy, prompt)
        } else {
            plain(gpu, &mut Sampler::new(sampling.clone()), prompt)
        }
    }

    /// One test, and one model on the device at a time.
    #[test]
    #[ignore = "needs KINETIC_TEST_GGUF and a CUDA device"]
    fn gpu_drafting_changes_no_token() {
        let (_, file, tokenizer) = model_file();
        let model = kinetic_models::load(&file).unwrap();
        let prompt = tokenizer.encode(CODE, true);
        let gpu = CudaModel::load(&model, 1024).unwrap();
        let cases: Vec<_> = settings()
            .into_iter()
            .map(|sampling| {
                let first = plain_for(&gpu, &sampling, &prompt);
                let mut longer = prompt.clone();
                longer.extend_from_slice(&first[..first.len() - 1]);
                longer.extend(tokenizer.encode(
                    "
fn rem(a: i32, b: i32) -> i32 {",
                    false,
                ));
                let second = plain_for(&gpu, &sampling, &longer);
                (sampling, first, longer, second)
            })
            .collect();
        drop(gpu);

        let mut fast = CudaBackend::new(&model, 1024).unwrap();
        for (sampling, first, longer, second) in &cases {
            assert_eq!(
                &generate(&mut fast, &prompt, sampling),
                first,
                "{sampling:?}"
            );
            assert_eq!(
                &generate(&mut fast, longer, sampling),
                second,
                "{sampling:?}"
            );
        }
    }

    #[test]
    #[ignore = "needs KINETIC_TEST_GGUF and a CUDA device"]
    fn gpu_running_ahead_changes_no_token() {
        let (path, file, tokenizer) = model_file();
        let model = kinetic_models::load(&file).unwrap();
        let id = warm::device_id(warm::model_id(&path).unwrap(), "cuda");
        let run = |ahead: bool| {
            let mut backend =
                CudaBackend::new(&model, 8192)
                    .unwrap()
                    .with_warm(Warm::new(&model, id, 1 << 30));
            chat_typed(&mut backend, &tokenizer, ahead)
        };
        let plain = run(false);
        assert_eq!(run(true), plain);
    }

    /// Every turn of a chat continued from the cache gives what the whole
    /// conversation gives run cold.
    #[test]
    #[ignore = "needs KINETIC_TEST_GGUF and a CUDA device"]
    fn gpu_chat_continues_like_a_cold_run() {
        let (_, file, tokenizer) = model_file();
        let model = kinetic_models::load(&file).unwrap();
        let turns: Vec<Vec<u32>> = [
            CODE.repeat(5),
            CODE.repeat(2),
            "
fn neg(a: i32) -> i32 {"
                .into(),
            CODE.repeat(9),
            CODE.into(),
        ]
        .iter()
        .enumerate()
        .map(|(i, text)| {
            tokenizer.encode(
                &format!(
                    "{text}
fn f{i}(a: i32) -> i32 {{"
                ),
                i == 0,
            )
        })
        .collect();
        let settings = settings();
        let gpu = CudaModel::load(&model, 4096).unwrap();
        let chats: Vec<_> = [&settings[0], &settings[2]]
            .into_iter()
            .map(|sampling| {
                let mut prompt = Vec::new();
                let mut chat = Vec::new();
                for turn in &turns {
                    prompt.extend_from_slice(turn);
                    let answer = plain_for(&gpu, sampling, &prompt);
                    chat.push((prompt.clone(), answer.clone()));
                    prompt.extend_from_slice(&answer[..answer.len() - 1]);
                }
                (sampling, chat)
            })
            .collect();
        drop(gpu);

        let mut backend = CudaBackend::new(&model, 4096).unwrap();
        for (sampling, chat) in &chats {
            for (turn, (prompt, answer)) in chat.iter().enumerate() {
                assert!(turn == 0 || backend.reuses(prompt) > 0, "turn {turn}");
                assert_eq!(
                    &generate(&mut backend, prompt, sampling),
                    answer,
                    "turn {turn}, {sampling:?}"
                );
            }
        }
    }
}

/// Two turns of a chat about a long prompt, every request after drafts of
/// it when `ahead`: growing as if typed, and one edited inside what already
/// ran ahead. Returns every answer.
fn chat_typed(backend: &mut dyn Backend, tokenizer: &Tokenizer, ahead: bool) -> Vec<Vec<u32>> {
    let system = CODE.repeat(24);
    let mut answers = Vec::new();
    for sampling in &settings() {
        let first = tokenizer.encode(&format!("{system}\nfn rem(a: i32, b: i32) -> i32 {{"), true);
        if ahead {
            type_ahead(backend, &first);
        }
        let a = generate(backend, &first, sampling);
        let mut second = first.clone();
        second.extend_from_slice(&a[..a.len() - 1]);
        second.extend(tokenizer.encode(&format!("\n{system}\nfn neg(a: i32) -> i32 {{"), false));
        if ahead {
            type_ahead(backend, &second[..second.len() - 5]);
            let mut edited = second.clone();
            edited[first.len() + a.len() + 700] = second[0];
            type_ahead(backend, &edited);
            type_ahead(backend, &second);
        }
        answers.push(a);
        answers.push(generate(backend, &second, sampling));
    }
    answers
}

/// Runs `prompt` ahead on `backend` as if typed, a few tokens at a time.
fn type_ahead(backend: &mut dyn Backend, prompt: &[u32]) {
    for end in (97..prompt.len()).step_by(97).chain([prompt.len()]) {
        let mut last = None;
        loop {
            let ran = backend.run_ahead(&prompt[..end]);
            if last == Some(ran) {
                break;
            }
            last = Some(ran);
        }
    }
}

const TAILS: [&str; 3] = [
    "
fn rem(a: i32, b: i32) -> i32 {",
    "
fn neg(a: i32) -> i32 {",
    "
fn abs(a: i32) -> i32 {",
];

/// Turns of a chat whose template writes every reply differently from how
/// it was generated, as reasoning models' templates do, so each prompt
/// leaves the cached sequence two tokens before the end of the previous
/// one. Returns every answer and the prompt tokens each request reused.
fn chat_rewritten(
    backend: &mut dyn Backend,
    tokenizer: &Tokenizer,
    sampling: &Sampling,
    ahead: bool,
) -> (Vec<Vec<u32>>, Vec<usize>) {
    let job = Job {
        sampling,
        max_tokens: 24,
        stop_tokens: &[],
        grammar: None,
        images: &[],
        logprobs: None,
    };
    let mut prompt = tokenizer.encode(&CODE.repeat(9), true);
    let (mut answers, mut reused) = (Vec::new(), Vec::new());
    for tail in TAILS {
        prompt.extend(tokenizer.encode(&format!("{tail}{CODE}"), false));
        if ahead {
            type_ahead(backend, &prompt);
        }
        let mut answer = Vec::new();
        let t = backend.generate(&prompt, &job, &mut |t| {
            answer.extend_from_slice(t);
            true
        });
        reused.push(t.cached_tokens);
        answers.push(answer);
        prompt.truncate(prompt.len() - 2);
    }
    (answers, reused)
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn rewritten_turns_resume_before_the_reply() {
    let (_, file, tokenizer) = model_file();
    let model = kinetic_models::load(&file).unwrap();
    for sampling in &settings()[..2] {
        let mut cold = Vec::new();
        let mut prompt = tokenizer.encode(&CODE.repeat(9), true);
        for tail in TAILS {
            prompt.extend(tokenizer.encode(&format!("{tail}{CODE}"), false));
            let mut fresh = CpuBackend::new(&model);
            let mut answer = generate(&mut fresh, &prompt, sampling);
            answer.truncate(24);
            cold.push(answer);
            prompt.truncate(prompt.len() - 2);
        }
        for ahead in [false, true] {
            let mut backend = CpuBackend::new(&model);
            let (answers, reused) = chat_rewritten(&mut backend, &tokenizer, sampling, ahead);
            assert_eq!(answers, cold, "{sampling:?} ahead {ahead}");
            assert!(reused[1..].iter().all(|&r| r >= 256), "{reused:?}");
        }
    }
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn running_ahead_changes_no_token() {
    let (path, file, tokenizer) = model_file();
    let model = kinetic_models::load(&file).unwrap();
    let id = warm::model_id(&path).unwrap();
    let backend = || CpuBackend::new(&model).with_warm(Warm::new(&model, id, 1 << 30));
    let plain = chat_typed(&mut backend(), &tokenizer, false);
    assert_eq!(chat_typed(&mut backend(), &tokenizer, true), plain);
}
