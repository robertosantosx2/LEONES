use std::env;
use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};

const TOOLS: &[&str] = &[
    "tensorfold-native", "llama-server", "llama-cli", "llama-bench",
    "mistralrs", "ollama", "vllm", "hermes", "docker", "podman",
    "python3", "cargo", "rustc", "git",
];

fn is_executable(path: &Path) -> bool {
    fs::metadata(path)
        .map(|meta| meta.is_file() && meta.permissions().mode() & 0o111 != 0)
        .unwrap_or(false)
}

fn find_executable(name: &str) -> Option<PathBuf> {
    for directory in env::split_paths(&env::var_os("PATH")?) {
        let candidate = directory.join(name);
        if is_executable(&candidate) {
            return Some(candidate);
        }
    }
    None
}

pub fn print_engines() -> Result<(), String> {
    println!("LEONES LAB AGENT — MOTORES Y HERRAMIENTAS");
    let mut found = 0usize;
    for tool in TOOLS {
        match find_executable(tool) {
            Some(path) => {
                println!("[OK] {tool}: {}", path.display());
                found += 1;
            }
            None => println!("[--] {tool}: no encontrado en PATH"),
        }
    }
    println!("Detectados: {found}/{}", TOOLS.len());
    println!("La detección no implica que un servidor esté activo.");
    Ok(())
}

fn home_dir() -> Option<PathBuf> {
    env::var_os("HOME").map(PathBuf::from)
}

pub fn local_model_dirs() -> Vec<PathBuf> {
    let Some(home) = home_dir() else { return Vec::new() };
    let hub = home.join(".cache/huggingface/hub");
    let Ok(entries) = fs::read_dir(hub) else { return Vec::new() };
    let mut models: Vec<PathBuf> = entries
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| path.is_dir() && path.file_name().and_then(|v| v.to_str()).map(|v| v.starts_with("models--")).unwrap_or(false))
        .collect();
    models.sort();
    models
}

pub fn print_models() -> Result<(), String> {
    println!("LEONES LAB AGENT — MODELOS LOCALES");
    let models = local_model_dirs();
    if models.is_empty() {
        println!("No se encontraron repositorios en ~/.cache/huggingface/hub.");
    } else {
        for model in &models {
            let name = model.file_name().and_then(|v| v.to_str()).unwrap_or("modelo");
            let repo = name.strip_prefix("models--").unwrap_or(name).replace("--", "/");
            let snapshots = model.join("snapshots");
            let count = fs::read_dir(snapshots)
                .map(|entries| entries.filter_map(Result::ok).filter(|e| e.path().is_dir()).count())
                .unwrap_or(0);
            println!("[LOCAL] {repo} — {count} snapshot(s)");
        }
    }
    println!("Solo se inspecciona la caché Hugging Face estándar; no se recorren discos completos.");
    Ok(())
}
