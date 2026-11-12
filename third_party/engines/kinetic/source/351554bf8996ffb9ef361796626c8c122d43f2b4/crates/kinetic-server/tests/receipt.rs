//! A receipt made on a busy engine, four requests at once with drafting on,
//! each with other samplers and one with logprobs, reruns to the same
//! tokens on an idle engine with drafting off; edited receipts fail.
//!
//! KINETIC_TEST_GGUF=LFM3-1.7B-Q4_K_M.gguf cargo test --release -p kinetic-server --test receipt -- --ignored

use kinetic_gguf::GgufFile;
use kinetic_server::receipt::Device;
use kinetic_server::{
    Backend, CpuBackend, Engine, Logprobs, Prompt, Receipt, Receipts, Request, Sampling,
};
use serde_json::{json, Map};

const QUESTIONS: [&str; 4] = [
    "Name a color and a fruit of that color.",
    "Write one sentence about the sea.",
    "What is 17 times 3? Explain briefly.",
    "Give a short tip for learning to cook.",
];

fn request(i: usize) -> Request {
    let plain = Sampling {
        temperature: 0.8,
        seed: Some(100 + i as u64),
        ..Sampling::default()
    };
    let sampling = match i {
        0 => plain,
        1 => Sampling {
            dry_multiplier: 0.8,
            xtc_probability: 0.5,
            presence_penalty: 0.4,
            frequency_penalty: 0.2,
            ..plain
        },
        2 => Sampling {
            typical_p: 0.8,
            top_n_sigma: 1.5,
            logit_bias: vec![(22, -2.0)],
            ..plain
        },
        _ => Sampling {
            mirostat: 2,
            ..plain
        },
    };
    Request {
        sampling,
        max_tokens: Some(40),
        stop: Vec::new(),
        grammar: None,
    }
}

fn rerun(engine: &Engine, r: &Receipt) -> Receipt {
    let request = r.request().unwrap();
    let c = engine
        .complete_tokens(
            r.prompt.ids.clone(),
            &Prompt::raw(""),
            &request,
            None,
            &mut |_, _| true,
        )
        .unwrap();
    let receipts = engine.receipts().unwrap();
    receipts.make(r.input.clone(), None, &request, &c).unwrap()
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn busy_receipts_verify_alone_without_drafts() {
    let path = std::env::var("KINETIC_TEST_GGUF").expect("set KINETIC_TEST_GGUF");
    let file = GgufFile::open(&path).unwrap();
    let model = kinetic_models::load(&file).unwrap();
    let receipts = || Receipts::new(&path, Device::cpu());

    let busy: Vec<Box<dyn Backend>> = (0..QUESTIONS.len())
        .map(|_| Box::new(CpuBackend::new(&model)) as Box<dyn Backend>)
        .collect();
    let mut busy = busy.into_iter();
    let first = busy.next().unwrap();
    let busy = Engine::new("m", file.header(), first, 4096)
        .unwrap()
        .with_backends(busy)
        .with_receipts(receipts().signed_with([3; 32]));
    let made: Vec<Receipt> = std::thread::scope(|s| {
        let runs: Vec<_> = QUESTIONS
            .iter()
            .enumerate()
            .map(|(i, q)| {
                let busy = &busy;
                s.spawn(move || {
                    let messages = [json!({"role": "user", "content": q})];
                    let prompt = busy.chat_prompt(&messages, &Map::new()).unwrap();
                    let request = request(i);
                    let logprobs = (i == 0).then(|| Logprobs::new(2));
                    let c = busy
                        .complete_with_logprobs(
                            &prompt,
                            &request,
                            logprobs.as_ref(),
                            &mut |_, _| true,
                        )
                        .unwrap();
                    if let Some(l) = &logprobs {
                        let n = l.range(0, usize::MAX).len();
                        assert!(n > 0 && n <= c.completion_tokens);
                    }
                    let receipts = busy.receipts().unwrap();
                    receipts.make(json!(messages), None, &request, &c).unwrap()
                })
            })
            .collect();
        runs.into_iter().map(|r| r.join().unwrap()).collect()
    });

    let alone = CpuBackend::new(&model).without_drafts();
    let alone = Engine::new("m", file.header(), Box::new(alone), 4096)
        .unwrap()
        .with_receipts(receipts());
    for r in &made {
        let r = Receipt::parse(&r.to_json()).unwrap();
        assert!(r.check().unwrap().is_some(), "signed");
        assert!(r.output.tokens.count > 0);
        let cmp = r.compare(&rerun(&alone, &r));
        assert_eq!(cmp.first_difference, None);
        assert!(cmp.reasons.is_empty(), "{:?}", cmp.reasons);
    }

    let mut edited = made[0].clone();
    edited.sampling.seed += 1;
    assert!(
        edited.check().is_err(),
        "a signed receipt with another seed"
    );
    edited.signature = None;
    assert!(edited.check().is_ok());
    let cmp = edited.compare(&rerun(&alone, &edited));
    assert!(cmp.first_difference.is_some(), "another seed, other tokens");

    let mut edited = made[1].clone();
    edited.signature = None;
    edited.output.tokens.ids[0] ^= 1;
    assert!(edited.check().is_err(), "edited tokens fail their hash");
}
