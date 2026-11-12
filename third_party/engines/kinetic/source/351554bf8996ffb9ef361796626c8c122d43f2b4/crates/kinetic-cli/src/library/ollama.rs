//! Ollama's store: manifests under `manifests/<host>/<namespace>/<model>/<tag>`
//! name content-addressed blobs, the model's weights among them as a GGUF.

use std::fs;
use std::path::{Path, PathBuf};

use serde_json::Value;

const MODEL: &str = "application/vnd.ollama.image.model";
const PROJECTOR: &str = "application/vnd.ollama.image.projector";
const DEFAULT_HOST: &str = "registry.ollama.ai";
const DEFAULT_NAMESPACE: &str = "library";

/// A tagged model: its name as `ollama list` prints it, its weights and
/// its vision projector.
pub struct Entry {
    pub name: String,
    pub model: PathBuf,
    pub projector: Option<PathBuf>,
}

/// Every model in the store at `root` whose weights are on disk.
pub fn scan(root: &Path) -> Vec<Entry> {
    let mut entries = Vec::new();
    for host in dirs(&root.join("manifests")) {
        for namespace in dirs(&host) {
            for model in dirs(&namespace) {
                for tag in files(&model) {
                    let name = display_name(&[&host, &namespace, &model, &tag]);
                    if let Some(entry) = read(root, &tag, name) {
                        entries.push(entry);
                    }
                }
            }
        }
    }
    entries
}

fn read(root: &Path, manifest: &Path, name: String) -> Option<Entry> {
    let manifest: Value = serde_json::from_slice(&fs::read(manifest).ok()?).ok()?;
    let layer = |kind: &str| {
        let digest = manifest["layers"]
            .as_array()?
            .iter()
            .find(|l| l["mediaType"] == kind)?["digest"]
            .as_str()?;
        // on disk the digest's colon becomes a dash: blobs/sha256-<hex>
        let blob = root.join("blobs").join(digest.replacen(':', "-", 1));
        blob.is_file().then_some(blob)
    };
    Some(Entry {
        name,
        model: layer(MODEL)?,
        projector: layer(PROJECTOR),
    })
}

/// `llama3.2:latest` for the default registry's library, `user/model:tag`
/// for other namespaces and `host/namespace/model:tag` for other hosts.
fn display_name(parts: &[&Path; 4]) -> String {
    let [host, namespace, model, tag] = parts.map(|p| {
        p.file_name()
            .map_or_else(String::new, |n| n.to_string_lossy().into_owned())
    });
    match (host.as_str(), namespace.as_str()) {
        (DEFAULT_HOST, DEFAULT_NAMESPACE) => format!("{model}:{tag}"),
        (DEFAULT_HOST, _) => format!("{namespace}/{model}:{tag}"),
        _ => format!("{host}/{namespace}/{model}:{tag}"),
    }
}

fn entries(dir: &Path, want_dir: bool) -> Vec<PathBuf> {
    let Ok(read) = fs::read_dir(dir) else {
        return Vec::new();
    };
    let mut out: Vec<PathBuf> = read
        .flatten()
        .filter(|e| e.file_type().is_ok_and(|t| t.is_dir() == want_dir))
        .map(|e| e.path())
        .collect();
    out.sort();
    out
}

fn dirs(dir: &Path) -> Vec<PathBuf> {
    entries(dir, true)
}

fn files(dir: &Path) -> Vec<PathBuf> {
    entries(dir, false)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reads_manifests_and_names_them_like_ollama() {
        let root = std::env::temp_dir().join(format!("kinetic-ollama-{}", std::process::id()));
        let manifest = |host: &str, ns: &str, model: &str, tag: &str, layers: &str| {
            let dir = root.join("manifests").join(host).join(ns).join(model);
            fs::create_dir_all(&dir).unwrap();
            fs::write(dir.join(tag), format!(r#"{{"layers":[{layers}]}}"#)).unwrap();
        };
        let layer = |kind: &str, hex: &str| {
            format!(
                r#"{{"mediaType":"application/vnd.ollama.image.{kind}","digest":"sha256:{hex}"}}"#
            )
        };
        fs::create_dir_all(root.join("blobs")).unwrap();
        for hex in ["aa", "bb", "cc"] {
            fs::write(root.join("blobs").join(format!("sha256-{hex}")), b"GGUF").unwrap();
        }
        let both = format!("{},{}", layer("model", "aa"), layer("projector", "bb"));
        manifest("registry.ollama.ai", "library", "llava", "7b", &both);
        manifest(
            "registry.ollama.ai",
            "someone",
            "tiny",
            "latest",
            &layer("model", "cc"),
        );
        manifest("hf.co", "org", "repo", "Q4_K_M", &layer("model", "cc"));
        manifest(
            "registry.ollama.ai",
            "library",
            "gone",
            "latest",
            &layer("model", "dd"),
        );

        let found = scan(&root);
        let names: Vec<&str> = found.iter().map(|e| e.name.as_str()).collect();
        assert_eq!(
            names,
            ["hf.co/org/repo:Q4_K_M", "llava:7b", "someone/tiny:latest"]
        );
        assert!(found[1].model.ends_with("sha256-aa"));
        assert!(found[1].projector.as_ref().unwrap().ends_with("sha256-bb"));
        assert!(found[2].projector.is_none());
        fs::remove_dir_all(&root).unwrap();
    }
}
