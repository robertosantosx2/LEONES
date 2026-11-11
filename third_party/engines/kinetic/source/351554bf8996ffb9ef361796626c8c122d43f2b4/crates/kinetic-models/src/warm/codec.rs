//! The byte form of a [`State`]: little-endian words with a running
//! checksum, every length checked against the model before anything is
//! allocated. An open checkpoint is not part of it.

use std::io::{self, Read, Write};

use super::hash::Hasher;
use crate::blocks::{Mixer, MixerState};
use crate::model::Mark;
use crate::{Model, State};

/// Longest sequence a stored state may claim, far beyond any context.
pub const MAX_TOKENS: usize = 1 << 26;

const CHUNK: usize = 1 << 16;

pub fn invalid(what: &str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, what)
}

pub struct Writer<W> {
    inner: W,
    hash: Hasher,
}

impl<W: Write> Writer<W> {
    pub fn new(inner: W) -> Self {
        Writer {
            inner,
            hash: Hasher::default(),
        }
    }

    pub fn u64(&mut self, v: u64) -> io::Result<()> {
        self.hash.word(v);
        self.inner.write_all(&v.to_le_bytes())
    }

    pub fn u32s(&mut self, v: &[u32]) -> io::Result<()> {
        self.words(v.len(), v.iter().copied())
    }

    pub fn f32s(&mut self, v: &[f32]) -> io::Result<()> {
        self.words(v.len(), v.iter().map(|x| x.to_bits()))
    }

    fn words(&mut self, len: usize, words: impl Iterator<Item = u32>) -> io::Result<()> {
        self.u64(len as u64)?;
        let mut buf = Vec::with_capacity(CHUNK);
        for w in words {
            self.hash.word(w.into());
            buf.extend_from_slice(&w.to_le_bytes());
            if buf.len() == CHUNK {
                self.inner.write_all(&buf)?;
                buf.clear();
            }
        }
        self.inner.write_all(&buf)
    }

    /// Appends the checksum of everything written and returns the sink.
    pub fn finish(mut self) -> io::Result<W> {
        let sum = self.hash.finish();
        self.inner.write_all(&sum.to_le_bytes())?;
        Ok(self.inner)
    }
}

pub struct Reader<R> {
    inner: R,
    hash: Hasher,
}

impl<R: Read> Reader<R> {
    pub fn new(inner: R) -> Self {
        Reader {
            inner,
            hash: Hasher::default(),
        }
    }

    fn raw(&mut self) -> io::Result<u64> {
        let mut b = [0; 8];
        self.inner.read_exact(&mut b)?;
        Ok(u64::from_le_bytes(b))
    }

    pub fn u64(&mut self) -> io::Result<u64> {
        let v = self.raw()?;
        self.hash.word(v);
        Ok(v)
    }

    /// A length of at most `max`.
    pub fn len(&mut self, max: usize) -> io::Result<usize> {
        usize::try_from(self.u64()?)
            .ok()
            .filter(|&n| n <= max)
            .ok_or_else(|| invalid("length out of range"))
    }

    pub fn u32s(&mut self, max: usize) -> io::Result<Vec<u32>> {
        let len = self.len(max)?;
        self.words(len)
    }

    /// Exactly `len` values; anything else means the file is not for this
    /// model.
    pub fn f32s(&mut self, len: usize) -> io::Result<Vec<f32>> {
        if self.len(usize::MAX)? != len {
            return Err(invalid("buffer size does not match the model"));
        }
        Ok(self.words(len)?.into_iter().map(f32::from_bits).collect())
    }

    fn words(&mut self, len: usize) -> io::Result<Vec<u32>> {
        let mut out = Vec::with_capacity(len);
        let mut buf = vec![0; CHUNK];
        while out.len() < len {
            let n = (len - out.len()).min(CHUNK / 4);
            self.inner.read_exact(&mut buf[..4 * n])?;
            for b in buf[..4 * n].chunks_exact(4) {
                let w = u32::from_le_bytes([b[0], b[1], b[2], b[3]]);
                self.hash.word(w.into());
                out.push(w);
            }
        }
        Ok(out)
    }

    /// Checks the checksum [`Writer::finish`] appended.
    pub fn finish(mut self) -> io::Result<()> {
        let want = self.hash.finish();
        if self.raw()? != want {
            return Err(invalid("checksum mismatch"));
        }
        Ok(())
    }
}

pub fn write_state<W: Write>(w: &mut Writer<W>, state: &State) -> io::Result<()> {
    w.u64(state.pos as u64)?;
    for layer in &state.layers {
        write_buffers(w, layer)?;
    }
    w.u64(state.marks.len() as u64)?;
    for mark in &state.marks {
        w.u64(mark.pos as u64)?;
        for layer in &mark.layers {
            w.u64(layer.is_some().into())?;
            if let Some(s) = layer {
                write_buffers(w, s)?;
            }
        }
    }
    Ok(())
}

fn write_buffers<W: Write>(w: &mut Writer<W>, state: &MixerState) -> io::Result<()> {
    state.buffers().into_iter().try_for_each(|b| w.f32s(b))
}

/// Reads a state written by [`write_state`] for the same model.
pub fn read_state<R: Read>(r: &mut Reader<R>, model: &Model) -> io::Result<State> {
    let mut state = model.new_state();
    state.pos = r.len(MAX_TOKENS)?;
    for (layer, ls) in model.layers.iter().zip(&mut state.layers) {
        read_buffers(r, &layer.mixer, ls, state.pos)?;
    }
    let n = r.len(state.pos + 1)?;
    for _ in 0..n {
        let pos = r.len(state.pos)?;
        if state.marks.last().is_some_and(|m| m.pos >= pos) {
            return Err(invalid("marks out of order"));
        }
        let mut layers = Vec::with_capacity(model.layers.len());
        for layer in &model.layers {
            let present = r.u64()?;
            if present != u64::from(layer.mixer.needs_mark()) {
                return Err(invalid("mark does not match the model"));
            }
            layers.push(if present == 1 {
                let mut s = layer.mixer.new_state();
                read_buffers(r, &layer.mixer, &mut s, pos)?;
                Some(s)
            } else {
                None
            });
        }
        state.marks.push(Mark { pos, layers });
    }
    Ok(state)
}

fn read_buffers<R: Read>(
    r: &mut Reader<R>,
    mixer: &Mixer,
    state: &mut MixerState,
    pos: usize,
) -> io::Result<()> {
    for (buf, len) in state.buffers_mut().into_iter().zip(mixer.buffer_lens(pos)) {
        *buf = r.f32s(len)?;
    }
    Ok(())
}

/// Bytes a state takes in memory, marks included.
pub fn state_bytes(state: &State) -> usize {
    let layer = |s: &MixerState| s.buffers().iter().map(|b| b.len()).sum::<usize>();
    let marks: usize = state
        .marks
        .iter()
        .flat_map(|m| m.layers.iter().flatten())
        .map(layer)
        .sum();
    4 * (state.layers.iter().map(layer).sum::<usize>() + marks)
}
