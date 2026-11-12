//! `kinetic pull`: the one command that uses the network. It downloads a
//! GGUF model from Hugging Face into Kinetic's models folder.

mod hub;
mod select;

use std::path::{Path, PathBuf};

use crate::{fit, library, system, Result};
use hub::Hub;
use select::RepoFile;

/// Disk left free after a download.
const SPARE_DISK: u64 = 2 << 30;
const GIB: f64 = (1u64 << 30) as f64;

/// What to download, as `kinetic pull` takes it.
pub struct Pull<'a> {
    /// `<org>/<repo>` or `<org>/<repo>:<quant>`.
    pub spec: &'a str,
    pub file: Option<&'a str>,
    pub projector: bool,
    pub dir: Option<&'a Path>,
}

/// Downloads what `p` asks for and returns the model file's path.
pub fn run(p: &Pull) -> Result<PathBuf> {
    // the only door to the internet, and it opens only when you knock
    let (repo, quant) = parse(p.spec)?;
    let root = match p.dir {
        Some(d) => d.to_path_buf(),
        None => library::kinetic_dir().ok_or("no folder for models; pass --dir")?,
    };
    let dest = repo.split('/').fold(root, |d, part| d.join(part));
    let hub = Hub::new()?;
    let listed = hub.files(repo)?;
    let quant = match (quant, p.file) {
        (None, None) => auto_quant(&listed),
        _ => quant,
    };
    let files = select::pick(&listed, quant, p.file, p.projector)?;

    let have = |f: &RepoFile| -> u64 {
        let size = |p: &Path| std::fs::metadata(p).map_or(0, |m| m.len());
        let target = target(&dest, &f.path);
        if size(&target) == f.size {
            f.size
        } else {
            size(&part(&target)).min(f.size)
        }
    };
    let total: u64 = files.iter().map(|f| f.size).sum();
    let missing: u64 = files.iter().map(|f| f.size - have(f)).sum();
    eprintln!("From {}", hub.repo_url(repo));
    for f in &files {
        eprintln!("  {} ({})", f.path, human(f.size));
    }
    eprintln!("{} into {}", human(total), dest.display());
    if let Some(free) = system::disk_free(&dest) {
        if free < missing + SPARE_DISK {
            return Err(format!(
                "{:.1} GiB is free there; the download needs {:.1} GiB and 2 GiB to spare",
                free as f64 / GIB,
                missing as f64 / GIB
            )
            .into());
        }
    }
    if files.len() > 1
        && files
            .iter()
            .all(|f| library::shard(Path::new(&f.path)).is_some())
    {
        eprintln!("kinetic: note that Kinetic does not load models split into parts yet");
    }

    for f in &files {
        let target = target(&dest, &f.path);
        if have(f) == f.size && target.is_file() {
            eprintln!("{} is already here", f.path);
            continue;
        }
        if let Some(dir) = target.parent() {
            std::fs::create_dir_all(dir)?;
        }
        let part = part(&target);
        if have(f) < f.size {
            hub.download(&hub.file_url(repo, &f.path), &part)?;
        }
        if let Some(expected) = &f.sha256 {
            eprintln!("checking {}", f.path);
            let actual = hub::sha256(&part)?;
            if &actual != expected {
                std::fs::remove_file(&part)?;
                return Err(format!(
                    "{} is corrupt (SHA256 {actual}, expected {expected}); it was deleted, run pull again",
                    f.path
                )
                .into());
            }
        }
        std::fs::rename(&part, &target)?;
    }

    let first = target(&dest, &files[0].path);
    let canonical = first.canonicalize()?;
    let name = library::discover()
        .into_iter()
        .find(|m| m.path.canonicalize().is_ok_and(|p| p == canonical))
        .map_or_else(|| first.display().to_string(), |m| m.name);
    eprintln!("Done. Run it with: kinetic run {name}");
    Ok(first)
}

/// The quantization that suits this computer, said in one line.
fn auto_quant(files: &[RepoFile]) -> Option<&'static str> {
    let (gpus, _) = system::gpus();
    let (room, place) = fit::room(&gpus);
    let (quant, fits) = select::fitting_quant(files, room)?;
    let room = room as f64 / GIB;
    if fits {
        eprintln!("Picked {quant}: the largest that fits {place} with room for context ({room:.1} GiB for the model); add :<quant> to choose");
    } else {
        eprintln!("Picked {quant}: the smallest of good quality, though it is tight {place} ({room:.1} GiB for the model), so expect slower answers");
    }
    Some(quant)
}

fn human(bytes: u64) -> String {
    if bytes >= 1 << 30 {
        format!("{:.2} GiB", bytes as f64 / GIB)
    } else {
        format!("{:.1} MiB", bytes as f64 / (1u64 << 20) as f64)
    }
}

fn target(dest: &Path, path: &str) -> PathBuf {
    path.split('/')
        .fold(dest.to_path_buf(), |d, part| d.join(part))
}

fn part(target: &Path) -> PathBuf {
    let mut name = target.as_os_str().to_owned();
    name.push(".part");
    PathBuf::from(name)
}

/// The repository and quantization of `org/repo[:quant]`, also accepted
/// as a huggingface.co or hf.co link.
fn parse(spec: &str) -> Result<(&str, Option<&str>)> {
    let spec = [
        "https://huggingface.co/",
        "huggingface.co/",
        "https://hf.co/",
        "hf.co/",
    ]
    .iter()
    .find_map(|p| spec.strip_prefix(p))
    .unwrap_or(spec);
    let (repo, quant) = match spec.split_once(':') {
        Some((repo, quant)) => (repo, Some(quant).filter(|q| !q.is_empty())),
        None => (spec, None),
    };
    let ok = |s: &str| {
        !s.is_empty()
            && !s.starts_with('.')
            && s.bytes()
                .all(|b| b.is_ascii_alphanumeric() || b"-_.".contains(&b))
    };
    match repo.split_once('/') {
        Some((org, name)) if ok(org) && ok(name) => Ok((repo, quant)),
        _ => Err(
            format!("{spec} is not a Hugging Face repository; write <org>/<repo>[:<quant>]").into(),
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reads_repository_names() {
        assert_eq!(
            parse("unsloth/Qwen3-4B-GGUF").unwrap(),
            ("unsloth/Qwen3-4B-GGUF", None)
        );
        assert_eq!(
            parse("hf.co/ggml-org/gemma-3-1b-it-GGUF:Q4_K_M").unwrap(),
            ("ggml-org/gemma-3-1b-it-GGUF", Some("Q4_K_M"))
        );
        assert_eq!(parse("https://huggingface.co/a/b").unwrap(), ("a/b", None));
        for bad in ["llama3.2", "a/b/c", "a/../b", "../x", "a/b c"] {
            assert!(parse(bad).is_err(), "{bad}");
        }
    }
}
