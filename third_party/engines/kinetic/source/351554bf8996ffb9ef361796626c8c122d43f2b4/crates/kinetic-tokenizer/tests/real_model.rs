//! Compares against token ids produced by llama.cpp for a real model.
//!
//! KINETIC_TEST_GGUF=model.gguf cargo test --release -p kinetic-tokenizer -- --ignored
//!
//! The bundled inputs are llama.cpp's `ggml-vocab-qwen35` test texts; the ids
//! are what llama.cpp's `llama-tokenize --no-escape` gives for Qwen3.5-4B,
//! whose vocabulary differs from the one upstream recorded. Set
//! KINETIC_TEST_VECTORS to another `.inp` file, with its `.out` next to it,
//! to check a different model or corpus.

use std::path::PathBuf;

use kinetic_gguf::GgufFile;
use kinetic_tokenizer::Tokenizer;

const SEPARATOR: &str = "\n__ggml_vocab_test__\n";

fn vectors() -> Vec<(String, Vec<u32>)> {
    let inp = std::env::var_os("KINETIC_TEST_VECTORS").map_or_else(
        || PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/data/qwen35.inp"),
        PathBuf::from,
    );
    let inputs = std::fs::read_to_string(&inp).unwrap();
    let outputs = std::fs::read_to_string(inp.with_extension("out")).unwrap();
    let inputs = inputs.strip_suffix(SEPARATOR).unwrap_or(&inputs);
    let pairs: Vec<_> = inputs
        .split(SEPARATOR)
        .zip(outputs.lines())
        .map(|(text, ids)| {
            let ids = ids
                .split_whitespace()
                .map(|id| id.parse().unwrap())
                .collect();
            (text.to_owned(), ids)
        })
        .collect();
    assert_eq!(
        pairs.len(),
        outputs.lines().count(),
        "inputs and outputs differ in count"
    );
    pairs
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn matches_llama_cpp_token_ids() {
    let path = std::env::var("KINETIC_TEST_GGUF").expect("set KINETIC_TEST_GGUF");
    let file = GgufFile::open(&path).unwrap();
    let tokenizer = Tokenizer::from_gguf(file.header()).unwrap();

    let bos = tokenizer.encode("", false);
    let vectors = vectors();
    let mut mismatches = 0;
    for (text, expected) in &vectors {
        let ids = tokenizer.encode(text, true);
        let body = &ids[bos.len()..];
        // Upstream vectors are recorded without the BOS the model may add.
        let ids = if expected.starts_with(&bos) {
            &ids
        } else {
            body
        };
        if ids != expected {
            mismatches += 1;
            println!("{text:?}\n  expected {expected:?}\n  got      {ids:?}");
        }
        let decoded = tokenizer.decode(body);
        // SentencePiece models may put a space in front of each run of text.
        assert!(
            decoded == *text || decoded.replace(' ', "") == text.replace(' ', ""),
            "decode does not round-trip: {decoded:?}"
        );
    }
    println!("{} of {} match", vectors.len() - mismatches, vectors.len());
    assert_eq!(mismatches, 0);
}
