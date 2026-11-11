//! What a model's GGUF header says about it, read without touching its
//! weights.

use std::path::Path;

use kinetic_gguf::GgufFile;

/// The facts `kinetic models` shows.
#[derive(Clone, Debug)]
pub struct Header {
    pub arch: String,
    /// The quantization as llama.cpp names the file type, e.g. Q4_K_M.
    pub quant: String,
    /// Bytes of every part of the model.
    pub size: u64,
    /// Files the model is split into.
    pub parts: u32,
}

impl Header {
    pub fn read(path: &Path) -> Result<Header, String> {
        // the header is parsed from the mapped file; the weights stay on disk
        let file = GgufFile::open(path).map_err(|e| e.to_string())?;
        let g = file.header();
        let arch = g.architecture().unwrap_or("unknown").to_owned();
        let quant = g.quantization();
        let (size, parts) = match shard(path) {
            Some((_, n)) => (shards_size(path, n), n),
            None => (file.len(), 1),
        };
        Ok(Header {
            arch,
            quant,
            size,
            parts,
        })
    }

    /// Whether this is a vision projector rather than a model.
    pub fn is_projector(&self) -> bool {
        self.arch == "clip"
    }

    /// Whether Kinetic runs it, and if not, why.
    pub fn support(&self) -> String {
        if self.parts > 1 {
            format!("no, {} parts", self.parts)
        } else if kinetic_models::supports(&self.arch) {
            "yes".into()
        } else {
            "no".into()
        }
    }
}

/// The part number and part count of a split GGUF file, named like
/// `model-00001-of-00003.gguf`.
pub fn shard(path: &Path) -> Option<(u32, u32)> {
    let stem = path.file_stem()?.to_str()?;
    let (rest, count) = stem.rsplit_once("-of-")?;
    let (_, index) = rest.rsplit_once('-')?;
    let digits = |s: &str| s.len() == 5 && s.bytes().all(|b| b.is_ascii_digit());
    if !digits(index) || !digits(count) {
        return None;
    }
    Some((index.parse().ok()?, count.parse().ok()?))
}

/// The file name without its extension and part suffix.
pub fn model_stem(path: &Path) -> String {
    let stem = path
        .file_stem()
        .map_or_else(String::new, |s| s.to_string_lossy().into_owned());
    match shard(path) {
        Some(_) => stem[..stem.len() - "-00001-of-00001".len()].to_owned(),
        None => stem,
    }
}

fn shards_size(first: &Path, parts: u32) -> u64 {
    let stem = model_stem(first);
    let dir = first.parent().unwrap_or(Path::new("."));
    (1..=parts)
        .filter_map(|i| {
            std::fs::metadata(dir.join(format!("{stem}-{i:05}-of-{parts:05}.gguf"))).ok()
        })
        .map(|m| m.len())
        .sum()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reads_part_suffixes() {
        let p = Path::new("dir/Qwen3-235B-Q4_K_M-00002-of-00005.gguf");
        assert_eq!(shard(p), Some((2, 5)));
        assert_eq!(model_stem(p), "Qwen3-235B-Q4_K_M");
        assert_eq!(shard(Path::new("model-of-x.gguf")), None);
        assert_eq!(
            model_stem(Path::new("a/LFM3-1.7B-Q4_K_M.gguf")),
            "LFM3-1.7B-Q4_K_M"
        );
    }
}
