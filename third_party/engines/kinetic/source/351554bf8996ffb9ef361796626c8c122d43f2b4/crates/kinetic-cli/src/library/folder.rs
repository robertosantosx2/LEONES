//! Stores that keep GGUF files as they are: one folder per Hugging Face
//! repository (LM Studio, the Hugging Face cache, `kinetic pull`) or plain
//! folders of files (llama.cpp's cache, a models folder).

use std::fs;
use std::path::{Path, PathBuf};

/// Folders below a root that are searched for GGUF files.
const MAX_DEPTH: usize = 4;

/// The GGUF files of one repository, or of one plain folder when `repo` is
/// `None`.
pub struct Group {
    pub repo: Option<String>,
    pub files: Vec<PathBuf>,
}

/// `<root>/<org>/<repo>/...`, as LM Studio and `kinetic pull` lay it out.
pub fn repos(root: &Path) -> Vec<Group> {
    let mut groups = Vec::new();
    for org in subdirs(root) {
        for repo in subdirs(&org) {
            let files = gguf_files(&repo, MAX_DEPTH);
            if !files.is_empty() {
                groups.push(Group {
                    repo: Some(format!("{}/{}", file_name(&org), file_name(&repo))),
                    files,
                });
            }
        }
    }
    groups
}

/// `<root>/models--<org>--<repo>/snapshots/<revision>/...`, the Hugging Face
/// cache, reading the revision `refs/main` points at.
pub fn hf_cache(root: &Path) -> Vec<Group> {
    let mut groups = Vec::new();
    for dir in subdirs(root) {
        let Some(repo) = file_name(&dir)
            .strip_prefix("models--")
            .map(|r| r.replacen("--", "/", 1))
        else {
            continue;
        };
        let snapshots = dir.join("snapshots");
        let main = fs::read_to_string(dir.join("refs").join("main"))
            .ok()
            .map(|rev| snapshots.join(rev.trim()))
            .filter(|d| d.is_dir());
        let revisions = main.map_or_else(|| subdirs(&snapshots), |d| vec![d]);
        let files: Vec<PathBuf> = revisions
            .iter()
            .flat_map(|r| gguf_files(r, MAX_DEPTH))
            .collect();
        if !files.is_empty() {
            groups.push(Group {
                repo: Some(repo),
                files,
            });
        }
    }
    groups
}

/// Every folder at or below `root` holding GGUF files, each a group.
pub fn flat(root: &Path) -> Vec<Group> {
    let mut groups = Vec::new();
    let mut pending = vec![(root.to_path_buf(), 0)];
    while let Some((dir, depth)) = pending.pop() {
        let files = gguf_files(&dir, 0);
        if !files.is_empty() {
            groups.push(Group { repo: None, files });
        }
        if depth < MAX_DEPTH {
            pending.extend(subdirs(&dir).into_iter().rev().map(|d| (d, depth + 1)));
        }
    }
    groups
}

/// GGUF files in `dir` and, `depth` levels down, its subfolders, sorted.
fn gguf_files(dir: &Path, depth: usize) -> Vec<PathBuf> {
    let Ok(read) = fs::read_dir(dir) else {
        return Vec::new();
    };
    let mut files = Vec::new();
    for entry in read.flatten() {
        let path = entry.path();
        if path.is_dir() {
            if depth > 0 {
                files.extend(gguf_files(&path, depth - 1));
            }
        } else if path
            .extension()
            .is_some_and(|e| e.eq_ignore_ascii_case("gguf"))
        {
            files.push(path);
        }
    }
    files.sort();
    files
}

fn subdirs(dir: &Path) -> Vec<PathBuf> {
    let Ok(read) = fs::read_dir(dir) else {
        return Vec::new();
    };
    let mut dirs: Vec<PathBuf> = read
        .flatten()
        .map(|e| e.path())
        .filter(|p| p.is_dir())
        .collect();
    dirs.sort();
    dirs
}

fn file_name(path: &Path) -> String {
    path.file_name()
        .map_or_else(String::new, |n| n.to_string_lossy().into_owned())
}
