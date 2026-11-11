# Qwen3.5-9B Feasibility on an NVIDIA RTX 3050 Laptop with 4 GiB

**Date:** 2026-11-11  
**Status:** documentary technical assessment; **NOT MEASURED**  
**Target system:** MSI Thin 15 B12UC · Intel Core i7-12650H · NVIDIA RTX 3050 Laptop 4 GiB · 14 GiB RAM · Ubuntu · driver 580.178.04 · CUDA runtime 13.0 · CUDA Toolkit 13.4  
**User environment reference:** TensorFold 1.2.3; local llama.cpp builds 0.7.0-dev/0.8.0-dev recorded in earlier inventory.

> **Executive conclusion:** Qwen3.5-9B is not a practical candidate for full residency in the RTX 3050's 4 GiB VRAM. Even a nominal 2-bit quantization takes approximately 2.1–2.3 GiB for theoretical weights alone; execution buffers, recurrent state, caches, multimodal components and headroom for the driver/desktop still have to fit. The technically plausible route is hybrid CPU+GPU execution, placing only a small fraction of layers on the GPU, **but only if the specific runtime and format support Qwen3.5-9B and its architecture**. That exact combination has not been demonstrated on this machine. The safer option, closer to the available evidence, remains Qwen3.5-4B.

## 1. Scope and evidence policy

This report answers one question: whether the official **Qwen/Qwen3.5-9B** model can run on the RTX 3050 Laptop with 4 GiB VRAM in the system described above.

Four evidence levels are kept separate:

- **SOURCE:** information published by the model or runtime project.
- **CALCULATED / ESTIMATED:** memory calculations and configuration recommendations. These are not execution measurements.
- **MEASURED:** a run using the exact model, quantization, runtime, version and hardware, with logs and telemetry.
- **UNKNOWN / NOT VERIFIED:** compatibility or behavior that cannot be inferred from a generic capability list.

No estimate is presented as a measured benchmark. As of this report, there is no attached physical Qwen3.5-9B run on this RTX 3050.

## 2. Model and architecture

The official Hugging Face model card classifies Qwen3.5-9B as a causal multimodal model with a vision encoder and lists **9B parameters** (a nominal/rounded figure), 32 layers, hidden size 4096, intermediate size 12288, vocabulary 248320 and a native context of 262144 tokens. The downloadable configuration declares `model_type=qwen3_5`, architecture `Qwen3_5ForConditionalGeneration`, `head_dim=256`, 16 attention heads, 4 KV heads and a hybrid stack of linear- and full-attention layers.

The text backbone is hybrid: three Gated DeltaNet linear-attention blocks for every full-attention block. Across 32 layers, the published pattern implies 24 linear-attention layers and 8 full-attention layers. Linear attention reduces attention cost compared with using full attention in every block, but **it does not make the model small or remove the cost of storing its weights**.

The configuration also includes a vision encoder: depth 27, hidden size 1152 and output size 4096. Therefore, a multimodal conversion or run should not be assumed to have exactly the same cost as a text-only load. Actual cost depends on whether the runtime loads the vision encoder/projector, the conversion and the inference path.

Primary sources:
- Model: https://huggingface.co/Qwen/Qwen3.5-9B
- Published configuration: https://huggingface.co/Qwen/Qwen3.5-9B/blob/main/config.json
- Qwen3.5 architecture documentation in Transformers: https://github.com/huggingface/transformers/blob/main/docs/source/en/model_doc/qwen3_5.md

## 3. Available hardware and practical limits

| Resource | System | Implication |
|---|---:|---|
| GPU | RTX 3050 Laptop, 4 GiB VRAM | Far below the capacity needed for all weights plus execution buffers |
| GPU architecture | SM 8.6 | CUDA is available; this does not automatically imply compatibility with every kernel/model |
| RAM | 14 GiB | Can host some/all weights on CPU if the format and runtime allow it, but is shared with Ubuntu and services |
| Swap | 31 GiB | Absorbs memory pressure; it is not equivalent to RAM and can make inference extremely slow |
| CPU | Intel Core i7-12650H | Enables CPU offload; speed depends on quantization, kernels, threads and memory bandwidth |
| Driver | 580.178.04 | Meets the R580+ driver requirement stated by TensorFold for its recent CUDA binaries |
| CUDA | runtime 13.0; Toolkit 13.4 | CUDA environment is installed; this does not guarantee backend support for this checkpoint |

The advertised 4 GiB is not entirely available to the model: the driver, graphical desktop, CUDA buffers and other processes consume some of it. Free memory must be measured immediately before each test with `nvidia-smi`; do not infer free VRAM from nominal capacity.

## 4. Weight-memory estimate

For quantization comparisons, use the ideal lower-bound formula:

`GiB_weights ≈ parameters_in_billions × bits_per_weight / (8 × 1.073741824)`

The official model card says 9B; for conservative planning, 9.7B is also shown as an upper sensitivity case, not as an exact count confirmed by the model card. The bit values are **theoretical average effective bits per weight**: they do not identify an actual format such as Q2_K, IQ2_XXS, Q3_K_M or a ModelOpt quantization.

| Average effective bits | 9.0B parameters | 9.7B parameters | Interpretation |
|---:|---:|---:|---|
| 2.0 | 2.10 GiB | 2.26 GiB | Extremely aggressive; potentially significant quality loss |
| 2.5 | 2.62 GiB | 2.82 GiB | Budget sensitivity case, not a guaranteed concrete format |
| 3.0 | 3.14 GiB | 3.39 GiB | Already occupies most VRAM before buffers |
| 4.0 | 4.19 GiB | 4.52 GiB | Exceeds 4 GiB for ideal weights alone |
| 5.0 | 5.24 GiB | 5.65 GiB | Does not fit in VRAM |
| 6.0 | 6.29 GiB | 6.78 GiB | Does not fit in VRAM |
| 8.0 | 8.38 GiB | 9.03 GiB | Does not fit in VRAM |

These figures are a mathematical floor, not the exact size of a downloadable file or peak VRAM. Real formats include scales, metadata, blocks, tensors that may retain higher precision, embeddings, heads and sometimes auxiliary tensors. Multimodal quantization may also treat model components differently.

### Interpretation

- **Q4:** ruled out for full GPU residency; ideal weights already exceed capacity.
- **Q3:** ruled out for full GPU residency; ideal weights use approximately 3.1–3.4 GiB and leave no operational headroom.
- **Q2.5:** should not be considered viable for full GPU residency either; theoretical weights alone take 2.6–2.8 GiB.
- **Q2 / IQ2:** the only range that might leave appreciable theoretical headroom, but it still does not prove that weights + vision + state + buffers will fit. Quality may degrade substantially and depends on the actual scheme.

## 5. Runtime memory: why weights are not enough

Actual usage consists of several components:

`VRAM_peak = GPU_weights + layer_buffers + activations + KV/SSM_state + scratch + workspace + CUDA/context + fragmentation`

For Qwen3.5, account for at least:

1. Weights placed on the GPU.
2. Temporary projection and MLP buffers.
3. Runtime-specific scratch and workspace.
4. Linear/recurrent layer state (DeltaNet) and cache for full-attention layers.
5. Prefill buffers and batch-size effects.
6. Possible vision encoder/processing.
7. CUDA context, runtime allocations and fragmentation.
8. Memory reserved by the driver and Ubuntu desktop.

This report does not assign a fixed scratch/KV/SSM value for 9B: it depends on backend, context, batch, sequence count, kernels and state precision. Giving one number without running the engine would be false precision.

The model's published 262144-token context is an architectural maximum, not a recommendation for this GPU. For a first constrained-hardware test, start with context 1024–2048, batch/parallel 1 and a small prefill, increasing only after measurement.

## 6. Quantization: Q2, Q2.5, Q3, Q4 and E-means

Q2/Q3/Q4 roughly describe precision/bit-rate families, but actual cost depends on the format. Do not confuse:

- **nominal bits** with effective bits per parameter;
- **file size** with peak VRAM;
- **model quantization** with the algorithm used to calculate centroids;
- **estimated quality** with measured quality.

E-means is a centroid-optimization method for clustering related to k-means. It is not a weight-quantization format and does not automatically create a “Q3 E-means” checkpoint. At the same bit count, block structure and encoding, E-means does not by itself reduce the memory lower bound. Only a concrete, published and validated quantization can justify a quality/memory comparison.

Therefore, “2.5 bits” in this report is a mathematical sensitivity column, not a recommendation to download a guaranteed Q2.5 file. Selecting an artifact requires its repository, format, license, actual size, quantization metadata and runtime compatibility.

## 6.1. E-means vs. K-means: implications for Qwen3.5-9B quantization

This section expands the quantization comparison to prevent an incorrect conclusion: **E-means and K-means cannot be considered equivalent in quality for Qwen3.5-9B weights unless concrete quantized artifacts are generated and evaluated**.

### What each method optimizes

- **K-means** groups values (for example, weight blocks or vectors) around centroids and minimizes the within-cluster sum of squared distances through centroid assignment and update steps.
- **E-means** is a centroid-optimization method related to k-means that uses *exponential moving average* (EMA)-style updates in a mini-batch scheme. Its main goal is to accelerate convergence toward a low-loss clustering solution; it does not by itself define a quantization format, bit width or weight encoding.

The paper **“e-means: outperforming k-means (in one-tenth the epochs)”** reports a median 12.6× reduction in epochs to reach Lloyd K-means loss after 25 epochs, across 234 configurations and 16 datasets ranging from 100,000 to 100 million points. These results concern clustering optimization; **they are not an LLM quantization evaluation, do not measure Qwen perplexity and do not prove quality equivalence between E-means- and K-means-quantized weights**.

Sources:
- Paper: https://arxiv.org/abs/2611.09501
- FAISS reference implementation: https://github.com/facebookresearch/faiss/tree/main/contrib/e_means

### Are they equivalent in quality?

There is insufficient evidence to claim that 3-bit E-means quantization matches 3-bit K-means quantization, or that fewer-bit E-means matches higher-bit K-means, on Qwen3.5-9B. Faster convergence or lower clustering loss does not by itself guarantee lower functional error in the model.

Final quality depends on, among other factors:
- which tensors are quantized and which remain at higher precision;
- grouping by tensor, channel, group or block;
- block size and number of centroids;
- actual effective bits, scales, indices and metadata;
- treatment of outliers and sensitive weights;
- calibration, representative data and subsequent fine-tuning;
- runtime kernel implementation and dequantization behavior.

If centroid/code count, effective bits, block structure and index representation are identical, the centroid-search method **does not by itself change the theoretical memory budget**. E-means may find useful centroids in fewer iterations or improve the clustering objective, but model-quality equivalence must be measured separately.

### TensorFold implications

Do not assume TensorFold 1.2.3 includes E-means as a quantizer, automatically accepts artifacts produced with FAISS, or that its CUDA backend can directly execute any externally generated codebook. E-means would, in principle, be part of the weight preparation/calibration process; TensorFold would still need to recognize the resulting format and provide compatible loading and execution kernels.

Before attributing support to TensorFold, verify:
1. exported format and centroid/index storage specification;
2. conversion of all required tensors, including embeddings and sensitive layers;
3. TensorFold parser and backend kernels for that format;
4. actual artifact size and peak load/inference memory;
5. numerical accuracy and functional quality against a comparable baseline.

### Recommended comparison protocol

To test the hypothesis on Qwen3.5-9B, produce two artifacts from the same checkpoint with identical settings: one using K-means and one using E-means. Keep effective bits, groups, centroid count, excluded tensors, calibration and auxiliary precision identical. Compare:

- weight and activation reconstruction error;
- perplexity on a fixed evaluation set;
- reasoning, knowledge, coding and instruction-following tasks;
- generation stability, repetition and multimodal degradation if vision is evaluated;
- on-disk size, resident memory, peak VRAM and speed in the same runtime.

Add a second rate-distortion comparison (for example, lower-bit E-means against higher-bit K-means) only after establishing the equal-budget result. Record versions, hashes, calibration data and commands for every run.

**Operational conclusion:** E-means is a promising alternative for accelerating or optimizing the clustering stage of quantization, but it is not accurate to label it “same quality as K-means” for Qwen3.5-9B. This report currently contains no E-means-quantized Qwen3.5-9B artifact validated in TensorFold and no measured comparison. Keep the status as **NOT MEASURED / NOT VERIFIED** until the protocol above is run.

## 7. Runtime compatibility: demonstrated vs. unproven

### TensorFold

The user has TensorFold 1.2.3 installed. The 1.2.2/1.2.3 line introduced Qwen3.5 support along different backend paths, but the release notes distinguish backend and format: the 1.2.2 release notes Qwen3.5-9B on the Metal engine derived from the 27B engine; 1.2.3 mentions Qwen3.5 BF16 on HIP/rocBLAS. This **does not demonstrate Qwen3.5-9B on CUDA on an RTX 3050**.

A generic `qwen3_5` capability or the fact that TensorFold starts with CUDA is not enough to conclude that every Qwen3.5 checkpoint, quantization and size is supported. A recipe must name exactly:
- TensorFold release/commit;
- Qwen3.5-9B family and size;
- checkpoint format and origin;
- CUDA backend;
- GPU architecture;
- context and memory reserve;
- actual run with logs and telemetry.

### PR #1879 — CUDA lazy scratch

The user's earlier TensorFold PR #1879 work addresses a real allocation issue: avoiding reservation of maximum Qwen3.5 scratch at startup and growing it on demand. The recorded local validation was 322/322 build steps and 113/113 host CUDA tests. The user also reported a specific Qwen3.5-4B CUDA validation.

This is evidence of a memory-management path correction and validation of the documented 4B case. **It does not prove** that 9B fits in 4 GiB, that 9B is enabled on CUDA, or that CPU/GPU offload exists for that checkpoint. More efficient reservation does not change weight size.

References:
- PR: https://github.com/ashhart/TensorFold/pull/1879
- Releases: https://github.com/ashhart/TensorFold/releases
- Repository: https://github.com/ashhart/TensorFold

### llama.cpp

llama.cpp documents hybrid CPU+GPU inference and quantization from 1.5 to 8 bits. That makes partial offload conceptually suitable for a GPU smaller than the model. However, general runtime capability does not prove that the user's local version correctly supports Qwen3.5-9B and the specific GGUF. Upstream documentation shows Qwen3.5 in its execution flow and the project has general CPU+GPU hybrid support; before recommending an exact command, verify model/architecture support in the local commit and that a compatible 9B GGUF exists.

The user's previous inventory records local builds 0.7.0-dev and 0.8.0-dev. Verify the exact commit, `llama-cli --version` output, tensor types and successful model load. Do not assume the local branch has the same capabilities as current upstream.

Reference: https://github.com/ggml-org/llama.cpp

## 8. Feasibility matrix

| Scenario | Feasibility on RTX 3050 4 GiB | Status |
|---|---|---|
| 9B Q4 fully on GPU | No | Ruled out by theoretical weights |
| 9B Q3 fully on GPU | Not practical | Ruled out by lack of headroom |
| 9B Q2.5 fully on GPU | Not recommended | Theoretical weights leave insufficient headroom |
| 9B Q2/IQ2 fully on GPU | Very unlikely/not demonstrated | Requires measurement; do not assume |
| 9B CPU-only | Possible in principle | Depends on format, available RAM and runtime; speed unmeasured |
| 9B partial CPU+GPU | Experimental candidate | Requires explicit runtime support and exact validation |
| 9B TensorFold CUDA 1.2.3 | Unconfirmed | No demonstrated 9B CUDA recipe for this GPU |
| 9B TensorFold Metal | Not applicable | Apple Silicon backend, not RTX |
| 9B llama.cpp GGUF hybrid | Conditional candidate | Verify GGUF/architecture in local build |
| Qwen3.5-4B CUDA | Best starting point | User has prior work and validation with PR #1879; do not extrapolate its figures to 9B |

## 9. Recommendation for this MSI

**Primary recommendation: do not spend time trying to load Qwen3.5-9B entirely into the RTX 3050.** If the goal is to experiment with 9B, use a hybrid CPU+GPU test in llama.cpp only after confirming that the local build recognizes the architecture and GGUF. If the goal is reliable local CUDA execution under tight memory limits, continue with Qwen3.5-4B first and complete its context, prefill and peak-VRAM tests.

Recommended order:

1. **Baseline:** capture free VRAM, available RAM, swap and GPU processes before startup.
2. **Verify artifact:** identify repository, file, actual effective quantization, metadata, license and hash.
3. **Verify backend:** confirm exact Qwen3.5-9B + format + CUDA or CPU/GPU hybrid support in the local version.
4. **CPU-only control:** if supported by the runtime, run a short test to validate loading/tokenization and RAM usage.
5. **Conservative hybrid:** batch 1, context 1024, prefill 32–64 and few GPU layers; measure before increasing offload.
6. **Scale up:** context 2048 and more GPU layers only if there is no OOM and RAM/swap remain within limits.
7. **Quality:** compare the quantization with a higher-precision baseline using fixed prompts and reproducible evaluation.
8. **Benchmark:** measure TTFT, prompt tokens/s, generation tokens/s, peak VRAM, peak RSS, swap, power and stability over multiple repetitions.

Do not disable the runtime memory reserve to force startup. The reserve protects the process from exhausting VRAM; reducing it can be an experimental variable, not a solution to weight size.

## 10. Reproducible validation plan

Before downloading or starting a model:

```bash
nvidia-smi
free -h
swapon --show
df -h "$HOME"
```

Record versions:

```bash
nvidia-smi
nvcc --version
command -v llama-cli || true
llama-cli --version 2>&1 || true
```

For every run, preserve:
- exact model name and repository URL;
- model revision/commit;
- filename and SHA-256;
- actual on-disk size;
- format and quantization metadata;
- runtime, version, commit and backend;
- complete arguments;
- context, batch, ubatch, GPU layers, threads and sequence count;
- `nvidia-smi` before/during/after;
- peak RSS, free memory, swap and elapsed time;
- exact prompt, input/output tokens and TTFT/PP/TG metrics;
- exit code and full log.

A run is **MEASURED** only if it completes and the record attributes the result to this machine and this exact combination. A partial startup, a compilation test or a run on another GPU does not count as a measurement of 9B on this MSI.

## 11. Risks and stop conditions

Stop the test if:
- OOM occurs or the process enters repeated allocation/retry loops;
- available RAM falls to a level that threatens Ubuntu;
- swap grows rapidly and the system begins to stall;
- other graphical applications share VRAM and free memory is insufficient;
- the runtime does not explicitly recognize the architecture or ignores tensors;
- the model produces corrupt output, NaNs, repetition loops or state errors;
- quantization origin/license/metadata cannot be verified.

Do not use swap as a substitute for VRAM for interactive inference: it may keep the process alive, but does not guarantee usable performance.

## 12. Final verdict

**Can Qwen3.5-9B run on a 4 GiB RTX 3050 Laptop?**

- **Entirely on GPU:** not practical; Q3/Q4 exceed the budget even under ideal weight calculations, and Q2 leaves no guaranteed room for buffers or state.
- **CPU-only:** technically possible if a compatible format exists and system RAM is sufficient, but speed has not been measured.
- **CPU+GPU:** the most reasonable experimental route, provided the runtime explicitly supports Qwen3.5-9B and the selected format. llama.cpp provides general hybrid infrastructure, but the exact version and GGUF must be validated.
- **TensorFold 1.2.3 CUDA:** do not treat 9B as supported on the RTX 3050 based on generic Qwen3.5 support, PR #1879 or support on other backends.
- **Recommended option:** Qwen3.5-4B for local CUDA; 9B as a hybrid CPU+GPU experiment, not as a full-VRAM deployment.

**LEONES status:** ESTIMATED / SOURCE REVIEW. No physical Qwen3.5-9B benchmark on this machine. Do not publish tokens/s, peak VRAM or quality as measured results until the validation plan is completed.

## Sources

1. Qwen, official Qwen3.5-9B model: https://huggingface.co/Qwen/Qwen3.5-9B
2. Qwen, official configuration: https://huggingface.co/Qwen/Qwen3.5-9B/blob/main/config.json
3. Hugging Face Transformers, Qwen3.5 architecture: https://github.com/huggingface/transformers/blob/main/docs/source/en/model_doc/qwen3_5.md
4. TensorFold, releases: https://github.com/ashhart/TensorFold/releases
5. TensorFold, PR #1879: https://github.com/ashhart/TensorFold/pull/1879
6. llama.cpp, project and documentation: https://github.com/ggml-org/llama.cpp
7. LEONES hardware profile: `hardware/UBUNTU-MSI-THIN-15-B12UC.md`

---
**Maintenance note:** update this report when a reproducible 9B run is available on the MSI or when the runtime publishes an explicit Qwen3.5-9B + CUDA/CPU-offload recipe for the installed version.
