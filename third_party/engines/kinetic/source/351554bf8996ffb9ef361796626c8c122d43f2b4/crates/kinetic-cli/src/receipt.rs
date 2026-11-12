//! Receipts from the command line: what each run records about its device,
//! and `kinetic verify-receipt`, which reruns one.

use std::path::{Path, PathBuf};

use clap::ValueEnum;
use kinetic_server::receipt::{self, Device as ReceiptDevice, ModelFile};
use kinetic_server::{Engine, Prompt, Receipt, Receipts, Request};
use serde_json::{Map, Value};

use crate::tech::Tech;
use crate::{
    library, with_engine, CacheType, Device, OffArg, Result, RopeArgs, RopeKind, RuntimeArgs,
};

/// What receipts made with this engine record: the model at `path`, run on
/// `kind` (described as `name`) with `runtime` and `context`.
pub fn receipts(
    path: &Path,
    kind: Device,
    name: &str,
    runtime: &RuntimeArgs,
    context: usize,
) -> Result<Receipts> {
    let mut device = match kind {
        Device::Cuda => ReceiptDevice::new(cuda_class(), name),
        Device::Vulkan => ReceiptDevice::new(format!("vulkan-{name}"), name),
        _ => ReceiptDevice::cpu(),
    };
    device.settings = settings(kind, runtime, context);
    let receipts = Receipts::new(path, device);
    Ok(match &runtime.sign_key {
        Some(key) => receipts.signed_with(receipt::read_key(key)?),
        None => receipts,
    })
}

#[cfg(feature = "cuda")]
fn cuda_class() -> String {
    kinetic_cuda::Device::get(0)
        .and_then(|d| d.info())
        .map_or("cuda".into(), |i| {
            let (major, minor) = i.compute_capability;
            format!("cuda-sm{major}{minor}")
        })
}

#[cfg(not(feature = "cuda"))]
fn cuda_class() -> String {
    "cuda".into()
}

/// Load settings that change the bits, named as their flags.
fn settings(kind: Device, runtime: &RuntimeArgs, context: usize) -> Map<String, Value> {
    let mut s = Map::new();
    s.insert("ctx-size".into(), context.into());
    if kind == Device::Cuda {
        for (flag, t) in [
            ("cache-type-k", runtime.cache_type_k),
            ("cache-type-v", runtime.cache_type_v),
        ] {
            if t != CacheType::F16 {
                s.insert(flag.into(), flag_value(t));
            }
        }
    }
    if let Some(n) = runtime.gpu_layers {
        s.insert("gpu-layers".into(), n.into());
    }
    let rope = &runtime.rope;
    if let Some(k) = rope.rope_scaling {
        s.insert("rope-scaling".into(), flag_value(k));
    }
    let floats = [
        ("rope-scale", rope.rope_scale),
        ("rope-freq-scale", rope.rope_freq_scale),
        ("rope-freq-base", rope.rope_freq_base),
    ];
    for (flag, v) in floats.into_iter().filter_map(|(f, v)| Some((f, v?))) {
        s.insert(flag.into(), v.into());
    }
    if let Some(n) = rope.yarn_orig_ctx {
        s.insert("yarn-orig-ctx".into(), n.into());
    }
    let lora = runtime.lora.iter().map(|p| p.display().to_string());
    let lora: Vec<Value> = lora
        .chain(runtime.lora_scaled.iter().cloned())
        .map(Value::from)
        .collect();
    if !lora.is_empty() {
        s.insert("lora".into(), lora.into());
    }
    s
}

fn flag_value(v: impl ValueEnum) -> Value {
    v.to_possible_value()
        .map_or(Value::Null, |p| p.get_name().into())
}

/// The runtime that reruns a receipt alone: one request at a time, no
/// drafts, no prompt cache, with the load settings it records.
fn rerun_runtime(
    r: &Receipt,
    device: Option<Device>,
    threads: Option<usize>,
) -> Result<RuntimeArgs> {
    let s = &r.device.settings;
    if s.contains_key("lora") {
        return Err(
            "this answer was made with LoRA adapters, which verify-receipt cannot rerun yet".into(),
        );
    }
    let int = |flag: &str| s.get(flag).and_then(Value::as_u64).map(|n| n as usize);
    let float = |flag: &str| s.get(flag).and_then(Value::as_f64).map(|v| v as f32);
    let parse = |flag: &str| s.get(flag).and_then(Value::as_str).map(str::to_owned);
    let cache = |flag: &str| -> Result<CacheType> {
        parse(flag).map_or(Ok(CacheType::F16), |v| {
            CacheType::from_str(&v, true).map_err(|e| format!("{flag}: {e}").into())
        })
    };
    let class = &r.device.class;
    let device = device.unwrap_or(if class.starts_with("cuda") {
        Device::Cuda
    } else if class.starts_with("vulkan") {
        Device::Vulkan
    } else {
        Device::Cpu
    });
    Ok(RuntimeArgs {
        context: int("ctx-size"),
        threads,
        device,
        gpu_layers: int("gpu-layers"),
        cache_dir: None,
        no_prompt_cache: true,
        cache_type_k: cache("cache-type-k")?,
        cache_type_v: cache("cache-type-v")?,
        sign_key: None,
        mlock: false,
        no_mmap: false,
        chat_template_file: None,
        lora: Vec::new(),
        lora_scaled: Vec::new(),
        off: OffArg {
            off: vec![Tech::Rad1, Tech::WarmStart, Tech::ZeroWait, Tech::Convoy],
        },
        rope: RopeArgs {
            rope_scaling: parse("rope-scaling")
                .map(|v| RopeKind::from_str(&v, true))
                .transpose()?,
            rope_scale: float("rope-scale"),
            rope_freq_scale: float("rope-freq-scale"),
            rope_freq_base: float("rope-freq-base"),
            yarn_orig_ctx: int("yarn-orig-ctx"),
        },
    })
}

/// Writes the receipt for the last answer, `c` to `request` from `input`,
/// to `file`, or prints it.
pub fn save(
    engine: &Engine,
    input: Value,
    request: &Request,
    c: &kinetic_server::Completion,
    file: Option<&Path>,
) -> Result<()> {
    let receipts = engine.receipts().ok_or("this engine makes no receipts")?;
    let json = receipts.make(input, None, request, c)?.to_json();
    match file {
        Some(f) => std::fs::write(f, json).map_err(|e| format!("{}: {e}", f.display()).into()),
        None => {
            print!("{json}");
            Ok(())
        }
    }
}

/// `kinetic verify-receipt`: reruns the receipt in `file` alone, with the
/// model at `model` or where the receipt says, and reports whether every
/// output token matches.
pub fn verify(
    file: &Path,
    model: Option<PathBuf>,
    device: Option<Device>,
    threads: Option<usize>,
) -> Result<()> {
    let text = std::fs::read_to_string(file).map_err(|e| format!("{}: {e}", file.display()))?;
    let r = Receipt::parse(&text)?;
    println!(
        "receipt:   {}, {} prompt and {} output tokens, seed {}, made on {} by Kinetic {} (build {})",
        r.model.file,
        r.prompt.count,
        r.output.tokens.count,
        r.sampling.seed,
        r.device.class,
        r.kinetic.version,
        r.kinetic.build
    );
    match r.check()? {
        Some(key) => println!("signature: valid, public key {key}"),
        None => println!("signature: none; token hashes match"),
    }
    let path = model.unwrap_or_else(|| PathBuf::from(&r.model.path));
    let local = library::locate(&path)?;
    let here = ModelFile::read(&local.path)?;
    if here.blake3 != r.model.blake3 {
        return Err(format!(
            "{} is not the receipt's model file: BLAKE3 {} here, {} in the receipt",
            local.path.display(),
            here.blake3,
            r.model.blake3
        )
        .into());
    }
    println!(
        "model:     {} matches (BLAKE3 {})",
        local.path.display(),
        &here.blake3[..16]
    );
    let runtime = rerun_runtime(&r, device, threads)?;
    with_engine(&local, None, &runtime, Some(1), |engine, _, _| {
        let request = r.request()?;
        let c = engine.complete_tokens(
            r.prompt.ids.clone(),
            &Prompt::raw(""),
            &request,
            None,
            &mut |_, _| true,
        )?;
        let receipts = engine.receipts().ok_or("this engine makes no receipts")?;
        let rerun = receipts.make(r.input.clone(), r.sampling.constraint.clone(), &request, &c)?;
        report(engine, &r, &rerun)
    })
}

fn report(engine: &Engine, r: &Receipt, rerun: &Receipt) -> Result<()> {
    let cmp = r.compare(rerun);
    let Some((at, want, got)) = cmp.first_difference else {
        println!(
            "rerun:     identical, {} of {} output tokens on {} (BLAKE3 {})",
            rerun.output.tokens.count,
            r.output.tokens.count,
            rerun.device.class,
            &rerun.output.tokens.blake3[..16]
        );
        for reason in &cmp.reasons {
            println!("note:      {reason}");
        }
        return Ok(());
    };
    let token = |t: Option<u32>| match t {
        Some(id) => format!(
            "{id} {:?}",
            String::from_utf8_lossy(engine.tokenizer().piece(id))
        ),
        None => "nothing (the output ended)".into(),
    };
    println!(
        "rerun:     differs at output token {at}: the receipt has {}, the rerun {}",
        token(want),
        token(got)
    );
    if cmp.reasons.is_empty() && r.signature.is_some() {
        println!(
            "why:       same build, device class and settings, so this is a bug; please report it"
        );
    } else if cmp.reasons.is_empty() {
        println!("why:       same build, device class and settings: the unsigned receipt was edited, or this is a bug");
    }
    for reason in &cmp.reasons {
        println!("why:       {reason}");
    }
    Err("the rerun does not match the receipt".into())
}
