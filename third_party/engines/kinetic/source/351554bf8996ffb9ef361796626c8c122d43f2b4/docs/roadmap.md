# Roadmap

What we are working on next, roughly in order. Nothing here has a date;
items move when they are ready, and only after they pass the same exactness
and speed checks as everything else. Ideas and pull requests for any of them
are welcome; open an issue first so we can agree on the approach.

## Landing next

- winget and scoop packages; the manifests are in `packaging/`.

## 0.1.x: fixes

Bug fixes, new pre-tokenizers, better error messages and documentation. No
changes to the command line or the server API that break existing use.

## 0.2: next features

- **More on Vulkan.** Llama, Qwen2.5, Qwen3, LFM3 and Qwen3.5 run on AMD,
  Intel and NVIDIA GPUs through `--device vulkan`; MoE models and the other
  architectures are next.
- **Layer splits on Vulkan.** Dense models larger than the GPU split their
  layers between GPU and CPU through CUDA today (`--gpu-layers`); Vulkan is
  next.
- **Gemma 4 26B A4B, LFM2.5 MoE** and more quantization formats.
- **Block drafters for RAD-1.**
- **Shared passes everywhere.** Convoy runs on the CPU and on CUDA when the
  whole model is on the GPU; layer splits, expert offload and Vulkan are next.
- **More vision models.** Today images work with Qwen3.5 and Gemma 4 and
  their `mmproj` projectors; other projectors are next.
- **Two GPUs.** Splitting one model across two devices.

## Later

- More architectures, driven by the "model not supported" issues.
- Constrained output (`--grammar`, `--json-schema`) in `kinetic run`; it is
  in the server already.
- Split GGUF files (`-00001-of-0000N.gguf`) read directly.
- `n` greater than 1 in the server API.
- `--imatrix` for `kinetic quantize`.
- Tools to convert and sign `.ktc` files from the command line.

Kinetic supports Windows and Linux on x86-64. macOS is not on the roadmap.
