//! `kinetic` alone in a terminal: models that run well on this computer,
//! one key to pick one, the download if it is not here yet, then a chat.

use std::io::Write;
use std::path::PathBuf;

use crate::fit::Speeds;
use crate::library::{self, Local};
use crate::system::{self, Gpu, Machine};
use crate::{console, pull, Result};

const GIB: f64 = (1u64 << 30) as f64;
/// Most models offered.
const MOST: usize = 3;
/// Slowest decode, in tokens per second, a model on disk is offered at.
const READABLE: f64 = 8.0;

/// A model worth downloading.
struct Suggestion {
    name: &'static str,
    /// What `kinetic pull` takes.
    spec: &'static str,
    /// Bytes of the file, as Hugging Face lists it.
    size: u64,
    /// GPU memory it is offered with; twice this in free RAM does too.
    memory: u64,
}

const SUGGESTIONS: [Suggestion; 2] = [
    Suggestion {
        name: "Qwen3.5 4B",
        spec: "unsloth/Qwen3.5-4B-MTP-GGUF:Q4_K_M",
        size: 2_834_975_040,
        memory: 4 << 30,
    },
    Suggestion {
        name: "LFM3 1.7B",
        spec: "LiquidAI/LFM3-1.7B-GGUF:Q4_K_M",
        size: 1_099_627_808,
        memory: 0,
    },
];

enum Source {
    Disk(PathBuf),
    Hub(&'static str),
}

struct Choice {
    name: String,
    size: u64,
    source: Source,
    /// Where it runs and its expected decode speed range.
    runs: (&'static str, f64, f64),
}

/// Offers models and returns the file of the one picked, downloaded if it
/// was not here; `None` when the user leaves instead.
pub fn run() -> Result<Option<PathBuf>> {
    println!("Welcome to Kinetic. Checking this computer...");
    let machine = system::machine();
    let (gpus, _) = system::gpus();
    let speeds = Speeds::measure(&gpus);
    println!("{}", describe(&machine, &gpus));
    let gpu_memory = gpus.iter().map(|g| g.memory_total).max().unwrap_or(0);
    let mut choices = choices(
        &speeds,
        gpu_memory,
        machine.ram_available,
        library::discover(),
    );

    let width = choices.iter().map(|c| c.name.len()).max().unwrap_or(0);
    println!("\nPick a model to chat with:");
    for (i, c) in choices.iter().enumerate() {
        let (on, lo, hi) = c.runs;
        let from = match c.source {
            Source::Disk(_) => "on this computer",
            Source::Hub(_) => "download",
        };
        println!(
            "  {}  {:<width$}  {:>5.2} GiB  {from:<16}  {on}, {lo:.0}-{hi:.0} tokens/s",
            i + 1,
            c.name,
            c.size as f64 / GIB
        );
    }
    print!("Press 1-{}, Enter for 1, or q to quit: ", choices.len());
    std::io::stdout().flush()?;
    let picked = loop {
        match console::read_key().map(char::from) {
            None | Some('\u{3}' | '\u{1b}' | 'q' | 'Q') => {
                println!();
                return Ok(None);
            }
            Some('\r' | '\n') => break 0,
            Some(k) => match k.to_digit(10) {
                Some(n @ 1..) if (n as usize) <= choices.len() => break n as usize - 1,
                _ => {}
            },
        }
    };
    let choice = choices.swap_remove(picked);
    println!("{}\n", picked + 1);
    match choice.source {
        Source::Disk(path) => {
            println!(
                "Next time, `kinetic chat {}` opens it directly.",
                choice.name
            );
            Ok(Some(path))
        }
        Source::Hub(spec) => {
            println!("Downloading {}; this happens only once.", choice.name);
            let path = pull::run(&pull::Pull {
                spec,
                file: None,
                projector: false,
                dir: None,
            })?;
            Ok(Some(path))
        }
    }
}

fn describe(m: &Machine, gpus: &[Gpu]) -> String {
    let gib = |b: u64| b as f64 / GIB;
    let gpu = match gpus.iter().max_by_key(|g| g.memory_total) {
        Some(g) => match g.memory_free {
            Some(free) => format!("{} ({:.1} GiB free)", g.name, gib(free)),
            None => format!("{} ({:.1} GiB)", g.name, gib(g.memory_total)),
        },
        None => "no GPU, so models run on the processor".into(),
    };
    format!(
        "{}, {:.0} GiB memory ({:.1} GiB free), {gpu}",
        m.cpu,
        gib(m.ram_total),
        gib(m.ram_available)
    )
}

/// The models to offer: chat models on disk that run at a readable speed,
/// largest first, then suggestions this computer has the memory for and
/// does not have yet.
fn choices(speeds: &Speeds, gpu_memory: u64, ram_free: u64, found: Vec<Local>) -> Vec<Choice> {
    let mut disk: Vec<Choice> = found
        .into_iter()
        .filter_map(|l| {
            let h = l.header.as_ref().ok()?;
            let chats = h.support() == "yes"
                && !h.is_projector()
                && !crate::is_embedding_model(&l.path).unwrap_or(true);
            let runs = chats.then(|| speeds.file(&l.path).ok())??;
            let size = h.size;
            ((runs.1 + runs.2) / 2.0 >= READABLE).then_some(Choice {
                name: l.name,
                size,
                source: Source::Disk(l.path),
                runs,
            })
        })
        .collect();
    disk.sort_by_key(|c| std::cmp::Reverse(c.size));
    let fresh = suggestions(gpu_memory, ram_free)
        // the same file under another name is already here
        .filter(|s| !disk.iter().any(|c| c.size == s.size))
        .map(|s| Choice {
            name: format!(
                "{} ({})",
                s.name,
                s.spec.split(':').next().unwrap_or(s.spec)
            ),
            size: s.size,
            source: Source::Hub(s.spec),
            runs: speeds.dense(s.size),
        })
        .collect::<Vec<_>>();
    disk.into_iter().chain(fresh).take(MOST).collect()
}

fn suggestions(gpu_memory: u64, ram_free: u64) -> impl Iterator<Item = &'static Suggestion> {
    SUGGESTIONS
        .iter()
        .filter(move |s| gpu_memory >= s.memory || ram_free >= 2 * s.memory)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn names(gpu: u64, ram: u64) -> Vec<&'static str> {
        suggestions(gpu, ram).map(|s| s.name).collect()
    }

    #[test]
    fn suggests_what_the_memory_holds() {
        assert_eq!(names(6 << 30, 4 << 30), ["Qwen3.5 4B", "LFM3 1.7B"]);
        assert_eq!(names(0, 12 << 30), ["Qwen3.5 4B", "LFM3 1.7B"]);
        assert_eq!(names(2 << 30, 4 << 30), ["LFM3 1.7B"]);
    }
}
