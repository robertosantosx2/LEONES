use kinetic_quant::Matrix;
use kinetic_vulkan::{
    AttentionGate, AttentionShape, Commands, DeviceBuffer, DeviceMatrix, KvCache, Out, QkvConsts,
    Rows,
};

use super::layer::{unsupported, R};
use super::rope::RopeTables;
use super::work::{Needs, Work};
use super::Gpu;
use crate::blocks::{Attention, Gate, RopeLayout};
use crate::LoadError;

/// Attention on the device; see [`Attention`].
pub(super) struct VulkanAttention {
    pub shape: AttentionShape,
    q: DeviceMatrix,
    k: DeviceMatrix,
    v: DeviceMatrix,
    o: DeviceMatrix,
    /// One gate value per head, when the layer has them.
    head_gate: Option<DeviceMatrix>,
    /// Query and key norms and the projection biases, at the offsets below.
    consts: DeviceBuffer<f32>,
    q_norm: Option<usize>,
    k_norm: Option<usize>,
    bias: Option<usize>,
    /// The batch table word where this layer's rotary angles start.
    rope_table: usize,
}

impl VulkanAttention {
    pub fn upload(gpu: &Gpu, a: &Attention, ropes: &mut RopeTables) -> Result<Self, LoadError> {
        let gate = match a.gate {
            Gate::Interleaved => AttentionGate::PerValue,
            Gate::PerHead(_) => AttentionGate::PerHead,
            Gate::None => AttentionGate::None,
        };
        let per_head = |n: &Option<Vec<f32>>| n.as_ref().is_none_or(|w| w.len() == a.head_dim);
        if !per_head(&a.q_norm) || !per_head(&a.k_norm) {
            return Err(unsupported("query and key norms across heads"));
        }
        let shape = AttentionShape {
            n_head: a.n_head,
            n_head_kv: a.n_head_kv,
            head_dim: a.head_dim,
            rope_dims: a.rope.dims,
            rope_adjacent: a.rope.layout == RopeLayout::Adjacent,
            norm_after_rope: a.norm_after_rope,
            gate,
            window: a.window,
            scale: a.scale.unwrap_or(1.0 / (a.head_dim as f32).sqrt()),
            eps: a.eps,
        };
        if a.q.rows != a.n_head * shape.q_head_len() || a.k.rows != shape.kv_dim() {
            return Err(LoadError(format!(
                "attention projections of {} and {} rows do not fit {shape:?}",
                a.q.rows, a.k.rows
            )));
        }

        let mut consts = Vec::new();
        let mut push = |v: &[f32]| {
            let at = consts.len();
            consts.extend_from_slice(v);
            at
        };
        let q_norm = a.q_norm.as_deref().map(&mut push);
        let k_norm = a.k_norm.as_deref().map(&mut push);
        let bias = (a.q_bias.is_some() || a.k_bias.is_some() || a.v_bias.is_some()).then(|| {
            let part = |b: &Option<Vec<f32>>, len: usize| b.clone().unwrap_or(vec![0.0; len]);
            let mut all = part(&a.q_bias, a.q.rows);
            all.extend(part(&a.k_bias, a.k.rows));
            all.extend(part(&a.v_bias, a.v.rows));
            push(&all)
        });
        if consts.is_empty() {
            consts.push(0.0);
        }
        let matrix = |m: &Matrix| gpu.matrix(m);
        Ok(VulkanAttention {
            q: matrix(&a.q)?,
            k: matrix(&a.k)?,
            v: matrix(&a.v)?,
            o: matrix(&a.o)?,
            head_gate: match &a.gate {
                Gate::PerHead(g) => Some(matrix(g)?),
                Gate::Interleaved | Gate::None => None,
            },
            consts: gpu.vector(&consts)?,
            q_norm,
            k_norm,
            bias,
            rope_table: ropes.table(&a.rope)?,
            shape,
        })
    }

    pub fn size_bytes(&self) -> usize {
        [&self.q, &self.k, &self.v, &self.o]
            .into_iter()
            .chain(&self.head_gate)
            .map(DeviceMatrix::size_bytes)
            .sum()
    }

    pub fn needs(&self) -> Needs {
        let s = &self.shape;
        Needs {
            proj: s.qkv_len(),
            width: s.n_head * s.head_dim,
            rec: 0,
        }
    }

    /// Reads `w.h` and leaves the projected output in `w.y`.
    pub fn record(&self, gpu: &Gpu, w: &Work, cache: &KvCache, c: &mut Commands) -> R {
        let (k, s) = (&gpu.kernels, &self.shape);
        let stride = s.qkv_len();
        let q_len = s.n_head * s.q_head_len();
        let projections = [
            (&self.q, 0),
            (&self.k, q_len),
            (&self.v, q_len + s.kv_dim()),
        ];
        let gates = self.head_gate.iter().map(|g| (g, s.gate_at()));
        // The projections write disjoint columns of each row.
        c.independent(|c| {
            for (m, offset) in projections.into_iter().chain(gates) {
                let out = Out { stride, offset };
                k.gemv_rows(m, &w.h, &w.proj, out, Rows::Tokens, &w.batch, c)?;
            }
            Ok(())
        })?;
        let consts = QkvConsts {
            data: &self.consts,
            q_norm: self.q_norm,
            k_norm: self.k_norm,
            bias: self.bias,
        };
        let att = w.mixed(s.n_head * s.head_dim);
        k.attention(
            &w.batch,
            s,
            &w.proj,
            &consts,
            self.rope_table,
            cache,
            att,
            c,
        )?;
        let out = Out {
            stride: w.d,
            offset: 0,
        };
        k.gemv_rows(&self.o, att, &w.y, out, Rows::Tokens, &w.batch, c)
    }
}
