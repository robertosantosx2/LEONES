# Inference Optimization Knowledge — hardware modesto

## Purpose
This layer sits between the user's hardware/use case and model candidate selection. It records techniques and runtimes that can make a model viable on constrained hardware. External claims remain knowledge/evidence; LEONES measurements are separate.

## Taxonomy

### QUANTIZATION
- GGUF / llama.cpp quantization: reduce weight memory and bandwidth; compare Q2/Q3/Q4/Q5/Q6/Q8 by quality, memory and measured speed.
- GPTQ / AWQ: low-bit weight quantization with runtime-specific trade-offs.
- BitNet / 1-bit approaches: extreme reduction in weight precision; treat as model/runtime-specific, not universally interchangeable with ordinary quantization.

### OFFLOAD / STREAMING
- AirLLM: layer-wise loading/offloading designed to run models larger than available GPU memory; particularly relevant to large and MoE models.
- FlexGen: execution/offloading planning across GPU, CPU and storage for constrained-memory inference.
- CPU/GPU layer offload: keep a subset of layers in VRAM and the remainder in system RAM/CPU.
- mmap: map model files without requiring the whole artifact to be eagerly loaded into RAM.
- Layer streaming + prefetch: stream layers and prefetch upcoming layers to hide part of transfer latency.

### SPARSE / MoE
- MoE expert-aware execution: distinguish total parameters from active parameters per token.
- Expert offload: place frequently used experts in faster memory and colder experts in CPU/RAM where the runtime supports it.
- PowerInfer: exploit activation/sparsity patterns to reduce GPU work and memory pressure; treat reported gains as source evidence until LEONES measures them.

### CACHE / DECODING
- KV-cache quantization/compression: reduce memory growth with long context.
- Speculative decoding: draft model proposes tokens and target model verifies; useful only when the draft/target pair and workload make acceptance gains worthwhile.

### COMPILED / HARDWARE-SPECIFIC
- llama.cpp backends and optimized CPU/GPU kernels (AVX2/AVX512/AMX, CUDA, Vulkan, SYCL, Metal, etc.) can materially alter viability and throughput.
- MLC-LLM: compile/adapt inference for the target device using TVM; relevant to heterogeneous and edge hardware.

### DISTRIBUTED
- Petals: distribute model layers across participating machines.
- Exo: distribute inference across multiple local devices.
- These are relevant when a single modest machine cannot host the selected configuration, but network latency/bandwidth becomes part of the benchmark contract.

## Candidate source projects
| Source | Family | LEONES use |
|---|---|---|
| AirLLM | offload/streaming | large models, MoE, low VRAM |
| llama.cpp | quantization + offload + hardware kernels | baseline local runtime |
| PowerInfer | sparse/activation-aware | CPU+small GPU, large models |
| FlexGen | offload/planning | constrained memory |
| Petals | distributed | multiple modest machines |
| BitNet | extreme low-bit | CPU/edge research |
| MLC-LLM | compiled/device-specific | heterogeneous devices |
| Exo | distributed | multiple local devices |
| LowMemoryLLM | experimental low-memory | experimental evidence only |

## Selector contract
Before model scoring, LEONES must establish:
1. user use case;
2. functional requirements;
3. actual hardware profile;
4. candidate inference runtimes;
5. compatible optimization techniques;
6. Dense vs MoE;
7. for MoE, total and active parameters;
8. only then evaluate model candidates.

## MoE rule
For Dense models, parameter-size selection uses `total_parameters_m`.
For MoE models, selection by computational scale uses `active_parameters_m`; total parameters remain recorded for storage/memory planning. Missing active-parameter data is `MISSING_ACTIVE_PARAMS` and must not be silently substituted.

## Runtime configuration is part of the candidate
A candidate is not merely `model_id`. The effective candidate is:
`model + quantization + runtime + offload + cache strategy + decoding optimization + hardware`.

## Evidence discipline
Do not convert source-reported speedups into `measured_tps`. Record source claims separately, then validate promising configurations through the controlled LEONES runtime/benchmark path.

## Status
`knowledge-contract-ready`: taxonomy and selector prerequisites defined; individual source fichas should remain independently maintained and linked to this layer.