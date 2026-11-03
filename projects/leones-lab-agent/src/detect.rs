use std::env;
use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

/// Runtime launchers and supporting tools. Presence is not proof that a service
/// is running or that a particular model/backend is usable.
pub const TOOLS: &[&str] = &[
    "tensorfold-native",
    "llama-server", "llama-cli", "llama-bench",
    "ollama",
    "vllm",
    "strata", "strata-cli",
    "rustinstrata", "rust-instrata",
    "mistralrs", "hermes", "magnitude",
    "docker", "podman", "python3", "cargo", "rustc", "git",
];

#[derive(Debug, Clone, Copy)]
pub struct Engine {
    pub id: &'static str,
    pub executables: &'static [&'static str],
    pub api_default: Option<&'static str>,
}

pub const ENGINES: &[Engine] = &[
    Engine { id: "ollama", executables: &["ollama"], api_default: Some("http://127.0.0.1:11434") },
    Engine { id: "llama.cpp", executables: &["llama-server", "llama-cli", "llama-bench"], api_default: Some("http://127.0.0.1:8080") },
    Engine { id: "vllm", executables: &["vllm"], api_default: Some("http://127.0.0.1:8000") },
    Engine { id: "strata", executables: &["strata", "strata-cli"], api_default: None },
    Engine { id: "rustinstrata", executables: &["rustinstrata", "rust-instrata"], api_default: None },
    Engine { id: "tensorfold", executables: &["tensorfold-native"], api_default: None },
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
    let mut paths = vec![home.join(".local/bin").join(name), home.join(".cargo/bin").join(name)];
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

/// Consulta la ayuda del binario sin cargar modelos ni iniciar un servidor.
fn probe_tandem(path: &Path) -> String {
    let mut child = match Command::new(path).arg("--help")
        .stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn() {
        Ok(child) => child,
        Err(error) => return format!("UNKNOWN (no se pudo ejecutar --help: {error})"),
    };
    let deadline = Instant::now() + Duration::from_secs(2);
    let mut timed_out = false;
    loop {
        match child.try_wait() {
            Ok(Some(_)) => break,
            Ok(None) if Instant::now() < deadline => thread::sleep(Duration::from_millis(25)),
            Ok(None) => { timed_out = true; let _ = child.kill(); break; }
            Err(error) => {
                let _ = child.kill(); let _ = child.wait();
                return format!("UNKNOWN (falló la sonda: {error})");
            }
        }
    }
    let output = match child.wait_with_output() {
        Ok(output) => output,
        Err(error) => return format!("UNKNOWN (no se pudo recoger --help: {error})"),
    };
    if timed_out { return "UNKNOWN (timeout de 2 s al consultar --help)".to_string(); }
    let mut help = String::from_utf8_lossy(&output.stdout).into_owned();
    help.push_str(&String::from_utf8_lossy(&output.stderr));
    if help.contains("--moe-cache-mib") {
        "VERIFIED (llama-server --help anuncia --moe-cache-mib)".to_string()
    } else {
        "NOT DETECTED (la ayuda no anuncia --moe-cache-mib; puede ser llama.cpp base u otra build)".to_string()
    }
}

pub fn print_engines(args: &[String]) -> Result<(), String> {
    println!("LEONES LAB AGENT — DETECCIÓN DE MOTORES");
    for engine in ENGINES {
        let found = engine.executables.iter().find_map(|exe| find_executable(exe));
        match found {
            Some(path) => println!("[OK] {}: {} ({})", engine.id, path.display(),
                engine.api_default.unwrap_or("API/endpoint no autodeterminado")),
            None => println!("[--] {}: runtime no encontrado; no se infiere que esté instalado", engine.id),
        }
    }
    if args.iter().any(|arg| arg == "--probe") {
        match find_executable("llama-server") {
            Some(path) => println!("[tandem.cpp] {}: {}", path.display(), probe_tandem(&path)),
            None => println!("[tandem.cpp] UNKNOWN: no se encontró llama-server para consultar --help"),
        }
    } else {
        println!("[~] tandem.cpp: parche de llama.cpp, no runtime independiente; usa `lab-agent engines --probe` para consultar --moe-cache-mib en la ayuda de llama-server.");
    }
    println!("\nHerramientas auxiliares:");
    let mut found = 0usize;
    for tool in TOOLS {
        if let Some(path) = find_executable(tool) {
            println!("[OK] {tool}: {}", path.display());
            found += 1;
        }
    }
    println!("Detectadas: {found} herramientas de {} entradas.", TOOLS.len());
    println!("La detección no implica que un servidor esté activo ni que un modelo sea ejecutable.");
    Ok(())
}
