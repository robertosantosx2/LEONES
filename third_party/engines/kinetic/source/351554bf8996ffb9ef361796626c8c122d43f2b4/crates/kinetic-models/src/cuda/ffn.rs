use kinetic_cuda::DeviceMatrix;

use super::fold::CudaFolding;
use super::scratch::{by_width, Needs, Scratch};
use super::{cuda_error, Gpu};
use crate::blocks::{Activation, SwiGlu};
use crate::LoadError;

/// The gated feed-forward on the device; see [`SwiGlu`].
pub(super) struct CudaFfn {
    gate: DeviceMatrix,
    up: DeviceMatrix,
    down: DeviceMatrix,
    activation: Activation,
    folding: Option<CudaFolding>,
}

impl CudaFfn {
    pub fn upload(gpu: &Gpu, f: &SwiGlu) -> Result<CudaFfn, LoadError> {
        let matrix = |m| gpu.matrix(m).map_err(cuda_error);
        Ok(CudaFfn {
            gate: matrix(&f.gate)?,
            up: matrix(&f.up)?,
            down: matrix(&f.down)?,
            activation: f.activation,
            folding: f
                .folding
                .as_deref()
                .map(|f| CudaFolding::upload(gpu, f))
                .transpose()?,
        })
    }

    pub fn size_bytes(&self) -> usize {
        self.gate.size_bytes() + self.up.size_bytes() + self.down.size_bytes()
    }

    pub fn needs(&self) -> Needs {
        let n_ff = self.gate.rows();
        Needs {
            proj: [n_ff, n_ff, 0, 0],
            scratch: 0,
            width: n_ff,
        }
    }

    /// Reads `s.h` and leaves the output for `n` tokens in `s.y`.
    pub fn forward(&self, gpu: &Gpu, s: &mut Scratch, n: usize) -> kinetic_cuda::Result<()> {
        let (k, stream) = (&gpu.kernels, &gpu.stream);
        let x = match &self.folding {
            Some(f) => f.fold(gpu, &s.h, &mut s.folded, n)?,
            None => &s.h,
        };
        let act = by_width(&mut s.ffn, self.gate.rows());
        let gelu = self.activation == Activation::Gelu;
        if !k.glu_matmul(&self.gate, &self.up, gelu, x, 0..n, act, stream)? {
            let [gate, up, ..] = &mut s.proj;
            k.gemv_rows(&self.gate, self.gate.rows(), x, 0..n, gate, stream)?;
            k.gemv_rows(&self.up, self.up.rows(), x, 0..n, up, stream)?;
            match self.activation {
                Activation::Silu => k.swiglu(gate, up, act, n, stream)?,
                Activation::Gelu => k.geglu(gate, up, act, n, stream)?,
            }
        }
        let act = match &self.folding {
            Some(f) => f.fold(gpu, act, &mut s.folded, n)?,
            None => &*act,
        };
        k.gemv_rows(&self.down, self.down.rows(), act, 0..n, &mut s.y, stream)
    }
}
