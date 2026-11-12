//! Peak resident memory of this process.

/// The most memory this process has had resident, in bytes, where the
/// platform reports it.
#[cfg(windows)]
pub fn peak_rss() -> Option<u64> {
    #[repr(C)]
    #[derive(Default)]
    struct ProcessMemoryCounters {
        cb: u32,
        page_fault_count: u32,
        peak_working_set_size: usize,
        working_set_size: usize,
        quota_peak_paged_pool_usage: usize,
        quota_paged_pool_usage: usize,
        quota_peak_non_paged_pool_usage: usize,
        quota_non_paged_pool_usage: usize,
        pagefile_usage: usize,
        peak_pagefile_usage: usize,
    }

    #[link(name = "kernel32")]
    extern "system" {
        fn GetCurrentProcess() -> isize;
        fn K32GetProcessMemoryInfo(
            process: isize,
            counters: *mut ProcessMemoryCounters,
            size: u32,
        ) -> i32;
    }

    let mut counters = ProcessMemoryCounters {
        cb: size_of::<ProcessMemoryCounters>() as u32,
        ..Default::default()
    };
    // SAFETY: the pseudo-handle from GetCurrentProcess is always valid, and
    // `counters` is a correctly sized PROCESS_MEMORY_COUNTERS that the call
    // only writes within `cb` bytes.
    let ok = unsafe { K32GetProcessMemoryInfo(GetCurrentProcess(), &mut counters, counters.cb) };
    (ok != 0).then_some(counters.peak_working_set_size as u64)
}

#[cfg(target_os = "linux")]
pub fn peak_rss() -> Option<u64> {
    let status = std::fs::read_to_string("/proc/self/status").ok()?;
    let kib: u64 = status
        .lines()
        .find_map(|l| l.strip_prefix("VmHWM:"))?
        .trim()
        .strip_suffix("kB")?
        .trim()
        .parse()
        .ok()?;
    Some(kib * 1024)
}

#[cfg(not(any(windows, target_os = "linux")))]
pub fn peak_rss() -> Option<u64> {
    None
}
