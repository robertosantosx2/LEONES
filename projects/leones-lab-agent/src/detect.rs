use std::env;
use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};

pub const TOOLS: &[&str] = &[
    "tensorfold-native", "llama-server", "llama-cli", "llama-bench",
    "mistralrs", "ollama", "vllm", "hermes", "magnitude", "docker",
    "podman", "python3", "cargo", "rustc", "git",
];

fn is_executable(path: &Path) -> bool {
    fs::metadata(path)
        .map(|meta| meta.is_file() && meta.permissions().mode() & 0o111 != 0)
        .unwrap_or(false)
}

fn known_candidates(name: &str) -> Vec<PathBuf> {
    let Some(home) = env::var_os("HOME").map(PathBuf::from) else {
        return Vec::new();
    };
    let mut paths = Vec::new();
    match name {
        "tensorfold-native" => {
            let root = home.join(".local/opt");
            if let Ok(entries) = fs::read_dir(root) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.file_name().and_then(|v| v.to_str())
                        .map(|v| v.starts_with("tensorfold-")).unwrap_or(false)
                    {
                        paths.push(path.join("bin/tensorfold-native"));
                    }
                }
            }
        }
        "llama-cli" | "llama-server" | "llama-bench" => {
            paths.push(home.join("llama-cpp-cuda/build-cuda/bin").join(name));
            paths.push(home.join("llama-cpp-cuda/build/bin").join(name));
        }
        "mistralrs" | "hermes" | "magnitude" => {
            paths.push(home.join(".local/bin").join(name));
        }
        _ => {}
    }
    paths
}

pub fn find_executable(name: &str) -> Option<PathBuf> {
    if let Some(path_var) = env::var_os("PATH") {
        for directory in env::split_paths(&path_var) {
            let candidate = directory.join(name);
            if is_executable(&candidate) {
                return Some(candidate);
            }
        }
    }
    known_candidates(name).into_iter().find(|path| is_executable(path))
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
            None => println!("[--] {tool}: no encontrado en PATH ni en rutas conocidas"),
        }
    }
    println!("Detectados: {found}/{}", TOOLS.len());
    println!("La detección no implica que un servidor esté activo.");
    Ok(())
}
