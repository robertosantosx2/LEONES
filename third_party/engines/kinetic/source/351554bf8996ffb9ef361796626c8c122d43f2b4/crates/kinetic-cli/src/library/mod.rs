//! Models already on this computer, in Kinetic's own folder and in the
//! stores of Ollama, LM Studio, Hugging Face and llama.cpp, found by name.

mod folder;
mod header;
mod ollama;
mod roots;

use std::collections::HashSet;
use std::io::Write;
use std::path::{Path, PathBuf};

pub use header::{shard, Header};
pub use roots::kinetic_dir;

use crate::Result;

/// Who put a model where it was found.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Store {
    Kinetic,
    Ollama,
    LmStudio,
    HuggingFace,
    LlamaCpp,
    Folder,
}

impl Store {
    fn label(self) -> &'static str {
        match self {
            Store::Kinetic => "kinetic",
            Store::Ollama => "ollama",
            Store::LmStudio => "lm studio",
            Store::HuggingFace => "hugging face",
            Store::LlamaCpp => "llama.cpp",
            Store::Folder => "folder",
        }
    }
}

/// A model found on this computer.
pub struct Local {
    /// The name it is asked for by, as its store names it.
    pub name: String,
    pub path: PathBuf,
    /// The vision projector stored with it.
    pub projector: Option<PathBuf>,
    pub store: Store,
    /// Its header, or why it could not be read.
    pub header: std::result::Result<Header, String>,
}

/// Every model in every store, each file once.
pub fn discover() -> Vec<Local> {
    discover_in(&roots::all())
}

/// The models in `dir` and its subfolders.
pub fn in_folder(dir: &Path) -> Vec<Local> {
    discover_in(&[(Store::Folder, dir.to_path_buf())])
}

fn discover_in(roots: &[(Store, PathBuf)]) -> Vec<Local> {
    let mut found = Vec::new();
    for (store, root) in roots {
        match store {
            Store::Ollama => found.extend(ollama::scan(root).into_iter().map(|e| Local {
                header: Header::read(&e.model),
                name: e.name,
                path: e.model,
                projector: e.projector,
                store: Store::Ollama,
            })),
            Store::HuggingFace => found.extend(from_groups(folder::hf_cache(root), *store)),
            Store::Kinetic | Store::LmStudio => {
                found.extend(from_groups(folder::repos(root), *store))
            }
            Store::LlamaCpp | Store::Folder => {
                found.extend(from_groups(folder::flat(root), *store))
            }
        }
    }
    // LM Studio and the Hugging Face cache link files they share
    let mut seen = HashSet::new();
    found.retain(|m| seen.insert(m.path.canonicalize().unwrap_or_else(|_| m.path.clone())));
    found
}

fn from_groups(groups: Vec<folder::Group>, store: Store) -> Vec<Local> {
    let mut found = Vec::new();
    for group in groups {
        let (projectors, models): (Vec<_>, Vec<_>) = group
            .files
            .into_iter()
            .filter(|f| header::shard(f).is_none_or(|(n, _)| n == 1))
            .map(|f| {
                let h = Header::read(&f);
                (f, h)
            })
            .partition(|(_, h)| h.as_ref().is_ok_and(Header::is_projector));
        let several = models.len() > 1;
        for (path, header) in models {
            let stem = header::model_stem(&path);
            let (name, projector) = match &group.repo {
                Some(repo) => {
                    let name = match (&header, several) {
                        (Ok(h), true) => format!("{repo}:{}", h.quant),
                        (Err(_), true) => format!("{repo}:{stem}"),
                        (_, false) => repo.clone(),
                    };
                    (name, projectors.first().map(|(p, _)| p.clone()))
                }
                None => {
                    let projector = projector_for(&stem, projectors.iter().map(|(p, _)| p));
                    (stem, projector)
                }
            };
            found.push(Local {
                name,
                path,
                projector,
                store,
                header,
            });
        }
    }
    found
}

/// The projector among `projectors` whose file name shares the longest start
/// with the model's `stem`, as `gemma-4-E2B-it-mmproj.gguf` does with
/// `gemma-4-E2B_q4_0-it`; none when no name shares at least 8 characters.
fn projector_for<'a>(stem: &str, projectors: impl Iterator<Item = &'a PathBuf>) -> Option<PathBuf> {
    let shared = |p: &Path| {
        let name = p
            .file_name()
            .map_or(String::new(), |n| n.to_string_lossy().to_lowercase());
        name.chars()
            .zip(stem.to_lowercase().chars())
            .take_while(|(a, b)| a == b)
            .count()
    };
    projectors
        .map(|p| (shared(p), p))
        .filter(|&(n, _)| n >= 8)
        .max_by_key(|&(n, _)| n)
        .map(|(_, p)| p.clone())
}

/// The model `arg` names: a file, or the name of a model found on this
/// computer.
pub fn locate(arg: &Path) -> Result<Local> {
    if arg.is_file() {
        let stem = header::model_stem(arg);
        let siblings = arg
            .parent()
            .and_then(|d| std::fs::read_dir(d).ok())
            .into_iter()
            .flatten()
            .filter_map(|e| e.ok().map(|e| e.path()))
            .filter(|p| p != arg && p.extension().is_some_and(|x| x == "gguf"))
            .filter(|p| Header::read(p).is_ok_and(|h| h.is_projector()))
            .collect::<Vec<_>>();
        return Ok(Local {
            projector: projector_for(&stem, siblings.iter()),
            name: stem,
            path: arg.to_path_buf(),
            store: Store::Folder,
            header: Header::read(arg),
        });
    }
    let looks_like_file = arg
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("gguf") || e.eq_ignore_ascii_case("ktc"));
    if looks_like_file {
        return Err(format!("{}: no such file", arg.display()).into());
    }
    pick(discover(), &arg.to_string_lossy())
}

fn pick(models: Vec<Local>, query: &str) -> Result<Local> {
    match matches(&models, query)[..] {
        [i] => return Ok(models.into_iter().nth(i).expect("index from matches")),
        [] => {}
        ref several => {
            let names: Vec<&str> = several.iter().map(|&i| models[i].name.as_str()).collect();
            return Err(format!("{query} could mean {}", names.join(", ")).into());
        }
    }
    let close = close_matches(&models, query);
    let mut msg = format!("no model file or model called {query} on this computer");
    if !close.is_empty() {
        msg += &format!("; did you mean {}?", close.join(", "));
    }
    msg += "\n`kinetic models` lists the models found; `kinetic pull <org>/<repo>` downloads one from Hugging Face";
    Err(msg.into())
}

/// The models `query` names: the exact name, then its `:latest` tag as
/// Ollama reads a bare name, then every tag or quant of it.
fn matches(models: &[Local], query: &str) -> Vec<usize> {
    let find = |f: &dyn Fn(&str) -> bool| -> Vec<usize> {
        (0..models.len())
            .filter(|&i| f(&models[i].name.to_lowercase()))
            .collect()
    };
    let query = query.to_lowercase();
    let exact = find(&|n| n == query);
    if !exact.is_empty() || query.contains(':') {
        return dedup_names(models, exact);
    }
    let latest = find(&|n| n == format!("{query}:latest"));
    if !latest.is_empty() {
        return latest;
    }
    let tagged = dedup_names(models, find(&|n| n.starts_with(&format!("{query}:"))));
    if !tagged.is_empty() {
        return tagged;
    }
    // a pulled model is named by its repository, but people type the file name
    (0..models.len())
        .filter(|&i| header::model_stem(&models[i].path).to_lowercase() == query)
        .collect()
}

/// One model per name: the first store found wins, as on `PATH`.
fn dedup_names(models: &[Local], found: Vec<usize>) -> Vec<usize> {
    let mut seen = HashSet::new();
    found
        .into_iter()
        .filter(|&i| seen.insert(models[i].name.to_lowercase()))
        .collect()
}

/// Names that resemble `query`, best first.
fn close_matches(models: &[Local], query: &str) -> Vec<String> {
    let query = query.to_lowercase();
    let base = query.split(':').next().unwrap_or(&query).to_owned();
    let mut scored: Vec<(usize, &str)> = models
        .iter()
        .filter_map(|m| {
            let name = m.name.to_lowercase();
            let name_base = name.split(':').next().unwrap_or(&name);
            let distance = strsim::levenshtein(&base, name_base);
            let related = name.contains(&base) || base.contains(name_base);
            (related || distance <= (base.len() / 3).max(2)).then_some((distance, m.name.as_str()))
        })
        .collect();
    scored.sort();
    let mut names: Vec<String> = scored.iter().map(|(_, n)| n.to_string()).collect();
    names.dedup();
    names.truncate(5);
    names
}

/// `kinetic models`: the table of models found.
pub fn list() -> Result<()> {
    let models = discover();
    let mut out = std::io::stdout().lock();
    if models.is_empty() {
        writeln!(
            out,
            "No models found. Kinetic looks in its own folder, Ollama, LM Studio, and the Hugging Face and llama.cpp caches."
        )?;
        return Ok(());
    }
    let width = models
        .iter()
        .map(|m| m.name.len())
        .max()
        .unwrap_or(4)
        .max(4);
    writeln!(
        out,
        "{:<width$}  {:>9}  {:<8}  {:<14}  {:<22}  FROM",
        "NAME", "SIZE", "QUANT", "ARCH", "RUNS ON KINETIC"
    )?;
    for m in &models {
        let (size, quant, arch, support) = match &m.header {
            Ok(h) => (
                format!("{:.2} GiB", h.size as f64 / (1u64 << 30) as f64),
                h.quant.clone(),
                h.arch.clone(),
                h.support(),
            ),
            Err(_) => ("?".into(), "?".into(), "?".into(), "no, unreadable".into()),
        };
        let vision = if m.projector.is_some() {
            ", vision"
        } else {
            ""
        };
        writeln!(
            out,
            "{:<width$}  {size:>9}  {quant:<8}  {arch:<14}  {:<22}  {}",
            m.name,
            format!("{support}{vision}"),
            m.store.label()
        )?;
    }
    Ok(())
}

#[cfg(test)]
mod tests;
