//! Times a verification pass of k drafted tokens against a one-token pass,
//! after a prompt, on the CPU: what speculative decoding pays per round.
//!
//! cargo run --release -p kinetic-models --example kpass -- model.gguf prompt.txt

use std::time::Instant;

use kinetic_gguf::GgufFile;
use kinetic_tokenizer::Tokenizer;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let path = args
        .next()
        .ok_or("usage: kpass <model.gguf> <prompt.txt>")?;
    let prompt = std::fs::read_to_string(args.next().ok_or("missing prompt file")?)?;
    let file = GgufFile::open(&path)?;
    let tokenizer = Tokenizer::from_gguf(file.header())?;
    let model = kinetic_models::load(&file)?;
    let ids = tokenizer.encode(&prompt, true);
    let mut state = model.new_state();
    model.forward_batch(&mut state, &ids);
    let draft: Vec<u32> = ids.iter().rev().take(16).copied().collect();
    let mut base = 0.0;
    for k in [1, 2, 4, 8, 16] {
        let mut best = f64::INFINITY;
        for _ in 0..6 {
            model.checkpoint(&mut state);
            let start = Instant::now();
            model.run_top(&mut state, &draft[..k], true, 1);
            best = best.min(start.elapsed().as_secs_f64());
            model.rollback(&mut state, 0);
        }
        if k == 1 {
            base = best;
        }
        println!("k {k:>2}  {:>7.1} ms  {:.2}x", best * 1e3, best / base);
    }
    Ok(())
}
