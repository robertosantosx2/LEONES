//! Tokenize each JSON string on stdin (one per line) with the GGUF's tokenizer; print the ids as a JSON array.
use rusting_strata::{gguf::Gguf, tokenizer::Tokenizer};
use std::io::BufRead;

fn main() -> anyhow::Result<()> {
    let g = Gguf::open(std::path::Path::new(&std::env::args().nth(1).expect("usage: tok_ids GGUF < strings.jsonl")))?;
    let t = Tokenizer::from_gguf(&g)?;
    for line in std::io::stdin().lock().lines() {
        let s: String = serde_json::from_str(&line?)?;
        println!("{}", serde_json::to_string(&t.encode(&s)?)?);
    }
    Ok(())
}
