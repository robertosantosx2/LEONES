use kinetic_vulkan::{
    Commands, DeltaShape, DeltaState, DeltaWeights, DeviceBuffer, DeviceMatrix, Out, Rows,
};

use super::layer::R;
use super::work::{Needs, Work};
use super::Gpu;
use crate::blocks::DeltaNet;
use crate::LoadError;

/// Gated delta-rule linear attention on the device; see [`DeltaNet`].
pub(super) struct VulkanDeltaNet {
    pub shape: DeltaShape,
    qkv: DeviceMatrix,
    z: DeviceMatrix,
    beta: DeviceMatrix,
    alpha: DeviceMatrix,
    conv: DeviceBuffer<f32>,
    /// `dt_bias`, then `a`, per value head.
    heads: DeviceBuffer<f32>,
    norm: DeviceBuffer<f32>,
    out: DeviceMatrix,
}

impl VulkanDeltaNet {
    pub fn upload(gpu: &Gpu, d: &DeltaNet) -> Result<Self, LoadError> {
        let shape = DeltaShape {
            n_k_heads: d.n_k_heads,
            n_v_heads: d.n_v_heads,
            head_k_dim: d.head_k_dim,
            head_v_dim: d.head_v_dim,
            conv_taps: d.conv_taps,
            eps: d.eps,
        };
        let heads: Vec<f32> = d.dt_bias.iter().chain(&d.a).copied().collect();
        Ok(VulkanDeltaNet {
            shape,
            qkv: gpu.matrix(&d.qkv)?,
            z: gpu.matrix(&d.z)?,
            beta: gpu.matrix(&d.beta)?,
            alpha: gpu.matrix(&d.alpha)?,
            conv: gpu.vector(&d.conv)?,
            heads: gpu.vector(&heads)?,
            norm: gpu.vector(&d.norm)?,
            out: gpu.matrix(&d.out)?,
        })
    }

    pub fn size_bytes(&self) -> usize {
        [&self.qkv, &self.z, &self.beta, &self.alpha, &self.out]
            .map(DeviceMatrix::size_bytes)
            .iter()
            .sum()
    }

    pub fn needs(&self) -> Needs {
        Needs {
            proj: self.shape.proj_len(),
            width: self.shape.value_dim(),
            rec: self.shape.value_dim(),
        }
    }

    /// Reads `w.h` and leaves the projected output in `w.y`.
    pub fn record(&self, gpu: &Gpu, w: &Work, state: &DeltaState, c: &mut Commands) -> R {
        let (k, s) = (&gpu.kernels, &self.shape);
        let stride = s.proj_len();
        let (channels, vd, nv) = (s.channels(), s.value_dim(), s.n_v_heads);
        let projections = [
            (&self.qkv, 0),
            (&self.z, channels),
            (&self.beta, channels + vd),
            (&self.alpha, channels + vd + nv),
        ];
        // The projections write disjoint columns of each row.
        c.independent(|c| {
            for (m, offset) in projections {
                let out = Out { stride, offset };
                k.gemv_rows(m, &w.h, &w.proj, out, Rows::Tokens, &w.batch, c)?;
            }
            Ok(())
        })?;
        let weights = DeltaWeights {
            conv: &self.conv,
            heads: &self.heads,
            norm: &self.norm,
        };
        let mixed = w.mixed(vd);
        k.delta_net(&w.batch, s, &w.proj, &weights, state, &w.rec, mixed, c)?;
        let out = Out {
            stride: w.d,
            offset: 0,
        };
        k.gemv_rows(&self.out, mixed, &w.y, out, Rows::Tokens, &w.batch, c)
    }

    /// Records the replay a rollback runs.
    pub fn record_replay(&self, gpu: &Gpu, w: &Work, state: &DeltaState, c: &mut Commands) -> R {
        gpu.kernels
            .delta_replay(&w.batch, &self.shape, state, &w.rec, c)
    }
}
