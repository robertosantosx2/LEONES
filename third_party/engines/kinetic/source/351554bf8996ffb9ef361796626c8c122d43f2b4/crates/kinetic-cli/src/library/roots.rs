//! Where other tools keep their models.

use std::path::PathBuf;

use super::Store;

fn var(name: &str) -> Option<PathBuf> {
    std::env::var_os(name)
        .filter(|v| !v.is_empty())
        .map(PathBuf::from)
}

fn home() -> Option<PathBuf> {
    std::env::home_dir().filter(|h| !h.as_os_str().is_empty())
}

/// The per-user cache directory other tools follow on Linux.
fn xdg_cache() -> Option<PathBuf> {
    var("XDG_CACHE_HOME").or_else(|| home().map(|h| h.join(".cache")))
}

/// Where `kinetic pull` stores models: `KINETIC_MODELS`, or the user's
/// local data directory.
pub fn kinetic_dir() -> Option<PathBuf> {
    if let Some(dir) = var("KINETIC_MODELS") {
        return Some(dir);
    }
    let base = if cfg!(windows) {
        var("LOCALAPPDATA")
    } else {
        var("XDG_DATA_HOME").or_else(|| home().map(|h| h.join(".local").join("share")))
    }?;
    Some(base.join("kinetic").join("models"))
}

/// Every place to look, in the order names are tried.
pub fn all() -> Vec<(Store, PathBuf)> {
    let mut roots = Vec::new();
    let mut add = |store, dir: Option<PathBuf>| {
        if let Some(dir) = dir {
            roots.push((store, dir));
        }
    };
    add(Store::Kinetic, kinetic_dir());

    match var("OLLAMA_MODELS") {
        Some(dir) => add(Store::Ollama, Some(dir)),
        None => {
            add(
                Store::Ollama,
                home().map(|h| h.join(".ollama").join("models")),
            );
            if cfg!(target_os = "linux") {
                // the systemd service installed by Ollama's script runs as user ollama
                add(
                    Store::Ollama,
                    Some(PathBuf::from("/usr/share/ollama/.ollama/models")),
                );
            }
        }
    }

    add(
        Store::LmStudio,
        home().map(|h| h.join(".lmstudio").join("models")),
    );
    add(
        Store::LmStudio,
        home().map(|h| h.join(".cache").join("lm-studio").join("models")),
    );

    let hf = var("HF_HUB_CACHE")
        .or_else(|| var("HF_HOME").map(|h| h.join("hub")))
        .or_else(|| xdg_cache().map(|c| c.join("huggingface").join("hub")));
    add(Store::HuggingFace, hf);

    let llama = var("LLAMA_CACHE").or_else(|| {
        if cfg!(windows) {
            var("LOCALAPPDATA").map(|d| d.join("llama.cpp"))
        } else {
            xdg_cache().map(|c| c.join("llama.cpp"))
        }
    });
    add(Store::LlamaCpp, llama);

    if cfg!(windows) {
        add(Store::Folder, Some(PathBuf::from(r"C:\models")));
    }
    roots
}
