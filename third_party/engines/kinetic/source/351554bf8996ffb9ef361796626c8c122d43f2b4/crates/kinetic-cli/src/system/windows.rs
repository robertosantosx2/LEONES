use std::os::windows::ffi::OsStrExt;
use std::path::Path;

#[repr(C)]
struct MemoryStatusEx {
    length: u32,
    memory_load: u32,
    total_phys: u64,
    avail_phys: u64,
    total_page_file: u64,
    avail_page_file: u64,
    total_virtual: u64,
    avail_virtual: u64,
    avail_extended_virtual: u64,
}

#[repr(C)]
struct OsVersionInfo {
    size: u32,
    major: u32,
    minor: u32,
    build: u32,
    platform: u32,
    service_pack: [u16; 128],
}

#[link(name = "kernel32")]
extern "system" {
    fn GlobalMemoryStatusEx(status: *mut MemoryStatusEx) -> i32;
    fn GetDiskFreeSpaceExW(
        dir: *const u16,
        free_to_caller: *mut u64,
        total: *mut u64,
        total_free: *mut u64,
    ) -> i32;
}

#[link(name = "ntdll")]
extern "system" {
    fn RtlGetVersion(info: *mut OsVersionInfo) -> i32;
}

/// Total and available physical memory.
pub fn memory() -> Option<(u64, u64)> {
    let mut s = MemoryStatusEx {
        length: size_of::<MemoryStatusEx>() as u32,
        memory_load: 0,
        total_phys: 0,
        avail_phys: 0,
        total_page_file: 0,
        avail_page_file: 0,
        total_virtual: 0,
        avail_virtual: 0,
        avail_extended_virtual: 0,
    };
    // SAFETY: `s` is a MEMORYSTATUSEX with its length set, as the call needs.
    let ok = unsafe { GlobalMemoryStatusEx(&mut s) };
    (ok != 0).then_some((s.total_phys, s.avail_phys))
}

pub fn disk_free(dir: &Path) -> Option<u64> {
    let wide: Vec<u16> = dir.as_os_str().encode_wide().chain([0]).collect();
    let mut free = 0;
    // SAFETY: `wide` is NUL-terminated; the null pointers are optional outputs.
    let ok = unsafe {
        GetDiskFreeSpaceExW(
            wide.as_ptr(),
            &mut free,
            std::ptr::null_mut(),
            std::ptr::null_mut(),
        )
    };
    (ok != 0).then_some(free)
}

/// "Windows 11 (build 26100)"; RtlGetVersion, unlike GetVersionEx, does not
/// depend on the executable's manifest.
pub fn name() -> String {
    let mut v = OsVersionInfo {
        size: size_of::<OsVersionInfo>() as u32,
        major: 0,
        minor: 0,
        build: 0,
        platform: 0,
        service_pack: [0; 128],
    };
    // SAFETY: `v` is an OSVERSIONINFOW with its size set.
    if unsafe { RtlGetVersion(&mut v) } != 0 {
        return "Windows".into();
    }
    // windows 11 still reports 10.0, told apart by its build number
    let release = match (v.major, v.build) {
        (10, b) if b >= 22000 => "11".to_owned(),
        (major, _) => format!("{major}.{}", v.minor),
    };
    format!("Windows {release} (build {})", v.build)
}
