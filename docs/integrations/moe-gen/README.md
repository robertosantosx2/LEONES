# MoE-Gen — ODS integration analysis

## Executive summary

MoE-Gen focuses on efficient single-GPU MoE execution through scheduling and module/expert batching rather than primarily solving model storage.

**ODS classification: P2 — throughput/runtime research.**

## Main idea

```
tokens
  |
routing
  |
expert groups
  |
module-based batching
  |
GPU kernels
```

This attacks GPU under-utilization caused by fragmented expert work.

## Difference from SSD streaming

Edge0, WARP and ramvamp primarily address models that do not fit memory. MoE-Gen primarily addresses inefficient use of a GPU that is already executing the model.

Both approaches can coexist.

## ODS relevance

The Runtime Selector should distinguish:

- memory-constrained MoE;
- throughput-constrained MoE;
- latency-sensitive interactive inference;
- batched inference.

Offline throughput must not be transferred directly to interactive assistant expectations.

## LEONES benchmark

Test batch 1 and larger batches where hardware allows. Record TTFT, tok/s, GPU utilization, VRAM and CPU utilization.

## Recommendation

Keep MoE-Gen at **P2** as a throughput-engineering reference.

## Sources

- Hugging Face MoE-Gen paper.
- Associated implementation/documentation.

Published speedups remain **reported**, not LEONES measurements.
