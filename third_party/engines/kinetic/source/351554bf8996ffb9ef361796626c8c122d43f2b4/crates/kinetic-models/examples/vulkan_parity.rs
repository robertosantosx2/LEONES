//! Checks greedy decoding on a Vulkan GPU against the CPU path. The GPU is
//! fed the CPU's tokens, so every step compares the same context; the top
//! four probabilities of the first steps are printed side by side, and
//! every step where the greedy tokens differ is listed with both margins.
//! Then the GPU decodes on its own, and runs the same tokens again in
//! batches and as speculative drafts, half of each draft wrong and rolled
//! back, which must all give exactly the same greedy tokens, and checks
//! that the largest logit alone comes back unchanged.
//!
//! cargo run --release -p kinetic-models --features vulkan --example vulkan_parity -- model.gguf prompt.txt [n] [shown] [device]

use std::cell::Cell;
use std::time::Instant;

use kinetic_gguf::GgufFile;
use kinetic_models::speculative::argmax;
use kinetic_models::vulkan::{devices, VulkanModel, VulkanRunner};
use kinetic_models::warm::Warm;
use kinetic_tokenizer::Tokenizer;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let path = args
        .next()
        .ok_or("usage: vulkan_parity <model.gguf> <prompt.txt> [n] [shown] [device]")?;
    let prompt = std::fs::read_to_string(args.next().ok_or("missing prompt file")?)?;
    let n: usize = args.next().map_or(Ok(32), |s| s.parse())?;
    let shown: usize = args.next().map_or(Ok(8), |s| s.parse())?;
    let index: usize = args.next().map_or(Ok(0), |s| s.parse())?;

    let file = GgufFile::open(&path)?;
    let tokenizer = Tokenizer::from_gguf(file.header())?;
    let model = kinetic_models::load(&file)?;
    let ids = tokenizer.encode(&prompt, true);
    let physical = devices()?.into_iter().nth(index).ok_or("no such device")?;
    // Room for the wrong tokens of the last draft.
    let gpu = VulkanModel::load_on(&model, ids.len() + n + 3, &physical)?;
    println!("device: {}", gpu.device_name());

    let mut cpu_state = model.new_state();
    let mut gpu_state = gpu.new_state()?;
    let mut cpu_logits = model.forward_batch(&mut cpu_state, &ids);
    let mut gpu_logits = gpu.run(&mut gpu_state, &ids, false)?.logits;

    println!("prompt {} tokens", ids.len());
    println!("step  cpu top4 (token:prob)                          gpu top4");
    let mut tokens = Vec::new();
    let mut differ = Vec::new();
    for step in 0..n {
        let (cpu, gpu_top) = (top_probs(&cpu_logits, 4), top_probs(&gpu_logits, 4));
        if step < shown {
            println!("{step:4}  {}  {}", show(&cpu), show(&gpu_top));
        }
        let token = argmax(&cpu_logits);
        if argmax(&gpu_logits) != token {
            differ.push((step, cpu, gpu_top));
        }
        tokens.push(token);
        cpu_logits = model.forward(&mut cpu_state, token);
        gpu_logits = gpu.run(&mut gpu_state, &[token], false)?.logits;
    }

    println!("greedy tokens agree on {}/{n} steps", n - differ.len());
    for (step, cpu, gpu_top) in &differ {
        println!("  step {step}: cpu {}  gpu {}", show(cpu), show(gpu_top));
    }
    println!("---\n{}\n---", tokenizer.decode(&tokens));

    let mut state = gpu.new_state()?;
    let (first, _) = gpu.run_greedy(&mut state, &ids, false)?;
    let mut alone = vec![first[0]];
    let start = Instant::now();
    for step in 1..n {
        let (next, _) = gpu.run_greedy(&mut state, &alone[step - 1..step], false)?;
        alone.push(next[0]);
    }
    let rate = (n - 1) as f64 / start.elapsed().as_secs_f64();
    let list: Vec<String> = alone.iter().map(u32::to_string).collect();
    println!("gpu greedy: {}", list.join(","));
    println!("gpu decode: {rate:.1} tokens/s");

    let mut state = gpu.new_state()?;
    let mut fed = ids.clone();
    fed.extend_from_slice(&alone[..n - 1]);
    let (batched, _) = gpu.run_greedy(&mut state, &fed, true)?;
    let same = batched[ids.len() - 1..] == alone[..];
    println!("batched rows give the same greedy tokens: {same}");

    let mut state = gpu.new_state()?;
    gpu.run_greedy(&mut state, &ids[..ids.len() - 1], false)?;
    let mut fed = vec![ids[ids.len() - 1]];
    fed.extend_from_slice(&alone[..n - 1]);
    let mut drafted = Vec::new();
    for good in fed.chunks(3) {
        let mut draft = good.to_vec();
        draft.extend([0, 1, 2]);
        gpu.checkpoint(&mut state)?;
        let (greedy, _) = gpu.run_greedy(&mut state, &draft, true)?;
        gpu.rollback(&mut state, good.len())?;
        drafted.extend_from_slice(&greedy[..good.len()]);
    }
    println!(
        "drafts rolled back give the same greedy tokens: {}",
        drafted == alone
    );

    // a host copy restored through the warm cache must decode the same
    let mut warm = Warm::new(&model, 0, 1 << 30);
    let runner = VulkanRunner {
        gpu: &gpu,
        model: &model,
        spare: Cell::new(None),
    };
    let cold = warm.prefill_on(&runner, &ids);
    let host = gpu.host_state(&model, &cold.state)?;
    warm.insert(&ids, &host, &cold.logits)?;
    let mut hot = warm.prefill_on(&runner, &ids);
    let mut restored = vec![argmax(&hot.logits)];
    for step in 1..n {
        let (next, _) = gpu.run_greedy(&mut hot.state, &restored[step - 1..step], false)?;
        restored.push(next[0]);
    }
    println!(
        "warm start of {} tokens gives the same greedy tokens: {}",
        hot.hit,
        restored == alone
    );

    let mut state = gpu.new_state()?;
    let full = gpu.run(&mut state, &ids, false)?.logits;
    gpu.reset(&mut state)?;
    let top = gpu.run_top1(&mut state, &ids, false)?.logits;
    let at = argmax(&full);
    let exact = argmax(&top) == at && top[at as usize].to_bits() == full[at as usize].to_bits();
    println!("top logit kept exactly: {exact}");
    Ok(())
}

fn top_probs(logits: &[f32], k: usize) -> Vec<(u32, f32)> {
    let max = logits.iter().copied().fold(f32::NEG_INFINITY, f32::max);
    let sum: f32 = logits.iter().map(|l| (l - max).exp()).sum();
    let mut idx: Vec<(u32, f32)> = logits
        .iter()
        .enumerate()
        .map(|(i, &l)| (i as u32, (l - max).exp() / sum))
        .collect();
    idx.sort_by(|a, b| b.1.total_cmp(&a.1));
    idx.truncate(k);
    idx
}

fn show(top: &[(u32, f32)]) -> String {
    let cells: Vec<String> = top.iter().map(|(t, p)| format!("{t:>6}:{p:.4}")).collect();
    cells.join(" ")
}
