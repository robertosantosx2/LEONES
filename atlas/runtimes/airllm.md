# AirLLM runtime profile

## Purpose

AirLLM is a memory-frugal inference runtime that streams model weights layer-by-layer from storage rather than keeping the full checkpoint resident in GPU memory. Its current implementation creates a Transformers model skeleton on the `meta` device and loads decoder layers on demand, with optional prefetching. This makes AirLLM relevant to LEONES when model size exceeds available VRAM.

## Evidence classification

- **Source:** https://github.com/lyogavin/airllm
- **Source type:** external
- **Evidence state:** reported/reproducible from upstream implementation; runtime capability is not a LEONES measurement.
- **LEONES measurement:** none until the runtime is executed on the target hardware and benchmarked.

## RULA implications

AirLLM can be represented as a runtime candidate, but `rula_status=verified` must only be assigned by a LEONES runtime probe on the target hardware/model combination. Upstream documentation is not sufficient to authorize execution.

The runtime profile therefore supplies capabilities and constraints, not measured throughput:

- layer-wise disk-to-device weight streaming;
- optional prefetching;
- optional compression/quantized checkpoint support;
- CUDA execution in the normal GPU path;
- CPU inference support exists in the project history/current ecosystem, but should not be treated as equivalent performance to GPU execution;
- storage I/O is a first-class performance constraint.

## Selector contract

A candidate using AirLLM may enter `runtime-selection.v1` with `rula_status=unknown` or `estimated`. It becomes executable only after a LEONES probe records a verified runtime identity, supported model/format, hardware compatibility, and successful smoke execution.

The probe should record:

- runtime name/version/commit;
- model identity and revision;
- model format/checkpoint layout;
- execution device;
- available VRAM/RAM/storage;
- context length;
- whether prefetching/compression was enabled;
- successful generation result;
- measured TTFT, tokens/s and failure/recovery information.

These measurements belong to the LEONES measurement layer and must never overwrite upstream source claims or LLMFit estimates.

## Known operational constraint

AirLLM trades memory pressure for storage traffic and layer materialisation. Consequently, the selector must consider storage latency/bandwidth and available VRAM rather than treating `weight_memory_gb` alone as sufficient for a recommendation.

## Sources

- Upstream repository: https://github.com/lyogavin/airllm
- Upstream implementation: https://github.com/lyogavin/airllm/blob/main/air_llm/airllm_base.py
