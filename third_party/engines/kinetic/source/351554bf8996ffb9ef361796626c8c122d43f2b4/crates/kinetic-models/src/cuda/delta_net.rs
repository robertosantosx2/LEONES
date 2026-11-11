use kinetic_cuda::{
    Batch, DeltaIo, DeltaParams, DeltaShape, DeltaState, DeviceBuffer, DeviceMatrix, Flow,
    ValueHeads, MAX_BATCH,
};

use super::fold::CudaFolding;
use super::scratch::{by_width, Needs, Scratch};
use super::{cuda_error, Gpu};
use crate::blocks::DeltaNet;
use crate::LoadError;

/// Gated delta-rule linear attention on the device; see [`DeltaNet`].
pub(super) struct CudaDeltaNet {
    shape: DeltaShape,
    qkv: DeviceMatrix,
    z: DeviceMatrix,
    beta: DeviceMatrix,
    alpha: DeviceMatrix,
    out: DeviceMatrix,
    conv: DeviceBuffer<f32>,
    dt_bias: DeviceBuffer<f32>,
    a: DeviceBuffer<f32>,
    norm: DeviceBuffer<f32>,
    folding: Option<CudaFolding>,
}

impl CudaDeltaNet {
    pub fn upload(gpu: &Gpu, d: &DeltaNet) -> Result<CudaDeltaNet, LoadError> {
        let matrix = |m| gpu.matrix(m).map_err(cuda_error);
        let vector = |v: &[f32]| gpu.vector(v).map_err(cuda_error);
        Ok(CudaDeltaNet {
            shape: DeltaShape {
                n_k_heads: d.n_k_heads,
                n_v_heads: d.n_v_heads,
                head_k_dim: d.head_k_dim,
                head_v_dim: d.head_v_dim,
                conv_taps: d.conv_taps,
                eps: d.eps,
            },
            qkv: matrix(&d.qkv)?,
            z: matrix(&d.z)?,
            beta: matrix(&d.beta)?,
            alpha: matrix(&d.alpha)?,
            out: matrix(&d.out)?,
            conv: vector(&d.conv)?,
            dt_bias: vector(&d.dt_bias)?,
            a: vector(&d.a)?,
            norm: vector(&d.norm)?,
            folding: d
                .folding
                .as_deref()
                .map(|f| CudaFolding::upload(gpu, f))
                .transpose()?,
        })
    }

    /// Convolution channels and taps.
    pub fn conv(&self) -> (usize, usize) {
        (self.shape.channels(), self.shape.conv_taps)
    }

    pub fn size_bytes(&self) -> usize {
        [&self.qkv, &self.z, &self.beta, &self.alpha, &self.out]
            .into_iter()
            .map(DeviceMatrix::size_bytes)
            .sum()
    }

    fn params(&self) -> DeltaParams<'_> {
        DeltaParams {
            shape: &self.shape,
            conv: &self.conv,
            dt_bias: &self.dt_bias,
            a: &self.a,
            norm: &self.norm,
        }
    }

    pub fn new_state(&self, gpu: &Gpu) -> kinetic_cuda::Result<DeltaState> {
        DeltaState::new(&gpu.ctx, &self.shape, MAX_BATCH)
    }

    /// Needs for batches of up to `rows` tokens.
    pub fn needs(&self, rows: usize) -> Needs {
        let (vd, nv) = (self.shape.value_dim(), self.shape.n_v_heads);
        Needs {
            proj: [self.shape.channels(), vd, nv, nv],
            scratch: self.shape.scratch_len(rows),
            width: vd,
        }
    }

    /// Reads `s.h` and leaves the projected output in `s.y`.
    pub fn forward(
        &self,
        gpu: &Gpu,
        s: &mut Scratch,
        state: &mut DeltaState,
        flow: Flow,
        batch: &Batch,
    ) -> kinetic_cuda::Result<()> {
        self.project(gpu, s, batch.len())?;
        self.mix(gpu, s, state, flow, batch)?;
        self.output(gpu, s, batch.len())
    }

    /// Queues the projections of the first `n` rows of `s.h` into `s.proj`.
    pub fn project(&self, gpu: &Gpu, s: &mut Scratch, n: usize) -> kinetic_cuda::Result<()> {
        let (k, stream) = (&gpu.kernels, &gpu.stream);
        let [qkv, z, alpha, beta] = &mut s.proj;
        let x = match &self.folding {
            Some(f) => f.fold(gpu, &s.h, &mut s.folded, n)?,
            None => &s.h,
        };
        gpu.fork()?;
        let side = &gpu.side;
        k.gemv_rows(&self.alpha, self.alpha.rows(), &s.h, 0..n, alpha, side)?;
        k.gemv_rows(&self.beta, self.beta.rows(), &s.h, 0..n, beta, side)?;
        k.gemv_rows(&self.qkv, self.qkv.rows(), x, 0..n, qkv, stream)?;
        k.gemv_rows(&self.z, self.z.rows(), x, 0..n, z, stream)?;
        gpu.join()
    }

    /// Queues the recurrence over the batch projected in `s.proj`, which
    /// leaves the output projection's input in `s.mixed`.
    pub fn mix(
        &self,
        gpu: &Gpu,
        s: &mut Scratch,
        state: &mut DeltaState,
        flow: Flow,
        batch: &Batch,
    ) -> kinetic_cuda::Result<()> {
        let [qkv, z, alpha, beta] = &mut s.proj;
        let out = by_width(&mut s.mixed, self.shape.value_dim());
        let io = DeltaIo {
            qkv,
            z,
            alpha,
            beta,
            scratch: &mut s.scratch,
            out: &mut *out,
        };
        gpu.kernels
            .delta_net(self.params(), io, state, flow, batch, &gpu.stream)
    }

    /// Queues the output projection of the first `n` rows of `s.mixed`
    /// into `s.y`.
    pub fn output(&self, gpu: &Gpu, s: &mut Scratch, n: usize) -> kinetic_cuda::Result<()> {
        let out = by_width(&mut s.mixed, self.shape.value_dim());
        let heads = ValueHeads {
            head_dim: self.shape.head_v_dim,
            n_k: self.shape.n_k_heads,
            n_v: self.shape.n_v_heads,
        };
        let out = match &self.folding {
            Some(f) => f.fold_heads(gpu, out, Some(heads), &mut s.folded, n)?,
            None => &*out,
        };
        gpu.kernels
            .gemv_rows(&self.out, self.out.rows(), out, 0..n, &mut s.y, &gpu.stream)
    }

    pub fn replay(
        &self,
        gpu: &Gpu,
        state: &mut DeltaState,
        keep: usize,
    ) -> kinetic_cuda::Result<()> {
        gpu.kernels
            .delta_replay(self.params(), state, keep, &gpu.stream)
    }
}
