//! Which experts the device holds: per slot size a pool of slots, each
//! holding one expert's matrices, refilled least-frequently-used first.

/// Where one layer's expert matrices sit inside a slot.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct SlotLayout {
    pub gate: usize,
    pub up: usize,
    pub down: usize,
}

impl SlotLayout {
    pub fn bytes(&self) -> usize {
        self.gate + self.up + self.down
    }
}

/// The bookkeeping of one pool's slots.
struct Pool {
    /// The (layer, expert) each slot holds.
    holder: Vec<Option<(usize, usize)>>,
    /// When each slot was last used, to break frequency ties.
    last_use: Vec<u64>,
    /// Slots whose copy has been queued on the prefetch stream.
    pending: Vec<bool>,
    /// Slots the work in flight reads, which must keep their contents.
    protected: Vec<bool>,
}

pub(super) struct ExpertCache {
    pools: Vec<Pool>,
    /// The pool of each layer.
    pool_of: Vec<usize>,
    /// The slot of each expert of each layer, if cached.
    slot_of: Vec<Vec<Option<u32>>>,
    clock: u64,
}

impl ExpertCache {
    /// Pools of `slots[p]` slots; layer `l` uses pool `pool_of[l]` and has
    /// `n_experts` experts.
    pub fn new(slots: &[usize], pool_of: Vec<usize>, n_experts: usize) -> ExpertCache {
        let pools = slots
            .iter()
            .map(|&n| Pool {
                holder: vec![None; n],
                last_use: vec![0; n],
                pending: vec![false; n],
                protected: vec![false; n],
            })
            .collect();
        ExpertCache {
            slot_of: vec![vec![None; n_experts]; pool_of.len()],
            pools,
            pool_of,
            clock: 0,
        }
    }

    pub fn pool_of(&self, layer: usize) -> usize {
        self.pool_of[layer]
    }

    fn pool_mut(&mut self, layer: usize) -> &mut Pool {
        &mut self.pools[self.pool_of[layer]]
    }

    fn tick(&mut self) -> u64 {
        self.clock += 1;
        self.clock
    }

    /// The slot holding expert `e` of `layer`, marked as used now.
    pub fn lookup(&mut self, layer: usize, e: usize) -> Option<u32> {
        let slot = self.slot_of[layer][e]?;
        let now = self.tick();
        self.pool_mut(layer).last_use[slot as usize] = now;
        Some(slot)
    }

    /// The slot holding expert `e` of `layer`, without marking it used.
    pub fn slot(&self, layer: usize, e: usize) -> Option<u32> {
        self.slot_of[layer][e]
    }

    pub fn is_pending(&self, layer: usize, slot: u32) -> bool {
        self.pools[self.pool_of[layer]].pending[slot as usize]
    }

    /// Marks every pending copy as done.
    pub fn settle(&mut self) {
        self.pools.iter_mut().for_each(|p| p.pending.fill(false));
    }

    /// Keeps `slot` of `layer`'s pool until [`ExpertCache::release`].
    pub fn protect(&mut self, layer: usize, slot: u32) {
        self.pool_mut(layer).protected[slot as usize] = true;
    }

    pub fn release(&mut self) {
        self.pools.iter_mut().for_each(|p| p.protected.fill(false));
    }

    /// A slot of `layer`'s pool for expert `e`: a free one, or the one whose
    /// holder has the fewest `uses` (the least recently used among equals),
    /// as long as those uses are below `limit`. Protected slots and pending
    /// copies are never taken. The slot is given to `e` and, with
    /// `pending`, marked as awaiting a copy.
    pub fn admit(
        &mut self,
        layer: usize,
        e: usize,
        uses: impl Fn(usize, usize) -> u32,
        limit: u32,
        pending: bool,
    ) -> Option<u32> {
        let pool = &self.pools[self.pool_of[layer]];
        let rank = |s: usize| match pool.holder[s] {
            None => (0, 0),
            Some((l, x)) => (uses(l, x).saturating_add(1), pool.last_use[s]),
        };
        let victim = (0..pool.holder.len())
            .filter(|&s| !pool.pending[s] && !pool.protected[s])
            .min_by_key(|&s| rank(s))?;
        if rank(victim).0 > limit {
            return None;
        }
        if let Some((l, x)) = pool.holder[victim] {
            self.slot_of[l][x] = None;
        }
        let now = self.tick();
        let pool = self.pool_mut(layer);
        pool.holder[victim] = Some((layer, e));
        pool.last_use[victim] = now;
        pool.pending[victim] = pending;
        self.slot_of[layer][e] = Some(victim as u32);
        Some(victim as u32)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn evicts_the_least_frequently_used() {
        let mut cache = ExpertCache::new(&[2], vec![0, 0], 4);
        let uses = |l: usize, e: usize| [[5, 1, 0, 0], [0, 0, 0, 0]][l][e];
        assert_eq!(cache.admit(0, 0, uses, u32::MAX, false), Some(0));
        assert_eq!(cache.admit(0, 1, uses, u32::MAX, false), Some(1));
        // Expert 1 has fewer uses than expert 0, so it goes first, but only
        // for a newcomer used at least as often.
        assert_eq!(cache.admit(1, 2, uses, 1, false), None);
        assert_eq!(cache.admit(1, 2, uses, 2, false), Some(1));
        assert_eq!(cache.slot(0, 1), None);
        assert_eq!(cache.lookup(1, 2), Some(1));
    }

    #[test]
    fn protected_and_pending_slots_stay() {
        let mut cache = ExpertCache::new(&[2], vec![0], 4);
        let none = |_: usize, _: usize| 0;
        let a = cache.admit(0, 0, none, u32::MAX, true).unwrap();
        let b = cache.admit(0, 1, none, u32::MAX, false).unwrap();
        cache.protect(0, b);
        assert_eq!(cache.admit(0, 2, none, u32::MAX, false), None);
        cache.release();
        cache.settle();
        assert!(!cache.is_pending(0, a));
        assert_eq!(cache.admit(0, 2, none, u32::MAX, false), Some(a));
    }
}
