# Inference Configuration Discovery — prototype

## Purpose

LEONES already separates model/runtime selection from runtime benchmarking.
The missing layer is Inference Configuration Discovery (ICD): determining
which configuration of a compatible runtime should actually be evaluated.

The prototype is deliberately declarative:

hardware/model/workload → compatible runtime profile → configuration candidates → benchmark → measured evidence → best configuration

It does not execute runtimes and does not turn estimates into measured claims.

## Configuration dimensions

The generic contract represents runtime and revision/build, kernel, model and
quantization, context length, GPU layers/offload, KV-cache format, Flash
Attention, speculation/MTP and draft-token count, and batch configuration.

This is intentionally not a cafe-llama.cpp-specific schema. cafe-llama.cpp is
the first experimental consumer; Strata and TensorFold can implement the same
discovery boundary later.

## Evidence rule

REPORTED, ESTIMATED, OBSERVED and MEASURED remain distinct. Only a configuration
matched to MEASURED evidence may be ranked as a measured performance result.

A measurement is keyed to the complete configuration_id, not merely to the
model or runtime. Changing the kernel, context, KV cache, MTP mode, or another
configuration dimension therefore creates a different experimental unit.

## Relationship to existing contracts

- runtime-selection.v1.1 decides whether a runtime/model combination is compatible.
- ICD proposes concrete configurations.
- runtime-benchmark.v1 measures an executed configuration.
- runtime-selection evidence closes the loop.
- No new execution authority or persistence mechanism is introduced.

## Transfer criterion to ODS

The prototype is ready to port when its tests demonstrate deterministic
configuration identity, runtime-profile compatibility remains authoritative,
configuration candidates are runtime-agnostic, execution and measurement
cannot leak into discovery, measured evidence ranks configurations only by
matching identity, and no runtime-specific branch is required by the core
discovery engine.
