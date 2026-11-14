# Atomic Chat + TensorFold native-runtime spike

This proof of concept checks whether the installed TensorFold Native CLI can be supervised as a child process and consumed through the same local HTTP shape Atomic Chat uses for native runtimes.

## Requirements

- Linux x86_64 + NVIDIA CUDA.
- Python 3 standard library only (no pip packages).
- TensorFold Native 1.2.3 (or a compatible build).
- A model checkpoint already downloaded and supported by the installed TensorFold build.

The reference machine has TensorFold Native 1.2.3 installed at `~/.local/opt/tensorfold-1.2.3-linux-x86_64/bin/tensorfold-native`; its release archive checksum was verified. Historical inference is already proven on this RTX 3050 with TensorFold 1.1.1 and the experimental PR #1879 build (see the evidence report below). The current 1.2.3 binary and the current rebased PR #1879 head still need a fresh receipt through this PoC.

The script does not install software, download models, edit Atomic Chat settings, or touch any pre-existing server. It first runs `tensorfold-native info MODEL` to inspect the exact local checkpoint and report TensorFold's documented memory floor (weights plus a generic 2 GiB runtime margin). That floor is an estimate, not a measured peak: LEONES has historical RTX 3050 receipts where Qwen3.5-4B completed inference even though a later binary's `info` floor was 4.85 GiB. The PoC therefore blocks by default if the floor exceeds free VRAM, but supports an explicit `TENSORFOLD_ALLOW_INFO_FLOOR_OVERCOMMIT=1` override for an already-tested exact model/version/GPU profile. The independent 3072 MiB free-VRAM guard remains mandatory and cannot be bypassed by that override. Never use the override for an unqualified model. `info` is not proof that every family/format has a CUDA implementation; native CUDA `serve` remains authoritative. The script selects a free loopback port, starts only the child process it owns, checks the API, and terminates that child.

## Run

From this directory:

```bash
python3 poc.py /absolute/path/to/an/already-downloaded/model
```

For a cached Hugging Face repository ID, pass the exact ID if the installed TensorFold CLI can resolve it locally.

Optional environment (the 3072 MiB free-VRAM guard remains mandatory; the info-floor override is only for a previously tested exact profile):

```bash
TENSORFOLD_BIN="$HOME/.local/opt/tensorfold-1.2.3-linux-x86_64/bin/tensorfold-native" \
TENSORFOLD_CONTEXT=2048 \
TENSORFOLD_TIMEOUT=300 \
python3 poc.py /path/to/model
```

## What it checks

1. `tensorfold-native --version`.
2. `tensorfold-native capabilities --json`.
3. Run `tensorfold-native info MODEL` without loading weights; reject a checkpoint the CLI cannot inspect. Treat its generic weights-plus-runtime floor as advisory. If it exceeds free VRAM, block by default; an explicit overcommit override is permitted only for an already-tested exact model/version/GPU profile.
4. Verify CUDA capability and a configurable minimum free-VRAM floor (default 3072 MiB), then launch with argv (no shell), loopback bind, a dynamically selected port, explicit CUDA backend and update checks disabled.
5. `GET /health`.
6. `GET /v1/models`.
7. `POST /v1/chat/completions` in normal and SSE streaming modes.
8. Child-only shutdown, with SIGKILL fallback after a grace period.

## Offline checks

The PoC helper tests use only Python's standard library and do not start TensorFold, allocate VRAM or download a model:

```bash
python3 -m py_compile poc.py tests/test_poc.py
python3 -m unittest discover -s tests -v
```

The LEONES pull request also runs these checks in GitHub Actions on changes to this experiment. A green CI result validates the helper code only; it does not replace the live CUDA/model/API acceptance test.

## Interpretation

A pass proves only that this TensorFold binary/model combination exposes the tested local API. It does not yet prove Atomic Core integration, GPU arbitration, model catalog compatibility, tool calling, vision, structured output, embeddings, or cross-platform support. The script intentionally does not claim those capabilities.

## Latest upstream and checkpoint audit

See [historical RTX 3050 inference evidence (2026-11-06)](../../research/atomic-chat-tensorfold-historical-rtx3050-evidence-2026-11-06.md) for measured Qwen3.5-2B/4B runs on this GPU and the matched baseline-vs-PR-#1879 result. The current 1.2.3 binary still needs a fresh receipt: historical success on 1.1.1 and the old PR #1879 build does not prove the current rebase head or 1.2.3 baseline.

## Reference-machine evidence

- [TensorFold Native 1.2.3 installation and capability record](evidence/tensorfold-1.2.3-install-and-capabilities-2026-11-05.md)
- [Atomic Core integration contract map](../../research/atomic-chat-tensorfold-core-contracts-2026-11.md)
- [Atomic Chat app integration map](../../research/atomic-chat-tensorfold-app-contracts-2026-11.md)
