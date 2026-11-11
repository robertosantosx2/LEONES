//! Speculative decoding on the GPU: checks that it is lossless and reports
//! prefill, plain and speculative speed. Greedy output must equal plain
//! greedy output token for token; with a temperature, every seed is sampled
//! plainly and speculatively, as in the `speculative` example.
//!
//! cargo run --release -p kinetic-models --features cuda --example cuda_speculative -- model.gguf prompt.txt [n] [lookup|session|mtp|all|chain|tree] [temperature] [seeds]

mod common;

use std::time::Instant;

use kinetic_gguf::GgufFile;
use kinetic_models::cuda::CudaModel;
use kinetic_models::speculative::{Greedy, Sampler};
use kinetic_tokenizer::Tokenizer;

use common::{decoder, plain, report, sampling, speculative, summarize, Run};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let usage = format!(
        "usage: cuda_speculative <model.gguf> <prompt.txt> [n] [{}] [temperature] [seeds]",
        common::DRAFTERS
    );
    let path = args.next().ok_or(usage)?;
    let prompt = std::fs::read_to_string(args.next().ok_or("missing prompt file")?)?;
    let n: usize = args.next().map_or(Ok(256), |s| s.parse())?;
    let source = args.next().unwrap_or_else(|| "lookup".into());
    let temperature: f32 = args.next().map_or(Ok(0.0), |s| s.parse())?;
    let seeds: u64 = args.next().map_or(Ok(50), |s| s.parse())?;

    let file = GgufFile::open(&path)?;
    let tokenizer = Tokenizer::from_gguf(file.header())?;
    let model = kinetic_models::load(&file)?;
    let ids = tokenizer.encode(&prompt, true);
    let gpu = CudaModel::load(&model, ids.len() + n + 16)?;
    let eos = tokenizer.eos();
    let stop = |t: u32| Some(t) == eos;

    let mut state = gpu.new_state()?;
    gpu.run_greedy(&mut state, &ids, false)?;
    let mut state = gpu.new_state()?;
    let start = Instant::now();
    gpu.run_greedy(&mut state, &ids, false)?;
    let prefill = start.elapsed().as_secs_f64();
    println!(
        "weights {:.2} GiB, state {:.0} MiB; prefill {} tokens in {:.1} ms, {:.0} tok/s",
        gpu.weight_bytes() as f64 / (1u64 << 30) as f64,
        gpu.state_bytes(&state) as f64 / (1u64 << 20) as f64,
        ids.len(),
        prefill * 1e3,
        ids.len() as f64 / prefill
    );

    if temperature <= 0.0 {
        let plain = plain(&gpu, &mut Greedy, &mut gpu.new_state()?, &ids, n, stop);
        let mut decoder = decoder(&gpu, &source)?;
        let fast = speculative(
            &gpu,
            &mut Greedy,
            &mut decoder,
            &mut gpu.new_state()?,
            &ids,
            plain.tokens.len(),
            stop,
        );
        println!("generated {}", plain.tokens.len());
        report(&source, &plain, &fast);
        println!("---\n{}", tokenizer.decode(&fast.tokens));
        return Ok(());
    }

    let sample = |seed: u64, fast: bool| -> Result<Run, Box<dyn std::error::Error>> {
        let mut sampler = Sampler::new(sampling(temperature, seed));
        let mut state = gpu.new_state()?;
        Ok(if fast {
            let mut decoder = decoder(&gpu, &source)?;
            speculative(&gpu, &mut sampler, &mut decoder, &mut state, &ids, n, stop)
        } else {
            plain(&gpu, &mut sampler, &mut state, &ids, n, stop)
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
