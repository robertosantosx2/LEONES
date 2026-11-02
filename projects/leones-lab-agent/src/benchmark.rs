use crate::detect;
use crate::output::json::{self, Value};
use std::collections::BTreeMap;
use std::fs::{self, File};
use std::io::Read;
use std::env;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

const MAX_PROMPT_TOKENS: u32 = 4096;
const MAX_GENERATION_TOKENS: u32 = 4096;
const MAX_REPETITIONS: u32 = 5;
const MAX_TIMEOUT_SECONDS: u64 = 1800;

#[derive(Debug)]
struct Config {
    model: PathBuf,
    prompt_tokens: u32,
    generation_tokens: u32,
    repetitions: u32,
    timeout_seconds: u64,
    output: Option<PathBuf>,
    approved: bool,
}

fn value_string(value: &str) -> Value {
    Value::String(value.to_string())
}

fn object(entries: &[(&str, Value)]) -> Value {
    let mut map = BTreeMap::new();
    for (key, value) in entries {
        map.insert((*key).to_string(), (*value).clone());
    }
    Value::Object(map)
}

fn parse_u32(flag: &str, raw: Option<&String>, default: u32, max: u32) -> Result<u32, String> {
    let Some(raw) = raw else { return Ok(default) };
    let value = raw.parse::<u32>().map_err(|_| format!("{flag} debe ser un entero."))?;
    if value == 0 || value > max {
        return Err(format!("{flag} debe estar entre 1 y {max}."));
    }
    Ok(value)
}

fn parse_u64(flag: &str, raw: Option<&String>, default: u64, max: u64) -> Result<u64, String> {
    let Some(raw) = raw else { return Ok(default) };
    let value = raw.parse::<u64>().map_err(|_| format!("{flag} debe ser un entero."))?;
    if !(30..=max).contains(&value) {
        return Err(format!("{flag} debe estar entre 30 y {max} segundos."));
    }
    Ok(value)
}

fn parse_args(args: &[String]) -> Result<Config, String> {
    let mut model = None;
    let mut prompt = None;
    let mut generation = None;
    let mut repetitions = None;
    let mut timeout = None;
    let mut output = None;
    let mut approved = false;
    let mut index = 0usize;
    while index < args.len() {
        let flag = args[index].as_str();
        match flag {
            "--approve" => approved = true,
            "--model" | "--prompt-tokens" | "--gen-tokens" | "--repetitions" | "--timeout" | "--output" => {
                index += 1;
                let raw = args.get(index).ok_or_else(|| format!("{flag} necesita un valor."))?;
                match flag {
                    "--model" => model = Some(PathBuf::from(raw)),
                    "--prompt-tokens" => prompt = Some(raw.clone()),
                    "--gen-tokens" => generation = Some(raw.clone()),
                    "--repetitions" => repetitions = Some(raw.clone()),
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

    let model = model.ok_or_else(|| "Falta --model RUTA.gguf.".to_string())?;
    let prompt_tokens = parse_u32("--prompt-tokens", prompt.as_ref(), 512, MAX_PROMPT_TOKENS)?;
    let generation_tokens = parse_u32("--gen-tokens", generation.as_ref(), 128, MAX_GENERATION_TOKENS)?;
    let repetitions = parse_u32("--repetitions", repetitions.as_ref(), 3, MAX_REPETITIONS)?;
    let timeout_seconds = parse_u64("--timeout", timeout.as_ref(), 900, MAX_TIMEOUT_SECONDS)?;

    Ok(Config {
        model,
        prompt_tokens,
        generation_tokens,
        repetitions,
        timeout_seconds,
        output,
        approved,
    })
}

fn help_text() -> &'static str {
    "Uso: lab-agent benchmark --model RUTA.gguf [OPCIONES]\n\
     \n\
     Opciones:\n\
       --prompt-tokens N   Tokens de prompt (1..4096, por defecto 512)\n\
       --gen-tokens N      Tokens de generación (1..4096, por defecto 128)\n\
       --repetitions N     Repeticiones (1..5, por defecto 3)\n\
       --timeout N         Timeout en segundos (30..1800, por defecto 900)\n\
       --output DIR        Directorio nuevo para evidencias\n\
       --approve           Autoriza ejecutar el benchmark; sin esto solo muestra el plan\n\
     \n\
     Solo ejecuta llama-bench con argumentos construidos por el agente. No usa shell."
}

fn has_gguf_magic(path: &Path) -> Result<bool, String> {
    let mut file = File::open(path).map_err(|e| format!("No se puede abrir el modelo: {e}"))?;
    let mut magic = [0u8; 4];
    file.read_exact(&mut magic).map_err(|e| format!("No se puede leer la cabecera GGUF: {e}"))?;
    Ok(&magic == b"GGUF")
}

fn command_args(config: &Config, model: &Path) -> Vec<String> {
    vec![
        "-m".to_string(), model.display().to_string(),
        "-p".to_string(), config.prompt_tokens.to_string(),
        "-n".to_string(), config.generation_tokens.to_string(),
        "-r".to_string(), config.repetitions.to_string(),
        "-o".to_string(), "json".to_string(),
    ]
}

fn display_command(program: &Path, args: &[String]) -> String {
    std::iter::once(program.display().to_string())
        .chain(args.iter().map(|arg| format!("{:?}", arg)))
        .collect::<Vec<_>>()
        .join(" ")
}

fn output_directory(config: &Config) -> PathBuf {
    config.output.clone().unwrap_or_else(|| {
        let now = SystemTime::now().duration_since(UNIX_EPOCH)
            .map(|d| d.as_nanos()).unwrap_or(0);
        PathBuf::from(format!("experiments/lab-agent-bench-{now}"))
    })
}

fn measured_results(value: &Value) -> bool {
    let Some(rows) = value.as_array() else { return false };
    !rows.is_empty() && rows.iter().all(|row| {
        let avg = row.get("avg_ts").and_then(|v| match v {
            Value::Number(number) => number.parse::<f64>().ok(),
            _ => None,
        });
        let deviation = row.get("stddev_ts").and_then(|v| match v {
            Value::Number(number) => number.parse::<f64>().ok(),
            _ => None,
        });
        let has_identity = row.get("model_filename").and_then(Value::as_str).is_some()
            && row.get("backends").and_then(Value::as_str).is_some()
            && row.get("test_time").and_then(Value::as_str).is_some();
        matches!(avg, Some(value) if value.is_finite() && value > 0.0)
            && matches!(deviation, Some(value) if value.is_finite() && value >= 0.0)
            && has_identity
    })
}

fn write_manifest(
    directory: &Path,
    state: &str,
    model: &Path,
    model_bytes: u64,
    model_sha256: &str,
    config: &Config,
    args: &[String],
    elapsed_ms: u128,
    exit_code: Option<i32>,
    results: Option<Value>,
    parse_error: Option<&str>,
) -> Result<(), String> {
    let command = Value::Array(args.iter().map(|arg| value_string(arg)).collect());
    let result = object(&[
        ("schema_version", Value::Number("1".to_string())),
        ("state", value_string(state)),
        ("engine", value_string("llama-bench")),
        ("model_path", value_string(&model.display().to_string())),
        ("model_bytes", Value::Number(model_bytes.to_string())),
        ("model_sha256", value_string(model_sha256)),
        ("prompt_tokens", Value::Number(config.prompt_tokens.to_string())),
        ("generation_tokens", Value::Number(config.generation_tokens.to_string())),
        ("repetitions", Value::Number(config.repetitions.to_string())),
        ("timeout_seconds", Value::Number(config.timeout_seconds.to_string())),
        ("timestamp_unix_ns", Value::Number(SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0).to_string())),
        ("elapsed_ms", Value::Number(elapsed_ms.to_string())),
        ("exit_code", exit_code.map(|v| Value::Number(v.to_string())).unwrap_or(Value::Null)),
        ("arguments", command),
        ("results", results.unwrap_or(Value::Null)),
        ("parse_error", parse_error.map(value_string).unwrap_or(Value::Null)),
        ("stdout_file", value_string("stdout.json")),
        ("stderr_file", value_string("stderr.log")),
    ]);
    fs::write(directory.join("manifest.json"), json::stringify(&result))
        .map_err(|e| format!("No se pudo guardar manifest.json: {e}"))
}

pub fn run(args: &[String]) -> Result<(), String> {
    if args.iter().any(|arg| arg == "--help" || arg == "-h") {
        println!("{}", help_text());
        return Ok(());
    }
    let config = parse_args(args)?;
    let model = config.model.canonicalize()
        .map_err(|e| format!("No se puede abrir el modelo {}: {e}", config.model.display()))?;
    if !model.is_file() {
        return Err("La ruta del modelo no es un fichero.".to_string());
    }
    if model.extension().and_then(|v| v.to_str()).map(|v| v.eq_ignore_ascii_case("gguf")) != Some(true) {
        return Err("Este runner solo admite modelos GGUF.".to_string());
    }
    if !has_gguf_magic(&model)? {
        return Err("La cabecera del fichero no es GGUF; se cancela el benchmark.".to_string());
    }
    let model_bytes = fs::metadata(&model).map_err(|e| format!("No se puede leer el modelo: {e}"))?.len();
    if model_bytes == 0 {
        return Err("El fichero GGUF está vacío.".to_string());
    }
    let executable = detect::find_executable("llama-bench")
        .ok_or_else(|| "No se encuentra llama-bench en PATH ni en las rutas conocidas.".to_string())?;
    let args = command_args(&config, &model);
    println!("Plan de benchmark (sin shell):");
    println!("{}", display_command(&executable, &args));
    println!("Modelo: {} bytes", model_bytes);
    println!("Timeout: {} s; repeticiones: {}", config.timeout_seconds, config.repetitions);

    if !config.approved {
        println!("DRY RUN: no se ha ejecutado nada. Añade --approve para autorizar este benchmark.");
        return Ok(());
    }

    let model_sha256 = crate::hash::sha256_file(&model)?;
    let directory = output_directory(&config);
    if directory.exists() {
        return Err(format!("El directorio de evidencia ya existe; no se sobrescribirá: {}", directory.display()));
    }
    fs::create_dir_all(&directory)
        .map_err(|e| format!("No se pudo crear {}: {e}", directory.display()))?;
    let stdout_file = File::create(directory.join("stdout.json"))
        .map_err(|e| format!("No se pudo crear stdout.json: {e}"))?;
    let stderr_file = File::create(directory.join("stderr.log"))
        .map_err(|e| format!("No se pudo crear stderr.log: {e}"))?;

    let started = Instant::now();
    let mut command = Command::new(&executable);
    command.args(&args).env_clear();
    for key in ["PATH", "HOME", "LD_LIBRARY_PATH", "CUDA_VISIBLE_DEVICES", "CUDA_HOME", "OMP_NUM_THREADS"] {
        if let Some(value) = env::var_os(key) {
            command.env(key, value);
        }
    }
    let mut child = command
        .stdin(Stdio::null())
        .stdout(Stdio::from(stdout_file))
        .stderr(Stdio::from(stderr_file))
        .spawn()
        .map_err(|e| format!("No se pudo iniciar llama-bench: {e}"))?;

    let mut timed_out = false;
    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) if started.elapsed() >= Duration::from_secs(config.timeout_seconds) => {
                timed_out = true;
                let _ = child.kill();
                break child.wait().map_err(|e| format!("No se pudo recoger el proceso tras timeout: {e}"))?;
            }
            Ok(None) => thread::sleep(Duration::from_millis(250)),
            Err(error) => {
                let _ = child.kill();
                let _ = child.wait();
                return Err(format!("Error supervisando llama-bench: {error}"));
            }
        }
    };
    let elapsed_ms = started.elapsed().as_millis();
    let mut stdout = String::new();
    File::open(directory.join("stdout.json"))
        .and_then(|mut file| file.read_to_string(&mut stdout))
        .map_err(|e| format!("No se pudo leer stdout.json: {e}"))?;

    let parsed = json::parse(&stdout).ok();
    let has_results = parsed.as_ref().map(measured_results).unwrap_or(false);
    let parse_error = if has_results {
        None
    } else {
        Some("stdout no contiene resultados JSON con avg_ts, stddev_ts e identidad del modelo")
    };
    let state = if timed_out {
        "TIMEOUT"
    } else if status.success() && has_results {
        "MEASURED"
    } else if status.success() {
        "RUN_COMPLETED_UNPARSED"
    } else {
        "FAILED"
    };
    write_manifest(
        &directory,
        state,
        &model,
        model_bytes,
        &model_sha256,
        &config,
        &args,
        elapsed_ms,
        status.code(),
        if has_results { parsed } else { None },
        parse_error,
    )?;

    println!("Estado: {state}");
    println!("Evidencia: {}", directory.display());
    if timed_out {
        return Err("Benchmark cancelado por timeout; se ha conservado la evidencia parcial.".to_string());
    }
    if !status.success() {
        return Err(format!("llama-bench terminó con código {:?}; consulta stderr.log.", status.code()));
    }
    if !has_results {
        return Err("El proceso terminó, pero no se pudieron validar métricas JSON; consulta stdout.json y stderr.log.".to_string());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{parse_args, Config};
    use std::path::PathBuf;

    #[test]
    fn defaults_are_bounded_and_dry_run() {
        let args = vec!["--model".to_string(), "model.gguf".to_string()];
        let config = parse_args(&args).unwrap();
        assert_eq!(config.prompt_tokens, 512);
        assert_eq!(config.generation_tokens, 128);
        assert_eq!(config.repetitions, 3);
        assert_eq!(config.timeout_seconds, 900);
        assert!(!config.approved);
        assert_eq!(config.model, PathBuf::from("model.gguf"));
    }

    #[test]
    fn rejects_unknown_flags() {
        let args = vec!["--model".to_string(), "model.gguf".to_string(), "--shell".to_string()];
        assert!(parse_args(&args).is_err());
    }

    #[test]
    fn rejects_unbounded_values() {
        let args = vec![
            "--model".to_string(), "model.gguf".to_string(),
            "--repetitions".to_string(), "99".to_string(),
        ];
        assert!(parse_args(&args).is_err());
    }

    #[test]
    fn approval_is_opt_in() {
        let args = vec!["--model".to_string(), "model.gguf".to_string(), "--approve".to_string()];
        let config: Config = parse_args(&args).unwrap();
        assert!(config.approved);
    }
}


#[cfg(test)]
mod metrics_tests {
    use super::measured_results;
    use crate::output::json;

    #[test]
    fn accepts_llama_bench_metrics() {
        let value = json::parse(r#"[{"avg_ts":42.5,"stddev_ts":0.2,"model_filename":"m.gguf","backends":"CUDA","test_time":"2026-01-01T00:00:00Z"}]"#).unwrap();
        assert!(measured_results(&value));
    }

    #[test]
    fn rejects_json_without_measured_metrics() {
        let value = json::parse(r#"[{"message":"benchmark started"}]"#).unwrap();
        assert!(!measured_results(&value));
    }

    #[test]
    fn rejects_zero_or_invalid_throughput() {
        let value = json::parse(r#"[{"avg_ts":0,"stddev_ts":0,"model_filename":"m.gguf","backends":"CPU","test_time":"now"}]"#).unwrap();
        assert!(!measured_results(&value));
    }
}


#[cfg(test)]
mod gguf_tests {
    use super::has_gguf_magic;
    use std::fs;
    use std::io::Write;

    #[test]
    fn validates_gguf_magic_header() {
        let path = std::env::temp_dir().join(format!("leones-lab-agent-{}.gguf", std::process::id()));
        let mut file = fs::File::create(&path).unwrap();
        file.write_all(b"GGUF\x03\x00\x00\x00").unwrap();
        drop(file);
        assert!(has_gguf_magic(&path).unwrap());
        fs::remove_file(path).unwrap();
    }

    #[test]
    fn rejects_non_gguf_magic_header() {
        let path = std::env::temp_dir().join(format!("leones-lab-agent-{}.bin", std::process::id()));
        fs::write(&path, b"NOPE").unwrap();
        assert!(!has_gguf_magic(&path).unwrap());
        fs::remove_file(path).unwrap();
    }
}
