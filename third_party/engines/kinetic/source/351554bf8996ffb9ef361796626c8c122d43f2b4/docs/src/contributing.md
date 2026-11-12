# Contributing

Bug reports, benchmarks on your hardware, fixes and new model support are all
welcome. The short version of the rules is in
[CONTRIBUTING.md](https://github.com/Veloresearch/kinetic/blob/main/CONTRIBUTING.md);
this chapter explains how the code fits together and walks through the two
most common contributions: a new architecture and a new weight format.

For anything larger than a small fix, open an issue first so we can agree on
the approach. The [good first issues](https://github.com/Veloresearch/kinetic/labels/good%20first%20issue)
are a good place to start.

## How the code is laid out

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="diagrams/architecture-dark.svg">
  <img src="diagrams/architecture-light.svg" alt="Kinetic in six layers: terminal, server and libraries on top; RAD-1, Warm Start, Zero Wait and Convoy, each switchable with --off; model families Qwen3.5, Gemma, LFM, Llama and a new family, one file each; shared blocks attention, delta-net, mamba2, short-conv and MoE; devices CPU, CUDA and Vulkan; GGUF and .ktc files" width="100%">
</picture>
</p>

| Crate | Holds |
|---|---|
| `kinetic-gguf` | the GGUF reader: header, metadata, memory-mapped tensors |
| `kinetic-quant` | `TensorType` and the scalar reference dequantization of every format: the definition the fast kernels are tested against |
| `kinetic-cpu` | AVX2 kernels: matrix-vector products per format, norms, rotary embeddings, the thread pool |
| `kinetic-models` | the shared blocks (`blocks/`), the architectures built from them (`arch/`), the CUDA executor (`cuda/`), speculative decoding (`speculative/`), Warm Start (`warm/`), Shortlist (`head/`) |
| `kinetic-cuda` | the CUDA driver API, the kernels (`cuda/*.cuh`) and their launchers |
| `kinetic-tokenizer` | BPE, SentencePiece and WordPiece tokenizers read from GGUF metadata |
| `kinetic-grammar` | GBNF and JSON Schema to a token mask |
| `kinetic-vision` | image encoders (`mmproj` files) |
| `kinetic-ktc` | the `.ktc` format: reader, writer, verification |
| `kinetic-server` | the engine (chat template, sampling, tool calls) and the HTTP server |
| `kinetic-cli` | the `kinetic` command |
| `kinetic`, `kinetic-capi` | the Rust and C libraries; `bindings/python` builds on `kinetic` |

## What every change must keep

- **Exactness.** Anything that speeds up decoding must give the same tokens
  as plain decoding. In practice this means a batch of tokens must produce,
  bit for bit, the logits those tokens produce one at a time. The identity
  tests below check it; a change that breaks them is not mergeable, however
  fast.
- **Own code.** No code copied from other inference engines. Reading
  llama.cpp's sources to understand a format or an architecture is fine and
  expected; tables and grids of a format are data, and their source goes
  into `NOTICE`.
- **No network.** Kinetic never connects to the network, except when you
  run `kinetic pull`. Nothing else may open a connection.
- **Small files with one job**, doc comments on public items, comments only
  where the reason is not obvious, `unsafe` only at FFI, SIMD and kernel
  boundaries with a `// SAFETY:` comment.
- **Numbers for speed claims**: model, hardware, command, before and after,
  best of several runs.

## Adding an architecture

[Adding a model family](adding-a-family.md) walks through it: a scaffold
script, the blocks and what each covers, mapping GGUF tensors, the family
descriptor, the conformance check against llama.cpp and the identity gates.

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="diagrams/add-a-family-dark.svg">
  <img src="diagrams/add-a-family-light.svg" alt="Five steps from left to right: scaffold from a GGUF, map its tensors to blocks in one file, add one line to the registry, check conformance against llama.cpp, open a pull request" width="100%">
</picture>
</p>


## Adding a weight format or a kernel

Every format is defined once, by its reference dequantization, and every
fast kernel is tested against that definition.

1. **The type.** `crates/kinetic-quant/src/types.rs`: the GGUF type id,
   elements and bytes per block, and the name.
2. **The definition.** A block decoder in `crates/kinetic-quant/src/dequant/`,
   wired into `dequantize`. Straightforward scalar code; this is what "correct"
   means for the format. Lookup grids go in `grids/` with their source noted
   in `NOTICE`.
3. **The CPU kernel.** A dot product against 8-bit activations in
   `crates/kinetic-cpu/src/kdot/`, with an AVX2 version where it pays.
   `kdot/tests.rs` compares every kernel with the reference on random
   blocks. Until a kernel exists, `matvec` falls back to dequantizing rows,
   so a new format works on the CPU from step 2 on.
4. **The CUDA kernel.** A GEMV in `crates/kinetic-cuda/cuda/`, its entry in
   `WEIGHT_TYPES` (`src/gemv.rs`) and its field layout (`src/layout.rs`),
   tested in `tests/gemv_quants.rs` against the reference and an f64 dot
   product, alone and batched. Expert kernels for mixture-of-experts models
   are separate (`src/moe.rs`, `tests/moe.rs`).
5. **The docs.** The format table in [Models and formats](models.md).

Batched kernels must give each row exactly what the single-row kernel gives.
That is what keeps speculative decoding and Warm Start exact; the GEMV tests
check it.

## Sign your work

Kinetic uses the [Developer Certificate of Origin](https://developercertificate.org)
(DCO) 1.1. By adding a `Signed-off-by` line to a commit you certify that you
wrote the change or otherwise have the right to submit it under the
project's license:

```sh
git commit -s -m "models: add lfm2"
```

Pull requests with unsigned commits cannot be merged. To sign commits you
already made, run `git rebase --signoff main` and force-push your branch.

Kinetic is licensed under the Apache License 2.0, and contributions are
accepted under the same license.
