//! Host RAM cap: `total physical RAM - margin`, or an explicit ceiling.
//!
//! The cap bounds memory the process owns outright (baked tensors, LoRA factors, parked conversation states). The
//! mmapped GGUF is page cache the OS can evict, so a model larger than RAM still loads and streams.

/// Total physical RAM in bytes, or `None` if undetectable.
pub fn total_ram() -> Option<u64> {
    #[cfg(target_os = "linux")]
    {
        let m = std::fs::read_to_string("/proc/meminfo").unwrap_or_default();
        let kb = m.lines().find_map(|l| l.strip_prefix("MemTotal:")?.trim().strip_suffix("kB")?.trim().parse::<u64>().ok());
        if let Some(k) = kb {
            return Some(k << 10);
        }
    }
    #[cfg(windows)]
    {
        #[repr(C)]
        struct MemStatus {
            len: u32,
            load: u32,
            total: u64,
            avail: u64,
            rest: [u64; 5],
        }
        #[link(name = "kernel32")]
        unsafe extern "system" {
            fn GlobalMemoryStatusEx(m: *mut MemStatus) -> i32;
        }
        let mut m = MemStatus { len: size_of::<MemStatus>() as u32, load: 0, total: 0, avail: 0, rest: [0; 5] };
        if unsafe { GlobalMemoryStatusEx(&mut m) } != 0 && m.total > 0 {
            return Some(m.total);
        }
    }
    None
}

/// Usable cap in bytes: `max_ram` if nonzero, else `total - margin`. `None` means unlimited (RAM undetectable).
pub fn ram_cap(margin: u64, max_ram: u64) -> Option<u64> {
    if max_ram > 0 {
        return Some(max_ram);
    }
    Some(total_ram()?.saturating_sub(margin))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn explicit_max_ram_wins() {
        assert_eq!(ram_cap(512 << 20, 8 << 30), Some(8 << 30));
    }

    #[test]
    fn margin_is_subtracted() {
        if let Some(t) = total_ram() {
            assert_eq!(ram_cap(1 << 30, 0), Some(t.saturating_sub(1 << 30)));
        }
    }
}
