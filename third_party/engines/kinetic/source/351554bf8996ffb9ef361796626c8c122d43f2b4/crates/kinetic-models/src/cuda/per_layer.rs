use kinetic_cuda::{AddNorm, Batch, DeviceBuffer, DeviceMatrix, RmsNorm};

use super::scratch::{by_width, Scratch};
use super::{cuda_error, Gpu};
use crate::per_layer::{LayerInput, PerLayer};
use crate::LoadError;

/// The per-layer token inputs on the device; see [`PerLayer`].
pub(super) struct CudaPerLayer {
    // shortcut: the 1.9 GB table of Gemma 4 E2B sits on the device; reading
    // rows on the host would free it for longer contexts
    embd: DeviceMatrix,
    proj: DeviceMatrix,
    norm: DeviceBuffer<f32>,
    width: usize,
    eps: f32,
}

impl CudaPerLayer {
    pub fn upload(gpu: &Gpu, p: &PerLayer, eps: f32) -> Result<CudaPerLayer, LoadError> {
        let matrix = |m| gpu.matrix(m).map_err(cuda_error);
        Ok(CudaPerLayer {
            embd: matrix(&p.embd)?,
            proj: matrix(&p.proj)?,
            norm: gpu.vector(&p.proj_norm).map_err(cuda_error)?,
            width: p.width,
            eps,
        })
    }

    /// Values per token of the inputs of all layers.
    pub fn len(&self) -> usize {
        self.proj.rows()
    }

    pub fn size_bytes(&self) -> usize {
        self.embd.size_bytes() + self.proj.size_bytes()
    }

    /// Queues the inputs of every layer for the batch, whose embeddings are
    /// in `s.x`, into `s.per_layer`.
    pub fn queue(&self, gpu: &Gpu, s: &mut Scratch, batch: &Batch) -> kinetic_cuda::Result<()> {
        self.embed(gpu, batch, &mut s.per_layer_tokens)?;
        self.project(gpu, s, batch.len())
    }

    /// Queues the token rows of the batch's tokens into `out`.
    pub fn embed(
        &self,
        gpu: &Gpu,
        batch: &Batch,
        out: &mut DeviceBuffer<f32>,
    ) -> kinetic_cuda::Result<()> {
        let scale = (self.width as f32).sqrt();
        gpu.kernels
            .embed(&self.embd, scale, batch, out, &gpu.stream)
    }

    /// Queues the inputs of `n` rows whose embeddings are in `s.x` and token
    /// rows in `s.per_layer_tokens` into `s.per_layer`.
    pub fn project(&self, gpu: &Gpu, s: &mut Scratch, n: usize) -> kinetic_cuda::Result<()> {
        let (k, stream) = (&gpu.kernels, &gpu.stream);
        k.input_rows(&s.x, &mut s.h, n, stream)?;
        k.gemv_rows(&self.proj, self.len(), &s.h, 0..n, &mut s.per_layer, stream)?;
        let norm = RmsNorm {
            weight: &self.norm,
            eps: self.eps,
        };
        let proj_scale = 1.0 / (self.proj.cols() as f32).sqrt();
        k.per_layer_inputs(
            &mut s.per_layer,
            &s.per_layer_tokens,
            norm,
            proj_scale,
            n * self.len(),
            stream,
        )
    }
}

/// How one layer folds its input in on the device; see [`LayerInput`].
pub(super) struct CudaLayerInput {
    gate: DeviceMatrix,
    proj: DeviceMatrix,
    norm: DeviceBuffer<f32>,
    scale: f32,
    layer: usize,
    layers: usize,
}

impl CudaLayerInput {
    pub fn upload(
        gpu: &Gpu,
        l: &LayerInput,
        layer: usize,
        layers: usize,
    ) -> Result<CudaLayerInput, LoadError> {
        let matrix = |m| gpu.matrix(m).map_err(cuda_error);
        Ok(CudaLayerInput {
            gate: matrix(&l.gate)?,
            proj: matrix(&l.proj)?,
            norm: gpu.vector(&l.norm).map_err(cuda_error)?,
            scale: l.scale,
            layer,
            layers,
        })
    }

    pub fn width(&self) -> usize {
        self.gate.rows()
    }

    pub fn size_bytes(&self) -> usize {
        self.gate.size_bytes() + self.proj.size_bytes()
    }

    /// Adds the layer's input to the stream `s.x`, whose layer output `s.h`
    /// holds as it is, scales it and leaves it normalized by `next` in `s.h`.
    pub fn queue(
        &self,
        gpu: &Gpu,
        s: &mut Scratch,
        n: usize,
        eps: f32,
        next: Option<&DeviceBuffer<f32>>,
    ) -> kinetic_cuda::Result<()> {
        let (k, stream, w) = (&gpu.kernels, &gpu.stream, self.width());
        let [gate, ..] = &mut s.proj;
        k.gemv_rows(&self.gate, w, &s.h, 0..n, gate, stream)?;
        let act = by_width(&mut s.ffn, w);
        k.per_layer_gate(gate, &s.per_layer, self.layer, self.layers, act, n, stream)?;
        k.gemv_rows(&self.proj, self.proj.rows(), act, 0..n, &mut s.y, stream)?;
        let added = AddNorm {
            post: Some(&self.norm),
            scale: 1.0,
            out_scale: self.scale,
            next,
            eps,
        };
        k.add_norm(&mut s.x, &s.y, added, &mut s.h, n, stream)
    }
}
