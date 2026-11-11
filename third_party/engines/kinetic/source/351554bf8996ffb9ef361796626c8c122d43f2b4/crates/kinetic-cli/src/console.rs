//! A double click in Explorer: instead of a window that flashes help and
//! closes, a terminal ready to use, with `kinetic` on its path.

use std::process::ExitCode;

const GREETING: &str = "Kinetic is ready. Try:
  kinetic pull LiquidAI/LFM3-1.7B-GGUF:Q4_K_M
  kinetic chat LiquidAI/LFM3-1.7B-GGUF
kinetic --help lists every command.";

/// Whether this process is alone in its console, as when Explorer started
/// it rather than a terminal.
#[cfg(windows)]
pub fn double_clicked() -> bool {
    use windows_sys::Win32::System::Console::GetConsoleProcessList;
    let mut ids = [0u32; 2];
    // SAFETY: the call writes at most ids.len() process ids into the buffer
    unsafe { GetConsoleProcessList(ids.as_mut_ptr(), ids.len() as u32) == 1 }
}

#[cfg(not(windows))]
pub fn double_clicked() -> bool {
    false
}

/// Opens PowerShell in this console with the binary's folder first on the
/// path; if that fails, explains and waits so the window stays readable.
pub fn open_terminal() -> ExitCode {
    let dir = std::env::current_exe()
        .ok()
        .and_then(|exe| exe.parent().map(|d| d.to_path_buf()));
    let mut shell = std::process::Command::new("powershell.exe");
    shell.args(["-NoExit", "-NoLogo", "-Command"]);
    let lines: Vec<String> = GREETING
        .lines()
        .map(|l| format!("Write-Host '{l}'"))
        .collect();
    shell.arg(lines.join("; "));
    if let Some(dir) = &dir {
        let path = std::env::var_os("PATH").unwrap_or_default();
        let joined =
            std::env::join_paths(std::iter::once(dir.clone()).chain(std::env::split_paths(&path)));
        shell.current_dir(dir);
        if let Ok(joined) = joined {
            shell.env("PATH", joined);
        }
    }
    match shell.status() {
        Ok(_) => ExitCode::SUCCESS,
        Err(_) => {
            println!("Kinetic runs in a terminal. Open one in this folder and type:\n{GREETING}");
            println!("\nPress Enter to close this window.");
            let _ = std::io::stdin().read_line(&mut String::new());
            ExitCode::SUCCESS
        }
    }
}

/// One key pressed in the terminal, read without waiting for Enter; Ctrl+C
/// comes back as 3. `None` when the terminal cannot be read.
#[cfg(windows)]
pub fn read_key() -> Option<u8> {
    extern "C" {
        fn _getch() -> std::ffi::c_int;
    }
    loop {
        // SAFETY: _getch is the CRT's console read and takes no arguments
        let key = unsafe { _getch() };
        match key {
            // arrows and function keys come as a prefix and a second code
            0 | 0xE0 => {
                // SAFETY: as above
                unsafe { _getch() };
            }
            k if k < 0 => return None,
            k => return u8::try_from(k).ok(),
        }
    }
}

#[cfg(unix)]
pub fn read_key() -> Option<u8> {
    // SAFETY: tcgetattr fills the zeroed termios, and the settings it held
    // are restored before returning; read writes at most one byte to `key`
    unsafe {
        let mut saved: libc::termios = std::mem::zeroed();
        if libc::tcgetattr(0, &mut saved) != 0 {
            return None;
        }
        let mut raw = saved;
        raw.c_lflag &= !(libc::ICANON | libc::ECHO | libc::ISIG);
        raw.c_cc[libc::VMIN] = 1;
        raw.c_cc[libc::VTIME] = 0;
        libc::tcsetattr(0, libc::TCSANOW, &raw);
        let mut key = 0u8;
        let n = libc::read(0, (&mut key as *mut u8).cast(), 1);
        libc::tcsetattr(0, libc::TCSANOW, &saved);
        (n == 1).then_some(key)
    }
}

#[cfg(not(any(windows, unix)))]
pub fn read_key() -> Option<u8> {
    None
}
