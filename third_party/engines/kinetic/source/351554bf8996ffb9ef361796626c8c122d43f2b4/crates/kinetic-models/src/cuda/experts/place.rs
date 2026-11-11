//! Where each picked expert runs, the copies that bring experts into the
//! device cache, and the copies ahead of the next layer.

use std::time::Instant;

use kinetic_cpu::pool;

use super::offload::{stage, Offload, DEMAND_STAGING, PREFETCH_STAGING, TRANSIT_SLOTS};
use super::Gpu;
use crate::blocks::{Job, Pick};

/// Where an expert of the current layer runs.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(super) enum Place {
    Unused,
    /// In this slot of the cache.
    Device(u32),
    /// In this transit slot, for this batch only.
    Transit(u32),
    Host,
}

impl Offload<'_> {
    /// Places every expert of layer `l` that `picks` use: in its cache slot,
    /// on the host, or, when that finishes sooner, copied into a cache slot
    /// it may take or else into a transit slot.
    /// Counts the picks. The copies are queued on the main stream.
    pub(super) fn route(
        &mut self,
        l: usize,
        picks: &[Pick],
        gpu: &Gpu,
    ) -> kinetic_cuda::Result<Vec<Place>> {
        let n_exp = self.n_experts();
        self.cache.release();
        let mut tokens_of = vec![0usize; n_exp];
        for p in picks {
            tokens_of[p.expert as usize] += 1;
        }
        let used: Vec<usize> = (0..n_exp).filter(|&e| tokens_of[e] > 0).collect();
        // Use counts once per batch, so a long prompt does not outweigh the
        // tokens generated after it.
        for &e in &used {
            self.usage[l * n_exp + e] += 1;
        }
        if l == 0 {
            self.stats.tokens += (picks.len() / self.moes[0].n_used) as u64;
        }
        self.stats.picks += picks.len() as u64;
        self.stats.used += used.len() as u64;
        self.stats.predicted_used += used
            .iter()
            .filter(|&&e| self.predicted.contains(&(e as u32)))
            .count() as u64;

        let waiting = used.iter().any(|&e| {
            self.cache
                .slot(l, e)
                .is_some_and(|slot| self.cache.is_pending(l, slot))
        });
        if waiting {
            self.copied.synchronize()?;
            self.cache.settle();
        }
        let mut place = vec![Place::Unused; n_exp];
        let mut cold = Vec::new();
        for &e in &used {
            match self.cache.lookup(l, e) {
                Some(slot) => {
                    self.cache.protect(l, slot);
                    place[e] = Place::Device(slot);
                }
                None => cold.push(e),
            }
        }
        cold.sort_by_key(|&e| std::cmp::Reverse(tokens_of[e]));

        let bytes = self.layouts[l].bytes();
        let usage = &self.usage;
        let uses = |layer: usize, e: usize| usage[layer * n_exp + e];
        let (mut host_time, mut copy_time) = (0.0, 0.0);
        let mut loads = Vec::new();
        let mut transit = 0;
        for e in cold {
            let host = self.costs.host(bytes, tokens_of[e]);
            let copy = self.costs.copy(bytes);
            let target = if copy_time + copy >= host_time + host {
                Place::Host
            } else if let Some(slot) = self.cache.admit(l, e, uses, uses(l, e), false) {
                self.cache.protect(l, slot);
                Place::Device(slot)
            } else if transit < TRANSIT_SLOTS {
                transit += 1;
                Place::Transit(transit as u32 - 1)
            } else {
                Place::Host
            };
            place[e] = target;
            match target {
                Place::Host => host_time += host,
                _ => {
                    loads.push((e, target));
                    copy_time += copy;
                }
            }
        }
        self.expected_host = host_time;
        self.stats.hits += picks
            .iter()
            .filter(|p| matches!(place[p.expert as usize], Place::Device(_)))
            .count() as u64;
        let host_experts = place.iter().filter(|p| **p == Place::Host).count();
        self.stats.host_experts += host_experts as u64;
        self.stats.host_bytes += (host_experts * bytes) as u64;
        self.stats.loaded += loads.len() as u64;
        self.stats.loaded_bytes += (loads.len() * bytes) as u64;
        self.load(l, &loads, gpu)?;
        Ok(place)
    }

    /// Copies `loads`, experts of layer `l` and their cache or transit
    /// slots, on the main stream, staging a round of them at a time in
    /// parallel.
    pub(super) fn load(
        &mut self,
        l: usize,
        loads: &[(usize, Place)],
        gpu: &Gpu,
    ) -> kinetic_cuda::Result<()> {
        let region = self.staging.region;
        let half = DEMAND_STAGING / 2;
        let pool = self.cache.pool_of(l);
        let slot_bytes = self.plan.pools[pool].slot_bytes;
        // Rounds alternate between the two halves of the staging, so one
        // half is filled while the other's copies run.
        for (round, batch) in loads.chunks(half).enumerate() {
            let side = round % 2;
            if round >= 2 {
                self.staged[side].synchronize()?;
            }
            let moe = &self.moes[l];
            let staging = &mut self.staging.demand.as_mut_slice()[side * half * region..];
            pool::for_each_chunk(&mut staging[..batch.len() * region], region, |i, dst| {
                stage(moe, batch[i].0, dst);
            });
            let len = self.layouts[l].bytes();
            for (i, &(_, target)) in batch.iter().enumerate() {
                let at = (side * half + i) * region;
                let (dst, start) = match target {
                    Place::Device(slot) => (&mut self.arenas[pool], slot as usize * slot_bytes),
                    Place::Transit(slot) => (&mut self.transit, slot as usize * region),
                    Place::Unused | Place::Host => unreachable!("loads go to the device"),
                };
                // SAFETY: this half of the staging is rewritten only after
                // its event, recorded below, or a synchronization of this
                // stream.
                unsafe {
                    self.staging
                        .demand
                        .upload(at..at + len, dst, start, &gpu.stream)?
                };
            }
            self.staged[side].record(&gpu.stream)?;
        }
        Ok(())
    }

    /// Slots for the experts `predicted` for layer `l` that the cache lacks,
    /// as far as staging allows and as long as each evicts only experts
    /// used less often. The slots are marked as awaiting their copy.
    pub fn admit_predicted(
        &mut self,
        l: usize,
        predicted: &[u32],
    ) -> kinetic_cuda::Result<Vec<(usize, u32)>> {
        self.predicted = predicted.to_vec();
        self.stats.predicted += predicted.len() as u64;
        let missing: Vec<usize> = predicted
            .iter()
            .map(|&e| e as usize)
            .filter(|&e| self.cache.slot(l, e).is_none())
            .take(PREFETCH_STAGING)
            .collect();
        if missing.is_empty() {
            return Ok(Vec::new());
        }
        self.copied.synchronize()?;
        self.cache.settle();
        let n_exp = self.n_experts();
        let usage = &self.usage;
        let uses = |layer: usize, e: usize| usage[layer * n_exp + e];
        Ok(missing
            .into_iter()
            .filter_map(|e| {
                let slot = self.cache.admit(l, e, uses, uses(l, e) + 1, true)?;
                Some((e, slot))
            })
            .collect())
    }

    /// Runs `jobs` of layer `l` on `h` on the host, timing them, then stages
    /// the `prefetch` experts of layer `l + 1`. Returns the staged lengths and
    /// the host's outputs, one row per job.
    pub fn stage_and_run(
        &mut self,
        l: usize,
        prefetch: &[(usize, u32)],
        h: &[f32],
        jobs: &[Job],
    ) -> (Vec<usize>, Vec<f32>) {
        let region = self.staging.region;
        let staging = self.staging.prefetch.as_mut_slice();
        let moes = &self.moes;
        let start = Instant::now();
        let outputs = if jobs.is_empty() {
            Vec::new()
        } else {
            moes[l].run_experts(h, jobs)
        };
        self.costs
            .observe_host(self.expected_host, start.elapsed().as_secs_f64());
        let lens = prefetch
            .iter()
            .enumerate()
            .map(|(i, &(e, _))| stage(&moes[l + 1], e, &mut staging[i * region..]))
            .collect();
        (lens, outputs)
    }

    /// Queues the copies of the `prefetch` experts of layer `l`, `lens[i]`
    /// bytes staged in region `i`, on the second stream.
    pub fn queue_prefetch(
        &mut self,
        l: usize,
        prefetch: &[(usize, u32)],
        lens: &[usize],
    ) -> kinetic_cuda::Result<()> {
        if prefetch.is_empty() {
            return Ok(());
        }
        let region = self.staging.region;
        let pool = self.cache.pool_of(l);
        let slot_bytes = self.plan.pools[pool].slot_bytes;
        for (i, (&(_, slot), &len)) in prefetch.iter().zip(lens).enumerate() {
            let start = i * region;
            // SAFETY: this staging region is rewritten only after `copied`
            // has been synchronized again.
            unsafe {
                self.staging.prefetch.upload(
                    start..start + len,
                    &mut self.arenas[pool],
                    slot as usize * slot_bytes,
                    &self.copies,
                )?
            };
            self.stats.prefetched += 1;
            self.stats.prefetched_bytes += len as u64;
        }
        self.copied.record(&self.copies)
    }
}
