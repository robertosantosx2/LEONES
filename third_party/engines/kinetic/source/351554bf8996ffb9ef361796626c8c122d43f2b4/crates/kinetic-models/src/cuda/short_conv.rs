use kinetic_cuda::{Batch, ConvState, DeviceBuffer, DeviceMatrix, MAX_BATCH};

use super::scratch::{by_width, Needs, Scratch};
use super::{cuda_error, Gpu};
use crate::blocks::ShortConv;
use crate::LoadError;

/// Gated short convolution on the device; see [`ShortConv`].
pub(super) struct CudaShortConv {
    in_proj: DeviceMatrix,
    out_proj: DeviceMatrix,
    conv: DeviceBuffer<f32>,
    taps: usize,
}

impl CudaShortConv {
    pub fn upload(gpu: &Gpu, s: &ShortConv) -> Result<CudaShortConv, LoadError> {
        Ok(CudaShortConv {
            in_proj: gpu.matrix(&s.in_proj).map_err(cuda_error)?,
            out_proj: gpu.matrix(&s.out_proj).map_err(cuda_error)?,
            conv: gpu.vector(&s.conv).map_err(cuda_error)?,
            taps: s.taps,
        })
    }

    pub fn size_bytes(&self) -> usize {
        self.in_proj.size_bytes() + self.out_proj.size_bytes()
    }

    fn channels(&self) -> usize {
        self.out_proj.cols()
    }

    /// Convolution channels and taps.
    pub fn conv(&self) -> (usize, usize) {
        (self.channels(), self.taps)
    }

    pub fn new_state(&self, gpu: &Gpu) -> kinetic_cuda::Result<ConvState> {
        ConvState::new(&gpu.ctx, self.channels(), self.taps, MAX_BATCH)
    }

    pub fn needs(&self) -> Needs {
        Needs {
            proj: [self.in_proj.rows(), 0, 0, 0],
            scratch: 0,
            width: self.channels(),
        }
    }

    /// Reads `s.h` and leaves the projected output in `s.y`.
    pub fn forward(
        &self,
        gpu: &Gpu,
        s: &mut Scratch,
        state: &mut ConvState,
        batch: &Batch,
    ) -> kinetic_cuda::Result<()> {
        self.project(gpu, s, batch.len())?;
        self.mix(gpu, s, state, batch)?;
        self.output(gpu, s, batch.len())
    }

    /// Queues the projection of the first `n` rows of `s.h` into `s.proj`.
    pub fn project(&self, gpu: &Gpu, s: &mut Scratch, n: usize) -> kinetic_cuda::Result<()> {
        let rows = self.in_proj.rows();
        gpu.kernels
            .gemv_rows(&self.in_proj, rows, &s.h, 0..n, &mut s.proj[0], &gpu.stream)
    }

    /// Queues the convolution of the batch projected in `s.proj`, which
    /// leaves the output projection's input in `s.mixed`.
    pub fn mix(
        &self,
        gpu: &Gpu,
        s: &mut Scratch,
        state: &mut ConvState,
        batch: &Batch,
    ) -> kinetic_cuda::Result<()> {
        let out = by_width(&mut s.mixed, self.channels());
        gpu.kernels
            .short_conv(&self.conv, &s.proj[0], state, out, batch, &gpu.stream)
    }

    /// Queues the output projection of the first `n` rows of `s.mixed`
    /// into `s.y`.
    pub fn output(&self, gpu: &Gpu, s: &mut Scratch, n: usize) -> kinetic_cuda::Result<()> {
        let out = by_width(&mut s.mixed, self.channels());
        let rows = self.out_proj.rows();
        gpu.kernels
            .gemv_rows(&self.out_proj, rows, out, 0..n, &mut s.y, &gpu.stream)
    }
}
