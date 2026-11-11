use kinetic_vulkan::{Batch, DeviceBuffer, GemvInput, HostBuffer};

use super::layer::VulkanLayer;
use super::Gpu;

/// The buffers one sequence runs its passes in.
pub(super) struct Work {
    /// The hidden width.
    pub d: usize,
    pub batch: Batch,
    /// The residual stream.
    pub x: DeviceBuffer<f32>,
    /// The output of the block just run.
    pub y: DeviceBuffer<f32>,
    /// The normalized stream, input of the next block or of the head.
    pub h: GemvInput,
    /// Mixer projections, one row per token.
    pub proj: DeviceBuffer<f32>,
    /// Recurrence outputs, one row per token.
    pub rec: DeviceBuffer<f32>,
    /// Mixer outputs, inputs of their output projections; one per width.
    mixed: Vec<GemvInput>,
    /// Gate and up projections side by side, one row per token.
    pub gu: DeviceBuffer<f32>,
    /// Feed-forward activations, one per width.
    ffn: Vec<GemvInput>,
    pub logits: DeviceBuffer<f32>,
    pub best: DeviceBuffer<u32>,
    /// The logits of the head's rows, when a run asks for them.
    pub logits_host: HostBuffer<f32>,
    /// The tokens' embeddings, written by the host.
    pub embedded: HostBuffer<f32>,
    /// The final hidden states of the last pass, and its greedy tokens
    /// each followed by the bits of its logit.
    pub hidden: HostBuffer<f32>,
    pub greedy: HostBuffer<u32>,
}

/// What a mixer needs of the work buffers per token: projection values,
/// the width of its output projection's input, and recurrence outputs.
#[derive(Default)]
pub(super) struct Needs {
    pub proj: usize,
    pub width: usize,
    pub rec: usize,
}

fn add_width(widths: &mut Vec<usize>, w: usize) {
    if !widths.contains(&w) {
        widths.push(w);
    }
}

fn by_width(inputs: &[GemvInput], width: usize) -> &GemvInput {
    inputs
        .iter()
        .find(|i| i.width() == width)
        .expect("work has an input of every width")
}

impl Work {
    /// Buffers for `layers` of width `d` run on `batch`, with an output
    /// head of `vocab` rows.
    pub fn new(
        gpu: &Gpu,
        layers: &[VulkanLayer],
        d: usize,
        batch: Batch,
        vocab: usize,
    ) -> kinetic_vulkan::Result<Work> {
        let dev = &gpu.device;
        let rows = batch.rows();
        let head = batch.head_rows();
        let (mut proj, mut rec, mut n_ff) = (0, 0, 0);
        let (mut mixed, mut ffn) = (Vec::new(), Vec::new());
        for layer in layers {
            let needs = layer.needs();
            proj = proj.max(needs.proj);
            rec = rec.max(needs.rec);
            n_ff = n_ff.max(layer.n_ff());
            add_width(&mut mixed, needs.width);
            add_width(&mut ffn, layer.n_ff());
        }
        let f32s = |len: usize| DeviceBuffer::<f32>::new(dev, len.max(1));
        let inputs = |widths: Vec<usize>| {
            widths
                .into_iter()
                .map(|w| GemvInput::batch(dev, w, rows))
                .collect::<kinetic_vulkan::Result<Vec<_>>>()
        };
        Ok(Work {
            d,
            x: f32s(rows * d)?,
            y: f32s(rows * d)?,
            h: GemvInput::batch(dev, d, rows)?,
            proj: f32s(rows * proj)?,
            rec: f32s(rows * rec)?,
            mixed: inputs(mixed)?,
            gu: f32s(rows * 2 * n_ff)?,
            ffn: inputs(ffn)?,
            logits: f32s(head * vocab)?,
            best: DeviceBuffer::new(dev, 2 * head.max(1))?,
            logits_host: HostBuffer::new(dev, (head * vocab).max(1))?,
            embedded: HostBuffer::new(dev, rows * d)?,
            hidden: HostBuffer::new(dev, rows * d)?,
            greedy: HostBuffer::new(dev, 2 * head.max(1))?,
            batch,
        })
    }

    pub fn mixed(&self, width: usize) -> &GemvInput {
        by_width(&self.mixed, width)
    }

    pub fn activations(&self, width: usize) -> &GemvInput {
        by_width(&self.ffn, width)
    }

    /// Device bytes held.
    pub fn size_bytes(&self) -> usize {
        let inputs: usize = self
            .mixed
            .iter()
            .chain(&self.ffn)
            .chain([&self.h])
            .map(|i| i.len() * 21 / 4)
            .sum();
        let floats = self.x.len() + self.y.len() + self.proj.len() + self.rec.len() + self.gu.len();
        4 * (floats + self.logits.len()) + inputs
    }
}
