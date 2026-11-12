//! Pinning a mapped file in RAM, for `--mlock`.

use std::io;

use memmap2::Mmap;

#[cfg(unix)]
pub fn lock(map: &Mmap) -> io::Result<()> {
    map.lock()
}

#[cfg(windows)]
pub fn lock(map: &Mmap) -> io::Result<()> {
    use windows_sys::Win32::System::Memory::VirtualLock;
    use windows_sys::Win32::System::Threading::{
        GetCurrentProcess, GetProcessWorkingSetSize, SetProcessWorkingSetSize,
    };

    let (mut min, mut max) = (0usize, 0usize);
    // SAFETY: plain Win32 calls on the current process; the out pointers
    // live on this stack frame.
    unsafe {
        let me = GetCurrentProcess();
        if GetProcessWorkingSetSize(me, &mut min, &mut max) == 0 {
            return Err(io::Error::last_os_error());
        }
        // VirtualLock fails past the minimum working set, which is ~200 KB by default
        let grow = map.len() + (1 << 20);
        if SetProcessWorkingSetSize(me, min + grow, max.max(min + grow)) == 0 {
            return Err(io::Error::last_os_error());
        }
        if VirtualLock(map.as_ptr().cast(), map.len()) == 0 {
            return Err(io::Error::last_os_error());
        }
    }
    Ok(())
}

#[cfg(not(any(unix, windows)))]
pub fn lock(_map: &Mmap) -> io::Result<()> {
    Err(io::ErrorKind::Unsupported.into())
}
