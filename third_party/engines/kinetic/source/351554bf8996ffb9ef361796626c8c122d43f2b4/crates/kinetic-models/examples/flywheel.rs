//! Greedy decoding of a mixture-of-experts model on CUDA with its routed
//! experts offloaded, reporting the placement plan, speeds and how the
//! expert cache did.
//!
//! cargo run --release -p kinetic-models --features cuda --example flywheel -- model.gguf 1,2,3 [n] [context]

use std::time::Instant;

use kinetic_gguf::GgufFile;
use kinetic_models::cuda::CudaModel;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let path = args
        .next()
        .ok_or("usage: flywheel <model.gguf> <ids> [n] [context]")?;
    let ids: Vec<u32> = args
        .next()
        .ok_or("missing ids")?
        .split(',')
        .map(str::parse)
        .collect::<Result<_, _>>()?;
    let n: usize = args.next().map_or(Ok(64), |s| s.parse())?;
    let context: usize = args.next().map_or(Ok(4096), |s| s.parse())?;

    let file = GgufFile::open(&path)?;
    let model = kinetic_models::load(&file)?;
    let start = Instant::now();
    let gpu = CudaModel::load(&model, context)?;
    println!("loaded in {:.1}s", start.elapsed().as_secs_f64());
    if let Some(plan) = gpu.plan() {
        println!("{plan}");
    }
    let mut state = gpu.new_state()?;

    let start = Instant::now();
    let (greedy, _) = gpu.run_greedy(&mut state, &ids, false)?;
    let prefill = start.elapsed().as_secs_f64();
    println!(
        "prefill {} tokens in {prefill:.2}s ({:.1} tok/s)",
        ids.len(),
        ids.len() as f64 / prefill
    );
    report(&gpu);

    let mut out = vec![greedy[0]];
    let start = Instant::now();
    while out.len() < n {
        let (greedy, _) = gpu.run_greedy(&mut state, &out[out.len() - 1..], false)?;
        out.push(greedy[0]);
    }
    let decode = start.elapsed().as_secs_f64();
    println!(
        "decode {} tokens in {decode:.2}s ({:.2} tok/s)",
        n - 1,
        (n - 1) as f64 / decode
    );
    report(&gpu);
    println!(
        "generated: {}",
        out.iter().map(u32::to_string).collect::<Vec<_>>().join(",")
    );
    Ok(())
}

fn report(gpu: &CudaModel) {
    if let Some(stats) = gpu.stats() {
        println!("{stats}");
    }
    gpu.reset_stats();
}
