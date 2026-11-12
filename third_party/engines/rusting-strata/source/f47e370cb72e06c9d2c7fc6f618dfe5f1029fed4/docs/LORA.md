# RustingStrata LoRA Abliteration

Runtime LoRA abliteration support for RustingStrata: an abliteration adapter is applied to the base model **without requantizing or baking a new file**; base GGUF weights on disk are never modified and memory uses F32 arithmetic (lossless equivalent of `W + B·A·scale` on resident tensors).

## Why it works (research basis)

Abliteration via LoRA is a **rank-1, closed-form** weight edit, not a fine-tune. The refusal direction `d` is extracted from residual-stream activations and written into LoRA factors:
`B = d`, `A = -α·dᵀW`. In GGUF adapter form (llama.cpp semantics), targets are the **residual writers** — `attn.o_proj`, per-expert `down_proj`, shared-expert `down_proj`, `ssm_out`, `ple_value`. Folding `scale`/`alpha` into `A` means runtime application `y += scale·(B·A)·x` matches baked output exactly (no re-quantization needed; the only information step is base dequantization to F32, which is also exact for F32 comparisons).

## Usage

```
rustingstrata.exe generate --model MODEL.gguf --lora ADAPTER.gguf:1.0 --prompt "..." -n 50
rustingstrata.exe serve --model MODEL.gguf --lora ADAPTER.gguf:1.0 --addr 127.0.0.1:8080 --ctx 32768
rustingstrata.exe chat --model MODEL.gguf --lora ADAPTER.gguf:1.0
```

`--lora` takes `path:scale` (repeatable) at the top level so `generate`/`chat`/`serve`/`bench`/`perplexity`/`score` apply it. `calibrate` accepts it for consistency but always calibrates the base model. Scale defaults to `1.0`; with `n_expert == 1` an adapter applies to every routed expert slot. Missing adapter targets warn (`lora: target … not found, skipping`). Graph capture (`CUDA graph` / Vulkan conditional) is bypassed for LoRA decode forwards.

## Two application paths (both lossless)

- **Baked (non-expert tensors).** `attn_output`, `ssm_out`, `ple_value`, and the shared-expert `ffn_down_shexp` are dequantized to F32 **once at load** and `scale·(B·A)` is added in F32, then stored as F32 `Weights::built` overrides. CPU and GPU read these modified weights identically; oven-resume is a no-op for them.
- **Runtime (routed experts).** `ffn_down_exps` stays quantized in memory (to avoid materializing huge F32 expert matrices). Routed expert down LoRA is applied on the fly in `Model::ffn` (CPU) and in `GpuModel::apply_lora_gpu_down` (GPU): `y += Σ_e w_e · Σ_r b_r·(a_r·act_e)`. The GPU path reads expert identity from `ids` (misses filtered via `slots < 0`) and dequantizes Q8 packed activations (`ffq`) to F32 for quantized down weights; float-typed down weights read post-SwiGLU `ge`. The correction is added to the residual (`x`/`mo`) **before** `hc_write` so hyper-connection models keep it. A per-layer mark makes Vulkan `finish`/resume replay skip layers that already got the correction. Prefill uses the step path when LoRA is present (`pf=None`).

## Verification status

- Unit/integration tests green (`cargo test --release --lib`, `--test model`, `--test gpu_model`, `--test cpu_moe`).
- Reported audit found and fixed: Vulkan resume double-apply, baked-tensor growth on model switch (the F32 copies are owned by `Weights` and freed on reload; synthesized `ssm_beta`/`ssm_alpha` are preserved), LoRA calibration poisoning (calibration is skipped for LoRA runs so tuning stays clean), stale help text, Windows `path:scale` parsing, `alpha/rank` scaling, single-expert fan-out.

## Limits

- LoRA and MTP/speculative decode together: LoRA disables graph capture (used, not errors). Batched prefill is bypassed under LoRA (step path), which is slower but numerically consistent with decode.
- KLD against llama.cpp requires per-backend numeric parity outside LoRA math; LoRA application itself is exactly reproducible by design (`W + scale·B·A`).
