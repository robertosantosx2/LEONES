//! A long message run ahead while it is written: the request after it
//! reuses nearly all of it and answers exactly as without Zero Wait.
//!
//! KINETIC_TEST_GGUF=LFM3-1.7B-Q4_K_M.gguf cargo test --release -p kinetic-server --test zero_wait -- --ignored
//!
//! With `--features cuda` and `KINETIC_TEST_DEVICE=cuda` it runs on the GPU.

use kinetic_gguf::GgufFile;
use kinetic_models::Model;
use kinetic_server::{Backend, Completion, CpuBackend, Engine, Request, Sampling};
use serde_json::{json, Map, Value};

fn backend<'m>(model: &'m Model<'m>) -> Box<dyn Backend + 'm> {
    #[cfg(feature = "cuda")]
    if std::env::var("KINETIC_TEST_DEVICE").is_ok_and(|d| d == "cuda") {
        return Box::new(kinetic_server::CudaBackend::new(model, 4096).unwrap());
    }
    Box::new(CpuBackend::new(model))
}

/// A short first turn, then a long second message, drafted first when
/// `ahead`; returns the second answer.
fn second_turn(engine: &Engine, ahead: bool) -> Completion {
    let request = Request {
        sampling: Sampling {
            temperature: 0.0,
            ..Sampling::default()
        },
        max_tokens: Some(24),
        stop: Vec::new(),
        grammar: None,
    };
    let options = Map::new();
    let complete = |messages: &[Value]| {
        let prompt = engine.chat_prompt(messages, &options).unwrap();
        engine
            .complete(&prompt, &request, &mut |_, _| true)
            .unwrap()
    };
    let mut messages = vec![json!({"role": "user", "content": "Hi, answer in one word."})];
    let first = complete(&messages);
    messages.push(json!({"role": "assistant", "content": first.content}));

    let file: String = (1..=60)
        .map(|i| format!("step {i}: read the next record, check its sum, write it out\n"))
        .collect();
    messages.push(json!({"role": "user", "content": format!("{file}What does this do?")}));
    if ahead {
        let draft = engine.draft_prompt(&messages, &options).unwrap();
        assert!(engine.prefill(&draft) > 0);
    }
    complete(&messages)
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn a_drafted_message_is_reused_by_its_request() {
    let path = std::env::var("KINETIC_TEST_GGUF").expect("set KINETIC_TEST_GGUF");
    let file = GgufFile::open(&path).unwrap();
    let model = kinetic_models::load(&file).unwrap();
    let engine = |zero_wait: bool| {
        let engine = Engine::new("m", file.header(), backend(&model), 4096).unwrap();
        if zero_wait {
            engine
        } else {
            engine.without_zero_wait()
        }
    };

    let cold = second_turn(&engine(false), false);
    let warm = second_turn(&engine(true), true);
    assert_eq!(warm.output_ids, cold.output_ids);
    let t = &warm.timings;
    assert!(t.prompt_tokens > 900, "{t:?}");
    // what runs at send is the last word, the reply's header and at most
    // one grid step of 32 tokens
    assert!(t.prompt_tokens - t.cached_tokens <= 48, "{t:?}");
}
