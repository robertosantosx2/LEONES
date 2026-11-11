//! Checks that speculative decoding is lossless on the CPU and reports the
//! speedup. Greedy output must equal plain greedy output token for token.
//! With a temperature, every seed is sampled plainly and speculatively:
//! seeded runs should match, and the token distributions at several steps,
//! across seeds, are compared with a chi-square test.
//!
//! cargo run --release -p kinetic-models --example speculative -- model.gguf prompt.txt [n] [lookup|session|mtp|all|chain|tree] [temperature] [seeds]

mod common;

use kinetic_gguf::GgufFile;
use kinetic_models::speculative::{Greedy, Sampler};
use kinetic_tokenizer::Tokenizer;

use common::{decoder, plain, report, sampling, speculative, summarize, Run};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let usage = format!(
        "usage: speculative <model.gguf> <prompt.txt> [n] [{}] [temperature] [seeds]",
        common::DRAFTERS
    );
    let path = args.next().ok_or(usage)?;
    let prompt = std::fs::read_to_string(args.next().ok_or("missing prompt file")?)?;
    let n: usize = args.next().map_or(Ok(256), |s| s.parse())?;
    let source = args.next().unwrap_or_else(|| "lookup".into());
    let temperature: f32 = args.next().map_or(Ok(0.0), |s| s.parse())?;
    let seeds: u64 = args.next().map_or(Ok(200), |s| s.parse())?;

    let file = GgufFile::open(&path)?;
    let tokenizer = Tokenizer::from_gguf(file.header())?;
    let model = kinetic_models::load(&file)?;
    let ids = tokenizer.encode(&prompt, true);
    let eos = tokenizer.eos();
    let stop = |t: u32| Some(t) == eos;
    println!("prompt {} tokens", ids.len());

    if temperature <= 0.0 {
        let plain = plain(&model, &mut Greedy, &mut model.new_state(), &ids, n, stop);
        let mut decoder = decoder(&model, &source)?;
        let fast = speculative(
            &model,
            &mut Greedy,
            &mut decoder,
            &mut model.new_state(),
            &ids,
            plain.tokens.len(),
            stop,
        );
        println!("generated {}", plain.tokens.len());
        report(&source, &plain, &fast);
        println!("---\n{}", tokenizer.decode(&fast.tokens));
        return Ok(());
    }

    let sample = |seed: u64, fast: bool| -> Result<Run, String> {
        let mut sampler = Sampler::new(sampling(temperature, seed));
        let mut state = model.new_state();
        Ok(if fast {
            let mut decoder = decoder(&model, &source)?;
            speculative(
                &model,
                &mut sampler,
                &mut decoder,
                &mut state,
                &ids,
                n,
                stop,
            )
        } else {
            plain(&model, &mut sampler, &mut state, &ids, n, stop)
        })
    };
    let (mut plain_runs, mut same_seed, mut other_seed) = (Vec::new(), Vec::new(), Vec::new());
    for seed in 0..seeds {
        plain_runs.push(sample(seed, false)?);
        same_seed.push(sample(seed, true)?);
        other_seed.push(sample(seeds + seed, true)?);
    }
    summarize(&source, &plain_runs, &same_seed, &other_seed, n);
    Ok(())
}
