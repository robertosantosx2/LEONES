#!/usr/bin/env python3
"""Warm-start cache simulator over GLM routing traces (the second opinion's step 0c).

Traces: /tmp/glm-traces/<name>.trace, lines "layer expert" per routed expert (336 visits/token:
42 MoE layers x top-8).  Set A (profile build): the *1 traces.  Set B (evaluation, held out): the *2.
Configs (all evaluated at steady state - the first 256 tokens of each 640-token trace are warm-up):
  single cold / single warm   - one LFU pool of SLOTS (today's single-GPU mode)
  split cold / split warm     - two per-half pools of SLOTS (the layer split at layer 23)
  split warm+static S         - the top-S pairs per half pinned (never evicted), LFU for the rest
  split warm+static+ram R     - VRAM evictions demote into a per-half RAM LFU (RAM hits cost no NVMe)
Metric: steady-state NVMe reads and MB per token on set B, plus VRAM/RAM hit shares.
"""
import collections
import glob
import os

SPLIT = 23
SLOTS = 2744              # VRAM slots per half (the split) - the measured per-half capacity
WARMUP_TOK = 256
TOK_VISITS = 336          # 42 MoE layers x top-8
GU16 = {3, 10, 11, 12, 15, 17, 18, 21, 24, 26, 29, 39, 43, 44}
DN23 = {11, 12, 44}

def blob_bytes(layer):
    gu = 1056 if layer in GU16 else 800
    dn = 1088 if layer in DN23 else 784
    return 2 * gu * 2048 + dn * 4096

class Lfu:
    def __init__(self, cap):
        self.cap = cap
        self.tick = 0
        self.evicts = 0
        self.slot = {}                     # key -> [count, tick]
    def touch(self, k, c=1):
        e = self.slot.get(k)
        if e is None:
            return False
        e[0] = min(e[0] + c, 1 << 20)
        self.tick += 1
        e[1] = self.tick
        return True
    def insert(self, k, c=1):
        ev = None
        if len(self.slot) >= self.cap:
            vk = min(self.slot, key=lambda x: (self.slot[x][0], self.slot[x][1]))
            del self.slot[vk]
            ev = vk
            self.evicts += 1
            if self.evicts % 4096 == 0:
                for v in self.slot.values():
                    v[0] >>= 1
        self.tick += 1
        self.slot[k] = [c, self.tick]
        return ev

def load(path):
    out = []
    with open(path) as f:
        for line in f:
            l, e = line.split()
            out.append((int(l), int(e)))
    return out

def profile(traces):
    c = collections.Counter()
    for t in traces:
        c.update(load(t))
    return c

def sim(visits, warm_counts, static, ram_cap, steady_from_tok, split=True, seed_cap=64):
    """One trace.  Returns per-token-boundary cumulative stats; steady window = the tail.
    split=True: two per-half pools (static+pinned per half).  split=False: ONE pool over all layers.
    Warm-seeded pairs get count min(profile_count, seed_cap) so stale seeds cannot freeze the pool."""
    npool = 2 if split else 1
    bounds = [(0, SPLIT), (SPLIT, 10**9)] if split else [(0, 10**9)]
    half_pools = [Lfu(SLOTS - (static if split else 0)) for _ in range(npool)]
    pinned = [set() for _ in range(npool)]
    ram = [Lfu(ram_cap // npool) for _ in range(npool)] if ram_cap else None
    for h in range(npool):
        lo, hi = bounds[h]
        pairs = [(k, c) for k, c in warm_counts.items() if lo <= k[0] < hi]
        pairs.sort(key=lambda x: -x[1])
        for k, c in pairs[:static]:
            pinned[h].add(k)
            half_pools[h].slot[k] = [min(c, seed_cap), half_pools[h].tick]
            half_pools[h].tick += 1
        if warm_counts:                    # the warm (non-static) part of the pool
            for k, c in pairs[static:static + (SLOTS - (static if split else 0))]:
                half_pools[h].slot[k] = [min(c, seed_cap), half_pools[h].tick]
                half_pools[h].tick += 1
    stats = [0, 0.0, 0, 0]                 # nvme reads, bytes, vram hits, ram hits
    per = []
    tok = -1
    for i, k in enumerate(visits):
        tok = i // TOK_VISITS
        h = 0 if split and k[0] < SPLIT else (1 if split else 0)
        if k in pinned[h]:
            stats[2] += 1
        elif half_pools[h].touch(k):
            stats[2] += 1
        elif ram is not None and ram[h].touch(k):
            stats[3] += 1                  # pinned-host hit: no NVMe
            ev = half_pools[h].insert(k)
            if ev is not None:
                ram[h].insert(ev, 1)
        else:
            stats[0] += 1
            stats[1] += blob_bytes(k[0])
            ev = half_pools[h].insert(k)
            if ram is not None:
                if ev is not None:
                    ram[h].insert(ev, 1)
        if tok >= steady_from_tok and (i + 1) % TOK_VISITS == 0:
            per.append(tuple(stats))
    return per

def main():
    tr = sorted(glob.glob("/tmp/glm-traces/*.trace"))
    A = [t for t in tr if not t.endswith("2.trace")]
    B = [t for t in tr if t.endswith("2.trace")]
    print("set A (profile):", [os.path.basename(t) for t in A])
    print("set B (held out):", [os.path.basename(t) for t in B])
    pc = profile(A)
    bkeys = set()
    for t in B:
        bkeys.update(load(t))
    print("profile pairs:", len(pc), "| pairs seen in B but never in A:", len(bkeys - set(pc)))
    STEADY = 256
    RAM_SLOTS = 2750                   # ~19 GB pinned / 6.9 MB average blob - the machine's real bound
    cfgs = [
        ("single cold        ", False, 0, 0, False),
        ("single warm        ", True, 0, 0, False),
        ("split cold         ", False, 0, 0, True),
        ("split warm         ", True, 0, 0, True),
        ("split warm+ram2750 ", True, 0, RAM_SLOTS, True),
        ("split+st1372+ram2750", True, 1372, RAM_SLOTS, True),
        ("split+st686+ram2750 ", True, 686, RAM_SLOTS, True),
    ]
    print()
    print("%-21s %10s %10s %8s %8s" % ("config", "reads/tok", "MB/tok", "vram%", "ram%"))
    base = None
    for name, warm, static, ram, split in cfgs:
        agg = []
        for t in B:
            v = load(t)
            per = sim(v, pc if warm else {}, static, ram, STEADY, split=split)
            first, tail = per[0], per[-1]
            n = max(1, len(per) - 1)
            d_reads = (tail[0] - first[0]) / n
            d_bytes = (tail[1] - first[1]) / n
            d_vh = (tail[2] - first[2]) / n
            d_rh = (tail[3] - first[3]) / n
            tot = d_reads + d_vh + d_rh
            agg.append((d_reads, d_bytes / 1e6, d_vh / tot * 100 if tot else 0,
                        d_rh / tot * 100 if tot else 0))
        rr = sum(a[0] for a in agg) / len(agg)
        mb = sum(a[1] for a in agg) / len(agg)
        vh = sum(a[2] for a in agg) / len(agg)
        rh = sum(a[3] for a in agg) / len(agg)
        if base is None:
            base = rr
        print("%-19s %10.1f %10.1f %7.1f%% %7.1f%%   (%.2fx vs single-cold)" %
              (name, rr, mb, vh, rh, rr / base))

if __name__ == "__main__":
    main()
