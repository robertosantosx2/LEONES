//! Long inputs to mixture-of-experts models run layer by layer: every token
//! of a pass goes through a layer's front, `MAX_BATCH` at a time, before the
//! layer's routed experts run once for all of them, so each expert's weights
//! are read once per pass instead of once per batch.
//!
//! Every kernel sees exactly the rows it would see batch by batch, so a pass
//! gives the same bits as running its tokens `MAX_BATCH` at a time.

use kinetic_cuda::{DeviceBuffer, Flow, MAX_BATCH};

use super::scratch::Work;
use super::{CudaModel, Gpu};

/// Most tokens in one pass.
pub(super) const PASS_ROWS: usize = 512;

/// The stream, feed-forward input and feed-forward output of every token of
/// a pass.
pub(super) struct PassRows {
    x: DeviceBuffer<f32>,
    h: DeviceBuffer<f32>,
    y: DeviceBuffer<f32>,
}

impl PassRows {
    pub fn new(gpu: &Gpu, d: usize) -> kinetic_cuda::Result<PassRows> {
        let rows = || DeviceBuffer::<f32>::new(&gpu.ctx, PASS_ROWS * d);
        Ok(PassRows {
            x: rows()?,
            h: rows()?,
            y: rows()?,
        })
    }

    pub fn size_bytes(&self) -> usize {
        4 * (self.x.len() + self.h.len() + self.y.len())
    }
}

impl CudaModel<'_> {
    /// Runs up to [`PASS_ROWS`] `tokens` from position `pos` and copies the
    /// normalized final hidden state of each into `hidden`. Leaves the last
    /// batch's final hidden states in the scratch for the head.
    pub(super) fn queue_pass(
        &self,
        work: &mut Work,
        pos: usize,
        tokens: &[u32],
        hidden: &mut [f32],
    ) -> kinetic_cuda::Result<()> {
        let (stream, d) = (&self.gpu.stream, self.n_embd);
        let n = tokens.len();
        let mut offload = self
            .offload
            .as_ref()
            .expect("passes need experts")
            .borrow_mut();
        let rows = work.pass.as_mut().expect("a state of an expert model");
        let experts = work.experts.as_mut().expect("a state of an expert model");
        let mut moe_layer = 0;
        for (l, layer) in self.layers.iter().enumerate() {
            // dense layers (LFM2 MoE's leading ones) only run front and back
            let routed = layer.experts.as_ref();
            let g = routed.map_or(0, |r| r.score_rows());
            for (c, chunk) in tokens.chunks(MAX_BATCH).enumerate() {
                let (at, m) = (c * MAX_BATCH * d, chunk.len());
                work.batch.set(pos + c * MAX_BATCH, chunk, stream)?;
                let s = &mut work.scratch;
                if l == 0 {
                    self.embed_rows(&work.batch, chunk, &mut s.x)?;
                    layer.input(&self.gpu, &s.x, &mut s.h, m)?;
                } else {
                    s.x.copy_from_device(0, &rows.x, at..at + m * d, stream)?;
                    s.y.copy_from_device(0, &rows.y, at..at + m * d, stream)?;
                    self.layers[l - 1].back(&self.gpu, s, m, layer.mixer_norm.as_ref())?;
                }
                layer.front(&self.gpu, s, &mut work.layers[l], Flow::Commit, &work.batch)?;
                if let Some(routed) = routed {
                    routed.score(&self.gpu, &s.h, m, &mut experts.chunk_gates)?;
                    let scores = c * MAX_BATCH * g;
                    experts.gates.copy_from_device(
                        scores,
                        &experts.chunk_gates,
                        0..m * g,
                        stream,
                    )?;
                }
                rows.x.copy_from_device(at, &s.x, 0..m * d, stream)?;
                rows.h
                    .copy_from_device(at, s.h.values(), 0..m * d, stream)?;
                rows.y.copy_from_device(at, &s.y, 0..m * d, stream)?;
            }
            if let Some(routed) = routed {
                routed.mix(
                    moe_layer,
                    &self.gpu,
                    &rows.h,
                    &mut rows.y,
                    experts,
                    &mut offload,
                    n,
                )?;
                moe_layer += 1;
            }
        }
        let last = self.layers.last().expect("a model has layers");
        for (c, chunk) in tokens.chunks(MAX_BATCH).enumerate() {
            let (at, m) = (c * MAX_BATCH * d, chunk.len());
            let s = &mut work.scratch;
            s.x.copy_from_device(0, &rows.x, at..at + m * d, stream)?;
            s.y.copy_from_device(0, &rows.y, at..at + m * d, stream)?;
            last.back(&self.gpu, s, m, Some(&self.output_norm))?;
            s.h.values().copy_range_to(0, &mut hidden[at..at + m * d])?;
        }
        Ok(())
    }
}
