//! Passes that several sequences share on the device.
//!
//! The rows of every sequence in a pass go through each weight in one GEMV
//! of at most [`MAX_BATCH`] inputs, which gives every input the bits it
//! gets alone; each sequence's mixer then runs on its own rows, state and
//! scratch, so every row comes out exactly as running its sequence alone
//! gives it.

use std::ops::Range;
use std::sync::atomic::{AtomicU64, Ordering};

use kinetic_cuda::{Flow, MAX_BATCH};

use super::layer::copy_lent;
use super::scratch::{by_width, Work};
use super::{CudaModel, CudaState, Output};
use crate::convoy::Seat;
use crate::Forward;

/// One sequence's run in [`CudaModel::run_many`]: what
/// [`CudaModel::run`] takes, and whether to bring the logits back.
pub struct Run<'r> {
    pub state: &'r mut CudaState,
    pub tokens: &'r [u32],
    pub all_rows: bool,
    pub logits: bool,
}

/// What a run in [`CudaModel::run_many`] gives: the greedy token after
/// each row given to the head, and what [`CudaModel::run`] returns, the
/// logits empty unless asked for.
pub struct Ran {
    pub greedy: Vec<u32>,
    pub forward: Forward,
}

/// A run waiting in the convoy for a shared pass.
pub(super) struct Job {
    /// Owned by a caller that waits in the convoy until the pass is done.
    state: *mut CudaState,
    tokens: Vec<u32>,
    all_rows: bool,
    logits: bool,
}

/// A fresh id for a state.
pub(super) fn next_id() -> u64 {
    static NEXT: AtomicU64 = AtomicU64::new(0);
    NEXT.fetch_add(1, Ordering::Relaxed)
}

impl CudaModel<'_> {
    /// Takes a seat for one sequence, once no other seat is driving the
    /// device. A thread may use this model, and states and drafts made from
    /// it, only while it holds a seat or while no other thread uses them.
    /// Runs through [`Target`](crate::speculative::Target) from seated
    /// threads wait for each other, a few milliseconds at most, and share
    /// passes over the weights; [`Seat::away`] lets the others drive the
    /// device meanwhile.
    pub fn seat(&self) -> Seat<'_> {
        self.convoy.seat()
    }

    /// Seats held now.
    pub fn seats(&self) -> usize {
        self.convoy.seats()
    }

    /// [`CudaModel::run_many`] for one run, sharing a pass with the runs of
    /// other seated sequences. Panics on a device failure.
    pub(super) fn run_seated(
        &self,
        state: &mut CudaState,
        tokens: &[u32],
        all_rows: bool,
        logits: bool,
    ) -> Ran {
        let job = Job {
            state,
            tokens: tokens.to_vec(),
            all_rows,
            logits,
        };
        self.convoy.run(job, |jobs| {
            let mut runs: Vec<Run> = jobs
                .iter()
                .map(|j| Run {
                    // SAFETY: the caller that owns the state waits in the
                    // convoy until this pass hands its result back, and the
                    // convoy orders this use after the caller's last one.
                    state: unsafe { &mut *j.state },
                    tokens: &j.tokens,
                    all_rows: j.all_rows,
                    logits: j.logits,
                })
                .collect();
            self.run_many(&mut runs)
                .unwrap_or_else(|e| panic!("CUDA: {e}"))
        })
    }

    /// Runs `runs`, each on its own state, sharing passes over the weights
    /// where they can: short runs of a model with only dense layers and
    /// mixers that run one after another, up to [`MAX_BATCH`] rows a pass.
    /// The rest run alone. Every result is exactly what running alone gives.
    pub fn run_many(&self, runs: &mut [Run]) -> kinetic_cuda::Result<Vec<Ran>> {
        let mut out: Vec<Option<Ran>> = (0..runs.len()).map(|_| None).collect();
        let mut group: Vec<usize> = Vec::new();
        let mut rows = 0;
        for i in 0..=runs.len() {
            let next = runs.get(i).filter(|r| self.shares(r));
            let fits = next.is_some_and(|r| rows + r.tokens.len() <= MAX_BATCH);
            if !fits && !group.is_empty() {
                let mut members: Vec<(usize, &mut Run)> = runs
                    .iter_mut()
                    .enumerate()
                    .filter(|(j, _)| group.contains(j))
                    .collect();
                // the same states in the same order replay the recorded pass
                members.sort_by_key(|(_, r)| r.state.id);
                let (order, mut members): (Vec<usize>, Vec<&mut Run>) = members.into_iter().unzip();
                let done = match &mut members[..] {
                    [one] => vec![self.alone(one)?],
                    many => self.shared(many)?,
                };
                for (j, ran) in order.into_iter().zip(done) {
                    out[j] = Some(ran);
                }
                group.clear();
                rows = 0;
            }
            match runs.get_mut(i) {
                Some(r) if self.shares(r) => {
                    group.push(i);
                    rows += r.tokens.len();
                }
                Some(r) => out[i] = Some(self.alone(r)?),
                None => {}
            }
        }
        Ok(out.into_iter().map(|r| r.expect("every run ran")).collect())
    }

    /// Whether `run` can share a pass: a valid run of at most [`MAX_BATCH`]
    /// tokens, which runs as one step alone too, on a model whose layers
    /// all split.
    fn shares(&self, run: &Run) -> bool {
        let state = &*run.state;
        let since = state.checkpoint.map_or(0, |start| state.pos - start);
        self.offload.is_none()
            && self.front == 0
            && self.layers.iter().all(|l| l.mixer.widths().is_some())
            && self.check_tokens(run.tokens).is_ok()
            && run.tokens.len() <= MAX_BATCH
            && state.pos + run.tokens.len() <= self.context
            && (state.checkpoint.is_none() || since + run.tokens.len() <= MAX_BATCH)
    }

    fn alone(&self, run: &mut Run) -> kinetic_cuda::Result<Ran> {
        let out = self.forward(run.state, run.tokens, run.all_rows, run.logits)?;
        Ok(Ran {
            greedy: out.greedy,
            forward: Forward {
                logits: out.logits,
                hidden: out.hidden,
            },
        })
    }

    /// One pass over `runs`, which all share. The first run's scratch holds
    /// the whole batch; the others' take their own rows for their mixers.
    fn shared(&self, runs: &mut [&mut Run]) -> kinetic_cuda::Result<Vec<Ran>> {
        let (gpu, d) = (&self.gpu, self.n_embd);
        let stream = &gpu.stream;
        let mut starts = Vec::with_capacity(runs.len());
        let mut total = 0;
        for r in runs.iter() {
            starts.push(total);
            total += r.tokens.len();
        }
        let flows: Vec<Flow> = runs
            .iter()
            .map(|r| match r.state.checkpoint {
                None => Flow::Commit,
                Some(start) => Flow::Record {
                    first: r.state.pos - start,
                },
            })
            .collect();
        for r in runs.iter_mut() {
            r.state.work.batch.set(r.state.pos, r.tokens, stream)?;
        }
        let heads: Vec<Range<usize>> = runs
            .iter()
            .zip(&starts)
            .map(|(r, &at)| {
                let end = at + r.tokens.len();
                if r.all_rows {
                    at..end
                } else {
                    end - 1..end
                }
            })
            .collect();
        let rows: usize = heads.iter().map(Range::len).sum();
        let logits = runs.iter().any(|r| r.logits);

        let one_step = !self.eager
            && rows == total
            && total == runs.len()
            && flows.iter().all(|&f| f == Flow::Commit);
        let ids: Vec<u64> = runs.iter().map(|r| r.state.id).collect();
        let (first, rest) = runs.split_first_mut().expect("a shared pass has runs");
        let lead = &mut first.state.work;
        self.embed_rows(&lead.batch, first.tokens, &mut lead.scratch.x)?;
        if let Some(p) = &self.per_layer {
            p.embed(gpu, &lead.batch, &mut lead.scratch.per_layer_tokens)?;
        }
        for (r, &at) in rest.iter_mut().zip(&starts[1..]) {
            let w = &mut r.state.work;
            self.embed_rows(&w.batch, r.tokens, &mut w.scratch.x)?;
            let x = &mut lead.scratch.x;
            x.copy_from_device(at * d, &w.scratch.x, 0..r.tokens.len() * d, stream)?;
            if let Some(p) = &self.per_layer {
                let (own, all) = (&mut w.scratch.per_layer_tokens, p.len());
                p.embed(gpu, &w.batch, own)?;
                let tokens = &mut lead.scratch.per_layer_tokens;
                tokens.copy_from_device(at * all, own, 0..r.tokens.len() * all, stream)?;
            }
        }
        if one_step {
            // perf: 4 seats on LFM3 take 8.0 ms a pass recorded, 11.0 ms launched
            let mut recorded = self.shared_step.borrow_mut();
            if recorded.as_ref().is_none_or(|(k, _)| *k != ids) {
                *recorded = None;
                let graph = stream.capture(|| {
                    self.queue_shared(lead, rest, &starts, &flows, total)?;
                    self.queue_head(&mut lead.scratch, 0..total)
                })?;
                *recorded = Some((ids, graph));
            }
            recorded
                .as_ref()
                .expect("a recorded pass")
                .1
                .launch(stream)?;
        } else {
            self.queue_shared(lead, rest, &starts, &flows, total)?;
            if rows == total {
                self.queue_head(&mut lead.scratch, 0..total)?;
            }
        }

        let s = &mut lead.scratch;
        let mut hidden = vec![0.0; total * d];
        s.h.values().copy_range_to(0, &mut hidden)?;
        let mut head = Output {
            greedy: Vec::new(),
            hidden: Vec::new(),
            logits: Vec::new(),
        };
        if rows == total {
            self.read_head(s, total, logits, &mut head)?;
        } else {
            // head rows packed into scratch this pass doesn't otherwise use
            let packed = &mut rest[0].state.work.scratch;
            let mut at = 0;
            for r in &heads {
                packed.h.copy_rows_from(at, &s.h, r.clone(), stream)?;
                at += r.len();
            }
            self.queue_head(packed, 0..rows)?;
            self.read_head(packed, rows, logits, &mut head)?;
        }

        let vocab = self.n_vocab();
        let (mut greedy, mut logit_rows) = (&head.greedy[..], &head.logits[..]);
        let mut hidden_rows = &hidden[..];
        let mut out = Vec::with_capacity(heads.len());
        for (r, rows) in std::iter::once(first)
            .chain(rest.iter_mut())
            .zip(heads.iter().map(Range::len))
        {
            let n = r.tokens.len();
            r.state.pos += n;
            let (g, rest_g) = greedy.split_at(rows);
            let (h, rest_h) = hidden_rows.split_at(n * d);
            let mine = if logits {
                let (l, rest_l) = logit_rows.split_at(rows * vocab);
                logit_rows = rest_l;
                l
            } else {
                &[]
            };
            (greedy, hidden_rows) = (rest_g, rest_h);
            out.push(Ran {
                greedy: g.to_vec(),
                forward: Forward {
                    logits: if r.logits { mine.to_vec() } else { Vec::new() },
                    hidden: h.to_vec(),
                },
            });
        }
        Ok(out)
    }

    /// Queues every layer of a shared pass of `total` rows: the weights over
    /// all rows in `lead`'s scratch, each mixer over its own run's rows.
    fn queue_shared(
        &self,
        lead: &mut Work,
        rest: &mut [&mut Run],
        starts: &[usize],
        flows: &[Flow],
        total: usize,
    ) -> kinetic_cuda::Result<()> {
        let (gpu, stream) = (&self.gpu, &self.gpu.stream);
        let s = &mut lead.scratch;
        if let Some(p) = &self.per_layer {
            p.project(gpu, s, total)?;
        }
        self.layers[0].input(gpu, &s.x, &mut s.h, total)?;
        for (i, layer) in self.layers.iter().enumerate() {
            let (proj, width) = layer.mixer.widths().expect("layers that split");
            if let Some(from) = layer.kv_source {
                copy_lent(gpu, &mut lead.layers, from, i, &lead.batch)?;
                for r in rest.iter_mut() {
                    let w = &mut r.state.work;
                    copy_lent(gpu, &mut w.layers, from, i, &w.batch)?;
                }
            }
            layer.mixer.project(gpu, s, total)?;
            layer
                .mixer
                .mix(gpu, s, &mut lead.layers[i], flows[0], &lead.batch)?;
            for ((r, &at), &flow) in rest.iter_mut().zip(&starts[1..]).zip(&flows[1..]) {
                let n = r.tokens.len();
                let w = &mut r.state.work;
                for ((own, all), &per) in w.scratch.proj.iter_mut().zip(&s.proj).zip(&proj) {
                    own.copy_from_device(0, all, at * per..(at + n) * per, stream)?;
                }
                layer
                    .mixer
                    .mix(gpu, &mut w.scratch, &mut w.layers[i], flow, &w.batch)?;
                let mixed = by_width(&mut w.scratch.mixed, width);
                by_width(&mut s.mixed, width).copy_rows_from(at, mixed, 0..n, stream)?;
            }
            layer.mixer.output(gpu, s, total)?;
            layer.feed(gpu, s, total)?;
            let next = match self.layers.get(i + 1) {
                Some(l) => l.mixer_norm.as_ref(),
                None => Some(&self.output_norm),
            };
            layer.back(gpu, s, total, next)?;
        }
        Ok(())
    }
}
