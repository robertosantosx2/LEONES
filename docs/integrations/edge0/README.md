# Edge0 — ODS integration analysis

## Executive summary

Edge0 is a research/runtime stack for sparse Mixture-of-Experts inference when total model weights exceed accelerator memory. Its Hugging Face releases are especially relevant because runtime, checkpoint and storage-aware execution are designed together.

**ODS classification: P1 — high-priority runtime candidate.**

## Relevant capabilities

- SSD/NVMe streaming of experts.
- GPU-resident hot expert cache.
- Prerouter for predicting likely future experts.
- Recover-LoRA for recovery from routing/prediction effects.
- Sparse MoE execution.
- OpenAI-compatible serving in the project runtime.
- Hugging Face checkpoints designed around this execution model.
- Current implementation emphasis on MLX/Apple Silicon; NVIDIA/CUDA maturity must be verified independently.

## Architecture

```
Experts on SSD
     |
  prerouter
     |
predicted experts
     |
 expert cache
     |
 accelerator
     |
 Recover-LoRA
```

## ODS integration

Expose an Edge0 adapter through the proposed Runtime Capability Manifest:

- accelerator/backend;
- minimum RAM/VRAM;
- NVMe requirement;
- supported model families;
- expert streaming;
- prerouting;
- LoRA recovery;
- API protocol.

This should complement llama-server rather than replace it.

## Hardware implications

With a small NVIDIA GPU, SSD latency, sustained bandwidth, RAM and cache size become first-class resources. A 4 GB GPU should therefore be classified as experimental until measured rather than declared compatible from model size alone.

## LEONES measurements

Record separately:

- reported model/runtime requirements;
- observed installation and health;
- measured SSD bandwidth;
- cache hit rate;
- TTFT;
- tokens/s;
- peak RAM/VRAM.

## Risks

1. CUDA maturity may lag the MLX path.
2. SSD performance can dominate latency.
3. Model/runtime coupling is stronger than GGUF + llama.cpp.
4. Prerouter/Recover-LoRA may restrict arbitrary model compatibility.

## Recommendation

Keep Edge0 in the **P1** ODS candidate set and study its Hugging Face model packaging together with the runtime. It is a strong reference for a storage-aware MoE adapter.

## Sources

- Hugging Face Edge0 organization and model cards.
- Edge0 project repository and documentation.
- Related Edge0 research.

Published benchmark figures remain **reported**, not LEONES-measured.


## Technology watch

- [Edge0 — vigilancia ODS](../../../research/vigilancia/edge0-ods.md)
- [English technology watch](../../../research/vigilancia/edge0-ods-eng.md)
