//! Tokenizes a text file and reports the speed.
//!
//! cargo run --release -p kinetic-tokenizer --example tokenize -- model.gguf input.txt

use std::time::Instant;

use kinetic_gguf::GgufFile;
use kinetic_tokenizer::Tokenizer;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let (Some(model), Some(input)) = (args.next(), args.next()) else {
        return Err("usage: tokenize <model.gguf> <input.txt>".into());
    };
    let file = GgufFile::open(&model)?;
    let start = Instant::now();
    let tokenizer = Tokenizer::from_gguf(file.header())?;
    let load = start.elapsed();
    let text = std::fs::read_to_string(&input)?;

    let start = Instant::now();
    let ids = tokenizer.encode(&text, false);
    let secs = start.elapsed().as_secs_f64();
    let round_trip = tokenizer.decode(&ids) == text;

    println!(
        "loaded {} tokens in {:.0} ms; {} bytes -> {} tokens in {:.3} s, {:.1} MB/s; round trip {}",
        tokenizer.vocab_size(),
        load.as_secs_f64() * 1e3,
        text.len(),
        ids.len(),
        secs,
        text.len() as f64 / secs / 1e6,
        if round_trip { "ok" } else { "differs" },
    );
    Ok(())
}
