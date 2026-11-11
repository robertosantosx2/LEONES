//! Drives `/v1/embeddings` over HTTP with a real embedding model.
//!
//! KINETIC_TEST_EMBED_GGUF=bge-small-en-v1.5-f16.gguf cargo test --release -p kinetic-server --test embeddings -- --ignored

use std::net::TcpListener;
use std::sync::OnceLock;

use kinetic_gguf::GgufFile;
use kinetic_models::Embedder;
use kinetic_server::Embeddings;
use serde_json::{json, Value};

fn base() -> &'static str {
    static BASE: OnceLock<String> = OnceLock::new();
    BASE.get_or_init(|| {
        let path = std::env::var("KINETIC_TEST_EMBED_GGUF").expect("set KINETIC_TEST_EMBED_GGUF");
        let file: &'static GgufFile = Box::leak(Box::new(GgufFile::open(path).unwrap()));
        let embedder = Embedder::load(file).unwrap();
        let model: &'static Embeddings = Box::leak(Box::new(
            Embeddings::new("test-embed", file.header(), embedder).unwrap(),
        ));
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let base = format!("http://{}", listener.local_addr().unwrap());
        std::thread::spawn(move || kinetic_server::serve_embeddings(model, listener));
        base
    })
}

fn post(path: &str, body: Value) -> Result<Value, (u16, Value)> {
    match ureq::post(&format!("{}{path}", base())).send_json(body) {
        Ok(r) => Ok(r.into_json().unwrap()),
        Err(ureq::Error::Status(code, r)) => Err((code, r.into_json().unwrap())),
        Err(e) => panic!("{e}"),
    }
}

fn vector(v: &Value) -> Vec<f32> {
    v.as_array()
        .unwrap()
        .iter()
        .map(|x| x.as_f64().unwrap() as f32)
        .collect()
}

fn dot(a: &[f32], b: &[f32]) -> f32 {
    a.iter().zip(b).map(|(x, y)| x * y).sum()
}

#[test]
#[ignore = "needs KINETIC_TEST_EMBED_GGUF"]
fn similar_texts_embed_close() {
    let r = post(
        "/v1/embeddings",
        json!({"model": "any", "input": [
            "The cat sits on the mat.",
            "A cat is sitting on a mat.",
            "Quarterly revenue grew by twelve percent.",
        ]}),
    )
    .unwrap();
    assert_eq!(r["object"], "list");
    assert_eq!(r["model"], "test-embed");
    let v: Vec<Vec<f32>> = r["data"]
        .as_array()
        .unwrap()
        .iter()
        .enumerate()
        .map(|(i, d)| {
            assert_eq!(d["index"], i);
            vector(&d["embedding"])
        })
        .collect();
    assert_eq!(v.len(), 3);
    assert!((dot(&v[0], &v[0]) - 1.0).abs() < 1e-4);
    assert!(dot(&v[0], &v[1]) > dot(&v[0], &v[2]) + 0.1);
    assert!(r["usage"]["prompt_tokens"].as_u64().unwrap() > 10);
}

#[test]
#[ignore = "needs KINETIC_TEST_EMBED_GGUF"]
fn one_string_tokens_and_base64_agree() {
    let text = post("/v1/embeddings", json!({"input": "hello world"})).unwrap();
    let floats = vector(&text["data"][0]["embedding"]);
    let b64 = post(
        "/v1/embeddings",
        json!({"input": "hello world", "encoding_format": "base64"}),
    )
    .unwrap();
    assert!(b64["data"][0]["embedding"].is_string());
    // bge wraps "hello world" as [CLS] hello world [SEP].
    let ids = post("/v1/embeddings", json!({"input": [101, 7592, 2088, 102]})).unwrap();
    assert_eq!(vector(&ids["data"][0]["embedding"]), floats);
}

#[test]
#[ignore = "needs KINETIC_TEST_EMBED_GGUF"]
fn bad_inputs_are_refused() {
    for input in [json!(""), json!([]), json!({"a": 1}), json!([[1, 2], "x"])] {
        let (code, body) = post("/v1/embeddings", json!({ "input": input })).unwrap_err();
        assert_eq!(code, 400, "{input}");
        assert!(body["error"]["message"].is_string());
    }
    let (code, _) = post(
        "/v1/embeddings",
        json!({"input": "x", "encoding_format": "f16"}),
    )
    .unwrap_err();
    assert_eq!(code, 400);
    let (code, body) = post("/v1/chat/completions", json!({"messages": []})).unwrap_err();
    assert_eq!(code, 400);
    assert!(body["error"]["message"]
        .as_str()
        .unwrap()
        .contains("embedding model"));
}

#[test]
#[ignore = "needs KINETIC_TEST_EMBED_GGUF"]
fn ollama_embed_matches_the_openai_vectors() {
    let openai = post("/v1/embeddings", json!({"input": ["a cat", "a dog"]})).unwrap();
    let r = post(
        "/api/embed",
        json!({"model": "x", "input": ["a cat", "a dog"]}),
    )
    .unwrap();
    assert_eq!(r["model"], "test-embed");
    assert!(r["prompt_eval_count"].as_u64().unwrap() > 0);
    for i in 0..2 {
        assert_eq!(
            vector(&r["embeddings"][i]),
            vector(&openai["data"][i]["embedding"])
        );
    }
    let one = post("/api/embed", json!({"model": "x", "input": "a cat"})).unwrap();
    assert_eq!(one["embeddings"].as_array().unwrap().len(), 1);
    let legacy = post("/api/embeddings", json!({"model": "x", "prompt": "a cat"})).unwrap();
    assert_eq!(vector(&legacy["embedding"]), vector(&r["embeddings"][0]));

    let short = post(
        "/api/embed",
        json!({"model": "x", "input": "a cat", "dimensions": 64}),
    )
    .unwrap();
    let v = vector(&short["embeddings"][0]);
    assert_eq!(v.len(), 64);
    assert!((dot(&v, &v) - 1.0).abs() < 1e-4);

    let long = "word ".repeat(2000);
    assert!(post("/api/embed", json!({"model": "x", "input": long})).is_ok());
    let (code, body) = post(
        "/api/embed",
        json!({"model": "x", "input": long, "truncate": false}),
    )
    .unwrap_err();
    assert_eq!(code, 400);
    assert!(body["error"].is_string(), "{body}");
    let (code, _) = post("/api/chat", json!({"model": "x", "messages": []})).unwrap_err();
    assert_eq!(code, 400);
}
