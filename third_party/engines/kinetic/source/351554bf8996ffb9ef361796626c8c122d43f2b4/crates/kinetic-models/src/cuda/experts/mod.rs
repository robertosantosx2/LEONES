//! The routed experts of mixture-of-experts layers, for models larger than
//! the device.
//!
//! Everything else of the model lives on the device; the rest of device
//! memory becomes a cache of routed experts ([`Plan`]). Every expert stays
//! in the memory-mapped file, so the operating system keeps the ones it has
//! room for in host memory and reads the rest from disk.
//!
//! Each layer reads its routing back from the device. Cached experts run
//! there; for the others the runtime weighs copying them over against
//! running them on the host, which mostly wins for a single token, and the
//! host runs its share while the device runs its own. The next layer's
//! router, applied to this layer's input, predicts which experts that layer
//! will pick, and those are copied into the cache on a second stream while
//! this layer finishes. The cache keeps the experts used most.
//!
//! Host and device compute an expert's output to the same bits (see
//! `blocks/moe/kernels.rs`), and outputs are mixed in pick order on the
//! device, so where an expert ran never changes a token's result.

mod cache;
mod offload;
mod place;
mod plan;
mod stats;
#[cfg(test)]
mod tests;
mod work;

use kinetic_cuda::{
    DeviceBuffer, DeviceMatrix, ExpertArena, ExpertMix, ExpertProduct, GateLogits, GemvInput,
    Q8kRows, Routing, EXPERT_TYPES,
};
use kinetic_quant::{Matrix, TensorType};

use super::{cuda_error, Gpu};
use crate::blocks::{Gating, Moe, Pick};
use crate::LoadError;

pub(super) use offload::Offload;
pub use plan::Plan;
pub use plan::PoolPlan;
pub(super) use plan::DEVICE_RESERVE;
pub use stats::Stats;
pub(super) use work::{ExpertDims, ExpertWork};

/// The device part of one layer's routed experts: one product scores this
/// layer's router, the next layer's router (if any) and the shared expert's
/// gate (if any).
pub(super) struct CudaExperts {
    gates: DeviceMatrix,
    n_experts: usize,
    predicts: bool,
    has_shared: bool,
    has_shared_gate: bool,
    bias: Option<DeviceBuffer<f32>>,
}

impl CudaExperts {
    /// Uploads the scores of `moe`; `next` is the following layer's router,
    /// and `shared` says whether the layer has a shared expert.
    pub fn upload(
        gpu: &Gpu,
        moe: &Moe,
        next: Option<&Matrix>,
        shared: bool,
    ) -> Result<CudaExperts, LoadError> {
        check_types(moe)?;
        let routers = [Some(&moe.router), next];
        if routers.iter().flatten().any(|r| r.ty != TensorType::F32) {
            return Err(LoadError("expert routers must be f32 on CUDA".into()));
        }
        let mut bytes: Vec<u8> = routers
            .iter()
            .flatten()
            .flat_map(|r| r.data)
            .copied()
            .collect();
        if let Some(g) = &moe.shared_gate {
            bytes.extend(g.iter().flat_map(|v| v.to_le_bytes()));
        }
        let cols = moe.router.cols;
        let gates = Matrix::new(TensorType::F32, &bytes, bytes.len() / (4 * cols), cols);
        Ok(CudaExperts {
            gates: gpu.matrix(&gates).map_err(cuda_error)?,
            n_experts: moe.n_experts(),
            predicts: next.is_some(),
            has_shared: shared,
            has_shared_gate: moe.shared_gate.is_some(),
            bias: match &moe.gating {
                Gating::Sigmoid { bias } => Some(gpu.vector(bias).map_err(cuda_error)?),
                Gating::Softmax => None,
            },
        })
    }

    pub fn size_bytes(&self) -> usize {
        self.gates.size_bytes()
    }

    pub fn score_rows(&self) -> usize {
        self.gates.rows()
    }

    /// Queues the scores of the `n` tokens of `h` into `out`.
    pub fn score(
        &self,
        gpu: &Gpu,
        h: &GemvInput,
        n: usize,
        out: &mut DeviceBuffer<f32>,
    ) -> kinetic_cuda::Result<()> {
        let g = self.gates.rows();
        gpu.kernels
            .gemv_rows(&self.gates, g, h, 0..n, out, &gpu.stream)
    }

    /// Adds layer `l`'s routed experts for the `n` tokens whose feed-forward
    /// input is `h`, scored into `work.gates`, to the shared expert's output
    /// in `y`, after scaling it by its gate.
    #[allow(clippy::too_many_arguments)]
    pub fn mix(
        &self,
        l: usize,
        gpu: &Gpu,
        h: &DeviceBuffer<f32>,
        y: &mut DeviceBuffer<f32>,
        work: &mut ExpertWork,
        off: &mut Offload,
        n: usize,
    ) -> kinetic_cuda::Result<()> {
        if off.is_resident() {
            return self.mix_resident(l, gpu, h, y, work, off, n);
        }
        let (k, stream) = (&gpu.kernels, &gpu.stream);
        let moe = &off.moes[l];
        let (d, n_exp, picks_per) = (moe.router.cols, self.n_experts, moe.n_used);
        let gating = moe.gating.clone();
        let g = self.gates.rows();
        k.quantize_q8k(h, n, d, &mut work.hq, &mut work.hd, stream)?;
        // SAFETY: the host reads the buffer only after the synchronization
        // below.
        unsafe {
            work.down.download(0, &work.gates, 0..n * g, stream)?;
            work.down.download(n * g, h, 0..n * d, stream)?;
        }
        stream.synchronize()?;
        let down = work.down.as_slice();
        let (gates, h) = (down[..n * g].to_vec(), down[n * g..n * g + n * d].to_vec());

        let picks: Vec<Pick> = gates
            .chunks_exact(g)
            .flat_map(|row| gating.pick(&mut row[..n_exp].to_vec(), picks_per))
            .collect();
        let place = off.route(l, &picks, gpu)?;
        let assigned = work.assign(&picks, &place, stream)?;
        // Cached groups come first, then transit groups.
        let parts = [
            (off.arena(l), 0, assigned.cached),
            (off.transit_arena(), assigned.cached, assigned.transit),
        ];
        self.queue_device(l, gpu, work, off, assigned.device, &parts)?;

        let predicted = if self.predicts {
            predict(&gates, &gating, n_exp, picks_per, g)
        } else {
            Vec::new()
        };
        let prefetch = off.admit_predicted(l + 1, &predicted)?;
        let (lens, outputs) = off.stage_and_run(l, &prefetch, &h, &assigned.host);
        off.queue_prefetch(l + 1, &prefetch, &lens)?;
        if !assigned.host.is_empty() {
            let len = outputs.len();
            work.host_out.as_mut_slice()[..len].copy_from_slice(&outputs);
            // SAFETY: the region is rewritten only after the next layer's
            // synchronization of this stream.
            unsafe {
                work.host_out
                    .upload(0..len, &mut work.out, assigned.device * d, stream)?
            };
        }
        // SAFETY: every row index points at a device or host output written
        // above, inside the room for a full batch of assignments.
        unsafe { self.combine(gpu, work, y, n, d, picks_per) }
    }

    /// [`CudaExperts::mix`] with every expert on the device: the routing,
    /// the grouping of picks by expert and the products all queued on the
    /// stream, with nothing read back, so a step can be recorded in a graph.
    #[allow(clippy::too_many_arguments)]
    fn mix_resident(
        &self,
        l: usize,
        gpu: &Gpu,
        h: &DeviceBuffer<f32>,
        y: &mut DeviceBuffer<f32>,
        work: &mut ExpertWork,
        off: &mut Offload,
        n: usize,
    ) -> kinetic_cuda::Result<()> {
        let (k, stream) = (&gpu.kernels, &gpu.stream);
        let moe = &off.moes[l];
        let (d, picks_per) = (moe.router.cols, moe.n_used);
        let a = n * picks_per;
        k.quantize_q8k(h, n, d, &mut work.hq, &mut work.hd, stream)?;
        let routing = Routing {
            gates: &work.gates,
            tokens: n,
            n_exp: self.n_experts,
            picks: picks_per,
            stride: self.gates.rows(),
            sigmoid: matches!(moe.gating, Gating::Sigmoid { .. }),
            bias: self.bias.as_ref(),
        };
        k.moe_route(&routing, &mut work.experts, &mut work.weights, stream)?;
        let slots = &off.resident.as_ref().expect("resident experts")[l];
        k.moe_assign(
            &work.experts,
            a,
            picks_per,
            slots,
            &mut work.groups,
            a,
            &mut work.inputs,
            &mut work.rows,
            stream,
        )?;
        self.queue_device(l, gpu, work, off, a, &[(off.arena(l), 0, a)])?;
        if l == 0 {
            off.stats.tokens += n as u64;
        }
        off.stats.picks += a as u64;
        off.stats.hits += a as u64;
        // SAFETY: the assignment gave every pick a row of the products.
        unsafe { self.combine(gpu, work, y, n, d, picks_per) }
    }

    /// Queues `y` = the shared expert's output in `y`, scaled by its gate,
    /// plus every token's picks, weighted, from the rows `work` names.
    ///
    /// # Safety
    ///
    /// Every row `work.rows` names must hold its pick's output.
    unsafe fn combine(
        &self,
        gpu: &Gpu,
        work: &ExpertWork,
        y: &mut DeviceBuffer<f32>,
        n: usize,
        d: usize,
        picks_per: usize,
    ) -> kinetic_cuda::Result<()> {
        let g = self.gates.rows();
        let mix = ExpertMix {
            experts: &work.out,
            rows: &work.rows,
            weights: &work.weights,
            picks: picks_per,
            shared: self.has_shared,
            gates: self.has_shared_gate.then_some(GateLogits {
                values: &work.gates,
                first: g - 1,
                stride: g,
            }),
            tokens: n,
            d,
        };
        // SAFETY: the caller vouches for the rows.
        unsafe { gpu.kernels.moe_combine(&mix, y, &gpu.stream) }
    }

    /// Queues the device's `assignments`: gate and up products, their
    /// activation quantized again, and the down products into `work.out`,
    /// each part's groups, from its first, reading that part's arena.
    fn queue_device(
        &self,
        l: usize,
        gpu: &Gpu,
        work: &mut ExpertWork,
        off: &Offload,
        assignments: usize,
        parts: &[(ExpertArena, usize, usize)],
    ) -> kinetic_cuda::Result<()> {
        if assignments == 0 {
            return Ok(());
        }
        let (k, stream) = (&gpu.kernels, &gpu.stream);
        let moe = &off.moes[l];
        let layout = off.layouts[l];
        let product = |first_group, n_groups, gated: bool| ExpertProduct {
            ty: if gated { moe.gate.ty } else { moe.down.ty },
            groups: &work.groups,
            first_group,
            n_groups,
            assignments,
            inputs: gated.then_some(&work.inputs),
            first: if gated { 0 } else { layout.gate + layout.up },
            second: gated.then_some(layout.gate),
            rows: if gated { moe.gate.rows } else { moe.down.rows },
            cols: if gated { moe.gate.cols } else { moe.down.cols },
        };
        let hq = Q8kRows {
            qs: &work.hq,
            ds: &work.hd,
        };
        for &(arena, first, n) in parts {
            let p = product(first, n, true);
            // SAFETY: every group's slot, of this layer's pool or of the
            // transit slots, holds, or is queued earlier on this stream to
            // receive, this layer's expert in `layout`; inputs are tokens
            // of the batch.
            unsafe { k.moe_product(&p, arena, &off.tables, &hq, &mut work.act, stream)? };
        }
        k.quantize_q8k(
            &work.act,
            assignments,
            moe.down.cols,
            &mut work.actq,
            &mut work.actd,
            stream,
        )?;
        let act = Q8kRows {
            qs: &work.actq,
            ds: &work.actd,
        };
        for &(arena, first, n) in parts {
            let p = product(first, n, false);
            // SAFETY: as above; assignment `a` reads activation row `a`.
            unsafe { k.moe_product(&p, arena, &off.tables, &act, &mut work.out, stream)? };
        }
        Ok(())
    }
}

/// The distinct experts the next layer's router picks for any token, from
/// the scores after this layer's own in each row of `gates`; a guess, so
/// this layer's gating stands in for the next one's.
fn predict(gates: &[f32], gating: &Gating, n_exp: usize, k: usize, g: usize) -> Vec<u32> {
    let mut experts: Vec<u32> = gates
        .chunks_exact(g)
        .flat_map(|row| gating.pick(&mut row[n_exp..2 * n_exp].to_vec(), k))
        .map(|p| p.expert)
        .collect();
    experts.sort_unstable();
    experts.dedup();
    experts
}

fn check_types(m: &Moe) -> Result<(), LoadError> {
    let ok = [m.gate.ty, m.down.ty]
        .iter()
        .all(|t| EXPERT_TYPES.contains(t))
        && m.gate.ty == m.up.ty;
    if ok {
        Ok(())
    } else {
        Err(LoadError(format!(
            "experts of types {}/{}/{} are not supported on CUDA yet",
            m.gate.ty, m.up.ty, m.down.ty
        )))
    }
}
