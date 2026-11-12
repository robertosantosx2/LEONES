//! Embeds or ranks the lines of a text file, for parity checks against
//! other runtimes. Prints each line's token ids and its embedding (or
//! relevance score), then the throughput of the best of `repeats` runs.
//! A ranking model takes `query<TAB>document` lines and lays them out with
//! the file's rerank template.
//!
//! cargo run --release -p kinetic-models --example embed -- model.gguf lines.txt [repeats]

use std::time::Instant;

use kinetic_gguf::GgufFile;
use kinetic_models::{Embedder, Pooling};
use kinetic_tokenizer::Tokenizer;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let usage = "usage: embed <model.gguf> <lines.txt> [repeats]";
    let path = args.next().ok_or(usage)?;
    let text = std::fs::read_to_string(args.next().ok_or(usage)?)?;
    let repeats: usize = args.next().map_or(Ok(1), |s| s.parse())?;

    let file = GgufFile::open(&path)?;
    let tokenizer = Tokenizer::from_gguf(file.header())?;
    let embedder = Embedder::load(&file)?;
    let rank = embedder.pooling() == Pooling::Rank;
    let template = file
        .header()
        .get("tokenizer.chat_template.rerank")
        .and_then(|v| v.as_str());

    let inputs: Vec<Vec<u32>> = text
        .lines()
        .filter(|l| !l.trim().is_empty())
        .map(|line| match (rank, template) {
            (true, Some(t)) => {
                let (query, doc) = line.split_once('\t').unwrap_or((line, ""));
                let prompt = t.replace("{query}", query).replace("{document}", doc);
                Ok(tokenizer.encode(&prompt, true))
            }
            (true, None) => Err("ranking model without a rerank template"),
            (false, _) => Ok(tokenizer.encode(line, true)),
        })
        .collect::<Result<_, _>>()?;
    let batch: Vec<&[u32]> = inputs.iter().map(Vec::as_slice).collect();

    let mut best = f64::INFINITY;
    let mut out = Vec::new();
    for _ in 0..repeats.max(1) {
        let start = Instant::now();
        out = if rank {
            embedder.rank(&batch).into_iter().map(|s| vec![s]).collect()
        } else {
            embedder.embed(&batch)
        };
        best = best.min(start.elapsed().as_secs_f64());
    }

    for (tokens, v) in inputs.iter().zip(&out) {
        let join = |it: &mut dyn Iterator<Item = String>| it.collect::<Vec<_>>().join(",");
        println!("tokens {}", join(&mut tokens.iter().map(u32::to_string)));
        println!("values {}", join(&mut v.iter().map(f32::to_string)));
    }
    let n_tokens: usize = inputs.iter().map(Vec::len).sum();
    println!(
        "{} inputs, {n_tokens} tokens in {:.1} ms: {:.1} inputs/s, {:.0} tokens/s",
        inputs.len(),
        best * 1e3,
        inputs.len() as f64 / best,
        n_tokens as f64 / best
    );
    Ok(())
}
