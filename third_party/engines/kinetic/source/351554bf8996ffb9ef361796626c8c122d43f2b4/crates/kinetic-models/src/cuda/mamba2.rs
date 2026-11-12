use kinetic_cuda::{Batch, DeviceBuffer, DeviceMatrix, Flow, SsmParams, SsmShape, SsmState};

use super::scratch::{by_width, Needs, Scratch};
use super::{cuda_error, Gpu};
use crate::blocks::Mamba2;
use crate::LoadError;

/// The Mamba-2 mixer on the device; see [`Mamba2`].
pub(super) struct CudaMamba2 {
    shape: SsmShape,
    in_proj: DeviceMatrix,
    out: DeviceMatrix,
    conv: DeviceBuffer<f32>,
    conv_bias: DeviceBuffer<f32>,
    dt_bias: DeviceBuffer<f32>,
    a: DeviceBuffer<f32>,
    d: DeviceBuffer<f32>,
    norm: Option<DeviceBuffer<f32>>,
}

impl CudaMamba2 {
    pub fn upload(gpu: &Gpu, m: &Mamba2) -> Result<CudaMamba2, LoadError> {
        let vector = |v: &[f32]| gpu.vector(v).map_err(cuda_error);
        Ok(CudaMamba2 {
            shape: SsmShape {
                n_head: m.n_head,
                head_dim: m.head_dim,
                n_group: m.n_group,
                d_state: m.d_state,
                conv_taps: m.conv_taps,
                eps: m.eps,
            },
            in_proj: gpu.matrix(&m.in_proj).map_err(cuda_error)?,
            out: gpu.matrix(&m.out).map_err(cuda_error)?,
            conv: vector(&m.conv)?,
            conv_bias: vector(&m.conv_bias)?,
            dt_bias: vector(&m.dt_bias)?,
            a: vector(&m.a)?,
            d: vector(&m.d)?,
            norm: m.norm.as_deref().map(vector).transpose()?,
        })
    }

    /// Convolution channels and taps.
    pub fn conv(&self) -> (usize, usize) {
        (self.shape.channels(), self.shape.conv_taps)
    }

    pub fn size_bytes(&self) -> usize {
        self.in_proj.size_bytes() + self.out.size_bytes()
    }

    fn params(&self) -> SsmParams<'_> {
        SsmParams {
            shape: &self.shape,
            conv: &self.conv,
            conv_bias: &self.conv_bias,
            dt_bias: &self.dt_bias,
            a: &self.a,
            d: &self.d,
            norm: self.norm.as_ref(),
        }
    }

    pub fn new_state(&self, gpu: &Gpu) -> kinetic_cuda::Result<SsmState> {
        SsmState::new(&gpu.ctx, &self.shape)
    }

    /// Needs for batches of up to `rows` tokens.
    pub fn needs(&self, rows: usize) -> Needs {
        Needs {
            proj: [self.shape.proj_len(), 0, 0, 0],
            scratch: self.shape.scratch_len(rows),
            width: self.shape.inner(),
        }
    }

    /// Reads `s.h` and leaves the projected output in `s.y`.
    pub fn forward(
        &self,
        gpu: &Gpu,
        s: &mut Scratch,
        state: &mut SsmState,
        flow: Flow,
        batch: &Batch,
    ) -> kinetic_cuda::Result<()> {
        self.project(gpu, s, batch.len())?;
        self.mix(gpu, s, state, flow, batch)?;
        self.output(gpu, s, batch.len())
    }

    /// Queues the projection of the first `n` rows of `s.h` into `s.proj`.
    pub fn project(&self, gpu: &Gpu, s: &mut Scratch, n: usize) -> kinetic_cuda::Result<()> {
        let rows = self.in_proj.rows();
        gpu.kernels
            .gemv_rows(&self.in_proj, rows, &s.h, 0..n, &mut s.proj[0], &gpu.stream)
    }

    /// Queues the scan over the batch projected in `s.proj`, which leaves
    /// the output projection's input in `s.mixed`.
    pub fn mix(
        &self,
        gpu: &Gpu,
        s: &mut Scratch,
        state: &mut SsmState,
        flow: Flow,
        batch: &Batch,
    ) -> kinetic_cuda::Result<()> {
        let out = by_width(&mut s.mixed, self.shape.inner());
        gpu.kernels.ssm(
            self.params(),
            &s.proj[0],
            &mut s.scratch,
            out,
            state,
            flow,
            batch,
            &gpu.stream,
        )
    }

    /// Queues the output projection of the first `n` rows of `s.mixed`
    /// into `s.y`.
    pub fn output(&self, gpu: &Gpu, s: &mut Scratch, n: usize) -> kinetic_cuda::Result<()> {
        let out = by_width(&mut s.mixed, self.shape.inner());
        gpu.kernels
            .gemv_rows(&self.out, self.out.rows(), out, 0..n, &mut s.y, &gpu.stream)
    }

    pub fn replay(&self, gpu: &Gpu, state: &mut SsmState, keep: usize) -> kinetic_cuda::Result<()> {
        gpu.kernels
            .ssm_replay(self.params(), state, keep, &gpu.stream)
    }
}
