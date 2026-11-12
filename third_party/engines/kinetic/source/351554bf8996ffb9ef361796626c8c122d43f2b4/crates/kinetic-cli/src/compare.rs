//! `kinetic bench --compare`: Kinetic and llama.cpp on the same file with
//! the same settings, summed up in a card to share.
//!
//! Each engine runs in its own process, one after the other, so only one
//! copy of the model is in memory at a time. llama.cpp's prompt and
//! generation numbers come from llama-bench; its edit number from
//! llama-server with the speculative mode that suits the model.

mod card;
mod llama;

use std::path::{Path, PathBuf};
use std::process::Command;

use serde_json::Value;

use crate::library::Local;
use crate::{system, Device, Result};

/// The settings both engines run with.
pub struct Settings {
    pub device: Device,
    pub threads: usize,
    pub repetitions: usize,
}

/// One engine's best speeds, in tokens per second.
#[derive(Debug, Default)]
pub struct Speeds {
    pub prompt: f64,
    pub generate: f64,
    pub edit: Option<f64>,
}

/// Runs both engines on `model` and prints the card.
pub fn run(model: &Local, llama_bench: &Path, settings: &Settings, as_json: bool) -> Result<()> {
    let bench = llama::find(llama_bench)?;
    eprintln!("kinetic: measuring Kinetic");
    let kinetic = kinetic(&model.path, settings)?;
    let on_gpu = kinetic["backend"] != "cpu";
    eprintln!("kinetic: measuring llama.cpp ({})", bench.display());
    let llama = llama::measure(&bench, &model.path, on_gpu, settings)?;
    let card = card::Card {
        model,
        settings,
        machine: system::machine(),
        kinetic_device: kinetic["device"].as_str().unwrap_or("?").to_owned(),
        on_gpu,
        kinetic: Speeds {
            prompt: number(&kinetic["prefill_tokens_per_second"])?,
            generate: number(&kinetic["decode_tokens_per_second"])?,
            edit: kinetic["edit_tokens_per_second"].as_f64(),
        },
        edit_identical: kinetic["edit_identical"].as_bool().unwrap_or(false),
        llama,
    };
    if as_json {
        println!("{:#}", card.json());
    } else {
        print!("{}", card.text());
    }
    Ok(())
}

/// `kinetic bench --json` on the same binary, in its own process.
fn kinetic(path: &Path, s: &Settings) -> Result<Value> {
    let device = match s.device {
        Device::Auto => "auto",
        Device::Cpu => "cpu",
        Device::Cuda => "cuda",
        Device::Vulkan => "vulkan",
    };
    let out = Command::new(std::env::current_exe()?)
        .arg("bench")
        .arg(path)
        .args(["--json", "--device", device])
        .args([
            "-t",
            &s.threads.to_string(),
            "-r",
            &s.repetitions.to_string(),
        ])
        .output()?;
    if !out.status.success() {
        return Err(format!(
            "kinetic bench failed: {}",
            String::from_utf8_lossy(&out.stderr).trim()
        )
        .into());
    }
    Ok(serde_json::from_slice(&out.stdout)?)
}

fn number(v: &Value) -> Result<f64> {
    v.as_f64()
        .ok_or_else(|| "kinetic bench reported no speed".into())
}

/// Where `name` may be on this computer, beyond `PATH`.
fn install_dirs() -> Vec<PathBuf> {
    let var = |k: &str| std::env::var_os(k).map(PathBuf::from);
    let mut dirs = Vec::new();
    if let Some(home) = std::env::home_dir() {
        for sub in [
            "llama.cpp/build/bin/Release",
            "llama.cpp/build/bin",
            "llama.cpp",
            ".local/bin",
        ] {
            dirs.push(home.join(sub));
        }
    }
    if cfg!(windows) {
        if let Some(local) = var("LOCALAPPDATA") {
            let winget = local.join("Microsoft").join("WinGet");
            dirs.push(winget.join("Links"));
            // winget unpacks llama.cpp into Packages\ggml.llamacpp_<source id>
            if let Ok(read) = std::fs::read_dir(winget.join("Packages")) {
                dirs.extend(
                    read.flatten()
                        .filter(|e| e.file_name().to_string_lossy().starts_with("ggml.llamacpp"))
                        .map(|e| e.path()),
                );
            }
        }
        dirs.push(PathBuf::from(r"C:\llama.cpp"));
    } else {
        for d in [
            "/usr/local/bin",
            "/usr/bin",
            "/opt/llama.cpp/bin",
            "/home/linuxbrew/.linuxbrew/bin",
        ] {
            dirs.push(PathBuf::from(d));
        }
    }
    dirs
}
