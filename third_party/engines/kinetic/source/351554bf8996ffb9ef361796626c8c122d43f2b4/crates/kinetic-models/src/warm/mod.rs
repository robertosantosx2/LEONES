//! Warm starts: prompts that begin like an earlier one resume from that
//! one's exact state and run only their new tokens.
//!
//! Agents and chat clients resend the same system prompt, tools and history
//! with every request. [`Warm`] keeps the states those prompts left behind,
//! in memory under a byte budget and optionally on disk, and starts each
//! new prompt from the longest cached prefix it can return to exactly.
//! Attention caches cut back to any length; recurrent layers only to the
//! marks taken every few hundred tokens, where prompts part and where they
//! resume.
//!
//! A restored state is bit for bit the one its run left behind, so a warm
//! prefill gives exactly the logits of a cold one on models whose results
//! do not depend on how a prompt is split into batches, as the speculative
//! decoder already requires of every block. Otherwise it matches a cold run
//! with the same batch boundaries, and a single batch up to rounding;
//! [`Warm::aligned`] makes those boundaries the same by construction.

mod codec;
mod disk;
mod hash;
#[cfg(test)]
mod tests;

use std::fs::File;
use std::io::{self, Read};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::{Duration, Instant, SystemTime};

use crate::{Model, State};
use disk::Disk;
use hash::Hasher;

/// Marks are taken at multiples of this many tokens, or of a larger
/// multiple of it when a mark is expensive next to the cache it saves.
const GRID: usize = 256;
const MAX_GRID: usize = 8192;

/// What runs prompts for a [`Warm`] cache: the [`Model`] itself, or a copy
/// of it on a device whose states have an exact host form.
pub trait Runner {
    /// A sequence's state where it runs.
    type State;
    /// The runner's copy of a host state.
    fn restore(&self, state: State) -> Self::State;
    /// Number of tokens `state` has run.
    fn len(&self, state: &Self::State) -> usize;
    /// Runs `tokens` and returns the logits after the last one.
    fn forward(&self, state: &mut Self::State, tokens: &[u32]) -> Vec<f32>;
    /// Saves what a later truncation needs to return to the current length,
    /// as [`Model::mark`] does.
    fn mark(&self, state: &mut Self::State);
    /// Seconds per byte of host state that [`Runner::restore`] is expected
    /// to take before any restore has been timed.
    fn restore_rate(&self) -> f64;
}

impl Runner for Model<'_> {
    type State = State;

    fn restore(&self, state: State) -> State {
        state
    }

    fn len(&self, state: &State) -> usize {
        state.len()
    }

    fn forward(&self, state: &mut State, tokens: &[u32]) -> Vec<f32> {
        self.forward_batch(state, tokens)
    }

    fn mark(&self, state: &mut State) {
        Model::mark(self, state);
    }

    fn restore_rate(&self) -> f64 {
        // A clone, at the speed of a memory copy.
        1.0 / 8e9
    }
}

/// What a prefill reused and what it cost.
pub struct Prefill<S = State> {
    /// The state after the whole prompt, ready to decode from.
    pub state: S,
    /// Logits after the last prompt token.
    pub logits: Vec<f32>,
    /// Prompt tokens restored from the cache rather than run.
    pub hit: usize,
    pub elapsed: Duration,
    /// Estimated time running the restored tokens would have taken, from
    /// the speed measured when they first ran.
    pub saved: Duration,
}

/// What an entry holds, without its state: enough to rank it for a prompt.
#[derive(Clone, PartialEq)]
struct Meta {
    tokens: Vec<u32>,
    marks: Vec<usize>,
    /// Whether the state cuts back to any shorter length in place.
    in_place: bool,
    /// Seconds per token of the prefill that produced it.
    rate: f64,
}

impl Meta {
    /// The longest length up to `len` the entry's state returns to exactly,
    /// as [`Model::reach`] gives it.
    fn reach(&self, len: usize) -> usize {
        let len = len.min(self.tokens.len());
        if len == self.tokens.len() || self.in_place {
            return len;
        }
        self.marks
            .iter()
            .copied()
            .filter(|&m| m <= len)
            .max()
            .unwrap_or(0)
    }

    /// Whether every length `old` returns to is also reachable from here.
    fn covers(&self, old: &Meta) -> bool {
        let n = old.tokens.len();
        self.tokens.starts_with(&old.tokens)
            && (self.in_place || !old.in_place)
            && old.marks.iter().chain([&n]).all(|&m| self.reach(m) == m)
    }

    /// The tokens of `prompt` a warm start from this entry skips, a
    /// multiple of `align`. Running at least one token is needed for
    /// logits, unless the entry is the whole prompt and has them.
    fn hit(&self, prompt: &[u32], align: usize) -> usize {
        let common = common_prefix(&self.tokens, prompt);
        if common == prompt.len() && self.tokens.len() == prompt.len() {
            return common;
        }
        let mut len = common.min(prompt.len() - 1);
        loop {
            let reached = self.reach(len / align * align);
            if reached.is_multiple_of(align) {
                return reached;
            }
            len = reached;
        }
    }
}

struct Entry {
    meta: Meta,
    /// Shared with a disk write still running.
    saved: Arc<Saved>,
    bytes: usize,
    used: u64,
}

struct Saved {
    state: State,
    /// Logits after the last token.
    logits: Vec<f32>,
}

impl Entry {
    fn new(meta: Meta, state: State, logits: Vec<f32>) -> Entry {
        let bytes = codec::state_bytes(&state) + 4 * (logits.len() + meta.tokens.len());
        Entry {
            meta,
            saved: Arc::new(Saved { state, logits }),
            bytes,
            used: 0,
        }
    }
}

/// Seconds per byte of reading a cached state from disk before any read
/// has been timed.
const LOAD_RATE: f64 = 1.0 / 5e8;

/// A prefix cache of exact model states for one model.
pub struct Warm<'m> {
    model: &'m Model<'m>,
    model_id: u64,
    grid: Option<usize>,
    /// Batches start at multiples of this, and so do warm starts.
    align: usize,
    budget: usize,
    clock: u64,
    entries: Vec<Entry>,
    disk: Option<Disk>,
    /// Seconds per token of the latest prefill.
    rate: f64,
    /// Measured seconds per byte of restoring a state on the runner, and of
    /// reading one from disk.
    restore_rate: Option<f64>,
    load_rate: f64,
}

impl<'m> Warm<'m> {
    /// An empty cache for `model` holding up to `memory_bytes` of states.
    /// `model_id` must identify the model file and the code that runs it;
    /// see [`model_id`].
    pub fn new(model: &'m Model<'m>, model_id: u64, memory_bytes: usize) -> Warm<'m> {
        Warm {
            model,
            model_id,
            grid: grid(model),
            align: 1,
            budget: memory_bytes,
            clock: 0,
            entries: Vec::new(),
            disk: None,
            rate: 0.0,
            restore_rate: None,
            load_rate: LOAD_RATE,
        }
    }

    /// Also keeps every inserted entry in `dir`, up to `budget` bytes, and
    /// finds those of earlier runs there. See [`default_dir`].
    pub fn with_disk(mut self, dir: impl Into<PathBuf>, budget: u64) -> io::Result<Self> {
        self.disk = Some(Disk::open(dir.into(), budget, self.model_id)?);
        Ok(self)
    }

    /// Runs prompts in batches of at most `tokens` that start at multiples
    /// of it, and resumes only at such multiples or from an identical
    /// prompt. A warm start then runs exactly the batches of a cold run cut
    /// at those multiples, so it gives the same results on every model,
    /// including those whose results depend on where batches start.
    pub fn aligned(mut self, tokens: usize) -> Self {
        self.align = tokens.max(1);
        self.grid = self.grid.map(|g| g.next_multiple_of(self.align));
        self
    }

    /// Bytes of states held in memory.
    pub fn memory_bytes(&self) -> usize {
        self.entries.iter().map(|e| e.bytes).sum()
    }

    /// The number of positions between the marks of a recurrent model, or
    /// `None` when its caches cut back anywhere.
    pub fn grid(&self) -> Option<usize> {
        self.grid
    }

    /// Runs `prompt` from the longest cached prefix it can resume exactly,
    /// marking the state on the grid as it goes and where the prompt leaves
    /// the cached ones, so that the next prompt sharing that prefix resumes
    /// at its end. The cache is not changed; hand the state to
    /// [`Warm::insert`] when it is worth keeping, after the prompt or after
    /// the reply.
    pub fn prefill(&mut self, prompt: &[u32]) -> Prefill {
        let model = self.model;
        self.prefill_on(model, prompt)
    }

    /// [`Warm::prefill`] with the uncached tokens run by `runner`, whose
    /// states must give the same results as the ones cached here, which
    /// is what [`device_id`] keeps apart.
    pub fn prefill_on<R: Runner>(&mut self, runner: &R, prompt: &[u32]) -> Prefill<R::State> {
        assert!(!prompt.is_empty(), "empty prompt");
        let start = Instant::now();
        let disk = self
            .disk
            .iter()
            .flat_map(|d| d.files.iter().map(|f| &f.meta));
        let branch = self
            .entries
            .iter()
            .map(|e| &e.meta)
            .chain(disk)
            .map(|m| common_prefix(&m.tokens, prompt))
            .max()
            .unwrap_or(0)
            / self.align
            * self.align;
        let (mut state, hit, cached, rate) = self.restore(runner, prompt);
        let logits = match cached {
            Some(logits) => logits,
            None => {
                let run = Instant::now();
                if hit > 0 && self.grid.is_some() {
                    // Lets the entry this one grows from be dropped as covered.
                    runner.mark(&mut state);
                }
                let logits = self.run(runner, &mut state, &prompt[hit..], branch);
                self.rate = run.elapsed().as_secs_f64() / (prompt.len() - hit) as f64;
                logits
            }
        };
        Prefill {
            state,
            logits,
            hit,
            elapsed: start.elapsed(),
            saved: Duration::from_secs_f64(rate * hit as f64),
        }
    }

    /// The state after the longest prefix of `prompt` the cache returns to
    /// exactly, restored on `runner`, and that prefix's length: a multiple
    /// of the alignment unless it is all of `prompt`, and zero with a new
    /// state when nothing pays off. [`Warm::prefill_on`] without running
    /// the rest, for callers that run it in batches of their own.
    pub fn resume_on<R: Runner>(&mut self, runner: &R, prompt: &[u32]) -> (R::State, usize) {
        assert!(!prompt.is_empty(), "empty prompt");
        let (state, hit, _, _) = self.restore(runner, prompt);
        (state, hit)
    }

    /// The restored state, its length, its logits when it is all of
    /// `prompt`, and the seconds per token of the run that made it.
    fn restore<R: Runner>(
        &mut self,
        runner: &R,
        prompt: &[u32],
    ) -> (R::State, usize, Option<Vec<f32>>, f64) {
        let restore_rate = self.restore_rate.unwrap_or_else(|| runner.restore_rate());
        match self.find(prompt, restore_rate) {
            Some((i, hit)) => {
                let restore = Instant::now();
                self.clock += 1;
                let e = &mut self.entries[i];
                e.used = self.clock;
                let mut state = e.saved.state.clone();
                let logits = (hit == prompt.len()).then(|| e.saved.logits.clone());
                let reached = self.model.truncate(&mut state, hit);
                debug_assert_eq!(reached, hit);
                let (rate, bytes) = (e.meta.rate, e.bytes);
                let state = runner.restore(state);
                let measured = restore.elapsed().as_secs_f64() / bytes.max(1) as f64;
                self.restore_rate = Some(average(self.restore_rate, measured));
                (state, hit, logits, rate)
            }
            None => (runner.restore(self.model.new_state()), 0, None, 0.0),
        }
    }

    /// Whether keeping the state after the first `tokens` tokens of a
    /// prompt is expected to pay off: a later prompt that resumes from it
    /// must save more prefill time than restoring and saving it cost. Until
    /// a prefill has been timed, every state is worth keeping.
    pub fn worth_keeping<R: Runner>(&self, runner: &R, tokens: usize) -> bool {
        let bytes: usize = self
            .model
            .layers
            .iter()
            .flat_map(|l| l.mixer.buffer_lens(tokens))
            .sum::<usize>()
            * 4;
        let restore = self.restore_rate.unwrap_or_else(|| runner.restore_rate());
        tokens as f64 * self.rate >= 2.0 * bytes as f64 * restore
    }

    /// Keeps a copy of `state`, which `tokens` produced and whose next-token
    /// logits are `logits`. Entries it makes redundant are dropped, and the
    /// least recently used ones go once memory is over budget. The copy is
    /// in memory either way and the disk write runs in the background; an
    /// error means only that the write could not start.
    pub fn insert(&mut self, tokens: &[u32], state: &State, logits: &[f32]) -> io::Result<()> {
        assert_eq!(tokens.len(), state.len(), "tokens do not match the state");
        assert_eq!(
            logits.len(),
            self.model.n_vocab(),
            "logits of another model"
        );
        let state = state.clone();
        let in_place = self
            .model
            .layers
            .iter()
            .all(|l| l.mixer.truncates_in_place(state.len()));
        let meta = Meta {
            tokens: tokens.to_vec(),
            marks: state.marks().collect(),
            in_place,
            rate: self.rate,
        };
        let mut entry = Entry::new(meta, state, logits.to_vec());
        let saved = self
            .disk
            .as_mut()
            .map_or(Ok(()), |d| d.save(&entry.meta, &entry.saved, entry.bytes));

        self.entries.retain(|e| !entry.meta.covers(&e.meta));
        self.clock += 1;
        entry.used = self.clock;
        self.keep(entry);
        saved
    }

    fn keep(&mut self, entry: Entry) {
        if entry.bytes > self.budget {
            return;
        }
        self.entries.push(entry);
        while self.memory_bytes() > self.budget {
            let oldest = (0..self.entries.len())
                .min_by_key(|&i| self.entries[i].used)
                .expect("over budget with no entries");
            self.entries.swap_remove(oldest);
        }
    }

    /// The entry, by index into memory, to resume `prompt` from and how many
    /// of its tokens to keep: the one that saves the most prefill time over
    /// restoring it at `restore_rate` seconds per byte, and for a file also
    /// over reading it; a file is loaded first. `None` when running the
    /// prompt from the start is expected to be as fast.
    fn find(&mut self, prompt: &[u32], restore_rate: f64) -> Option<(usize, usize)> {
        let rate = self.rate;
        let align = self.align;
        let gain = |m: &Meta, bytes: usize, read: f64| {
            let hit = m.hit(prompt, align);
            let per_token = if m.rate > 0.0 { m.rate } else { rate };
            // Until a prefill has been timed, any hit is taken.
            let saved = if per_token > 0.0 {
                hit as f64 * per_token
            } else {
                f64::INFINITY
            };
            (hit, saved - bytes as f64 * (restore_rate + read))
        };
        let best = |gains: &mut dyn Iterator<Item = (usize, f64)>| {
            gains
                .enumerate()
                .filter(|&(_, (hit, gain))| hit > 0 && gain > 0.0)
                .max_by(|a, b| a.1 .1.total_cmp(&b.1 .1))
                .map(|(i, (hit, gain))| (i, hit, gain))
        };
        let memory = best(&mut self.entries.iter().map(|e| gain(&e.meta, e.bytes, 0.0)));
        let load_rate = self.load_rate;
        let on_disk = self
            .disk
            .as_ref()
            .and_then(|d| best(&mut d.files.iter().map(|f| gain(&f.meta, f.bytes, load_rate))));
        let disk = self.disk.as_mut().zip(on_disk);
        if let Some((disk, (i, hit, _))) = disk.filter(|d| memory.is_none_or(|m| d.1 .2 > m.2)) {
            let start = Instant::now();
            let bytes = disk.files[i].bytes;
            if let Ok(mut entry) = disk.load(i, self.model) {
                let measured = start.elapsed().as_secs_f64() / bytes.max(1) as f64;
                self.load_rate = average(Some(self.load_rate), measured);
                self.clock += 1;
                entry.used = self.clock;
                self.keep(entry);
                if let Some(at) = self.entries.iter().position(|e| e.used == self.clock) {
                    return Some((at, hit));
                }
            }
        }
        memory.map(|(i, hit, _)| (i, hit))
    }

    /// Runs `tokens` in batches that end on the grid, at length `branch`
    /// and at multiples of the alignment, marking the state on the grid and
    /// at `branch`, and returns the logits after the last token. Models whose
    /// caches cut back anywhere need no marks.
    fn run<R: Runner>(
        &self,
        runner: &R,
        state: &mut R::State,
        tokens: &[u32],
        branch: usize,
    ) -> Vec<f32> {
        let next = |len: usize, step: usize| len + step - len % step;
        let mut logits = Vec::new();
        let mut rest = tokens;
        while !rest.is_empty() {
            let len = runner.len(state);
            let mark = self.grid.map(|g| match next(len, g) {
                on_grid if branch > len => on_grid.min(branch),
                on_grid => on_grid,
            });
            let cut = match self.align {
                1 => usize::MAX,
                align => next(len, align),
            };
            let stop = mark.unwrap_or(usize::MAX).min(cut);
            let (batch, tail) = rest.split_at((stop - len).min(rest.len()));
            logits = runner.forward(state, batch);
            if Some(runner.len(state)) == mark {
                runner.mark(state);
            }
            rest = tail;
        }
        logits
    }
}

/// Mark spacing for `model`: none if every layer cuts back in place,
/// otherwise wide enough that a mark costs about as much memory as the
/// attention cache of the tokens between two marks.
fn grid(model: &Model) -> Option<usize> {
    let bytes = |pos: usize, marked: bool| -> usize {
        model
            .layers
            .iter()
            .filter(|l| l.mixer.needs_mark() == marked)
            .flat_map(|l| l.mixer.buffer_lens(pos))
            .sum()
    };
    let mark = bytes(usize::MAX, true);
    if mark == 0 {
        return None;
    }
    let per_token = bytes(1, false).max(1);
    Some(
        (mark / per_token)
            .next_multiple_of(GRID)
            .clamp(GRID, MAX_GRID),
    )
}

/// `measured` folded into the running average `old`.
fn average(old: Option<f64>, measured: f64) -> f64 {
    old.map_or(measured, |old| 0.5 * (old + measured))
}

fn common_prefix(a: &[u32], b: &[u32]) -> usize {
    a.iter().zip(b).take_while(|(a, b)| a == b).count()
}

/// Identifies the model file at `path` together with this build of the
/// code that runs it: its size, modification time and leading megabyte,
/// and the crate version. A new file or a new release starts a new cache.
pub fn model_id(path: impl AsRef<Path>) -> io::Result<u64> {
    let file = File::open(path)?;
    let meta = file.metadata()?;
    let modified = meta
        .modified()?
        .duration_since(SystemTime::UNIX_EPOCH)
        .unwrap_or_default();
    let mut head = Vec::new();
    file.take(1 << 20).read_to_end(&mut head)?;
    let mut h = Hasher::default();
    h.word(meta.len());
    h.word(modified.as_nanos() as u64);
    h.bytes(&head);
    h.bytes(env!("CARGO_PKG_VERSION").as_bytes());
    Ok(h.finish())
}

/// `model_id` for states that `device`, such as "cuda", ran: devices round
/// differently, so each resumes only from states it produced itself.
pub fn device_id(model_id: u64, device: &str) -> u64 {
    let mut h = Hasher::default();
    h.word(model_id);
    h.bytes(device.as_bytes());
    h.finish()
}

/// `kinetic/warm` in the user's cache directory: `%LOCALAPPDATA%` on
/// Windows, `~/Library/Caches` on macOS, `$XDG_CACHE_HOME` or `~/.cache`
/// elsewhere.
pub fn default_dir() -> Option<PathBuf> {
    let var = |name| {
        std::env::var_os(name)
            .filter(|v| !v.is_empty())
            .map(PathBuf::from)
    };
    let base = if cfg!(windows) {
        var("LOCALAPPDATA")
    } else if cfg!(target_os = "macos") {
        var("HOME").map(|h| h.join("Library").join("Caches"))
    } else {
        var("XDG_CACHE_HOME").or_else(|| var("HOME").map(|h| h.join(".cache")))
    }?;
    Some(base.join("kinetic").join("warm"))
}
