//! `kinetic bench`: the llama-bench pp512 and tg128 tests, and an edit test
//! that measures speculative decoding where the answer repeats the prompt.

use std::io::Write;
use std::path::Path;
use std::time::Instant;

use kinetic_models::{LoadError, Model};
use kinetic_server::{Backend, CpuBackend, Job, Sampling};
use kinetic_tokenizer::Tokenizer;
use serde_json::json;

use crate::memory::peak_rss;
use crate::model_file::ModelFile;
use crate::tech::{self, Tech};
use crate::{gpu, Device, Result};

const PROMPT_TOKENS: usize = 512;
const GENERATED_TOKENS: usize = 128;
pub const EDIT_TOKENS: usize = 256;
/// Positions a benchmark sequence needs at most, past the depth.
const CONTEXT: usize = 2048;

/// How the tests run.
#[derive(Clone, Copy)]
pub struct Tests {
    /// Runs of each test; the best is reported.
    pub repetitions: usize,
    /// Tokens in the context before the generation test.
    pub depth: usize,
}

/// The edit test's file: the answer is the file again with one name changed.
const EDIT_FILE: &str = "pub fn summarize(values: &[i64]) -> (i64, i64, f64) {
    let mut count = 0;
    let mut sum = 0;
    for v in values {
        if *v >= 0 {
            count += 1;
            sum += v;
        }
    }
    let mean = if count == 0 { 0.0 } else { sum as f64 / count as f64 };
    (count, sum, mean)
}

pub fn histogram(values: &[i64], width: i64) -> Vec<(i64, usize)> {
    let mut buckets: Vec<(i64, usize)> = Vec::new();
    for v in values {
        let key = v / width;
        match buckets.iter_mut().find(|(k, _)| *k == key) {
            Some((_, n)) => *n += 1,
            None => buckets.push((key, 1)),
        }
    }
    buckets.sort();
    buckets
}
";

/// The edit test's prompt: a file, and the start of its copy.
pub fn edit_prompt() -> String {
    format!(
        "Here is a file:\n```rust\n{EDIT_FILE}```\n\nThe same file with `count` renamed to `total`:\n```rust\n"
    )
}

/// Best speeds over the repetitions, in tokens per second.
struct Speeds {
    prefill: f64,
    decode: f64,
    edit: f64,
    /// Whether the edit test's drafted output equals plain decoding.
    edit_identical: bool,
}

/// Technologies the tests take part in; Warm Start, Zero Wait and Convoy
/// need repeated, typed or concurrent requests, which the tests never send.
const MEASURED: [Tech; 3] = [Tech::Rad1, Tech::Shortlist, Tech::Torque];

pub fn run(
    path: &Path,
    name: &str,
    device: Device,
    tests: Tests,
    off: &[Tech],
    as_json: bool,
) -> Result<()> {
    let repetitions = tests.repetitions;
    let start = Instant::now();
    let file = ModelFile::open(path)?;
    let model = kinetic_models::load(file.source())?;
    let load = start.elapsed().as_secs_f64();
    if off.contains(&Tech::Shortlist) {
        model.disable_shortlist();
    }
    let rad1 = !off.contains(&Tech::Rad1);
    let tokenizer = Tokenizer::from_gguf(file.source().header())?;
    let edit = tokenizer.encode(&edit_prompt(), true);

    // The backend's name and the device's.
    let context = CONTEXT + tests.depth;
    let eager = off.contains(&Tech::Torque);
    let picked = gpu::pick(device, |kind| plain(&model, kind, context, eager))?;
    let kind = picked.as_ref().map_or(Device::Cpu, |&(_, k)| k);
    let (backend, on, speeds) = match picked.map(|(p, _)| p) {
        #[cfg(feature = "cuda")]
        Some(Plain::Cuda(plain)) => {
            let on = plain.device().to_owned();
            let drafting = || {
                let placement = kinetic_models::cuda::Placement {
                    eager,
                    ..Default::default()
                };
                let gpu = kinetic_server::CudaBackend::with_placement(&model, context, placement)?;
                Ok(if rad1 { gpu } else { gpu.without_drafts() })
            };
            let speeds = measure(*plain, drafting, &model, &edit, tests)?;
            ("CUDA", on, speeds)
        }
        #[cfg(feature = "vulkan")]
        Some(Plain::Vulkan(plain)) => {
            let on = plain.device().to_owned();
            let drafting = || {
                let gpu = kinetic_server::VulkanBackend::new(&model, context)?;
                Ok(if rad1 { gpu } else { gpu.without_drafts() })
            };
            let speeds = measure(*plain, drafting, &model, &edit, tests)?;
            ("Vulkan", on, speeds)
        }
        #[cfg(not(any(feature = "cuda", feature = "vulkan")))]
        Some(Plain::Unavailable(never, _)) => match never {},
        None => {
            let drafting = || {
                let cpu = CpuBackend::new(&model);
                Ok(if rad1 { cpu } else { cpu.without_drafts() })
            };
            let plain = CpuBackend::plain(&model);
            let speeds = measure(plain, drafting, &model, &edit, tests)?;
            ("CPU", "the CPU".to_owned(), speeds)
        }
    };
    let technologies = tech::status(off, kind, &MEASURED);
    let peak = peak_rss();
    let threads = rayon::current_num_threads();
    let header = file.source().header();
    let params: u64 = header.tensors.iter().map(|t| t.elements()).sum();
    let mut out = std::io::stdout().lock();

    if as_json {
        let report = json!({
            "model": path.display().to_string(),
            "backend": backend.to_lowercase(),
            "device": on,
            "threads": threads,
            "repetitions": repetitions,
            "load_seconds": load,
            "size_bytes": file.len(),
            "parameters": params,
            "prefill_tokens": PROMPT_TOKENS,
            "prefill_tokens_per_second": speeds.prefill,
            "decode_tokens": GENERATED_TOKENS,
            "decode_depth": tests.depth,
            "decode_tokens_per_second": speeds.decode,
            "edit_tokens": EDIT_TOKENS,
            "edit_tokens_per_second": speeds.edit,
            "edit_identical": speeds.edit_identical,
            "technologies": technologies,
            "peak_rss_bytes": peak,
        });
        writeln!(out, "{report:#}")?;
        return Ok(());
    }
    let size = format!("{:.2} GiB", file.len() as f64 / (1u64 << 30) as f64);
    let params = format!("{:.2} B", params as f64 / 1e9);
    writeln!(
        out,
        "| model | size | params | backend | threads | test | t/s |"
    )?;
    writeln!(out, "| --- | ---: | ---: | --- | ---: | ---: | ---: |")?;
    let decode = match tests.depth {
        0 => format!("tg{GENERATED_TOKENS}"),
        d => format!("tg{GENERATED_TOKENS} @ d{d}"),
    };
    for (test, speed) in [
        (format!("pp{PROMPT_TOKENS}"), speeds.prefill),
        (decode, speeds.decode),
        (format!("edit{EDIT_TOKENS}"), speeds.edit),
    ] {
        writeln!(
            out,
            "| {name} | {size} | {params} | {backend} | {threads} | {test} | {speed:.2} |"
        )?;
    }
    writeln!(out)?;
    writeln!(out, "on {on}, best of {repetitions}, load {load:.2} s")?;
    writeln!(
        out,
        "speed technologies {technologies}; Warm Start, Zero Wait and Convoy take no part"
    )?;
    let identical = if speeds.edit_identical { "yes" } else { "NO" };
    writeln!(
        out,
        "edit: drafted output identical to plain decoding: {identical}"
    )?;
    if let Some(bytes) = peak {
        writeln!(
            out,
            "peak memory {:.2} GiB",
            bytes as f64 / (1u64 << 30) as f64
        )?;
    }
    if speeds.edit_identical {
        Ok(())
    } else {
        Err("drafted decoding changed the output".into())
    }
}

/// A GPU backend that never drafts.
enum Plain<'a> {
    #[cfg(feature = "cuda")]
    Cuda(Box<kinetic_server::CudaBackend<'a>>),
    #[cfg(feature = "vulkan")]
    Vulkan(Box<kinetic_server::VulkanBackend<'a>>),
    // only carries 'a in a build without GPU backends
    #[cfg(not(any(feature = "cuda", feature = "vulkan")))]
    #[allow(dead_code)]
    Unavailable(std::convert::Infallible, std::marker::PhantomData<&'a ()>),
}

/// The plain backend of GPU kind `kind`, or `None` when this build lacks it.
#[cfg_attr(
    not(any(feature = "cuda", feature = "vulkan")),
    allow(unused_variables)
)]
fn plain<'a>(
    model: &'a Model<'a>,
    kind: Device,
    #[cfg_attr(
        not(any(feature = "cuda", feature = "vulkan")),
        allow(unused_variables)
    )]
    context: usize,
    #[cfg_attr(not(feature = "cuda"), allow(unused_variables))] eager: bool,
) -> Option<std::result::Result<Plain<'a>, LoadError>> {
    match kind {
        #[cfg(feature = "cuda")]
        Device::Cuda => {
            let placement = kinetic_models::cuda::Placement {
                eager,
                ..Default::default()
            };
            Some(
                kinetic_server::CudaBackend::with_placement(model, context, placement)
                    .map(|b| Plain::Cuda(Box::new(b.without_drafts()))),
            )
        }
        #[cfg(feature = "vulkan")]
        Device::Vulkan => Some(
            kinetic_server::VulkanBackend::plain(model, context)
                .map(|b| Plain::Vulkan(Box::new(b))),
        ),
        _ => None,
    }
}

/// Runs pp512 and tg128 (after `tests.depth` tokens) on `plain`, which
/// never drafts, and the edit test on it and then, once `plain` is dropped,
/// on the drafting backend that `drafting` makes.
fn measure<P: Backend, D: Backend>(
    mut plain: P,
    drafting: impl FnOnce() -> Result<D>,
    model: &Model,
    edit: &[u32],
    tests: Tests,
) -> Result<Speeds> {
    let vocab = model.n_vocab() as u64;
    let sequence = |n: usize| -> Vec<u32> {
        (0..n as u64)
            .map(|i| (i.wrapping_mul(2_654_435_761) % vocab) as u32)
            .collect()
    };
    let tokens = sequence(PROMPT_TOKENS);
    let context = sequence(tests.depth.max(1));
    let sampling = Sampling {
        temperature: 1.0,
        top_k: 1,
        ..Sampling::default()
    };
    let job = |max_tokens| Job {
        sampling: &sampling,
        max_tokens,
        stop_tokens: &[],
        grammar: None,
        images: &[],
        logprobs: None,
    };
    let mut ignore = |_: &[u32]| true;

    // Pages the weights in; it does not share a prefix with the tests.
    plain.generate(&tokens[1..17], &job(2), &mut ignore);
    let mut speeds = Speeds {
        prefill: 0.0,
        decode: 0.0,
        edit: 0.0,
        edit_identical: true,
    };
    for _ in 0..tests.repetitions {
        let t = plain.generate(&tokens, &job(1), &mut ignore);
        speeds.prefill = speeds
            .prefill
            .max(PROMPT_TOKENS as f64 / t.prefill.as_secs_f64());
        // The last token is sampled but never run, so one more is asked for.
        let t = plain.generate(&context, &job(GENERATED_TOKENS + 1), &mut ignore);
        speeds.decode = speeds
            .decode
            .max(GENERATED_TOKENS as f64 / t.decode.as_secs_f64());
    }

    let answer = |backend: &mut dyn Backend| {
        let mut tokens = Vec::new();
        let t = backend.generate(edit, &job(EDIT_TOKENS + 1), &mut |new: &[u32]| {
            tokens.extend_from_slice(new);
            true
        });
        (tokens, t.generated as f64 / t.decode.as_secs_f64())
    };
    let (expected, _) = answer(&mut plain);
    drop(plain);
    let mut drafting = drafting()?;
    for _ in 0..tests.repetitions {
        let (tokens, speed) = answer(&mut drafting);
        speeds.edit_identical &= tokens == expected;
        speeds.edit = speeds.edit.max(speed);
    }
    Ok(speeds)
}
