# ODS cafe-llama.cpp ICD integration prototype

## Objective

This LEONES branch is an ODS-shaped validation lane for the real target:
integrating cafe-llama.cpp into ODS as an optional runtime that participates in
model/runtime selection rather than being only a manually enabled service.

The already-merged ODS service scaffold provides the process boundary. The
missing selection layer is:

hardware + model
→ compatible runtime profile
→ ICD configurations
→ runtime validation
→ benchmark
→ MEASURED evidence
→ selected configuration
→ runtime environment.

## ODS contract reproduced here

The prototype preserves the existing ODS distinction:

- runtime_profile: compatibility and executable profile.
- ConfigurationCandidate: concrete configuration proposed for evaluation.
- configuration_id: deterministic identity of the complete configuration.
- MEASURED: only evidence class allowed to rank measured throughput.
- adapter mapping: runtime-specific environment belongs outside generic ICD.

## cafe-llama dimensions

The fixture deliberately exercises:

- kernel
- context
- KV cache
- GPU layers
- speculation/MTP
- draft token depth
- offload
- Flash Attention

The multidimensional integration test generates 32 deterministic candidates
from a 2×2×2×2×2 search space. No benchmark value is stored in a discovered
configuration.

## cafe-specific validation

runtime_selection/cafe_llama.py is the ODS-shaped adapter contract.

It validates constraints that are specific to cafe-llama.cpp:

- Turbo KV requires Flash Attention.
- draft-mtp requires a positive draft depth.
- non-speculative configurations must not carry draft tokens.
- supported configuration dimensions map to ODS LLAMA_ARG_* environment keys.

The adapter does not execute a process.

## Port to ODS

Once this branch is accepted, the production ODS implementation should:

1. add the generic ICD module beside model_selection.py;
2. attach discovered configurations to the existing Candidate selection result;
3. preserve runtime_profiles as the compatibility source of truth;
4. expose cafe-llama's runtime profile/capabilities in the model catalog;
5. validate the selected configuration through the cafe adapter;
6. reuse ODS's existing benchmark/evidence and memory qualification paths;
7. persist the winning configuration_id together with the selected runtime profile;
8. keep the default llama-server path unchanged when no cafe configuration is selected.

The production implementation must not create a second evidence database and
must not put benchmark results inside ICD candidates.

## Important limitation

This branch proves the selection contract in LEONES. It does not claim that a
configuration has been measured on the user's hardware. A production ODS
benchmark still needs to execute the actual cafe-llama.cpp build and record
MEASURED evidence under a controlled workload.
