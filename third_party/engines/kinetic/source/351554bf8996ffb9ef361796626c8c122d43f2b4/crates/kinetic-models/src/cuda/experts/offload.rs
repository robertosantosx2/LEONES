use std::time::Instant;

use kinetic_cuda::{DeviceBuffer, Event, ExpertArena, ExpertTables, PinnedBuffer, Stream};

use super::cache::{ExpertCache, SlotLayout};
use super::place::Place;
use super::plan::{self, Plan};
use super::stats::Stats;
use super::Gpu;
use crate::blocks::{Job, Moe};
use crate::LoadError;

/// Experts staged for copies a layer waits for, and for copies ahead of the
/// next layer.
pub(super) const DEMAND_STAGING: usize = 48;
pub(super) const PREFETCH_STAGING: usize = 16;

/// Device slots for experts a batch copies over without caching them, when
/// the cache keeps experts used more often.
pub(super) const TRANSIT_SLOTS: usize = 128;

/// Seconds per byte of expert weights for the host to run an expert, and to
/// copy one to the device, measured at load time, and how much slower the
/// host has lately been than that.
#[derive(Clone, Copy, Debug, Default)]
pub(super) struct Costs {
    host: f64,
    host_per_token: f64,
    copy: f64,
    /// Other programs taking the processor make the host slower than it
    /// measured, and the few experts of one token run slower than the
    /// many it measured; the device then takes more of them.
    slowdown: f64,
}

/// Weight of the latest layer in [`Costs::slowdown`].
const SLOWDOWN_WEIGHT: f64 = 0.3;

/// How far a layer whose experts all ran on the device moves the slowdown
/// back towards 1, so that the host is tried again.
const SLOWDOWN_RELAX: f64 = 0.02;

impl Costs {
    pub fn host(&self, bytes: usize, tokens: usize) -> f64 {
        self.slowdown * self.measured_host(bytes, tokens)
    }

    fn measured_host(&self, bytes: usize, tokens: usize) -> f64 {
        bytes as f64 * (self.host + (tokens - 1) as f64 * self.host_per_token)
    }

    pub fn copy(&self, bytes: usize) -> f64 {
        bytes as f64 * self.copy
    }

    /// Folds in that the host took `seconds` for work that [`Costs::host`]
    /// put at `expected`, or, with no work, relaxes the slowdown.
    pub fn observe_host(&mut self, expected: f64, seconds: f64) {
        self.slowdown = if expected > 0.0 {
            let sample = seconds * self.slowdown / expected;
            (1.0 - SLOWDOWN_WEIGHT) * self.slowdown + SLOWDOWN_WEIGHT * sample
        } else {
            self.slowdown - SLOWDOWN_RELAX * (self.slowdown - 1.0)
        };
        self.slowdown = self.slowdown.clamp(0.5, 100.0);
    }
}

/// Page-locked host memory that copies to the device go through, one region
/// per expert.
pub(super) struct Staging {
    pub demand: PinnedBuffer<u8>,
    pub prefetch: PinnedBuffer<u8>,
    pub region: usize,
}

/// The routed experts of a model, the device cache of them and what is
/// known about their use, shared by every state.
pub(in crate::cuda) struct Offload<'m> {
    pub moes: Vec<Moe<'m>>,
    pub(super) layouts: Vec<SlotLayout>,
    pub(super) tables: ExpertTables,
    pub(super) arenas: Vec<DeviceBuffer<u8>>,
    /// [`TRANSIT_SLOTS`] slots of the staging region's size.
    pub(super) transit: DeviceBuffer<u8>,
    pub(super) cache: ExpertCache,
    pub(super) staging: Staging,
    pub(super) costs: Costs,
    /// What [`Costs::host`] put the host's share of the layer being run at.
    pub(super) expected_host: f64,
    pub plan: Plan,
    pub stats: Stats,
    /// Per layer and expert, how many batches picked it.
    pub(super) usage: Vec<u32>,
    /// The experts predicted for the layer about to run.
    pub(super) predicted: Vec<u32>,
    /// The stream copies ahead of a layer go on, and the event recorded
    /// after the latest of them.
    pub(super) copies: Stream,
    pub(super) copied: Event,
    /// Recorded after the copies out of each half of the demand staging.
    pub(super) staged: [Event; 2],
    /// When the cache holds every expert, each layer's slot per expert, and
    /// routing stays on the device.
    pub(super) resident: Option<Vec<DeviceBuffer<u32>>>,
}

impl<'m> Offload<'m> {
    /// Plans the cache for `moes` in at most `budget` device bytes, besides
    /// `dense_bytes` already taken.
    pub fn new(
        gpu: &Gpu,
        moes: Vec<Moe<'m>>,
        budget: usize,
        dense_bytes: usize,
    ) -> Result<Offload<'m>, LoadError> {
        let err = super::cuda_error;
        let layouts: Vec<SlotLayout> = moes
            .iter()
            .map(|m| SlotLayout {
                gate: m.gate.expert_bytes(),
                up: m.up.expert_bytes(),
                down: m.down.expert_bytes(),
            })
            .collect();
        let n_experts = moes[0].n_experts();
        let region = layouts.iter().map(SlotLayout::bytes).max().unwrap_or(0);
        let staging = Staging {
            demand: PinnedBuffer::new(&gpu.ctx, DEMAND_STAGING * region).map_err(err)?,
            prefetch: PinnedBuffer::new(&gpu.ctx, PREFETCH_STAGING * region).map_err(err)?,
            region,
        };
        let transit = DeviceBuffer::<u8>::new(&gpu.ctx, TRANSIT_SLOTS * region).map_err(err)?;
        let budget = budget.saturating_sub(transit.len());
        let (pools, pool_of) = plan::share_cache(&layouts, n_experts, budget);
        let arenas = pools
            .iter()
            .map(|p| DeviceBuffer::<u8>::new(&gpu.ctx, (p.slots * p.slot_bytes).max(1)))
            .collect::<kinetic_cuda::Result<Vec<_>>>()
            .map_err(err)?;
        let slots: Vec<usize> = pools.iter().map(|p| p.slots).collect();
        let plan = Plan {
            dense_bytes,
            expert_bytes: layouts.iter().map(|l| l.bytes() * n_experts).sum(),
            pools,
            staging_bytes: staging.demand.len() + staging.prefetch.len(),
            host_rate: 0.0,
            copy_rate: 0.0,
        };
        let mut off = Offload {
            usage: vec![0; moes.len() * n_experts],
            cache: ExpertCache::new(&slots, pool_of, n_experts),
            moes,
            layouts,
            tables: ExpertTables::new(&gpu.ctx).map_err(err)?,
            arenas,
            transit,
            staging,
            costs: Costs::default(),
            expected_host: 0.0,
            plan,
            stats: Stats::default(),
            predicted: Vec::new(),
            copies: Stream::new(&gpu.ctx).map_err(err)?,
            copied: Event::new(&gpu.ctx).map_err(err)?,
            staged: [
                Event::new(&gpu.ctx).map_err(err)?,
                Event::new(&gpu.ctx).map_err(err)?,
            ],
            resident: None,
        };
        off.costs = off.measure_costs(gpu).map_err(err)?;
        off.plan.host_rate = 1.0 / off.costs.host;
        off.plan.copy_rate = 1.0 / off.costs.copy;
        let everything = off
            .plan
            .pools
            .iter()
            .all(|p| p.slots == p.layers * n_experts);
        if everything {
            off.resident = Some(off.load_all(gpu).map_err(err)?);
        }
        Ok(off)
    }

    /// Whether every expert lives on the device, so routing needs no host.
    pub fn is_resident(&self) -> bool {
        self.resident.is_some()
    }

    /// Copies every expert into a slot of its own and returns each layer's
    /// slots by expert.
    fn load_all(&mut self, gpu: &Gpu) -> kinetic_cuda::Result<Vec<DeviceBuffer<u32>>> {
        let n_exp = self.n_experts();
        let mut tables = Vec::with_capacity(self.moes.len());
        for l in 0..self.moes.len() {
            let none = |_: usize, _: usize| 0;
            let loads: Vec<(usize, Place)> = (0..n_exp)
                .map(|e| {
                    let slot = self.cache.admit(l, e, none, 0, false);
                    (e, Place::Device(slot.expect("a slot for every expert")))
                })
                .collect();
            self.load(l, &loads, gpu)?;
            let slots: Vec<u32> = loads
                .iter()
                .map(|&(_, p)| match p {
                    Place::Device(slot) => slot,
                    _ => unreachable!("every expert has a slot"),
                })
                .collect();
            tables.push(DeviceBuffer::from_slice(&gpu.ctx, &slots)?);
        }
        gpu.stream.synchronize()?;
        Ok(tables)
    }

    pub fn n_experts(&self) -> usize {
        self.moes[0].n_experts()
    }

    pub fn arena(&self, layer: usize) -> ExpertArena<'_> {
        let pool = self.cache.pool_of(layer);
        ExpertArena {
            data: &self.arenas[pool],
            slot_bytes: self.plan.pools[pool].slot_bytes,
        }
    }

    pub fn transit_arena(&self) -> ExpertArena<'_> {
        ExpertArena {
            data: &self.transit,
            slot_bytes: self.staging.region,
        }
    }

    /// Times the host running experts and the copy of experts to the
    /// device, to choose between them per expert later.
    fn measure_costs(&mut self, gpu: &Gpu) -> kinetic_cuda::Result<Costs> {
        let moe = &self.moes[0];
        let bytes = self.layouts[0].bytes() as f64;
        let d = moe.router.cols;
        let experts = 8.min(moe.n_experts());
        let h: Vec<f32> = (0..experts * d)
            .map(|i| ((i % 7) as f32 - 3.0) * 0.1)
            .collect();
        let time_host = |tokens: usize| {
            let jobs: Vec<Job> = (0..experts)
                .flat_map(|e| {
                    (0..tokens).map(move |t| Job {
                        row: t as u32,
                        expert: e as u32,
                    })
                })
                .collect();
            let start = Instant::now();
            moe.run_experts(&h[..tokens * d], &jobs);
            start.elapsed().as_secs_f64() / (experts as f64 * bytes)
        };
        // The best of a few rounds, since other programs may be busy.
        let best = |time: &mut dyn FnMut() -> f64| (0..3).map(|_| time()).fold(f64::MAX, f64::min);
        let host = best(&mut || time_host(1));
        let many = best(&mut || time_host(experts));
        let host_per_token = ((many - host) / (experts - 1).max(1) as f64).max(0.0);

        let slots = self.plan.pools[self.cache.pool_of(0)]
            .slots
            .min(experts)
            .min(DEMAND_STAGING);
        let mut time_copy = || -> kinetic_cuda::Result<f64> {
            let start = Instant::now();
            let region = self.staging.region;
            let pool = self.cache.pool_of(0);
            let slot_bytes = self.plan.pools[pool].slot_bytes;
            for e in 0..slots {
                let at = e * region;
                let len = stage(
                    &self.moes[0],
                    e,
                    &mut self.staging.demand.as_mut_slice()[at..],
                );
                // SAFETY: the stream is synchronized before staging is reused.
                unsafe {
                    self.staging.demand.upload(
                        at..at + len,
                        &mut self.arenas[pool],
                        e * slot_bytes,
                        &gpu.stream,
                    )?
                };
            }
            gpu.stream.synchronize()?;
            Ok(start.elapsed().as_secs_f64() / (slots.max(1) as f64 * bytes))
        };
        let mut copy = f64::MAX;
        for _ in 0..3 {
            copy = copy.min(time_copy()?);
        }
        Ok(Costs {
            host,
            host_per_token,
            copy,
            slowdown: 1.0,
        })
    }
}

/// Copies expert `e`'s gate, up and down matrices from the file to the
/// start of `dst` and returns their length.
pub(super) fn stage(moe: &Moe, e: usize, dst: &mut [u8]) -> usize {
    let mut at = 0;
    for m in [moe.gate.expert(e), moe.up.expert(e), moe.down.expert(e)] {
        dst[at..at + m.data.len()].copy_from_slice(m.data);
        at += m.data.len();
    }
    at
}
