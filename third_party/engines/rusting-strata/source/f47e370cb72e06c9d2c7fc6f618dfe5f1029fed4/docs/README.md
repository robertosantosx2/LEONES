# Docs

## Guides

- [USAGE.md](USAGE.md): flags, server API, prompt caching, several GPUs.
- [HOSTING.md](HOSTING.md): running a server for other people (keys, TLS, systemd, usage log).
- [LORA.md](LORA.md): runtime LoRA / abliteration adapters.
- [SUPPORTED_GPUS.md](SUPPORTED_GPUS.md): every GPU tried so far.
- [AMD.md](AMD.md): known AMD issues and what to send in a report.

## Benchmark history

- [BENCHMARKS.md](BENCHMARKS.md): every model against llama.cpp (and other engines where measured), one table per model.

Raw results and methods, newest work last. The headline numbers are in the [README](../README.md).

- [baseline.md](baseline.md): llama.cpp baseline and `--n-cpu-moe` sweep on the RTX 3060.
- [m2-results.md](m2-results.md): GPU forward and parity.
- [m4-results.md](m4-results.md): chunked prefill.
- [m6-results.md](m6-results.md): v1.0 gate run against llama.cpp.
- [V100-results.md](V100-results.md): V100 bring-up, parity and benchmarks (long; written by `tools/bench_v100.sh`).
- [datacenter-nvidia-results.md](datacenter-nvidia-results.md): A100, A30, L40S and H100 test runs and benchmarks.
