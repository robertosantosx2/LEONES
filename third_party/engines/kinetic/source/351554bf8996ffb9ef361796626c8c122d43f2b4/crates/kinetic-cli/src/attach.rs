//! Images attached to the next chat message: from a file path, typed or
//! dropped on the window, or from the clipboard.

use std::path::Path;

/// An image waiting to go out with the next message.
pub struct Attachment {
    pub name: String,
    pub bytes: Vec<u8>,
    pub width: u32,
    pub height: u32,
}

impl Attachment {
    /// Checks that `bytes` hold a picture the encoder reads.
    pub fn new(name: String, bytes: Vec<u8>) -> Result<Attachment, String> {
        let img = kinetic_vision::decode(&bytes).map_err(|e| format!("{name}: {e}"))?;
        Ok(Attachment {
            name,
            width: img.width(),
            height: img.height(),
            bytes,
        })
    }

    /// Reads the image file at `path`.
    pub fn open(path: &Path) -> Result<Attachment, String> {
        let bytes = std::fs::read(path).map_err(|e| format!("{}: {e}", path.display()))?;
        let name = path.file_name().map_or_else(
            || path.display().to_string(),
            |n| n.to_string_lossy().into_owned(),
        );
        Attachment::new(name, bytes)
    }

    /// "screenshot.png 1280x720"
    pub fn describe(&self) -> String {
        format!("{} {}x{}", self.name, self.width, self.height)
    }
}

const EXTENSIONS: [&str; 6] = ["png", "jpg", "jpeg", "webp", "bmp", "gif"];

/// The image file `line` names when it is nothing but a path, as a terminal
/// pastes a dropped file, maybe in quotes.
pub fn dropped_path(line: &str) -> Option<&Path> {
    let line = line.trim();
    let path = ['"', '\'']
        .iter()
        .find_map(|q| line.strip_prefix(*q).and_then(|l| l.strip_suffix(*q)))
        .unwrap_or(line);
    let path = Path::new(path);
    let ext = path.extension()?.to_str()?.to_ascii_lowercase();
    (EXTENSIONS.contains(&ext.as_str()) && path.is_file()).then_some(path)
}

/// The image on the clipboard, as the bytes of an image file, or why there
/// is none.
pub fn clipboard() -> Result<Vec<u8>, String> {
    platform::clipboard()
}

#[cfg(windows)]
mod platform {
    use windows_sys::Win32::System::DataExchange::{
        CloseClipboard, GetClipboardData, IsClipboardFormatAvailable, OpenClipboard,
        RegisterClipboardFormatW,
    };
    use windows_sys::Win32::System::Memory::{GlobalLock, GlobalSize, GlobalUnlock};

    // see WinUser.h; windows-sys keeps these under System::Ole
    const CF_DIB: u32 = 8;
    const CF_DIBV5: u32 = 17;

    pub fn clipboard() -> Result<Vec<u8>, String> {
        let png: Vec<u16> = "PNG\0".encode_utf16().collect();
        // SAFETY: `png` is NUL-terminated UTF-16.
        let png = unsafe { RegisterClipboardFormatW(png.as_ptr()) };
        // SAFETY: plain calls on the clipboard this thread opens and closes.
        unsafe {
            if OpenClipboard(std::ptr::null_mut()) == 0 {
                return Err("the clipboard is busy".into());
            }
            let found = [(png, false), (CF_DIBV5, true), (CF_DIB, true)]
                .into_iter()
                .find(|&(f, _)| f != 0 && IsClipboardFormatAvailable(f) != 0)
                .and_then(|(f, dib)| Some((read(f)?, dib)));
            CloseClipboard();
            match found {
                Some((bytes, true)) => bmp_file(&bytes),
                Some((bytes, false)) => Ok(bytes),
                None => Err("there is no image on the clipboard".into()),
            }
        }
    }

    /// A copy of the clipboard's data in `format`.
    ///
    /// # Safety
    /// The clipboard must be open on this thread.
    unsafe fn read(format: u32) -> Option<Vec<u8>> {
        // SAFETY: the clipboard is open, so the handle stays valid until it
        // closes; the locked block holds `GlobalSize` bytes.
        unsafe {
            let handle = GetClipboardData(format);
            if handle.is_null() {
                return None;
            }
            let data = GlobalLock(handle).cast::<u8>();
            if data.is_null() {
                return None;
            }
            let bytes = std::slice::from_raw_parts(data, GlobalSize(handle)).to_vec();
            GlobalUnlock(handle);
            Some(bytes)
        }
    }

    /// A device-independent bitmap with the file header a .bmp starts with.
    fn bmp_file(dib: &[u8]) -> Result<Vec<u8>, String> {
        let word = |at: usize| {
            dib.get(at..at + 4)
                .map(|b| u32::from_le_bytes([b[0], b[1], b[2], b[3]]))
        };
        let half = |at: usize| {
            dib.get(at..at + 2)
                .map(|b| u16::from_le_bytes([b[0], b[1]]))
        };
        let (Some(header), Some(bits), Some(compression), Some(used)) =
            (word(0), half(14), word(16), word(32))
        else {
            return Err("the clipboard bitmap is cut short".into());
        };
        // BI_BITFIELDS after a plain 40-byte header keeps its three masks
        // apart from the header
        let masks = if header == 40 && compression == 3 {
            12
        } else {
            0
        };
        let colors = match (used, bits) {
            (0, 1..=8) => 1 << bits,
            (n, _) => n,
        };
        let offset = 14 + header + masks + 4 * colors;
        let mut file = Vec::with_capacity(14 + dib.len());
        file.extend_from_slice(b"BM");
        file.extend_from_slice(&(14 + dib.len() as u32).to_le_bytes());
        file.extend_from_slice(&[0; 4]);
        file.extend_from_slice(&offset.to_le_bytes());
        file.extend_from_slice(dib);
        Ok(file)
    }
}

#[cfg(not(windows))]
mod platform {
    use std::process::Command;

    pub fn clipboard() -> Result<Vec<u8>, String> {
        let tools: [(&str, &[&str]); 2] = [
            ("wl-paste", &["--type", "image/png"]),
            (
                "xclip",
                &["-selection", "clipboard", "-t", "image/png", "-o"],
            ),
        ];
        let mut ran = false;
        for (tool, args) in tools {
            let Ok(out) = Command::new(tool).args(args).output() else {
                continue;
            };
            ran = true;
            if out.status.success() && !out.stdout.is_empty() {
                return Ok(out.stdout);
            }
        }
        Err(match ran {
            true => "there is no image on the clipboard".into(),
            false => "reading the clipboard needs wl-paste (Wayland) or xclip (X11)".into(),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::dropped_path;

    #[test]
    fn only_whole_image_paths_are_dropped_files() {
        let dir = std::env::temp_dir().join("kinetic-attach-test");
        std::fs::create_dir_all(&dir).unwrap();
        let png = dir.join("shot one.PNG");
        std::fs::write(&png, b"x").unwrap();
        let quoted = format!("\"{}\"", png.display());
        assert_eq!(dropped_path(&quoted), Some(png.as_path()));
        assert_eq!(
            dropped_path(&format!(" {} ", png.display())),
            Some(png.as_path())
        );
        assert_eq!(dropped_path(&format!("look at {}", png.display())), None);
        assert_eq!(
            dropped_path(&dir.join("missing.png").display().to_string()),
            None
        );
        std::fs::remove_dir_all(&dir).unwrap();
    }
}
