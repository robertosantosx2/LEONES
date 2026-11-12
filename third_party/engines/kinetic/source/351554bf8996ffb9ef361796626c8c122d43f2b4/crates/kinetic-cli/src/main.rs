//! `kinetic`: run, chat with, serve and measure local language models.

mod ahead;
mod attach;
mod bench;
mod chat;
mod compare;
mod console;
mod doctor;
mod fit;
mod fix;
mod generate;
mod gpu;
mod info;
mod library;
mod llama_flags;
mod memory;
mod model_file;
mod perplexity;
mod pull;
mod quantize;
mod receipt;
mod render;
mod sampler_args;
mod sampling_command;
mod start;
mod system;
mod tech;

use std::io::IsTerminal;
use std::net::TcpListener;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use clap::{Args, Parser, Subcommand, ValueEnum};
use kinetic_gguf::{Gguf, GgufFile, TensorSource};
use kinetic_models::lora::{Adapted, Adapter};
use kinetic_models::warm::{self, Warm};
use kinetic_models::{Embedder, Model, RopeScaling, ScalingKind};
use kinetic_server::{Backend, CpuBackend, Embeddings, Engine, Request, Sampling};
use kinetic_vision::VisionEncoder;

use library::Local;
use model_file::ModelFile;
use sampler_args::SamplerArgs;
use tech::Tech;

type Result<T> = std::result::Result<T, Box<dyn std::error::Error + Send + Sync>>;

/// Context length used when the model allows more and -c is not given.
const DEFAULT_CONTEXT: usize = 32768;
/// Bytes of prompt states the warm cache keeps in memory and on disk.
const WARM_MEMORY: usize = 1 << 30;
const WARM_DISK: u64 = 2 << 30;

#[derive(Parser)]
#[command(
    name = "kinetic",
    version,
    about = "Run language models on your own computer."
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Answer one prompt, streamed to stdout (reads stdin without a prompt)
    Run {
        #[command(flatten)]
        model: ModelArg,
        /// The prompt
        prompt: Option<String>,
        /// The prompt, as a flag
        #[arg(
            short = 'p',
            long = "prompt",
            value_name = "PROMPT",
            conflicts_with = "prompt"
        )]
        prompt_flag: Option<String>,
        /// Write a receipt that reproduces the answer to FILE
        #[arg(long, value_name = "FILE")]
        receipt: Option<PathBuf>,
        #[command(flatten)]
        gen: GenArgs,
    },
    /// Chat in the terminal
    Chat {
        #[command(flatten)]
        model: ModelArg,
        /// Vision projector of a multimodal model [default: the one stored
        /// with the model]
        #[arg(long, value_name = "FILE")]
        mmproj: Option<PathBuf>,
        #[command(flatten)]
        gen: GenArgs,
    },
    /// Serve OpenAI- and Ollama-compatible APIs
    Serve {
        #[command(flatten)]
        model: ModelArg,
        /// Address to listen on; anything but 127.0.0.1 exposes the server
        #[arg(long, default_value = "127.0.0.1")]
        host: String,
        /// Port to listen on [default: 8080, or 11434 with --ollama]
        #[arg(long)]
        port: Option<u16>,
        /// Listen on Ollama's port, so apps made for Ollama work unchanged
        #[arg(long)]
        ollama: bool,
        /// Vision projector of a multimodal model, so requests may carry images
        #[arg(long, value_name = "FILE")]
        mmproj: Option<PathBuf>,
        /// Requests answered at once [default: as many as half the free
        /// memory holds at full context, up to 4]
        #[arg(long, value_name = "N", value_parser = clap::value_parser!(u16).range(1..))]
        parallel: Option<u16>,
        /// Model name the API reports [default: the file's name]
        #[arg(long, value_name = "NAME")]
        alias: Option<String>,
        /// Require `Authorization: Bearer KEY` on every route but /health
        #[arg(long, value_name = "KEY")]
        api_key: Option<String>,
        #[command(flatten)]
        runtime: RuntimeArgs,
    },
    /// Measure load time, prompt, generation and edit speed, and peak memory
    Bench {
        #[command(flatten)]
        model: ModelArg,
        /// Print the results as JSON
        #[arg(long)]
        json: bool,
        /// Runs of each test; the best is reported
        #[arg(short = 'r', long, default_value_t = 3)]
        repetitions: usize,
        /// CPU threads [default: all]
        #[arg(short = 't', long, value_name = "N")]
        threads: Option<usize>,
        /// Where the model runs; auto picks the GPU when the model fits on it
        #[arg(long, value_enum, default_value_t = Device::Auto, ignore_case = true)]
        device: Device,
        /// Also run llama.cpp's llama-bench on the same file with the same
        /// settings and print a card comparing both [default: llama-bench
        /// on PATH or in a usual install folder]
        #[arg(long, value_name = "LLAMA_BENCH", num_args = 0..=1, default_missing_value = "")]
        compare: Option<String>,
        /// Tokens already in the context when the generation test starts
        #[arg(
            short = 'd',
            long,
            value_name = "N",
            default_value_t = 0,
            conflicts_with = "compare"
        )]
        depth: usize,
        #[command(flatten)]
        off: OffArg,
    },
    /// Check this computer: CPU, memory, GPUs, drivers and disk, with fixes
    Doctor,
    /// Download a GGUF model from Hugging Face; the only command that uses
    /// the network
    Pull {
        /// The repository, and optionally the quantization: <org>/<repo>[:<quant>]
        repo: String,
        /// The file to download, when the quantization does not single one out
        #[arg(long, value_name = "NAME")]
        file: Option<String>,
        /// Skip the vision projector a multimodal model comes with
        #[arg(long)]
        no_mmproj: bool,
        /// Where to keep models [default: KINETIC_MODELS, or the user's data folder]
        #[arg(long, value_name = "DIR")]
        dir: Option<PathBuf>,
    },
    /// Show where each model would run here and roughly how fast
    Fit {
        /// A model, a model's name or a folder [default: every model found]
        target: Option<PathBuf>,
    },
    /// List the models on this computer, from Ollama, LM Studio, the
    /// Hugging Face and llama.cpp caches and Kinetic's own folder
    Models,
    /// Show what a model file contains
    Info {
        #[command(flatten)]
        model: ModelArg,
    },
    /// Check every hash of a .ktc file and report its signature
    Verify {
        /// The .ktc file
        file: PathBuf,
    },
    /// Rerun the request a receipt records and check every output token
    VerifyReceipt {
        /// The receipt
        file: PathBuf,
        /// The model file [default: the path in the receipt]
        #[arg(short = 'm', long, value_name = "MODEL")]
        model: Option<PathBuf>,
        /// Where to rerun [default: the receipt's device]
        #[arg(long, value_enum, ignore_case = true)]
        device: Option<Device>,
        /// CPU threads [default: all]
        #[arg(short = 't', long, value_name = "N")]
        threads: Option<usize>,
    },
    /// Measure perplexity over a text file, as llama-perplexity does (CPU)
    Perplexity {
        #[command(flatten)]
        model: ModelArg,
        /// The text to score
        #[arg(value_name = "FILE")]
        text: Option<PathBuf>,
        /// The text to score, as a flag
        #[arg(
            short = 'f',
            long = "file",
            value_name = "FILE",
            conflicts_with = "text"
        )]
        file: Option<PathBuf>,
        /// Tokens per chunk; the second half of each is scored
        #[arg(
            short = 'c',
            long = "ctx-size",
            value_name = "N",
            default_value_t = 512
        )]
        context: usize,
        /// Score at most N chunks [default: all]
        #[arg(long, value_name = "N")]
        chunks: Option<usize>,
        /// Save the log-probabilities for a later --kl-divergence
        #[arg(long, value_name = "FILE", conflicts_with = "kl_divergence")]
        kl_divergence_base: Option<PathBuf>,
        /// Compare with log-probabilities saved by --kl-divergence-base here
        /// or by llama-perplexity
        #[arg(long, value_name = "BASE_LOGITS")]
        kl_divergence: Option<PathBuf>,
        /// CPU threads [default: all]
        #[arg(short = 't', long, value_name = "N")]
        threads: Option<usize>,
    },
    /// Write a GGUF model in another type, as llama-quantize does
    Quantize {
        /// The model to read, with F32, F16, BF16 or Q8_0 weights
        input: PathBuf,
        /// The GGUF file to write
        output: PathBuf,
        /// Q8_0, Q6_K, Q5_K_M, Q4_K_M or Q4_0
        #[arg(value_name = "TYPE")]
        kind: String,
        /// CPU threads [default: all]
        #[arg(short = 't', long, value_name = "N")]
        threads: Option<usize>,
    },
}

#[derive(Args)]
struct ModelArg {
    /// A .gguf or .ktc model file, or the name of a model `kinetic models`
    /// lists, such as qwen3:4b
    #[arg(value_name = "MODEL", required_unless_present = "model_flag")]
    model: Option<PathBuf>,
    /// The model file, as a flag
    #[arg(short = 'm', long = "model", value_name = "MODEL")]
    model_flag: Option<PathBuf>,
}

impl ModelArg {
    /// The model, and the first positional argument when -m named the
    /// model instead.
    fn split(self) -> Result<(Local, Option<String>)> {
        let (arg, rest) = match (self.model_flag, self.model) {
            (Some(path), rest) => (path, rest.map(|p| p.to_string_lossy().into_owned())),
            (None, Some(path)) => (path, None),
            (None, None) => unreachable!("clap requires a model"),
        };
        Ok((library::locate(&arg)?, rest))
    }

    fn locate(self) -> Result<Local> {
        match self.split()? {
            (model, None) => Ok(model),
            (_, Some(extra)) => Err(format!("unexpected argument {extra:?}").into()),
        }
    }
}

#[derive(Args)]
struct RuntimeArgs {
    /// Most tokens per conversation; 0 uses all the model supports
    #[arg(short = 'c', long = "ctx-size", value_name = "N")]
    context: Option<usize>,
    /// CPU threads [default: all]
    #[arg(short = 't', long, value_name = "N")]
    threads: Option<usize>,
    /// Where the model runs; auto picks the GPU when the model fits on it
    #[arg(long, value_enum, default_value_t = Device::Auto, ignore_case = true)]
    device: Device,
    /// Most layers on the GPU; the rest run on the CPU [default: as many as fit]
    #[arg(long, value_name = "N")]
    gpu_layers: Option<usize>,
    /// Directory for states of earlier prompts, which later prompts that
    /// start the same way resume from [default: the user's cache directory]
    #[arg(long, value_name = "DIR")]
    cache_dir: Option<PathBuf>,
    /// Run every prompt from its first token; same as --off warm-start
    #[arg(long, conflicts_with = "cache_dir")]
    no_prompt_cache: bool,
    /// How the CUDA cache stores keys; q8_0 takes about half the memory of
    /// f16 but rounds them, so outputs change
    #[arg(long, value_enum, value_name = "TYPE", default_value_t = CacheType::F16)]
    cache_type_k: CacheType,
    /// How the CUDA cache stores values, as --cache-type-k
    #[arg(long, value_enum, value_name = "TYPE", default_value_t = CacheType::F16)]
    cache_type_v: CacheType,
    /// Sign receipts with this Ed25519 secret key: 32 bytes or 64 hex digits
    #[arg(long, value_name = "FILE")]
    sign_key: Option<PathBuf>,
    /// Keep the model in RAM, so the system never swaps it out
    #[arg(long)]
    mlock: bool,
    /// Read the model into memory instead of mapping the file
    #[arg(long)]
    no_mmap: bool,
    /// Jinja chat template to use instead of the model's own
    #[arg(long, value_name = "FILE")]
    chat_template_file: Option<PathBuf>,
    /// LoRA adapters in GGUF to merge into the model, comma-separated;
    /// repeatable
    #[arg(long, value_name = "FILE", value_delimiter = ',')]
    lora: Vec<PathBuf>,
    /// LoRA adapters with scales, as FILE:SCALE, comma-separated; repeatable
    #[arg(long, value_name = "FILE:SCALE", value_delimiter = ',')]
    lora_scaled: Vec<String>,
    #[command(flatten)]
    off: OffArg,
    #[command(flatten)]
    rope: RopeArgs,
}

impl RuntimeArgs {
    fn is_off(&self, tech: Tech) -> bool {
        self.off.off.contains(&tech) || (tech == Tech::WarmStart && self.no_prompt_cache)
    }

    /// The adapter files and their scales, opened.
    fn adapters(&self) -> Result<Vec<(GgufFile, f32)>> {
        let open =
            |path: &Path| GgufFile::open(path).map_err(|e| format!("{}: {e}", path.display()));
        let mut out = Vec::new();
        for path in &self.lora {
            out.push((open(path)?, 1.0));
        }
        for spec in &self.lora_scaled {
            // split at the last colon: Windows paths have one too
            let (path, scale) = spec
                .rsplit_once(':')
                .and_then(|(p, s)| Some((p, s.parse::<f32>().ok()?)))
                .ok_or_else(|| format!("--lora-scaled {spec}: write it as FILE:SCALE"))?;
            out.push((open(Path::new(path))?, scale));
        }
        Ok(out)
    }

    fn turned_off(&self) -> Vec<Tech> {
        Tech::ALL.into_iter().filter(|&t| self.is_off(t)).collect()
    }
}

#[derive(Args)]
struct OffArg {
    /// Speed technologies to turn off, to measure each one's gain: rad1,
    /// warm-start, zero-wait, shortlist, torque, convoy
    #[arg(
        long,
        value_enum,
        value_name = "LIST",
        value_delimiter = ',',
        hide_possible_values = true
    )]
    off: Vec<Tech>,
}

#[derive(Clone, Copy, PartialEq, Eq, ValueEnum)]
enum CacheType {
    F16,
    #[value(name = "q8_0")]
    Q8_0,
}

#[cfg(feature = "cuda")]
impl From<CacheType> for kinetic_cuda::KvType {
    fn from(t: CacheType) -> Self {
        match t {
            CacheType::F16 => kinetic_cuda::KvType::F16,
            CacheType::Q8_0 => kinetic_cuda::KvType::Q8_0,
        }
    }
}

/// Rotary scaling, as llama.cpp spells it; unset values keep the model's.
#[derive(Args)]
struct RopeArgs {
    /// Rotary scaling for contexts past the trained length [default: the model's]
    #[arg(long, value_enum, value_name = "KIND")]
    rope_scaling: Option<RopeKind>,
    /// How many times the trained context rotary positions stretch to
    #[arg(long, value_name = "N", conflicts_with = "rope_freq_scale")]
    rope_scale: Option<f32>,
    /// One over --rope-scale
    #[arg(long, value_name = "N")]
    rope_freq_scale: Option<f32>,
    /// Rotary base frequency; raising it is NTK-aware scaling
    #[arg(long, value_name = "N")]
    rope_freq_base: Option<f32>,
    /// The context the model was trained on, which YaRN stretches from
    #[arg(long, value_name = "N")]
    yarn_orig_ctx: Option<usize>,
}

#[derive(Clone, Copy, PartialEq, Eq, ValueEnum)]
enum RopeKind {
    None,
    Linear,
    Yarn,
}

impl RopeArgs {
    fn scaling(&self) -> RopeScaling {
        RopeScaling {
            kind: self.rope_scaling.map(|k| match k {
                RopeKind::None => ScalingKind::None,
                RopeKind::Linear => ScalingKind::Linear,
                RopeKind::Yarn => ScalingKind::Yarn,
            }),
            factor: self
                .rope_scale
                .or(self.rope_freq_scale.filter(|&s| s > 0.0).map(|s| 1.0 / s)),
            freq_base: self.rope_freq_base,
            original_context: self.yarn_orig_ctx,
        }
    }
}

#[derive(Clone, Copy, PartialEq, Eq, ValueEnum)]
enum Device {
    Auto,
    #[value(alias = "none")]
    Cpu,
    #[value(alias = "cuda0")]
    Cuda,
    #[value(alias = "vulkan0")]
    Vulkan,
}

#[derive(Args)]
struct GenArgs {
    /// System prompt
    #[arg(long)]
    system: Option<String>,
    /// Most tokens to generate per answer
    #[arg(
        short = 'n',
        long = "n-predict",
        value_name = "N",
        allow_negative_numbers = true
    )]
    max_tokens: Option<i64>,
    /// 0 always picks the likeliest token [default: the model's]
    #[arg(long)]
    temp: Option<f32>,
    /// Sample from the N likeliest tokens; 0 for all
    #[arg(long, value_name = "N")]
    top_k: Option<usize>,
    /// Sample from the likeliest tokens that add up to P
    #[arg(long, value_name = "P")]
    top_p: Option<f32>,
    /// Skip tokens less than P times as likely as the best
    #[arg(long, value_name = "P")]
    min_p: Option<f32>,
    /// Penalty for repeating recent tokens; 1 for none
    #[arg(long, value_name = "X")]
    repeat_penalty: Option<f32>,
    /// Seed for repeatable sampling
    #[arg(short = 's', long, value_name = "N")]
    seed: Option<u64>,
    /// Whether chat starts with the model's reasoning on, as llama.cpp's
    /// --reasoning
    #[arg(long, value_name = "on|off", value_parser = ["on", "off", "auto"], default_value = "on")]
    reasoning: String,
    #[command(flatten)]
    samplers: SamplerArgs,
    #[command(flatten)]
    runtime: RuntimeArgs,
}

impl GenArgs {
    fn request(&self, defaults: &Sampling) -> Request {
        let mut s = defaults.clone();
        s.temperature = self.temp.unwrap_or(s.temperature);
        s.top_k = self.top_k.unwrap_or(s.top_k);
        s.top_p = self.top_p.unwrap_or(s.top_p);
        s.min_p = self.min_p.unwrap_or(s.min_p);
        s.repeat_penalty = self.repeat_penalty.unwrap_or(s.repeat_penalty);
        s.seed = self.seed.or(s.seed);
        self.samplers.apply(&mut s);
        Request {
            sampling: s,
            // llama.cpp spells "no limit" as -1.
            max_tokens: self
                .max_tokens
                .and_then(|n| usize::try_from(n).ok())
                .filter(|&n| n > 0),
            stop: Vec::new(),
            grammar: None,
        }
    }
}

fn main() -> ExitCode {
    if std::env::args().len() == 1 {
        if console::double_clicked() {
            return console::open_terminal();
        }
        if std::io::stdin().is_terminal() && std::io::stdout().is_terminal() {
            return finish(first_run());
        }
    }
    let args = match llama_flags::translate(llama_flags::dispatch(std::env::args().collect())) {
        Ok(args) => args,
        Err(msg) => {
            eprintln!("kinetic: {msg}");
            return ExitCode::from(2);
        }
    };
    finish(run(Cli::parse_from(args)))
}

/// `kinetic` with nothing after it: pick a model, then chat with it.
fn first_run() -> Result<()> {
    match start::run()? {
        Some(model) => {
            let args = ["kinetic".into(), "chat".into(), model.into_os_string()];
            run(Cli::parse_from(args))
        }
        None => Ok(()),
    }
}

fn finish(result: Result<()>) -> ExitCode {
    match result {
        Ok(()) => ExitCode::SUCCESS,
        // Output piped into a command that stopped reading, as `| head` does.
        Err(e)
            if e.downcast_ref::<std::io::Error>()
                .is_some_and(|e| e.kind() == std::io::ErrorKind::BrokenPipe) =>
        {
            ExitCode::SUCCESS
        }
        Err(e) => {
            let msg = e.to_string();
            eprintln!("kinetic: {msg}");
            if let Some(fix) = fix::for_error(&msg) {
                eprintln!("  {fix}");
            }
            ExitCode::FAILURE
        }
    }
}

fn run(cli: Cli) -> Result<()> {
    match cli.command {
        Command::Run {
            model,
            prompt,
            prompt_flag,
            receipt,
            gen,
        } => {
            let (model, first) = model.split()?;
            let prompt = match (first, prompt) {
                (Some(_), Some(extra)) => {
                    return Err(format!("unexpected argument {extra:?}").into())
                }
                (first, prompt) => first.or(prompt).or(prompt_flag),
            };
            with_engine(&model, None, &gen.runtime, Some(1), |engine, device, _| {
                let prompt = match prompt {
                    Some(p) => p,
                    None => std::io::read_to_string(std::io::stdin())?,
                };
                generate::answer(engine, &gen, &prompt, device, receipt.as_deref())
            })
        }
        Command::Chat { model, mmproj, gen } => {
            let model = model.locate()?;
            read_ahead(&model.path);
            let mmproj = mmproj.or_else(|| model.projector.clone());
            with_engine(
                &model,
                mmproj.as_deref(),
                &gen.runtime,
                Some(1),
                |engine, device, _| chat::chat(engine, &gen, device),
            )
        }
        Command::Serve {
            model,
            host,
            port,
            ollama,
            mmproj,
            parallel,
            alias,
            api_key,
            runtime,
        } => {
            let port = port.unwrap_or(if ollama { 11434 } else { 8080 });
            let mut model = model.locate()?;
            if let Some(alias) = alias {
                model.name = alias;
            }
            let options = kinetic_server::Options { api_key };
            let path = &model.path;
            let listen = |name: &str, device: &str| -> Result<TcpListener> {
                let listener = TcpListener::bind((host.as_str(), port))
                    .map_err(|e| format!("cannot listen on {host}:{port}: {e}"))?;
                let addr = listener.local_addr()?;
                if !addr.ip().is_loopback() {
                    eprintln!("kinetic: listening beyond this computer; anyone who can reach {addr} can use the model");
                }
                eprintln!("Serving {name} on {device} at http://{addr}/v1 and, for Ollama apps, http://{addr}");
                Ok(listener)
            };
            if is_embedding_model(path)? {
                set_threads(runtime.threads)?;
                let file = ModelFile::open(path)?;
                let embedder = Embedder::load(file.source())?;
                let model = Embeddings::new(&model.name, file.source().header(), embedder)?;
                kinetic_server::serve_embeddings_with(&model, listen(model.name(), CPU)?, &options);
                return Ok(());
            }
            let mmproj = mmproj.or_else(|| model.projector.clone());
            let parallel = parallel.map(usize::from);
            with_engine(
                &model,
                mmproj.as_deref(),
                &runtime,
                parallel,
                |engine, device, technologies| {
                    let listener = listen(engine.name(), device)?;
                    eprintln!("Speed technologies {technologies}");
                    kinetic_server::serve_with(engine, listener, &options);
                    Ok(())
                },
            )
        }
        Command::Bench {
            model,
            json,
            repetitions,
            threads,
            device,
            compare,
            depth,
            off,
        } => {
            let model = model.locate()?;
            if let Some(llama_bench) = compare {
                if !off.off.is_empty() {
                    return Err("--off does not apply to --compare".into());
                }
                let settings = compare::Settings {
                    device,
                    threads: threads.unwrap_or_else(|| system::machine().threads),
                    repetitions: repetitions.max(1),
                };
                return compare::run(&model, Path::new(&llama_bench), &settings, json);
            }
            set_threads(threads)?;
            let tests = bench::Tests {
                repetitions: repetitions.max(1),
                depth,
            };
            bench::run(&model.path, &model.name, device, tests, &off.off, json)
        }
        Command::Doctor => doctor::run(),
        Command::Fit { target } => fit::run(target.as_deref()),
        Command::Pull {
            repo,
            file,
            no_mmproj,
            dir,
        } => pull::run(&pull::Pull {
            spec: &repo,
            file: file.as_deref(),
            projector: !no_mmproj,
            dir: dir.as_deref(),
        })
        .map(drop),
        Command::Models => library::list(),
        Command::Info { model } => info::print(&model.locate()?.path),
        Command::Verify { file } => verify(&file),
        Command::VerifyReceipt {
            file,
            model,
            device,
            threads,
        } => receipt::verify(&file, model, device, threads),
        Command::Perplexity {
            model,
            text,
            file,
            context,
            chunks,
            kl_divergence_base,
            kl_divergence,
            threads,
        } => {
            set_threads(threads)?;
            let (model, first) = model.split()?;
            let text = file.or(text).or(first.map(PathBuf::from));
            if let Some(base) = kl_divergence {
                return perplexity::kl_divergence(&model.path, &base);
            }
            let text = text.ok_or("give the text file to score")?;
            let opts = perplexity::Options {
                context: context.max(4),
                chunks,
                save_base: kl_divergence_base.as_deref(),
            };
            perplexity::run(&model.path, &text, &opts)
        }
        Command::Quantize {
            input,
            output,
            kind,
            threads,
        } => {
            set_threads(threads)?;
            quantize::run(&input, &output, &kind)
        }
    }
}

fn verify(file: &Path) -> Result<()> {
    let report = kinetic_ktc::verify(file, None)?;
    println!("{report}");
    if report.is_ok() {
        Ok(())
    } else {
        Err(format!("{} failed verification", file.display()).into())
    }
}

fn set_threads(threads: Option<usize>) -> Result<()> {
    if let Some(n) = threads {
        rayon::ThreadPoolBuilder::new()
            .num_threads(n)
            .build_global()?;
    }
    Ok(())
}

/// Loads `model`, with the vision projector at `mmproj` if given, onto the
/// device `runtime` asks for, to answer `parallel` requests at once or as
/// many as memory allows, and hands the engine, the device's description
/// and which speed technologies run to `f`.
fn with_engine(
    model: &Local,
    mmproj: Option<&Path>,
    runtime: &RuntimeArgs,
    parallel: Option<usize>,
    f: impl FnOnce(&Engine, &str, &str) -> Result<()>,
) -> Result<()> {
    set_threads(runtime.threads)?;
    let path = &model.path;
    let file = ModelFile::open_with(path, !runtime.no_mmap)?;
    if runtime.mlock {
        file.lock()?;
    }
    let projector = mmproj.map(GgufFile::open).transpose()?;
    let name = model.name.clone();
    let scaling = runtime.rope.scaling();
    let adapters = runtime.adapters()?;
    let adapted = match adapters.is_empty() {
        true => None,
        false => {
            let list: Vec<Adapter> = adapters
                .iter()
                .map(|(file, scale)| Adapter {
                    file,
                    scale: *scale,
                })
                .collect();
            Some(Adapted::new(file.source(), &list)?)
        }
    };
    let source: &dyn TensorSource = match &adapted {
        Some(a) => a,
        None => file.source(),
    };
    let model = kinetic_models::load_with(source, &scaling)?;
    if runtime.is_off(Tech::Shortlist) {
        model.disable_shortlist();
    }
    let n_embd = model.n_embd();
    let trained = file
        .source()
        .header()
        .arch_key("context_length")
        .and_then(|v| v.as_u64())
        .map_or(DEFAULT_CONTEXT, |n| n as usize);
    // A stretched context reaches as far as it is stretched.
    let trained = match scaling.factor {
        Some(f) if f > 1.0 => (trained as f64 * f as f64) as usize,
        _ => trained,
    };
    let context = match runtime.context {
        Some(0) => trained,
        Some(n) => n.min(trained),
        None => gpu_context(
            &model,
            file.source().header(),
            runtime,
            DEFAULT_CONTEXT.min(trained),
        ),
    };
    let parallel = match runtime.is_off(Tech::Convoy) {
        true => Some(1),
        false => parallel,
    };
    let ((mut backends, device), kind) = backend(&model, path, runtime, context, parallel)?;
    let first = backends.remove(0);
    let receipts = receipt::receipts(path, kind, &device, runtime, context)?;
    let mut engine = Engine::new(name, file.source().header(), first, context)?
        .with_backends(backends)
        .with_receipts(receipts);
    if runtime.is_off(Tech::ZeroWait) {
        engine = engine.without_zero_wait();
    }
    if let Some(file) = &runtime.chat_template_file {
        let source =
            std::fs::read_to_string(file).map_err(|e| format!("{}: {e}", file.display()))?;
        engine = engine.with_chat_template(&source)?;
    }
    let engine = match &projector {
        Some(p) => {
            #[allow(unused_mut)]
            let mut encoder = VisionEncoder::load(p)?;
            if encoder.n_embd_out() != n_embd {
                return Err("the projector was made for a different model".into());
            }
            // images encode where the text runs; without room they stay on the CPU
            #[cfg(feature = "cuda")]
            if kind == Device::Cuda {
                let _ = encoder.use_cuda();
            }
            engine.with_vision(encoder)?
        }
        None => engine,
    };
    f(
        &engine,
        &device,
        &tech::status(&runtime.turned_off(), kind, &Tech::ALL),
    )
}

/// `wanted`, or when its cache would not fit beside the model on the CUDA
/// GPU, the largest context that does, said in one line; otherwise layers
/// would quietly move to the CPU.
fn gpu_context(model: &Model, header: &Gguf, runtime: &RuntimeArgs, wanted: usize) -> usize {
    let gpu = cfg!(feature = "cuda") && matches!(runtime.device, Device::Auto | Device::Cuda);
    let weights = fit::Weights::of(header);
    // experts leave the GPU by design, and --gpu-layers asked for a split
    if !gpu || runtime.gpu_layers.is_some() || weights.has_experts() {
        return wanted;
    }
    let Some(free) = system::cuda_free() else {
        return wanted;
    };
    // state_bytes counts f32; the GPU keeps attention caches in --cache-type-*
    let share = |t: CacheType| match t {
        CacheType::F16 => 0.5,
        CacheType::Q8_0 => 34.0 / 128.0,
    };
    let share = (share(runtime.cache_type_k) + share(runtime.cache_type_v)) / 2.0;
    let fixed = model.state_bytes(0) as u64;
    let cache = |n| fixed + ((model.state_bytes(n) as u64 - fixed) as f64 * share) as u64;
    match fit::gpu_context(wanted, free, weights.total(), cache) {
        Some(n) => {
            eprintln!(
                "kinetic: context {}k to fit the GPU; -c to change",
                n / 1024
            );
            n
        }
        None => wanted,
    }
}

const CPU: &str = "the CPU";

/// Most requests answered at once when the user does not say.
const MAX_DEFAULT_SLOTS: usize = 4;

/// As many sequences of `context` tokens as half the free memory holds, at
/// least one and at most [`MAX_DEFAULT_SLOTS`].
fn default_slots(model: &Model, context: usize) -> usize {
    let per = model.state_bytes(context).max(1) as u64;
    kinetic_models::memory::available().map_or(1, |free| {
        ((free / 2 / per) as usize).clamp(1, MAX_DEFAULT_SLOTS)
    })
}

/// Backends for one model on one device, one per request answered at once,
/// and the description of the device.
type Placed<'a> = (Vec<Box<dyn Backend + 'a>>, String);

/// Backends on the device `runtime` asks for, `parallel` of them or as many
/// as memory allows, the device's description and its kind.
fn backend<'a>(
    model: &'a Model<'a>,
    path: &Path,
    runtime: &RuntimeArgs,
    context: usize,
    parallel: Option<usize>,
) -> Result<(Placed<'a>, Device)> {
    let picked = gpu::pick(runtime.device, |kind| match kind {
        Device::Cuda => cuda_backend(model, path, runtime, context, parallel),
        _ => vulkan_backend(model, path, runtime, context),
    })?;
    if let Some(gpu) = picked {
        return Ok(gpu);
    }
    let rad1 = !runtime.is_off(Tech::Rad1);
    let new = || match rad1 {
        true => CpuBackend::new(model),
        false => CpuBackend::new(model).without_drafts(),
    };
    let cpu = match warm_cache(model, path, runtime, None) {
        Some(w) => new().with_warm(w),
        None => new(),
    };
    let slots = parallel.unwrap_or_else(|| default_slots(model, context));
    // states grow as conversations do, so a context that cannot fit only fails much later
    let need = model.state_bytes(context) as u64 * slots as u64;
    if let Some(free) = kinetic_models::memory::available().filter(|&free| need > free) {
        eprintln!(
            "kinetic: {slots} full {context}-token conversations need {:.1} GiB, more than the {:.1} GiB free; lower -c or --parallel if long ones run out of memory",
            need as f64 / (1u64 << 30) as f64,
            free as f64 / (1u64 << 30) as f64
        );
    }
    let mut backends: Vec<Box<dyn Backend + 'a>> = vec![Box::new(cpu)];
    backends.extend((1..slots).map(|_| Box::new(new()) as Box<dyn Backend>));
    Ok(((backends, CPU.into()), Device::Cpu))
}

#[cfg(feature = "cuda")]
fn cuda_backend<'a>(
    model: &'a Model<'a>,
    path: &Path,
    runtime: &RuntimeArgs,
    context: usize,
    parallel: Option<usize>,
) -> Option<std::result::Result<Placed<'a>, kinetic_models::LoadError>> {
    let placement = kinetic_models::cuda::Placement {
        gpu_layers: runtime.gpu_layers,
        eager: runtime.is_off(Tech::Torque),
        cache_k: runtime.cache_type_k.into(),
        cache_v: runtime.cache_type_v.into(),
        ..kinetic_models::cuda::Placement::default()
    };
    let gpu = match kinetic_server::CudaBackend::with_placement(model, context, placement) {
        Ok(gpu) if runtime.is_off(Tech::Rad1) => gpu.without_drafts(),
        Ok(gpu) => gpu,
        Err(e) => return Some(Err(e)),
    };
    let name = gpu.device().to_owned();
    let mut slots: Vec<Box<dyn Backend + 'a>> = Vec::new();
    for _ in 1..parallel.unwrap_or(MAX_DEFAULT_SLOTS) {
        match gpu.slot() {
            Ok(slot) => slots.push(Box::new(slot)),
            Err(e) if parallel.is_some() => {
                let e = format!("--parallel {}: {e}", slots.len() + 2);
                return Some(Err(kinetic_models::LoadError(e)));
            }
            Err(_) => break,
        }
    }
    let gpu = match warm_cache(model, path, runtime, Some("cuda")) {
        Some(w) => gpu.with_warm(w),
        None => gpu,
    };
    slots.insert(0, Box::new(gpu));
    Some(Ok((slots, name)))
}

#[cfg(not(feature = "cuda"))]
fn cuda_backend<'a>(
    _model: &'a Model<'a>,
    _path: &Path,
    _runtime: &RuntimeArgs,
    _context: usize,
    _parallel: Option<usize>,
) -> Option<std::result::Result<Placed<'a>, kinetic_models::LoadError>> {
    None
}

#[cfg(feature = "vulkan")]
fn vulkan_backend<'a>(
    model: &'a Model<'a>,
    path: &Path,
    runtime: &RuntimeArgs,
    context: usize,
) -> Option<std::result::Result<Placed<'a>, kinetic_models::LoadError>> {
    Some(
        kinetic_server::VulkanBackend::new(model, context).map(|gpu| {
            let gpu = match runtime.is_off(Tech::Rad1) {
                true => gpu.without_drafts(),
                false => gpu,
            };
            let name = gpu.device().to_owned();
            let gpu = match warm_cache(model, path, runtime, Some("vulkan")) {
                Some(w) => gpu.with_warm(w),
                None => gpu,
            };
            (vec![Box::new(gpu) as Box<dyn Backend>], name)
        }),
    )
}

#[cfg(not(feature = "vulkan"))]
fn vulkan_backend<'a>(
    _model: &'a Model<'a>,
    _path: &Path,
    _runtime: &RuntimeArgs,
    _context: usize,
) -> Option<std::result::Result<Placed<'a>, kinetic_models::LoadError>> {
    None
}

/// The prompt cache `runtime` asks for, on disk where it can be, for states
/// made on the CPU or on `device`.
fn warm_cache<'a>(
    model: &'a Model<'a>,
    path: &Path,
    runtime: &RuntimeArgs,
    device: Option<&str>,
) -> Option<Warm<'a>> {
    // saved states belong to the weights without the adapters
    if runtime.is_off(Tech::WarmStart)
        || !runtime.lora.is_empty()
        || !runtime.lora_scaled.is_empty()
    {
        return None;
    }
    let id = warm::model_id(path).ok()?;
    let id = device.map_or(id, |d| warm::device_id(id, d));
    let Some(dir) = runtime.cache_dir.clone().or_else(warm::default_dir) else {
        return Some(Warm::new(model, id, WARM_MEMORY));
    };
    match Warm::new(model, id, WARM_MEMORY).with_disk(&dir, WARM_DISK) {
        Ok(w) => Some(w),
        Err(e) => {
            eprintln!(
                "kinetic: prompt cache in memory only, {} is not usable: {e}",
                dir.display()
            );
            Some(Warm::new(model, id, WARM_MEMORY))
        }
    }
}

/// Whether the file holds an encoder or a model that pools its states into
/// one vector, rather than one that generates text.
fn is_embedding_model(path: &Path) -> Result<bool> {
    let file = ModelFile::open(path)?;
    let header = file.source().header();
    let encoder = header
        .architecture()
        .is_some_and(kinetic_models::is_encoder);
    Ok(encoder || header.arch_key("pooling_type").is_some())
}

/// Reads the model file once in the background so the first answer does not
/// wait for the weights to come off the disk, when it fits easily in memory.
fn read_ahead(path: &Path) {
    let size = std::fs::metadata(path).map_or(u64::MAX, |m| m.len());
    if size > system::machine().ram_available / 2 {
        return;
    }
    let path = path.to_path_buf();
    std::thread::spawn(move || {
        use std::io::Read;
        let Ok(mut file) = std::fs::File::open(&path) else {
            return;
        };
        let mut buffer = vec![0u8; 16 << 20];
        while matches!(file.read(&mut buffer), Ok(n) if n > 0) {}
    });
}
