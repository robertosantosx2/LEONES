use clap::{Args, Parser, Subcommand};
use anyhow::Context;
use rusting_strata::memory;
use rusting_strata::model::{Model, State};
use rusting_strata::{backend, gpu_model::GpuModel};
use rusting_strata::{config::ModelConfig, gguf::Gguf, hf, ops, ops::Sampler, quant::GgmlType, serve, tokenizer::Tokenizer};
use rusting_strata::chat::{Hold, Msg, Template};
use serde_json::json;
use std::io::{BufRead, BufReader, Read, Write};
use std::{collections::BTreeMap, net::{TcpListener, TcpStream}, sync::atomic::Ordering::Relaxed, path::{Path, PathBuf}, time::{Duration, Instant, SystemTime}};

#[derive(Parser)]
#[command(name = "rustingstrata", version, about = "Rust inference engine for Qwen3.5/3.6-family GGUF models")]
struct Cli {
    /// Without a command, strata serves the chat page on 127.0.0.1:8080 on the GPU (else the CPU) and opens it in
    /// the browser.
    #[command(subcommand)]
    cmd: Option<Cmd>,
}

#[derive(Args, Clone)]
struct Engine {
    /// Run on the GPU (experts that do not fit in VRAM run on the CPU) instead of the CPU reference.
    #[arg(long)]
    gpu: bool,
    /// GPU context length (KV cache size) in tokens.
    #[arg(long, default_value_t = 4096)]
    ctx: usize,
    /// Prefill chunk in tokens (GPU; 0 = token by token) [default: calibrated, else 4096].
    #[arg(long)]
    chunk: Option<usize>,
    /// VRAM left free after placing expert layers, in MB.
    #[arg(long, default_value_t = 512)]
    vram_margin: usize,
    /// Speculative decoding with the model's MTP draft head, N drafts per step (GPU; greedy output unchanged, sampling keeps its distribution)
    /// [default: calibrated, else 0].
    #[arg(long, value_name = "N", default_missing_value = "1", num_args = 0..=1)]
    mtp: Option<usize>,
    /// Sampling temperature; 0 is greedy.
    #[arg(long, default_value_t = 0.0)]
    temp: f32,
    /// Sample only from the K most likely tokens (0 = all).
    #[arg(long, default_value_t = 0)]
    top_k: usize,
    #[arg(long, default_value_t = 1.0)]
    top_p: f32,
    /// Random seed for sampling [default: from the clock].
    #[arg(long)]
    seed: Option<u64>,
    /// CPU threads for expert work [default: calibrated, else all logical cores].
    #[arg(long)]
    threads: Option<usize>,
    /// Match llama.cpp's CPU numerics on the GPU (q8_K activations, f32 prefill attention, f16 decode attention
    /// accumulator) for parity runs; attention gets much slower.
    #[arg(long)]
    llama_numerics: bool,
    /// Place experts in layer order and never move them, ignoring and keeping the routing profile, so parity runs
    /// repeat exactly.
    #[arg(long)]
    fixed_experts: bool,
    /// Host RAM left free for the OS, in MB. The cap is `total RAM - margin` and bounds memory the process owns
    /// (baked tensors, LoRA factors, `--cache-ram`); the mmapped model is evictable page cache and is not counted.
    #[arg(long, default_value_t = 512)]
    ram_margin: usize,
    /// Absolute host RAM cap in MB; overrides `--ram-margin`. 0 uses the margin.
    #[arg(long, default_value_t = 0)]
    max_ram: usize,
    /// Host memory in MB for conversation states that a request with another history replaced (GPU): a later request
    /// that continues one of them takes it back instead of prefilling it again. 0 keeps none.
    #[arg(long, default_value_t = 4096)]
    cache_ram: usize,
    /// GGUF LoRA adapter(s) to apply at runtime as "path:scale" (repeatable; CPU and GPU).
    #[arg(long, value_name = "PATH:SCALE", action = clap::ArgAction::Append)]
    lora: Vec<String>,
    /// Keep the think block of earlier replies in the prompt (Qwen3.5/3.6 templates' `preserve_thinking`; a request
    /// can set it in `chat_template_kwargs`). The template drops it from replies before the last user message, so
    /// each new user message changes the earlier text and the whole conversation is prefilled again; with this, a
    /// coding agent's long history stays cached across user messages. `--preserve-thinking false` follows the
    /// template's default.
    #[arg(long, default_value_t = true, action = clap::ArgAction::Set, num_args = 0..=1, default_missing_value = "true")]
    preserve_thinking: bool,
    /// KV cache format (GPU): f16, or q8 (q8_0 blocks, half the KV memory; numerics differ slightly from
    /// llama.cpp's default f16 cache).
    #[arg(long, default_value = "f16", value_parser = ["f16", "q8"])]
    kv: String,
    /// GPU backend: cuda or vulkan [default: cuda if it loads, else vulkan].
    #[arg(long)]
    backend: Option<String>,
    /// GPU index, or several separated by commas (such as 0,1) to split the layers over those GPUs in proportion to
    /// their free VRAM.
    #[arg(long, default_value = "0", value_delimiter = ',')]
    device: Vec<usize>,
    /// Prompts shorter than this skip the batched prefill (from `strata calibrate`, else 32).
    #[arg(skip)]
    short: usize,
    /// Run on the CPU when no GPU backend opens (the bare `strata` launch).
    #[arg(skip)]
    cpu_fallback: bool,
    /// Sequences in GPU memory at once (`serve --parallel`).
    #[arg(skip)]
    parallel: usize,
}

/// `serve` options for a server that other people use (docs/HOSTING.md).
#[derive(clap::Args, Clone, Debug)]
struct Hosting {
    /// File of customer keys, one `name key` pair a line (`#` comments). These keys reach only the chat APIs and
    /// the model list, and each key's cached conversations are kept apart from the others'. `--api-key` stays
    /// the admin key for every route. A changed file is read again before the next request.
    #[arg(long)]
    api_keys: Option<PathBuf>,
    /// Append one JSON line per chat request (time, key name, token counts, timings, how it finished) to this file.
    #[arg(long)]
    usage_log: Option<PathBuf>,
    /// Open connections (being read, generated or queued, health checks included); more get `503` with `Retry-After`.
    #[arg(long, default_value_t = 16)]
    max_waiting: usize,
    /// Requests one customer key may have read, generated or queued at once; more get `429` with `Retry-After`
    /// [default: no limit besides `--max-waiting`].
    #[arg(long)]
    max_per_key: Option<usize>,
    /// Extra `Host` header names accepted by the chat page, model list and stats, comma-separated. Needed when the
    /// server is reached through a LAN name while bound to `0.0.0.0`. [default: $STRATA_ALLOWED_HOSTS]
    #[arg(long, value_delimiter = ',')]
    allowed_hosts: Vec<String>,
    /// Most reply tokens a request may ask for (and the default when it asks for none) [default: what the context
    /// leaves].
    #[arg(long)]
    max_tokens: Option<usize>,
    /// Requests answered at once (GPU): each gets its own slot of `--ctx` tokens of KV cache, and the
    /// slots that decode share each forward, up to 4 at a time. Between the chunks of a prompt's prefill the others
    /// decode for as long as the chunk took (a smaller `--chunk` gives shorter pauses). MTP drafting is off.
    #[arg(long, default_value_t = 1)]
    parallel: usize,
}

enum Runner<'a> { Cpu(&'a Model<'a>, State), Gpu(Box<GpuModel<'a>>), Slot(Client) }

impl Runner<'_> {
    fn step(&mut self, t: u32) -> anyhow::Result<Vec<f32>> {
        match self { Runner::Cpu(m, st) => Ok(m.step(st, t)), Runner::Gpu(g) => g.step(t), Runner::Slot(c) => Ok(c.step(t, true)?.1) }
    }
    /// Feed a prompt; returns the logits after its last token.
    fn prefill(&mut self, ts: &[u32]) -> anyhow::Result<Vec<f32>> {
        match self {
            Runner::Cpu(m, st) => Ok(ts.iter().map(|&t| m.step(st, t)).last().unwrap_or_default()),
            Runner::Gpu(g) => g.prefill(ts),
            Runner::Slot(_) => anyhow::bail!("prefill on a slot"),
        }
    }
    /// Feed a chat prompt as a fresh sequence, reusing the earlier request's state for the shared message history
    /// (GPU; `history` is the prompt without the assistant header, `system` its system and tools block, kept for
    /// later requests that rewrite the history). Returns the logits and the number of tokens reused.
    fn chat(&mut self, tok: &Tokenizer, prompt: &str, history: &str, system: &str) -> anyhow::Result<(Vec<u32>, Vec<f32>, usize)> {
        let ids = tok.encode(prompt)?;
        let h = tok.encode(history)?;
        let keep = if ids.starts_with(&h) { h.len() } else { 0 };
        let s = if system.is_empty() { vec![] } else { tok.encode(system)? };
        let sys = if ids.starts_with(&s) && s.len() <= keep { s.len() } else { 0 };
        let (logits, reused) = match self {
            Runner::Gpu(g) => g.prefill_cached(&ids, sys, keep)?,
            Runner::Slot(c) => c.chat(&ids, sys, keep)?,
            _ => { self.reset()?; (self.prefill(&ids)?, 0) }
        };
        Ok((ids, logits, reused))
    }
    /// Forget the sequence so far.
    fn reset(&mut self) -> anyhow::Result<()> {
        match self { Runner::Cpu(m, st) => { *st = State::new(&m.cfg); Ok(()) } Runner::Gpu(g) => g.reset(), Runner::Slot(_) => Ok(()) }
    }
    /// Seconds spent waiting on CPU experts so far (GPU only).
    fn cpu_secs(&self) -> f64 { if let Runner::Gpu(g) = self { g.parts().map(|p| p.cpu_time.as_secs_f64()).sum() } else { 0.0 } }
    /// Bytes of routed-expert weights one decode token reads from the cache (0 without an expert cache).
    fn expert_bytes_per_token(&self) -> usize {
        if let Runner::Gpu(g) = self { g.parts().map(|p| p.expert_bytes_per_token()).sum() } else { 0 }
    }
    /// Split model: seconds per part but the last (forward until its GPU is done, copy to the next part).
    fn split_secs(&self) -> Vec<(f64, f64)> {
        let Runner::Gpu(g) = self else { return vec![] };
        let mut v: Vec<_> = g.parts().map(|p| (p.split_time.0.as_secs_f64(), p.split_time.1.as_secs_f64())).collect();
        v.pop();
        v
    }
    /// Backend name of the first part (`"cpu"` on the CPU, `"slot"` for a serve slot).
    fn backend_name(&self) -> &'static str {
        match self {
            Runner::Cpu(..) => "cpu",
            Runner::Gpu(g) => g.parts().next().map_or("cpu", |p| p.gpu.name()),
            Runner::Slot(_) => "slot",
        }
    }
    /// Expert-cache counters summed over the parts, for `finish()` and the benchmark JSON (`None` off the GPU).
    fn expert_stats(&self) -> Option<ExpertStats> {
        let Runner::Gpu(g) = self else { return None };
        let sum = |f: &dyn Fn(&GpuModel) -> usize| g.parts().map(f).sum::<usize>();
        let parts: Vec<_> = g.parts().collect();
        let cached: Vec<_> = parts.iter().filter(|p| p.cache.is_some()).collect();
        Some(ExpertStats {
            hits: sum(&|p| p.hits),
            misses: sum(&|p| p.misses),
            swaps: sum(&|p| p.cache.as_ref().map_or(0, |c| c.swaps)),
            resident: sum(&|p| p.cache.as_ref().map_or(0, |c| c.resident_count())),
            total: sum(&|p| p.cache.as_ref().map_or(0, |c| c.total_experts())),
            bytes_per_token: sum(&|p| p.expert_bytes_per_token()),
            cached: !cached.is_empty(),
            all_fast: cached.iter().all(|p| p.expert_fast_path()),
        })
    }
    /// The same counters, but only when an expert cache exists (the benchmark record's top-level `expert`).
    fn expert_summary(&self) -> Option<ExpertStats> {
        self.expert_stats().filter(|s| s.cached)
    }
    fn finish(&self) -> anyhow::Result<()> {
        if let Runner::Gpu(g) = self {
            let sum = |f: &dyn Fn(&GpuModel) -> usize| g.parts().map(f).sum::<usize>();
            let st = self.expert_stats().expect("Runner::Gpu has expert stats");
            if g.drafts.0 > 0 { eprintln!("MTP drafts accepted {}/{} ({:.1}%)", g.drafts.1, g.drafts.0, 100.0 * g.drafts.1 as f64 / g.drafts.0 as f64); }
            eprintln!("expert hit rate {:.1}% ({} misses), cache swaps {}", 100.0 * st.hits as f64 / (st.hits + st.misses).max(1) as f64, st.misses, st.swaps);
            // Issue #34 R1: printed on every run, so a fully resident run reads as a measured 0 in the log instead of
            // an absent line. `tokens` counts the token forwards the worker could have been asked about.
            let tokens = sum(&|p| p.tokens);
            let busy: f64 = g.parts().map(|p| p.cpu_time.as_secs_f64()).sum();
            let stalls = sum(&|p| p.resumed.get());
            eprintln!("worker busy {:.1} µs/token, worker stalls {stalls}", if tokens > 0 { 1e6 * busy / tokens as f64 } else { 0.0 });
            let mode = if !st.cached { "no expert cache".to_string() }
                else if st.all_fast { format!("fast path on, {}/{} experts resident", st.resident, st.total) }
                else { format!("fast path off, {}/{} experts resident", st.resident, st.total) };
            eprintln!("mailbox traffic: {} GPU writes, {} host routing reads ({mode})", sum(&|p| p.mailbox_writes.get()), sum(&|p| p.mailbox_reads.get()));
            for p in g.parts() { if let Some(c) = &p.cache { c.save_profile()?; } }
        }
        Ok(())
    }
}

impl Engine {
    /// Fills settings not given on the command line from the model's calibration file, else built-in defaults.
    fn ram_cap(&self) -> Option<u64> { memory::ram_cap((self.ram_margin as u64) << 20, (self.max_ram as u64) << 20) }
    fn runner<'a>(&mut self, m: &'a Model<'a>, model: &Path) -> anyhow::Result<Runner<'a>> {
        if let Some(cap) = self.ram_cap() {
            let used = m.ram_estimate() as u64;
            anyhow::ensure!(used <= cap, "model needs ~{} MB of host RAM (baked tensors, LoRA), over the {} MB cap; lower --ram-margin or raise --max-ram", used >> 20, cap >> 20);
            let want = (self.cache_ram as u64) << 20;
            let room = cap - used;
            if want > room {
                eprintln!("RAM cap: clamping --cache-ram from {} MB to {} MB", self.cache_ram, room >> 20);
                self.cache_ram = (room >> 20) as usize;
            }
        }
        if self.llama_numerics { unsafe { std::env::set_var("STRATA_LLAMA_NUMERICS", "1") } }  // read by Gpu::new
        if self.kv == "q8" { unsafe { std::env::set_var("STRATA_KV_Q8", "1") } }  // read by Gpu::new and Vk::new
        let open = || self.device.iter().map(|&d| backend::open(self.backend.as_deref(), d)).collect::<anyhow::Result<Vec<_>>>();
        let bk = match self.gpu.then(open).transpose() {
            Err(e) if self.cpu_fallback => { eprintln!("no GPU backend ({e:#}), running on the CPU"); None }
            r => r?,
        };
        let path = calibration_path(model, bk.as_ref().map_or("cuda", |b| b[0].name()));
        let v: serde_json::Value = std::fs::read(&path).ok().and_then(|b| serde_json::from_slice(&b).ok()).unwrap_or_default();
        if !v.is_null() { eprintln!("calibration: {}", path.display()); }
        let get = |k: &str| v[k].as_u64().map(|x| x as usize);
        self.chunk.get_or_insert(get("chunk").unwrap_or(4096));
        self.mtp.get_or_insert(get("mtp").unwrap_or(0));
        self.short = get("short").unwrap_or(32);
        // The global pool can be built once; a model loaded later by `serve` keeps the first one's threads.
        if let Some(n) = self.threads.or(get("threads")) { let _ = rayon::ThreadPoolBuilder::new().num_threads(n).build_global(); }
        let Some(bk) = bk else {
            let (notes, _, mtp) = resolve_flags(false, self.parallel, self.mtp(), m.cfg.n_nextn, m.cfg.hc_n, false)?;
            for n in notes { eprintln!("{n}"); }
            self.mtp = Some(mtp);
            return Ok(Runner::Cpu(m, State::new(&m.cfg)));
        };
        let split = bk.len() > 1;
        let (notes, parallel, mtp) = resolve_flags(true, self.parallel, self.mtp(), m.cfg.n_nextn, m.cfg.hc_n, split)?;
        for n in notes { eprintln!("{n}"); }
        (self.parallel, self.mtp) = (parallel, Some(mtp));
        if self.fixed_experts { unsafe { std::env::set_var("STRATA_FIXED_EXPERTS", "1") } }  // read by ExpertCache::new
        // Before the first weight is uploaded: fail if a pipeline these weight types need does not fit the device's
        // shared memory (Vulkan; a no-op elsewhere). No pipeline or model buffer exists yet.
        let types = rusting_strata::gpu_model::gpu_weight_types(&m.w.g);
        for b in &bk { b.preflight(&types, false)?; }
        let mut g = if self.parallel > 1 {
            GpuModel::load_split(m, bk, self.ctx, self.chunk(), self.vram_margin << 20, 0, self.parallel).context(LOAD_HINT)?
        } else {
            GpuModel::load_split(m, bk, self.ctx, self.chunk(), self.vram_margin << 20, self.mtp(), 1).context(LOAD_HINT)?
        };
        g.short = self.short;
        g.cache_ram = self.cache_ram << 20;
        Ok(Runner::Gpu(Box::new(g)))
    }
    fn sampler(&self) -> Sampler {
        Sampler { temp: self.temp, top_k: self.top_k, top_p: self.top_p, rng: seed(self.seed) }
    }
    fn chunk(&self) -> usize { self.chunk.unwrap_or(4096) }
    fn mtp(&self) -> usize { self.mtp.unwrap_or(0) }
}

/// The negative log-likelihood of `tok` under `logits`, and in `row` the log-probabilities as llama-perplexity stores
/// them: scale and minimum as two f32, then each logit as a u16 step over the 16 nats below the largest (0 below
/// that), padded to an even count. Same arithmetic as its `log_softmax`.
fn log_probs(logits: &[f32], tok: u32, row: &mut Vec<u16>) -> f64 {
    let max = logits.iter().fold(f32::NEG_INFINITY, |a, &b| a.max(b));
    let min = logits.iter().fold(f32::INFINITY, |a, &b| a.min(b)).max(max - 16.0);
    let lse = logits.iter().map(|&x| (x - max).exp() as f64).sum::<f64>().ln() as f32;
    let scale = (max - min) / 65535.0;
    row.clear();
    for f in [scale, min - max - lse] { let b = f.to_bits(); row.extend([b as u16, (b >> 16) as u16]); }
    row.extend(logits.iter().map(|&x| if scale != 0.0 && x > min { ((x - min) * (1.0 / scale)).round_ties_even() as u16 } else { 0 }));
    if logits.len() % 2 == 1 { row.push(0); }
    (max + lse - logits[tok as usize]) as f64
}

/// A nonzero xorshift state from `s`, or from the clock.
fn seed(s: Option<u64>) -> u64 {
    s.unwrap_or_else(|| SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).map_or(1, |d| d.as_nanos() as u64))
        .wrapping_mul(0x9e37_79b9_7f4a_7c15) | 1
}

const LOAD_HINT: &str = "loading the model onto the GPU failed (if VRAM ran out: lower --ctx, add --kv q8, or close programs using VRAM)";

/// Settle the flag combinations that cannot all take effect: an invalid request (`--parallel` outside 1..=255) is an
/// error; a feature that cannot run is turned off with one message naming the flag and the reason. `parallel` 0 means
/// "not set" (commands other than `serve`), treated as one slot. Returns the notices, the slots in effect and the MTP
/// drafts in effect.
fn resolve_flags(gpu: bool, parallel: usize, mtp: usize, n_nextn: usize, hc_n: usize, split: bool) -> anyhow::Result<(Vec<String>, usize, usize)> {
    let p = parallel.max(1);
    anyhow::ensure!((1..=255).contains(&p), "--parallel {parallel}: 1 to 255 slots");
    let mut notes = vec![];
    if !gpu {
        if p > 1 { notes.push(format!("--parallel {p}: requires --gpu (the CPU answers one request at a time)")); }
        if mtp > 0 { notes.push(format!("--mtp {mtp}: requires --gpu: decoding without drafts")); }
        return Ok((notes, p, 0));
    }
    if p > 1 && mtp > 0 {
        notes.push(format!("--parallel {p} and --mtp {mtp}: not supported together, decoding without MTP drafts"));
        return Ok((notes, p, 0));
    }
    let why = if mtp == 0 { None }
        else if split { Some("not available with a multi-GPU layer split") }
        else if hc_n > 0 { Some("not supported for this model (hyper-connections)") }
        else if n_nextn == 0 { Some("this model has no MTP head") }
        else { None };
    let mut k = mtp;
    if let Some(why) = why { notes.push(format!("--mtp {mtp}: {why}: decoding without drafts")); k = 0; }
    Ok((notes, p, k))
}

/// Calibration file for `model` on `backend`; CUDA keeps the original name.
fn calibration_path(model: &Path, backend: &str) -> PathBuf {
    let stem = model.file_stem().and_then(|s| s.to_str()).unwrap_or("model");
    let sfx = if backend == "cuda" { String::new() } else { format!("-{backend}") };
    rusting_strata::expert_cache::cache_dir().join(format!("strata-{stem}{sfx}.json"))
}

impl Engine {
    pub fn lora_specs(&self) -> Vec<(String, f32)> {
        self.lora.iter().map(|s| {
            if let Some(idx) = s.rfind(':') {
                if let Ok(scale) = s[idx+1..].parse::<f32>() {
                    return (s[..idx].to_string(), scale);
                }
            }
            (s.clone(), 1.0)
        }).collect()
    }
}

/// Expert-cache counters summed over the GPU parts (`Runner::finish` and the benchmark JSON share them).
#[derive(Debug, Clone, Copy, PartialEq)]
struct ExpertStats {
    hits: usize,
    misses: usize,
    swaps: usize,
    resident: usize,
    total: usize,
    bytes_per_token: usize,
    /// At least one part has an expert cache.
    cached: bool,
    /// Every part with a cache takes the fully-resident fast path.
    all_fast: bool,
}

/// Round to the one decimal the text block prints, so the JSON carries exactly those digits (no second, different
/// rounding of the raw float).
fn round1(x: f64) -> f64 {
    format!("{x:.1}").parse().unwrap_or(x)
}

/// Mean/min/max of a benchmark series. The text block and the JSON record both read these fields, so the numbers
/// cannot drift apart.
#[derive(Debug, Clone, Copy, PartialEq)]
struct Stat {
    mean: f64,
    min: f64,
    max: f64,
}

impl Stat {
    fn of(v: &[f64]) -> Self {
        if v.is_empty() { return Self { mean: 0.0, min: 0.0, max: 0.0 }; }
        // The same fold as the text block always used, so formatting cannot change any printed digit.
        let (lo, hi) = v.iter().fold((f64::INFINITY, 0f64), |(a, b), &x| (a.min(x), b.max(x)));
        Self { mean: round1(v.iter().sum::<f64>() / v.len() as f64), min: round1(lo), max: round1(hi) }
    }
    /// The `MEAN (MIN-MAX)` field of the `pp …` line.
    fn text(&self) -> String { format!("{:.1} ({:.1}-{:.1})", self.mean, self.min, self.max) }
}

/// The run-wide values of a `strata bench` invocation (`strata.bench.v1`).
struct BenchMeta<'a> {
    backend: &'a str,
    backend_arg: Option<&'a str>,
    device: &'a [usize],
    model: &'a Path,
    ctx: usize,
    chunk: usize,
    kv: &'a str,
    mtp: usize,
    tg: usize,
    reps: usize,
}

/// One `--pp` length: the two `Stat`s the text prints and what the expert record needs.
struct BenchResult {
    pp: usize,
    prefill: Stat,
    decode: Stat,
    /// Bytes of expert weights one decode token reads (0 without an expert cache: no `expert` object).
    bytes_per_token: usize,
    /// The same median decode rate the `expert traffic:` line prints.
    decode_median: f64,
}

/// The `strata.bench.v1` record. Pure so it can be tested without a model or a GPU.
fn bench_record(meta: &BenchMeta, results: &[BenchResult], expert: Option<&ExpertStats>, unix_time: u64) -> serde_json::Value {
    let mut v = json!({
        "schema": "strata.bench.v1",
        "unix_time": unix_time,
        "backend": meta.backend,
        "device": meta.device,
        "model": {
            "path": meta.model.display().to_string(),
            "name": meta.model.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default(),
        },
        "ctx": meta.ctx,
        "chunk": meta.chunk,
        "kv": meta.kv,
        "mtp": meta.mtp,
        "tg": meta.tg,
        "reps": meta.reps,
    });
    if let Some(b) = meta.backend_arg { v["backend_arg"] = json!(b); }
    let results: Vec<_> = results.iter().map(|r| {
        let mut o = json!({
            "pp": r.pp,
            "prefill_tok_s": {"mean": r.prefill.mean, "min": r.prefill.min, "max": r.prefill.max},
            "decode_tok_s": {"mean": r.decode.mean, "min": r.decode.min, "max": r.decode.max},
        });
        if r.bytes_per_token > 0 {
            o["expert"] = json!({
                "bytes_per_token": r.bytes_per_token,
                "mb_per_token": round1(r.bytes_per_token as f64 / 1048576.0),
                "gb_per_s": round1(r.bytes_per_token as f64 * r.decode_median / 1e9),
                "at_decode_tok_s": round1(r.decode_median),
            });
        }
        o
    }).collect();
    v["results"] = json!(results);
    if let Some(e) = expert {
        v["expert"] = json!({
            "hit_rate_pct": round1(100.0 * e.hits as f64 / (e.hits + e.misses).max(1) as f64),
            "misses": e.misses,
            "swaps": e.swaps,
            "resident": e.resident,
            "total": e.total,
            "bytes_per_token": e.bytes_per_token,
            "mb_per_token": round1(e.bytes_per_token as f64 / 1048576.0),
        });
    }
    v
}

/// `--json-out` values: a file path, never `-` (stdout keeps the text block).
fn json_out_path(s: &str) -> Result<PathBuf, String> {
    if s == "-" {
        Err("`-` is not a file: stdout carries the text block, give a path".into())
    } else {
        Ok(PathBuf::from(s))
    }
}

#[derive(Subcommand)]
enum Cmd {
    /// Print model config and tensor type histogram.
    Info {
        #[arg(long)]
        model: PathBuf,
    },
    /// Teacher-force token ids; print argmax and top-5 logprobs for each continuation position.
    /// Input JSON: {"prompt": [ids], "continuation": [ids]} ("-" reads stdin).
    Score {
        #[arg(long)]
        model: PathBuf,
        #[arg(long)]
        input: String,
        #[command(flatten)]
        engine: Engine,
    },
    /// Interactive chat on stdin (greedy unless --temp; on the GPU each turn prefills only what follows the previous turn's messages).
    Chat {
        #[arg(long)]
        model: PathBuf,
        #[arg(long)]
        system: Option<String>,
        /// Max tokens per reply.
        #[arg(short, default_value_t = 2048)]
        n: usize,
        /// Let the model think before answering (template default; off here).
        #[arg(long)]
        think: bool,
        #[command(flatten)]
        engine: Engine,
    },
    /// OpenAI-compatible HTTP server: POST /v1/chat/completions (streaming or not), GET /v1/models.
    /// One request at a time; temperature, top_k, top_p and seed are honored, greedy when left out. A request that
    /// extends the previous one's messages prefills only the new part (usage.prompt_tokens_details.cached_tokens);
    /// one that keeps only the system prompt and tools (a compacted conversation) starts after them.
    /// GET / is a chat page that can also switch between the models in `--models-dir` (POST /api/load), so the
    /// server can start without `--model`.
    Serve {
        #[arg(long)]
        model: Option<PathBuf>,
        /// Folder of .gguf models the chat page offers [default: $XDG_DATA_HOME/rusting_strata/models,
        /// %LOCALAPPDATA%\rusting_strata\models on Windows, else ~/.local/share/rusting_strata/models].
        #[arg(long)]
        models_dir: Option<PathBuf>,
        #[arg(long, default_value = "127.0.0.1:8080")]
        addr: String,
        /// Open the chat page in the browser (if the address is taken, open it and exit: strata already runs there).
        #[arg(long)]
        open: bool,
        /// Require `Authorization: Bearer <key>` on every request [default: $STRATA_API_KEY, which keeps the key out
        /// of the process list].
        #[arg(long)]
        api_key: Option<String>,
        #[command(flatten)]
        host: Hosting,
        #[command(flatten)]
        engine: Engine,
    },
    /// Measure prefill chunk, MTP drafts per step and the short-prompt threshold on this machine (GPU) and write
    /// them to the model's calibration file, which later runs read unless flags override.
    Calibrate {
        #[arg(long)]
        model: PathBuf,
        /// GPU context length used while measuring and assumed for the results.
        #[arg(long, default_value_t = 4096)]
        ctx: usize,
        #[arg(long, default_value_t = 512)]
        vram_margin: usize,
        #[arg(long)]
        backend: Option<String>,
        /// GPU index, or several separated by commas (such as 0,1) to calibrate the layer split over those GPUs.
        #[arg(long, default_value = "0", value_delimiter = ',')]
        device: Vec<usize>,
        /// Accepted for consistency with the other commands; calibration always uses the base model.
        #[arg(long, value_name = "PATH:SCALE", action = clap::ArgAction::Append)]
        lora: Vec<String>,
        /// KV cache format to calibrate with (q8 leaves more VRAM for experts), as `--kv` of the runs that use it.
        #[arg(long, default_value = "f16", value_parser = ["f16", "q8"])]
        kv: String,
        /// Accepted for symmetry with the other commands: calibration always runs on the GPU.
        #[arg(long, hide = true)]
        gpu: bool,
    },
    /// Check that every Vulkan pipeline this model needs fits the device's `maxComputeSharedMemorySize`, naming the
    /// kernel, specialization, bytes needed and limit when one does not; exits non-zero on overflow. No model is
    /// loaded, no weight uploaded and no pipeline created: it is SPIR-V plus spec-constant arithmetic only.
    Check {
        #[arg(long)]
        model: PathBuf,
        #[arg(long)]
        backend: Option<String>,
        #[arg(long, default_value_t = 0)]
        device: usize,
    },
    /// Speed test: for each prompt length, prefill that many tokens of prose, then greedily decode `tg` more at that
    /// depth. Prints prefill and decode tok/s as mean (min-max) over `reps` runs. `--ctx` grows to fit.
    /// `--json-out PATH` also writes the same numbers as one `strata.bench.v1` JSON object plus a newline (`-` is
    /// rejected: stdout keeps the text block).
    Bench {
        #[arg(long)]
        model: PathBuf,
        #[arg(long, value_delimiter = ',', default_value = "512,4096")]
        pp: Vec<usize>,
        #[arg(long, default_value_t = 128)]
        tg: usize,
        #[arg(long, default_value_t = 3)]
        reps: usize,
        #[arg(long, value_parser = json_out_path)]
        json_out: Option<PathBuf>,
        #[command(flatten)]
        engine: Engine,
    },
    /// Perplexity over a text file as llama-perplexity computes it: chunks of `ctx-len` tokens, each from an empty
    /// context, scored over their second half (the first half prefilled, the rest decoded token by token).
    /// `--kld-base` writes the log-probabilities in llama-perplexity's format, so
    /// `llama-perplexity -m MODEL --kl-divergence --kl-divergence-base FILE` compares llama.cpp's logits with these
    /// (KLD, top-token agreement and both perplexities) on the same tokens.
    Perplexity {
        #[arg(long)]
        model: PathBuf,
        #[arg(long)]
        file: PathBuf,
        #[arg(long, default_value_t = 512)]
        ctx_len: usize,
        /// Score only the first N chunks.
        #[arg(long)]
        chunks: Option<usize>,
        #[arg(long)]
        kld_base: Option<PathBuf>,
        #[command(flatten)]
        engine: Engine,
    },
    /// Text generation (greedy unless --temp).
    Generate {
        #[arg(long)]
        model: PathBuf,
        /// Prompt text ("-" reads stdin; long prompts exceed the 128 KiB argument limit).
        #[arg(long)]
        prompt: String,
        #[arg(short, default_value_t = 32)]
        n: usize,
        #[command(flatten)]
        engine: Engine,
    },
}

fn main() -> anyhow::Result<()> {
    let Some(cmd) = Cli::parse().cmd else {
        // Started without arguments, as by a double click: keep the window open on an error so it can be read.
        let Some(Cmd::Serve { model, models_dir, addr, api_key, open, host, mut engine }) = Cli::parse_from(["rustingstrata", "serve", "--gpu", "--open"]).cmd else { unreachable!() };
        engine.cpu_fallback = true;
        let r = run(Cmd::Serve { model, models_dir, addr, api_key, open, host, engine });
        if let Err(e) = &r {
            eprintln!("error: {e:#}\npress Enter to close");
            let _ = std::io::stdin().read_line(&mut String::new());
        }
        return r;
    };
    run(cmd)
}

fn run(cmd: Cmd) -> anyhow::Result<()> {
    match cmd {
        Cmd::Info { model } => {
            let g = Gguf::open(&model)?;
            println!("{:#?}", ModelConfig::from_gguf(&g)?);
            let mut hist = BTreeMap::<String, usize>::new();
            for t in g.tensors.values() {
                let name = GgmlType::from_u32(t.ty).map(|ty| ty.name().to_string()).unwrap_or(format!("type{}", t.ty));
                *hist.entry(name).or_default() += 1;
            }
            for (ty, n) in hist { println!("{n:5} {ty}"); }
        }
        Cmd::Score { model, input, mut engine } => {
            let text = if input == "-" {
                let mut s = String::new();
                std::io::stdin().read_to_string(&mut s)?;
                s
            } else {
                std::fs::read_to_string(&input)?
            };
            let v: serde_json::Value = serde_json::from_str(&text)?;
            let ids = |k: &str| -> anyhow::Result<Vec<u32>> {
                v[k].as_array().with_context(|| format!("missing {k}"))?
                    .iter().map(|x| x.as_u64().and_then(|x| u32::try_from(x).ok()).context("bad id")).collect()
            };
            let (prompt, cont) = (ids("prompt")?, ids("continuation")?);
            anyhow::ensure!(!prompt.is_empty() && !cont.is_empty(), "empty prompt or continuation");
            let g = Gguf::open(&model)?;
            let mut m = Model::load(&g)?;
            if !engine.lora.is_empty() { m.apply_lora(&engine.lora_specs())?; }
            if let Some(&t) = prompt.iter().chain(&cont).find(|&&t| t as usize >= m.cfg.n_vocab) {
                anyhow::bail!("token id {t} out of range (vocabulary has {} tokens)", m.cfg.n_vocab);
            }
            let mut r = engine.runner(&m, &model)?;
            let feed: Vec<u32> = prompt.iter().chain(&cont[..cont.len() - 1]).copied().collect();
            let (mut argmax, mut top5) = (Vec::new(), Vec::new());
            let mut logits = r.prefill(&prompt)?;
            for i in prompt.len() - 1..feed.len() {
                if i >= prompt.len() { logits = r.step(feed[i])?; }
                let lse = logits.iter().fold(f32::NEG_INFINITY, |a, &b| a.max(b));
                let lse = lse + logits.iter().map(|x| (x - lse).exp()).sum::<f32>().ln();
                argmax.push(ops::argmax(&logits));
                top5.push(ops::top_k(&logits, 5).into_iter().map(|j| (j, logits[j] - lse)).collect::<Vec<_>>());
            }
            r.finish()?;
            println!("{}", serde_json::json!({"argmax": argmax, "top5": top5}));
        }
        Cmd::Generate { model, prompt, n, mut engine } => {
            let g = Gguf::open(&model)?;
            if g.get("general.architecture").ok().and_then(|v| v.as_str()) == Some("gemma4") {
                let prompt = if prompt == "-" { let mut s = String::new(); std::io::stdin().read_to_string(&mut s)?; s } else { prompt };
                return rusting_strata::gemma4::generate(&g, &prompt, n);
            }
            if g.get("general.architecture").ok().and_then(|v| v.as_str()) == Some("glm5-next") {
                let prompt = if prompt == "-" { let mut s = String::new(); std::io::stdin().read_to_string(&mut s)?; s } else { prompt };
                return rusting_strata::glm::generate(&g, &prompt, n);
            }
            if g.get("general.architecture").ok().and_then(|v| v.as_str()) == Some("deepseek41") {
                let prompt = if prompt == "-" { let mut s = String::new(); std::io::stdin().read_to_string(&mut s)?; s } else { prompt };
                return rusting_strata::deepseek::chat::generate(&g, &prompt, n);
            }
            let mut m = Model::load(&g)?;
            if !engine.lora.is_empty() { m.apply_lora(&engine.lora_specs())?; }
            let tok = Tokenizer::from_gguf(&g)?;
            let prompt = if prompt == "-" {
                let mut s = String::new();
                std::io::stdin().read_to_string(&mut s)?;
                s
            } else { prompt };
            let ids = tok.encode(&prompt)?;
            anyhow::ensure!(!ids.is_empty(), "empty prompt");
            let mut r = engine.runner(&m, &model)?;
            let t0 = Instant::now();
            let logits = r.prefill(&ids)?;
            let t1 = Instant::now();
            let (cpu0, split0) = (r.cpu_secs(), r.split_secs());
            let cap = room(&engine, ids.len(), n);
            let (out, _) = decode(&mut r, &tok, engine.mtp() > 0, &mut engine.sampler(), logits, cap, &mut |t| { print!("{t}"); std::io::stdout().flush()?; Ok(false) })?;
            let (pp, tg) = ((t1 - t0).as_secs_f64(), t1.elapsed().as_secs_f64());
            if out.len() == cap && cap < n { eprint!("\n(stopped: the context is full at {} tokens; raise --ctx)", engine.ctx); }
            eprintln!("\nprompt {} tok {:.2} tok/s | gen {} tok {:.2} tok/s", ids.len(), ids.len() as f64 / pp, out.len(), out.len() as f64 / tg);
            if engine.gpu { eprintln!("CPU expert compute, share of gen time: {:.1}%", 100.0 * (r.cpu_secs() - cpu0) / tg); }
            let ms = |s: f64| 1e3 * s / out.len().max(1) as f64;
            for (i, ((a, b), (a0, b0))) in r.split_secs().into_iter().zip(split0).enumerate() {
                eprintln!("device {i}: {:.2} ms/token forward, {:.2} ms/token copy to the next device", ms(a - a0), ms(b - b0));
            }
            if !r.split_secs().is_empty() { eprintln!("gen total {:.2} ms/token", ms(tg)); }
            r.finish()?;
        }
        Cmd::Perplexity { model, file, ctx_len: n, chunks, kld_base, mut engine } => {
            let g = Gguf::open(&model)?;
            let mut m = Model::load(&g)?;
            if !engine.lora.is_empty() { m.apply_lora(&engine.lora_specs())?; }
            let tok = Tokenizer::from_gguf(&g)?;
            // ponytail: no BOS at chunk starts (llama-perplexity adds one where the vocabulary asks for it; Qwen does not)
            let ids = tok.encode(&std::fs::read_to_string(&file)?)?;
            let n_chunk = (ids.len() / n).min(chunks.unwrap_or(usize::MAX));
            anyhow::ensure!(n >= 4 && n_chunk > 0, "{} tokens: need at least one chunk of --ctx-len {n} (>= 4)", ids.len());
            engine.ctx = engine.ctx.max(n);
            let mut r = engine.runner(&m, &model)?;
            let nv = m.cfg.n_vocab;
            let mut out = kld_base.map(|p| std::fs::File::create(p).map(std::io::BufWriter::new)).transpose()?;
            if let Some(o) = &mut out {
                o.write_all(b"_logits_")?;
                for v in [n, nv, n_chunk] { o.write_all(&(v as u32).to_le_bytes())?; }
                for &t in &ids[..n_chunk * n] { o.write_all(&t.to_le_bytes())?; }
            }
            let (mut nll, mut count, mut row) = (0f64, 0usize, Vec::new());
            let first = n / 2;
            for c in ids.chunks_exact(n).take(n_chunk) {
                r.reset()?;
                let mut logits = r.prefill(&c[..=first])?;
                for i in first..n - 1 {
                    if i > first { logits = r.step(c[i])?; }
                    anyhow::ensure!(logits.len() == nv, "{} logits, vocabulary {nv}", logits.len());
                    nll += log_probs(&logits, c[i + 1], &mut row);
                    if let Some(o) = &mut out { for v in &row { o.write_all(&v.to_le_bytes())?; } }
                    count += 1;
                }
                eprint!("[{}]{:.4},", count / (n - 1 - first), (nll / count as f64).exp());
            }
            if let Some(o) = &mut out { o.flush()?; }
            println!("\nPPL = {:.4} over {n_chunk} chunks of {n} tokens ({count} scored)", (nll / count as f64).exp());
            r.finish()?;
        }
        Cmd::Bench { model, pp, tg, reps, json_out, mut engine } => {
            let g = Gguf::open(&model)?;
            let mut m = Model::load(&g)?;
            if !engine.lora.is_empty() { m.apply_lora(&engine.lora_specs())?; }
            let tok = Tokenizer::from_gguf(&g)?;
            engine.ctx = engine.ctx.max(pp.iter().max().unwrap_or(&0) + tg);
            let mut r = engine.runner(&m, &model)?;
            let mut results = Vec::with_capacity(pp.len());
            for n in pp {
                let ids = prose(&tok, n)?;
                let (mut p, mut d) = (Vec::new(), Vec::new());
                for _ in 0..reps {
                    r.reset()?;
                    let t = Instant::now();
                    let l = r.prefill(&ids)?;
                    p.push(n as f64 / t.elapsed().as_secs_f64());
                    let t = Instant::now();
                    let k = decode(&mut r, &tok, engine.mtp() > 0, &mut Sampler::greedy(), l, tg, &mut |_| Ok(false))?.0.len();
                    d.push(k as f64 / t.elapsed().as_secs_f64());
                }
                let (prefill, decode_stat) = (Stat::of(&p), Stat::of(&d));
                println!("pp {n:6}: prefill {} tok/s | tg {tg}: decode {} tok/s", prefill.text(), decode_stat.text());
                // R3: the attained expert-read bandwidth (bytes per token x tokens per second), against the ~900 GB/s
                // of the V100, for the prefetch decision the window records.
                let eb = r.expert_bytes_per_token();
                let mid = if eb > 0 {
                    let mid = { let mut v = d.clone(); v.sort_by(f64::total_cmp); v[v.len() / 2] };
                    eprintln!("expert traffic: {:.1} MB/token -> {:.1} GB/s at {mid:.1} tok/s", eb as f64 / 1048576.0, eb as f64 * mid / 1e9);
                    mid
                } else { 0.0 };
                results.push(BenchResult { pp: n, prefill, decode: decode_stat, bytes_per_token: eb, decode_median: mid });
            }
            r.finish()?;
            // After `finish()`: the expert counters are final, and the record cannot reorder `save_profile()`.
            if let Some(path) = json_out {
                let device: &[usize] = if r.backend_name() == "cpu" { &[] } else { &engine.device };
                let meta = BenchMeta {
                    backend: r.backend_name(),
                    backend_arg: engine.backend.as_deref(),
                    device,
                    model: &model,
                    ctx: engine.ctx,
                    chunk: engine.chunk(),
                    kv: &engine.kv,
                    mtp: engine.mtp(),
                    tg,
                    reps,
                };
                let unix_time = SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).map_or(0, |d| d.as_secs());
                let record = bench_record(&meta, &results, r.expert_summary().as_ref(), unix_time);
                let mut line = serde_json::to_string(&record)?;
                line.push('\n');
                std::fs::write(&path, line).with_context(|| format!("writing the JSON record to {}", path.display()))?;
            }
        }
        Cmd::Calibrate { model, ctx, vram_margin, backend, device, kv, lora, gpu: _ } => {
            if kv == "q8" { unsafe { std::env::set_var("STRATA_KV_Q8", "1") } }  // read by Gpu::new and Vk::new
            if !lora.is_empty() { eprintln!("note: --lora is ignored by calibrate; calibration uses the base model"); }
            calibrate(&model, ctx, vram_margin << 20, backend.as_deref(), &device)?
        }
        Cmd::Check { model, backend, device } => {
            let g = Gguf::open(&model)?;
            if g.get("general.architecture").ok().and_then(|v| v.as_str()) == Some("deepseek41") {
                let c = rusting_strata::deepseek::DsConfig::from_gguf(&g)?;
                c.validate(&g)?;
                println!("check: deepseek41 ok: {} layers, {} experts ({} used), {} tensors, tensor table valid (CPU reference only; no GPU path yet)", c.n_layer, c.n_expert, c.n_used, g.tensors.len());
                return Ok(());
            }
            if g.get("general.architecture").ok().and_then(|v| v.as_str()) == Some("glm5-next") {
                let c = rusting_strata::glm::GlmConfig::from_gguf(&g)?;
                c.validate(&g)?;
                println!("check: glm5-next ok: {} layers ({} KDA, {} DSA) + {} NextN, {} experts ({} used), {} tensors, tensor table valid", c.n_layer, c.n_kda(), c.n_dsa(), c.n_nextn, c.n_expert, c.n_used, g.tensors.len());
                return Ok(());
            }
            let types = rusting_strata::gpu_model::gpu_weight_types(&g);
            let b = backend::open(backend.as_deref(), device)?;
            if b.name() != "vulkan" {
                eprintln!("check: the shared-memory preflight is Vulkan-only; nothing to check on {}", b.name());
                return Ok(());
            }
            b.preflight(&types, true)?;
        }
        Cmd::Chat { model, system, n, think, mut engine } => {
            let g = Gguf::open(&model)?;
            if g.get("general.architecture").ok().and_then(|v| v.as_str()) == Some("glm5-next") {
                return rusting_strata::glm::chat(&g, system, n);
            }
            if g.get("general.architecture").ok().and_then(|v| v.as_str()) == Some("deepseek41") {
                return rusting_strata::deepseek::chat::chat(&g, system, n, think);
            }
            let mut m = Model::load(&g)?;
            if !engine.lora.is_empty() { m.apply_lora(&engine.lora_specs())?; }
            let tok = Tokenizer::from_gguf(&g)?;
            let mut r = engine.runner(&m, &model)?;
            let mut smp = engine.sampler();
            let tpl = template(&g);
            let mut msgs: Vec<Msg> = system.iter().map(|s| Msg::new("system", s)).collect();
            let stdin = std::io::stdin();
            loop {
                print!("> ");
                std::io::stdout().flush()?;
                let mut line = String::new();
                if stdin.lock().read_line(&mut line)? == 0 { break; }
                if line.trim().is_empty() { continue; }
                msgs.push(Msg::new("user", line.trim_end()));
                let (ids, logits, _) = r.chat(&tok, &tpl.render(&msgs, &[], think, engine.preserve_thinking, true), &tpl.render(&msgs, &[], think, engine.preserve_thinking, false), "")?;
                let (out, _) = decode(&mut r, &tok, engine.mtp() > 0, &mut smp, logits, room(&engine, ids.len(), n), &mut |t| { print!("{t}"); std::io::stdout().flush()?; Ok(false) })?;
                println!();
                msgs.push(Msg::new("assistant", &answer(&tok.decode(&out)?)));
            }
            r.finish()?;
        }
        Cmd::Serve { model, models_dir, addr, api_key, open, host, mut engine } => {
            if let Some(mp) = &model && let Ok(g) = Gguf::open(mp) && g.get("general.architecture").ok().and_then(|v| v.as_str()) == Some("glm5-next") {
                let name = mp.file_name().map_or("glm".into(), |n| n.to_string_lossy().into_owned());
                let key = api_key.or_else(|| std::env::var("STRATA_API_KEY").ok());
                anyhow::ensure!(key.as_ref().is_none_or(|k| !k.is_empty()), "empty API key");
                return rusting_strata::glm::serve(&g, &name, &addr, key.as_deref());
            }
            if let Some(mp) = &model && let Ok(g) = Gguf::open(mp) && g.get("general.architecture").ok().and_then(|v| v.as_str()) == Some("deepseek41") {
                let name = mp.file_name().map_or("deepseek".into(), |n| n.to_string_lossy().into_owned());
                let key = api_key.or_else(|| std::env::var("STRATA_API_KEY").ok());
                anyhow::ensure!(key.as_ref().is_none_or(|k| !k.is_empty()), "empty API key");
                return rusting_strata::deepseek::chat::serve(&g, &name, &addr, key.as_deref());
            }
            engine.parallel = host.parallel;
            // Before the model is loaded: a slot count outside 1..=255 is an invalid request, not a downgrade.
            anyhow::ensure!((1..=255).contains(&engine.parallel), "--parallel {}: 1 to 255 slots", engine.parallel);
            let api_key = api_key.or_else(|| std::env::var("STRATA_API_KEY").ok());
            anyhow::ensure!(api_key.as_ref().is_none_or(|k| !k.is_empty()), "empty API key");
            let mut allowed_hosts = host.allowed_hosts.clone();
            if allowed_hosts.is_empty() && let Ok(v) = std::env::var("STRATA_ALLOWED_HOSTS") {
                allowed_hosts.extend(v.split(',').map(str::trim).filter(|h| !h.is_empty()).map(str::to_owned));
            }
            let mut keys_time = host.api_keys.as_ref().and_then(|f| std::fs::metadata(f).and_then(|m| m.modified()).ok());
            let users = match &host.api_keys {
                Some(f) => serve::Keys::parse(&std::fs::read_to_string(f).with_context(|| format!("reading {}", f.display()))?)
                    .with_context(|| format!("in {}", f.display()))?,
                None => vec![],
            };
            anyhow::ensure!(!users.iter().any(|u| api_key.as_ref() == Some(&u.1)), "the admin key is also a customer key");
            // An empty key file would leave the server open to anyone.
            anyhow::ensure!(host.api_keys.is_none() || !users.is_empty() || api_key.is_some(), "the key file has no keys");
            let keys = std::sync::Arc::new(std::sync::RwLock::new(serve::Keys { admin: api_key, users }));
            let keys_file = host.api_keys.clone();
            let usage = match &host.usage_log {
                Some(f) => Some(std::sync::Mutex::new(std::fs::OpenOptions::new().create(true).append(true).open(f)
                    .with_context(|| format!("opening {}", f.display()))?)),
                None => None,
            };
            let max_waiting = host.max_waiting.max(1);
            anyhow::ensure!(host.max_per_key != Some(0), "--max-per-key must be at least 1");
            let url = format!("http://{addr}/");
            let listener = match TcpListener::bind(&addr) {
                Err(e) if open && e.kind() == std::io::ErrorKind::AddrInUse => { open_browser(&url); return Ok(()); }
                l => l?,
            };
            // Connections are read on their own threads, so a client that is slow to send its request does not hold
            // up the others; complete requests run one at a time, in arrival order.
            let (tx, rx) = std::sync::mpsc::channel();
            let open_conns = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
            let waiting = open_conns.clone();
            let stats = std::sync::Arc::new(std::sync::Mutex::new(serve::Stats::default()));
            let (st, a, k, allowed, t0) = (stats.clone(), addr.clone(), keys.clone(), allowed_hosts.clone(), Instant::now());
            let (per_key, held) = (host.max_per_key, serve::Open::default());
            let stop = on_sigterm();
            // SIGTERM (systemctl stop or restart): new requests get 503, the requests accepted before it finish, then
            // the server exits. The model thread does that itself, after saving the expert profile (`Serving::stopped`);
            // this thread covers a server with no model or one loading. Two looks 0.2 s apart cover a connection counted
            // just before the signal, and the model thread gets 3 s to save first.
            let oc = open_conns.clone();
            std::thread::spawn(move || loop {
                std::thread::sleep(Duration::from_millis(200));
                if !stop.load(Relaxed) { continue; }
                let n = oc.load(Relaxed);
                if n == 0 { std::thread::sleep(Duration::from_millis(200)); if oc.load(Relaxed) == 0 { std::thread::sleep(Duration::from_secs(3)); eprintln!("stopped"); std::process::exit(0); } }
                else { eprintln!("stopping: {n} requests to finish"); std::thread::sleep(Duration::from_secs(5)); }
            });
            std::thread::spawn(move || for (i, conn) in listener.incoming().enumerate() {
                let mut c = match conn { Ok(c) => c, Err(e) => { eprintln!("request {i}: {e:#}"); continue } };
                if stop.load(Relaxed) {
                    let b = json!({"error": {"message": "server is stopping, retry later", "type": "overloaded_error"}}).to_string();
                    let _ = c.set_write_timeout(Some(Duration::from_secs(5)));
                    let _ = write!(c, "HTTP/1.1 503 Service Unavailable\r\nRetry-After: 5\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{b}", b.len());
                    let _ = c.shutdown(std::net::Shutdown::Write);
                    continue;
                }
                // ponytail: one cap on connections read or queued (each may hold an 8 MB body), not one per key.
                if open_conns.fetch_add(1, Relaxed) >= max_waiting {
                    open_conns.fetch_sub(1, Relaxed);
                    eprintln!("request {i}: {max_waiting} requests already waiting, answered 503");
                    let b = json!({"error": {"message": "server busy, retry later", "type": "overloaded_error"}}).to_string();
                    let _ = c.set_write_timeout(Some(Duration::from_secs(5)));
                    let _ = write!(c, "HTTP/1.1 503 Service Unavailable\r\nRetry-After: 2\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{b}", b.len());
                    let _ = c.shutdown(std::net::Shutdown::Write);
                    continue;
                }
                // A changed key file takes effect from the next request; one that does not parse keeps the old keys.
                if let Some(f) = &keys_file && let Ok(t) = std::fs::metadata(f).and_then(|m| m.modified()) && Some(t) != keys_time {
                    keys_time = Some(t);
                    let mut kw = k.write().unwrap();
                    match std::fs::read_to_string(f).map_err(Into::into).and_then(|t| serve::Keys::parse(&t)) {
                        Ok(u) if u.iter().any(|u| kw.admin.as_ref() == Some(&u.1)) => eprintln!("{}: the admin key is also a customer key, keeping the old keys", f.display()),
                        // An empty file (or one caught mid-write) would leave the server open.
                        Ok(u) if u.is_empty() && kw.admin.is_none() => eprintln!("{}: no keys, keeping the old keys", f.display()),
                        Ok(u) => { eprintln!("{}: {} keys", f.display(), u.len()); kw.users = u; }
                        Err(e) => eprintln!("{}: {e:#}, keeping the old keys", f.display()),
                    }
                }
                let (tx, oc, st, a, k, allowed, held) = (tx.clone(), open_conns.clone(), st.clone(), a.clone(), k.clone(), allowed.clone(), held.clone());
                std::thread::spawn(move || {
                    let q = c.set_read_timeout(Some(Duration::from_secs(30))).and_then(|_| c.set_write_timeout(Some(Duration::from_secs(30))))
                        .map_err(Into::into).and_then(|_| serve::read_request(&mut BufReader::new(&c)));
                    let reply = |v: serde_json::Value, status: &str| {
                        let b = v.to_string();
                        let _ = write!(&c, "HTTP/1.1 {status}\r\nContent-Type: application/json\r\nCache-Control: no-store\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{b}", b.len());
                        oc.fetch_sub(1, Relaxed);
                    };
                    // For load balancers: no key, no Host check, and an answer while a reply is generated.
                    if let Ok(r) = &q && r.method == "GET" && r.path == "/health" {
                        let (model, loading, slots) = { let g = st.lock().unwrap(); (g.model.is_some() && !g.loading, g.loading, g.slots) };
                        let waiting = oc.load(Relaxed) - 1;
                        return if model { reply(json!({"status": "ok", "waiting": waiting, "slots": slots}), "200 OK") }
                            else { reply(json!({"status": if loading { "loading" } else { "no model" }}), "503 Service Unavailable") };
                    }
                    // The page's side panel is answered here, so it stays current while a reply is generated or a
                    // model loads. A bad Host or key falls through to `handle`, which refuses it.
                    if let Ok(r) = &q && r.method == "GET" && matches!(r.path.as_str(), "/api/stats" | "/metrics") && let k = k.read().unwrap().clone()
                        && (k.any() || serve::host_ok(&r.host, &a, &allowed)) && k.who(&r.auth).is_some_and(|w| w.admin) {
                        if r.path == "/metrics" {
                            let b = st.lock().unwrap().prometheus(oc.load(Relaxed) - 1, t0.elapsed().as_secs());
                            let _ = write!(&c, "HTTP/1.1 200 OK\r\nContent-Type: text/plain; version=0.0.4\r\nCache-Control: no-store\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{b}", b.len());
                            oc.fetch_sub(1, Relaxed);
                            return;
                        }
                        let mut v = json!(*st.lock().unwrap());
                        (v["system"], v["uptime_s"]) = (serve::system(), t0.elapsed().as_secs().into());
                        return reply(v, "200 OK");
                    }
                    // A malformed request, a wrong key, the page and the model list are answered here, not in the queue,
                    // where without `--parallel` they would wait for the reply being generated (`handle` checks the key
                    // again: the keys may change meanwhile). The page holds no secret, so it loads without the key (it
                    // asks for it); without keys the Host check stops DNS rebinding.
                    let who = q.as_ref().ok().and_then(|r| k.read().unwrap().who(&r.auth));
                    match &q {
                        Err(e) => {
                            eprintln!("request {i}: {e:#}");
                            return reply(json!({"error": {"message": format!("{e:#}"), "type": "invalid_request_error"}}), "400 Bad Request");
                        }
                        Ok(r) if r.method == "GET" && r.path == "/" && (k.read().unwrap().any() || serve::host_ok(&r.host, &a, &allowed)) => {
                            let _ = write!(&c, "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nX-Frame-Options: DENY\r\nContent-Security-Policy: frame-ancestors 'none'\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{PAGE}", PAGE.len());
                            oc.fetch_sub(1, Relaxed);
                            return;
                        }
                        Ok(_) if who.is_none() =>
                            return reply(json!({"error": {"message": "missing or wrong API key", "type": "invalid_api_key"}}), "401 Unauthorized"),
                        // Clients list the models often; a model still loading is listed, as its chats wait for the load.
                        Ok(r) if r.method == "GET" && r.path.split('?').next() == Some("/v1/models") && (k.read().unwrap().any() || serve::host_ok(&r.host, &a, &allowed)) => {
                            let created = SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).map_or(0, |d| d.as_secs());
                            let (m, n_ctx, n_ctx_train) = {
                                let state = st.lock().unwrap();
                                (state.model.clone(), state.ctx, state.ctx_train)
                            };
                            return reply(json!({"object": "list", "data": m.map(|id| json!([{
                                "id": id, "object": "model", "created": created, "owned_by": "strata",
                                "meta": {"n_ctx": n_ctx, "n_ctx_train": n_ctx_train}
                            }])).unwrap_or(json!([]))}), "200 OK");
                        }
                        _ => {}
                    }
                    // A customer key over `--max-per-key` is refused here, before it takes a place in the queue.
                    let hold = match (who, per_key) {
                        (Some(w), Some(cap)) if !w.admin => match serve::Hold::take(&held, w.id, cap) {
                            Some(h) => Some(h),
                            None => {
                                eprintln!("request {i}: {} already has {cap} requests open, answered 429", w.name);
                                let b = json!({"error": {"message": format!("this key already has {cap} requests open, retry later"), "type": "rate_limit_error"}}).to_string();
                                let _ = write!(&c, "HTTP/1.1 429 Too Many Requests\r\nRetry-After: 1\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{b}", b.len());
                                oc.fetch_sub(1, Relaxed);
                                return;
                            }
                        },
                        _ => None,
                    };
                    let _ = tx.send((c, q, i, hold));
                });
            });
            let s = Serving { rx: rx.into(), waiting, stop, addr, allowed_hosts, keys, usage, max_tokens: host.max_tokens.unwrap_or(usize::MAX), dir: models_dir.unwrap_or_else(models_dir_default), model: model.clone(),
                dl: Default::default(), stats };
            // The model to load next and the /api/load request waiting for the outcome (none for --model).
            let mut next = model.map(|p| (p, None));
            eprintln!("listening on {url} (models folder: {})", s.dir.display());
            // Chats wait while a model loads; the page shows at once.
            if open { open_browser(&url); }
            loop {
                let (p, mut w) = match next.take() {
                    Some(x) => x,
                    None => match s.serve(None, &engine) { Some((p, w)) => (p, Some(w)), None => return Ok(()) },
                };
                match serve_model(&p, engine.clone(), &s, &mut w) {
                    Ok(Some((p, w))) => next = Some((p, Some(w))),
                    Ok(None) => return Ok(()),
                    Err(e) if w.is_none() => return Err(e),
                    Err(e) => {
                        s.stats.lock().unwrap().unload(None);
                        eprintln!("loading {}: {e:#}", p.display());
                        let b = json!({"error": {"message": format!("{e:#}"), "type": "server_error"}}).to_string();
                        let _ = write!(w.unwrap(), "HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{b}", b.len());
                    }
                }
            }
        }
    }
    Ok(())
}

/// `n` tokens of varied prose, repeated: the prefill prompt for `bench` and `calibrate`.
fn prose(tok: &Tokenizer, n: usize) -> anyhow::Result<Vec<u32>> {
    let text = "The river town woke before dawn. Fishermen checked their nets, bakers lit ovens, and a clockmaker \
        argued with his apprentice about gears, tides and the price of brass. In 1874 the bridge washed away; \
        the council voted 7 to 5 to rebuild it in stone. ";
    let ids: Vec<u32> = tok.encode(&text.repeat(n / 20 + 1))?.into_iter().take(n).collect();
    anyhow::ensure!(ids.len() == n, "prose prompt too short");
    Ok(ids)
}

/// Best (lowest) of three timings of `f`, in seconds.
fn best(f: &mut dyn FnMut() -> anyhow::Result<()>) -> anyhow::Result<f64> {
    let mut b = f64::INFINITY;
    for _ in 0..3 {
        let t = Instant::now();
        f()?;
        b = b.min(t.elapsed().as_secs_f64());
    }
    Ok(b)
}

fn calibrate(model: &Path, ctx: usize, margin: usize, kind: Option<&str>, device: &[usize]) -> anyhow::Result<()> {
    let g = Gguf::open(model)?;
    let m = Model::load(&g)?;
    let tok = Tokenizer::from_gguf(&g)?;
    let n_pf = 4096.min(ctx.saturating_sub(256));
    anyhow::ensure!(n_pf >= 512, "--ctx too small to calibrate");
    let pf = prose(&tok, n_pf)?;
    let load = |chunk: usize| -> anyhow::Result<GpuModel> {
        let bk = device.iter().map(|&d| backend::open(kind, d)).collect::<anyhow::Result<Vec<_>>>()?;
        // MTP is not available with a layer split (as in serve): no drafts to measure.
        let mut gm = GpuModel::load_split(&m, bk, ctx, chunk, margin, if device.len() > 1 { 0 } else { 3 }, 1).context(LOAD_HINT)?;
        gm.adapt_every = 0; // fixed placement: steadier timings
        Ok(gm)
    };

    let mut chunk = (0, 0.0);
    for c in [512, 1024, 2048, 4096].into_iter().filter(|&c| c <= ctx) {
        // A larger chunk's prefill scratch may not fit beside a long --ctx: keep the chunks measured so far.
        let mut gm = match load(c) { Ok(gm) => gm, Err(e) if chunk.0 > 0 => { eprintln!("chunk {c:5}: {e:#}"); break } Err(e) => return Err(e) };
        let t = best(&mut || { gm.reset()?; gm.prefill(&pf).map(drop) })?;
        let tps = n_pf as f64 / t;
        eprintln!("chunk {c:5}: prefill {n_pf} tok {tps:.0} tok/s");
        if tps > chunk.1 { chunk = (c, tps); }
    }

    let mut gm = load(chunk.0)?;
    let mut short = usize::MAX;
    for n in [8, 16, 32, 64, 128] {
        let p = &pf[..n];
        gm.short = usize::MAX;
        let ts = best(&mut || { gm.reset()?; gm.prefill(p).map(drop) })?;
        gm.short = 0;
        let tb = best(&mut || { gm.reset()?; gm.prefill(p).map(drop) })?;
        eprintln!("prompt {n:4}: steps {:.1} ms, batched {:.1} ms", ts * 1e3, tb * 1e3);
        if tb < ts && short == usize::MAX { short = n; }
    }
    if short == usize::MAX { short = 256; }

    let dec = tok.encode("Write a long story about a dragon.")?;
    let kmax = gm.k;
    let mut r = Runner::Gpu(Box::new(gm));
    let mut mtp = (0, 0.0);
    for k in 0..=kmax {
        if let Runner::Gpu(g) = &mut r { g.k = k.max(1); }
        let mut toks = 0;
        let t = best(&mut || {
            r.reset()?;
            let l = r.prefill(&dec)?;
            toks = decode(&mut r, &tok, k > 0, &mut Sampler::greedy(), l, 128, &mut |_| Ok(false))?.0.len();
            Ok(())
        })?;
        // `best` times prefill too; it is the same for every k, so the ranking holds.
        let tps = toks as f64 / t;
        eprintln!("mtp {k}: decode {toks} tok {tps:.1} tok/s");
        if tps > mtp.1 { mtp = (k, tps); }
    }

    let Runner::Gpu(g) = &r else { unreachable!() };
    let path = calibration_path(model, g.gpu.name());
    std::fs::create_dir_all(path.parent().unwrap())?;
    let v = json!({"chunk": chunk.0, "mtp": mtp.0, "short": short, "ctx": ctx,
        "measured": {"prefill_tok_s": chunk.1.round(), "decode_tok_s": (mtp.1 * 10.0).round() / 10.0}});
    std::fs::write(&path, serde_json::to_string_pretty(&v)?)?;
    println!("{v}\nwritten to {}", path.display());
    Ok(())
}

/// Decoding of up to `n` tokens after `logits`; `emit` gets each new complete piece of text and returns true to stop.
/// Returns the tokens and whether an end-of-turn token or `emit` stopped it.
fn decode(r: &mut Runner, tok: &Tokenizer, mtp: bool, smp: &mut Sampler, mut logits: Vec<f32>, n: usize,
          emit: &mut dyn FnMut(&str) -> anyhow::Result<bool>) -> anyhow::Result<(Vec<u32>, bool)> {
    let eos = tok.eos_ids();
    // `ahead`: the next token when `spec_step` or `step_greedy` already picked it.
    // `start`: the first token whose text is not emitted yet (the text before it ends on a whole character).
    let (mut out, mut start, mut row, mut ahead) = (Vec::new(), 0, 0, None);
    while out.len() < n {
        let next = match ahead.take() { Some(t) => t, None => smp.pick(&logits)? as u32 };
        if eos.contains(&next) { return Ok((out, true)); }
        let toks = match r {
            Runner::Gpu(g) if mtp => {
                let (toks, nx, rw) = g.spec_step(next, row, smp)?;
                (ahead, row) = (Some(nx), rw);
                toks
            }
            // Greedy without MTP: the argmax on the GPU, so only the token id is copied back, not the logits.
            Runner::Gpu(g) if smp.temp <= 0.0 => { ahead = Some(g.step_greedy(next)?); vec![next] }
            Runner::Slot(c) if smp.temp <= 0.0 => { ahead = Some(c.step(next, false)?.0); vec![next] }
            _ => { logits = r.step(next)?; vec![next] }
        };
        for t in toks {
            if eos.contains(&t) { return Ok((out, true)); }
            if out.len() == n { break; }
            out.push(t);
            let s = tok.decode(&out[start..])?;
            if !s.ends_with('\u{fffd}') {
                if emit(&s)? { return Ok((out, true)); }
                start = out.len();
            }
        }
    }
    Ok((out, false))
}

/// Tokens left for a reply: `n`, capped by the context after a `used`-token prompt.
fn room(e: &Engine, used: usize, n: usize) -> usize { n.min(e.ctx.saturating_sub(used)) }

/// The chat format from the GGUF's `tokenizer.chat_template`.
fn template(g: &Gguf) -> Template {
    let t = Template::detect(g.meta.get("tokenizer.chat_template").and_then(|v| v.as_str()));
    eprintln!("chat template: {t:?}");
    t
}

/// Reply text without the thinking part (the template drops it from history too).
fn answer(s: &str) -> String { s.rsplit_once("</think>").map_or(s, |x| x.1).trim().to_string() }

/// A model `serve` has loaded.
struct Loaded<'a> { r: Runner<'a>, tok: &'a Tokenizer, tpl: Template, name: String, path: PathBuf }

/// What `serve` keeps across model loads.
struct Serving {
    /// Complete requests, with their key's place when `--max-per-key` counts it (freed once answered).
    rx: std::sync::Mutex<std::sync::mpsc::Receiver<(TcpStream, anyhow::Result<serve::Request>, usize, Option<serve::Hold>)>>,
    waiting: std::sync::Arc<std::sync::atomic::AtomicUsize>,
    /// Set by SIGTERM.
    stop: &'static std::sync::atomic::AtomicBool,
    addr: String,
    allowed_hosts: Vec<String>,
    keys: std::sync::Arc<std::sync::RwLock<serve::Keys>>,
    usage: Option<std::sync::Mutex<std::fs::File>>,
    max_tokens: usize,
    dir: PathBuf,
    /// The --model, offered beside the models folder.
    model: Option<PathBuf>,
    /// The Hugging Face download running on its own thread, or the last one.
    dl: std::sync::Arc<std::sync::Mutex<hf::Progress>>,
    stats: std::sync::Arc<std::sync::Mutex<serve::Stats>>,
}

/// A flag that SIGTERM sets (instead of ending the process). Never set on Windows.
fn on_sigterm() -> &'static std::sync::atomic::AtomicBool {
    static STOP: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
    #[cfg(unix)]
    {
        extern "C" fn h(_: i32) { STOP.store(true, Relaxed); }
        unsafe extern "C" { fn signal(sig: i32, handler: extern "C" fn(i32)) -> usize; }
        // SAFETY: the handler only stores to an atomic, which is async-signal-safe. 15 is SIGTERM on Linux and macOS.
        unsafe { signal(15, h); }
    }
    &STOP
}

impl Serving {
    /// Answers requests until one asks for a model to be loaded; returns its path and connection (None once the
    /// listener is gone).
    fn serve(&self, mut l: Option<&mut Loaded>, e: &Engine) -> Option<(PathBuf, TcpStream)> {
        if let Some(l) = l.as_deref_mut() && matches!(&l.r, Runner::Gpu(g) if g.slots() > 1) { return self.serve_slots(l, e); }
        let rx = self.rx.lock().unwrap();
        loop {
            let (c, q, i, _hold) = match rx.recv_timeout(Duration::from_millis(200)) {
                Ok(x) => x,
                Err(std::sync::mpsc::RecvTimeoutError::Timeout) if self.stopped() => { eprintln!("stopped"); return None }
                Err(std::sync::mpsc::RecvTimeoutError::Timeout) => continue,
                Err(std::sync::mpsc::RecvTimeoutError::Disconnected) => return None,
            };
            let mut next = None;
            let res = handle(c, q, l.as_deref_mut(), e, self, i, &mut next);
            self.waiting.fetch_sub(1, Relaxed);
            if let Err(e) = res { eprintln!("request {i}: {e:#}"); }
            if next.is_some() { return next; }
        }
    }
    /// SIGTERM came and the requests accepted before it are answered: `serve` returns None, so the expert profile
    /// is saved and the server exits.
    fn stopped(&self) -> bool { self.stop.load(Relaxed) && self.waiting.load(Relaxed) == 0 }
    /// The models the page offers: the models folder, then --model if it is elsewhere.
    fn models(&self) -> Vec<(String, PathBuf, u64)> {
        let mut v = serve::list_models(&self.dir);
        if let Some(p) = self.model.as_ref().filter(|p| !v.iter().any(|x| &x.1 == *p)) {
            v.push((p.display().to_string(), p.clone(), std::fs::metadata(p).map_or(0, |m| m.len())));
        }
        v
    }
}

/// What a request thread asks of the model's thread under `--parallel` (`Serving::serve_slots`).
enum Job {
    /// `prefill_cached` in a free slot; answers the logits, the tokens reused, the slot and when the prefill began.
    /// `gone` is set when the client leaves while the chat waits for a slot; the chat is then dropped.
    Chat { ids: Vec<u32>, sys: usize, keep: usize, owner: u64, gone: std::sync::Arc<std::sync::atomic::AtomicBool>, back: std::sync::mpsc::Sender<anyhow::Result<(Vec<f32>, usize, usize, Instant)>> },
    /// One decode step in a slot the request holds; answers the greedy next token and the logits if `logits`.
    Step { slot: usize, token: u32, logits: bool, back: std::sync::mpsc::Sender<anyhow::Result<(u32, Vec<f32>)>> },
    /// The request is done with its slot.
    Done(usize),
}

/// A request's handle on the model under `--parallel`; dropping it frees the slot.
/// `conn` is the request's connection, watched while the chat waits for a slot; `started` is when the model took
/// the chat, after that wait.
struct Client { tx: std::sync::mpsc::Sender<Job>, slot: Option<usize>, owner: u64, conn: Option<TcpStream>, started: Option<Instant> }

impl Client {
    fn chat(&mut self, ids: &[u32], sys: usize, keep: usize) -> anyhow::Result<(Vec<f32>, usize)> {
        if let Some(s) = self.slot.take() { let _ = self.tx.send(Job::Done(s)); }
        let (back, r) = std::sync::mpsc::channel();
        let gone = std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false));
        self.tx.send(Job::Chat { ids: ids.to_vec(), sys, keep, owner: self.owner, gone: gone.clone(), back }).map_err(|_| anyhow::anyhow!("model gone"))?;
        let (logits, reused, s, started) = loop {
            match r.recv_timeout(Duration::from_millis(250)) {
                Ok(x) => break x?,
                // A client that left is flagged, and the wait goes on: the model drops the chat if it is still queued
                // (the channel closes), or sends its slot if the prefill already started, which `handle` then frees.
                Err(std::sync::mpsc::RecvTimeoutError::Timeout) => if !gone.load(Relaxed) && self.conn.as_ref().is_some_and(serve::gone) {
                    gone.store(true, Relaxed);
                },
                Err(_) if gone.load(Relaxed) => anyhow::bail!("client closed the connection"),
                Err(_) => anyhow::bail!("model gone"),
            }
        };
        (self.slot, self.started) = (Some(s), Some(started));
        Ok((logits, reused))
    }
    fn step(&mut self, token: u32, logits: bool) -> anyhow::Result<(u32, Vec<f32>)> {
        let slot = self.slot.context("step before chat")?;
        let (back, r) = std::sync::mpsc::channel();
        self.tx.send(Job::Step { slot, token, logits, back }).map_err(|_| anyhow::anyhow!("model gone"))?;
        r.recv()?
    }
}

impl Drop for Client {
    fn drop(&mut self) { if let Some(s) = self.slot { let _ = self.tx.send(Job::Done(s)); } }
}

/// The model thread's view of the slots under `--parallel` (`Serving::serve_slots`).
#[derive(Default)]
struct Sched {
    /// Slots held by a request, and when each was last freed (the least recently used goes first).
    held: Vec<bool>,
    freed: Vec<u64>,
    tick: u64,
    /// The key that holds each slot (`Client::owner`).
    who: Vec<u64>,
    /// Chat jobs waiting for a free slot, and decode steps waiting for a forward (since the first came).
    chats: std::collections::VecDeque<Job>,
    steps: Vec<(usize, u32, bool, std::sync::mpsc::Sender<anyhow::Result<(u32, Vec<f32>)>>)>,
    since: Option<Instant>,
}

impl Sched {
    /// How long a decode step waits for the other decoding slots' steps to share its forward.
    const GATHER: Duration = Duration::from_millis(2);

    fn decoding(&self) -> usize { self.held.iter().filter(|&&h| h).count() }

    /// The queued chat to start next: the one whose key holds the fewest slots, the oldest among those, so that one
    /// customer's burst of requests does not hold back the others'. With one key (or none) it is the oldest.
    fn next_chat(&self) -> Option<usize> {
        let holds = |o: u64| self.held.iter().zip(&self.who).filter(|&(&h, &w)| h && w == o).count();
        (0..self.chats.len()).min_by_key(|&j| (if let Job::Chat { owner, .. } = &self.chats[j] { holds(*owner) } else { usize::MAX }, j))
    }

    /// How long to wait for jobs: until the steps of all decoding slots are in, at most `GATHER` after the first.
    fn wait(&self) -> Duration {
        match self.since {
            Some(t) if self.steps.len() < self.decoding() => Self::GATHER.saturating_sub(t.elapsed()),
            Some(_) => Duration::ZERO,
            None => Duration::from_millis(5),
        }
    }

    /// Take the jobs that come within `wait`.
    fn take(&mut self, jobs: &std::sync::mpsc::Receiver<Job>, wait: Duration) {
        let mut got: Vec<Job> = jobs.recv_timeout(wait).into_iter().collect();
        got.extend(jobs.try_iter());
        for j in got {
            match j {
                Job::Done(s) => { self.held[s] = false; self.tick += 1; self.freed[s] = self.tick; }
                Job::Step { slot, token, logits, back } => { self.since.get_or_insert_with(Instant::now); self.steps.push((slot, token, logits, back)); }
                c => self.chats.push_back(c),
            }
        }
    }

    fn ready(&self) -> bool { self.since.is_some_and(|t| self.steps.len() >= self.decoding() || t.elapsed() >= Self::GATHER) }

    /// One forward over the oldest steps (with more than `TMAX` slots decoding, each waits its turn), in slot order
    /// (fewer graphs to capture).
    fn run(&mut self, g: &mut GpuModel) {
        let mut batch: Vec<_> = self.steps.drain(..self.steps.len().min(rusting_strata::cpu_worker::TMAX)).collect();
        batch.sort_by_key(|s| s.0);
        self.since = if self.steps.is_empty() { None } else { Some(Instant::now() - Self::GATHER) };
        match g.step_rows(&batch.iter().map(|b| (b.0, b.1, b.2)).collect::<Vec<_>>()) {
            Ok(rows) => for (b, l) in batch.into_iter().zip(rows) { let _ = b.3.send(Ok(l)); },
            Err(err) => for b in batch { let _ = b.3.send(Err(anyhow::anyhow!("{err:#}"))); },
        }
    }
}

impl Serving {
    /// `serve` with several slots (`--parallel`): each request runs `handle` on its own thread and sends its model
    /// work here, where prefills run one at a time (the decoding slots run between its chunks) and the decode steps of
    /// up to `TMAX` slots share a forward.
    fn serve_slots(&self, l: &mut Loaded, e: &Engine) -> Option<(PathBuf, TcpStream)> {
        use std::sync::mpsc::{TryRecvError, channel};
        let Loaded { r, tok, tpl, name, path } = l;
        let Runner::Gpu(g) = r else { unreachable!() };
        let (tx, jobs) = channel::<Job>();
        let (next, live) = (std::sync::Mutex::new(None), std::sync::atomic::AtomicUsize::new(0));
        let rx = self.rx.lock().unwrap();
        let n = g.slots();
        std::thread::scope(|sc| {
            // Owned here, so that a panic drops the queued jobs' reply channels and the request threads end (the
            // scope then joins them and the panic goes on).
            let (jobs, mut s) = (jobs, Sched { held: vec![false; n], freed: vec![0; n], who: vec![0; n], ..Default::default() });
            let mut open = true;
            loop {
                while open && next.lock().unwrap().is_none() {
                    match rx.try_recv() {
                        Ok((c, q, i, hold)) => {
                            live.fetch_add(1, Relaxed);
                            let (tx, tok, tpl, name, path, next, live) = (tx.clone(), &**tok, *tpl, name.clone(), path.clone(), &next, &live);
                            sc.spawn(move || {
                                let mut l = Loaded { r: Runner::Slot(Client { tx, slot: None, owner: 0, conn: None, started: None }), tok, tpl, name, path };
                                let mut nx = None;
                                // A panic still gives back the counts below, so the model thread can switch models.
                                let res = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| handle(c, q, Some(&mut l), e, self, i, &mut nx)))
                                    .unwrap_or_else(|_| Err(anyhow::anyhow!("panicked")));
                                drop((l, hold));
                                self.waiting.fetch_sub(1, Relaxed);
                                if let Err(e) = res { eprintln!("request {i}: {e:#}"); }
                                if nx.is_some() { *next.lock().unwrap() = nx; }
                                live.fetch_sub(1, Relaxed);
                            });
                        }
                        Err(TryRecvError::Empty) => break,
                        Err(TryRecvError::Disconnected) => open = false,
                    }
                }
                if open && self.stopped() { eprintln!("stopped"); open = false; }
                if (!open || next.lock().unwrap().is_some()) && live.load(Relaxed) == 0 { break; }
                s.take(&jobs, s.wait());
                // One prefill between decode steps, in the free slot whose saved state this prompt extends the
                // furthest, else the least recently used one.
                s.chats.retain(|j| !matches!(j, Job::Chat { gone, .. } if gone.load(Relaxed)));
                let first = s.next_chat();
                if let Some(sl) = (0..n).filter(|&i| !s.held[i]).max_by_key(|&i| {
                    let reuse = match first.and_then(|j| s.chats.get(j)) {
                        Some(Job::Chat { ids, keep, owner, .. }) => { let (sv, o) = g.slot_saved(i); if o == *owner && ids[..*keep].starts_with(sv) { sv.len() } else { 0 } }
                        _ => 0,
                    };
                    (reuse, std::cmp::Reverse(s.freed[i]))
                }) && let Some(Job::Chat { ids, sys, keep, owner, back, .. }) = first.and_then(|j| s.chats.remove(j)) {
                    g.use_slot(sl);
                    g.owner = owner;
                    // Between two prefill chunks the decoding slots run for as long as the chunk before took, so a long
                    // prompt shares the GPU with them evenly instead of stalling them.
                    // ponytail: an even share; weigh it (or cap the prompt's chunk) if first-token time matters more.
                    let (started, mut t0) = (Instant::now(), Instant::now());
                    let r = g.prefill_cached_with(&ids, sys, keep, &mut |g| {
                        let end = Instant::now() + t0.elapsed();
                        while s.decoding() > 0 && Instant::now() < end {
                            s.take(&jobs, s.wait().min(end.saturating_duration_since(Instant::now())));
                            if s.ready() { s.run(g); }
                        }
                        t0 = Instant::now();
                        Ok(())
                    });
                    (s.held[sl], s.who[sl]) = (r.is_ok(), owner);
                    // A client that left during the prefill takes no slot.
                    if back.send(r.map(|(l, u)| (l, u, sl, started))).is_err() && s.held[sl] {
                        s.held[sl] = false;
                        s.tick += 1;
                        s.freed[sl] = s.tick;
                    }
                    gpu_model_stats(g, &mut self.stats.lock().unwrap());
                }
                if s.ready() { s.run(g); }
            }
        });
        next.into_inner().unwrap()
    }
}

/// Loads `model`, answers `w` (the /api/load request that asked for it) and serves until another model is asked
/// for. The model and its GPU memory are freed on return.
fn serve_model(model: &Path, mut engine: Engine, s: &Serving, w: &mut Option<TcpStream>) -> anyhow::Result<Option<(PathBuf, TcpStream)>> {
    eprintln!("loading {}", model.display());
    let name = model.file_stem().and_then(|s| s.to_str()).unwrap_or("strata").to_string();
    {
        let mut st = s.stats.lock().unwrap();
        st.unload(Some(name.clone()));
        st.ctx = engine.ctx;
        st.ram_cap = engine.ram_cap();
    }
    let g = Gguf::open(model)?;
    let arch = g.get("general.architecture")?.as_str().context("general.architecture")?;
    s.stats.lock().unwrap().ctx_train = g.meta.get(&format!("{arch}.context_length")).and_then(|v| v.as_u64());
    let mut m = Model::load(&g)?;
    if !engine.lora.is_empty() { m.apply_lora(&engine.lora_specs())?; }
    let tok = Tokenizer::from_gguf(&g)?;
    let r = engine.runner(&m, model)?;
    {
        let mut st = s.stats.lock().unwrap();
        st.loading = false;
        (st.backend, st.device, st.ctx, st.slots) = match &r { Runner::Gpu(g) => (g.gpu.name().into(), g.gpu.device(), engine.ctx, g.slots()), _ => ("cpu".into(), String::new(), engine.ctx, 1) };
        gpu_stats(&r, &mut st);
    }
    let mut l = Loaded { r, tok: &tok, tpl: template(&g), name, path: model.to_path_buf() };
    eprintln!("loaded {}", l.name);
    if let Some(mut w) = w.take() {
        let b = json!({"loaded": l.name}).to_string();
        let _ = write!(w, "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{b}", b.len());
    }
    let next = s.serve(Some(&mut l), &engine);
    s.stats.lock().unwrap().unload(None);
    // A failed profile save must not stop the server between two models.
    if let Err(e) = l.r.finish() { eprintln!("{e:#}"); }
    Ok(next)
}

/// The side panel's device memory, expert cache and MTP counts.
fn gpu_stats(r: &Runner, s: &mut serve::Stats) {
    if let Runner::Gpu(g) = r { gpu_model_stats(g, s) }
}

fn gpu_model_stats(g: &GpuModel, s: &mut serve::Stats) {
    s.vram = g.gpu.mem_info().ok().map(|(f, t)| ((t - f) as u64, t as u64));
    s.experts = g.cache.as_ref().map(|_| (g.hits as u64, g.misses as u64));
    s.drafts = (g.drafts.0 > 0).then_some((g.drafts.0 as u64, g.drafts.1 as u64));
}

/// Default models folder: `$XDG_DATA_HOME`, `%LOCALAPPDATA%` on Windows, else `~/.local/share`.
fn models_dir_default() -> PathBuf {
    std::env::var_os("XDG_DATA_HOME").or_else(|| std::env::var_os("LOCALAPPDATA")).map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(std::env::var_os("HOME").unwrap_or_default()).join(".local/share"))
        .join("rusting_strata").join("models")
}

fn open_browser(url: &str) {
    #[cfg(windows)]
    let r = std::process::Command::new("cmd").args(["/c", "start", "", url]).spawn();
    #[cfg(target_os = "macos")]
    let r = std::process::Command::new("open").arg(url).spawn();
    #[cfg(all(unix, not(target_os = "macos")))]
    let r = std::process::Command::new("xdg-open").arg(url).spawn();
    if let Err(e) = r { eprintln!("could not open a browser ({e}); open {url}"); }
}

/// One Messages API stream event.
fn sse(w: &mut impl Write, v: serde_json::Value) -> anyhow::Result<()> { Ok(write!(w, "event: {}\ndata: {v}\n\n", v["type"].as_str().unwrap_or_default())?) }

/// Streamed reply text as a Messages API text block (index 0), started by the first piece.
fn text_delta(w: &mut impl Write, opened: &mut bool, t: &str) -> anyhow::Result<()> {
    if !std::mem::replace(opened, true) { sse(w, json!({"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}))?; }
    sse(w, json!({"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": t}}))
}

/// The chat page, served by the connection threads of `strata serve`.
const PAGE: &str = include_str!("web/index.html");

fn handle(mut w: TcpStream, q: anyhow::Result<serve::Request>, l: Option<&mut Loaded>, e: &Engine, s: &Serving, i: usize,
    next: &mut Option<(PathBuf, TcpStream)>) -> anyhow::Result<()> {
    let send = |w: &mut TcpStream, status: &str, v: serde_json::Value| -> anyhow::Result<()> {
        let b = v.to_string();
        Ok(write!(w, "HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{b}", b.len())?)
    };
    // A malformed request gets a 400 (best effort: the client may be gone) and is still logged.
    let serve::Request { method, path, host, auth, json, body } = match q {
        Ok(q) => q,
        Err(err) => {
            let _ = send(&mut w, "400 Bad Request", json!({"error": {"message": format!("{err:#}"), "type": "invalid_request_error"}}));
            return Err(err);
        }
    };
    let created = SystemTime::now().duration_since(SystemTime::UNIX_EPOCH)?.as_secs();
    // Browsers can reach a loopback server: the Host check stops DNS rebinding, and requiring a JSON content type
    // makes a cross-site POST need a CORS preflight, which is never answered.
    // With a key the check is not needed (a rebinding page has no key) and would refuse a reverse proxy's Host.
    let keys = s.keys.read().unwrap().clone();
    if !keys.any() && !serve::host_ok(&host, &s.addr, &s.allowed_hosts) { return send(&mut w, "403 Forbidden", json!({"error": {"message": "bad Host header", "type": "forbidden"}})); }
    let Some(who) = keys.who(&auth) else { return send(&mut w, "401 Unauthorized", json!({"error": {"message": "missing or wrong API key", "type": "invalid_api_key"}})) };
    if method == "POST" && !json { return send(&mut w, "415 Unsupported Media Type", json!({"error": {"message": "Content-Type must be application/json", "type": "invalid_request_error"}})); }
    // Claude Code adds `?beta=true`.
    let route = path.split('?').next().unwrap_or_default();
    // Customer keys may not load models, download files or read the server's stats.
    if !who.admin && !matches!(route, "/v1/chat/completions" | "/v1/messages" | "/v1/messages/count_tokens" | "/v1/models") {
        return send(&mut w, "403 Forbidden", json!({"error": {"message": "this key may use only /v1/chat/completions, /v1/messages (and count_tokens) and /v1/models", "type": "permission_error"}}));
    }
    match (method.as_str(), route) {
        ("GET", "/api/models") => {
            let models: Vec<_> = s.models().into_iter().map(|(id, p, n)| json!({"id": id, "bytes": n, "loaded": l.as_ref().is_some_and(|l| l.path == p)})).collect();
            send(&mut w, "200 OK", json!({"dir": s.dir, "models": models}))
        }
        // Answered once the model has loaded (or failed to).
        ("POST", "/api/load") => {
            let id = serde_json::from_slice::<serde_json::Value>(&body).ok().and_then(|v| v["model"].as_str().map(String::from)).unwrap_or_default();
            match s.models().into_iter().find(|m| m.0 == id) {
                Some((_, p, _)) => { *next = Some((p, w)); Ok(()) }
                None => send(&mut w, "404 Not Found", json!({"error": {"message": format!("no model {id:?} in {}", s.dir.display()), "type": "not_found"}})),
            }
        }
        ("POST", "/api/hf/files") => {
            let repo = serde_json::from_slice::<serde_json::Value>(&body).ok().and_then(|v| v["repo"].as_str().map(String::from)).unwrap_or_default();
            match hf::list(&repo) {
                Ok(f) => send(&mut w, "200 OK", json!({"files": f.into_iter().map(|(f, n)| json!({"file": f, "bytes": n})).collect::<Vec<_>>()})),
                Err(err) => send(&mut w, "502 Bad Gateway", json!({"error": {"message": format!("{err:#}"), "type": "server_error"}})),
            }
        }
        ("GET", "/api/download") => send(&mut w, "200 OK", json!(*s.dl.lock().unwrap())),
        ("POST", "/api/download/cancel") => { s.dl.lock().unwrap().cancel = true; send(&mut w, "200 OK", json!(*s.dl.lock().unwrap())) }
        // Runs on its own thread so chats go on meanwhile; the page polls GET /api/download.
        ("POST", "/api/download") => {
            let v: serde_json::Value = serde_json::from_slice(&body).unwrap_or_default();
            let (repo, file) = (v["repo"].as_str().unwrap_or_default().to_string(), v["file"].as_str().unwrap_or_default().to_string());
            let mut g = s.dl.lock().unwrap();
            if g.running { drop(g); return send(&mut w, "409 Conflict", json!({"error": {"message": "a download is already running", "type": "conflict"}})); }
            *g = hf::Progress { repo: repo.clone(), file: file.clone(), running: true, ..Default::default() };
            drop(g);
            let (dl, dir) = (s.dl.clone(), s.dir.clone());
            std::thread::spawn(move || {
                let r = hf::download(&repo, &file, &dir, &dl);
                if let Err(e) = &r { eprintln!("download {repo} {file}: {e:#}"); } else { eprintln!("downloaded {repo} {file}"); }
                let mut g = dl.lock().unwrap();
                (g.running, g.error) = (false, r.err().map(|e| format!("{e:#}")));
            });
            send(&mut w, "202 Accepted", json!(*s.dl.lock().unwrap()))
        }
        // The prompt's tokens as the model would see them, template and tools included.
        ("POST", "/v1/messages/count_tokens") => {
            let Some(l) = l else { return send(&mut w, "503 Service Unavailable", json!({"error": {"message": "no model loaded", "type": "server_error"}})) };
            match serve::messages_body(&body).and_then(|b| serve::chat_request(&b)) {
                Ok(req) => {
                    let prompt = l.tpl.render(&req.messages, &req.tools, req.think, req.preserve_thinking.unwrap_or(e.preserve_thinking), true);
                    send(&mut w, "200 OK", json!({"input_tokens": l.tok.encode(&prompt)?.len()}))
                }
                Err(err) => send(&mut w, "400 Bad Request", json!({"error": {"message": format!("{err:#}"), "type": "invalid_request_error"}})),
            }
        }
        // The Anthropic Messages API (Claude Code) is translated to a chat request, and the reply back.
        ("POST", p @ ("/v1/chat/completions" | "/v1/messages")) => {
            let anth = p == "/v1/messages";
            let Some(l) = l else { return send(&mut w, "503 Service Unavailable", json!({"error": {"message": "no model loaded", "type": "server_error"}})) };
            let (r, tok, tpl, name) = (&mut l.r, &l.tok, l.tpl, l.name.as_str());
            match r { Runner::Gpu(g) => g.owner = who.id, Runner::Slot(c) => (c.owner, c.conn) = (who.id, w.try_clone().ok()), _ => {} }
            let req = match if anth { serve::messages_body(&body) } else { Ok(body.clone()) }.and_then(|b| serve::chat_request(&b)) {
                Ok(q) => q,
                Err(err) => return send(&mut w, "400 Bad Request", json!({"error": {"message": format!("{err:#}"), "type": "invalid_request_error"}})),
            };
            // Room is checked on the full prompt before any state changes.
            let preserve = req.preserve_thinking.unwrap_or(e.preserve_thinking);
            let prompt = tpl.render(&req.messages, &req.tools, req.think, preserve, true);
            // The system and tools block, which compacted or rewritten conversations keep.
            let n_sys = req.messages.iter().take_while(|m| m.role == "system").count();
            let system = tpl.render(&req.messages[..n_sys], &req.tools, req.think, preserve, false);
            let ids = tok.encode(&prompt)?;
            // One line per chat request, and one when it finishes (see `log` below).
            let key_name = if who.name.is_empty() { "open" } else { who.name.as_str() };
            eprintln!("request: {method} {p} key={key_name} model={name} prompt={} tok stream={} tools={}",
                ids.len(), req.stream, req.tools.len());
            let mut smp = e.sampler();
            smp.temp = req.temperature.unwrap_or(smp.temp);
            smp.top_k = req.top_k.unwrap_or(smp.top_k);
            smp.top_p = req.top_p.unwrap_or(smp.top_p);
            if req.seed.is_some() { smp.rng = seed(req.seed); }
            let n = room(e, ids.len(), req.max_tokens.unwrap_or(usize::MAX).min(s.max_tokens));
            if n == 0 { return send(&mut w, "400 Bad Request", json!({"error": {"message": format!("prompt of {} tokens fills the context", ids.len()), "type": "invalid_request_error"}})); }
            let id = format!("chatcmpl-{i}");
            let chunk = |delta: serde_json::Value, finish: Option<&str>| json!({"id": id, "object": "chat.completion.chunk", "created": created, "model": name,
                "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]});
            // With tools, a stream holds back the text from a `<tool_call>` tag on until the reply is parsed.
            let tools = req.tool_calls && !req.tools.is_empty();
            let mut cached = 0;
            let mut k = 0;  // tokens decoded
            let mut opened = false;  // Messages API stream: the text block has started
            let mut hold = Hold::new(tools, req.stop);
            let n_system = tok.encode(&system)?.len();
            let (mut t0, mut t1) = (Instant::now(), Instant::now());
            // Under `--parallel` a request is busy (and its prefill timed) from when the model takes it, not while it
            // waits for a slot.
            let mut busy = false;
            let start = |busy: &mut bool| {
                let mut st = s.stats.lock().unwrap();
                if st.busy == 0 { st.live_tokens = 0; }
                st.busy += 1;
                *busy = true;
            };
            if !matches!(r, Runner::Slot(_)) { start(&mut busy); }
            // Whether the prompt reached the model: a client that left while it waited in the queue is not logged.
            let mut prefilled = false;
            let res = (|| -> anyhow::Result<(Vec<u32>, bool)> {
                let logits;
                if serve::gone(&w) { anyhow::bail!("client closed the connection"); }
                (_, logits, cached) = r.chat(tok, &prompt, &tpl.render(&req.messages, &req.tools, req.think, preserve, false), &system)?;
                if let Runner::Slot(c) = &*r && let Some(t) = c.started { t0 = t; start(&mut busy); }
                prefilled = true;
                t1 = Instant::now();
                if serve::gone(&w) { anyhow::bail!("client closed the connection"); }
                if req.stream {
                    write!(w, "HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nCache-Control: no-cache\r\nConnection: close\r\n\r\n")?;
                    if anth {
                        sse(&mut w, json!({"type": "message_start", "message": {"id": format!("msg_{i}"), "type": "message", "role": "assistant", "model": name,
                            "content": [], "stop_reason": null, "stop_sequence": null,
                            "usage": {"input_tokens": ids.len() - cached, "cache_read_input_tokens": cached, "output_tokens": 0}}}))?;
                    } else {
                        write!(w, "data: {}\n\n", chunk(json!({"role": "assistant", "content": ""}), None))?;
                    }
                }
                let mut last_stream_activity = Instant::now();
                decode(r, tok, e.mtp() > 0, &mut smp, logits, n, &mut |t| {
                    s.stats.lock().unwrap().live_tokens += 1;
                    // A client that left stops the reply (a stream notices on the next write; held text writes nothing).
                    k += 1;
                    if k % 16 == 0 && serve::gone(&w) { anyhow::bail!("client closed the connection"); }
                    let t = hold.push(t);
                    if req.stream {
                        if !t.is_empty() {
                            if !anth { write!(w, "data: {}\n\n", chunk(json!({"content": t}), None))?; } else { text_delta(&mut w, &mut opened, &t)?; }
                            last_stream_activity = Instant::now();
                        } else if last_stream_activity.elapsed() >= Duration::from_secs(15) {
                            w.write_all(b": keep-alive\n\n")?;
                            last_stream_activity = Instant::now();
                        }
                    }
                    Ok(hold.stopped)
                })
            })();
            {
                let mut st = s.stats.lock().unwrap();
                if busy { st.busy -= 1; }
                gpu_stats(r, &mut st);
            }
            let decoded = t1.elapsed();
            let ms = |d: Duration| d.as_secs_f64() * 1e3;
            let mut last = serve::Last { at: created, model: name.into(), system_tokens: n_system, cached_tokens: cached,
                prompt_tokens: ids.len(), completion_tokens: k, prefill_ms: ms(t1 - t0), decode_ms: ms(decoded), finish: String::new() };
            let log = |last: &serve::Last| {
                let decode_s = last.decode_ms / 1e3;
                let prefill_s = last.prefill_ms / 1e3;
                // Cached prompt tokens were not prefilled again, so they do not count toward the prefill speed.
                let new_prompt = last.prompt_tokens.saturating_sub(last.cached_tokens);
                let decode_tps = if decode_s > 0.0 { last.completion_tokens as f64 / decode_s } else { 0.0 };
                let prefill_tps = if prefill_s > 0.0 { new_prompt as f64 / prefill_s } else { 0.0 };
                eprintln!("done: key={key_name} model={} prompt={} tok ({} cached) -> {} tok in {decode_s:.2} s, \
                    decode {decode_tps:.1} tok/s, prefill {prefill_tps:.1} tok/s, finish={}",
                    last.model, last.prompt_tokens, last.cached_tokens, last.completion_tokens, last.finish);
                if let Some(f) = &s.usage {
                    let mut v = json!(last);
                    v["key"] = who.name.clone().into();
                    // A failed write must not fail the reply; it is reported.
                    if let Err(err) = writeln!(f.lock().unwrap(), "{v}") { eprintln!("usage log: {err}"); }
                }
            };
            // The next request starts from the saved history state or from scratch. A stream that already started is just cut off.
            let (out, stop) = match res {
                Ok(x) => x,
                Err(err) => {
                    // Logged with the tokens decoded so far, which a client that left may have received.
                    let gone = serve::gone(&w);
                    last.finish = if gone { "cut" } else { "error" }.into();
                    if prefilled || !gone { log(&last); }
                    if !req.stream && !gone { return send(&mut w, "500 Internal Server Error", json!({"error": {"message": format!("{err:#}"), "type": "server_error"}})); }
                    return Err(err);
                }
            };
            // A malformed call goes out as plain text.
            let calls = if tools { tpl.parse_calls(&hold.text, &req.tools) } else { None };
            last.completion_tokens = out.len();
            last.finish = if calls.is_some() { "tool_calls" } else if stop { "stop" } else { "length" }.into();
            log(&last);
            s.stats.lock().unwrap().record(last);
            let calls_json = |(content, calls): &(String, Vec<(String, String)>), stream: bool| {
                let c: Vec<_> = calls.iter().enumerate().map(|(k, (f, a))| {
                    let mut c = json!({"id": format!("call_{i}_{k}"), "type": "function", "function": {"name": f, "arguments": a}});
                    if stream { c["index"] = k.into(); }
                    c
                }).collect();
                if stream { json!({"tool_calls": c}) }
                else { json!({"role": "assistant", "content": if content.is_empty() { None } else { Some(content) }, "tool_calls": c}) }
            };
            if anth {
                let reason = if calls.is_some() { "tool_use" } else if stop { "end_turn" } else { "max_tokens" };
                let usage = json!({"input_tokens": ids.len() - cached, "cache_read_input_tokens": cached, "cache_creation_input_tokens": 0, "output_tokens": out.len()});
                let uses: Vec<_> = calls.iter().flat_map(|c| &c.1).enumerate().map(|(k, (f, a))| json!({"type": "tool_use", "id": format!("toolu_{i}_{k}"),
                    "name": f, "input": serde_json::from_str::<serde_json::Value>(a).unwrap_or(json!({}))})).collect();
                if !req.stream {
                    let text = calls.as_ref().map_or(&hold.text, |c| &c.0);
                    let content: Vec<_> = (!text.is_empty()).then(|| json!({"type": "text", "text": text})).into_iter().chain(uses).collect();
                    return send(&mut w, "200 OK", json!({"id": format!("msg_{i}"), "type": "message", "role": "assistant", "model": name, "content": content,
                        "stop_reason": reason, "stop_sequence": null, "usage": usage}));
                }
                if calls.is_none() && !hold.rest().is_empty() { text_delta(&mut w, &mut opened, hold.rest())?; }
                if opened { sse(&mut w, json!({"type": "content_block_stop", "index": 0}))?; }
                for (k, u) in uses.iter().enumerate() {
                    let (index, input) = (k + opened as usize, u["input"].to_string());
                    let mut start = u.clone();
                    start["input"] = json!({});
                    sse(&mut w, json!({"type": "content_block_start", "index": index, "content_block": start}))?;
                    sse(&mut w, json!({"type": "content_block_delta", "index": index, "delta": {"type": "input_json_delta", "partial_json": input}}))?;
                    sse(&mut w, json!({"type": "content_block_stop", "index": index}))?;
                }
                sse(&mut w, json!({"type": "message_delta", "delta": {"stop_reason": reason, "stop_sequence": null}, "usage": {"output_tokens": out.len()}}))?;
                return sse(&mut w, json!({"type": "message_stop"}));
            }
            let finish = if calls.is_some() { "tool_calls" } else if stop { "stop" } else { "length" };
            let usage = json!({"prompt_tokens": ids.len(), "completion_tokens": out.len(), "total_tokens": ids.len() + out.len(),
                "prompt_tokens_details": {"cached_tokens": cached}});
            if req.stream {
                match &calls {
                    Some(c) => write!(w, "data: {}\n\n", chunk(calls_json(c, true), None))?,
                    None if !hold.rest().is_empty() => write!(w, "data: {}\n\n", chunk(json!({"content": hold.rest()}), None))?,
                    None => {}
                }
                let mut last = chunk(json!({}), Some(finish));
                last["usage"] = usage;
                Ok(write!(w, "data: {last}\n\ndata: [DONE]\n\n")?)
            } else {
                let message = match &calls { Some(c) => calls_json(c, false), None => json!({"role": "assistant", "content": hold.text}) };
                send(&mut w, "200 OK", json!({"id": id, "object": "chat.completion", "created": created, "model": name,
                    "choices": [{"index": 0, "message": message, "finish_reason": finish}], "usage": usage}))
            }
        }
        _ => send(&mut w, "404 Not Found", json!({"error": {"message": format!("no route {method} {path}"), "type": "not_found"}})),
    }
}

#[cfg(test)]
mod flag_tests {
    use super::resolve_flags;

    #[test]
    fn parallel_mtp_are_explained() {
        // `--parallel` with MTP: MTP off, one message naming both flags.
        let (n, p, k) = resolve_flags(true, 4, 1, 1, 0, false).unwrap();
        assert_eq!((p, k), (4, 0));
        assert_eq!(n, ["--parallel 4 and --mtp 1: not supported together, decoding without MTP drafts"]);
    }

    #[test]
    fn mtp_without_a_head_runs_without_drafts() {
        let (n, _, k) = resolve_flags(true, 1, 3, 0, 0, false).unwrap();
        assert_eq!(k, 0);
        assert_eq!(n, ["--mtp 3: this model has no MTP head: decoding without drafts"]);
        // A model with a head keeps its drafts.
        let (n, _, k) = resolve_flags(true, 1, 3, 1, 0, false).unwrap();
        assert!(n.is_empty() && k == 3);
        // A layer split or hyper-connections explain themselves instead.
        for (split, hc, why) in [(true, 0, "not available with a multi-GPU layer split"),
                                 (false, 4, "not supported for this model (hyper-connections)")] {
            let (n, _, k) = resolve_flags(true, 1, 3, 1, hc, split).unwrap();
            assert_eq!(k, 0);
            assert_eq!(n, [format!("--mtp 3: {why}: decoding without drafts")]);
        }
    }

    #[test]
    fn cpu_requires_the_gpu_for_both() {
        let (n, _, k) = resolve_flags(false, 2, 1, 1, 0, false).unwrap();
        assert_eq!(k, 0);
        assert_eq!(n, ["--parallel 2: requires --gpu (the CPU answers one request at a time)",
                       "--mtp 1: requires --gpu: decoding without drafts"]);
        // No flags set (0 means unset) prints nothing.
        assert_eq!(resolve_flags(false, 0, 0, 0, 0, false).unwrap(), (vec![], 1, 0));
    }

    #[test]
    fn parallel_range_is_rejected() {
        for n in [256, 1000] {
            let e = resolve_flags(true, n, 0, 0, 0, false).unwrap_err().to_string();
            assert_eq!(e, format!("--parallel {n}: 1 to 255 slots"));
        }
        assert!(resolve_flags(true, 255, 0, 0, 0, false).is_ok());
        assert_eq!(resolve_flags(true, 1, 0, 0, 0, false).unwrap(), (vec![], 1, 0));
    }
}

#[cfg(test)]
mod bench_tests {
    use super::{bench_record, round1, BenchMeta, BenchResult, Cli, ExpertStats, Stat};
    use clap::Parser;
    use serde_json::Value;
    use std::path::Path;

    fn meta() -> BenchMeta<'static> {
        BenchMeta {
            backend: "cpu",
            backend_arg: None,
            device: &[],
            model: Path::new("/mnt/models/Qwen3.6-35B-A3B-UD-Q2_K_XL.gguf"),
            ctx: 32896,
            chunk: 4096,
            kv: "f16",
            mtp: 0,
            tg: 128,
            reps: 3,
        }
    }

    fn result(pp: usize, prefill: Stat, decode: Stat) -> BenchResult {
        BenchResult { pp, prefill, decode, bytes_per_token: 0, decode_median: decode.mean }
    }

    fn parsed(record: &Value) -> Value {
        // One compact object plus a newline is what reaches the file: it must parse back unchanged.
        let mut line = serde_json::to_string(record).unwrap();
        line.push('\n');
        assert!(line.ends_with("}\n") && line.matches('\n').count() == 1);
        serde_json::from_slice::<Value>(line.as_bytes()).unwrap()
    }

    #[test]
    fn bench_record_schema_and_one_result_per_pp_in_order() {
        let st = |x: f64| Stat { mean: round1(x), min: round1(x), max: round1(x) };
        let results = [result(512, st(2135.7), st(129.5)), result(4096, st(1900.0), st(120.0)), result(32768, st(1500.0), st(80.0))];
        let v = parsed(&bench_record(&meta(), &results, None, 1_762_617_600));
        assert_eq!(v["schema"], "strata.bench.v1");
        assert_eq!(v["unix_time"], 1_762_617_600u64);
        assert_eq!(v["backend"], "cpu");
        assert!(v.get("backend_arg").is_none());
        assert_eq!(v["device"], serde_json::json!([]));
        assert_eq!(v["model"]["name"], "Qwen3.6-35B-A3B-UD-Q2_K_XL.gguf");
        assert_eq!(v["model"]["path"], "/mnt/models/Qwen3.6-35B-A3B-UD-Q2_K_XL.gguf");
        assert_eq!((v["ctx"].as_u64(), v["chunk"].as_u64(), v["mtp"].as_u64()), (Some(32896), Some(4096), Some(0)));
        assert_eq!((v["tg"].as_u64(), v["reps"].as_u64()), (Some(128), Some(3)));
        let rs = v["results"].as_array().unwrap();
        assert_eq!(rs.iter().map(|r| r["pp"].as_u64().unwrap()).collect::<Vec<_>>(), [512, 4096, 32768]);
        assert_eq!(rs[0]["prefill_tok_s"]["mean"], 2135.7);
    }

    #[test]
    fn bench_record_rates_match_the_text_rendering() {
        let raw_p = [2144.9, 2129.6, 2132.6];
        let raw_d = [128.9, 129.8, 129.8];
        let (p, d) = (Stat::of(&raw_p), Stat::of(&raw_d));
        let text = format!("pp {:6}: prefill {} tok/s | tg {}: decode {} tok/s", 512, p.text(), 32, d.text());
        let v = parsed(&bench_record(&meta(), &[result(512, p, d)], None, 0));
        for (key, stat) in [("prefill_tok_s", p), ("decode_tok_s", d)] {
            let o = &v["results"][0][key];
            assert_eq!(o["mean"], stat.mean);
            assert_eq!(o["min"], stat.min);
            assert_eq!(o["max"], stat.max);
            // The same decimal strings the text line carries.
            assert!(text.contains(&format!("{:.1}", o["mean"].as_f64().unwrap())));
        }
        assert_eq!(format!("{:.1}", p.mean), "2135.7");
        assert_eq!(format!("{:.1}", p.min), "2129.6");
        assert_eq!(format!("{:.1}", p.max), "2144.9");
        assert!(text.starts_with("pp    512: prefill 2135.7 (2129.6-2144.9) tok/s | tg 32: decode 129.5 (128.9-129.8) tok/s"));
    }

    #[test]
    fn bench_record_omits_expert_without_a_cache() {
        let v = parsed(&bench_record(&meta(), &[result(512, Stat { mean: 1.0, min: 1.0, max: 1.0 }, Stat { mean: 2.0, min: 2.0, max: 2.0 })], None, 0));
        assert!(v.get("expert").is_none());
        assert!(v["results"][0].get("expert").is_none());
    }

    #[test]
    fn bench_record_expert_object_uses_the_printed_numbers() {
        let stats = ExpertStats {
            hits: 1024, misses: 0, swaps: 3, resident: 10240, total: 10240,
            bytes_per_token: 329_006_694, cached: true, all_fast: true,
        };
        let mut r = result(512, Stat { mean: 2135.7, min: 2129.6, max: 2144.9 }, Stat { mean: 129.5, min: 128.9, max: 129.8 });
        r.bytes_per_token = 329_006_694;
        r.decode_median = 129.7;
        let mut m = meta();
        m.backend = "vulkan";
        m.backend_arg = Some("vulkan");
        m.device = &[0];
        let v = parsed(&bench_record(&m, &[r], Some(&stats), 0));
        assert_eq!(v["backend"], "vulkan");
        assert_eq!(v["backend_arg"], "vulkan");
        assert_eq!(v["device"], serde_json::json!([0]));
        let e = &v["expert"];
        assert_eq!(e["hit_rate_pct"], 100.0);
        assert_eq!((e["misses"].as_u64(), e["swaps"].as_u64()), (Some(0), Some(3)));
        assert_eq!((e["resident"].as_u64(), e["total"].as_u64()), (Some(10240), Some(10240)));
        assert_eq!(e["bytes_per_token"], 329_006_694u64);
        assert_eq!(e["mb_per_token"], 313.8);
        let pe = &v["results"][0]["expert"];
        assert_eq!(pe["bytes_per_token"], 329_006_694u64);
        assert_eq!(pe["mb_per_token"], 313.8);
        assert_eq!(pe["gb_per_s"], round1(329_006_694.0 * 129.7 / 1e9));
        assert_eq!(pe["at_decode_tok_s"], 129.7);
    }

    #[test]
    fn bench_record_rejects_json_out_dash() {
        let e = Cli::try_parse_from(["rustingstrata", "bench", "--model", "m.gguf", "--json-out", "-"]).err().unwrap();
        assert!(e.to_string().contains("stdout carries the text block"), "{e}");
        assert!(Cli::try_parse_from(["rustingstrata", "bench", "--model", "m.gguf", "--json-out", "/tmp/x.json"]).is_ok());
    }
}
