# Atomic Chat + TensorFold native-runtime spike

This proof of concept checks whether the installed TensorFold Native CLI can be supervised as a child process and consumed through the same local HTTP shape Atomic Chat uses for native runtimes.

## Requirements

- Linux x86_64 + NVIDIA CUDA.
- Python 3 standard library only (no pip packages).
- TensorFold Native 1.2.3 (or a compatible build).
- A model checkpoint already downloaded and supported by the installed TensorFold build.

The reference machine has TensorFold Native 1.2.3 installed at `~/.local/opt/tensorfold-1.2.3-linux-x86_64/bin/tensorfold-native`. The release archive checksum was verified. Only version and capability discovery have been validated so far; model inference has not yet been run.

The script does not install software, download models, edit Atomic Chat settings, or touch any pre-existing server. It checks that the binary declares CUDA and that GPU 0 has at least 3072 MiB free by default before loading a model. This is a safety floor, not a guarantee that the checkpoint will fit. It selects a free loopback port, starts only the child process it owns, checks the API, and terminates that child.

## Run

From this directory:

```bash
python3 poc.py /absolute/path/to/an/already-downloaded/model
```

For a cached Hugging Face repository ID, pass the exact ID if the installed TensorFold CLI can resolve it locally.

Optional environment (the VRAM floor can be raised; lowering it is an explicit risk acceptance):

```bash
TENSORFOLD_BIN="$HOME/.local/opt/tensorfold-1.2.3-linux-x86_64/bin/tensorfold-native" \
TENSORFOLD_CONTEXT=2048 \
TENSORFOLD_TIMEOUT=300 \
python3 poc.py /path/to/model
```

## What it checks

1. `tensorfold-native --version`.
2. `tensorfold-native capabilities --json`.
3. Verify CUDA capability and a configurable minimum free-VRAM floor (default 3072 MiB), then launch with argv (no shell), loopback bind, a dynamically selected port, explicit CUDA backend and update checks disabled.
4. `GET /health`.
5. `GET /v1/models`.
6. `POST /v1/chat/completions` in normal and SSE streaming modes.
7. Child-only shutdown, with SIGKILL fallback after a grace period.

## Offline checks

The PoC helper tests use only Python's standard library and do not start TensorFold, allocate VRAM or download a model:

```bash
python3 -m py_compile poc.py tests/test_poc.py
python3 -m unittest discover -s tests -v
```

The LEONES pull request also runs these checks in GitHub Actions on changes to this experiment. A green CI result validates the helper code only; it does not replace the live CUDA/model/API acceptance test.

## Interpretation

A pass proves only that this TensorFold binary/model combination exposes the tested local API. It does not yet prove Atomic Core integration, GPU arbitration, model catalog compatibility, tool calling, vision, structured output, embeddings, or cross-platform support. The script intentionally does not claim those capabilities.


## Reference-machine evidence

- [TensorFold Native 1.2.3 installation and capability record](evidence/tensorfold-1.2.3-install-and-capabilities-2026-11-05.md)
- [Atomic Core integration contract map](../../research/atomic-chat-tensorfold-core-contracts-2026-11.md)
- [Atomic Chat app integration map](../../research/atomic-chat-tensorfold-app-contracts-2026-11.md)
