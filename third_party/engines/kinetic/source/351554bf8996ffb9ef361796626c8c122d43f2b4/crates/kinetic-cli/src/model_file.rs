use std::fs::File;
use std::io::Read;
use std::path::Path;

use kinetic_gguf::{GgufFile, TensorSource};
use kinetic_ktc::KtcFile;

/// A model file in either format, told apart by its first bytes.
pub enum ModelFile {
    Gguf(GgufFile),
    Ktc(Box<KtcFile>),
}

impl ModelFile {
    pub fn open(path: &Path) -> Result<ModelFile, String> {
        ModelFile::open_with(path, true)
    }

    /// Opens the file mapped, or with `mmap` false read into memory, which
    /// only GGUF files support.
    pub fn open_with(path: &Path, mmap: bool) -> Result<ModelFile, String> {
        let fail = |e: &dyn std::fmt::Display| format!("{}: {e}", path.display());
        let mut magic = [0u8; 4];
        File::open(path)
            .and_then(|mut f| f.read_exact(&mut magic))
            .map_err(|e| match e.kind() {
                std::io::ErrorKind::UnexpectedEof => fail(&"not a GGUF or .ktc file"),
                _ => fail(&e),
            })?;
        if &magic == b"KTC1" && !mmap {
            Err(fail(&"--no-mmap works with GGUF files"))
        } else if &magic == b"KTC1" {
            KtcFile::open(path)
                .map(|f| ModelFile::Ktc(Box::new(f)))
                .map_err(|e| fail(&e))
        } else if !mmap {
            GgufFile::read(path)
                .map(ModelFile::Gguf)
                .map_err(|e| fail(&e))
        } else {
            GgufFile::open(path)
                .map(ModelFile::Gguf)
                .map_err(|e| fail(&e))
        }
    }

    pub fn source(&self) -> &dyn TensorSource {
        match self {
            ModelFile::Gguf(f) => f,
            ModelFile::Ktc(f) => &**f,
        }
    }

    /// Pins the file in RAM, as `--mlock` asks.
    pub fn lock(&self) -> Result<(), String> {
        match self {
            ModelFile::Gguf(f) => f.lock().map_err(|e| format!("--mlock: {e}")),
            ModelFile::Ktc(_) => Err("--mlock works with GGUF files".into()),
        }
    }

    pub fn len(&self) -> u64 {
        match self {
            ModelFile::Gguf(f) => f.len(),
            ModelFile::Ktc(f) => f.len(),
        }
    }
}
