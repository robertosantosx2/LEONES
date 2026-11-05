# Atomic Chat + TensorFold native-runtime spike

This proof of concept checks whether the installed TensorFold Native CLI can be supervised as a child process and consumed through the same local HTTP shape Atomic Chat uses for native runtimes.

## Requirements

- Linux x86_64 + NVIDIA CUDA.
- Python 3 standard library only (no pip packages).
- TensorFold Native 1.2.0 (or a compatible build).
- A model checkpoint already downloaded and supported by the installed TensorFold build.

The script does not install software, download models, edit Atomic Chat settings, or touch any pre-existing server. It selects a free loopback port, starts only the child process it owns, checks the API, and terminates that child.

## Run

From this directory:

```bash
python3 poc.py /absolute/path/to/an/already-downloaded/model
```

For a cached Hugging Face repository ID, pass the exact ID if the installed TensorFold CLI can resolve it locally.

Optional environment:

```bash
TENSORFOLD_BIN="$HOME/.local/opt/tensorfold-1.2.0-linux-x86_64/bin/tensorfold-native" \
TENSORFOLD_CONTEXT=2048 \
TENSORFOLD_TIMEOUT=300 \
python3 poc.py /path/to/model
```

## What it checks

1. `tensorfold-native --version`.
2. `tensorfold-native capabilities --json`.
3. Launch with argv (no shell), loopback bind and a dynamically selected port.
4. `GET /health`.
5. `GET /v1/models`.
6. `POST /v1/chat/completions` in normal and SSE streaming modes.
7. Child-only shutdown, with SIGKILL fallback after a grace period.

## Interpretation

A pass proves only that this TensorFold binary/model combination exposes the tested local API. It does not yet prove Atomic Core integration, GPU arbitration, model catalog compatibility, tool calling, vision, structured output, embeddings, or cross-platform support. The script intentionally does not claim those capabilities.
