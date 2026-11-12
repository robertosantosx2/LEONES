//! A real model generating under a JSON Schema produces a matching document.
//!
//! KINETIC_TEST_GGUF=model.gguf cargo test --release -p kinetic-grammar -- --ignored
//!
//! The model must use ChatML turns, as LFM3, Qwen3 and Qwen3.5 do. Decoding
//! is greedy over the logits the grammar allows.

use std::time::{Duration, Instant};

use kinetic_gguf::GgufFile;
use kinetic_grammar::{Grammar, Matcher, TokenSet, Vocabulary};
use kinetic_tokenizer::Tokenizer;
use serde_json::{json, Value};

const MAX_TOKENS: usize = 160;

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn greedy_generation_matches_the_schema() {
    let path = std::env::var("KINETIC_TEST_GGUF").expect("set KINETIC_TEST_GGUF to a .gguf model");
    let file = GgufFile::open(&path).unwrap();
    let tokenizer = Tokenizer::from_gguf(file.header()).unwrap();
    let model = kinetic_models::load(&file).unwrap();
    let vocab = Vocabulary::from_tokenizer(&tokenizer);

    let schema = json!({
        "type": "object",
        "properties": {
            "name": {"type": "string", "maxLength": 40},
            "age": {"type": "integer", "minimum": 0, "maximum": 150},
            "languages": {"type": "array", "items": {"enum": ["Polish", "English", "German"]}, "minItems": 1, "maxItems": 3},
            "birth_date": {"type": "string", "format": "date"},
            "pets": {"type": "array", "items": {"$ref": "#/$defs/pet"}, "maxItems": 2}
        },
        "required": ["name", "age", "languages", "birth_date"],
        "$defs": {
            "pet": {
                "type": "object",
                "properties": {"kind": {"enum": ["cat", "dog"]}, "name": {"type": "string", "maxLength": 20}},
                "required": ["kind", "name"]
            }
        }
    });
    let grammar = Grammar::from_json_schema(&schema).unwrap();
    let prompt = "<|im_start|>user\nDescribe a fictional Polish engineer as JSON with name, age, languages, \
                  birth_date and pets.<|im_end|>\n<|im_start|>assistant\n";

    let mut state = model.new_state();
    let mut logits = model.forward_batch(&mut state, &tokenizer.encode(prompt, true));
    let mut matcher = Matcher::new(&grammar, &vocab);
    let mut allowed = TokenSet::new(vocab.len());
    let mut generated = Vec::new();
    let mut masking = Duration::ZERO;
    let mut stopped = false;
    for _ in 0..MAX_TOKENS {
        let start = Instant::now();
        matcher.allowed(&mut allowed);
        masking += start.elapsed();
        let token = (0..logits.len() as u32)
            .filter(|&t| allowed.contains(t))
            .max_by(|&a, &b| logits[a as usize].total_cmp(&logits[b as usize]))
            .expect("the grammar allows some token");
        matcher.accept(token).unwrap();
        if vocab.stop_tokens().contains(&token) {
            stopped = true;
            break;
        }
        generated.push(token);
        logits = model.forward(&mut state, token);
    }
    let text = tokenizer.decode(&generated);
    println!(
        "{} tokens, masks {:.3} ms per token:\n{text}",
        generated.len(),
        masking.as_secs_f64() * 1e3 / (generated.len() + 1) as f64
    );

    assert!(
        stopped || matcher.is_complete(),
        "generation ran out of tokens"
    );
    let doc: Value = serde_json::from_str(&text).expect("valid JSON");
    let obj = doc.as_object().unwrap();
    let keys: Vec<&str> = obj.keys().map(String::as_str).collect();
    let order = ["name", "age", "languages", "birth_date", "pets"];
    assert!(
        keys.iter().all(|k| order.contains(k)) && keys.len() >= 4,
        "{keys:?}"
    );
    assert!(keys
        .windows(2)
        .all(|w| order.iter().position(|o| *o == w[0]) < order.iter().position(|o| *o == w[1])));
    assert!(obj["name"].as_str().unwrap().chars().count() <= 40);
    assert!((0..=150).contains(&obj["age"].as_i64().unwrap()));
    let languages = obj["languages"].as_array().unwrap();
    assert!((1..=3).contains(&languages.len()));
    assert!(languages
        .iter()
        .all(|l| ["Polish", "English", "German"].contains(&l.as_str().unwrap())));
    let date = obj["birth_date"].as_str().unwrap();
    let parts: Vec<u32> = date.split('-').map(|p| p.parse().unwrap()).collect();
    assert!(
        date.len() == 10
            && parts.len() == 3
            && (1..=12).contains(&parts[1])
            && (1..=31).contains(&parts[2])
    );
    for pet in obj
        .get("pets")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
    {
        assert!(["cat", "dog"].contains(&pet["kind"].as_str().unwrap()));
        assert!(pet["name"].as_str().unwrap().chars().count() <= 20);
    }
}
