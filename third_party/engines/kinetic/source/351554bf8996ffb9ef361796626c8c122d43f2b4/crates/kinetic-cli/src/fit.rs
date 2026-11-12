//! `kinetic fit`: where each model would run on this computer, and roughly
//! how fast it would write.

use std::io::Write;
use std::path::Path;

use kinetic_gguf::{Gguf, GgufFile};

use crate::library::{self, Local};
use crate::system::{self, Gpu};
use crate::Result;

const GIB: f64 = (1u64 << 30) as f64;
/// GPU memory kept free for the cache and the kernels' scratch.
const HEADROOM: u64 = 1 << 30;
/// Decode reaches this share of memory bandwidth, low to high; Kinetic
/// measured 0.70-0.77 on an RTX 3060 and ~0.6 on DDR5.
const GPU_EFFICIENCY: (f64, f64) = (0.55, 0.85);
const CPU_EFFICIENCY: (f64, f64) = (0.45, 0.75);

/// Smallest context [`gpu_context`] shrinks to.
const MIN_CONTEXT: usize = 4096;

/// The bytes a model reads per generated token.
#[derive(Debug, PartialEq)]
pub struct Weights {
    /// Everything but the experts of a mixture-of-experts model.
    dense: u64,
    /// All experts.
    experts: u64,
    /// Experts' bytes one token reads.
    active_experts: u64,
}

impl Weights {
    fn read(path: &Path) -> Result<Weights> {
        Ok(Weights::of(GgufFile::open(path)?.header()))
    }

    pub fn of(g: &Gguf) -> Weights {
        let tied = g.tensor("output.weight").is_none();
        let (mut dense, mut experts) = (0, 0);
        for t in &g.tensors {
            if t.name.contains("_exps") {
                experts += t.size;
            } else if t.name != "token_embd.weight" || tied {
                // one row of the embeddings is read per token, unless they double as the output
                dense += t.size;
            }
        }
        let n = |key| g.arch_key(key).and_then(|v| v.as_u64()).unwrap_or(0);
        let (count, used) = (n("expert_count"), n("expert_used_count"));
        let active_experts = (experts * used).checked_div(count).unwrap_or(experts);
        Weights {
            dense,
            experts,
            active_experts,
        }
    }

    pub fn total(&self) -> u64 {
        self.dense + self.experts
    }

    pub fn has_experts(&self) -> bool {
        self.experts > 0
    }
}

/// What decode speed depends on here: the CUDA GPU with the most free
/// memory, as (free bytes, bandwidth), and the RAM's measured bandwidth.
pub struct Speeds {
    gpu: Option<(u64, f64)>,
    cpu_bandwidth: f64,
}

impl Speeds {
    pub fn measure(gpus: &[Gpu]) -> Speeds {
        let gpu = best_cuda(gpus)
            .and_then(|g| Some((g.memory_free.unwrap_or(g.memory_total), g.bandwidth?)));
        Speeds {
            gpu,
            cpu_bandwidth: system::memory_bandwidth(),
        }
    }

    /// Where a model of `bytes`, none of them experts, runs and its decode
    /// speed range in tokens per second.
    pub fn dense(&self, bytes: u64) -> (&'static str, f64, f64) {
        let w = Weights {
            dense: bytes,
            experts: 0,
            active_experts: 0,
        };
        place(&w, self.gpu, self.cpu_bandwidth)
    }

    /// As [`Speeds::dense`], for the model file at `path`.
    pub fn file(&self, path: &Path) -> Result<(&'static str, f64, f64)> {
        Ok(place(&Weights::read(path)?, self.gpu, self.cpu_bandwidth))
    }
}

fn best_cuda(gpus: &[Gpu]) -> Option<&Gpu> {
    gpus.iter()
        .filter(|g| g.api == "CUDA")
        .max_by_key(|g| g.memory_free.unwrap_or(g.memory_total))
}

/// Bytes a model may take here with room left for its context, and where:
/// the free memory of the CUDA GPU, else half the available RAM, as the
/// rest of the system needs some too.
pub fn room(gpus: &[Gpu]) -> (u64, &'static str) {
    match best_cuda(gpus).and_then(|g| g.memory_free) {
        Some(free) => (free.saturating_sub(HEADROOM), "on the GPU"),
        None => (system::machine().ram_available / 2, "in memory"),
    }
}

/// The context to use on a GPU with `free` bytes when `wanted` positions do
/// not fit beside `weights`: the largest multiple of 1024, at least 4096,
/// whose cache of `cache(n)` bytes does. `None` when `wanted` fits, or when
/// not even 4096 does and only moving layers off the GPU helps.
pub fn gpu_context(
    wanted: usize,
    free: u64,
    weights: u64,
    cache: impl Fn(usize) -> u64,
) -> Option<usize> {
    let room = free.checked_sub(weights + HEADROOM)?;
    if wanted <= MIN_CONTEXT || cache(wanted) <= room {
        return None;
    }
    (MIN_CONTEXT / 1024..wanted.div_ceil(1024))
        .rev()
        .map(|k| k * 1024)
        .find(|&n| cache(n) <= room)
}

/// Where a model goes and the decode speed range it would reach.
fn place(w: &Weights, gpu: Option<(u64, f64)>, cpu_bandwidth: f64) -> (&'static str, f64, f64) {
    // everything fits somewhere; the question is only how fast
    let per_token = (w.dense + w.active_experts) as f64;
    // seconds per token at the GPU's and the CPU's efficiency, low then high
    let speeds = |on, seconds: &dyn Fn(f64, f64) -> f64| {
        let low = 1.0 / seconds(GPU_EFFICIENCY.0, CPU_EFFICIENCY.0);
        let high = 1.0 / seconds(GPU_EFFICIENCY.1, CPU_EFFICIENCY.1);
        (on, low, high)
    };
    if let Some((free, bandwidth)) = gpu {
        if w.dense + w.experts + HEADROOM <= free {
            return speeds("GPU", &|g, _| per_token / (bandwidth * g));
        }
        if w.experts > 0 && w.dense + HEADROOM <= free {
            return speeds("GPU, experts on CPU", &|g, c| {
                w.dense as f64 / (bandwidth * g) + w.active_experts as f64 / (cpu_bandwidth * c)
            });
        }
    }
    speeds("CPU", &|_, c| per_token / (cpu_bandwidth * c))
}

pub fn run(target: Option<&Path>) -> Result<()> {
    let models: Vec<Local> = match target {
        None => library::discover(),
        Some(dir) if dir.is_dir() => library::in_folder(dir),
        Some(model) => vec![library::locate(model)?],
    };
    let machine = system::machine();
    let (gpus, _) = system::gpus();
    let speeds = Speeds::measure(&gpus);
    let cuda = best_cuda(&gpus);

    let mut out = std::io::stdout().lock();
    if models.is_empty() {
        writeln!(out, "No models found.")?;
        return Ok(());
    }
    let width = models
        .iter()
        .map(|m| m.name.len())
        .max()
        .unwrap_or(5)
        .max(5);
    writeln!(
        out,
        "{:<width$}  {:>9}  {:<20}  EXPECTED DECODE",
        "MODEL", "SIZE", "RUNS ON"
    )?;
    for m in &models {
        let support = m.header.as_ref().map(|h| h.support());
        let line = match (support.as_deref(), Weights::read(&m.path)) {
            (Err(e), _) => format!("{:>9}  unreadable: {e}", ""),
            (Ok(why), _) if why != "yes" => {
                let arch = m.header.as_ref().map_or("", |h| h.arch.as_str());
                let why = why.strip_prefix("no, ").unwrap_or(arch);
                format!("{:>9}  not supported yet: {why}", "")
            }
            (_, Err(e)) => format!("{:>9}  unreadable: {e}", ""),
            (_, Ok(w)) => {
                let (on, lo, hi) = place(&w, speeds.gpu, speeds.cpu_bandwidth);
                let size = (w.dense + w.experts) as f64 / GIB;
                let mut note = String::new();
                if on == "CPU" && w.dense + w.experts > machine.ram_available {
                    note = ", more than the free memory: reads from disk, much slower".into();
                }
                format!("{size:>5.2} GiB  {on:<20}  {lo:.0}-{hi:.0} t/s{note}",)
            }
        };
        writeln!(out, "{:<width$}  {line}", m.name)?;
    }
    let gpu_note = match (cuda, speeds.gpu) {
        (Some(g), Some((free, bw))) => format!(
            "{} with {:.1} GiB free at {:.0} GB/s nominal",
            g.name,
            free as f64 / GIB,
            bw / 1e9
        ),
        _ => "no CUDA GPU".into(),
    };
    writeln!(out)?;
    writeln!(
        out,
        "Estimates from each model's size and memory bandwidth ({gpu_note}; RAM {:.0} GB/s measured), not measurements; `kinetic bench` measures.",
        speeds.cpu_bandwidth / 1e9
    )?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    const GB: u64 = 1_000_000_000;

    #[test]
    fn dense_models_fit_or_fall_back_to_the_cpu() {
        let w = Weights {
            dense: 2 * GB,
            experts: 0,
            active_experts: 0,
        };
        let gpu = Some((6 * GB, 300e9));
        let (on, lo, hi) = place(&w, gpu, 50e9);
        assert_eq!(on, "GPU");
        assert!(
            (lo - 82.5).abs() < 0.1 && (hi - 127.5).abs() < 0.1,
            "{lo} {hi}"
        );
        let (on, lo, _) = place(&w, Some((2 * GB, 300e9)), 50e9);
        assert_eq!(on, "CPU");
        assert!((lo - 11.25).abs() < 0.01, "{lo}");
    }

    #[test]
    fn large_mixtures_keep_experts_on_the_cpu() {
        let w = Weights {
            dense: GB,
            experts: 12 * GB,
            active_experts: GB,
        };
        let (on, lo, hi) = place(&w, Some((6 * GB, 300e9)), 50e9);
        assert_eq!(on, "GPU, experts on CPU");
        // 1 GB at 165 GB/s plus 1 GB at 22.5 GB/s
        assert!((lo - 1.0 / (1.0 / 165.0 + 1.0 / 22.5)).abs() < 0.01, "{lo}");
        assert!(hi > lo);
        assert_eq!(place(&w, None, 50e9).0, "CPU");
    }

    #[test]
    fn context_shrinks_to_what_the_gpu_holds() {
        // 1 MB fixed state plus 100 KB a position
        let cache = |n: usize| 1_000_000 + 100_000 * n as u64;
        let free = 6 * GB;
        let weights = free - HEADROOM - cache(10_000);
        assert_eq!(gpu_context(32768, free, weights, cache), Some(9216));
        assert_eq!(gpu_context(9216, free, weights, cache), None);
        assert_eq!(gpu_context(32768, free, weights + cache(8000), cache), None);
        assert_eq!(gpu_context(32768, GB, weights, cache), None);
    }
}
