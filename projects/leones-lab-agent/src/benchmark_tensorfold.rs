use crate::detect;
use crate::hash;
use crate::output::json::{self, Value};
use std::collections::BTreeMap;
use std::env;
use std::fs::{self, File};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

const MAX_TOKENS: u32 = 4096;
const MAX_REPETITIONS: u32 = 5;
const MAX_TIMEOUT_SECONDS: u64 = 1800;

#[derive(Debug)]
struct Config {
    model: String,
    tokens: u32,
    repetitions: u32,
    timeout_seconds: u64,
    output: Option<PathBuf>,
    approved: bool,
}

fn string(value: &str) -> Value {
    Value::String(value.to_string())
}

fn object(entries: &[(&str, Value)]) -> Value {
    let mut map = BTreeMap::new();
    for (key, value) in entries {
        map.insert((*key).to_string(), (*value).clone());
    }
    Value::Object(map)
}

fn parse_number(flag: &str, raw: Option<&String>, default: u32, max: u32) -> Result<u32, String> {
    let Some(raw) = raw else { return Ok(default) };
    let value = raw.parse::<u32>().map_err(|_| format!("{flag} debe ser un entero."))?;
    if value == 0 || value > max {
        return Err(format!("{flag} debe estar entre 1 y {max}."));
    }
    Ok(value)
}

fn parse_timeout(raw: Option<&String>) -> Result<u64, String> {
    let Some(raw) = raw else { return Ok(900) };
    let value = raw.parse::<u64>().map_err(|_| "--timeout debe ser un entero.".to_string())?;
    if !(30..=MAX_TIMEOUT_SECONDS).contains(&value) {
        return Err(format!("--timeout debe estar entre 30 y {MAX_TIMEOUT_SECONDS} segundos."));
    }
    Ok(value)
}

fn valid_model_reference(model: &str) -> bool {
    if model.is_empty() || model.len() > 512 || model.starts_with('-') {
        return false;
    }
    if model.chars().any(|ch| ch.is_control() || ch.is_whitespace()) {
        return false;
    }
    // Accept HF-style owner/repository IDs or local directory paths.
    let parts: Vec<&str> = model.split('/').collect();
    if model.starts_with('/') || model.starts_with("./") || model.starts_with("../") {
        return true;
    }
    parts.len() == 2 && parts.iter().all(|part| {
        !part.is_empty()
            && !part.starts_with('.')
            && part.bytes().all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'_' | b'.'))
    })
        && !model.contains("..")
}

fn parse_args(args: &[String]) -> Result<Config, String> {
    let mut model = None;
    let mut tokens = None;
    let mut repetitions = None;
    let mut timeout = None;
    let mut output = None;
    let mut approved = false;
    let mut index = 0usize;
    while index < args.len() {
        let flag = args[index].as_str();
        match flag {
            "--approve" => approved = true,
            "--model" | "--tokens" | "--reps" | "--timeout" | "--output" => {
                index += 1;
                let raw = args.get(index).ok_or_else(|| format!("{flag} necesita un valor."))?;
                match flag {
                    "--model" => model = Some(raw.clone()),
                    "--tokens" => tokens = Some(raw.clone()),
                    "--reps" => repetitions = Some(raw.clone()),
                    "--timeout" => timeout = Some(raw.clone()),
                    "--output" => output = Some(PathBuf::from(raw)),
                    _ => unreachable!(),
                }
            }
            "--help" | "-h" => return Err(help_text().to_string()),
            other => return Err(format!("Opción no permitida: {other}. No se aceptan argumentos arbitrarios.")),
        }
        index += 1;
    }
    let model = model.ok_or_else(|| "Falta --model REPO_HF o directorio local.".to_string())?;
    if !valid_model_reference(&model) {
        return Err("Referencia de modelo no válida. Usa owner/repo de Hugging Face o una ruta local.".to_string());
    }
    Ok(Config {
        model,
        tokens: parse_number("--tokens", tokens.as_ref(), 256, MAX_TOKENS)?,
        repetitions: parse_number("--reps", repetitions.as_ref(), 3, MAX_REPETITIONS)?,
        timeout_seconds: parse_timeout(timeout.as_ref())?,
        output,
        approved,
    })
}

fn help_text() -> &'static str {
    "Uso: lab-agent benchmark-tensorfold --model owner/repo [OPCIONES]\n\
     \n\
     Opciones:\n\
       --tokens N      Tokens de salida (1..4096, por defecto 256)\n\
       --reps N        Repeticiones (1..5, por defecto 3)\n\
       --timeout N     Timeout en segundos (30..1800, por defecto 900)\n\
       --output DIR    Directorio nuevo para guardar recibo y manifiesto\n\
       --approve       Autoriza ejecución; sin esto solo muestra el plan\n\
     \n\
     Ejecuta exclusivamente tensorfold-native benchmark. No descarga modelos,\n\
     no publica recibos y no usa shell. El modelo debe estar ya disponible localmente."
}

fn args_for(config: &Config, receipt: &Path) -> Vec<String> {
    vec![
        "benchmark".to_string(),
        config.model.clone(),
        "--output".to_string(),
        receipt.display().to_string(),
        "--reps".to_string(),
        config.repetitions.to_string(),
        "--tokens".to_string(),
        config.tokens.to_string(),
        "--temperatures".to_string(),
        "0".to_string(),
    ]
}

fn display_command(program: &Path, args: &[String]) -> String {
    std::iter::once(program.display().to_string())
        .chain(args.iter().map(|arg| format!("{arg:?}")))
        .collect::<Vec<_>>()
        .join(" ")
}

fn default_dir() -> PathBuf {
    let stamp = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0);
    PathBuf::from(format!("experiments/lab-agent-tensorfold-{stamp}"))
}

fn write_manifest(
    dir: &Path,
    config: &Config,
    executable: &Path,
    args: &[String],
    state: &str,
    started_unix_ns: u128,
    elapsed_ms: u128,
    exit_code: Option<i32>,
    receipt_sha256: Option<&str>,
    error: Option<&str>,
) -> Result<(), String> {
    let result = object(&[
        ("schema_version", Value::Number("1".to_string())),
        ("engine", string("tensorfold-native")),
        ("engine_version", Value::Null),
        ("model_reference", string(&config.model)),
        ("tokens", Value::Number(config.tokens.to_string())),
        ("repetitions", Value::Number(config.repetitions.to_string())),
        ("temperatures", Value::Array(vec![Value::Number("0".to_string())])),
        ("timeout_seconds", Value::Number(config.timeout_seconds.to_string())),
        ("timestamp_unix_ns", Value::Number(started_unix_ns.to_string())),
        ("elapsed_ms", Value::Number(elapsed_ms.to_string())),
        ("executable", string(&executable.display().to_string())),
        ("arguments", Value::Array(args.iter().map(|arg| string(arg)).collect())),
        ("state", string(state)),
        ("exit_code", exit_code.map(|v| Value::Number(v.to_string())).unwrap_or(Value::Null)),
        ("receipt_file", string("tensorfold-receipt.json")),
        ("receipt_sha256", receipt_sha256.map(string).unwrap_or(Value::Null)),
        ("error", error.map(string).unwrap_or(Value::Null)),
    ]);
    fs::write(dir.join("manifest.json"), json::stringify(&result))
        .map_err(|e| format!("No se pudo guardar manifest.json: {e}"))
}

pub fn run(args: &[String]) -> Result<(), String> {
    if args.iter().any(|arg| arg == "--help" || arg == "-h") {
        println!("{}", help_text());
        return Ok(());
    }
    let config = parse_args(args)?;
    let executable = detect::find_executable("tensorfold-native")
        .ok_or_else(|| "No se encuentra tensorfold-native en PATH ni en ~/.local/opt/tensorfold-*/bin.".to_string())?;
    let directory = config.output.clone().unwrap_or_else(default_dir);
    if directory.exists() {
        return Err(format!("El directorio de evidencia ya existe; no se sobrescribirá: {}", directory.display()));
    }
    let receipt = directory.join("tensorfold-receipt.json");
    let args = args_for(&config, &receipt);
    println!("Plan TensorFold (sin shell):");
    println!("{}", display_command(&executable, &args));
    println!("Modelo: {}; tokens: {}; repeticiones: {}; temperaturas: greedy (0)", config.model, config.tokens, config.repetitions);
    println!("Se presupone que el checkpoint ya está descargado/caché. No se publicará el recibo.");
    if !config.approved {
        println!("DRY RUN: no se ha ejecutado nada. Añade --approve para autorizar.");
        return Ok(());
    }

    fs::create_dir_all(&directory).map_err(|e| format!("No se pudo crear evidencia: {e}"))?;
    let stdout_path = directory.join("stdout.log");
    let stderr_path = directory.join("stderr.log");
    let stdout = File::create(&stdout_path).map_err(|e| format!("No se pudo crear stdout.log: {e}"))?;
    let stderr = File::create(&stderr_path).map_err(|e| format!("No se pudo crear stderr.log: {e}"))?;

    let started_unix_ns = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0);
    let started = Instant::now();
    let mut command = Command::new(&executable);
    command.args(&args).env_clear();
    for key in ["PATH", "HOME", "LD_LIBRARY_PATH", "CUDA_VISIBLE_DEVICES", "CUDA_HOME", "OMP_NUM_THREADS"] {
        if let Some(value) = env::var_os(key) {
            command.env(key, value);
        }
    }
    let mut child = command.stdin(Stdio::null()).stdout(Stdio::from(stdout)).stderr(Stdio::from(stderr))
        .spawn().map_err(|e| format!("No se pudo iniciar TensorFold: {e}"))?;

    let mut timed_out = false;
    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) if started.elapsed() >= Duration::from_secs(config.timeout_seconds) => {
                timed_out = true;
                let _ = child.kill();
                break child.wait().map_err(|e| format!("No se pudo recoger TensorFold tras timeout: {e}"))?;
            }
            Ok(None) => thread::sleep(Duration::from_millis(250)),
            Err(error) => {
                let _ = child.kill();
                let _ = child.wait();
                return Err(format!("Error supervisando TensorFold: {error}"));
            }
        }
    };
    let elapsed_ms = started.elapsed().as_millis();
    let receipt_sha = if receipt.is_file() {
        hash::sha256_file(&receipt).ok()
    } else {
        None
    };
    let state = if timed_out {
        "TIMEOUT"
    } else if status.success() && receipt_sha.is_some() {
        "RECEIPT_SAVED_UNVERIFIED"
    } else if status.success() {
        "RUN_COMPLETED_NO_RECEIPT"
    } else {
        "FAILED"
    };
    let error = match state {
        "TIMEOUT" => Some("TensorFold excedió el timeout; se conserva evidencia parcial."),
        "RUN_COMPLETED_NO_RECEIPT" => Some("TensorFold terminó sin crear el recibo esperado."),
        "FAILED" => Some("TensorFold terminó con error; consulta stderr.log."),
        _ => None,
    };
    write_manifest(
        &directory, &config, &executable, &args, state, started_unix_ns,
        elapsed_ms, status.code(), receipt_sha.as_deref(), error,
    )?;
    println!("Estado: {state}");
    println!("Evidencia: {}", directory.display());
    if timed_out {
        return Err("TensorFold cancelado por timeout; evidencia parcial conservada.".to_string());
    }
    if !status.success() {
        return Err(format!("TensorFold terminó con código {:?}; consulta stderr.log.", status.code()));
    }
    if receipt_sha.is_none() {
        return Err("No se encontró el recibo; consulta stdout.log y stderr.log.".to_string());
    }
    println!("Recibo TensorFold guardado (no clasificado MEASURED hasta validar esquema y protocolo).");
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{args_for, parse_args, valid_model_reference};
    use std::path::Path;

    #[test]
    fn defaults_are_conservative_and_dry() {
        let config = parse_args(&["--model".into(), "owner/model".into()]).unwrap();
        assert_eq!(config.tokens, 256);
        assert_eq!(config.repetitions, 3);
        assert_eq!(config.timeout_seconds, 900);
        assert!(!config.approved);
    }

    #[test]
    fn rejects_unbounded_or_unknown_options() {
        assert!(parse_args(&["--model".into(), "owner/model".into(), "--reps".into(), "99".into()]).is_err());
        assert!(parse_args(&["--model".into(), "owner/model".into(), "--shell".into()]).is_err());
    }

    #[test]
    fn rejects_remote_command_injection_as_model_id() {
        for bad in ["--help", "owner/model;rm", "owner/model@revision", "owner/model\nx", "https://example.com/x"] {
            assert!(!valid_model_reference(bad), "accepted: {bad}");
        }
    }

    #[test]
    fn builds_fixed_allowlisted_argv() {
        let config = parse_args(&["--model".into(), "owner/model".into(), "--tokens".into(), "64".into()]).unwrap();
        let args = args_for(&config, Path::new("receipt.json"));
        assert_eq!(args, vec![
            "benchmark", "owner/model", "--output", "receipt.json",
            "--reps", "3", "--tokens", "64", "--temperatures", "0",
        ]);
    }

    #[test]
    fn approval_is_opt_in() {
        let config = parse_args(&["--model".into(), "owner/model".into(), "--approve".into()]).unwrap();
        assert!(config.approved);
    }
}
