//! Whole models on a Vulkan GPU: AMD, Intel or NVIDIA.
//!
//! [`VulkanModel::load`] uploads the weights of a loaded [`Model`] once; a
//! [`VulkanState`] holds a sequence's caches and working buffers on the
//! device. Token embeddings and rotary angles are computed on the host,
//! exactly as the CPU path computes them; greedy tokens, hidden states and,
//! when asked for, logits come back.
//!
//! A state records its pass once, as a command buffer replayed for every
//! batch of up to [`MAX_BATCH`] tokens: the kernels read how many tokens run
//! and where from a small buffer the host fills before each run. Every
//! kernel computes a token's result the same way whatever else shares its
//! batch, so a verified speculative draft yields exactly the tokens plain
//! decoding would. Attention caches and convolution rings are indexed by
//! position, so a rollback has nothing to undo there; delta-rule layers
//! leave their state alone after a checkpoint and replay the kept tokens
//! from a journal on rollback.

mod attention;
mod delta_net;
mod ffn;
mod host;
mod layer;
mod mtp;
mod rope;
mod short_conv;
mod target;
mod work;

use std::ops::Range;
use std::rc::Rc;

use kinetic_quant::{dequantize_row, Matrix};
use kinetic_vulkan::{
    Batch, Commands, Device, DeviceBuffer, DeviceMatrix, Graph, Instance, Kernels, Out,
    PhysicalDevice, Rows,
};

use crate::model::{embed_into, Mark};
use crate::{Forward, LoadError, Model};
use layer::{LayerState, VulkanLayer};
use mtp::VulkanMtp;

pub use host::VulkanRunner;
pub use mtp::VulkanMtpState;
use rope::RopeTables;
use work::Work;

/// Most tokens one pass runs, and most that may run between a checkpoint
/// and its rollback.
pub const MAX_BATCH: usize = 16;

/// The device and its kernels.
struct Gpu {
    device: Rc<Device>,
    kernels: Kernels,
}

impl Gpu {
    fn matrix(&self, m: &Matrix) -> Result<DeviceMatrix, LoadError> {
        DeviceMatrix::upload(&self.device, m).map_err(vulkan_error)
    }

    fn vector(&self, v: &[f32]) -> Result<DeviceBuffer<f32>, LoadError> {
        DeviceBuffer::from_slice(&self.device, v).map_err(vulkan_error)
    }
}

fn vulkan_error(e: kinetic_vulkan::Error) -> LoadError {
    LoadError(format!("Vulkan: {e}"))
}

/// The Vulkan devices that can run models, discrete GPUs first.
pub fn devices() -> kinetic_vulkan::Result<Vec<PhysicalDevice>> {
    let mut devices = Instance::new()?.physical_devices()?;
    devices.retain(|d| d.info().missing().is_none());
    Ok(devices)
}

/// A model whose weights live on a Vulkan device.
///
/// Its own methods report device failures as errors. Driven through
/// [`Target`](crate::speculative::Target), which has no error path, a
/// device failure panics.
pub struct VulkanModel<'m> {
    gpu: Gpu,
    name: String,
    /// Most tokens a state holds.
    context: usize,
    n_embd: usize,
    eps: f32,
    embd: Matrix<'m>,
    embd_scale: Option<f32>,
    output: DeviceMatrix,
    /// The output head as the model file holds it, for drafts.
    output_rows: Matrix<'m>,
    output_norm: DeviceBuffer<f32>,
    layers: Vec<VulkanLayer>,
    mtp: Option<VulkanMtp>,
    ropes: RopeTables,
}

/// A sequence's caches and buffers on the device.
pub struct VulkanState {
    pos: usize,
    checkpoint: Option<usize>,
    work: Work,
    layers: Vec<LayerState>,
    /// The recorded pass, and the same with the logits of one head row
    /// brought back.
    step: Graph,
    step_logits: Graph,
    /// Brings back the logits of every head row.
    all_logits: Graph,
    /// What a rollback runs, when a layer needs it.
    replay: Option<Graph>,
    /// Host copies of recurrent layers at earlier lengths, for the warm
    /// cache; see [`Model::mark`].
    marks: Vec<Mark>,
}

impl VulkanState {
    /// Number of tokens processed so far.
    pub fn len(&self) -> usize {
        self.pos
    }

    pub fn is_empty(&self) -> bool {
        self.pos == 0
    }
}

/// What a run produces besides the state it advances.
struct Output {
    /// The greedy token after each row given to the head.
    greedy: Vec<u32>,
    /// The logit of each greedy token.
    top: Vec<f32>,
    /// The normalized final hidden state of every token.
    hidden: Vec<f32>,
    /// Logits of each row given to the head, when asked for.
    logits: Vec<f32>,
}

impl<'m> VulkanModel<'m> {
    /// Uploads `model` to the first Vulkan device that can run it, for
    /// sequences of up to `context` tokens.
    pub fn load(model: &Model<'m>, context: usize) -> Result<VulkanModel<'m>, LoadError> {
        let physical = devices()
            .map_err(vulkan_error)?
            .into_iter()
            .next()
            .ok_or_else(|| LoadError("no Vulkan device can run models".into()))?;
        VulkanModel::load_on(model, context, &physical)
    }

    /// Uploads `model` to `physical` for sequences of up to `context` tokens.
    pub fn load_on(
        model: &Model<'m>,
        context: usize,
        physical: &PhysicalDevice,
    ) -> Result<VulkanModel<'m>, LoadError> {
        if model.folded {
            return Err(LoadError(
                "weights stored folded are not supported on Vulkan yet".into(),
            ));
        }
        if model.per_layer.is_some() || model.logit_cap.is_some() {
            return Err(LoadError(
                "per-layer inputs and capped logits are not supported on Vulkan yet".into(),
            ));
        }
        let e = &model.embd;
        dequantize_row(e.ty, e.data, 0, &mut vec![0.0; e.cols])
            .map_err(|_| LoadError(format!("{} embeddings are not supported", e.ty)))?;
        let device = Device::new(physical).map_err(vulkan_error)?;
        let gpu = Gpu {
            kernels: Kernels::load(&device).map_err(vulkan_error)?,
            device,
        };
        let mut ropes = RopeTables::new(MAX_BATCH);
        let layers = model
            .layers
            .iter()
            .map(|l| VulkanLayer::upload(&gpu, l, &mut ropes))
            .collect::<Result<Vec<_>, _>>()?;
        let mtp = model
            .mtp
            .as_ref()
            .map(|m| VulkanMtp::upload(&gpu, m, &mut ropes))
            .transpose()?;
        Ok(VulkanModel {
            name: physical.info().name.clone(),
            context,
            n_embd: model.n_embd,
            eps: model.eps,
            embd: model.embd,
            embd_scale: model.embd_scale,
            output: gpu.matrix(&model.output)?,
            output_rows: model.output,
            mtp,
            output_norm: gpu.vector(&model.output_norm)?,
            layers,
            ropes,
            gpu,
        })
    }

    /// The name of the device the model runs on.
    pub fn device_name(&self) -> &str {
        &self.name
    }

    pub fn n_vocab(&self) -> usize {
        self.output.rows()
    }

    pub fn n_embd(&self) -> usize {
        self.n_embd
    }

    /// Device bytes taken by the weights.
    pub fn weight_bytes(&self) -> usize {
        let layers: usize = self.layers.iter().map(VulkanLayer::size_bytes).sum();
        let mtp = self.mtp.as_ref().map_or(0, VulkanMtp::size_bytes);
        layers + mtp + self.output.size_bytes()
    }

    /// An empty state for a new sequence.
    pub fn new_state(&self) -> kinetic_vulkan::Result<VulkanState> {
        let dev = &self.gpu.device;
        let batch = Batch::new(dev, MAX_BATCH, MAX_BATCH, self.context, self.ropes.words())?;
        let work = Work::new(&self.gpu, &self.layers, self.n_embd, batch, self.n_vocab())?;
        let layers = self
            .layers
            .iter()
            .map(|l| l.new_state(dev, self.context, MAX_BATCH))
            .collect::<kinetic_vulkan::Result<Vec<_>>>()?;
        let vocab = self.n_vocab();
        let mut all_logits = Commands::new(dev)?;
        all_logits.download(&work.logits, 0, &work.logits_host, 0, MAX_BATCH * vocab)?;
        let replay = match self.layers.iter().any(VulkanLayer::replays) {
            true => Some(self.record_replay(&work, &layers)?),
            false => None,
        };
        Ok(VulkanState {
            pos: 0,
            checkpoint: None,
            step: self.record(&work, &layers, false)?,
            step_logits: self.record(&work, &layers, true)?,
            all_logits: all_logits.finish()?,
            replay,
            work,
            layers,
            marks: Vec::new(),
        })
    }

    /// Empties `state` for a new sequence, keeping its buffers.
    pub fn reset(&self, state: &mut VulkanState) -> kinetic_vulkan::Result<()> {
        state.pos = 0;
        state.checkpoint = None;
        state.marks.clear();
        for (layer, s) in self.layers.iter().zip(&mut state.layers) {
            layer.clear(s)?;
        }
        Ok(())
    }

    /// Device bytes held by `state`.
    pub fn state_bytes(&self, state: &VulkanState) -> usize {
        let layers: usize = state.layers.iter().map(LayerState::size_bytes).sum();
        state.work.size_bytes() + layers
    }

    /// Records one pass: the batch and embeddings in, every layer, the
    /// head and its greedy tokens, and the results out, with `logits` the
    /// logits of the first head row too.
    fn record(
        &self,
        w: &Work,
        states: &[LayerState],
        logits: bool,
    ) -> kinetic_vulkan::Result<Graph> {
        let (k, d) = (&self.gpu.kernels, self.n_embd);
        let mut c = Commands::new(&self.gpu.device)?;
        let rows = w.batch.rows();
        c.independent(|c| {
            w.batch.record_upload(c)?;
            c.upload(&w.embedded, 0, &w.x, 0, rows * d)
        })?;
        let first = &self.layers[0].mixer_norm;
        k.norm(&w.batch, &w.x, None, first, self.eps, &w.h, &mut c)?;
        for (i, (layer, state)) in self.layers.iter().zip(states).enumerate() {
            let next = self
                .layers
                .get(i + 1)
                .map_or(&self.output_norm, |l| &l.mixer_norm);
            layer.record(&self.gpu, w, state, next, self.eps, &mut c)?;
        }
        let vocab = self.n_vocab();
        let out = Out {
            stride: vocab,
            offset: 0,
        };
        k.gemv_rows(
            &self.output,
            &w.h,
            &w.logits,
            out,
            Rows::Head,
            &w.batch,
            &mut c,
        )?;
        k.argmax(&w.batch, &w.logits, vocab, &w.best, &mut c)?;
        c.download(w.h.values(), 0, &w.hidden, 0, rows * d)?;
        c.download(&w.best, 0, &w.greedy, 0, w.greedy.len())?;
        if logits {
            c.download(&w.logits, 0, &w.logits_host, 0, vocab)?;
        }
        c.finish()
    }

    /// Records what a rollback runs: every layer's replay of the tokens it
    /// keeps.
    fn record_replay(&self, w: &Work, states: &[LayerState]) -> kinetic_vulkan::Result<Graph> {
        let mut c = Commands::new(&self.gpu.device)?;
        w.batch.record_upload(&mut c)?;
        for (layer, state) in self.layers.iter().zip(states) {
            layer.record_replay(&self.gpu, w, state, &mut c)?;
        }
        c.finish()
    }

    /// Runs `tokens` in order. With `all_logits` the logits after every
    /// token are returned, `tokens.len()` rows of [`VulkanModel::n_vocab`]
    /// values; otherwise only those after the last one.
    pub fn run(
        &self,
        state: &mut VulkanState,
        tokens: &[u32],
        all_logits: bool,
    ) -> kinetic_vulkan::Result<Forward> {
        let out = self.forward(state, tokens, all_logits, true)?;
        Ok(Forward {
            logits: out.logits,
            hidden: out.hidden,
        })
    }

    /// Runs `tokens` like [`VulkanModel::run`] but returns only the greedy
    /// token after every row (with `all_rows`) or after the last, and the
    /// normalized final hidden states; logits never leave the device.
    pub fn run_greedy(
        &self,
        state: &mut VulkanState,
        tokens: &[u32],
        all_rows: bool,
    ) -> kinetic_vulkan::Result<(Vec<u32>, Vec<f32>)> {
        let out = self.forward(state, tokens, all_rows, false)?;
        Ok((out.greedy, out.hidden))
    }

    /// [`VulkanModel::run`] for a choice that needs only the largest logit
    /// of each row: rows hold that logit at its greedy token and negative
    /// infinity elsewhere, so only a token and a float per row leave the
    /// device.
    pub fn run_top1(
        &self,
        state: &mut VulkanState,
        tokens: &[u32],
        all_rows: bool,
    ) -> kinetic_vulkan::Result<Forward> {
        let out = self.forward(state, tokens, all_rows, false)?;
        let vocab = self.n_vocab();
        let mut logits = vec![f32::NEG_INFINITY; out.greedy.len() * vocab];
        for (row, (&t, &v)) in out.greedy.iter().zip(&out.top).enumerate() {
            logits[row * vocab + t as usize] = v;
        }
        Ok(Forward {
            logits,
            hidden: out.hidden,
        })
    }

    /// Marks the current length so a later [`VulkanModel::rollback`] can
    /// return to any point after it. At most [`MAX_BATCH`] tokens may run
    /// between the two.
    pub fn checkpoint(&self, state: &mut VulkanState) -> kinetic_vulkan::Result<()> {
        if let Some(start) = state.checkpoint {
            self.rollback(state, state.pos - start)?;
        }
        state.checkpoint = Some(state.pos);
        Ok(())
    }

    /// Keeps the first `keep` tokens run since the checkpoint and discards
    /// the rest, leaving the state exactly as if they had never run.
    pub fn rollback(&self, state: &mut VulkanState, keep: usize) -> kinetic_vulkan::Result<()> {
        let start = state
            .checkpoint
            .take()
            .expect("rollback without a checkpoint");
        assert!(
            start + keep <= state.pos,
            "cannot keep more tokens than were run"
        );
        if let Some(replay) = state.replay.as_ref().filter(|_| keep > 0) {
            state.work.batch.set_replay(start, start + keep)?;
            replay.launch()?;
        }
        state.pos = start + keep;
        Ok(())
    }

    fn check(&self, state: &VulkanState, tokens: &[u32]) -> kinetic_vulkan::Result<()> {
        let vocab = self.n_vocab();
        let since = state.checkpoint.map(|start| state.pos - start);
        let msg = if tokens.is_empty() {
            "empty batch".to_string()
        } else if let Some(t) = tokens.iter().find(|&&t| t as usize >= vocab) {
            format!("token {t} is not below {vocab}")
        } else if state.pos + tokens.len() > self.context {
            format!(
                "{} tokens past a context of {}",
                state.pos + tokens.len(),
                self.context
            )
        } else if since.is_some_and(|s| s + tokens.len() > MAX_BATCH) {
            format!("more than {MAX_BATCH} tokens between a checkpoint and its rollback")
        } else {
            return Ok(());
        };
        Err(kinetic_vulkan::Error::Shape(msg))
    }

    fn forward(
        &self,
        state: &mut VulkanState,
        tokens: &[u32],
        all_rows: bool,
        logits: bool,
    ) -> kinetic_vulkan::Result<Output> {
        self.check(state, tokens)?;
        let (d, vocab) = (self.n_embd, self.n_vocab());
        let mut out = Output {
            greedy: Vec::new(),
            top: Vec::new(),
            hidden: Vec::with_capacity(tokens.len() * d),
            logits: Vec::new(),
        };
        let mut done = 0;
        for chunk in tokens.chunks(MAX_BATCH) {
            let n = chunk.len();
            let head: Range<usize> = match (all_rows, done + n == tokens.len()) {
                (true, _) => 0..n,
                (false, true) => n - 1..n,
                (false, false) => n..n,
            };
            let w = &mut state.work;
            w.batch.set(n, state.pos, head.clone(), state.checkpoint)?;
            self.ropes.fill(&mut w.batch, state.pos, n);
            let x = &mut w.embedded.as_mut_slice()[..n * d];
            embed_into(&self.embd, self.embd_scale, chunk, x);
            let one = logits && head.len() == 1;
            match one {
                true => state.step_logits.launch()?,
                false => state.step.launch()?,
            }
            for pair in w.greedy.as_slice()[..2 * head.len()].chunks_exact(2) {
                out.greedy.push(pair[0]);
                out.top.push(f32::from_bits(pair[1]));
            }
            out.hidden.extend_from_slice(&w.hidden.as_slice()[..n * d]);
            if logits && head.len() > 1 {
                state.all_logits.launch()?;
            }
            if logits {
                let rows = &w.logits_host.as_slice()[..head.len() * vocab];
                out.logits.extend_from_slice(rows);
            }
            state.pos += n;
            done += n;
        }
        Ok(out)
    }
}
