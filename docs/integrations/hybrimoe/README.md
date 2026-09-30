# HybriMoE — ODS integration analysis

## Executive summary

HybriMoE explores hybrid CPU/GPU execution for MoE inference, combining dynamic scheduling, prefetching and cache management for limited accelerator memory.

**ODS classification: P1/P2 — research/runtime architecture candidate.**

## Core problem

A sparse MoE runtime must continuously decide:

```
what stays on GPU?
what stays in RAM?
what should be prefetched?
what should be evicted?
what can execute on CPU?
```

## Architecture reference

```
experts
 |        |
RAM      NVMe
 |
cache -> prefetch -> GPU VRAM -> compute
```

## ODS integration

Represent the relevant capabilities rather than hard-coding a backend:

- CPU/GPU collaboration;
- dynamic expert placement;
- asynchronous prefetch;
- cache policy;
- eviction;
- heterogeneous execution.

## Small-GPU relevance

A 4 GB GPU may benefit from hybrid execution, but transfer overhead can erase gains. Measure RAM, NVMe, PCIe, expert size, routing locality, context and batch size.

## LEONES benchmark

Compare GPU-only where possible, CPU/RAM offload, CPU/GPU hybrid and SSD streaming. Record TTFT, tok/s, RAM, VRAM, NVMe traffic, CPU usage and cache hit rate.

## Recommendation

Keep HybriMoE in the **P1/P2** research pool and use its concepts to inform the Runtime Selector and benchmark schema.

## Sources

- Hugging Face HybriMoE paper.
- Associated research/code where available.

Research performance claims remain **reported** until measured by LEONES.
