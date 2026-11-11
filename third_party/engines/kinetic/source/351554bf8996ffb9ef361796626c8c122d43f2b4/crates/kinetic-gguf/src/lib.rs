//! Reader for GGUF model files.
//!
//! [`Gguf::parse`] validates the header against the buffer it came from, so
//! every tensor it reports lies inside that buffer. [`GgufFile`] maps a file
//! from disk and hands out tensor bytes without copying.

mod file_type;
mod lock;
mod reader;
mod value;
mod writer;

use std::fmt;
use std::fs::File;
use std::path::Path;

use memmap2::{Mmap, MmapOptions};

pub use kinetic_quant::TensorType;
use reader::Reader;
pub use value::Value;
pub use writer::{write, TensorOut};

// the four letters every local model has opened with since 2023
const MAGIC: &[u8; 4] = b"GGUF";
// 32 bytes: the hardware likes round numbers and so do we
const DEFAULT_ALIGNMENT: u64 = 32;
const MAX_DIMS: usize = 4;

#[derive(Debug)]
pub enum Error {
    Io(std::io::Error),
    NotGguf,
    UnsupportedVersion(u32),
    Truncated { offset: usize },
    UnknownTensorType { tensor: String, id: u32 },
    Invalid(String),
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::Io(e) => write!(f, "{e}"),
            Error::NotGguf => f.write_str("not a GGUF file"),
            Error::UnsupportedVersion(v) => write!(f, "unsupported GGUF version {v}"),
            Error::Truncated { offset } => write!(f, "file ends early at offset {offset}"),
            Error::UnknownTensorType { tensor, id } => {
                write!(f, "tensor {tensor} has unknown type id {id}")
            }
            Error::Invalid(msg) => f.write_str(msg),
        }
    }
}

impl std::error::Error for Error {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Error::Io(e) => Some(e),
            _ => None,
        }
    }
}

impl From<std::io::Error> for Error {
    fn from(e: std::io::Error) -> Self {
        Error::Io(e)
    }
}

#[derive(Clone, Debug)]
pub struct TensorInfo {
    pub name: String,
    /// Dimensions, innermost first (`dims[0]` is the contiguous row length).
    pub dims: Vec<u64>,
    pub ty: TensorType,
    /// Absolute byte offset in the file.
    pub offset: u64,
    pub size: u64,
}

impl TensorInfo {
    pub fn elements(&self) -> u64 {
        self.dims.iter().product()
    }
}

#[derive(Clone, Debug)]
pub struct Gguf {
    pub version: u32,
    pub alignment: u64,
    /// Absolute offset where tensor data begins.
    pub data_offset: u64,
    pub metadata: Vec<(String, Value)>,
    pub tensors: Vec<TensorInfo>,
}

impl Gguf {
    pub fn parse(buf: &[u8]) -> Result<Gguf, Error> {
        if buf.len() < 4 || &buf[..4] != MAGIC {
            return Err(Error::NotGguf);
        }
        let mut r = Reader::new(&buf[4..]);
        let version = r.u32()?;
        if !(2..=3).contains(&version) {
            return Err(Error::UnsupportedVersion(version));
        }
        let tensor_count = r.count(24)?;
        let kv_count = r.count(12)?;

        let mut metadata = Vec::with_capacity(kv_count);
        for _ in 0..kv_count {
            let key = r.string()?;
            let value = r.value()?;
            metadata.push((key, value));
        }

        let alignment = match metadata.iter().find(|(k, _)| k == "general.alignment") {
            Some((_, v)) => v
                .as_u64()
                .filter(|a| a.is_power_of_two())
                .ok_or_else(|| Error::Invalid("general.alignment must be a power of two".into()))?,
            None => DEFAULT_ALIGNMENT,
        };

        let mut raw = Vec::with_capacity(tensor_count);
        for _ in 0..tensor_count {
            let name = r.string()?;
            let n_dims = r.u32()? as usize;
            if n_dims == 0 || n_dims > MAX_DIMS {
                return Err(Error::Invalid(format!(
                    "tensor {name} has {n_dims} dimensions"
                )));
            }
            let dims = (0..n_dims)
                .map(|_| r.u64())
                .collect::<Result<Vec<_>, _>>()?;
            let id = r.u32()?;
            let offset = r.u64()?;
            let ty = TensorType::from_id(id).ok_or_else(|| Error::UnknownTensorType {
                tensor: name.clone(),
                id,
            })?;
            raw.push((name, dims, ty, offset));
        }

        let data_offset = align_up(4 + r.pos() as u64, alignment);
        let file_len = buf.len() as u64;
        let mut tensors = Vec::with_capacity(raw.len());
        for (name, dims, ty, rel) in raw {
            let invalid = |why: &str| Error::Invalid(format!("tensor {name}: {why}"));
            let elements = dims
                .iter()
                .try_fold(1u64, |acc, &d| acc.checked_mul(d))
                .ok_or_else(|| invalid("element count overflows"))?;
            if !dims[0].is_multiple_of(ty.block_len() as u64) {
                return Err(invalid("row length is not a whole number of blocks"));
            }
            let size = ty
                .bytes_for(elements)
                .ok_or_else(|| invalid("size overflows"))?;
            if !rel.is_multiple_of(alignment) {
                return Err(invalid("data is not aligned"));
            }
            let offset = data_offset
                .checked_add(rel)
                .filter(|o| o.checked_add(size).is_some_and(|end| end <= file_len))
                .ok_or_else(|| invalid("data lies outside the file"))?;
            tensors.push(TensorInfo {
                name,
                dims,
                ty,
                offset,
                size,
            });
        }

        Ok(Gguf {
            version,
            alignment,
            data_offset,
            metadata,
            tensors,
        })
    }

    pub fn get(&self, key: &str) -> Option<&Value> {
        self.metadata.iter().find(|(k, _)| k == key).map(|(_, v)| v)
    }

    pub fn architecture(&self) -> Option<&str> {
        self.get("general.architecture")?.as_str()
    }

    /// Looks up `{architecture}.{key}`, e.g. `arch_key("block_count")`.
    pub fn arch_key(&self, key: &str) -> Option<&Value> {
        self.get(&format!("{}.{key}", self.architecture()?))
    }

    pub fn tensor(&self, name: &str) -> Option<&TensorInfo> {
        self.tensors.iter().find(|t| t.name == name)
    }
}

/// Anything that holds a GGUF-shaped header and the bytes of its tensors,
/// such as a GGUF file or another container laid out the same way.
pub trait TensorSource {
    fn header(&self) -> &Gguf;

    /// The bytes of a tensor listed in [`TensorSource::header`].
    fn tensor_data(&self, tensor: &TensorInfo) -> &[u8];
}

impl TensorSource for GgufFile {
    fn header(&self) -> &Gguf {
        &self.header
    }

    fn tensor_data(&self, tensor: &TensorInfo) -> &[u8] {
        GgufFile::tensor_data(self, tensor)
    }
}

/// A GGUF file mapped into memory.
pub struct GgufFile {
    header: Gguf,
    map: Mmap,
}

impl GgufFile {
    pub fn open(path: impl AsRef<Path>) -> Result<GgufFile, Error> {
        let file = File::open(path)?;
        // SAFETY: the map is read-only. Another process truncating the file
        // while it is mapped is outside what any mmap-based loader can guard.
        let map = unsafe { Mmap::map(&file)? };
        let header = Gguf::parse(&map)?;
        Ok(GgufFile { header, map })
    }

    /// Reads the whole file into memory instead of mapping it, as
    /// llama.cpp's `--no-mmap` does; later changes to the file do not show.
    pub fn read(path: impl AsRef<Path>) -> Result<GgufFile, Error> {
        let mut file = File::open(path)?;
        let len = file.metadata()?.len();
        let len = usize::try_from(len).map_err(|_| Error::NotGguf)?;
        let mut map = MmapOptions::new().len(len.max(1)).map_anon()?;
        std::io::Read::read_exact(&mut file, &mut map[..len])?;
        let map = map.make_read_only()?;
        let header = Gguf::parse(&map[..len])?;
        Ok(GgufFile { header, map })
    }

    /// Keeps the file's pages in RAM, so the system never swaps them out.
    pub fn lock(&self) -> std::io::Result<()> {
        lock::lock(&self.map)
    }

    pub fn header(&self) -> &Gguf {
        &self.header
    }

    pub fn tensor_data(&self, tensor: &TensorInfo) -> &[u8] {
        &self.map[tensor.offset as usize..(tensor.offset + tensor.size) as usize]
    }

    pub fn len(&self) -> u64 {
        self.map.len() as u64
    }

    pub fn is_empty(&self) -> bool {
        self.map.is_empty()
    }
}

fn align_up(x: u64, align: u64) -> u64 {
    x.div_ceil(align) * align
}

#[cfg(test)]
mod tests;
