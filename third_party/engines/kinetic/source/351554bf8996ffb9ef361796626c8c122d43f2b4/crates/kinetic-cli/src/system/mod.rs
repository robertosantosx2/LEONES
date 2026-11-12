//! This computer: operating system, CPU, memory, disks and GPUs.

#[cfg(target_os = "linux")]
mod linux;
#[cfg(windows)]
mod windows;

mod gpu;

#[cfg(target_os = "linux")]
use linux as os;
#[cfg(windows)]
use windows as os;

use std::path::Path;
use std::time::Instant;

use rayon::prelude::*;

pub use gpu::{cuda_free, gpus, Gpu};

/// The CPU and memory.
pub struct Machine {
    pub os: String,
    pub cpu: String,
    pub threads: usize,
    /// The instruction sets Kinetic's CPU kernels need.
    pub avx2: bool,
    pub fma: bool,
    pub f16c: bool,
    pub ram_total: u64,
    pub ram_available: u64,
}

pub fn machine() -> Machine {
    let (ram_total, ram_available) = os::memory().unwrap_or((0, 0));
    let (avx2, fma, f16c) = features();
    Machine {
        os: os::name(),
        cpu: cpu_name().unwrap_or_else(|| std::env::consts::ARCH.to_owned()),
        threads: std::thread::available_parallelism().map_or(1, |n| n.get()),
        avx2,
        fma,
        f16c,
        ram_total,
        ram_available,
    }
}

/// Bytes free for this user on the disk holding `path`.
pub fn disk_free(path: &Path) -> Option<u64> {
    let mut dir = path;
    // the folder may not exist yet; ask about the nearest one that does
    while !dir.exists() {
        dir = dir.parent()?;
    }
    os::disk_free(dir)
}

#[cfg(target_arch = "x86_64")]
fn features() -> (bool, bool, bool) {
    (
        is_x86_feature_detected!("avx2"),
        is_x86_feature_detected!("fma"),
        is_x86_feature_detected!("f16c"),
    )
}

#[cfg(not(target_arch = "x86_64"))]
fn features() -> (bool, bool, bool) {
    (false, false, false)
}

/// The brand string the CPU reports, from cpuid leaves 0x80000002..4.
#[cfg(target_arch = "x86_64")]
// __cpuid is a safe fn on toolchains newer than the 1.91 MSRV
#[allow(unused_unsafe)]
fn cpu_name() -> Option<String> {
    use std::arch::x86_64::__cpuid;
    // SAFETY: cpuid exists on every x86-64 CPU; the extended leaves are
    // read only after leaf 0x80000000 says they exist.
    let max = unsafe { __cpuid(0x8000_0000) }.eax;
    if max < 0x8000_0004 {
        return None;
    }
    let mut bytes = Vec::with_capacity(48);
    for leaf in 0x8000_0002..=0x8000_0004u32 {
        // SAFETY: as above, the leaf is within the reported range.
        let r = unsafe { __cpuid(leaf) };
        for word in [r.eax, r.ebx, r.ecx, r.edx] {
            bytes.extend(word.to_le_bytes());
        }
    }
    let name = String::from_utf8_lossy(&bytes);
    let name = name.trim_matches(|c: char| c == '\0' || c.is_whitespace());
    (!name.is_empty()).then(|| name.split_whitespace().collect::<Vec<_>>().join(" "))
}

#[cfg(not(target_arch = "x86_64"))]
fn cpu_name() -> Option<String> {
    None
}

/// Read bandwidth of main memory in bytes per second, measured by summing
/// a buffer larger than any cache on every thread, best of a few passes.
pub fn memory_bandwidth() -> f64 {
    // the speed limit; everything else in kinetic is about not paying it twice
    const BYTES: usize = 256 << 20;
    let buffer = vec![1u64; BYTES / 8];
    let mut best = f64::MAX;
    for _ in 0..4 {
        let start = Instant::now();
        let sum: u64 = buffer
            .par_chunks(1 << 16)
            .map(|c| c.iter().sum::<u64>())
            .sum();
        std::hint::black_box(sum);
        best = best.min(start.elapsed().as_secs_f64());
    }
    BYTES as f64 / best
}
