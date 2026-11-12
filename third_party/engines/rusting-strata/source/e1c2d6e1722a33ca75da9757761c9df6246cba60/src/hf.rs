//! Model downloads from Hugging Face for the chat page of `rustingstrata serve`. `HF_TOKEN`, if set, is sent for gated
//! and private repos.

use crate::serve::{models, shard};
use anyhow::{Context, bail, ensure};
use std::io::{Read, Write};
use std::path::Path;
use std::sync::Mutex;
use std::time::Duration;

/// The running or last download, as the chat page shows it.
#[derive(Clone, Default, serde::Serialize)]
pub struct Progress {
    pub repo: String,
    pub file: String,
    pub done: u64,
    pub total: u64,
    pub running: bool,
    pub cancel: bool,
    pub error: Option<String>,
}

/// A GET with timeouts for a stalled connection: 30 s to connect, 60 s for the response and for each read of the
/// body (so a stalled download fails and can be cancelled), and `whole` for everything.
fn get(url: &str, whole: Option<Duration>) -> ureq::RequestBuilder<ureq::typestate::WithoutBody> {
    let s = Some(Duration::from_secs(60));
    let agent: ureq::Agent = ureq::Agent::config_builder().timeout_connect(Some(Duration::from_secs(30)))
        .timeout_recv_response(s).timeout_per_read(s).timeout_global(whole).build().into();
    let r = agent.get(url);
    match std::env::var("HF_TOKEN") { Ok(t) if !t.is_empty() => r.header("Authorization", format!("Bearer {t}")), _ => r }
}

/// "owner/name" with the characters Hugging Face allows, so it cannot change the URL it goes into.
pub fn valid_repo(r: &str) -> bool {
    let ok = |s: &str| !s.is_empty() && s != "." && s != ".." && s.bytes().all(|b| b.is_ascii_alphanumeric() || b"._-".contains(&b));
    r.split_once('/').is_some_and(|(a, b)| ok(a) && ok(b))
}

/// The name a repo file is saved under: its last path component, if that is a plain .gguf file name. The name comes
/// from the repo, so `\` (a separator on Windows), `:` (a drive or stream on Windows) and control characters are
/// refused.
pub fn local_name(f: &str) -> Option<&str> {
    let n = f.rsplit('/').next()?;
    (n.ends_with(".gguf") && !n.starts_with('.') && !n.chars().any(|c| c == '\\' || c == ':' || c.is_control()))
        .then_some(n)
}

/// FNV-1a: a hash that stays the same across builds, for file names.
fn fnv(s: &str) -> u64 { s.bytes().fold(0xcbf29ce484222325, |h, b| (h ^ b as u64).wrapping_mul(0x100000001b3)) }

/// Every file of `repo` with its size in bytes.
fn files(repo: &str) -> anyhow::Result<Vec<(String, u64)>> {
    ensure!(valid_repo(repo), "{repo:?} is not a Hugging Face repo name (owner/name)");
    let mut r = get(&format!("https://huggingface.co/api/models/{repo}?blobs=true"), Some(Duration::from_secs(60))).call()
        .with_context(|| format!("Hugging Face repo {repo} (check the name; a private or gated repo needs HF_TOKEN)"))?;
    let v: serde_json::Value = serde_json::from_str(&r.body_mut().read_to_string()?)?;
    Ok(v["siblings"].as_array().context("no file list")?.iter()
        .filter_map(|s| Some((s["rfilename"].as_str()?.to_string(), s["size"].as_u64().unwrap_or(0)))).collect())
}

/// The models of `repo` as (file, bytes over all shards); see `serve::models`.
pub fn list(repo: &str) -> anyhow::Result<Vec<(String, u64)>> { Ok(models(&files(repo)?)) }

/// Downloads `file` of `repo` (with the other shards of a split model) into `dir`, without the repo's folders.
/// Each file goes through a `.part` file that a later attempt resumes. `p` tracks the bytes; `p.cancel` stops it.
pub fn download(repo: &str, file: &str, dir: &Path, p: &Mutex<Progress>) -> anyhow::Result<()> {
    let all = files(repo)?;
    let want: Vec<_> = all.into_iter().filter(|(f, _)| f.ends_with(".gguf") && match shard(file) {
        Some((stem, _)) => shard(f).is_some_and(|(s, _)| s == stem),
        None => f == file,
    }).collect();
    ensure!(!want.is_empty(), "{repo} has no model file {file}");
    std::fs::create_dir_all(dir).with_context(|| format!("create {}", dir.display()))?;
    p.lock().unwrap().total = want.iter().map(|x| x.1).sum();
    let mut before = 0;
    for (f, size) in &want {
        let name = local_name(f).with_context(|| format!("{repo} has a file name strata does not save: {f:?}"))?;
        // The .part name carries the repo and path, so a same-named file of another repo or folder is not resumed.
        let (dst, part) = (dir.join(name), dir.join(format!("{name}.{:016x}.part", fnv(&format!("{repo}/{f}")))));
        if let Ok(m) = std::fs::metadata(&dst) {
            ensure!(*size == 0 || m.len() == *size, "{} already exists with another size; move it away to download {f}", dst.display());
        } else {
            let mut have = std::fs::metadata(&part).map_or(0, |m| m.len());
            if have > *size && *size > 0 { have = 0; }  // not this file: start over
            if have < *size || *size == 0 {
                let url = format!("https://huggingface.co/{repo}/resolve/main/{f}");
                let r = get(&url, None).header("Range", format!("bytes={have}-")).call().with_context(|| format!("download {f}"))?;
                if r.status() != 206 { have = 0; }  // the range was ignored: start over
                let mut out = std::fs::OpenOptions::new().create(true).write(true).append(have > 0).truncate(have == 0).open(&part)?;
                let (mut rd, mut buf) = (r.into_body().into_reader(), vec![0; 1 << 20]);
                loop {
                    let n = rd.read(&mut buf).with_context(|| format!("download {f}"))?;
                    if n == 0 { break; }
                    out.write_all(&buf[..n]).with_context(|| format!("write {}", part.display()))?;
                    have += n as u64;
                    let mut g = p.lock().unwrap();
                    g.done = before + have;
                    if g.cancel { bail!("cancelled ({} kept, the next download of this file resumes it)", part.display()); }
                }
            }
            ensure!(*size == 0 || have == *size, "{f}: received {have} of {size} bytes");
            std::fs::rename(&part, &dst)?;
        }
        before += size;
        p.lock().unwrap().done = before;
    }
    Ok(())
}
