//! Drives the Ollama API over HTTP with a real model.
//!
//! KINETIC_TEST_GGUF=LFM3-1.7B-Q4_K_M.gguf cargo test --release -p kinetic-server --test ollama -- --ignored

use std::net::TcpListener;
use std::sync::OnceLock;

use kinetic_gguf::GgufFile;
use kinetic_models::Model;
use kinetic_server::{CpuBackend, Engine};
use serde_json::{json, Value};

fn base() -> &'static str {
    static BASE: OnceLock<String> = OnceLock::new();
    BASE.get_or_init(|| {
        let path = std::env::var("KINETIC_TEST_GGUF").expect("set KINETIC_TEST_GGUF");
        let file: &'static GgufFile = Box::leak(Box::new(GgufFile::open(path).unwrap()));
        let model: &'static Model = Box::leak(Box::new(kinetic_models::load(file).unwrap()));
        let backend = Box::new(CpuBackend::new(model));
        let engine: &'static Engine = Box::leak(Box::new(
            Engine::new("lfm3:test", file.header(), backend, 4096).unwrap(),
        ));
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let base = format!("http://{}", listener.local_addr().unwrap());
        std::thread::spawn(move || kinetic_server::serve(engine, listener));
        base
    })
}

fn get(path: &str) -> Value {
    ureq::get(&format!("{}{path}", base()))
        .call()
        .unwrap()
        .into_json()
        .unwrap()
}

fn post(path: &str, body: Value) -> ureq::Response {
    ureq::post(&format!("{}{path}", base()))
        .send_json(body)
        .unwrap()
}

/// The objects of an NDJSON stream.
fn lines(path: &str, body: Value) -> Vec<Value> {
    let response = post(path, body);
    assert_eq!(response.content_type(), "application/x-ndjson");
    let text = response.into_string().unwrap();
    text.lines()
        .map(|l| serde_json::from_str(l).unwrap())
        .collect()
}

fn greedy(n: u32) -> Value {
    json!({"temperature": 0, "top_k": 1, "num_predict": n})
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn version_tags_and_show() {
    assert!(get("/api/version")["version"].is_string());
    let tags = get("/api/tags");
    let m = &tags["models"][0];
    assert_eq!(m["name"], "lfm3:test");
    assert_eq!(m["details"]["format"], "gguf");
    assert_eq!(m["details"]["family"], "lfm3");
    assert_eq!(m["details"]["quantization_level"], "Q4_K_M");
    assert!(m["size"].as_u64().unwrap() > 0);
    let show: Value = post("/api/show", json!({"model": "lfm3:test"}))
        .into_json()
        .unwrap();
    assert!(show["capabilities"]
        .as_array()
        .unwrap()
        .contains(&json!("completion")));
    assert!(show["model_info"]["lfm3.context_length"].as_u64().unwrap() > 0);
    assert!(
        show["model_info"]["general.parameter_count"]
            .as_u64()
            .unwrap()
            > 1_000_000_000
    );
    assert!(show["template"].as_str().unwrap().contains("messages"));
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn chat_streams_the_same_text_it_answers_with() {
    let body = |stream: bool| {
        json!({"model": "lfm3:test", "messages": [{"role": "user", "content": "Name the capital of France."}],
               "stream": stream, "options": greedy(16)})
    };
    let whole: Value = post("/api/chat", body(false)).into_json().unwrap();
    let answer = whole["message"]["content"].as_str().unwrap();
    assert!(answer.contains("Paris"), "{answer}");
    assert_eq!(whole["done"], true);
    assert_eq!(whole["message"]["role"], "assistant");
    for key in [
        "total_duration",
        "prompt_eval_count",
        "eval_count",
        "eval_duration",
    ] {
        assert!(whole[key].as_u64().unwrap() > 0, "{key}");
    }

    let pieces = lines("/api/chat", body(true));
    let (last, rest) = pieces.split_last().unwrap();
    let streamed: String = rest
        .iter()
        .map(|p| {
            assert_eq!(p["done"], false);
            p["message"]["content"].as_str().unwrap()
        })
        .collect();
    assert_eq!(streamed, answer);
    assert_eq!(last["done"], true);
    assert_eq!(last["message"]["content"], "");
    assert_eq!(last["eval_count"], whole["eval_count"]);
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn generate_stops_at_num_predict_and_follows_a_schema() {
    let pieces = lines(
        "/api/generate",
        json!({"model": "x", "prompt": "Count to twenty.", "options": greedy(5)}),
    );
    let last = pieces.last().unwrap();
    assert_eq!(last["done_reason"], "length");
    assert_eq!(last["eval_count"], 5);

    let schema =
        json!({"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]});
    let r: Value = post(
        "/api/generate",
        json!({"model": "x", "prompt": "Which city is the capital of Italy? Answer in JSON.",
               "stream": false, "format": schema, "options": greedy(40)}),
    )
    .into_json()
    .unwrap();
    let answer: Value = serde_json::from_str(r["response"].as_str().unwrap()).unwrap();
    assert!(answer["city"].is_string(), "{answer}");

    let loaded: Value = post("/api/generate", json!({"model": "x"}))
        .into_json()
        .unwrap();
    assert_eq!(loaded["done_reason"], "load");
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn chat_calls_tools_with_object_arguments() {
    let tools = json!([{"type": "function", "function": {
        "name": "get_weather",
        "description": "Get the current weather in a city",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
    }}]);
    let r: Value = post(
        "/api/chat",
        json!({"model": "x", "stream": false, "tools": tools, "options": greedy(64),
               "messages": [{"role": "user", "content": "What is the weather in Paris?"}]}),
    )
    .into_json()
    .unwrap();
    let call = &r["message"]["tool_calls"][0]["function"];
    assert_eq!(call["name"], "get_weather", "{r}");
    assert!(call["arguments"]["city"].is_string(), "{r}");
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn errors_have_the_ollama_shape() {
    let r =
        ureq::post(&format!("{}/api/embed", base())).send_json(json!({"model": "x", "input": "a"}));
    let Err(ureq::Error::Status(400, response)) = r else {
        panic!("expected a 400")
    };
    let body: Value = response.into_json().unwrap();
    assert!(body["error"].as_str().unwrap().contains("embedding model"));
    let r = ureq::post(&format!("{}/api/pull", base())).send_json(json!({"model": "x"}));
    assert!(matches!(r, Err(ureq::Error::Status(404, _))));
}
