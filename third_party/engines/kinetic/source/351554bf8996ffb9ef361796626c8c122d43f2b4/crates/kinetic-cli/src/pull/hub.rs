//! Hugging Face, reached through the system's curl so that the kinetic
//! binary itself holds no network code.

use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

use serde_json::Value;
use sha2::{Digest, Sha256};

use super::select::RepoFile;
use crate::Result;

const DEFAULT_ENDPOINT: &str = "https://huggingface.co";

pub struct Hub {
    endpoint: String,
    /// From `HF_TOKEN`; handed to curl on its stdin, never on its command
    /// line or in output.
    token: Option<String>,
    curl: PathBuf,
}

impl Hub {
    pub fn new() -> Result<Hub> {
        let curl = find_curl()
            .ok_or("kinetic pull downloads with curl, which is not on PATH; install it")?;
        let var = |k| {
            std::env::var(k)
                .ok()
                .filter(|v: &String| !v.trim().is_empty())
        };
        Ok(Hub {
            endpoint: var("HF_ENDPOINT")
                .unwrap_or_else(|| DEFAULT_ENDPOINT.into())
                .trim_end_matches('/')
                .to_owned(),
            token: var("HF_TOKEN").map(|t| t.trim().to_owned()),
            curl,
        })
    }

    pub fn repo_url(&self, repo: &str) -> String {
        format!("{}/{repo}", self.endpoint)
    }

    pub fn file_url(&self, repo: &str, path: &str) -> String {
        format!("{}/{repo}/resolve/main/{path}", self.endpoint)
    }

    /// Every file of `repo` on its main branch.
    // shortcut: one page of the tree listing, which holds 1000 entries; GGUF repos stay far below
    pub fn files(&self, repo: &str) -> Result<Vec<RepoFile>> {
        let url = format!(
            "{}/api/models/{repo}/tree/main?recursive=true",
            self.endpoint
        );
        let out = self.curl(&["-sS", &url], Stdio::piped())?;
        let list: Value = serde_json::from_slice(&out)
            .map_err(|_| format!("{} did not list the files of {repo}", self.endpoint))?;
        let Some(items) = list.as_array() else {
            let why = list["error"].as_str().unwrap_or("unexpected answer");
            return Err(format!("{repo}: {why}").into());
        };
        Ok(items
            .iter()
            .filter(|i| i["type"] == "file")
            .filter_map(|i| {
                let path = i["path"].as_str().filter(|p| safe_path(p))?;
                Some(RepoFile {
                    path: path.to_owned(),
                    size: i["lfs"]["size"].as_u64().or(i["size"].as_u64())?,
                    sha256: i["lfs"]["oid"].as_str().map(str::to_owned),
                })
            })
            .collect())
    }

    /// Fetches `url` into `part`, continuing what is already there.
    pub fn download(&self, url: &str, part: &Path) -> Result<()> {
        let part = part.to_string_lossy();
        self.curl(
            &["-#", "-C", "-", "--retry", "3", "-o", &part, url],
            Stdio::inherit(),
        )?;
        Ok(())
    }

    fn curl(&self, args: &[&str], stdout: Stdio) -> Result<Vec<u8>> {
        let mut child = Command::new(&self.curl)
            .args(["-fL", "--config", "-"])
            .args(args)
            .stdin(Stdio::piped())
            .stdout(stdout)
            .spawn()?;
        let mut config = String::from("user-agent = \"kinetic\"\n");
        if let Some(token) = &self.token {
            config += &format!("header = \"Authorization: Bearer {token}\"\n");
        }
        if let Some(mut stdin) = child.stdin.take() {
            stdin.write_all(config.as_bytes())?;
        }
        let out = child.wait_with_output()?;
        if !out.status.success() {
            let code = out.status.code().unwrap_or(-1);
            // 22 is curl's code for an HTTP error status under -f
            let why = if code == 22 {
                "the server refused (a gated or private repository needs HF_TOKEN)".to_owned()
            } else {
                format!("curl failed with code {code}")
            };
            return Err(why.into());
        }
        Ok(out.stdout)
    }
}

/// Whether a listed path stays inside the folder it is written to.
fn safe_path(path: &str) -> bool {
    path.split('/')
        .all(|part| !part.is_empty() && part != "." && part != ".." && !part.contains(['\\', ':']))
}

fn find_curl() -> Option<PathBuf> {
    let name = format!("curl{}", std::env::consts::EXE_SUFFIX);
    let path = std::env::var_os("PATH")?;
    std::env::split_paths(&path)
        .map(|d| d.join(&name))
        .find(|p| p.is_file())
}

/// The SHA256 of the file at `path`, in lowercase hex.
pub fn sha256(path: &Path) -> Result<String> {
    let mut file = std::fs::File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buf = vec![0; 1 << 20];
    loop {
        let n = file.read(&mut buf)?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    Ok(hasher
        .finalize()
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn listed_paths_stay_inside() {
        assert!(safe_path("model.gguf") && safe_path("Q4_K_M/model-00001-of-00002.gguf"));
        for bad in [
            "../x.gguf",
            "a/../../x",
            "/abs.gguf",
            "C:x.gguf",
            r"a\..\x",
            "a//b",
        ] {
            assert!(!safe_path(bad), "{bad}");
        }
    }
}
