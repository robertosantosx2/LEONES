use kinetic_cuda::{
    AttentionIo, AttentionParams, AttentionShape, Batch, DeviceBuffer, DeviceMatrix, KvCache,
    MAX_BATCH,
};

use super::fold::CudaFolding;
use super::scratch::{by_width, Needs, Scratch};
use super::{cuda_error, Gpu};
use crate::blocks::{Attention, Gate, RopeLayout, SharedKv};
use crate::LoadError;

/// Gated attention on the device; see [`Attention`].
pub(super) struct CudaAttention {
    shape: AttentionShape,
    q: DeviceMatrix,
    /// `None` in a layer that attends over keys and values copied from
    /// another.
    k: Option<DeviceMatrix>,
    v: Option<DeviceMatrix>,
    o: DeviceMatrix,
    head_gate: Option<DeviceMatrix>,
    q_norm: Option<DeviceBuffer<f32>>,
    k_norm: Option<DeviceBuffer<f32>>,
    rope_factors: Option<DeviceBuffer<f32>>,
    q_bias: Option<DeviceBuffer<f32>>,
    k_bias: Option<DeviceBuffer<f32>>,
    v_bias: Option<DeviceBuffer<f32>>,
    folding: Option<CudaFolding>,
}

impl CudaAttention {
    pub fn upload(gpu: &Gpu, a: &Attention) -> Result<CudaAttention, LoadError> {
        let v_norm = match &a.v_norm {
            None => false,
            Some(w) if w.iter().all(|&w| w == 1.0) => true,
            Some(_) => {
                return Err(LoadError(
                    "weighted value norms are not supported on CUDA yet".into(),
                ))
            }
        };
        let own_kv = !matches!(a.shared_kv, SharedKv::Borrows(_));
        let shape = AttentionShape {
            n_head: a.n_head,
            n_head_kv: a.n_head_kv,
            head_dim: a.head_dim,
            rope_dims: a.rope.dims,
            rope_base: a.rope.base,
            rope_adjacent: a.rope.layout == RopeLayout::Adjacent,
            rope_mscale: a.rope.mscale,
            norm_after_rope: a.norm_after_rope,
            scale: a.scale.unwrap_or(1.0 / (a.head_dim as f32).sqrt()),
            eps: a.eps,
            window: a.window,
            interleaved_gate: matches!(a.gate, Gate::Interleaved),
            v_norm,
        };
        let matrix = |m| gpu.matrix(m).map_err(cuda_error);
        let vector = |v: &Option<Vec<f32>>| {
            v.as_deref()
                .map(|v| gpu.vector(v))
                .transpose()
                .map_err(cuda_error)
        };
        Ok(CudaAttention {
            shape,
            q: matrix(&a.q)?,
            k: own_kv.then(|| matrix(&a.k)).transpose()?,
            v: own_kv.then(|| matrix(&a.v)).transpose()?,
            o: matrix(&a.o)?,
            head_gate: match &a.gate {
                Gate::PerHead(g) => Some(matrix(g)?),
                Gate::Interleaved | Gate::None => None,
            },
            q_norm: vector(&a.q_norm)?,
            k_norm: vector(&a.k_norm)?,
            rope_factors: vector(&a.rope.factors)?,
            q_bias: vector(&a.q_bias)?,
            k_bias: vector(&a.k_bias)?,
            v_bias: vector(&a.v_bias)?,
            folding: a
                .folding
                .as_deref()
                .map(|f| CudaFolding::upload(gpu, f))
                .transpose()?,
        })
    }

    /// Past positions kept, when the layer attends through a window.
    pub fn window(&self) -> Option<usize> {
        self.shape.window
    }

    pub fn size_bytes(&self) -> usize {
        [&self.q, &self.o]
            .into_iter()
            .chain(&self.k)
            .chain(&self.v)
            .chain(&self.head_gate)
            .map(DeviceMatrix::size_bytes)
            .sum()
    }

    /// A cache for `capacity` positions run in batches of up to `rows`; a
    /// windowed one keeps the window plus room for a batch, which also
    /// covers the tokens run since a checkpoint.
    pub fn new_cache(
        &self,
        gpu: &Gpu,
        capacity: usize,
        rows: usize,
    ) -> kinetic_cuda::Result<KvCache> {
        let slots = self.shape.window.map_or(capacity, |w| w + rows);
        let [k, v] = gpu.cache;
        KvCache::with_types(&gpu.ctx, &self.shape, slots, k, v)
    }

    pub fn needs(&self, slots: usize) -> Needs {
        let s = &self.shape;
        let kv = s.n_head_kv * s.head_dim;
        Needs {
            proj: [s.q_len(), kv, kv, s.n_head],
            scratch: s.scratch_len(MAX_BATCH, slots),
            width: s.n_head * s.head_dim,
        }
    }

    /// Reads `s.h` and leaves the projected output in `s.y`.
    pub fn forward(
        &self,
        gpu: &Gpu,
        s: &mut Scratch,
        cache: &mut KvCache,
        batch: &Batch,
    ) -> kinetic_cuda::Result<()> {
        self.project(gpu, s, batch.len())?;
        self.mix(gpu, s, cache, batch)?;
        self.output(gpu, s, batch.len())
    }

    /// Queues the projections of the first `n` rows of `s.h` into `s.proj`.
    pub fn project(&self, gpu: &Gpu, s: &mut Scratch, n: usize) -> kinetic_cuda::Result<()> {
        let (k, stream) = (&gpu.kernels, &gpu.stream);
        let [q, keys, values, gates] = &mut s.proj;
        let x = match &self.folding {
            Some(f) => f.fold(gpu, &s.h, &mut s.folded, n)?,
            None => &s.h,
        };
        gpu.fork()?;
        let side = &gpu.side;
        if let (Some(km), Some(vm)) = (&self.k, &self.v) {
            k.gemv_rows(km, km.rows(), x, 0..n, keys, side)?;
            k.gemv_rows(vm, vm.rows(), x, 0..n, values, side)?;
        }
        if let Some(g) = &self.head_gate {
            k.gemv_rows(g, g.rows(), x, 0..n, gates, side)?;
        }
        k.gemv_rows(&self.q, self.q.rows(), x, 0..n, q, stream)?;
        gpu.join()
    }

    /// Queues attention of the batch projected in `s.proj` over `cache`,
    /// which leaves the output projection's input in `s.mixed`.
    pub fn mix(
        &self,
        gpu: &Gpu,
        s: &mut Scratch,
        cache: &mut KvCache,
        batch: &Batch,
    ) -> kinetic_cuda::Result<()> {
        let (k, stream) = (&gpu.kernels, &gpu.stream);
        let [q, keys, values, gates] = &mut s.proj;
        let out = by_width(&mut s.mixed, self.shape.n_head * self.shape.head_dim);
        let params = AttentionParams {
            shape: &self.shape,
            q_norm: self.q_norm.as_ref(),
            k_norm: self.k_norm.as_ref(),
            rope_factors: self.rope_factors.as_ref(),
            q_bias: self.q_bias.as_ref(),
            k_bias: self.k_bias.as_ref(),
            v_bias: self.v_bias.as_ref(),
            store: self.k.is_some(),
        };
        let io = AttentionIo {
            q,
            k: keys,
            v: values,
            head_gate: self.head_gate.as_ref().map(|_| &*gates),
            scratch: &mut s.scratch,
            out: &mut *out,
        };
        k.attention(params, io, cache, batch, stream)
    }

    /// Queues the output projection of the first `n` rows of `s.mixed`
    /// into `s.y`.
    pub fn output(&self, gpu: &Gpu, s: &mut Scratch, n: usize) -> kinetic_cuda::Result<()> {
        let out = by_width(&mut s.mixed, self.shape.n_head * self.shape.head_dim);
        let out = match &self.folding {
            Some(f) => f.fold(gpu, out, &mut s.folded, n)?,
            None => &*out,
        };
        gpu.kernels
            .gemv_rows(&self.o, self.o.rows(), out, 0..n, &mut s.y, &gpu.stream)
    }
}
