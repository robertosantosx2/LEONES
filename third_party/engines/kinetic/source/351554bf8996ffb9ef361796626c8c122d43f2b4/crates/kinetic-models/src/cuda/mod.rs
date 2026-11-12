//! Whole models on a CUDA GPU.
//!
//! [`CudaModel::load`] uploads the weights of a loaded [`Model`] once; a
//! [`CudaState`] holds a sequence's caches and working buffers on the
//! device. Only token ids go in and greedy tokens, hidden states and, when
//! asked for, logits come out.
//!
//! Every kernel computes a token's result the same way whatever else shares
//! its batch of up to [`MAX_BATCH`] tokens, so a verified speculative draft
//! yields exactly the tokens plain decoding would. One-token steps are
//! recorded into a CUDA graph the first time and replayed after.
//!
//! Longer runs outside a checkpoint, such as a prompt, go through in batches
//! of up to [`PREFILL_BATCH`] tokens on matrix-product, flash-attention and
//! chunked-recurrence kernels. They are as accurate as the decode kernels,
//! but their sums run in another order, so their results differ slightly
//! from token-by-token decoding; they do not depend on where a prompt is cut
//! into batches, as long as the cuts fall on [`PREFILL_GRID`].

mod attention;
mod delta_net;
mod experts;
mod ffn;
mod fold;
mod host;
mod image;
mod lanes;
mod layer;
mod mamba2;
mod mtp;
mod pass;
mod per_layer;
mod scratch;
mod short_conv;
mod split;
mod target;

use std::cell::RefCell;
use std::ops::Range;
use std::rc::Rc;
use std::sync::Arc;

use kinetic_cuda::{
    Batch, Context, Device, DeviceBuffer, DeviceMatrix, Event, Graph, Kernels, KvType,
    PinnedBuffer, Stream, MAX_BATCH,
};

use crate::blocks::{Folding, Moe};
use crate::convoy::Convoy;
use crate::model::Mark;
use crate::{Forward, LoadError, Model};
use experts::{CudaExperts, ExpertWork, Offload};
use fold::CudaFolding;
use kinetic_cuda::Flow;
use layer::{copy_lent, CudaLayer, Routed};
use pass::{PassRows, PASS_ROWS};
use per_layer::{CudaLayerInput, CudaPerLayer};
use scratch::{Scratch, Spare, Work};

pub use experts::{Plan, PoolPlan, Stats};
pub use host::CudaRunner;
pub use lanes::{Ran, Run};
pub use mtp::CudaMtpState;
pub use split::Placement;

/// Most tokens one prefill pass runs; a state keeps buffers for this many.
pub const PREFILL_BATCH: usize = 512;

/// Prompt runs give the same bits wherever they are cut on multiples of
/// this many tokens: every kernel sums a token's terms in an order that does
/// not depend on the batch, and the chunked recurrence starts its chunks on
/// it.
pub const PREFILL_GRID: usize = 32;

/// Fewest tokens that run as a prefill pass rather than in steps of
/// [`MAX_BATCH`], where the larger kernels become the faster choice.
const PREFILL_FROM: usize = 2 * MAX_BATCH;

/// The device, its kernels and the stream all work is queued on.
struct Gpu {
    ctx: Rc<Context>,
    kernels: Kernels,
    stream: Stream,
    /// Runs small independent products beside the main stream's large
    /// ones, which fills the device while those start and drain.
    side: Stream,
    fork: Event,
    join: Event,
    /// How attention caches store keys and values.
    cache: [KvType; 2],
}

impl Gpu {
    fn new(ctx: Rc<Context>) -> kinetic_cuda::Result<Gpu> {
        Ok(Gpu {
            kernels: Kernels::load(&ctx)?,
            stream: Stream::new(&ctx)?,
            side: Stream::new(&ctx)?,
            fork: Event::new(&ctx)?,
            join: Event::new(&ctx)?,
            cache: [KvType::F16; 2],
            ctx,
        })
    }

    /// Lets work queued on `side` from now on start on what `stream` has
    /// queued so far.
    fn fork(&self) -> kinetic_cuda::Result<()> {
        self.fork.record(&self.stream)?;
        self.side.wait(&self.fork)
    }

    /// Makes work queued on `stream` from now on wait for `side`.
    fn join(&self) -> kinetic_cuda::Result<()> {
        self.join.record(&self.side)?;
        self.stream.wait(&self.join)
    }

    fn matrix(&self, m: &kinetic_quant::Matrix) -> kinetic_cuda::Result<DeviceMatrix> {
        DeviceMatrix::upload(&self.ctx, m)
    }

    fn vector(&self, v: &[f32]) -> kinetic_cuda::Result<DeviceBuffer<f32>> {
        DeviceBuffer::from_slice(&self.ctx, v)
    }
}

/// A model whose weights live on a CUDA device.
///
/// The routed experts of a mixture-of-experts model stay in the model file
/// and run from a device cache of them or on the host; see
/// [`CudaModel::plan`].
///
/// Its own methods report device failures as errors. Driven through
/// [`Target`](crate::speculative::Target), which has no error path, a device
/// failure panics. While a state records its decode graph, the first time it
/// runs a single token, synchronous copies from other threads into the same
/// device fail, so a process should drive the device from one thread, or
/// from threads that each hold a [`CudaModel::seat`] for all of their use.
pub struct CudaModel<'m> {
    gpu: Gpu,
    /// Most tokens a state holds.
    context: usize,
    n_embd: usize,
    eps: f32,
    embd: Embeddings,
    embd_scale: f32,
    /// The output head, or `None` when it shares the embedding table.
    output: Option<DeviceMatrix>,
    head_folding: Option<CudaFolding>,
    embd_folding: Option<CudaFolding>,
    /// Whether any weight was stored folded.
    folded: bool,
    output_norm: DeviceBuffer<f32>,
    layers: Vec<CudaLayer>,
    per_layer: Option<CudaPerLayer>,
    /// Most tokens one pass runs.
    rows: usize,
    mtp: Option<mtp::CudaMtp>,
    /// The routed experts and their cache, in a mixture-of-experts model.
    offload: Option<RefCell<Offload<'m>>>,
    /// The model uploaded, which runs the first `front` layers on the host.
    host: &'m Model<'m>,
    front: usize,
    /// Gathers the runs of seated sequences into shared passes.
    convoy: Convoy<lanes::Job, Ran>,
    /// Full prefill buffers shared by every state, unless states keep their
    /// own.
    spare: Option<RefCell<Spare>>,
    /// The last shared one-token pass recorded, and the states it runs.
    shared_step: RefCell<Option<(Vec<u64>, Graph)>>,
    /// See [`Placement::eager`].
    eager: bool,
}

/// The token embedding table: on the device, or, in a model whose device
/// memory is worth more as layers or expert cache, read on the host a row
/// per token.
enum Embeddings {
    Device(DeviceMatrix),
    Host,
}

/// A sequence's caches and buffers on the device.
pub struct CudaState {
    pos: usize,
    checkpoint: Option<usize>,
    work: Work,
    /// The recorded one-token step, made on first use.
    step: Option<Step>,
    /// Tells states apart in the recorded shared passes.
    id: u64,
    /// Host copies of recurrent layers at earlier lengths, for the warm
    /// cache; see [`Model::mark`].
    marks: Vec<Mark>,
}

impl CudaState {
    /// Number of tokens processed so far.
    pub fn len(&self) -> usize {
        self.pos
    }

    pub fn is_empty(&self) -> bool {
        self.pos == 0
    }

    /// Drops every mark, as [`State::forget_marks`] does.
    pub fn forget_marks(&mut self) {
        self.marks.clear();
    }
}

/// A recorded one-token step and the host buffers it leaves its greedy
/// token and hidden state in.
struct Step {
    graph: Graph,
    greedy: PinnedBuffer<u32>,
    hidden: PinnedBuffer<f32>,
}

/// What a run produces besides the state it advances.
struct Output {
    /// The greedy token after each row given to the head.
    greedy: Vec<u32>,
    /// The normalized final hidden state of every token.
    hidden: Vec<f32>,
    /// Logits of each row given to the head, when asked for.
    logits: Vec<f32>,
}

fn cuda_error(e: kinetic_cuda::Error) -> LoadError {
    LoadError(format!("CUDA: {e}"))
}

impl<'m> CudaModel<'m> {
    /// Uploads `model` to the first CUDA device, for sequences of up to
    /// `context` tokens. Routed experts become a cache in the device memory
    /// left once one state fits; the rest run from the model file. Without
    /// routed experts, layers that do not fit run on the host.
    pub fn load(model: &'m Model<'m>, context: usize) -> Result<CudaModel<'m>, LoadError> {
        CudaModel::load_with(model, context, Placement::default())
    }

    /// [`CudaModel::load`] within the limits of `placement`. A model with
    /// routed experts keeps all its layers on the device.
    pub fn load_with(
        model: &'m Model<'m>,
        context: usize,
        placement: Placement,
    ) -> Result<CudaModel<'m>, LoadError> {
        let ctx = Context::new(Device::get(0).map_err(cuda_error)?).map_err(cuda_error)?;
        let mut gpu = Gpu::new(ctx).map_err(cuda_error)?;
        gpu.cache = [placement.cache_k, placement.cache_v];
        let (start, _) = gpu.ctx.memory_info().map_err(cuda_error)?;
        let moes = routed_experts(model)?;
        let tied = std::ptr::eq(model.output.data, model.embd.data);
        let output = (!tied)
            .then(|| gpu.matrix(&model.output))
            .transpose()
            .map_err(cuda_error)?;
        let output_norm = gpu.vector(&model.output_norm).map_err(cuda_error)?;
        let table = || gpu.matrix(&model.embd).map_err(cuda_error);
        // uploaded first, so the layers that fit are counted without it
        let per_layer = model
            .per_layer
            .as_ref()
            .map(|p| CudaPerLayer::upload(&gpu, p, model.eps))
            .transpose()?;
        let rows = batch_rows(&gpu.kernels, context);
        let (embd, front, layers) = match moes {
            Some(_) => {
                let layers = upload_experts_layers(&gpu, model)?;
                // A tied head or a prediction block reads the table.
                let device = tied
                    || model
                        .mtp
                        .as_ref()
                        .is_some_and(|m| m.layer.experts.is_none());
                let embd = match device {
                    true => Embeddings::Device(table()?),
                    false => Embeddings::Host,
                };
                (embd, 0, layers)
            }
            None => {
                let vocab = model.output.rows;
                let embd = Embeddings::Device(table()?);
                let split = |placement| {
                    split::upload_layers(&gpu, model, context, rows, vocab, placement, start)
                };
                let (front, layers) = split(placement)?;
                if front == 0 || tied {
                    (embd, front, layers)
                } else {
                    // Layers stay on the host: the table goes there too, to
                    // make room for more.
                    drop((embd, layers));
                    let (front, layers) = split(placement)?;
                    (Embeddings::Host, front, layers)
                }
            }
        };
        let mut layers = layers;
        if let Some(p) = &model.per_layer {
            if front > 0 {
                return Err(LoadError(
                    "per-layer inputs need every layer on the device".into(),
                ));
            }
            for (i, (layer, input)) in layers.iter_mut().zip(&p.layers).enumerate() {
                layer.input = Some(CudaLayerInput::upload(&gpu, input, i, p.layers.len())?);
            }
        }
        // A prediction block with routed experts of its own is left out, as
        // is one after layers on the host; speculative decoding then drafts
        // from lookups.
        let mtp = model
            .mtp
            .as_ref()
            .filter(|m| m.layer.experts.is_none() && front == 0)
            .map(|m| mtp::CudaMtp::upload(&gpu, m, model.eps))
            .transpose()?;
        let fold = |f: &Option<Arc<Folding>>| {
            f.as_deref()
                .map(|f| CudaFolding::upload(&gpu, f))
                .transpose()
        };
        let mut cuda = CudaModel {
            context,
            n_embd: model.n_embd,
            eps: model.eps,
            embd,
            embd_scale: model.embd_scale.unwrap_or(1.0),
            output,
            output_norm,
            head_folding: fold(&model.head_folding)?,
            embd_folding: fold(&model.embd_folding)?,
            folded: model.folded,
            layers,
            per_layer,
            rows,
            mtp,
            gpu,
            offload: None,
            host: model,
            front,
            convoy: Convoy::for_device(),
            spare: None,
            shared_step: RefCell::new(None),
            eager: placement.eager,
        };
        if let Some(moes) = moes {
            cuda.offload = Some(RefCell::new(cuda.plan_offload(moes)?));
            if cuda.routes_on_host() {
                model.page_in_experts();
            }
        } else if cuda.batch_rows() > MAX_BATCH {
            // perf: one set of 512-row buffers instead of one per sequence,
            // ~230 MB each on Qwen3.5-4B, lets --parallel 4 fit in 6 GB
            let spare = cuda.new_work(cuda.batch_rows()).map_err(cuda_error)?;
            cuda.spare = Some(RefCell::new(Spare::new(spare)));
            if let Some(spare) = cuda.new_mtp_work(cuda.batch_rows()).map_err(cuda_error)? {
                let mtp = cuda.mtp.as_mut().expect("a prediction block");
                mtp.spare = Some(RefCell::new(Spare::new(spare)));
            }
        }
        Ok(cuda)
    }

    /// Gives the routed experts the device memory left after the weights,
    /// one state and a reserve.
    fn plan_offload(&self, moes: Vec<Moe<'m>>) -> Result<Offload<'m>, LoadError> {
        let mut state = self.new_dense_state().map_err(cuda_error)?;
        state.work.experts = Some(self.expert_work(&moes).map_err(cuda_error)?);
        state.work.pass = Some(PassRows::new(&self.gpu, self.n_embd).map_err(cuda_error)?);
        let state_bytes = state.work.size_bytes();
        drop(state);
        let (free, _) = self.gpu.ctx.memory_info().map_err(cuda_error)?;
        let budget = free.saturating_sub(state_bytes + experts::DEVICE_RESERVE);
        Offload::new(&self.gpu, moes, budget, self.weight_bytes() + state_bytes)
    }

    fn expert_work(&self, moes: &[Moe]) -> kinetic_cuda::Result<ExpertWork> {
        let dims = experts::ExpertDims {
            d: self.n_embd,
            rows: PASS_ROWS,
            picks: moes[0].n_used,
            n_ff: moes.iter().map(|m| m.gate.rows).max().unwrap_or(0),
            scores: self
                .layers
                .iter()
                .filter_map(|l| l.experts.as_ref())
                .map(CudaExperts::score_rows)
                .max()
                .unwrap_or(0),
        };
        ExpertWork::new(&self.gpu, &dims)
    }

    /// Whether a mixture-of-experts model routes its tokens on the host,
    /// reading the routing of every layer back: when some experts live off
    /// the device.
    fn routes_on_host(&self) -> bool {
        self.offload
            .as_ref()
            .is_some_and(|o| !o.borrow().is_resident())
    }

    /// Where the routed experts of a mixture-of-experts model live.
    pub fn plan(&self) -> Option<Plan> {
        self.offload.as_ref().map(|o| o.borrow().plan.clone())
    }

    /// What the routed experts did since load or the last reset.
    pub fn stats(&self) -> Option<Stats> {
        self.offload.as_ref().map(|o| o.borrow().stats)
    }

    pub fn reset_stats(&self) {
        if let Some(o) = &self.offload {
            o.borrow_mut().stats = Stats::default();
        }
    }

    pub fn n_vocab(&self) -> usize {
        self.head().rows()
    }

    pub fn n_embd(&self) -> usize {
        self.n_embd
    }

    /// Device bytes taken by the weights.
    pub fn weight_bytes(&self) -> usize {
        let layers: usize = self.layers.iter().map(CudaLayer::size_bytes).sum();
        let mtp = self.mtp.as_ref().map_or(0, mtp::CudaMtp::size_bytes);
        let output = self.output.as_ref().map_or(0, DeviceMatrix::size_bytes);
        let embd = match &self.embd {
            Embeddings::Device(t) => t.size_bytes(),
            Embeddings::Host => 0,
        };
        let per_layer = self.per_layer.as_ref().map_or(0, CudaPerLayer::size_bytes);
        embd + output + layers + mtp + per_layer
    }

    /// Free and total device memory in bytes.
    pub fn memory_info(&self) -> kinetic_cuda::Result<(usize, usize)> {
        self.gpu.ctx.memory_info()
    }

    /// An empty state for a new sequence.
    pub fn new_state(&self) -> kinetic_cuda::Result<CudaState> {
        let mut state = self.new_dense_state()?;
        if let Some(off) = &self.offload {
            state.work.experts = Some(self.expert_work(&off.borrow().moes)?);
            state.work.pass = Some(PassRows::new(&self.gpu, self.n_embd)?);
        }
        Ok(state)
    }

    fn new_dense_state(&self) -> kinetic_cuda::Result<CudaState> {
        let mut work = self.new_work(self.state_rows())?;
        work.front = self.new_front();
        Ok(CudaState {
            pos: 0,
            checkpoint: None,
            work,
            step: None,
            id: lanes::next_id(),
            marks: Vec::new(),
        })
    }

    fn new_work(&self, rows: usize) -> kinetic_cuda::Result<Work> {
        let layers: Vec<&CudaLayer> = self.layers.iter().collect();
        let (d, vocab) = (self.n_embd, self.n_vocab());
        let mut work = Work::new(
            &self.gpu,
            &layers,
            d,
            self.context,
            rows,
            vocab,
            0,
            self.folded,
        )?;
        if self.host.grid_rope {
            work.batch.use_grid();
        }
        Ok(work)
    }

    /// Rows a state keeps buffers for; longer batches borrow the spare.
    fn state_rows(&self) -> usize {
        match self.spare {
            Some(_) => MAX_BATCH,
            None => self.batch_rows(),
        }
    }

    fn batch_rows(&self) -> usize {
        self.rows
    }

    /// Device bytes held by `state`.
    pub fn state_bytes(&self, state: &CudaState) -> usize {
        state.work.size_bytes()
    }

    /// Runs `tokens` in order. With `all_logits` the logits after every
    /// token are returned, `tokens.len()` rows of [`CudaModel::n_vocab`]
    /// values; otherwise only those after the last one.
    pub fn run(
        &self,
        state: &mut CudaState,
        tokens: &[u32],
        all_logits: bool,
    ) -> kinetic_cuda::Result<Forward> {
        let out = self.forward(state, tokens, all_logits, true)?;
        Ok(Forward {
            logits: out.logits,
            hidden: out.hidden,
        })
    }

    /// Runs `tokens` like [`CudaModel::run`] but returns only the greedy
    /// token after every row (with `all_rows`) or after the last, and the
    /// normalized final hidden states; logits never leave the device.
    pub fn run_greedy(
        &self,
        state: &mut CudaState,
        tokens: &[u32],
        all_rows: bool,
    ) -> kinetic_cuda::Result<(Vec<u32>, Vec<f32>)> {
        let out = self.forward(state, tokens, all_rows, false)?;
        Ok((out.greedy, out.hidden))
    }

    /// Marks the current length so a later [`CudaModel::rollback`] can
    /// return to any point after it. At most [`MAX_BATCH`] tokens may run
    /// between the two.
    pub fn checkpoint(&self, state: &mut CudaState) -> kinetic_cuda::Result<()> {
        if let Some(start) = state.checkpoint {
            self.rollback(state, state.pos - start)?;
        }
        state.checkpoint = Some(state.pos);
        self.checkpoint_front(&mut state.work);
        Ok(())
    }

    /// Keeps the first `keep` tokens run since the checkpoint and discards
    /// the rest, leaving the state exactly as if they had never run.
    pub fn rollback(&self, state: &mut CudaState, keep: usize) -> kinetic_cuda::Result<()> {
        let start = state
            .checkpoint
            .take()
            .expect("rollback without a checkpoint");
        assert!(
            start + keep <= state.pos,
            "cannot keep more tokens than were run"
        );
        for (layer, s) in self.layers.iter().zip(&mut state.work.layers) {
            layer.replay(&self.gpu, s, keep)?;
        }
        self.rollback_front(&mut state.work, keep);
        state.pos = start + keep;
        Ok(())
    }

    fn head(&self) -> &DeviceMatrix {
        match (&self.output, &self.embd) {
            (Some(head), _) | (None, Embeddings::Device(head)) => head,
            (None, Embeddings::Host) => {
                unreachable!("a tied head keeps its table on the device")
            }
        }
    }

    /// Writes the embeddings of `tokens`, which the batch of `work` holds,
    /// after any layers on the host, into its scratch.
    fn embed(&self, work: &mut Work, tokens: &[u32]) -> kinetic_cuda::Result<()> {
        match self.front {
            0 => self.embed_rows(&work.batch, tokens, &mut work.scratch.x),
            _ => self.embed_front(work, tokens),
        }
    }

    /// Writes the embeddings of `tokens`, which `batch` holds, into `x`.
    fn embed_rows(
        &self,
        batch: &Batch,
        tokens: &[u32],
        x: &mut DeviceBuffer<f32>,
    ) -> kinetic_cuda::Result<()> {
        match &self.embd {
            Embeddings::Device(table) => {
                let (k, stream) = (&self.gpu.kernels, &self.gpu.stream);
                k.embed(table, self.embd_scale, batch, x, stream)?;
                match &self.embd_folding {
                    Some(f) => f.restore(&self.gpu, x, self.n_embd, tokens.len()),
                    None => Ok(()),
                }
            }
            // Ordered after the work queued so far, like every synchronous
            // copy.
            Embeddings::Host => x.copy_range_from(0, &self.host.embed(tokens)),
        }
    }

    fn check_tokens(&self, tokens: &[u32]) -> kinetic_cuda::Result<()> {
        let vocab = self.n_vocab();
        match tokens.iter().find(|&&t| t as usize >= vocab) {
            _ if tokens.is_empty() => Err(shape("empty batch".into())),
            Some(t) => Err(shape(format!("token {t} is not below {vocab}"))),
            None => Ok(()),
        }
    }

    fn forward(
        &self,
        state: &mut CudaState,
        tokens: &[u32],
        all_rows: bool,
        logits: bool,
    ) -> kinetic_cuda::Result<Output> {
        let Some(spare) = self.spare.as_ref().filter(|_| tokens.len() > MAX_BATCH) else {
            return self.forward_rows(state, tokens, all_rows, logits);
        };
        let mut spare = spare.borrow_mut();
        // the decode graph reads the state's own buffers
        let step = state.step.take();
        let shift = state.work.batch.grid_shift();
        spare.swap(&mut state.work);
        state.work.batch.set_grid_shift(shift);
        let out = self.forward_rows(state, tokens, all_rows, logits);
        spare.swap(&mut state.work);
        state.step = step;
        out
    }

    fn forward_rows(
        &self,
        state: &mut CudaState,
        tokens: &[u32],
        all_rows: bool,
        logits: bool,
    ) -> kinetic_cuda::Result<Output> {
        self.check_tokens(tokens)?;
        if state.pos + tokens.len() > self.context {
            return Err(shape(format!(
                "{} tokens past a context of {}",
                state.pos + tokens.len(),
                self.context
            )));
        }
        let since = state.checkpoint.map(|start| state.pos - start);
        if since.is_some_and(|s| s + tokens.len() > MAX_BATCH) {
            return Err(shape(format!(
                "more than {MAX_BATCH} tokens between a checkpoint and its rollback"
            )));
        }

        let d = self.n_embd;
        let mut out = Output {
            greedy: Vec::new(),
            hidden: vec![0.0; tokens.len() * d],
            logits: Vec::new(),
        };
        if self.routes_on_host() && since.is_none() && !all_rows && tokens.len() > MAX_BATCH {
            self.forward_passes(state, tokens, logits, &mut out)?;
            return Ok(out);
        }
        let mut done = 0;
        for chunk in batches(tokens, state.pos, since.is_none(), self.batch_rows()) {
            let n = chunk.len();
            let last = done + n == tokens.len();
            let head = match (all_rows, last) {
                (true, _) => Some(0..n),
                (false, true) => Some(n - 1..n),
                (false, false) => None,
            };
            let flow = match state.checkpoint {
                None => Flow::Commit,
                Some(start) => Flow::Record {
                    first: state.pos - start,
                },
            };
            state.work.batch.set(state.pos, chunk, &self.gpu.stream)?;
            // Experts routed on the host read their routing back, which a
            // graph cannot; embeddings read on the host are copied before.
            if flow == Flow::Commit
                && n == 1
                && head.is_some()
                && !self.routes_on_host()
                && !self.eager
            {
                let embed_on_device = self.front == 0 && matches!(self.embd, Embeddings::Device(_));
                if !embed_on_device {
                    self.embed(&mut state.work, chunk)?;
                }
                if state.step.is_none() {
                    state.step = Some(self.record_step(&mut state.work, chunk, embed_on_device)?);
                }
                if let Some(step) = &state.step {
                    step.graph.launch(&self.gpu.stream)?;
                    self.gpu.stream.synchronize()?;
                    out.greedy.extend_from_slice(step.greedy.as_slice());
                    out.hidden[done * d..][..d].copy_from_slice(step.hidden.as_slice());
                }
                if logits {
                    let start = out.logits.len();
                    out.logits.resize(start + self.n_vocab(), 0.0);
                    state
                        .work
                        .scratch
                        .logits
                        .copy_range_to(0, &mut out.logits[start..])?;
                    self.host.cap(&mut out.logits[start..]);
                }
            } else {
                self.queue(&mut state.work, chunk, flow)?;
                for rows in head.iter().flat_map(|r| slices(r.clone())) {
                    let m = rows.len();
                    self.queue_head(&mut state.work.scratch, rows)?;
                    self.read_head(&state.work.scratch, m, logits, &mut out)?;
                }
                let hidden = &mut out.hidden[done * d..][..n * d];
                state.work.scratch.h.values().copy_range_to(0, hidden)?;
            }
            state.pos += n;
            done += n;
        }
        Ok(out)
    }

    /// Records the one-token step over the batch in `work`, which holds
    /// `token`, from its embedding on the device or from the embedding in
    /// the scratch.
    fn record_step(
        &self,
        work: &mut Work,
        token: &[u32],
        embed_on_device: bool,
    ) -> kinetic_cuda::Result<Step> {
        let stream = &self.gpu.stream;
        let mut greedy = PinnedBuffer::new(&self.gpu.ctx, 1)?;
        let mut hidden = PinnedBuffer::new(&self.gpu.ctx, self.n_embd)?;
        let graph = stream.capture(|| {
            if embed_on_device {
                self.embed(work, token)?;
            }
            self.queue_layers(work, Flow::Commit)?;
            let s = &mut work.scratch;
            self.queue_head(s, 0..1)?;
            // SAFETY: the step owns both buffers with its graph, and they are
            // read only after the stream has passed each launch.
            unsafe {
                greedy.download(0, s.greedy.best(), 0..1, stream)?;
                hidden.download(0, s.h.values(), 0..self.n_embd, stream)
            }
        })?;
        Ok(Step {
            graph,
            greedy,
            hidden,
        })
    }

    /// Runs `tokens` in passes of up to [`PASS_ROWS`] and the head on the
    /// last of them.
    fn forward_passes(
        &self,
        state: &mut CudaState,
        tokens: &[u32],
        logits: bool,
        out: &mut Output,
    ) -> kinetic_cuda::Result<()> {
        let (d, vocab) = (self.n_embd, self.n_vocab());
        for (i, pass) in tokens.chunks(PASS_ROWS).enumerate() {
            let hidden = &mut out.hidden[i * PASS_ROWS * d..][..pass.len() * d];
            self.queue_pass(&mut state.work, state.pos, pass, hidden)?;
            state.pos += pass.len();
        }
        let last = (tokens.len() - 1) % MAX_BATCH;
        let s = &mut state.work.scratch;
        let (k, stream) = (&self.gpu.kernels, &self.gpu.stream);
        let h = match &self.head_folding {
            Some(f) => f.fold(&self.gpu, &s.h, &mut s.folded, last + 1)?,
            None => &s.h,
        };
        k.gemv_rows(self.head(), vocab, h, last..last + 1, &mut s.logits, stream)?;
        k.argmax(&s.logits, vocab, 1, &mut s.greedy, stream)?;
        out.greedy = vec![0];
        s.greedy.best().copy_range_to(0, &mut out.greedy)?;
        if logits {
            out.logits = vec![0.0; vocab];
            s.logits.copy_range_to(0, &mut out.logits)?;
            self.host.cap(&mut out.logits);
        }
        Ok(())
    }

    /// Appends the greedy tokens, and with `logits` the logits, of the
    /// `rows` rows the head last ran on.
    fn read_head(
        &self,
        s: &Scratch,
        rows: usize,
        logits: bool,
        out: &mut Output,
    ) -> kinetic_cuda::Result<()> {
        let mut greedy = vec![0; rows];
        s.greedy.best().copy_range_to(0, &mut greedy)?;
        out.greedy.extend(greedy);
        if logits {
            let start = out.logits.len();
            out.logits.resize(start + rows * self.n_vocab(), 0.0);
            s.logits.copy_range_to(0, &mut out.logits[start..])?;
            self.host.cap(&mut out.logits[start..]);
        }
        Ok(())
    }

    /// Queues the output head and its greedy tokens over `rows` rows of the
    /// last pass, at most [`MAX_BATCH`].
    fn queue_head(&self, s: &mut Scratch, rows: Range<usize>) -> kinetic_cuda::Result<()> {
        let (k, stream) = (&self.gpu.kernels, &self.gpu.stream);
        let (m, vocab) = (rows.len(), self.n_vocab());
        let h = match &self.head_folding {
            Some(f) => f.fold(&self.gpu, &s.h, &mut s.folded, rows.end)?,
            None => &s.h,
        };
        k.gemv_rows(self.head(), vocab, h, rows, &mut s.logits, stream)?;
        k.argmax(&s.logits, vocab, m, &mut s.greedy, stream)
    }

    /// Queues one pass over the batch in `work`, which holds `tokens`.
    fn queue(&self, work: &mut Work, tokens: &[u32], flow: Flow) -> kinetic_cuda::Result<()> {
        self.embed(work, tokens)?;
        self.queue_layers(work, flow)
    }

    /// Queues the layers over the batch in `work`, whose embeddings are in
    /// the scratch.
    fn queue_layers(&self, work: &mut Work, flow: Flow) -> kinetic_cuda::Result<()> {
        let n = work.batch.len();
        let s = &mut work.scratch;
        if let Some(p) = &self.per_layer {
            p.queue(&self.gpu, s, &work.batch)?;
        }
        self.layers[0].input(&self.gpu, &s.x, &mut s.h, n)?;
        let mut offload = self.offload.as_ref().map(RefCell::borrow_mut);
        let mut moe_layer = 0;
        for (i, layer) in self.layers.iter().enumerate() {
            let next = match self.layers.get(i + 1) {
                Some(l) => l.mixer_norm.as_ref(),
                None => Some(&self.output_norm),
            };
            let routed = match (offload.as_deref_mut(), work.experts.as_mut()) {
                (Some(offload), Some(work)) if layer.experts.is_some() => {
                    moe_layer += 1;
                    Some(Routed {
                        layer: moe_layer - 1,
                        work,
                        offload,
                    })
                }
                _ => None,
            };
            if let Some(from) = layer.kv_source {
                copy_lent(&self.gpu, &mut work.layers, from, i, &work.batch)?;
            }
            let state = &mut work.layers[i];
            layer.forward(&self.gpu, s, state, flow, &work.batch, next, routed)?;
        }
        Ok(())
    }
}

/// Uploads every layer of a model with routed experts, each scoring the
/// next layer's router too.
fn upload_experts_layers(gpu: &Gpu, model: &Model) -> Result<Vec<CudaLayer>, LoadError> {
    model
        .layers
        .iter()
        .enumerate()
        .map(|(i, l)| {
            let experts = l
                .experts
                .as_ref()
                .map(|moe| {
                    let next = model.layers.get(i + 1).and_then(|n| n.experts.as_ref());
                    CudaExperts::upload(gpu, moe, next.map(|n| &n.router), l.ffn.is_some())
                })
                .transpose()?;
            CudaLayer::upload(gpu, l, experts, model.eps)
        })
        .collect()
}

/// Tokens a pass runs at most: a prefill batch, or the whole context when
/// that is shorter; a step on devices without large-batch kernels.
fn batch_rows(kernels: &Kernels, context: usize) -> usize {
    if !kernels.large_batches() {
        return MAX_BATCH;
    }
    PREFILL_BATCH.min(context).max(MAX_BATCH)
}

/// Splits `tokens`, which follow `pos` others, into the batches a run
/// takes: with `prefill`, runs of at least [`PREFILL_FROM`] tokens go in
/// full batches of `rows` and the rest, since the matrix products work in
/// tiles of many tokens and a full batch leaves none of a tile empty;
/// anything else in steps of [`MAX_BATCH`]. A run's last tokens after the
/// [`PREFILL_GRID`] that are too few for a batch of their own go in steps
/// too, as a run of only them would take them.
fn batches(tokens: &[u32], pos: usize, prefill: bool, rows: usize) -> impl Iterator<Item = &[u32]> {
    let tail = (pos + tokens.len() - 1) % PREFILL_GRID + 1;
    let head = match prefill && tokens.len() >= PREFILL_FROM {
        true if tail < PREFILL_FROM => tokens.len() - tail,
        true => tokens.len(),
        false => 0,
    };
    let (head, tail) = tokens.split_at(head);
    head.chunks(rows).chain(tail.chunks(MAX_BATCH))
}

/// `rows` in runs of at most [`MAX_BATCH`].
fn slices(rows: Range<usize>) -> impl Iterator<Item = Range<usize>> {
    let end = rows.end;
    rows.step_by(MAX_BATCH)
        .map(move |start| start..(start + MAX_BATCH).min(end))
}

/// The routed experts of the layers that have them, in order; the dense
/// layers come before them (LFM2 MoE).
fn routed_experts<'m>(model: &Model<'m>) -> Result<Option<Vec<Moe<'m>>>, LoadError> {
    let moes: Vec<Moe<'m>> = model
        .layers
        .iter()
        .filter_map(|l| l.experts.clone())
        .collect();
    match moes.len() {
        0 => Ok(None),
        n if model.layers[model.layers.len() - n..]
            .iter()
            .all(|l| l.experts.is_some()) =>
        {
            Ok(Some(moes))
        }
        _ => Err(LoadError(
            "routed experts between dense layers are not supported on CUDA yet".into(),
        )),
    }
}

fn shape(msg: String) -> kinetic_cuda::Error {
    kinetic_cuda::Error::Shape(msg)
}
