use kinetic_cuda::{
    DeviceBuffer, ExpertGroup, PinnedBuffer, Stream, EXPERT_GROUP, MAX_BATCH, Q8K_BLOCK,
};

use super::place::Place;
use super::Gpu;
use crate::blocks::{Job, Pick};

/// Sizes the expert buffers of a state are made for.
pub(in crate::cuda) struct ExpertDims {
    pub d: usize,
    /// Most tokens per batch.
    pub rows: usize,
    pub picks: usize,
    pub n_ff: usize,
    /// Most scores per token, see [`super::CudaExperts::score_rows`].
    pub scores: usize,
}

/// A state's buffers for running routed experts, on the device and pinned
/// on the host.
pub(in crate::cuda) struct ExpertWork {
    pub gates: DeviceBuffer<f32>,
    /// The scores of one batch of a pass.
    pub chunk_gates: DeviceBuffer<f32>,
    pub hq: DeviceBuffer<i8>,
    pub hd: DeviceBuffer<f32>,
    pub groups: DeviceBuffer<u32>,
    pub inputs: DeviceBuffer<u32>,
    pub act: DeviceBuffer<f32>,
    pub actq: DeviceBuffer<i8>,
    pub actd: DeviceBuffer<f32>,
    /// Device outputs, then host outputs, one row per assignment.
    pub out: DeviceBuffer<f32>,
    /// Per token and pick, its row of `out` and its weight.
    pub rows: DeviceBuffer<u32>,
    pub weights: DeviceBuffer<f32>,
    /// Per token and pick, its expert, when routing stays on the device.
    pub experts: DeviceBuffer<u32>,
    /// Scores, then the feed-forward input, read back each layer.
    pub down: PinnedBuffer<f32>,
    /// Groups, inputs and rows on their way to the device.
    route: PinnedBuffer<u32>,
    route_weights: PinnedBuffer<f32>,
    pub host_out: PinnedBuffer<f32>,
    picks: usize,
}

/// How a batch's picks were assigned: `device` assignments in `cached`
/// groups of cache slots then `transit` groups of transit slots, then the
/// host's jobs.
pub(super) struct Assigned {
    pub device: usize,
    pub cached: usize,
    pub transit: usize,
    pub host: Vec<Job>,
}

impl ExpertWork {
    pub fn new(gpu: &Gpu, dims: &ExpertDims) -> kinetic_cuda::Result<ExpertWork> {
        let ctx = &gpu.ctx;
        let ExpertDims {
            d,
            rows,
            picks,
            n_ff,
            scores,
        } = *dims;
        let assigned = rows * picks;
        let f32s = |len: usize| DeviceBuffer::<f32>::new(ctx, len.max(1));
        let u32s = |len: usize| DeviceBuffer::<u32>::new(ctx, len.max(1));
        let i8s = |len: usize| DeviceBuffer::<i8>::new(ctx, len.max(1));
        Ok(ExpertWork {
            gates: f32s(rows * scores)?,
            chunk_gates: f32s(MAX_BATCH * scores)?,
            hq: i8s(rows * d)?,
            hd: f32s(rows * d / Q8K_BLOCK)?,
            groups: u32s(4 * assigned)?,
            inputs: u32s(assigned)?,
            act: f32s(assigned * n_ff)?,
            actq: i8s(assigned * n_ff)?,
            actd: f32s(assigned * n_ff / Q8K_BLOCK)?,
            out: f32s(assigned * d)?,
            rows: u32s(assigned)?,
            weights: f32s(assigned)?,
            experts: u32s(assigned)?,
            down: PinnedBuffer::new(ctx, rows * (scores + d))?,
            route: PinnedBuffer::new(ctx, 6 * assigned)?,
            route_weights: PinnedBuffer::new(ctx, assigned)?,
            host_out: PinnedBuffer::new(ctx, assigned * d)?,
            picks,
        })
    }

    /// Device bytes held.
    pub fn size_bytes(&self) -> usize {
        let f32s = [
            &self.gates,
            &self.chunk_gates,
            &self.hd,
            &self.act,
            &self.actd,
            &self.out,
            &self.weights,
        ];
        let u32s = [&self.groups, &self.inputs, &self.rows, &self.experts];
        4 * f32s.iter().map(|b| b.len()).sum::<usize>()
            + 4 * u32s.iter().map(|b| b.len()).sum::<usize>()
            + self.hq.len()
            + self.actq.len()
    }

    /// Assigns every pick, [`ExpertWork::picks`] per token, to a device
    /// group or a host job as `place` says, and uploads the groups, inputs
    /// and per-pick rows and weights.
    pub(super) fn assign(
        &mut self,
        picks: &[Pick],
        place: &[Place],
        stream: &Stream,
    ) -> kinetic_cuda::Result<Assigned> {
        let k = self.picks;
        let mut cached: Vec<(u32, Vec<usize>)> = Vec::new();
        let mut transit: Vec<(u32, Vec<usize>)> = Vec::new();
        let mut host = Vec::new();
        for (s, p) in picks.iter().enumerate() {
            let (list, slot) = match place[p.expert as usize] {
                Place::Device(slot) => (&mut cached, slot),
                Place::Transit(slot) => (&mut transit, slot),
                Place::Host => {
                    host.push(s);
                    continue;
                }
                Place::Unused => unreachable!("a picked expert has a place"),
            };
            match list.iter_mut().find(|(x, _)| *x == slot) {
                Some((_, slots)) => slots.push(s),
                None => list.push((slot, vec![s])),
            }
        }
        let n_cached: usize = cached
            .iter()
            .map(|(_, s)| s.len().div_ceil(EXPERT_GROUP))
            .sum();
        let n = picks.len();
        let route = self.route.as_mut_slice();
        let (groups_at, inputs_at, rows_at) = (0, 4 * n, 5 * n);
        let mut groups = 0;
        let mut a = 0;
        for (slot, list) in cached.iter().chain(&transit) {
            for chunk in list.chunks(EXPERT_GROUP) {
                let group = ExpertGroup {
                    slot: *slot,
                    first: a as u32,
                    count: chunk.len() as u32,
                };
                route[groups_at + 4 * groups..][..4].copy_from_slice(&group.words());
                groups += 1;
                for &s in chunk {
                    route[inputs_at + a] = (s / k) as u32;
                    route[rows_at + s] = a as u32;
                    a += 1;
                }
            }
        }
        let device = a;
        let jobs: Vec<Job> = host
            .iter()
            .enumerate()
            .map(|(j, &s)| {
                route[rows_at + s] = (device + j) as u32;
                Job {
                    row: (s / k) as u32,
                    expert: picks[s].expert,
                }
            })
            .collect();
        let weights = self.route_weights.as_mut_slice();
        for (w, p) in weights.iter_mut().zip(picks) {
            *w = p.weight;
        }
        // SAFETY (each upload): the regions are rewritten only after the
        // next layer's synchronization of this stream.
        unsafe {
            self.route
                .upload(rows_at..rows_at + n, &mut self.rows, 0, stream)?;
            self.route_weights
                .upload(0..n, &mut self.weights, 0, stream)?;
            if device > 0 {
                self.route.upload(
                    groups_at..groups_at + 4 * groups,
                    &mut self.groups,
                    0,
                    stream,
                )?;
                self.route
                    .upload(inputs_at..inputs_at + device, &mut self.inputs, 0, stream)?;
            }
        }
        Ok(Assigned {
            device,
            cached: n_cached,
            transit: groups - n_cached,
            host: jobs,
        })
    }
}
