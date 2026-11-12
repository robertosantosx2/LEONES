//! Requests that run at once share passes over the weights, yet each must
//! come out exactly as it does alone: greedy and seeded, short and long
//! prompts, joining late, and with one cancelled part-way.
//!
//! KINETIC_TEST_GGUF=LFM3-1.7B-Q4_K_M.gguf cargo test --release -p kinetic-server --test convoy -- --ignored
//!
//! With `--features cuda` the same holds for slots of one GPU backend.

use std::time::Duration;

use kinetic_gguf::GgufFile;
use kinetic_server::{Backend, CpuBackend, Job, Sampling};
use kinetic_tokenizer::Tokenizer;

struct Case {
    prompt: Vec<u32>,
    sampling: Sampling,
    max_tokens: usize,
    /// Stops reading after this many tokens, as a client that goes away.
    cancel_after: Option<usize>,
    /// Arrives this long after the others.
    late: Duration,
}

fn generate(backend: &mut dyn Backend, case: &Case) -> Vec<u32> {
    let job = Job {
        sampling: &case.sampling,
        max_tokens: case.max_tokens,
        stop_tokens: &[],
        grammar: None,
        images: &[],
        logprobs: None,
    };
    let mut out = Vec::new();
    backend.generate(&case.prompt, &job, &mut |t| {
        out.extend_from_slice(t);
        case.cancel_after.is_none_or(|n| out.len() < n)
    });
    out
}

fn cases(tokenizer: &Tokenizer) -> Vec<Case> {
    let code: String = (0..40)
        .map(|i| format!("fn f{i}(a: i32) -> i32 {{ a * {i} + {} }}\n", i % 7))
        .collect();
    let greedy = Sampling {
        temperature: 0.0,
        ..Sampling::default()
    };
    let seeded = Sampling {
        temperature: 1.1,
        top_k: 0,
        top_p: 0.9,
        repeat_penalty: 1.2,
        seed: Some(7),
        ..Sampling::default()
    };
    let case = |text: &str, sampling: &Sampling, max_tokens| Case {
        prompt: tokenizer.encode(text, true),
        sampling: sampling.clone(),
        max_tokens,
        cancel_after: None,
        late: Duration::ZERO,
    };
    vec![
        case(&format!("{code}fn f40(a: i32) -> i32 {{"), &greedy, 64),
        case("Once upon a time, in a quiet village,", &seeded, 40),
        Case {
            cancel_after: Some(9),
            ..case("The three laws of motion are", &greedy, 80)
        },
        Case {
            late: Duration::from_millis(300),
            ..case("List the planets of the solar system:", &seeded, 24)
        },
    ]
}

/// Runs every case on its own backend, all at once, and checks each
/// against running it alone on the first.
fn check(mut backends: Vec<Box<dyn Backend + '_>>, cases: &[Case]) {
    let alone: Vec<Vec<u32>> = cases
        .iter()
        .map(|c| generate(&mut *backends[0], c))
        .collect();
    let together: Vec<Vec<u32>> = std::thread::scope(|s| {
        let runs: Vec<_> = cases
            .iter()
            .zip(&mut backends)
            .map(|(c, backend)| {
                s.spawn(move || {
                    std::thread::sleep(c.late);
                    generate(&mut **backend, c)
                })
            })
            .collect();
        runs.into_iter().map(|r| r.join().unwrap()).collect()
    });
    for (i, (a, t)) in alone.iter().zip(&together).enumerate() {
        assert!(!a.is_empty());
        assert_eq!(a, t, "request {i}");
    }
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn requests_at_once_match_each_alone() {
    let path = std::env::var("KINETIC_TEST_GGUF").expect("set KINETIC_TEST_GGUF");
    let file = GgufFile::open(&path).unwrap();
    let tokenizer = Tokenizer::from_gguf(file.header()).unwrap();
    let model = kinetic_models::load(&file).unwrap();
    let cases = cases(&tokenizer);

    let cpu = (0..cases.len())
        .map(|_| Box::new(CpuBackend::new(&model)) as Box<dyn Backend>)
        .collect();
    check(cpu, &cases);

    #[cfg(feature = "cuda")]
    {
        let gpu = kinetic_server::CudaBackend::new(&model, 2048).unwrap();
        // as many slots as fit beside whatever else is on the device
        let mut slots: Vec<Box<dyn Backend>> = (1..cases.len())
            .map_while(|_| gpu.slot().ok())
            .map(|slot| Box::new(slot) as Box<dyn Backend>)
            .collect();
        assert!(!slots.is_empty(), "no room on the device for a second slot");
        slots.insert(0, Box::new(gpu));
        let n = slots.len();
        check(slots, &cases[..n]);
    }
}
