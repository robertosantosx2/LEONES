use std::ffi::CString;
use std::os::unix::ffi::OsStrExt;
use std::path::Path;

/// Total and available physical memory, from /proc/meminfo.
pub fn memory() -> Option<(u64, u64)> {
    let info = std::fs::read_to_string("/proc/meminfo").ok()?;
    let kib = |key: &str| -> Option<u64> {
        let line = info.lines().find_map(|l| l.strip_prefix(key))?;
        line.trim().strip_suffix("kB")?.trim().parse().ok()
    };
    Some((kib("MemTotal:")? * 1024, kib("MemAvailable:")? * 1024))
}

pub fn disk_free(dir: &Path) -> Option<u64> {
    let path = CString::new(dir.as_os_str().as_bytes()).ok()?;
    // SAFETY: statvfs is plain data, valid when zeroed.
    let mut s: libc::statvfs = unsafe { std::mem::zeroed() };
    // SAFETY: `path` is NUL-terminated and `s` is writable.
    if unsafe { libc::statvfs(path.as_ptr(), &mut s) } != 0 {
        return None;
    }
    Some(s.f_bavail * s.f_frsize)
}

/// The distribution's PRETTY_NAME, such as "Ubuntu 24.04.1 LTS".
pub fn name() -> String {
    std::fs::read_to_string("/etc/os-release")
        .ok()
        .and_then(|r| {
            r.lines()
                .find_map(|l| l.strip_prefix("PRETTY_NAME="))
                .map(|v| v.trim_matches('"').to_owned())
        })
        .unwrap_or_else(|| "Linux".into())
}
