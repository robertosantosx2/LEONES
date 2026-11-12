# Changelog

All notable changes to Kinetic are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
the rules in [Versioning](https://veloresearch.github.io/kinetic/versioning.html).

## [Unreleased]

### Models

- Gemma 4 (`gemma4`) on the CPU and CUDA, with images through its `gemma4v`
  projector.
- LFM2.5 mixture of experts (`lfm2moe`), experimental, on the CPU and CUDA,
  with experts kept in system memory when they do not fit the GPU.

## [0.1.0] - 2026-11-05

The first public release.

### Command line

- `kinetic run`, `chat`, `serve`, `bench`, `info` and `verify`.
- Common llama.cpp flags work unchanged (`-m`, `-p`, `-n`, `-c`, `-t`, `-s`,
  `--temp`, `-ngl`, `-dev` and others); the ones Kinetic does not need are
  explained instead of rejected.
- `kinetic bench` runs llama-bench's pp512 and tg128 tests, plus an edit test
  that checks drafted output against plain decoding.

### Server

- OpenAI-compatible `/v1/chat/completions`, `/v1/completions`, `/v1/models`
  and `/v1/health`, with streaming, stop strings, seeds, tool calls,
  `response_format` (JSON and JSON Schema), GBNF grammars and reasoning output.
- `/v1/embeddings` for embedding models and `/v1/rerank` for rerankers.
- Images for Qwen3.5 with its `mmproj` projector.
- Listens on 127.0.0.1 by default and refuses requests from web pages.

### Models

- Architectures: `qwen35`, `qwen35moe`, `lfm3`, `lfm2`, `llama`, `qwen2`,
  `qwen3`, `gemma3`, `ernie4_5`, `hunyuan-dense`, `exaone4`, `olmo2`,
  `granite`, `granitehybrid`, `granitemoe`, `falcon-h1`, `bert`, `nomic-bert`
  and `gemma-embedding`, and decoder embedding and reranking models built on
  them.
- Every GGUF weight type in common use: F32, F16, BF16, the legacy and
  K-quants, the IQ formats, TQ1_0, TQ2_0 and MXFP4.
- The `.ktc` format, version 1: one file with weights, tokenizer, chat
  template and a hashed manifest, optionally signed with Ed25519.

### Devices

- x86-64 CPUs, with AVX2 kernels.
- NVIDIA GPUs from Turing (RTX 20 series) on, through CUDA. The driver is
  loaded at runtime, so the CUDA build also starts on machines without one.
- Mixture-of-experts models larger than GPU memory (Flywheel).

### Speed

- RAD-1: speculative decoding that is exact and automatic, drafting from the
  context, from earlier requests and from a model's own multi-token
  prediction block.
- Warm Start: prompts that begin like an earlier one resume from its exact
  state, in memory and on disk.
- Shortlist: exact top tokens without reading the whole output layer.

### Libraries

- Python package `kinetic`, C API (`kinetic.h`, `kinetic_capi`) and the Rust
  crate `kinetic`.
- Release archives for Windows and Linux, CPU and CUDA, and Dockerfiles.

[Unreleased]: https://github.com/Veloresearch/kinetic/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Veloresearch/kinetic/releases/tag/v0.1.0
