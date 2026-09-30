# MoE-Lens — ODS integration analysis

## Executive summary

MoE-Lens is more valuable to ODS as a performance-modeling and hardware/runtime design reference than as an inference server.

**ODS classification: P1 — architecture and benchmarking reference.**

## Why it matters

MoE suitability cannot be reduced to model size versus VRAM. Relevant variables include:

- total parameters;
- active parameters;
- expert count and size;
- GPU/CPU memory;
- PCIe transfer cost;
- NVMe bandwidth;
- routing locality;
- batch size;
- context length.

This supports ODS's move toward hardware-aware runtime selection.

## Proposed ODS model

```
hardware profile
   |
model profile
   |
runtime profile
   |
predicted operating regime
```

The prediction must remain labelled **estimated**.

## LEONES

Use the concepts to design benchmark matrices and identify compute-, memory- and I/O-bound regimes.

Record RAM, VRAM, NVMe behaviour, TTFT, tokens/s, context and cache metrics. Estimates must never be presented as LEONES measurements.

## Recommendation

Adopt the concepts in ODS/LEONES profiling and the future Runtime Selector rather than adding MoE-Lens as a runtime dependency.

## Sources

- Hugging Face MoE-Lens paper.
- Related MoE performance-model research.

Published figures remain **reported** until reproduced.
