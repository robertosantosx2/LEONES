# ODS Dashboard inference configuration discovery

## Status

Experimental LEONES specification for the ODS integration.

This document defines the Dashboard-facing layer on top of the Inference Configuration Discovery (ICD) contract already validated in this repository.

ODS remains the production target; LEONES records architecture, contract, evidence boundaries, and acceptance criteria.

## User flow

model selection
-> compatible runtime profile
-> inference configuration discovery
-> parameter editing
-> runtime validation
-> apply
-> benchmark
-> MEASURED evidence
-> selected configuration

The existing model activation path remains responsible for loading the model. The inference editor is a second-stage configuration surface and must not create a competing model activation mechanism.

## Dashboard capabilities

For a selected model, expose only dimensions declared by the selected runtime and compatible with the model:

- runtime
- runtime revision
- kernel
- quantization
- context
- GPU layers
- KV-cache type
- Flash Attention
- offload strategy
- speculation / MTP
- draft-token depth
- batch dimensions

The UI must not expose an unbounded Cartesian product. Discovery produces a bounded candidate set; the editor changes individual dimensions and submits one concrete configuration for validation.

## API contract

### Discovery

GET /api/models/{model_id}/inference-configurations

The response contains schema_version, model_id, compatible runtimes, runtime capabilities, discovered configuration candidates, and selected configuration when one exists.

Each discovered configuration contains deterministic configuration_id, complete configuration, source=discovery, evidence_level=estimated, measurement_required=true, and execution_authorized=false.

No throughput, latency, benchmark result, or other measurement belongs in this response.

### Apply

POST /api/models/{model_id}/inference-configuration

The backend must:

1. validate the generic ICD schema;
2. verify model_ref;
3. verify runtime compatibility;
4. invoke runtime-specific validation;
5. translate the configuration into runtime settings;
6. use ODS environment/lifecycle mechanisms;
7. optionally execute the existing benchmark path;
8. return the deterministic configuration identity.

Applying a configuration does not turn estimated evidence into measured evidence. Only the benchmark/evidence path can do that.

## i18n contract

The Dashboard editor must use the existing Dashboard i18n hook. UI keys belong under models.inferenceConfiguration.*.

English remains the fallback language. Spanish and Simplified Chinese extend the same key set.

Suggested keys:

- title
- runtime
- kernel
- context
- gpu_layers
- kv_cache
- flash_attention
- offload
- speculation
- draft_tokens
- batch
- apply
- benchmark
- refresh
- close
- loading
- estimated
- empty
- note

## Evidence boundary

The Dashboard may display DISCOVERED / ESTIMATED, VALIDATED, and MEASURED states.

A discovered or validated configuration must never be displayed as though its performance had been measured.

Measured ranking remains keyed by the exact configuration_id so a benchmark for one context, KV cache, kernel, or offload combination cannot be reused for another.

## Runtime boundary

The generic ICD layer remains runtime-agnostic. The cafe-llama.cpp adapter owns its capability vocabulary, semantic validation, environment mapping, and future executable integration.

Future runtimes such as Strata or TensorFold should implement the same conceptual contract rather than adding runtime-specific branches to Dashboard core.

## Acceptance criteria

- A selected model can request ICD configurations from the Dashboard.
- The Dashboard exposes only runtime-supported dimensions.
- A user can modify a concrete configuration.
- Invalid runtime combinations are rejected before execution.
- Applying configuration uses the existing ODS lifecycle.
- Benchmarking is optional and uses the existing evidence path.
- Measured results are associated with the exact configuration ID.
- No benchmark values are embedded in ICD discovery data.
- Existing model loading remains unchanged.
- The default llama-server path remains unchanged when cafe-llama.cpp is not selected.
- The UI can merge cleanly with Dashboard ES/ZH i18n work.

## Relation to the existing LEONES prototype

This document extends docs/experimental/ods-cafe-llama-icd-port.md.

That document establishes the ODS-shaped ICD contract and production port requirements; this one adds the human-facing Dashboard layer.

The implementation belongs in ODS. LEONES retains the specification, tests, provenance, and evidence needed to review that implementation.

## Explicit non-goals

This phase does not replace model selection, create a new model activation path, create a second evidence database, claim hardware performance, integrate Strata or TensorFold into ODS, or authorize arbitrary runtime execution from an unvalidated configuration.
