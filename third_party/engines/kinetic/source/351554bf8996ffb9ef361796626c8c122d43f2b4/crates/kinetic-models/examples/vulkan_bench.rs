//! pp512 and tg128 of a model on one Vulkan device, best of three, as
//! llama-bench measures them: 512 prompt tokens in one run, then 128
//! tokens decoded one at a time.
//!
//! cargo run --release -p kinetic-models --features vulkan --example vulkan_bench -- model.gguf [device]

use std::time::Instant;

use kinetic_gguf::GgufFile;
use kinetic_models::vulkan::{devices, VulkanModel};

const PROMPT: usize = 512;
const DECODE: usize = 128;
const TRIALS: usize = 3;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let path = args
        .next()
        .ok_or("usage: vulkan_bench <model.gguf> [device]")?;
    let index: usize = args.next().map_or(Ok(0), |s| s.parse())?;
    let file = GgufFile::open(&path)?;
    let model = kinetic_models::load(&file)?;
    let physical = devices()?.into_iter().nth(index).ok_or("no such device")?;
    let gpu = VulkanModel::load_on(&model, PROMPT + DECODE + 1, &physical)?;
    let vocab = gpu.n_vocab() as u64;
    let tokens: Vec<u32> = (0..PROMPT as u64)
        .map(|i| (i.wrapping_mul(2_654_435_761) % vocab) as u32)
        .collect();

    let mut state = gpu.new_state()?;
    gpu.run_greedy(&mut state, &tokens[..16], false)?;
    let (mut pp, mut tg) = (0.0f64, 0.0f64);
    for _ in 0..TRIALS {
        gpu.reset(&mut state)?;
        let start = Instant::now();
        let (next, _) = gpu.run_greedy(&mut state, &tokens, false)?;
        pp = pp.max(PROMPT as f64 / start.elapsed().as_secs_f64());

        gpu.reset(&mut state)?;
        let mut token = next[0];
        let start = Instant::now();
        for _ in 0..DECODE {
            token = gpu.run_greedy(&mut state, &[token], false)?.0[0];
        }
        tg = tg.max(DECODE as f64 / start.elapsed().as_secs_f64());
    }
    println!(
        "{}: pp{PROMPT} {pp:.1} t/s, tg{DECODE} {tg:.1} t/s",
        gpu.device_name()
    );
    Ok(())
}
