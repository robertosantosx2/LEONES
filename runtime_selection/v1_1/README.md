# Runtime Registry V1.1

This directory defines the V1.1 runtime registry boundary for LEONES.

## Fixed architecture

```text
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

## Boundary rules

1. The selector consumes capabilities and eligibility state; it does **not** know runtime commands or shell syntax.
2. `entrypoint_ref` is an opaque trusted reference. Only the adapter resolves it to an executable entrypoint.
3. A runtime never selects a model. It receives an already authorized `runtime-selection.v1` plan.
4. The runner executes the adapter plan and records execution; it does not promote estimates to measurements.
5. `runtime-benchmark.v1` is the common measurement boundary.
6. `estimated_tps` and `measured_tps` are different semantic fields and cannot substitute for one another.
7. A measured result requires a benchmark execution and provenance.

## Required registry information

Every runtime declares identity/version policy, adapter identity, trusted entrypoint reference, host availability probe, execution modes, supported architectures/formats, hardware/memory/bandwidth requirements, capabilities, metric extraction, and measurement policy.

## Availability and gates

The registry can describe `available`, `unavailable`, `unknown`, or `blocked`. Capability matching must reject a runtime when it is unknown/unavailable, the plan is not authorized, the trusted entrypoint cannot be resolved, or model/quantization/hardware requirements do not match.

Runtime-specific eligibility gates are adapter-owned. This preserves special handling such as the FreeToken gate without teaching the selector runtime-specific command logic.

## Measurement semantics

The registry may permit estimates because estimates are useful for selection. It never creates a measurement. `measured_tps` can only be populated by the common benchmark path, with runtime version, model, quantization, hardware, workload, protocol, timestamp and provenance preserved by the evidence layer.

## Initial entries

The initial V1.1 registry contains the four first-wave runtimes:

- llama.cpp — canonical reference adapter.
- Ollama — normalized A01 adapter boundary.
- FreeToken — adapter-owned eligibility gate.
- AirLLM — executable runtime candidate with host/dependency/model checks delegated to its adapter.

The second wave is deliberately added through the same schema rather than introducing runtime-specific selector branches.

## V1 compatibility

This registry is additive. It does not alter the V1 evidence contract or reinterpret existing evidence. V1 remains the evidence baseline; V1.1 extends execution capability around it.
