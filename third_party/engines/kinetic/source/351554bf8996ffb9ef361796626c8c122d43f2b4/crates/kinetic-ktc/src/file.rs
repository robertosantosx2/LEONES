use std::collections::HashSet;
use std::fs::File;
use std::ops::Range;
use std::path::Path;

use kinetic_gguf::{Gguf, TensorInfo, Value};
use memmap2::Mmap;

use crate::error::{invalid, Error};
use crate::manifest::{Manifest, Section};

pub(crate) const MAGIC: &[u8; 4] = b"KTC1";
// there is no version 0; we do not talk about version 0
pub const VERSION: u32 = 1;
pub(crate) const HEADER_LEN: usize = 96;
pub(crate) const SIGNATURE: Range<usize> = 32..96;
pub(crate) const FLAGS: Range<usize> = 8..12;
pub(crate) const FLAG_SIGNED: u32 = 1;
/// Every section and tensor starts on this boundary, so each can be mapped
/// or advised page by page.
pub const ALIGNMENT: u64 = 4096;
/// The section that holds all tensor data.
pub const TENSORS: &str = "tensors";
const MAX_DIMS: usize = 4;

/// A parsed `.ktc` header, checked against the buffer it came from.
#[derive(Clone, Debug)]
pub struct Ktc {
    pub version: u32,
    /// The Ed25519 signature of the manifest bytes, if the file is signed.
    pub signature: Option<[u8; 64]>,
    pub manifest: Manifest,
    /// Where the manifest bytes lie in the file.
    pub manifest_range: Range<usize>,
    /// Absolute offset that section offsets are relative to.
    pub data_offset: u64,
}

impl Ktc {
    /// Parses and validates a whole file held in `buf`. Every section and
    /// tensor it reports lies inside `buf`.
    pub fn parse(buf: &[u8]) -> Result<Ktc, Error> {
        if buf.len() < MAGIC.len() || &buf[..MAGIC.len()] != MAGIC {
            return Err(Error::BadMagic);
        }
        if buf.len() < HEADER_LEN {
            return Err(invalid("file ends inside the header"));
        }
        let u32_at = |at: usize| u32::from_le_bytes(buf[at..at + 4].try_into().unwrap());
        let u64_at = |at: usize| u64::from_le_bytes(buf[at..at + 8].try_into().unwrap());
        let version = u32_at(4);
        if version != VERSION {
            return Err(Error::UnsupportedVersion(version));
        }
        let flags = u32_at(FLAGS.start);
        if flags & !FLAG_SIGNED != 0 || u32_at(12) != 0 {
            return Err(invalid("reserved header bits are set"));
        }
        let file_len = buf.len() as u64;
        let manifest_end = u64_at(16)
            .checked_add(HEADER_LEN as u64)
            .filter(|&end| end <= file_len)
            .ok_or_else(|| invalid("manifest extends past the end of the file"))?;
        let data_offset = u64_at(24);
        if data_offset != manifest_end.next_multiple_of(ALIGNMENT) || data_offset > file_len {
            return Err(invalid("data offset does not follow the manifest"));
        }
        let signature: [u8; 64] = buf[SIGNATURE].try_into().unwrap();
        let signature = if flags & FLAG_SIGNED != 0 {
            Some(signature)
        } else if signature.iter().any(|&b| b != 0) {
            return Err(invalid("unsigned file carries signature bytes"));
        } else {
            None
        };

        let manifest_range = HEADER_LEN..manifest_end as usize;
        let manifest: Manifest = serde_json::from_slice(&buf[manifest_range.clone()])
            .map_err(|e| invalid(format!("manifest: {e}")))?;
        check_sections(&manifest, buf, manifest_end, data_offset)?;
        check_tensors(&manifest)?;
        if let Some(name) = &manifest.tokenizer.section {
            if manifest.section(name).is_none() {
                return Err(invalid(format!("tokenizer section {name} is missing")));
            }
        }
        Ok(Ktc {
            version,
            signature,
            manifest,
            manifest_range,
            data_offset,
        })
    }

    /// Absolute byte range of a section listed in the manifest.
    pub fn section_range(&self, section: &Section) -> Range<usize> {
        let start = (self.data_offset + section.offset) as usize;
        start..start + section.size as usize
    }

    /// The manifest as GGUF metadata and tensor infos with absolute offsets,
    /// so code written for GGUF reads a `.ktc` unchanged.
    pub fn to_gguf(&self) -> Gguf {
        let m = &self.manifest;
        let mut metadata = vec![
            (
                "general.architecture".to_owned(),
                Value::String(m.architecture.clone()),
            ),
            ("general.name".to_owned(), Value::String(m.name.clone())),
        ];
        metadata.extend(m.metadata.iter().cloned());
        let prefixed = |prefix: &str, entries: &[(String, Value)]| {
            entries
                .iter()
                .map(|(k, v)| (format!("{prefix}.{k}"), v.clone()))
                .collect::<Vec<_>>()
        };
        metadata.extend(prefixed(&m.architecture, &m.hyperparameters));
        metadata.extend(prefixed("tokenizer", &m.tokenizer.metadata));
        if let Some(template) = &m.chat_template {
            metadata.push((
                "tokenizer.chat_template".to_owned(),
                Value::String(template.clone()),
            ));
        }
        let base = self.data_offset + m.section(TENSORS).map_or(0, |s| s.offset);
        let tensors = m
            .tensors
            .iter()
            .map(|t| TensorInfo {
                name: t.name.clone(),
                dims: t.dims.clone(),
                ty: t.ty,
                offset: base + t.offset,
                size: t.size,
            })
            .collect();
        Gguf {
            // The metadata follows GGUF v3 conventions.
            version: 3,
            alignment: ALIGNMENT,
            data_offset: base,
            metadata,
            tensors,
        }
    }
}

fn check_sections(m: &Manifest, buf: &[u8], manifest_end: u64, data: u64) -> Result<(), Error> {
    let mut names = HashSet::new();
    let mut ranges = Vec::with_capacity(m.sections.len());
    for s in &m.sections {
        let bad = |why: &str| invalid(format!("section {}: {why}", s.name));
        if s.name.is_empty() || !names.insert(s.name.as_str()) {
            return Err(bad("name is empty or repeated"));
        }
        if !s.offset.is_multiple_of(ALIGNMENT) {
            return Err(bad("offset is not aligned"));
        }
        let range = data
            .checked_add(s.offset)
            .and_then(|start| Some((start, start.checked_add(s.size)?)))
            .filter(|&(_, end)| end <= buf.len() as u64)
            .ok_or_else(|| bad("data lies outside the file"))?;
        ranges.push(range);
    }
    if !names.contains(TENSORS) {
        return Err(invalid("manifest has no tensors section"));
    }
    ranges.sort_unstable();
    let mut cursor = manifest_end;
    for (start, end) in ranges {
        if start < cursor.max(data) {
            return Err(invalid("sections overlap"));
        }
        if buf[cursor as usize..start as usize].iter().any(|&b| b != 0) {
            return Err(invalid("padding before a section is not zero"));
        }
        cursor = end;
    }
    if cursor.max(data) != buf.len() as u64 {
        return Err(invalid("file has bytes after its last section"));
    }
    Ok(())
}

pub(crate) fn check_tensors(m: &Manifest) -> Result<(), Error> {
    let section = m.section(TENSORS).map_or(0, |s| s.size);
    let mut names = HashSet::new();
    let mut ranges = Vec::with_capacity(m.tensors.len());
    for t in &m.tensors {
        let bad = |why: &str| invalid(format!("tensor {}: {why}", t.name));
        if !names.insert(t.name.as_str()) {
            return Err(bad("name is repeated"));
        }
        if t.dims.is_empty() || t.dims.len() > MAX_DIMS {
            return Err(bad("needs one to four dimensions"));
        }
        let elements = t
            .dims
            .iter()
            .try_fold(1u64, |acc, &d| acc.checked_mul(d))
            .ok_or_else(|| bad("element count overflows"))?;
        if !t.dims[0].is_multiple_of(t.ty.block_len() as u64) {
            return Err(bad("row length is not a whole number of blocks"));
        }
        if t.ty.bytes_for(elements) != Some(t.size) {
            return Err(bad("size does not match its type and shape"));
        }
        if !t.offset.is_multiple_of(ALIGNMENT) {
            return Err(bad("offset is not aligned"));
        }
        let end = t
            .offset
            .checked_add(t.size)
            .filter(|&end| end <= section)
            .ok_or_else(|| bad("data lies outside the tensors section"))?;
        ranges.push((t.offset, end));
    }
    ranges.sort_unstable();
    if ranges.windows(2).any(|w| w[1].0 < w[0].1) {
        return Err(invalid("tensors overlap"));
    }
    Ok(())
}

/// A `.ktc` file mapped into memory.
pub struct KtcFile {
    header: Ktc,
    gguf: Gguf,
    map: Mmap,
}

impl KtcFile {
    pub fn open(path: impl AsRef<Path>) -> Result<KtcFile, Error> {
        let file = File::open(path)?;
        // SAFETY: the map is read-only. Another process truncating the file
        // while it is mapped is outside what any mmap-based loader can guard.
        let map = unsafe { Mmap::map(&file)? };
        let header = Ktc::parse(&map)?;
        let gguf = header.to_gguf();
        Ok(KtcFile { header, gguf, map })
    }

    pub fn header(&self) -> &Ktc {
        &self.header
    }

    pub fn manifest(&self) -> &Manifest {
        &self.header.manifest
    }

    /// The manifest exactly as stored, which is what a signature covers.
    pub fn manifest_bytes(&self) -> &[u8] {
        &self.map[self.header.manifest_range.clone()]
    }

    /// The file seen as GGUF; see [`Ktc::to_gguf`].
    pub fn gguf(&self) -> &Gguf {
        &self.gguf
    }

    /// Bytes of a tensor from [`KtcFile::gguf`], without copying.
    pub fn tensor_data(&self, tensor: &TensorInfo) -> &[u8] {
        &self.map[tensor.offset as usize..(tensor.offset + tensor.size) as usize]
    }

    pub fn section_data(&self, section: &Section) -> &[u8] {
        &self.map[self.header.section_range(section)]
    }

    pub fn len(&self) -> u64 {
        self.map.len() as u64
    }

    pub fn is_empty(&self) -> bool {
        self.map.is_empty()
    }
}

impl kinetic_gguf::TensorSource for KtcFile {
    fn header(&self) -> &Gguf {
        &self.gguf
    }

    fn tensor_data(&self, tensor: &TensorInfo) -> &[u8] {
        KtcFile::tensor_data(self, tensor)
    }
}
