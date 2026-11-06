# TensorFold 1.2.3: checkpoint eligibility for the 4 GiB RTX 3050 reference host

Date: 2026-11-06  
Scope: source/recipe compatibility review only. No model was downloaded, loaded or run.

## Important correction: capabilities are not a per-checkpoint CUDA guarantee

The captured `capabilities --json` reports formats as a family-level union. The upstream Qwen3.5-2B recipe explicitly warns that `families.qwen3_5` is a union across multiple engines/geometries, and that the listed formats do not all load at every geometry.

The exact checkpoint `mlx-community/Qwen3.5-2B-MLX-4bit` at revision `93760be4f1f69842a46bc13dbdc0f19e291392a3` is documented in a **native Metal preview recipe**, but a review of the current upstream `main` README and changelog corrects the earlier interpretation: Qwen3.5-2B also has a native CUDA serving path. The README lists its machine scope as one Mac (M5 Max checked) or one GB10 and labels the CUDA release checks; the changelog records Qwen3.5-2B serving on CUDA (#836). The same upstream sources do **not** document an RTX 3050 / sm_86 serving receipt for this checkpoint. Thus it is not Metal-only, but its published CUDA qualification is insufficient to call it supported on this 4 GiB laptop.

The Qwen3.5 EXL3 documentation also distinguishes the native engine from the historical Python CUDA engine and records format/family-specific limitations. In v1.2.3, its native-CUDA section says `qwen3_5` serves EXL3 packs of Qwen3.5 **MoE** models and Qwen3.8-27B; it does not document the dense Qwen3.5-4B checkpoint. The upstream changelog further says the 2B geometry admits only `mlx-q4g64` (#2139), so its CUDA path does not make an arbitrary EXL3 2B pack valid. Do not treat an EXL3 repository, or a family-level `exl3` capability, as proof that an arbitrary dense Qwen3.5 checkpoint can be served by the v1.2.3 native CUDA engine.

## Other inspected small-family candidates

- `XHToken/Spark-X2.6-4B` has a native CUDA recipe, but the recorded 8-bit run reports 9.47 GiB model memory on an RTX 5090. The recipe's 4-bit conversion is explicitly lower fidelity and has no 4 GiB RTX 3050 qualification.
- `Aleph-Alpha/Kolibri-1` is native CUDA but its tested checkpoint is 74 GB; clearly unsuitable for the reference GPU.
- Qwen3.5-4B EXL3 community checkpoints surfaced in model discovery are not accepted as a candidate without a matching v1.2.3 native-CUDA recipe, a format-specific family check, and a memory-floor calculation.

## Safe conclusion

At this point there is **no live receipt for the currently installed TensorFold Native 1.2.3 binary on the reference RTX 3050**. This is not the same as saying the GPU has never run TensorFold: LEONES records Qwen3.5-2B and Qwen3.5-4B inference on this exact card with TensorFold 1.1.1, and a matched baseline-vs-PR-#1879 experiment where the baseline OOMed but the PR build completed three Qwen3.5-4B inferences. See [historical RTX 3050 evidence](atomic-chat-tensorfold-historical-rtx3050-evidence-2026-11-06.md).

Therefore:
1. Qwen3.5-2B MLX 4-bit is historically proven on this RTX 3050 with TensorFold 1.1.1 (context 1024; 95.08–105.71 tok/s). That historical receipt does not qualify the currently installed 1.2.3 binary or a newer rebase head. Use it as a known historical reference, not as an untested 1.2.3 claim.
2. Qwen3.5-4B dense MLX-4bit is historically proven on this RTX 3050 with TensorFold 1.1.1 and the experimental PR #1879 build. The current 1.2.3 `info` output (4.85 GiB generic floor) is not a measured peak and must not erase those receipts. However, the matched baseline at a later commit did fail with CUDA OOM; prefer a validated build containing the lazy-scratch fix. The v1.2.3 EXL3 CUDA statement still does not admit arbitrary dense 4B EXL3 checkpoints.
3. Do not use the Spark-X2.6-4B or Kolibri-1 recipes as a 4 GiB smoke-test model.
4. For Atomic Chat, target the already-cached Qwen3.5-4B revision `32f3e8ecf65426fc3306969496342d504bfa13f3`, context 512, parallel 1, using the user's current rebased PR #1879 build after code gates pass.
5. Treat `info`'s weights-plus-2-GiB floor as advisory, not a measured VRAM peak. Keep the independent 3072 MiB free-VRAM guard mandatory; any explicit floor override is limited to the exact historical model/version/GPU profile.
6. Never stop the existing `llama-server` automatically to create headroom.

This does not invalidate the integration architecture or offline PoC tests. It means the first real inference receipt must use a different, genuinely supported and small-enough CUDA checkpoint, or a machine with more VRAM.

## Source references

- Qwen3.5-2B native Metal recipe: https://github.com/ashhart/TensorFold/blob/v1.2.3/docs/recipes/qwen3.5-2b-native.md
- TensorFold EXL3 support status: https://github.com/ashhart/TensorFold/blob/v1.2.3/docs/recipes/exl3.md
- Native CUDA recipe book: https://github.com/ashhart/TensorFold/blob/v1.2.3/docs/recipes/cuda.md
- Spark-X2.6-4B native CUDA recipe: https://github.com/ashhart/TensorFold/blob/v1.2.3/docs/recipes/spark-x2.6-4b-cuda.md
- Kolibri-1 native CUDA recipe: https://github.com/ashhart/TensorFold/blob/v1.2.3/docs/recipes/kolibri-1.md


## Local checkpoint inspection: Qwen3.5-4B MLX 4-bit (2026-11-06)

The user ran the exact non-loading inspection command on the Ubuntu reference host:

```text
$ tensorfold-native info mlx-community/Qwen3.5-4B-MLX-4bit
family: Qwen3.5-2B or Qwen3.8-27B (qwen3_5)
format: 4-bit, group 64
weights: 2.85 GiB (3061131350 bytes)
memory floor: 4.85 GiB (weights plus a 2.00 GiB runtime margin)
```

This is an observed `info` result, not a model-load or inference test. The reported 4.85 GiB floor exceeds the reference GPU's 4 GiB physical VRAM by at least 0.85 GiB even with an otherwise idle GPU. The user's latest prior GPU snapshot also had only about 1.35 GiB free because the pre-existing `llama-server` process occupied approximately 2.7 GiB. Do not stop or signal that process.

The family description is ambiguous (`Qwen3.5-2B or Qwen3.8-27B`) and does not identify this checkpoint as a supported dense Qwen3.5-4B native-CUDA geometry. Thus the inspection independently disqualifies it on memory, while leaving CUDA format compatibility unproven. Keep it out of the real-inference PoC. Do not attempt to start it on this host.

The result confirms the memory-floor guard is useful: it should reject this checkpoint before server startup. Preserve the 3072 MiB free-VRAM guard as an additional independent safety check.


## Expanded native-CUDA candidate audit (2026-11-06)

The v1.2.3 recipe book and native CUDA registry were checked for smaller families beyond the initial Qwen/Spark/Kolibri shortlist. No additional safe chat-generation checkpoint was qualified for the 4 GiB RTX 3050.

| Candidate | What v1.2.3 actually supports | Decision for this PoC |
| --- | --- | --- |
| `LiquidAI/LFM3-1.7B-MLX-4bit` | The LFM3 page is explicitly a host-side metadata/layout bring-up. It says it does not register a serving engine and text generation/image input are not implemented or qualified. | Not an inference candidate, despite the small parameter count. |
| `LiquidAI/d1-3B` | The LFM2 CUDA open path is for d1's decision model. Its loader requires the checkpoint's own BF16 weights and quantizes nothing at load; the public README describes dedicated `/v1/systemone` and `/v1/decisions` APIs, not general chat completions. | Not a general Atomic Chat text-generation candidate. Its BF16 3B weights also do not provide a plausible 4 GiB fit; do not download or load it for this PoC. |
| Dory (`model_type: dory`) | Native CUDA registry entry, but the v1.2.3 source's pinned config is a 72-sublayer, hidden-size-2560 model with ModelOpt NVFP4 group-16 weights (or other explicitly admitted formats). | Large architecture, not a small-model candidate for a 4 GiB laptop GPU. No 4 GiB qualification. |
| Qwen3.5-2B MLX 4-bit | Native CUDA serving exists (#836); current upstream README's documented CUDA machine scope is one GB10. The 2B geometry admits only `mlx-q4g64` (#2139). No RTX 3050/sm_86 serving receipt is documented. | Legitimate CUDA-path candidate, but not qualified on this 4 GiB RTX 3050; exact local `info` floor is still unknown. |
| Qwen3.5-4B MLX 4-bit (user's inspected checkpoint) | `info` reports 2.85 GiB weights and a 4.85 GiB memory floor; family string is ambiguous and no dense-4B native CUDA receipt is documented. | Fails the physical VRAM floor and remains format/geometry-unqualified. |

The source-level native CUDA registry also contains families whose documented checkpoints are far beyond this machine (for example, 30B-class Nemotron, 24B-class Spark-X2.6, 27B-class Qwen/Dory and larger models). A registry entry is not evidence that a small quantized derivative is admitted.

### Result

There is no v1.2.3 checkpoint that currently satisfies all three necessary conditions for the reference machine:

1. A native CUDA serving path in this exact release.
2. A model/checkpoint contract that is explicitly admitted by that path and exposes ordinary text chat generation.
3. A reported checkpoint memory floor that fits the actual GPU budget with the PoC's safety margin.

Do not start another model load on the reference host on the basis of parameter count or family-level capabilities. The next useful action is either to qualify a different machine with more VRAM against an explicitly supported checkpoint, or wait for a smaller native CUDA family/checkpoint to be implemented and documented upstream. The Atomic Chat integration remains a valid architecture/adapter research effort, but its live TensorFold runtime gate stays blocked.

### Additional source references

- LFM3 native bring-up (explicitly no serving engine): https://github.com/ashhart/TensorFold/blob/v1.2.3/docs/recipes/lfm3-native.md
- Native CUDA registry and family boundaries: https://github.com/ashhart/TensorFold/blob/v1.2.3/docs/recipes/cuda.md
- LFM2/d1 CUDA family config (BF16 weights, d1 decision model): https://github.com/ashhart/TensorFold/blob/v1.2.3/zig/src/families/lfm2/config.zig
- Dory CUDA config (72 sublayers, hidden size 2560, quantization constraints): https://github.com/ashhart/TensorFold/blob/v1.2.3/zig/src/families/dory/config.zig
- Native CUDA Dory registry/open path: https://github.com/ashhart/TensorFold/blob/v1.2.3/zig/src/native/cuda.zig


## Dory 1.0 4B NVFP4: exact public checkpoint-size cross-check (2026-11-06)

A further check of NVIDIA's official Hugging Face repository identifies `nvidia/NVIDIA-Nemotron-Labs-Dory1.0-4B-NVFP4` as a 4B NVFP4 checkpoint. Its repository reports a 3.2 GB `model.safetensors` file (about 2.98 GiB), with the full repository about 3.22 GB.

This makes Dory an especially clear rejection for the 4 GiB reference GPU even before considering its large recurrent architecture and runtime/KV allocations: applying TensorFold's documented 2.00 GiB runtime margin to the weight-file size gives a rough lower-bound estimate of about **4.98 GiB**, already above physical VRAM. This is a size-based estimate, not a locally observed `tensorfold-native info` result; no Dory files were downloaded and no process was started.

The public v1.2.3 CUDA registry does list Dory, but the registry explicitly does not qualify every checkpoint, format, GPU or rank count. The official Dory NVFP4 model is therefore not a safe exception to the no-model-load decision.

Sources:
- Official NVIDIA Dory NVFP4 model card and architecture: https://huggingface.co/nvidia/NVIDIA-Nemotron-Labs-Dory1.0-4B-NVFP4
- Official checkpoint file listing and size: https://huggingface.co/nvidia/NVIDIA-Nemotron-Labs-Dory1.0-4B-NVFP4/tree/main
- TensorFold v1.2.3 native CUDA registry and qualification caveat: https://github.com/ashhart/TensorFold/blob/v1.2.3/docs/recipes/cuda.md


## Upstream clarification: Qwen3.5-2B has a CUDA path, but not an RTX 3050 qualification (2026-11-06)

A fresh review of the current upstream `main` README, recipe index and changelog found that the earlier “Metal-only” wording for Qwen3.5-2B was too broad:

- The current README's model table lists Qwen3.5-2B MLX 4-bit as usable on one Mac (M5 Max checked) or one GB10, and links “CUDA release checks”.
- The changelog records Qwen3.5-2B and Qwen3.8-27B serving on CUDA through the native server (#836).
- The CUDA Qwen family reads mixed-width MLX checkpoints (2–8 bits per module, group size 64).
- The current changelog's geometry clarification says Qwen3.5-2B admits only `mlx-q4g64` (#2139).
- The published machine scope for the Qwen3.5-2B checkpoint is GB10, not RTX 3050 / sm_86. The CUDA registry and presence of sm_86 fatbins are not a per-model/per-GPU serving receipt.

This changes the candidate classification from “not a CUDA candidate” to “valid native CUDA path, but only publicly qualified on GB10 for the listed checkpoint; not yet qualified on the reference laptop”. The checkpoint is approximately 1.72 GB on Hugging Face, so its eventual TensorFold `info` memory floor may be close to the laptop's 4 GiB capacity; the exact floor must be measured locally before any launch. The 3072 MiB free-VRAM guard remains mandatory, and the existing `llama-server` must not be stopped to create room.

No model was downloaded or started during this documentation review.

Additional sources:
- https://github.com/ashhart/TensorFold/blob/main/README.md#qualified-models
- https://github.com/ashhart/TensorFold/blob/main/CHANGELOG.md
- https://github.com/ashhart/TensorFold/blob/main/docs/recipes/qwen3.5-2b-native.md
- https://huggingface.co/mlx-community/Qwen3.5-2B-MLX-4bit


## Historical RTX 3050 evidence reconciliation (2026-11-06)

The preceding sections assess the installed 1.2.3 binary and upstream support metadata. They must not be read as a statement that TensorFold has never run on the reference GPU.

LEONES contains measured TensorFold 1.1.1 CUDA inference for:
- Qwen3.5-2B MLX 4-bit, context 1024: 95.08 and 105.71 tok/s; TTFT 88.2 and 94.1 ms; about 2,388 MiB process VRAM.
- Qwen3.5-4B MLX 4-bit, context 512: 53.64 and 53.42 tok/s; TTFT 193 and 212 ms; about 3,120 MiB process VRAM.

It also contains a matched RTX 3050 baseline-vs-PR-#1879 experiment with Qwen3.5-4B at the same checkpoint revision, context, parallelism and 0.5 GiB reserve. The baseline failed at cuMemAlloc with CUDA_ERROR_OUT_OF_MEMORY; the PR build loaded in 10.4 seconds and completed three HTTP 200 chat requests at 54.32–56.05 tok/s. The observed global GPU peak was 3,227 MiB used. This confirms a functional load/admission advantage for that tested PR build; it does not quantify exact scratch bytes saved or qualify the current rebase head.

The current 1.2.3 info floor of 4.85 GiB is weights plus a generic 2 GiB runtime margin. It is not a measured peak. It must remain a warning and a useful candidate-comparison metric, not a categorical proof that this previously successful checkpoint cannot run.

Full evidence: [historical RTX 3050 inference reconciliation](atomic-chat-tensorfold-historical-rtx3050-evidence-2026-11-06.md).
