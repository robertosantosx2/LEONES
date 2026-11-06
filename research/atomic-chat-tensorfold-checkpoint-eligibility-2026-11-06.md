# TensorFold 1.2.3: checkpoint eligibility for the 4 GiB RTX 3050 reference host

Date: 2026-11-06  
Scope: source/recipe compatibility review only. No model was downloaded, loaded or run.

## Important correction: capabilities are not a per-checkpoint CUDA guarantee

The captured `capabilities --json` reports formats as a family-level union. The upstream Qwen3.5-2B recipe explicitly warns that `families.qwen3_5` is a union across multiple engines/geometries, and that the listed formats do not all load at every geometry.

The exact checkpoint `mlx-community/Qwen3.5-2B-MLX-4bit` at revision `93760be4f1f69842a46bc13dbdc0f19e291392a3` is documented as a **native Metal preview**. Its recipe explicitly says there is no native Qwen3.5-2B backend on CUDA/non-Apple platforms. It must not be selected for the Linux CUDA PoC merely because the capability JSON contains `qwen3_5` and `mlx-q4g64`.

The Qwen3.5 EXL3 documentation also distinguishes the native engine from the historical Python CUDA engine and records format/family-specific limitations. Do not treat an EXL3 repository, or a family-level `exl3` capability, as proof that an arbitrary dense Qwen3.5 checkpoint can be served by the v1.2.3 native CUDA engine.

## Other inspected small-family candidates

- `XHToken/Spark-X2.6-4B` has a native CUDA recipe, but the recorded 8-bit run reports 9.47 GiB model memory on an RTX 5090. The recipe's 4-bit conversion is explicitly lower fidelity and has no 4 GiB RTX 3050 qualification.
- `Aleph-Alpha/Kolibri-1` is native CUDA but its tested checkpoint is 74 GB; clearly unsuitable for the reference GPU.
- Qwen3.5-4B EXL3 community checkpoints surfaced in model discovery are not accepted as a candidate without a matching v1.2.3 native-CUDA recipe, a format-specific family check, and a memory-floor calculation.

## Safe conclusion

At this point there is **no verified, supported, memory-qualified TensorFold Native 1.2.3 checkpoint for the reference RTX 3050 Laptop GPU with 4 GiB VRAM**.

Therefore:
1. Do not launch Qwen3.5-2B MLX 4-bit on this Linux CUDA binary.
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
