use std::fs::{self, File};
use std::io::{BufWriter, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};

use kinetic_gguf::TensorType;
use memmap2::Mmap;

use crate::error::{invalid, Error};
use crate::file::{self, Ktc, ALIGNMENT, FLAG_SIGNED, HEADER_LEN, MAGIC, TENSORS, VERSION};
use crate::manifest::{ExecutionProfile, Manifest, Section, Tensor, Tokenizer};
use crate::metadata::Metadata;
use crate::sign::sign;

/// Everything that goes into a `.ktc` file. Data is borrowed, typically from
/// a memory-mapped source, and streamed to disk.
pub struct Contents<'a> {
    pub name: String,
    pub architecture: String,
    pub hyperparameters: Metadata,
    pub tokenizer: Tokenizer,
    pub chat_template: Option<String>,
    pub metadata: Metadata,
    pub execution_profile: Option<ExecutionProfile>,
    pub tensors: Vec<TensorData<'a>>,
    /// Sections besides `tensors`, stored verbatim.
    pub sections: Vec<(String, &'a [u8])>,
}

pub struct TensorData<'a> {
    pub name: String,
    pub ty: TensorType,
    /// Innermost first.
    pub dims: Vec<u64>,
    pub data: &'a [u8],
}

/// Writes `contents` to `path` and returns the manifest it stored. The file
/// is signed when `secret_key` is given.
///
/// The file is written next to `path` under a temporary name, read back
/// through the same checks as [`crate::KtcFile::open`], and only then moved
/// into place, so a failed write never leaves a broken file at `path`.
pub fn write(
    path: impl AsRef<Path>,
    contents: &Contents,
    secret_key: Option<&[u8; 32]>,
) -> Result<Manifest, Error> {
    let path = path.as_ref();
    let mut manifest = layout(contents);
    file::check_tensors(&manifest)?;
    let data_offset = ((HEADER_LEN + to_json(&manifest)?.len()) as u64).next_multiple_of(ALIGNMENT);

    let partial = partial_path(path);
    let result = write_partial(&partial, contents, &mut manifest, data_offset, secret_key)
        .and_then(|()| {
            let file = File::open(&partial)?;
            // SAFETY: read-only map of the file this function just wrote.
            Ktc::parse(&unsafe { Mmap::map(&file)? })?;
            Ok(())
        })
        .and_then(|()| Ok(fs::rename(&partial, path)?));
    if result.is_err() {
        let _ = fs::remove_file(&partial);
    }
    result.map(|()| manifest)
}

/// The manifest with every offset and size filled in and zero hashes.
fn layout(c: &Contents) -> Manifest {
    let mut end = 0;
    let tensors = c
        .tensors
        .iter()
        .map(|t| {
            let offset = u64::next_multiple_of(end, ALIGNMENT);
            end = offset + t.data.len() as u64;
            Tensor {
                name: t.name.clone(),
                ty: t.ty,
                dims: t.dims.clone(),
                offset,
                size: t.data.len() as u64,
            }
        })
        .collect();
    let mut sections = vec![Section {
        name: TENSORS.into(),
        offset: 0,
        size: end,
        blake3: [0; 32],
    }];
    for (name, data) in &c.sections {
        let offset = end.next_multiple_of(ALIGNMENT);
        end = offset + data.len() as u64;
        sections.push(Section {
            name: name.clone(),
            offset,
            size: data.len() as u64,
            blake3: [0; 32],
        });
    }
    Manifest {
        name: c.name.clone(),
        architecture: c.architecture.clone(),
        hyperparameters: c.hyperparameters.clone(),
        tokenizer: c.tokenizer.clone(),
        chat_template: c.chat_template.clone(),
        metadata: c.metadata.clone(),
        tensors,
        sections,
        execution_profile: c.execution_profile.clone(),
    }
}

/// Streams the data while hashing it, then fills in the manifest. Hashes are
/// fixed-width hex, so the final manifest is exactly as long as the one the
/// data offset was computed from.
fn write_partial(
    path: &Path,
    c: &Contents,
    manifest: &mut Manifest,
    data_offset: u64,
    secret_key: Option<&[u8; 32]>,
) -> Result<(), Error> {
    let mut out = BufWriter::with_capacity(1 << 20, File::create(path)?);
    out.write_all(&vec![0; data_offset as usize])?;
    let mut pos = 0;
    let mut hasher = blake3::Hasher::new();
    for (t, entry) in c.tensors.iter().zip(&manifest.tensors) {
        let pad = vec![0; (entry.offset - pos) as usize];
        out.write_all(&pad)?;
        hasher.update(&pad);
        out.write_all(t.data)?;
        hasher.update_rayon(t.data);
        pos = entry.offset + entry.size;
    }
    manifest.sections[0].blake3 = hasher.finalize().into();
    for ((_, data), entry) in c.sections.iter().zip(&mut manifest.sections[1..]) {
        out.write_all(&vec![0; (entry.offset - pos) as usize])?;
        out.write_all(data)?;
        entry.blake3 = blake3::Hasher::new().update_rayon(data).finalize().into();
        pos = entry.offset + entry.size;
    }

    let bytes = to_json(manifest)?;
    let header = header(
        bytes.len() as u64,
        data_offset,
        secret_key.map(|k| sign(&bytes, k)),
    );
    let mut file = out.into_inner().map_err(|e| e.into_error())?;
    file.seek(SeekFrom::Start(0))?;
    file.write_all(&header)?;
    file.write_all(&bytes)?;
    Ok(())
}

fn to_json(manifest: &Manifest) -> Result<Vec<u8>, Error> {
    serde_json::to_vec(manifest).map_err(|e| invalid(format!("manifest: {e}")))
}

fn header(manifest_len: u64, data_offset: u64, signature: Option<[u8; 64]>) -> [u8; HEADER_LEN] {
    let mut h = [0; HEADER_LEN];
    h[..4].copy_from_slice(MAGIC);
    h[4..8].copy_from_slice(&VERSION.to_le_bytes());
    if let Some(signature) = signature {
        h[file::FLAGS].copy_from_slice(&FLAG_SIGNED.to_le_bytes());
        h[file::SIGNATURE].copy_from_slice(&signature);
    }
    h[16..24].copy_from_slice(&manifest_len.to_le_bytes());
    h[24..32].copy_from_slice(&data_offset.to_le_bytes());
    h
}

fn partial_path(path: &Path) -> PathBuf {
    let mut name = path.file_name().unwrap_or_default().to_owned();
    name.push(".partial");
    path.with_file_name(name)
}
