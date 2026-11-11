//! Which files of a repository `kinetic pull` downloads.

use std::path::Path;

use crate::library::shard;

/// One file of a repository, as the Hugging Face API lists it.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RepoFile {
    pub path: String,
    pub size: u64,
    /// The SHA256 of a file kept in LFS, as GGUF files are.
    pub sha256: Option<String>,
}

/// The quantization llama.cpp picks when none is named.
const DEFAULT_QUANT: &str = "Q4_K_M";

/// What `kinetic pull` picks among by itself, smallest first: below Q4_K_M
/// answers get noticeably worse, past Q8_0 a model only gets slower.
const AUTO_QUANTS: [&str; 4] = ["Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0"];

/// The largest of Q4_K_M, Q5_K_M, Q6_K and Q8_0 the repository has whose
/// model fits in `room` bytes, and whether it fits; Q4_K_M, not fitting,
/// when none does. `None` when the repository has no Q4_K_M.
pub fn fitting_quant(files: &[RepoFile], room: u64) -> Option<(&'static str, bool)> {
    let size = |q: &str| -> u64 {
        files
            .iter()
            .filter(|f| {
                let p = f.path.to_ascii_lowercase();
                p.ends_with(".gguf") && !p.contains("mmproj") && names_quant(&f.path, q)
            })
            .map(|f| f.size)
            .sum()
    };
    if size(DEFAULT_QUANT) == 0 {
        return None;
    }
    let fitting = AUTO_QUANTS
        .iter()
        .rev()
        .find(|q| (1..=room).contains(&size(q)));
    Some(fitting.map_or((DEFAULT_QUANT, false), |q| (*q, true)))
}

/// The model files to fetch, every part of a split one, and its projector
/// unless `projector` is false.
pub fn pick(
    files: &[RepoFile],
    quant: Option<&str>,
    file: Option<&str>,
    projector: bool,
) -> Result<Vec<RepoFile>, String> {
    let ggufs: Vec<&RepoFile> = files
        .iter()
        .filter(|f| f.path.to_ascii_lowercase().ends_with(".gguf"))
        .collect();
    let is_projector = |f: &RepoFile| f.path.to_ascii_lowercase().contains("mmproj");
    // a split model counts once, by its first part
    let models: Vec<&RepoFile> = ggufs
        .iter()
        .copied()
        .filter(|f| !is_projector(f) && shard(Path::new(&f.path)).is_none_or(|(n, _)| n == 1))
        .collect();
    if models.is_empty() {
        return Err("the repository has no GGUF model files".into());
    }
    let chosen: Vec<&RepoFile> = match (file, quant) {
        (Some(name), _) => models
            .iter()
            .copied()
            .filter(|f| f.path == name || file_name(&f.path) == name)
            .collect(),
        (None, Some(q)) => models
            .iter()
            .copied()
            .filter(|f| names_quant(&f.path, q))
            .collect(),
        (None, None) if models.len() == 1 => models.clone(),
        (None, None) => models
            .iter()
            .copied()
            .filter(|f| names_quant(&f.path, DEFAULT_QUANT))
            .collect(),
    };
    let first = match chosen[..] {
        [one] => one,
        _ => {
            let list: Vec<&str> = models.iter().map(|f| f.path.as_str()).collect();
            let wanted = match (file, quant) {
                (Some(f), _) => format!("--file {f}"),
                (None, Some(q)) => format!("quantization {q}"),
                (None, None) => "no quantization".into(),
            };
            let verb = if chosen.is_empty() {
                "matches no file"
            } else {
                "matches several files"
            };
            return Err(format!(
                "{wanted} {verb}; name one with <org>/<repo>:<quant> or --file:\n  {}",
                list.join("\n  ")
            ));
        }
    };
    let mut picked = parts(&ggufs, first);
    if projector {
        let projectors: Vec<&RepoFile> =
            ggufs.iter().copied().filter(|f| is_projector(f)).collect();
        // f16 is what llama.cpp's own -hf picks; bf16 and f32 are larger or less supported
        let best = projectors
            .iter()
            .find(|f| {
                let p = f.path.to_ascii_lowercase();
                p.contains("f16") && !p.contains("bf16")
            })
            .or(projectors.first());
        picked.extend(best.map(|f| (*f).clone()));
    }
    Ok(picked)
}

/// `first` and, when it is the first part of a split model, every part.
fn parts(ggufs: &[&RepoFile], first: &RepoFile) -> Vec<RepoFile> {
    let Some((_, count)) = shard(Path::new(&first.path)) else {
        return vec![first.clone()];
    };
    let prefix = &first.path[..first.path.len() - "00001-of-00001.gguf".len()];
    (1..=count)
        .filter_map(|i| {
            let name = format!("{prefix}{i:05}-of-{count:05}.gguf");
            ggufs.iter().find(|f| f.path == name).map(|f| (*f).clone())
        })
        .collect()
}

fn file_name(path: &str) -> &str {
    path.rsplit('/').next().unwrap_or(path)
}

/// Whether the file name holds `quant` as a whole word: Q4_K matches
/// `x-Q4_K.gguf` but not `x-Q4_K_M.gguf`.
fn names_quant(path: &str, quant: &str) -> bool {
    let name = file_name(path).to_ascii_lowercase();
    let quant = quant.to_ascii_lowercase();
    let word = |c: Option<char>| c.is_none_or(|c| !c.is_ascii_alphanumeric() && c != '_');
    name.match_indices(&quant).any(|(i, m)| {
        word(name[..i].chars().next_back()) && word(name[i + m.len()..].chars().next())
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn repo(names: &[&str]) -> Vec<RepoFile> {
        names
            .iter()
            .map(|n| RepoFile {
                path: n.to_string(),
                size: 1,
                sha256: None,
            })
            .collect()
    }

    fn paths(files: &[RepoFile]) -> Vec<&str> {
        files.iter().map(|f| f.path.as_str()).collect()
    }

    #[test]
    fn picks_the_named_quant_and_its_projector() {
        let files = repo(&[
            "README.md",
            "gemma-3-4b-it-Q4_K_M.gguf",
            "gemma-3-4b-it-Q4_K_S.gguf",
            "gemma-3-4b-it-Q8_0.gguf",
            "mmproj-model-bf16.gguf",
            "mmproj-model-f16.gguf",
        ]);
        let got = pick(&files, Some("q8_0"), None, true).unwrap();
        assert_eq!(
            paths(&got),
            ["gemma-3-4b-it-Q8_0.gguf", "mmproj-model-f16.gguf"]
        );
        let got = pick(&files, None, None, false).unwrap();
        assert_eq!(paths(&got), ["gemma-3-4b-it-Q4_K_M.gguf"]);
        let err = pick(&files, Some("Q4_K"), None, false).unwrap_err();
        assert!(
            err.contains("matches no file") && err.contains("Q4_K_S"),
            "{err}"
        );
        let got = pick(&files, None, Some("gemma-3-4b-it-Q4_K_S.gguf"), false).unwrap();
        assert_eq!(paths(&got), ["gemma-3-4b-it-Q4_K_S.gguf"]);
    }

    #[test]
    fn takes_every_part_of_a_split_model() {
        let files = repo(&[
            "Q4_K_M/big-Q4_K_M-00001-of-00002.gguf",
            "Q4_K_M/big-Q4_K_M-00002-of-00002.gguf",
            "Q8_0/big-Q8_0-00001-of-00002.gguf",
            "Q8_0/big-Q8_0-00002-of-00002.gguf",
        ]);
        let got = pick(&files, Some("Q8_0"), None, true).unwrap();
        assert_eq!(
            paths(&got),
            [
                "Q8_0/big-Q8_0-00001-of-00002.gguf",
                "Q8_0/big-Q8_0-00002-of-00002.gguf"
            ]
        );
    }

    #[test]
    fn picks_the_largest_quant_that_fits() {
        let sized = |list: &[(&str, u64)]| -> Vec<RepoFile> {
            list.iter()
                .map(|&(n, size)| RepoFile {
                    path: n.into(),
                    size,
                    sha256: None,
                })
                .collect()
        };
        let files = sized(&[
            ("m-Q4_K_M.gguf", 25),
            ("m-Q6_K.gguf", 36),
            ("m-Q8_0.gguf", 46),
            ("m-BF16.gguf", 86),
            ("mmproj-Q8_0.gguf", 6),
        ]);
        assert_eq!(fitting_quant(&files, 100), Some(("Q8_0", true)));
        assert_eq!(fitting_quant(&files, 40), Some(("Q6_K", true)));
        assert_eq!(fitting_quant(&files, 10), Some(("Q4_K_M", false)));
        assert_eq!(fitting_quant(&sized(&[("m-Q8_0.gguf", 1)]), 100), None);
    }

    #[test]
    fn a_lone_model_needs_no_quant() {
        let files = repo(&["tiny.gguf"]);
        assert_eq!(
            paths(&pick(&files, None, None, true).unwrap()),
            ["tiny.gguf"]
        );
        assert!(pick(&repo(&["a.safetensors"]), None, None, true).is_err());
    }
}
