use unicode_width::UnicodeWidthChar;

/// The terminal window's columns and rows.
#[cfg(windows)]
pub fn size() -> Option<(usize, usize)> {
    use windows_sys::Win32::System::Console::{
        GetConsoleScreenBufferInfo, GetStdHandle, CONSOLE_SCREEN_BUFFER_INFO, STD_OUTPUT_HANDLE,
    };
    // SAFETY: the call fills the zeroed struct it is handed
    unsafe {
        let mut info: CONSOLE_SCREEN_BUFFER_INFO = std::mem::zeroed();
        (GetConsoleScreenBufferInfo(GetStdHandle(STD_OUTPUT_HANDLE), &mut info) != 0).then(|| {
            let w = info.srWindow;
            (
                (w.Right - w.Left + 1) as usize,
                (w.Bottom - w.Top + 1) as usize,
            )
        })
    }
}

#[cfg(unix)]
pub fn size() -> Option<(usize, usize)> {
    // SAFETY: TIOCGWINSZ fills the zeroed winsize it is handed
    unsafe {
        let mut size: libc::winsize = std::mem::zeroed();
        (libc::ioctl(libc::STDOUT_FILENO, libc::TIOCGWINSZ, &mut size) == 0 && size.ws_col > 0)
            .then_some((size.ws_col as usize, size.ws_row as usize))
    }
}

/// Columns `text` takes on screen, escape sequences skipped.
pub fn width(text: &str) -> usize {
    let mut chars = text.chars();
    let mut n = 0;
    while let Some(c) = chars.next() {
        if c == '\x1b' {
            if chars.next() == Some('[') {
                for c in chars.by_ref() {
                    if ('\x40'..='\x7e').contains(&c) {
                        break;
                    }
                }
            }
        } else {
            n += c.width().unwrap_or(0);
        }
    }
    n
}

/// How many rows the cursor has moved down since `text` began to print at
/// the start of a row, wrapping at `cols`.
pub fn rows_up(text: &str, cols: usize) -> usize {
    let mut lines = text.split('\n');
    let last = lines.next_back().map_or(0, width);
    let full: usize = lines.map(|l| width(l).div_ceil(cols).max(1)).sum();
    // a row filled to the edge leaves the cursor on it until the next char
    full + last.saturating_sub(1) / cols
}
