//! `kinetic doctor`: what this computer offers Kinetic, and what to fix.

use std::io::Write;

use crate::library;
use crate::system::{self, Gpu};
use crate::Result;

const GIB: f64 = (1u64 << 30) as f64;
/// What NVIDIA GPUs have in their names.
const NVIDIA: &str = "NVIDIA";

pub fn run() -> Result<()> {
    let m = system::machine();
    let bandwidth = system::memory_bandwidth();
    let (gpus, notes) = system::gpus();
    let models = library::discover();
    let dir = library::kinetic_dir();
    let free = dir.as_deref().and_then(system::disk_free);

    let mut out = std::io::stdout().lock();
    let gib = |b: u64| b as f64 / GIB;
    let yes = |b: bool| if b { "yes" } else { "NO" };
    writeln!(out, "Kinetic {}", env!("CARGO_PKG_VERSION"))?;
    writeln!(out, "  system   {}", m.os)?;
    writeln!(
        out,
        "  cpu      {}, {} threads, AVX2 {}, FMA {}, F16C {}",
        m.cpu,
        m.threads,
        yes(m.avx2),
        yes(m.fma),
        yes(m.f16c)
    )?;
    writeln!(
        out,
        "  memory   {:.1} GiB, {:.1} GiB available, reads at {:.0} GB/s (measured)",
        gib(m.ram_total),
        gib(m.ram_available),
        bandwidth / 1e9
    )?;
    for g in &gpus {
        writeln!(out, "  gpu      {}", describe(g))?;
    }
    for n in &notes {
        writeln!(out, "  gpu      {n}")?;
    }
    let supported = models
        .iter()
        .filter(|l| l.header.as_ref().is_ok_and(|h| h.support() == "yes"))
        .count();
    writeln!(
        out,
        "  models   {} found, {supported} that Kinetic runs (`kinetic models` lists them)",
        models.len()
    )?;
    if let (Some(dir), Some(free)) = (&dir, free) {
        // the home folder as ~, so output pasted into an issue names no user
        let shown = std::env::home_dir()
            .and_then(|home| dir.strip_prefix(home).ok())
            .map_or_else(|| dir.clone(), |rest| std::path::Path::new("~").join(rest));
        writeln!(
            out,
            "  disk     {:.1} GiB free for {}",
            gib(free),
            shown.display()
        )?;
    }

    let mut fixes = Vec::new();
    if !(m.avx2 && m.fma && m.f16c) {
        fixes.push("this CPU lacks AVX2, FMA or F16C, which Kinetic's CPU kernels use; expect slow CPU runs".to_owned());
    }
    let cuda = gpus.iter().any(|g| g.api == "CUDA");
    let nvidia_seen = gpus.iter().any(|g| g.name.contains(NVIDIA));
    if !cuda && nvidia_seen {
        let why = notes
            .iter()
            .find(|n| n.starts_with("CUDA"))
            .cloned()
            .unwrap_or_default();
        fixes.push(format!(
            "an NVIDIA GPU is present but CUDA is not usable ({why}); install or update the NVIDIA driver"
        ));
    }
    if gpus.is_empty() {
        fixes.push("no GPU found; models run on the CPU, so prefer small ones (`kinetic fit` shows what runs well)".into());
    }
    for g in &gpus {
        if let Some(problem) = &g.problem {
            fixes.push(format!(
                "{} through {}: {problem}; update its driver",
                g.name, g.api
            ));
        }
        if let Some(free) = g.memory_free {
            if g.memory_total >= 4 << 30 && free < 1 << 30 {
                fixes.push(format!(
                    "only {:.1} GiB of {} memory is free; close programs that use the GPU",
                    gib(free),
                    g.name
                ));
            }
        }
    }
    if m.ram_available > 0 && m.ram_available < 4 << 30 {
        fixes.push(format!(
            "only {:.1} GiB of memory is available; close programs before loading a model",
            gib(m.ram_available)
        ));
    }
    if free.is_some_and(|f| f < 10 << 30) {
        fixes.push("under 10 GiB of disk is free where models are kept".into());
    }
    if supported == 0 {
        fixes.push("no model Kinetic runs was found; `kinetic pull <org>/<repo>` downloads one, or pass a .gguf file".into());
    }

    writeln!(out)?;
    if fixes.is_empty() {
        writeln!(out, "Nothing to fix. Go make something.")?;
    } else {
        writeln!(out, "To fix:")?;
        for f in fixes {
            writeln!(out, "  - {f}")?;
        }
    }
    Ok(())
}

fn describe(g: &Gpu) -> String {
    let gib = |b: u64| b as f64 / GIB;
    let memory = match g.memory_free {
        Some(free) => format!("{:.1} of {:.1} GiB free", gib(free), gib(g.memory_total)),
        None => format!("{:.1} GiB", gib(g.memory_total)),
    };
    let bandwidth = g
        .bandwidth
        .map_or_else(String::new, |b| format!(", {:.0} GB/s nominal", b / 1e9));
    format!(
        "{} via {}: {}{bandwidth}; {}",
        g.name, g.api, memory, g.driver
    )
}
