//! Cached states on disk, one file per entry. Files are written under a
//! temporary name and renamed, so a reader never sees half a file, and any
//! of them can be deleted at any time; the oldest go first once the
//! directory outgrows its budget.

use std::fs::{self, File};
use std::io::{self, BufReader, BufWriter};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::thread::{self, JoinHandle};
use std::time::SystemTime;

use super::codec::{self, invalid, Reader, Writer, MAX_TOKENS};
use super::{hash::Hasher, Entry, Meta, Saved};
use crate::Model;

const MAGIC: u64 = u64::from_le_bytes(*b"KNWARM\0\0");
/// Bump whenever the layout of a file changes; older files are then skipped
/// and age out.
const VERSION: u64 = 1;
const EXT: &str = "kwarm";
const TEMP_EXT: &str = "kwarm-tmp";

pub struct Disk {
    dir: PathBuf,
    budget: u64,
    model_id: u64,
    /// The usable files for this model.
    pub files: Vec<Indexed>,
    /// The file being written in the background, if any.
    writing: Option<JoinHandle<()>>,
}

/// A cache file: where it is, what it holds and its size.
pub struct Indexed {
    pub path: PathBuf,
    pub meta: Meta,
    pub bytes: usize,
}

impl Disk {
    /// Opens `dir`, creating it readable by the current user only, and
    /// indexes the files written for `model_id` from their headers.
    pub fn open(dir: PathBuf, budget: u64, model_id: u64) -> io::Result<Disk> {
        create_private_dir(&dir)?;
        let mut files = Vec::new();
        for (path, len, _) in cache_files(&dir)? {
            if path.extension().is_some_and(|e| e == EXT) {
                if let Ok(meta) = read_header(&path, model_id) {
                    files.push(Indexed {
                        path,
                        meta,
                        bytes: len as usize,
                    });
                }
            }
        }
        Ok(Disk {
            dir,
            budget,
            model_id,
            files,
            writing: None,
        })
    }

    /// Writes `saved`, which `meta` describes and which takes `bytes` in
    /// memory, in the background, then drops
    /// the files it covers and trims the directory to its budget. The index
    /// takes the file at once; one whose write failed is dropped when a
    /// read of it fails.
    pub fn save(&mut self, meta: &Meta, saved: &Arc<Saved>, bytes: usize) -> io::Result<()> {
        self.wait();
        let mut key = Hasher::default();
        key.word(self.model_id);
        meta.tokens.iter().for_each(|&t| key.word(t.into()));
        let path = self.dir.join(format!("{:016x}.{EXT}", key.finish()));
        let temp = path.with_extension(format!("{}.{TEMP_EXT}", std::process::id()));

        let (covered, kept): (Vec<_>, Vec<_>) = self
            .files
            .drain(..)
            .filter(|f| f.path != path)
            .partition(|f| meta.covers(&f.meta));
        self.files = kept;
        self.files.push(Indexed {
            path: path.clone(),
            meta: meta.clone(),
            bytes,
        });
        let (dir, budget, model_id) = (self.dir.clone(), self.budget, self.model_id);
        let (meta, saved) = (meta.clone(), Arc::clone(saved));
        self.writing = Some(thread::Builder::new().spawn(move || {
            let written =
                write_entry(&temp, model_id, &meta, &saved).and_then(|()| fs::rename(&temp, &path));
            if written.is_err() {
                let _ = fs::remove_file(&temp);
                return;
            }
            for f in covered {
                let _ = fs::remove_file(&f.path);
            }
            let _ = trim(&dir, budget);
        })?);
        Ok(())
    }

    /// Reads file `i` in full. A file that fails its checks is deleted.
    pub fn load(&mut self, i: usize, model: &Model) -> io::Result<Entry> {
        self.wait();
        let f = &self.files[i];
        let entry = read_entry(&f.path, self.model_id, &f.meta, model);
        if entry.is_ok() {
            let _ = File::options()
                .write(true)
                .open(&f.path)
                .and_then(|f| f.set_modified(SystemTime::now()));
        } else {
            let _ = fs::remove_file(&f.path);
            self.files.remove(i);
        }
        entry
    }

    /// Waits for the background write, if one is running.
    fn wait(&mut self) {
        if let Some(writing) = self.writing.take() {
            let _ = writing.join();
        }
    }
}

impl Drop for Disk {
    fn drop(&mut self) {
        self.wait();
    }
}

/// Deletes the oldest cache files in `dir`, of any model, until it fits
/// `budget`.
fn trim(dir: &Path, budget: u64) -> io::Result<()> {
    let mut files = cache_files(dir)?;
    files.sort_by_key(|f| f.2);
    let mut total: u64 = files.iter().map(|f| f.1).sum();
    for (path, len, _) in files {
        if total <= budget {
            break;
        }
        if fs::remove_file(&path).is_ok() {
            total -= len;
        }
    }
    Ok(())
}

fn create_private_dir(dir: &Path) -> io::Result<()> {
    let mut builder = fs::DirBuilder::new();
    builder.recursive(true);
    #[cfg(unix)]
    std::os::unix::fs::DirBuilderExt::mode(&mut builder, 0o700);
    builder.create(dir)
}

/// Every file this module writes, finished or not, with its size and age.
fn cache_files(dir: &Path) -> io::Result<Vec<(PathBuf, u64, SystemTime)>> {
    let mut out = Vec::new();
    for entry in fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        let ours = path.extension().is_some_and(|e| e == EXT || e == TEMP_EXT);
        let meta = entry.metadata()?;
        if ours && meta.is_file() {
            out.push((path, meta.len(), meta.modified()?));
        }
    }
    Ok(out)
}

fn write_entry(path: &Path, model_id: u64, meta: &Meta, saved: &Saved) -> io::Result<()> {
    let mut w = Writer::new(BufWriter::new(File::create(path)?));
    for v in [MAGIC, VERSION, model_id] {
        w.u64(v)?;
    }
    w.u32s(&meta.tokens)?;
    w.u64(meta.marks.len() as u64)?;
    for &m in &meta.marks {
        w.u64(m as u64)?;
    }
    w.u64(meta.in_place.into())?;
    w.u64(meta.rate.to_bits())?;
    codec::write_state(&mut w, &saved.state)?;
    w.f32s(&saved.logits)?;
    io::Write::flush(&mut w.finish()?)
}

fn header<R: io::Read>(r: &mut Reader<R>, model_id: u64) -> io::Result<Meta> {
    if r.u64()? != MAGIC || r.u64()? != VERSION || r.u64()? != model_id {
        return Err(invalid("not a cache file for this model and version"));
    }
    let tokens = r.u32s(MAX_TOKENS)?;
    let n = r.len(tokens.len() + 1)?;
    let marks = (0..n)
        .map(|_| r.len(tokens.len()))
        .collect::<io::Result<_>>()?;
    let in_place = r.u64()? == 1;
    let rate = f64::from_bits(r.u64()?);
    Ok(Meta {
        tokens,
        marks,
        in_place,
        rate,
    })
}

fn read_header(path: &Path, model_id: u64) -> io::Result<Meta> {
    header(
        &mut Reader::new(BufReader::new(File::open(path)?)),
        model_id,
    )
}

fn read_entry(path: &Path, model_id: u64, meta: &Meta, model: &Model) -> io::Result<Entry> {
    let mut r = Reader::new(BufReader::with_capacity(1 << 20, File::open(path)?));
    if header(&mut r, model_id)? != *meta {
        return Err(invalid("file changed since it was indexed"));
    }
    let state = codec::read_state(&mut r, model)?;
    let logits = r.f32s(model.n_vocab())?;
    r.finish()?;
    if state.len() != meta.tokens.len() || !state.marks().eq(meta.marks.iter().copied()) {
        return Err(invalid("state does not match its header"));
    }
    Ok(Entry::new(meta.clone(), state, logits))
}
