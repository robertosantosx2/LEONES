//! Checks greedy decoding on the GPU against the CPU path. The GPU is fed
//! the CPU's tokens, so every step compares the same context; the top four
//! probabilities of the first steps are printed side by side, and every step
//! where the greedy tokens differ is listed with both margins. Then the GPU
//! decodes on its own, for comparison with other GPU runtimes.
//!
//! cargo run --release -p kinetic-models --features cuda --example cuda_parity -- model.gguf prompt.txt [n] [shown]

use kinetic_gguf::GgufFile;
use kinetic_models::cuda::CudaModel;
use kinetic_models::speculative::argmax;
use kinetic_tokenizer::Tokenizer;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let path = args
        .next()
        .ok_or("usage: cuda_parity <model.gguf> <prompt.txt> [n] [shown]")?;
    let prompt = std::fs::read_to_string(args.next().ok_or("missing prompt file")?)?;
    let n: usize = args.next().map_or(Ok(32), |s| s.parse())?;
    let shown: usize = args.next().map_or(Ok(8), |s| s.parse())?;

    let file = GgufFile::open(&path)?;
    let tokenizer = Tokenizer::from_gguf(file.header())?;
    let model = kinetic_models::load(&file)?;
    let ids = tokenizer.encode(&prompt, true);
    let gpu = CudaModel::load(&model, ids.len() + n)?;

    let mut cpu_state = model.new_state();
    let mut gpu_state = gpu.new_state()?;
    let mut cpu_logits = model.forward_batch(&mut cpu_state, &ids);
    let mut gpu_logits = gpu.run(&mut gpu_state, &ids, false)?.logits;

    let list: Vec<String> = ids.iter().map(u32::to_string).collect();
    println!("prompt {} tokens: {}", ids.len(), list.join(","));
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

    println!("gpu alone:");
    let mut state = gpu.new_state()?;
    let mut logits = gpu.run(&mut state, &ids, false)?.logits;
    let mut tokens = Vec::new();
    for step in 0..n {
        if step < shown {
            println!("{step:4}  {}", show(&top_probs(&logits, 4)));
        }
        tokens.push(argmax(&logits));
        logits = gpu.run(&mut state, &tokens[step..], false)?.logits;
    }
    let list: Vec<String> = tokens.iter().map(u32::to_string).collect();
    println!("gpu greedy: {}", list.join(","));
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
