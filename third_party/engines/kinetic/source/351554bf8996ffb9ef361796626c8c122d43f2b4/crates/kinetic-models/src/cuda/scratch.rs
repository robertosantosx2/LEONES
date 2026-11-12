use kinetic_cuda::{Argmax, Batch, DeviceBuffer, GemvInput, MAX_BATCH};

use super::experts::ExpertWork;
use super::layer::{CudaLayer, LayerState};
use super::pass::PassRows;
use super::Gpu;
use crate::blocks::MixerState;

/// Working buffers for a batch of tokens; the output head runs on at most
/// [`MAX_BATCH`] rows at a time.
pub(super) struct Scratch {
    /// The residual stream.
    pub x: DeviceBuffer<f32>,
    /// The output of the block just run.
    pub y: DeviceBuffer<f32>,
    /// The summed outputs of parallel mixers run so far.
    pub sum: DeviceBuffer<f32>,
    /// The normalized stream, input of the next block or of the head.
    pub h: GemvInput,
    /// Projection outputs.
    pub proj: [DeviceBuffer<f32>; 4],
    /// Attention partials and recurrence outputs.
    pub scratch: DeviceBuffer<f32>,
    /// Mixer outputs, inputs of their output projections; one per width.
    pub mixed: Vec<GemvInput>,
    /// Feed-forward activations, one per width.
    pub ffn: Vec<GemvInput>,
    /// Inputs of weights stored folded, one per width; empty unless the
    /// model has such weights.
    pub folded: Vec<GemvInput>,
    /// Embedding and hidden state side by side, for the prediction block.
    pub joined: Option<GemvInput>,
    pub logits: DeviceBuffer<f32>,
    pub greedy: Argmax,
    /// Per-layer inputs of every layer, and the token rows they start from.
    pub per_layer: DeviceBuffer<f32>,
    pub per_layer_tokens: DeviceBuffer<f32>,
}

/// The input with `width` elements among `inputs`, which has one.
pub(super) fn by_width(inputs: &mut [GemvInput], width: usize) -> &mut GemvInput {
    inputs
        .iter_mut()
        .find(|i| i.width() == width)
        .expect("scratch has an input of every width")
}

/// What a block needs of the scratch: projections per token, scratch for a
/// full batch and the width of its output projection's input.
#[derive(Default)]
pub(super) struct Needs {
    pub proj: [usize; 4],
    pub scratch: usize,
    pub width: usize,
}

/// Adds width `w` to `widths`; zero, a block that has no such input, as a
/// layer without a shared expert, adds none.
fn add_width(widths: &mut Vec<usize>, w: usize) {
    if w > 0 && !widths.contains(&w) {
        widths.push(w);
    }
}

/// A batch, its scratch and the per-layer state of one sequence.
pub(super) struct Work {
    pub batch: Batch,
    pub scratch: Scratch,
    pub layers: Vec<LayerState>,
    /// Buffers for routed experts and for passes, in a mixture-of-experts
    /// model.
    pub experts: Option<ExpertWork>,
    pub pass: Option<PassRows>,
    /// The states of the layers that run on the host.
    pub front: Vec<MixerState>,
}

/// A batch and scratch for full prefill batches, lent to whichever state
/// runs one, so that states keep buffers for [`MAX_BATCH`] rows only.
pub(super) struct Spare {
    batch: Batch,
    scratch: Scratch,
}

impl Spare {
    pub fn new(work: Work) -> Spare {
        Spare {
            batch: work.batch,
            scratch: work.scratch,
        }
    }

    /// Trades these buffers for `work`'s; a second call trades them back.
    pub fn swap(&mut self, work: &mut Work) {
        std::mem::swap(&mut self.batch, &mut work.batch);
        std::mem::swap(&mut self.scratch, &mut work.scratch);
    }
}

impl Work {
    /// Buffers for running `layers` of width `d` over up to `capacity`
    /// positions in batches of up to `rows` tokens, with room for
    /// [`MAX_BATCH`] rows of `vocab` logits and, if `joined` is not zero, a
    /// joined input of that width; olded adds inputs for folded weights.
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        gpu: &Gpu,
        layers: &[&CudaLayer],
        d: usize,
        capacity: usize,
        rows: usize,
        vocab: usize,
        joined: usize,
        folded: bool,
    ) -> kinetic_cuda::Result<Work> {
        let ctx = &gpu.ctx;
        // windows keep room for a full batch, which a spare may lend
        let window_rows = super::batch_rows(&gpu.kernels, capacity).max(rows);
        let states = layers
            .iter()
            .map(|l| l.new_state(gpu, capacity, window_rows))
            .collect::<kinetic_cuda::Result<Vec<_>>>()?;

        let mut proj = [0; 4];
        let mut scratch = 0;
        let (mut mixed, mut ffn) = (Vec::new(), Vec::new());
        for (layer, state) in layers.iter().zip(&states) {
            let ffn_needs = layer.ffn_needs();
            for needs in layer.mixer.needs(state, rows) {
                let both = needs.proj.into_iter().zip(ffn_needs.proj);
                for (p, (m, f)) in proj.iter_mut().zip(both) {
                    *p = (*p).max(m).max(f);
                }
                scratch = scratch.max(needs.scratch);
                add_width(&mut mixed, needs.width);
            }
            add_width(&mut ffn, ffn_needs.width);
            add_width(&mut ffn, layer.input.as_ref().map_or(0, |i| i.width()));
        }
        let per_layer: usize = layers
            .iter()
            .filter_map(|l| l.input.as_ref())
            .map(|i| i.width())
            .sum();
        let parallel = layers.iter().any(|l| l.mixer.is_parallel());
        let mut folded_widths = Vec::new();
        if folded {
            for w in mixed.iter().chain(&ffn).chain([&d]) {
                add_width(&mut folded_widths, *w);
            }
        }

        let f32s = |len: usize| DeviceBuffer::<f32>::new(ctx, len.max(1));
        let inputs = |widths: Vec<usize>| {
            widths
                .into_iter()
                .map(|w| GemvInput::batch(ctx, w, rows))
                .collect::<kinetic_cuda::Result<Vec<_>>>()
        };
        Ok(Work {
            batch: Batch::new(ctx, rows)?,
            scratch: Scratch {
                x: f32s(rows * d)?,
                y: f32s(rows * d)?,
                sum: f32s(if parallel { rows * d } else { 0 })?,
                h: GemvInput::batch(ctx, d, rows)?,
                proj: [
                    f32s(rows * proj[0])?,
                    f32s(rows * proj[1])?,
                    f32s(rows * proj[2])?,
                    f32s(rows * proj[3])?,
                ],
                scratch: f32s(scratch)?,
                mixed: inputs(mixed)?,
                ffn: inputs(ffn)?,
                folded: inputs(folded_widths)?,
                joined: (joined > 0)
                    .then(|| GemvInput::batch(ctx, joined, rows))
                    .transpose()?,
                logits: f32s(MAX_BATCH * vocab)?,
                greedy: Argmax::new(ctx, MAX_BATCH, vocab)?,
                per_layer: f32s(rows * per_layer)?,
                per_layer_tokens: f32s(rows * per_layer)?,
            },
            layers: states,
            experts: None,
            pass: None,
            front: Vec::new(),
        })
    }

    /// Device bytes held.
    pub fn size_bytes(&self) -> usize {
        let s = &self.scratch;
        let input = |i: &GemvInput| i.capacity() * i.width() * 6;
        let buffers = s.x.len()
            + s.y.len()
            + s.sum.len()
            + s.scratch.len()
            + s.logits.len()
            + s.per_layer.len()
            + s.per_layer_tokens.len();
        let proj: usize = s.proj.iter().map(DeviceBuffer::len).sum();
        let inputs: usize = s
            .mixed
            .iter()
            .chain(&s.ffn)
            .chain(&s.folded)
            .chain(&s.joined)
            .chain([&s.h])
            .map(input)
            .sum();
        let layers: usize = self.layers.iter().map(LayerState::size_bytes).sum();
        let experts = self.experts.as_ref().map_or(0, ExpertWork::size_bytes)
            + self.pass.as_ref().map_or(0, PassRows::size_bytes);
        4 * (buffers + proj) + inputs + layers + experts
    }
}
