mod common;
use rusting_strata::{gguf::Gguf, tokenizer::Tokenizer};

#[test]
fn matches_llama_cpp() {
    let Some(p) = common::model_path() else { return };
    let g = Gguf::open(&p).unwrap();
    let tok = Tokenizer::from_gguf(&g).unwrap();
    let pre = g.get("tokenizer.ggml.pre").unwrap().as_str().unwrap().to_string();
    let fx: serde_json::Value = serde_json::from_str(match pre.as_str() {
        "qwen2" => include_str!("fixtures/tokens-qwen2.json"),
        _ => include_str!("fixtures/tokens.json"),
    }).unwrap();
    for case in fx.as_array().unwrap() {
        let text = case["text"].as_str().unwrap();
        let want: Vec<u32> = case["ids"].as_array().unwrap().iter().map(|v| v.as_u64().unwrap() as u32).collect();
        assert_eq!(tok.encode(text).unwrap(), want, "encode {text:?}");
        assert_eq!(tok.decode(&want).unwrap(), text, "decode {text:?}");
    }
    assert!(!tok.eos_ids().is_empty());
}
