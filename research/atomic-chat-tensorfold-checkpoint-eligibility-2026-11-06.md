# TensorFold 1.2.3: checkpoint eligibility for the 4 GiB RTX 3050 reference host

Date: 2026-11-06  
Scope: source/recipe compatibility review only. No model was downloaded, loaded or run.

## Important correction: capabilities are not a per-checkpoint CUDA guarantee

The captured `capabilities --json` reports formats as a family-level union. The upstream Qwen3.5-2B recipe explicitly warns that `families.qwen3_5` is a union across multiple engines/geometries, and that the listed formats do not all load at every geometry.

The exact checkpoint `mlx-community/Qwen3.5-2B-MLX-4bit` at revision `93760be4f1f69842a46bc13dbdc0f19e291392a3` is documented as a **native Metal preview**. Its recipe explicitly says there is no native Qwen3.5-2B backend on CUDA/non-Apple platforms. It must not be selected for the Linux CUDA PoC merely because the capability JSON contains `qwen3_5` and `mlx-q4g64`.

The Qwen3.5 EXL3 documentation also distinguishes the native engine from the historical Python CUDA engine and records format/family-specific limitations. In v1.2.3, its native-CUDA section says `qwen3_5` serves EXL3 packs of Qwen3.5 **MoE** models and Qwen3.8-27B; it does not document the dense Qwen3.5-4B checkpoint. The separate Qwen3.5-2B recipe is Metal-only. Do not treat an EXL3 repository, or a family-level `exl3` capability, as proof that an arbitrary dense Qwen3.5 checkpoint can be served by the v1.2.3 native CUDA engine.

## Other inspected small-family candidates

- `XHToken/Spark-X2.6-4B` has a native CUDA recipe, but the recorded 8-bit run reports 9.47 GiB model memory on an RTX 5090. The recipe's 4-bit conversion is explicitly lower fidelity and has no 4 GiB RTX 3050 qualification.
- `Aleph-Alpha/Kolibri-1` is native CUDA but its tested checkpoint is 74 GB; clearly unsuitable for the reference GPU.
- Qwen3.5-4B EXL3 community checkpoints surfaced in model discovery are not accepted as a candidate without a matching v1.2.3 native-CUDA recipe, a format-specific family check, and a memory-floor calculation.

## Safe conclusion

At this point there is **no verified, supported, memory-qualified TensorFold Native 1.2.3 checkpoint for the reference RTX 3050 Laptop GPU with 4 GiB VRAM**.

Therefore:
1. Do not launch Qwen3.5-2B MLX 4-bit on this Linux CUDA binary.
2. Do not assume the cached Qwen3.5-4B dense MLX checkpoint can run via native CUDA or EXL3; v1.2.3's EXL3 CUDA statement covers Qwen3.5 MoE, not that dense checkpoint.
2. Do not use the Spark-X2.6-4B or Kolibri-1 recipes as a 4 GiB smoke-test model.
3. Keep the real-inference step blocked until a specific native CUDA checkpoint is found and its exact family/format/geometry plus `tensorfold-native info` memory floor are checked.
4. Preserve the 3072 MiB free-VRAM PoC preflight. Never stop the existing `llama-server` automatically to create headroom.

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
| Qwen3.5-2B MLX 4-bit | Explicit native Metal preview; the recipe says there is no native Qwen3.5-2B backend on CUDA/non-Apple platforms. | Not supported on this Ubuntu CUDA path, regardless of memory. |
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
