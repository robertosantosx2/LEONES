//! Running llama.cpp's own tools, as installed on this computer.

use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant};

use kinetic_gguf::GgufFile;
use serde_json::{json, Value};

use super::{install_dirs, Settings, Speeds};
use crate::bench::{edit_prompt, EDIT_TOKENS};
use crate::Result;

/// How long llama-server may take to load the model.
const START_TIMEOUT: Duration = Duration::from_secs(120);

/// What llama.cpp measured, and how it ran.
pub struct Llama {
    pub speeds: Speeds,
    /// Such as `b12001 (eb4e244be)`.
    pub version: String,
    pub backend: String,
    pub gpu: String,
    /// The speculative mode of the edit test, or why it was not run.
    pub edit_mode: String,
}

fn exe(name: &str) -> String {
    format!("{name}{}", std::env::consts::EXE_SUFFIX)
}

/// llama-bench: the file or folder given, else on `PATH` or in a common
/// install folder. Nothing is ever downloaded.
pub fn find(given: &Path) -> Result<PathBuf> {
    if !given.as_os_str().is_empty() {
        let path = if given.is_dir() {
            given.join(exe("llama-bench"))
        } else {
            given.to_path_buf()
        };
        return if path.is_file() {
            Ok(path)
        } else {
            Err(format!("{}: no such file", path.display()).into())
        };
    }
    let path = std::env::var_os("PATH").unwrap_or_default();
    let mut dirs: Vec<PathBuf> = std::env::split_paths(&path).collect();
    dirs.extend(install_dirs());
    dirs.iter()
        .map(|d| d.join(exe("llama-bench")))
        .find(|p| p.is_file())
        .ok_or_else(|| {
            "llama-bench was not found on PATH or in the usual install folders; \
             pass it: kinetic bench <model> --compare <path to llama-bench>"
                .into()
        })
}

pub fn measure(bench: &Path, model: &Path, on_gpu: bool, s: &Settings) -> Result<Llama> {
    let mut cmd = Command::new(bench);
    cmd.arg("-m")
        .arg(model)
        .args(["-p", "512", "-n", "128", "-fa", "1", "-o", "json"])
        .args([
            "-r",
            &s.repetitions.to_string(),
            "-t",
            &s.threads.to_string(),
        ])
        .args(device_args(on_gpu));
    let out = cmd.stderr(Stdio::piped()).output()?;
    if !out.status.success() {
        let log = String::from_utf8_lossy(&out.stderr);
        let tail: Vec<&str> = log.lines().rev().take(3).collect();
        return Err(format!(
            "llama-bench failed: {}",
            tail.into_iter().rev().collect::<Vec<_>>().join(" | ")
        )
        .into());
    }
    let tests: Vec<Value> = serde_json::from_slice(&out.stdout)?;
    let best = |key: &str| {
        tests
            .iter()
            .filter(|t| t[key].as_u64().unwrap_or(0) > 0)
            .flat_map(|t| t["samples_ts"].as_array().cloned().unwrap_or_default())
            .filter_map(|v| v.as_f64())
            .fold(0.0, f64::max)
    };
    let first = tests.first().cloned().unwrap_or_default();
    let text = |key: &str| first[key].as_str().unwrap_or("").trim().to_owned();
    let version = match (first["build_number"].as_u64(), text("build_commit")) {
        (Some(n), commit) => format!("b{n} ({commit})"),
        (None, commit) => commit,
    };

    let mode = edit_mode(model);
    let server = bench.with_file_name(exe("llama-server"));
    let (edit, edit_mode) = if !server.is_file() {
        (
            None,
            "not run: llama-server is not next to llama-bench".to_owned(),
        )
    } else {
        match edit(&server, model, on_gpu, s, mode) {
            Ok(speed) => (Some(speed), mode.to_owned()),
            Err(e) => (None, format!("not run: {e}")),
        }
    };
    Ok(Llama {
        speeds: Speeds {
            prompt: best("n_prompt"),
            generate: best("n_gen"),
            edit,
        },
        version,
        backend: text("backends"),
        gpu: text("gpu_info"),
        edit_mode,
    })
}

fn device_args(on_gpu: bool) -> Vec<&'static str> {
    if on_gpu {
        vec!["-ngl", "99"]
    } else {
        vec!["-ngl", "0", "-dev", "none"]
    }
}

/// The speculative mode llama.cpp has for the model: its own prediction
/// layers where it has them, else drafts looked up in the context, as
/// Kinetic does.
fn edit_mode(model: &Path) -> &'static str {
    let mtp = GgufFile::open(model).ok().is_some_and(|f| {
        f.header()
            .arch_key("nextn_predict_layers")
            .and_then(|v| v.as_u64())
            .is_some_and(|n| n > 0)
    });
    if mtp {
        "draft-mtp"
    } else {
        "ngram-simple"
    }
}

/// Kills llama-server however the measurement ends.
struct Server(Child);

impl Drop for Server {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

/// The best greedy decode speed of llama-server on the edit prompt.
fn edit(server: &Path, model: &Path, on_gpu: bool, s: &Settings, mode: &str) -> Result<f64> {
    let port = TcpListener::bind("127.0.0.1:0")?.local_addr()?.port();
    let child = Command::new(server)
        .arg("-m")
        .arg(model)
        .args(["--host", "127.0.0.1", "--port", &port.to_string()])
        .args([
            "-c",
            "2048",
            "-np",
            "1",
            "-fa",
            "on",
            "--no-webui",
            "--spec-type",
            mode,
        ])
        .args(["-t", &s.threads.to_string()])
        .args(device_args(on_gpu))
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()?;
    let mut server = Server(child);
    let start = Instant::now();
    while request(port, "GET", "/health", None).is_err() {
        if start.elapsed() > START_TIMEOUT || server.0.try_wait()?.is_some() {
            return Err(format!("llama-server did not start with --spec-type {mode}").into());
        }
        std::thread::sleep(Duration::from_millis(250));
    }
    let body = json!({
        "prompt": edit_prompt(),
        "n_predict": EDIT_TOKENS,
        "temperature": 0,
        "top_k": 1,
        "repeat_penalty": 1.0,
        "ignore_eos": true,
        "cache_prompt": false,
    });
    let mut best: f64 = 0.0;
    // the first run pages the weights in
    for _ in 0..=s.repetitions {
        let answer = request(port, "POST", "/completion", Some(&body))?;
        let speed = answer
            .pointer("/timings/predicted_per_second")
            .and_then(Value::as_f64)
            .ok_or("llama-server reported no timings")?;
        best = best.max(speed);
    }
    drop(server);
    Ok(best)
}

/// One HTTP/1.1 request to llama-server on this computer.
fn request(port: u16, method: &str, path: &str, body: Option<&Value>) -> Result<Value> {
    let mut stream = TcpStream::connect(("127.0.0.1", port))?;
    stream.set_read_timeout(Some(Duration::from_secs(300)))?;
    let body = body.map(Value::to_string).unwrap_or_default();
    write!(
        stream,
        "{method} {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
        body.len()
    )?;
    let mut response = Vec::new();
    stream.read_to_end(&mut response)?;
    let text = String::from_utf8_lossy(&response);
    let (head, body) = text.split_once("\r\n\r\n").ok_or("malformed response")?;
    if !head.starts_with("HTTP/1.1 200") {
        return Err(head.lines().next().unwrap_or("no status").to_owned().into());
    }
    Ok(serde_json::from_str(body)?)
}
