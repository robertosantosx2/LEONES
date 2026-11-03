# Edge0 and moe-anywhere: Technical Analysis and Integration Opportunities

**Date:** 2026-11-03  
**Scope:** Local inference of sparse-MoE models, expert offloading, routing prediction, and acceleration of TensorFold and related runtimes.  
**Status:** Documentary analysis of repositories and published benchmarks; integration proposals are hypotheses that require prototyping and measurement.

## Executive Summary

Edge0 and moe-anywhere address complementary parts of the MoE inference bottleneck:

- **Edge0** combines streaming expert weights from SSD, a trained *prerouter* that predicts experts for the next token, and **Recover-LoRA** to recover quality lost through int4 quantization.
- **moe-anywhere** explores VRAM expert caching, prediction/pre-gating and prefetch, as well as a hybrid CPU/GPU path for cache misses in llama.cpp.
- For **TensorFold**, the most transferable approach is not to copy either runtime, but to incorporate decoupled mechanisms: expert indexes, anticipatory prediction, multilevel caching, cost-based scheduling, admission control, and telemetry.
- For **tandem.cpp**, moe-anywhere contributes cache policies and evaluation; Edge0 contributes the idea of anticipating routing to hide storage latency.
- **InferSSD** remains the closest candidate to Edge0 for SSD streaming. Edge0 adds an important dimension: learned routing prediction and LoRA-based quality recovery.

## 1. Edge0

Repository: https://github.com/menonpg/edge0  
Organization: https://github.com/Edge0-AI/Edge0  
Technical report: https://arxiv.org/abs/2609.XXXXX (verify the final identifier in the repository before citing in external publications)  
Research page: https://edge0.ai/research/edge0

### What it does

Edge0 is a streaming MoE inference framework. Its thesis is that peak memory should depend on the set of active experts, rather than the total parameter count.

Its main approach combines:

1. **SSD expert offload.** Experts are read from storage when needed. The system avoids keeping all expert weights resident in RAM or VRAM.
2. **Prerouter / routing prediction.** A trained head predicts the set of experts for the next token. Loading can begin while the current token is being computed, overlapping I/O and computation.
3. **Recover-LoRA.** The int4-quantized base remains frozen. LoRA adapters trained through distillation from a full-precision teacher compensate for some quality loss.
4. **Unmerged adapters.** The read-only base model can serve different LoRA sets without duplicating or rewriting base weights.
5. **Backend separation.** In the Python framework, model, streaming, routing, and server logic are abstracted from MLX. CUDA appears as a reserved backend in the architecture, but this must not be mistaken for operational CUDA support in the Python framework.

### Notable internal design

The architecture separates modules for:

- model, layout, and MoE quantization specification;
- per-layer expert streaming;
- mmap access to safetensors file ranges;
- shared LRU cache across layers;
- prerouter, staging, and double buffering;
- inference loop and LoRA adapters;
- OpenAI-compatible HTTP server.

During decode, prerouter predictions are placed in double-buffered slots. The expert layer uses quantized gather and updates slots without repeatedly rebuilding large tensor structures. This implementation is currently tied to MLX in the Python version.

### Published models and benchmarks

Edge0 publishes two complete pipelines with base checkpoints and trained adapters:

| Tier | Base | Profile |
|---|---|---|
| edge0-35b | Qwen3.6-35B-A3B | int4, 40 layers, 256 experts, K=4 |
| edge0-8b | Ling 3.0 hybrid | int4, 24 layers, 128 experts, K=8 |

Team benchmarks, on a 24 GB Mac mini M4 Pro:

| Model | Decode | Cold / warm prefill | Peak active memory |
|---|---:|---:|---:|
| Edge0-35B-A3B | 14.9–17.7 tok/s | 113 / 140 tok/s | 2.9 GiB |
| Edge0-8B-A1B | 23.9–25.3 tok/s | 500 / 1428 tok/s | 1.0 GiB |

The repository reports up to **+59% decode throughput** from the prerouter in certain scenarios. This is the authors’ result and must not be extrapolated to TensorFold, CUDA, or the MSI’s RTX 3050 without independent benchmarking.

Published quality evaluation (OpenCompass, 0–100 scale):

| Model | Edge0 int4 + adapters | fp16 base | Mean difference |
|---|---:|---:|---:|
| Edge0-35B | 79.2 | 83.2 | −4.0 |
| Edge0-8B | 69.9 | 72.7 | −2.8 |

### What it could contribute to TensorFold

**High priority — prerouter and prefetch**
- Predict next-token experts from states available for the current token.
- Launch asynchronous expert reads/copies into an alternate buffer.
- Measure predictor recall@K, useful-hit rate, unused prefetched bytes, and hidden latency.
- Introduce an exact fallback: an incorrect prediction must not alter routing or the target model’s distribution.

**High priority — double buffering**
- Separate the expert buffer consumed by the kernel from the one being prepared for the next step.
- Avoid global synchronization; establish per-layer events and dependencies.
- Evaluate whether the additional reserved memory is offset by reduced GPU idle time.

**Medium priority — streaming architecture**
- Index expert tensors by byte ranges without duplicating the file.
- Share a cache across layers with explicit policies and budgets.
- Read experts on demand and manage hot experts.

**Medium / experimental priority — Recover-LoRA**
- Investigate whether a distilled LoRA can recover quality from aggressive quantization enough to make a model viable in 4 GB of VRAM.
- This requires training, a dataset, a teacher, and evaluation; it is not a runtime-only optimization.
- Do not assume Edge0 adapters can be reused with other base models, quantizations, architectures, or engines.

### Limitations and risks

- The public Python path is MLX / Apple Silicon; CUDA is reserved, not implemented in that framework according to the consulted architecture.
- The prerouter requires model-, layer-, and routing-configuration-specific training.
- A high-recall predictor may still be inefficient if it preloads too many experts or consumes VRAM needed by the model.
- int4 quality depends on paired adapters and checkpoints.
- Published numbers come from Apple Silicon hardware; they do not represent NVIDIA performance.

## 2. moe-anywhere

Repository: https://github.com/carl0sfelipe/moe-anywhere  
Experiments: https://github.com/carl0sfelipe/moe-anywhere/blob/main/research/experiments.md

### What it does

moe-anywhere is a llama.cpp-based laboratory for running sparse MoE on consumer GPUs through offloading, expert caching, and prefetch. It does not initially attempt to replace the entire runtime: it adds experimental mechanisms to the existing execution flow.

### Main mechanisms

1. **CPU/GPU expert offloading.** Experts can reside in RAM and are executed or transferred according to placement.
2. **VRAM expert cache.** Keeps frequently used experts, with policies such as LRU and explicit cache sizing.
3. **Pre-gating.** Runs a future layer’s router early using activations available from the previous layer, estimating which experts will be needed.
4. **Asynchronous prefetch.** Loads candidates while current work is running.
5. **Hybrid cache-miss path.** In its llama.cpp patch, a miss can be processed by CPU while the GPU continues with resident experts, rather than serializing the entire step.
6. **Routing traces.** Proposes recording (layer, token, top-k expert IDs) and building datasets to evaluate predictors over horizons of 1, 2, and 3 tokens.

### Published results

Experiments with **Sage-A1.5 (Qwen3.6-35B-A3B, 256 experts per layer, top-8)**:

| Experiment | GPU / RAM | Published decode |
|---|---|---:|
| llama.cpp baseline, experts on CPU | RTX 5050 8 GB + 31 GB RAM | 41.05 tok/s |
| VRAM cache + load-mode none | RTX 5050 8 GB + 31 GB RAM | 52.1 tok/s |
| Hybrid CPU/GPU cache | RTX 5050 8 GB + 31 GB RAM | 55.1 tok/s |
| Hybrid, different system | RTX 5050 + Ryzen 7 7800X3D + 30 GB DDR5 | 61.5 tok/s |

The experiments page reports:

- Pre-gating layer L+1 from the output of L recovers **82%** of the next layer’s experts (96% with 16 candidates).
- LRU with 64 of 256 experts per layer in VRAM (~4.9 GB) captures **79%** of selections.
- These figures are from an RTX 5050 with 8 GB and a system with ~30 GB RAM. They are not estimates for an RTX 3050 with 4 GB.

### What it could contribute to TensorFold

**High priority — cache and placement policy**
- Compare LRU, frequency, recency, next-layer prediction, and pre-gating.
- Measure cache recall per layer and per expert, not just global hit rate.
- Reserve VRAM after subtracting dense weights, KV cache, compute buffers, and a safety margin.
- A configurable MiB limit and explicit eviction policy are preferable to allocations that compete opaquely for VRAM.

**High priority — concurrent CPU/GPU execution**
- On a cache miss, decide whether transferring the expert to GPU or running it on CPU is preferable.
- Keep the GPU busy with resident experts while the CPU handles other experts, when the graph and semantics allow it.
- Cost-based scheduler: CPU expert latency vs. PCIe transfer + GPU execution.
- Measure the actual bottleneck: CPU, PCIe bandwidth, SSD, GPU kernel, or synchronization.

**High priority — routing traces and benchmarking**
- Reproducible routing dataset for specific models, prompts, and configurations.
- Evaluate predictors by recall@K and horizon, but also by bytes read, false prefetches, VRAM occupancy, and tok/s.
- Reproduce baseline and each patch on the same llama.cpp revision.

**Medium priority — hybrid cache design**
- Investigate whether moe-anywhere’s hybrid miss path can become an independent module instead of an invasive runtime patch.
- Integrate it with TensorFold’s memory manager and the PR #1879 admission/reclaim improvements in particular.

### What it could contribute to tandem.cpp

The synergy is direct: tandem already proposes experts in RAM, GPU caching, and CPU/GPU/PCIe overlap. moe-anywhere can contribute:

- systematic evaluation of predictors and policies;
- routing traces;
- pre-gating;
- hit/miss and recall metrics;
- adaptive cache selection;
- an alternative hybrid miss path.

Integration must preserve tandem’s adaptive split and must not assume moe-anywhere’s RTX 5050 results scale linearly to an RTX 3050.

### Limitations and risks

- It is a llama.cpp laboratory, and some results require patches to specific commits.
- Results were measured with an RTX 5050 8 GB and substantially more RAM than the MSI.
- Pre-gating may preload incorrect experts; high recall does not necessarily imply throughput gains.
- The published 4.9–5.1 GiB cache does not fit the user’s 4 GiB GPU; smaller sizes and hybrid policies must be explored.

## 3. Quick comparison

| Capability | Edge0 | moe-anywhere | InferSSD | tandem.cpp |
|---|---|---|---|
| SSD streaming | Core | Not its main current focus | Core | Not core |
| Learned routing prediction | Trained prerouter | Pre-gating / experimental predictors | — | Scheduler/prefetch |
| VRAM cache | Buffers and streaming cache | Core | GPU expert cache | Core |
| CPU experts | Less central in current MLX Python framework | CPU fallback/hybrid | CPU sink | CPU execution |
| Quantization-recovery LoRA | Recover-LoRA is core | Not core | Not core | Not core |
| Routing dataset | Implicit in predictor training | Explicit roadmap | Runtime telemetry | Possible benchmarking |
| Portable backend | Modular design; platform-specific engines | llama.cpp | Own runtime/fork | llama.cpp patch |
| Direct portability to TensorFold | Algorithms, not MLX runtime | Algorithms/patches, not full runtime | I/O/cache/scheduler modules | Scheduling ideas |

## 4. Proposed TensorFold architecture

A modular experimental architecture could separate:

1. **ExpertStore**: offsets/layout index, model validation, SSD/RAM reading.
2. **ExpertCache**: RAM and VRAM levels, budget, LRU/frequency/predictive policies.
3. **RoutingPredictor**: initial heuristic pre-gating; trained predictor as an optional backend.
4. **PrefetchScheduler**: asynchronous queue, double buffering, cancellation, and priorities.
5. **PlacementScheduler**: CPU vs. GPU based on measured cost and availability.
6. **MemoryAdmission/Reclaimer**: integration with PR #1879 memory limits and recovery.
7. **Telemetry**: hit/miss, recall@K, SSD/PCIe bytes, CPU/GPU time, false prefetches, peak VRAM/RAM, tok/s, and first-token latency.
8. **Speculative interface**: UBTree/other methods as a separate module; the tree must account for additional expert and KV costs.

### Recommended experimental sequence

**Phase A — TensorFold baseline**
- Qwen3-30B-A3B-2507 with PR #1879.
- Measure loading, prefill, TTFT, decode tok/s, RAM/VRAM, errors, and stability.

**Phase B — cache/prefetch without a learned predictor**
- LRU and frequency.
- Next-layer pre-gating.
- Small cache sizes compatible with 4 GiB.
- Recall and false-prefetch metrics.

**Phase C — concurrent CPU/GPU**
- Evaluate CPU experts in parallel with GPU experts.
- Measure when transfer is slower than CPU execution.
- Incorporate admission/reclaim.

**Phase D — SSD streaming**
- If the model does not fit in RAM, stream by byte ranges and use asynchronous reads.
- Measure the MSI SSD’s actual latency and performance; do not extrapolate from PCIe 4/5.

**Phase E — trained predictor / Recover-LoRA**
- Only after sufficient traces and a robust baseline exist.
- Train and evaluate independently; preserve exact fallback behavior.

## 5. Sources

- Edge0 README: https://github.com/menonpg/edge0
- Edge0 architecture: https://github.com/Edge0-AI/Edge0/blob/main/docs/architecture.md
- Edge0 README in Spanish: https://github.com/Edge0-AI/Edge0/blob/main/README_es.md
- Edge0 technical article: https://edge0.ai/research/edge0
- moe-anywhere README and results: https://github.com/carl0sfelipe/moe-anywhere
- moe-anywhere experiments: https://github.com/carl0sfelipe/moe-anywhere/blob/main/research/experiments.md

## Conclusion

**Edge0** primarily contributes *anticipation*: learned prediction, staging, and int4 quality recovery.  
**moe-anywhere** primarily contributes *observability and scheduling*: traces, pre-gating, GPU cache, policy evaluation, and hybrid misses.  
**InferSSD** contributes *multilevel SSD/RAM/GPU streaming*.  
**tandem.cpp** contributes *concurrent CPU/GPU execution and adaptive splitting*.

The opportunity for TensorFold is to combine these ideas in its own measurable modules, without turning it into a llama.cpp or MLX fork. On the MSI, the initial goal should be to demonstrate a stable improvement with a small cache and hybrid execution before attempting SSD streaming or speculative trees.
