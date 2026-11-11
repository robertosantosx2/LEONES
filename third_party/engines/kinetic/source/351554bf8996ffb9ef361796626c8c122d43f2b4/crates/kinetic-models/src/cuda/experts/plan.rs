//! Where each part of a mixture-of-experts model lives: everything but the
//! routed experts on the device, then as many experts as the device has
//! room for in a cache, the rest in host memory or, beyond it, on disk.

use std::fmt;

use super::cache::SlotLayout;

/// Device memory kept free for the driver and for buffers made later.
pub const DEVICE_RESERVE: usize = 384 << 20;

/// The placement chosen at load time.
#[derive(Clone, Debug)]
pub struct Plan {
    /// Device bytes of the dense weights, head and caches of one sequence.
    pub dense_bytes: usize,
    /// Bytes of every routed expert of the model.
    pub expert_bytes: usize,
    /// Per slot size: bytes per slot, slots and the layers using them.
    pub pools: Vec<PoolPlan>,
    /// Pinned host bytes used to stage copies to the device.
    pub staging_bytes: usize,
    /// Measured bytes per second of expert weights the host runs through
    /// for one token, and copies to the device.
    pub host_rate: f64,
    pub copy_rate: f64,
}

#[derive(Clone, Debug)]
pub struct PoolPlan {
    pub slot_bytes: usize,
    pub slots: usize,
    pub layers: usize,
}

impl Plan {
    /// Device bytes the expert cache holds.
    pub fn cache_bytes(&self) -> usize {
        self.pools.iter().map(|p| p.slot_bytes * p.slots).sum()
    }

    /// Fraction of all routed experts the device caches.
    pub fn cached_share(&self) -> f64 {
        self.cache_bytes() as f64 / self.expert_bytes.max(1) as f64
    }
}

impl fmt::Display for Plan {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        const MIB: f64 = (1 << 20) as f64;
        write!(
            f,
            "device: {:.0} MiB dense, {:.0} MiB expert cache ({:.0}% of {:.0} MiB of experts in",
            self.dense_bytes as f64 / MIB,
            self.cache_bytes() as f64 / MIB,
            100.0 * self.cached_share(),
            self.expert_bytes as f64 / MIB,
        )?;
        for p in &self.pools {
            write!(
                f,
                " {} slots of {:.2} MiB for {} layers;",
                p.slots,
                p.slot_bytes as f64 / MIB,
                p.layers
            )?;
        }
        write!(
            f,
            "); host: {:.0} MiB pinned staging, the rest mapped from the file; host experts at {:.1} GB/s, copies at {:.1} GB/s",
            self.staging_bytes as f64 / MIB,
            self.host_rate / 1e9,
            self.copy_rate / 1e9,
        )
    }
}

/// Groups layers by slot size and shares `budget` device bytes among the
/// groups in proportion to the bytes of their experts, so every layer can
/// cache about the same fraction of its experts. Returns the slot sizes,
/// the slots of each and the group of every layer.
pub fn share_cache(
    layouts: &[SlotLayout],
    n_experts: usize,
    budget: usize,
) -> (Vec<PoolPlan>, Vec<usize>) {
    let mut sizes: Vec<usize> = layouts.iter().map(SlotLayout::bytes).collect();
    sizes.sort_unstable();
    sizes.dedup();
    let pool_of: Vec<usize> = layouts
        .iter()
        .map(|l| sizes.binary_search(&l.bytes()).expect("size is listed"))
        .collect();
    let total: usize = layouts.iter().map(|l| l.bytes() * n_experts).sum();
    let pools = sizes
        .iter()
        .enumerate()
        .map(|(p, &slot_bytes)| {
            let layers = pool_of.iter().filter(|&&q| q == p).count();
            let bytes = slot_bytes * n_experts * layers;
            let share = (budget as f64 * bytes as f64 / total.max(1) as f64) as usize;
            PoolPlan {
                slot_bytes,
                slots: (share / slot_bytes).min(n_experts * layers),
                layers,
            }
        })
        .collect();
    (pools, pool_of)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn layers_share_the_budget_by_expert_bytes() {
        let small = SlotLayout {
            gate: 100,
            up: 100,
            down: 100,
        };
        let large = SlotLayout {
            gate: 200,
            up: 200,
            down: 200,
        };
        let (pools, pool_of) = share_cache(&[small, large, small], 10, 6000);
        assert_eq!(pool_of, [0, 1, 0]);
        // 6000 + 6000 bytes of experts per group: 3000 bytes each.
        assert_eq!((pools[0].slots, pools[0].layers), (10, 2));
        assert_eq!((pools[1].slots, pools[1].layers), (5, 1));
        let (pools, _) = share_cache(&[small], 10, 1 << 30);
        assert_eq!(pools[0].slots, 10);
    }
}
