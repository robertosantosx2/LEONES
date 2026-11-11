//! Drives `/v1/rerank` over HTTP with a real ranking model.
//!
//! KINETIC_TEST_RERANK_GGUF=qwen3-reranker-0.6b-q8_0.gguf cargo test --release -p kinetic-server --test rerank -- --ignored

use std::net::TcpListener;

use kinetic_gguf::GgufFile;
use kinetic_models::Embedder;
use kinetic_server::Embeddings;
use serde_json::{json, Value};

/// One test, so one server: requests and refusals in turn.
#[test]
#[ignore = "needs KINETIC_TEST_RERANK_GGUF"]
fn documents_come_back_most_relevant_first() {
    let path = std::env::var("KINETIC_TEST_RERANK_GGUF").expect("set KINETIC_TEST_RERANK_GGUF");
    let file: &'static GgufFile = Box::leak(Box::new(GgufFile::open(path).unwrap()));
    let ranker = Embedder::load(file).unwrap();
    let model: &'static Embeddings = Box::leak(Box::new(
        Embeddings::new("test-rerank", file.header(), ranker).unwrap(),
    ));
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let base = format!("http://{}", listener.local_addr().unwrap());
    std::thread::spawn(move || kinetic_server::serve_embeddings(model, listener));
    let post = |path: &str, body: Value| -> Result<Value, u16> {
        match ureq::post(&format!("{base}{path}")).send_json(body) {
            Ok(r) => Ok(r.into_json().unwrap()),
            Err(ureq::Error::Status(code, _)) => Err(code),
            Err(e) => panic!("{e}"),
        }
    };

    let documents = [
        "Gravity attracts two bodies towards each other.",
        "The capital of China is Beijing.",
        "Shanghai is the largest city in China.",
    ];
    let r = post(
        "/v1/rerank",
        json!({"query": "What is the capital of China?", "documents": documents, "top_n": 2, "return_documents": true}),
    )
    .unwrap();
    assert_eq!(r["model"], "test-rerank");
    let results = r["results"].as_array().unwrap();
    assert_eq!(results.len(), 2);
    assert_eq!(results[0]["index"], 1);
    assert_eq!(results[0]["document"]["text"], documents[1]);
    let score = |i: usize| results[i]["relevance_score"].as_f64().unwrap();
    assert!(score(0) > 0.9 && score(0) > score(1), "{r}");
    assert!(r["usage"]["prompt_tokens"].as_u64().unwrap() > 30);

    let objects = json!({"query": "capital of China", "documents": [{"text": "Beijing"}]});
    assert!(post("/rerank", objects).is_ok());
    assert_eq!(
        post("/v1/rerank", json!({"query": "q", "documents": []})),
        Err(400)
    );
    assert_eq!(
        post("/v1/rerank", json!({"query": "q", "documents": [1]})),
        Err(400)
    );
    assert_eq!(post("/v1/embeddings", json!({"input": "x"})), Err(400));
}
