# Edge0 — LEONES / ODS technology watch

**Status:** technology watch / future research  
**Date:** 2026-10-01  
**Repository:** https://github.com/Edge0-AI/Edge0  
**Relationship:** potential ODS inference backend; tracked by LEONES

## Summary

Edge0 is an open **streaming MoE inference** framework combining SSD expert offload, Recover-LoRA, and a prerouter that predicts the experts likely to be needed. The project separates backend concerns from its core and provides an OpenAI-compatible HTTP server.

This is particularly relevant to LEONES because Edge0 attempts to decouple a model's total MoE size from the amount of memory that must remain active during inference.

## Current status

The current implementation provides an **MLX backend for Apple Silicon**. A **CUDA backend is planned but is not yet a supported production backend**, so Edge0 should not currently be treated as an installable runtime for the ODS Linux/NVIDIA environment.

The repository's backend abstraction makes a future CUDA implementation directly relevant to ODS.

## Models under watch

| Tier | Model family | Published profile | Approx. disk | Published active memory* |
|---|---|---|---:|---:|
| edge0-8b | Ling 3.0 hybrid | 8B-class, 128 experts, 4-bit | ~4.2 GB | ~1.0 GB |
| edge0-35b | Qwen3.6-35B-A3B | 35B-class, 256 experts, 4-bit | ~23 GB | ~2.9 GB |

\* Published values are for short-context profiles and are not the total VRAM/RAM requirement. System memory, tokenizer/runtime buffers and KV-cache growth require additional headroom.

## ODS fit

The potential integration is conceptually straightforward because Edge0 provides:

- `GET /healthz`
- `GET /v1/models`
- `POST /v1/chat/completions`
- chat streaming
- an OpenAI-compatible API

Once a usable CUDA backend exists, the candidate path is:

```
ODS
 └── LiteLLM
      └── Edge0
           ├── streaming MoE
           ├── SSD expert offload
           ├── prerouter
           └── LoRA
```

Edge0 would therefore be better treated as an **additional inference engine/backend** than as a separate user-facing ODS application.

## Relevance to LEONES NVIDIA hardware

The NVIDIA reference machine for this research line has an RTX 3050 Laptop GPU with 4 GB VRAM.

The published ~2.9 GB active-memory figure for edge0-35b must **not** be interpreted as proof that the model will run on a 4 GB GPU. It is a benchmark/profile figure and additional memory is required.

The LEONES test gate should be:

1. a functional and maintained CUDA backend;
2. reproducible Linux/NVIDIA execution;
3. measured VRAM, RAM, SSD traffic, tokens/s, latency and stability;
4. compatibility with the OpenAI API used by ODS/LiteLLM;
5. comparison with the ODS reference inference backend.

## Watch signals

Track:

- CUDA backend development;
- non-macOS/Linux support;
- Edge0 execution on NVIDIA hardware outside Apple Silicon;
- CUDA benchmarks and reproducible installation instructions.

These signals justify keeping Edge0 in **Technology Watch**, but not promoting it to an operational ODS integration yet.

## Reassessment triggers

- [ ] Official or sufficiently stable CUDA backend.
- [ ] Reproducible Linux/NVIDIA support.
- [ ] Documented installation outside Apple Silicon.
- [ ] Published CUDA benchmark.
- [ ] Verification on 4–8 GB GPUs.
- [ ] OpenAI-compatible API test behind LiteLLM.
- [ ] Edge0-8B evaluation.
- [ ] Edge0-35B evaluation.
- [ ] Measurement of whether SSD I/O cost is justified by the reduction in active memory.

## Evidence

- [Edge0 project](https://github.com/Edge0-AI/Edge0)
- [Edge0 architecture](https://github.com/Edge0-AI/Edge0/blob/main/docs/architecture.md)
- [Edge0 issues](https://github.com/Edge0-AI/Edge0/issues)

## Watch conclusion

**Keep Edge0 under technology watch for LEONES/ODS.**

Its architecture has a clear conceptual fit with ODS's inference-backend abstraction and OpenAI-compatible service layer. The current blocker is a usable, verifiable CUDA/Linux path. The next review should focus on that capability rather than attempting to install the MLX/Apple-Silicon path in the ODS Ubuntu/NVIDIA environment.

**Language versions:** [Español](edge0-ods.md) · [English](edge0-ods-eng.md)
