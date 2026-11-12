//! `kinetic pull` against a local stand-in for Hugging Face.

use std::io::{BufRead, BufReader, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

use sha2::{Digest, Sha256};

const FILE: &str = "tiny-Q4_K_M.gguf";

struct Hub {
    url: String,
    body: Arc<Vec<u8>>,
    served: Arc<AtomicUsize>,
}

/// Serves `good/model` with the right hash and `bad/model` with a wrong one.
fn hub() -> Hub {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let url = format!("http://{}", listener.local_addr().unwrap());
    let body: Arc<Vec<u8>> = Arc::new((0..300_000u32).map(|i| (i % 251) as u8).collect());
    let served = Arc::new(AtomicUsize::new(0));
    let (b, s) = (body.clone(), served.clone());
    std::thread::spawn(move || {
        for stream in listener.incoming().flatten() {
            answer(stream, &b, &s);
        }
    });
    Hub { url, body, served }
}

fn answer(mut stream: TcpStream, body: &[u8], served: &AtomicUsize) {
    let mut reader = BufReader::new(stream.try_clone().unwrap());
    let mut line = String::new();
    reader.read_line(&mut line).unwrap();
    let target = line.split(' ').nth(1).unwrap_or("").to_owned();
    let mut from = 0;
    loop {
        let mut h = String::new();
        if reader.read_line(&mut h).unwrap() == 0 || h.trim().is_empty() {
            break;
        }
        if let Some(r) = h.to_ascii_lowercase().strip_prefix("range: bytes=") {
            from = r.trim().trim_end_matches('-').parse().unwrap();
        }
    }
    let sha = |good| match good {
        true => format!("{:x}", Sha256::digest(body)),
        false => "0".repeat(64),
    };
    let (status, bytes) = match target.as_str() {
        "/api/models/good/model/tree/main?recursive=true"
        | "/api/models/bad/model/tree/main?recursive=true" => {
            let list = serde_json::json!([
                {"type": "file", "path": "README.md", "size": 10},
                {"type": "file", "path": FILE, "size": body.len(),
                 "lfs": {"oid": sha(target.contains("good")), "size": body.len()}},
            ]);
            ("200 OK".to_owned(), list.to_string().into_bytes())
        }
        t if t.ends_with(&format!("/model/resolve/main/{FILE}")) => {
            served.fetch_add(body.len() - from, Ordering::SeqCst);
            let status = match from {
                0 => "200 OK".to_owned(),
                n => format!(
                    "206 Partial Content\r\nContent-Range: bytes {n}-{}/{}",
                    body.len() - 1,
                    body.len()
                ),
            };
            (status, body[from..].to_vec())
        }
        _ => (
            "404 Not Found".to_owned(),
            b"{\"error\":\"not found\"}".to_vec(),
        ),
    };
    let head = format!(
        "HTTP/1.1 {status}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
        bytes.len()
    );
    stream.write_all(head.as_bytes()).unwrap();
    stream.write_all(&bytes).unwrap();
}

fn has_curl() -> bool {
    Command::new("curl").arg("--version").output().is_ok()
}

fn pull(hub: &Hub, repo: &str, dir: &Path) -> Output {
    Command::new(env!("CARGO_BIN_EXE_kinetic"))
        .args(["pull", repo, "--dir"])
        .arg(dir)
        .env("HF_ENDPOINT", &hub.url)
        .env_remove("HF_TOKEN")
        .output()
        .unwrap()
}

fn scratch(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("kinetic-pull-{name}-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    dir
}

fn stderr(out: &Output) -> String {
    String::from_utf8_lossy(&out.stderr).into_owned()
}

#[test]
fn downloads_resumes_and_skips() {
    if !has_curl() {
        eprintln!("skipped: no curl on PATH");
        return;
    }
    let hub = hub();
    let dir = scratch("good");
    let file = dir.join("good").join("model").join(FILE);

    let out = pull(&hub, "good/model", &dir);
    assert!(out.status.success(), "{}", stderr(&out));
    assert_eq!(std::fs::read(&file).unwrap(), *hub.body);
    assert!(!dir.join("good/model/README.md").exists());

    std::fs::remove_file(&file).unwrap();
    let half = hub.body.len() / 2;
    let mut part = file.clone().into_os_string();
    part.push(".part");
    std::fs::write(&part, &hub.body[..half]).unwrap();
    let before = hub.served.load(Ordering::SeqCst);
    let out = pull(&hub, "good/model", &dir);
    assert!(out.status.success(), "{}", stderr(&out));
    assert_eq!(std::fs::read(&file).unwrap(), *hub.body);
    assert_eq!(
        hub.served.load(Ordering::SeqCst) - before,
        hub.body.len() - half
    );

    let out = pull(&hub, "good/model", &dir);
    assert!(stderr(&out).contains("is already here"), "{}", stderr(&out));
    std::fs::remove_dir_all(&dir).unwrap();
}

#[test]
fn deletes_a_corrupt_download() {
    if !has_curl() {
        eprintln!("skipped: no curl on PATH");
        return;
    }
    let hub = hub();
    let dir = scratch("bad");
    let out = pull(&hub, "bad/model", &dir);
    assert!(!out.status.success());
    assert!(stderr(&out).contains("is corrupt"), "{}", stderr(&out));
    let left: Vec<_> = std::fs::read_dir(dir.join("bad").join("model"))
        .unwrap()
        .collect();
    assert!(left.is_empty());
    std::fs::remove_dir_all(&dir).unwrap();
}

#[test]
fn a_missing_repository_is_an_error() {
    if !has_curl() {
        eprintln!("skipped: no curl on PATH");
        return;
    }
    let hub = hub();
    let dir = scratch("missing");
    let out = pull(&hub, "nobody/nothing", &dir);
    assert!(!out.status.success());
    assert!(!dir.exists());
}
