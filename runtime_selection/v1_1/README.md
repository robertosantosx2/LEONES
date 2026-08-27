# Runtime Registry V1.1

This directory defines the **V1.1 runtime registry boundary** for LEONES. It is the compatibility layer between model selection and executable inference runtimes.

## Fixed architecture

```text
knowledge / measurements / estimates
              ↓
           selector
              ↓
      runtime-selection.v1
              ↓
     runtime registry + capability match
              ↓
       trusted runtime adapter
              ↓
            runner
              ↓
      runtime-benchmark.v1
              ↓
        evidence / Router
```

The critical architectural rule is that **selection, execution, measurement and evidence are different responsibilities**. A runtime entry describes what a runtime can support; it does not grant permission to execute arbitrary commands and it does not manufacture performance measurements.

## Boundary rules

1. The selector consumes capabilities and eligibility state; it does **not** know runtime commands, shell syntax or local executable paths.
2. `entrypoint_ref` is an opaque trusted reference. Only the adapter resolves it to an executable entrypoint.
3. A runtime never selects a model. It receives an already authorized `runtime-selection.v1` plan.
4. The runner executes the adapter plan and records execution; it does not promote estimates to measurements.
5. `runtime-benchmark.v1` is the common measurement boundary for runtime observations.
6. `estimated_tps` and `measured_tps` are different semantic fields and cannot substitute for one another.
7. A measured result requires benchmark execution and provenance: runtime, runtime version, model, variant/quantization, hardware, workload, protocol and timestamp must remain recoverable.
8. Runtime availability is explicit. `unknown` is not equivalent to `available` and must not silently become an execution authorization.
9. Runtime-specific eligibility belongs to the adapter. This keeps special cases such as the FreeToken gate out of selector branches.
10. The registry is descriptive. It must never contain executable `command`, `argv`, `shell` or host-specific command strings.

## Registry contract

Every runtime declares:

- stable `runtime_id` and human-readable `display_name`;
- version discovery/policy;
- adapter identity;
- opaque trusted `entrypoint_ref`;
- availability probe and state;
- execution modes (`cpu`, `gpu`, `hybrid`, `serving`, as applicable);
- supported model architecture classes and formats;
- accelerator, memory and bandwidth requirements;
- runtime capabilities such as batching, KV cache, speculative decoding, multimodality, concurrency and streaming;
- metric source and required metric fields;
- measurement policy, including the rule that measured throughput requires the common benchmark path.

## Availability and gates

The registry can describe `available`, `unavailable`, `unknown`, or `blocked`.

Capability matching must reject a runtime when:

- availability is incompatible with execution;
- the plan is not authorized;
- the trusted entrypoint cannot be resolved;
- model architecture or format is unsupported;
- hardware, memory or accelerator requirements do not match; or
- an adapter-owned eligibility gate rejects the candidate.

This is deliberately stricter than “the package exists”. A runtime being installed is not sufficient evidence that a particular model can execute safely or efficiently on a particular host.

## Measurement semantics

The registry may permit estimates because estimates are useful during model/runtime selection. **The registry never creates a measurement.**

`measured_tps` can only be populated by an actual benchmark execution through the common benchmark boundary. Evidence must preserve the provenance needed to distinguish:

```text
source claim       → external published evidence
estimate            → selector/runtime estimate
execution           → successful runtime execution
measurement         → benchmark-derived runtime metric
real evidence       → measured execution + provenance
```

A deterministic CI fixture may prove the complete execution trajectory without producing throughput. That is valid evidence of the **execution contract**, not evidence of real hardware throughput. Real-runtime evidence, such as the Ollama A01 execution, remains a separate artifact and must retain its runtime/model provenance.

## Runtime coverage

The registry already follows the same contract for a broad first V1.1 runtime set, including:

| Runtime family | Primary role | Typical execution domain | LEONES rule |
|---|---|---|---|
| llama.cpp | local GGUF inference | CPU/GPU/hybrid | canonical reference adapter |
| Ollama | local/serving inference | CPU/GPU/hybrid | normalized `ollama.v1` adapter |
| FreeToken | optimized GPU inference | GPU/hybrid | adapter-owned eligibility gate |
| AirLLM | layer/offload-oriented inference | CPU/GPU/hybrid | dependency/model/host checks in adapter |
| vLLM | high-throughput serving | GPU/hybrid | serving-oriented adapter |
| SGLang | serving and optimized inference | GPU/hybrid | serving-oriented adapter |
| MLX / MLX-LM | Apple Silicon inference | Metal | host-specific adapter |
| ExLlama families | quantized GPU inference | CUDA | format/architecture-aware adapter |

The registry may grow further without changing the selector contract. Adding a runtime means adding a registry declaration and adapter implementation, **not adding a new runtime-specific branch to the selector**.

## V1 compatibility

V1.1 is additive. It does not reinterpret or rewrite V1 evidence.

V1 remains the evidence baseline:

```text
V1 evidence contract
       ↑
       │ preserved
       │
V1.1 runtime selection / adapters
       │
       └── adds execution choices
```

Existing V1 evidence remains valid. V1.1 adds the ability to express and execute more runtime choices while preserving the same evidence semantics.

## Verification strategy

V1.1 verification is deliberately layered:

1. **Schema/registry tests** verify that every runtime declares the common fields and trusted entrypoint form.
2. **Selector contract tests** verify that selection does not leak commands or shell syntax.
3. **Adapter contract tests** verify runtime-specific eligibility and preparation.
4. **A01 deterministic CI** proves the complete selector → adapter → executor → grader → benchmark → evidence → Router path without requiring a model or GPU.
5. **Real-runtime runs** provide hardware-backed evidence and measured throughput when the host/runtime actually reports it.

The CI path therefore proves reproducibility of the architecture without pretending that a GitHub-hosted fixture is a substitute for real hardware measurement.
