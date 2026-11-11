//! Prefill on the GPU: speed at each prompt length, against running the
//! prompt in decode-sized steps, and the device memory it takes. With
//! `check`, how closely the prefill path matches decoding on the text
//! itself: the KL divergence and top-1 agreement of the logits at every
//! position against GPU decode steps, both against the CPU for scale, then
//! greedy continuations from each of the three states.
//!
//! cargo run --release -p kinetic-models --features cuda --example cuda_prefill -- model.gguf text.txt [512,2048] [check]
//!
//! For the speed runs the text is tokenized and repeated as needed to make
//! each length.

use std::time::Instant;

use kinetic_cuda::MAX_BATCH;
use kinetic_gguf::GgufFile;
use kinetic_models::cuda::{CudaModel, CudaState};
use kinetic_models::speculative::argmax;
use kinetic_models::{Model, State};
use kinetic_tokenizer::Tokenizer;

const RUNS: usize = 5;
const CONTINUATION: usize = 128;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let usage = "usage: cuda_prefill <model.gguf> <text.txt> [lengths] [check]";
    let path = args.next().ok_or(usage)?;
    let text = std::fs::read_to_string(args.next().ok_or(usage)?)?;
    let lengths: Vec<usize> = args
        .next()
        .unwrap_or_else(|| "512,2048".into())
        .split(',')
        .map(str::parse)
        .collect::<Result<_, _>>()?;
    let check = args.next().as_deref() == Some("check");

    let file = GgufFile::open(&path)?;
    let tokenizer = Tokenizer::from_gguf(file.header())?;
    let model = kinetic_models::load(&file)?;
    let text_ids = tokenizer.encode(&text, true);
    let longest = lengths.iter().copied().chain([text_ids.len()]).max();
    let longest = longest.ok_or("no lengths")?;
    let ids: Vec<u32> = text_ids.iter().copied().cycle().take(longest).collect();
    let gpu = CudaModel::load(&model, longest + CONTINUATION + MAX_BATCH)?;
    println!(
        "weights {:.0} MiB, {} tokens of text",
        mib(gpu.weight_bytes()),
        text_ids.len()
    );

    for &n in &lengths {
        let prompt = &ids[..n];
        let batched = best_seconds(&gpu, |s| gpu.run_greedy(s, prompt, false).map(drop))?;
        let stepped = best_seconds(&gpu, |s| {
            prompt
                .chunks(MAX_BATCH)
                .try_for_each(|step| gpu.run_greedy(s, step, false).map(drop))
        })?;
        let mut state = gpu.new_state()?;
        gpu.run_greedy(&mut state, prompt, false)?;
        let (free, total) = gpu.memory_info()?;
        println!(
            "prefill {n:5}: {:7.1} ms, {:6.0} tok/s ({:5.0} tok/s in steps of {MAX_BATCH}); \
             state {:.0} MiB, device in use {:.0} of {:.0} MiB",
            batched * 1e3,
            n as f64 / batched,
            n as f64 / stepped,
            mib(gpu.state_bytes(&state)),
            mib(total - free),
            mib(total)
        );
    }
    if check {
        compare(&gpu, &model, &text_ids)?;
    }
    Ok(())
}

/// The fastest of RUNS timed calls of `f` on a fresh state, after one
/// untimed; making the state is not timed.
fn best_seconds(
    gpu: &CudaModel,
    mut f: impl FnMut(&mut CudaState) -> kinetic_cuda::Result<()>,
) -> kinetic_cuda::Result<f64> {
    f(&mut gpu.new_state()?)?;
    let mut best = f64::INFINITY;
    for _ in 0..RUNS {
        let mut state = gpu.new_state()?;
        let start = Instant::now();
        f(&mut state)?;
        best = best.min(start.elapsed().as_secs_f64());
    }
    Ok(best)
}

/// KL divergences of one pair of paths at every position.
#[derive(Default)]
struct Divergence(Vec<f64>);

impl Divergence {
    fn push(&mut self, p: &[f32], q: &[f32]) {
        self.0.push(kl_divergence(p, q));
    }

    fn summary(&self) -> String {
        let n = self.0.len();
        let (worst, at) =
            self.0
                .iter()
                .enumerate()
                .fold((0.0, 0), |w, (i, &v)| if v > w.0 { (v, i) } else { w });
        format!(
            "KL mean {:.2e}, max {worst:.2e} at {at}",
            self.0.iter().sum::<f64>() / n as f64
        )
    }
}

/// Runs `ids` through the prefill path, in GPU steps of [`MAX_BATCH`] and
/// on the CPU, comparing the logits at every position and the greedy
/// continuations.
fn compare(gpu: &CudaModel, model: &Model, ids: &[u32]) -> kinetic_cuda::Result<()> {
    let vocab = gpu.n_vocab();
    let (mut fast, mut steps) = (gpu.new_state()?, gpu.new_state()?);
    let mut cpu = model.new_state();
    let a = gpu.run(&mut fast, ids, true)?.logits;
    let mut b = Vec::with_capacity(a.len());
    for step in ids.chunks(MAX_BATCH) {
        b.extend(gpu.run(&mut steps, step, true)?.logits);
    }
    let c = model.run(&mut cpu, ids, true).logits;

    let (mut prefill, mut gpu_cpu, mut prefill_cpu) = Default::default();
    let mut agree = 0;
    for ((x, y), z) in b.chunks(vocab).zip(a.chunks(vocab)).zip(c.chunks(vocab)) {
        Divergence::push(&mut prefill, x, y);
        Divergence::push(&mut gpu_cpu, z, x);
        Divergence::push(&mut prefill_cpu, z, y);
        agree += usize::from(argmax(x) == argmax(y));
    }
    let n = ids.len();
    println!("{n} positions");
    println!(
        "  prefill against GPU steps of {MAX_BATCH}: {}; top-1 agreement {agree}/{n}",
        prefill.summary()
    );
    println!("  GPU steps against the CPU: {}", gpu_cpu.summary());
    println!("  prefill against the CPU:   {}", prefill_cpu.summary());

    let last = |l: &[f32]| argmax(&l[l.len() - vocab..]);
    let from_prefill = continue_greedy(gpu, &mut fast, last(&a))?;
    let from_steps = continue_greedy(gpu, &mut steps, last(&b))?;
    let from_cpu = continue_cpu(model, &mut cpu, last(&c));
    println!(
        "greedy continuation of {CONTINUATION}: prefill and GPU steps share {}, \
         prefill and CPU {}, GPU steps and CPU {}",
        common_prefix(&from_prefill, &from_steps),
        common_prefix(&from_prefill, &from_cpu),
        common_prefix(&from_steps, &from_cpu)
    );
    Ok(())
}

fn common_prefix(a: &[u32], b: &[u32]) -> usize {
    a.iter().zip(b).take_while(|(x, y)| x == y).count()
}

fn continue_greedy(
    gpu: &CudaModel,
    state: &mut CudaState,
    first: u32,
) -> kinetic_cuda::Result<Vec<u32>> {
    let mut tokens = vec![first];
    while tokens.len() < CONTINUATION {
        let next = gpu.run_greedy(state, &tokens[tokens.len() - 1..], false)?.0[0];
        tokens.push(next);
    }
    Ok(tokens)
}

fn continue_cpu(model: &Model, state: &mut State, first: u32) -> Vec<u32> {
    let mut tokens = vec![first];
    while tokens.len() < CONTINUATION {
        let logits = model.forward(state, tokens[tokens.len() - 1]);
        tokens.push(argmax(&logits));
    }
    tokens
}

/// KL(p || q) of the softmax distributions of two logit rows, in nats.
fn kl_divergence(p: &[f32], q: &[f32]) -> f64 {
    let (lp, lq) = (log_softmax(p), log_softmax(q));
    lp.iter().zip(&lq).map(|(a, b)| a.exp() * (a - b)).sum()
}

fn log_softmax(x: &[f32]) -> Vec<f64> {
    let max = x.iter().copied().fold(f32::NEG_INFINITY, f32::max) as f64;
    let sum: f64 = x.iter().map(|&v| (v as f64 - max).exp()).sum();
    let shift = max + sum.ln();
    x.iter().map(|&v| v as f64 - shift).collect()
}

fn mib(bytes: usize) -> f64 {
    bytes as f64 / (1u64 << 20) as f64
}
