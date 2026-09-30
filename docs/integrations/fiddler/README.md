# Fiddler — ODS integration analysis

## Executive summary

Fiddler explores CPU/GPU collaborative execution for large MoE models. Instead of using CPU only as a storage tier, selected computation can be performed on CPU to reduce data movement to the GPU.

**ODS classification: P2 — hybrid inference research candidate.**

## Core idea

Traditional offload:

```
CPU/RAM -> transfer expert -> GPU -> compute
```

Fiddler-style hybrid execution:

```
CPU compute + GPU compute -> minimized transfer
```

## ODS capability

A future Runtime Capability Manifest could expose:

- CPU expert computation;
- GPU expert computation;
- hybrid scheduling;
- transfer minimization;
- CPU/GPU synchronization.

## Relevance

This can be useful when VRAM is limited and CPU compute is available, but CPU execution may also become the bottleneck. For interactive inference the result must be measured.

## LEONES benchmark

Compare GPU-only, CPU-only, CPU/GPU hybrid and GPU plus storage offload. Measure TTFT, tok/s, CPU/GPU utilization, PCIe traffic and RAM/VRAM.

## Integration strategy

Do not make Fiddler a mandatory ODS dependency. Use it as a research reference and reproducible benchmark candidate.

## Recommendation

**P2.** Monitor whether its techniques enter mainstream runtimes.

## Sources

- Hugging Face Fiddler paper.
- Associated open-source repository/documentation.

Published benchmark results remain **reported** until reproduced.
