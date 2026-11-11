//! Greedy decoding from token ids, for parity checks against other runtimes.
//!
//! cargo run --release -p kinetic-models --example greedy -- model.gguf 1,2,3 16

use std::time::Instant;

use kinetic_gguf::GgufFile;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let path = args.next().ok_or("usage: greedy <model.gguf> <ids> [n]")?;
    let prompt: Vec<u32> = args
        .next()
        .ok_or("missing ids")?
        .split(',')
        .map(str::parse)
        .collect::<Result<_, _>>()?;
    let n: usize = args.next().map_or(Ok(16), |s| s.parse())?;

    let file = GgufFile::open(&path)?;
    let model = kinetic_models::load(&file)?;
    let mut state = model.new_state();

    let start = Instant::now();
    let mut logits = model.forward_batch(&mut state, &prompt);
    let prefill = start.elapsed();

    let start = Instant::now();
    let mut out = Vec::new();
    for step in 0..n {
        let top4 = probs(&logits, 4);
        println!("step {step} top4: {top4:?}");
        let best = top4[0].0;
        out.push(best);
        logits = model.forward(&mut state, best);
    }
    let decode = start.elapsed();

    println!(
        "generated: {}",
        out.iter().map(u32::to_string).collect::<Vec<_>>().join(",")
    );
    println!(
        "prefill {} tok in {:.2}s, decode {n} tok in {:.2}s ({:.2} tok/s)",
        prompt.len(),
        prefill.as_secs_f64(),
        decode.as_secs_f64(),
        n as f64 / decode.as_secs_f64()
    );
    Ok(())
}

fn top(logits: &[f32], k: usize) -> Vec<(u32, f32)> {
    let mut idx: Vec<(u32, f32)> = logits
        .iter()
        .enumerate()
        .map(|(i, &l)| (i as u32, l))
        .collect();
    idx.sort_by(|a, b| b.1.total_cmp(&a.1));
    idx.truncate(k);
    idx
}

fn probs(logits: &[f32], k: usize) -> Vec<(u32, f32)> {
    let max = logits.iter().copied().fold(f32::NEG_INFINITY, f32::max);
    let sum: f32 = logits.iter().map(|l| (l - max).exp()).sum();
    top(logits, k)
        .into_iter()
        .map(|(i, l)| (i, (l - max).exp() / sum))
        .collect()
}
