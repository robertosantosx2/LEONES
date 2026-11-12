//! BLAKE3 of large files, remembered by path, size and modification time,
//! so a model is hashed once rather than on every request.

use std::collections::BTreeMap;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;

use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, PartialEq)]
struct Entry {
    size: u64,
    modified: u128,
    blake3: String,
}

/// `kinetic/hashes.json` in the user's cache directory.
fn cache_file() -> Option<PathBuf> {
    Some(
        kinetic_models::warm::default_dir()?
            .parent()?
            .join("hashes.json"),
    )
}

/// The BLAKE3 of the file at `path` in hex, from the cache when the file
/// has not changed since it was last hashed.
pub fn blake3_hex(path: &Path) -> io::Result<String> {
    let path = fs::canonicalize(path)?;
    let meta = fs::metadata(&path)?;
    let modified = meta
        .modified()?
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    let key = path.to_string_lossy().into_owned();
    let cache = cache_file();
    let mut known: BTreeMap<String, Entry> = cache
        .as_ref()
        .and_then(|f| fs::read(f).ok())
        .and_then(|b| serde_json::from_slice(&b).ok())
        .unwrap_or_default();
    if let Some(e) = known.get(&key) {
        if e.size == meta.len() && e.modified == modified {
            return Ok(e.blake3.clone());
        }
    }
    let hash = blake3::Hasher::new()
        .update_mmap_rayon(&path)?
        .finalize()
        .to_hex()
        .to_string();
    known.retain(|p, _| Path::new(p).exists());
    known.insert(
        key,
        Entry {
            size: meta.len(),
            modified,
            blake3: hash.clone(),
        },
    );
    // a cache that cannot be written only costs a rehash next time
    if let Some(file) = cache {
        let _ = save(&file, &known);
    }
    Ok(hash)
}

fn save(file: &Path, known: &BTreeMap<String, Entry>) -> io::Result<()> {
    if let Some(dir) = file.parent() {
        fs::create_dir_all(dir)?;
    }
    let tmp = file.with_extension(format!("{}.tmp", std::process::id()));
    fs::write(&tmp, serde_json::to_vec(known)?)?;
    fs::rename(&tmp, file)
}
