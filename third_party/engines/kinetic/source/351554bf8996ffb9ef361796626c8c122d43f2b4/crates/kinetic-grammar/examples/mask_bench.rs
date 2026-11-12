//! Times token masks while replaying a JSON document through a grammar.
//!
//! cargo run --release -p kinetic-grammar --example mask_bench -- model.gguf

use std::time::{Duration, Instant};

use kinetic_gguf::GgufFile;
use kinetic_grammar::{Grammar, Matcher, TokenSet, Vocabulary};
use kinetic_tokenizer::Tokenizer;
use serde_json::json;

const DOCUMENT: &str = r#"{"name": "Zażółć gęślą jaźń", "age": 42, "email": "ann@example.com", "tags": ["rust", "inference", "json"], "address": {"street": "Długa 7", "city": "Kraków", "zip": "30-001"}, "scores": [0.5, 12.25, -3], "active": true, "notes": "Line one.\nLine two with \"quotes\" and a \\ backslash; more text follows so the string runs long enough to measure masks inside it."}"#;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let path = std::env::args()
        .nth(1)
        .ok_or("usage: mask_bench <model.gguf>")?;
    let file = GgufFile::open(&path)?;
    let tokenizer = Tokenizer::from_gguf(file.header())?;

    let start = Instant::now();
    let vocab = Vocabulary::from_tokenizer(&tokenizer);
    println!(
        "vocabulary of {} tokens built in {:.0} ms",
        vocab.len(),
        ms(start.elapsed())
    );

    let schema = json!({
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0, "maximum": 150},
            "email": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
            "address": {
                "type": "object",
                "properties": {"street": {"type": "string"}, "city": {"type": "string"}, "zip": {"type": "string", "pattern": "^[0-9]{2}-[0-9]{3}$"}},
                "required": ["street", "city", "zip"]
            },
            "scores": {"type": "array", "items": {"type": "number"}},
            "active": {"type": "boolean"},
            "notes": {"type": "string"}
        },
        "required": ["name", "age"]
    });
    let tokens = tokenizer.encode(DOCUMENT, false);
    for (label, grammar) in [
        ("any JSON", Grammar::any_json()),
        ("schema", Grammar::from_json_schema(&schema)?),
    ] {
        for run in 0..3 {
            let (times, allowed) = replay(&grammar, &vocab, &tokens);
            let mut sorted = times.clone();
            sorted.sort();
            let total: Duration = times.iter().sum();
            println!(
                "{label} run {run}: {} tokens, mean {:.3} ms, median {:.3} ms, max {:.3} ms, first {:.3} ms, mean allowed {:.0}",
                times.len(),
                ms(total) / times.len() as f64,
                ms(sorted[sorted.len() / 2]),
                ms(*sorted.last().expect("tokens")),
                ms(times[0]),
                allowed,
            );
        }
    }
    Ok(())
}

/// Mask time before each token, and the mean number of allowed tokens.
fn replay(grammar: &Grammar, vocab: &Vocabulary, tokens: &[u32]) -> (Vec<Duration>, f64) {
    let mut matcher = Matcher::new(grammar, vocab);
    let mut allowed = TokenSet::new(vocab.len());
    let mut times = Vec::with_capacity(tokens.len());
    let mut total = 0;
    for &token in tokens {
        let start = Instant::now();
        matcher.allowed(&mut allowed);
        times.push(start.elapsed());
        total += allowed.count();
        assert!(
            allowed.contains(token),
            "mask leaves out {token} {:?}",
            String::from_utf8_lossy(vocab.piece(token))
        );
        matcher.accept(token).expect("the document matches");
    }
    assert!(matcher.is_complete());
    (times, total as f64 / tokens.len() as f64)
}

fn ms(d: Duration) -> f64 {
    d.as_secs_f64() * 1e3
}
