# TensorFold MoE Forensic Analysis — RTX 3050 Laptop 4 GiB

- **Case date:** 2026-10-24
- **Repository:** robertosantosx2/LEONES
- **Status:** memory-admission rejection before inference; no tokens or performance measurements were obtained.
- **Engine:** tensorfold-native 1.1.3
- **Host:** MSI Thin 15 B12UC, Ubuntu, NVIDIA GeForce RTX 3050 Laptop GPU with 4 GiB VRAM.
- **Evidence status:** This report documents observed commands, console output, local log identities, and a capability audit. The original host-side logs have now been copied into the repository with SHA-256 checksums. The earlier console transcripts are retained separately and must not be confused with the original files.

## 1. Executive conclusion

Two startup attempts were captured with TensorFold native 1.1.3:

1. **NVIDIA Nemotron 3.5 Lightning 30B-A3B**, model `TensorFold/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-MLX-4bit`. TensorFold reported 16.6 GiB of weights and rejected startup because the effective CUDA budget was 2.6 GiB (3.6 GiB detected as free minus a 1.0 GiB reserve). Exit code: 1.
2. **Qwen3.6-35B-A3B**, model `TensorFold/Qwen3.6-35B-A3B-MLX-4bit-MTP`. `tensorfold info` reported 19.47 GiB (20,904,564,068 bytes) of weights and a 21.47 GiB memory floor. The `serve` command reported 19.0 GiB of weights (rounded) against the same 2.6 GiB CUDA budget. Exit code: 1.

Both processes exited on their own within seconds. Neither reached inference. The memory rejection happened before an API server became available; it is neither a throughput result nor evidence of an out-of-memory failure during generation.

**Strict LEONES conclusion:** the measured result is a CUDA-memory-budget admission rejection. Functional execution of either model on this 4 GiB RTX 3050 has not been demonstrated. This does not prove that either model is generally incompatible with TensorFold, nor does it prove that the engine has no internal offload mechanism.

## 2. Environment identity

| Field | Observed value |
|---|---|
| Host | MSI Thin 15 B12UC |
| CPU | Intel Core i7-12650H |
| Logical CPUs | 16 |
| Operating system | Ubuntu |
| Kernel reported in earlier inventory | `7.0.0-38-generic` |
| Physical RAM | 14 GiB |
| GPU | NVIDIA GeForce RTX 3050 Laptop GPU |
| VRAM | 4096 MiB / 4 GiB |
| NVIDIA driver | 580.178.04 |
| CUDA reported by nvidia-smi | 13.0 |
| TensorFold | tensorfold-native 1.1.3 |
| Binary SHA-256 | `a51ec99fa4f87ab12bd48261e1c1cbeb1e7b51f72755a71d4a7eda89712ff671` |
| Executable | `/home/ssantos/tensorfold-1.1.3-check.aOKPG0/tensorfold-1.1.3-linux-x86_64/bin/tensorfold-native` |
| Graphics process | Xorg, PID 5911 |
| VRAM used before Qwen attempt | 15 MiB; Xorg accounted for 4 MiB in the process table |
| Available RAM before Qwen serve | 2.3 GiB |
| Swap used before Qwen serve | 7.7 GiB of 31 GiB |

The version and binary hash match the shared records for Nemotron, Qwen info, Qwen serve, and the capability audit.

### 2.1 Host memory before and after Qwen serve

Literal `free -h` output before the attempt:

    total       used       free  shared  buff/cache  available
    Mem:            14Gi        12Gi       463Mi       874Mi       3.1Gi       2.3Gi
    Swap:           31Gi       7.7Gi        24Gi

Output afterwards:

    total       used       free  shared  buff/cache  available
    Mem:            14Gi        12Gi       738Mi       887Mi       3.1Gi       2.6Gi
    Swap:           31Gi       7.7Gi        24Gi

The source console labelled the swap row “Inter”; the values are reproduced here in conventional English terminology for readability. The process exited quickly, and there is no evidence of sustained weight loading.

### 2.2 Incorrect path ruled out

An earlier attempt used `$HOME/.local/opt/tensorfold-1.1.3-check.aOKPG0/...`, which did not exist. That was a path error, not a TensorFold or checkpoint failure. The documented tests used the correct path under `$HOME/tensorfold-1.1.3-check.aOKPG0/`.

## 3. Evidence A — Nemotron 3.5 Lightning 30B-A3B

### 3.1 Identity, configuration, and timing

- Model: `TensorFold/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-MLX-4bit`
- Service name: `nemotron-forensic`
- Host: `127.0.0.1`
- Port: `18089`
- Requested backend: `auto`
- Parallelism: 1
- Context: 512
- Temperature: 0
- Thinking: disabled with `--no-thinking`
- Start: `2026-10-24T21:45:53,499655019+02:00`
- End: `2026-10-24T21:45:58,572657071+02:00`
- Approximate duration: 5.073 seconds
- Recorded exit code: 1
- Preflight log: [`nemotron-1.1.3-preflight.log`](artifacts/tensorfold-moe-forensic-2026-10-24/nemotron-1.1.3-preflight.log)
- Startup log: [`nemotron-1.1.3-context512.log`](artifacts/tensorfold-moe-forensic-2026-10-24/nemotron-1.1.3-context512.log)

The script recorded the label `timeout_exit_code=1`. Although the command was wrapped in a timeout, the timeout did not expire: the program exited by itself with code 1.

### 3.2 Exact startup command

    /home/ssantos/tensorfold-1.1.3-check.aOKPG0/tensorfold-1.1.3-linux-x86_64/bin/tensorfold-native serve \
      TensorFold/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-MLX-4bit \
      --name nemotron-forensic \
      --host 127.0.0.1 \
      --port 18089 \
      --backend auto \
      --parallel 1 \
      --context 512 \
      --temperature 0 \
      --no-thinking

### 3.3 Captured error, verbatim

    tensorfold: the checkpoint's 16.6 GiB of weights do not fit the 2.6 GiB the CUDA memory budget grants (3.6 GiB free less a 1.0 GiB reserve); free device memory or adjust TENSORFOLD_MEMORY_RESERVE_GIB / TENSORFOLD_CUDA_MEMORY_LIMIT_GB

### 3.4 Interpretation

The message states:
- Weights: 16.6 GiB.
- Detected free CUDA memory: 3.6 GiB.
- Reserve: 1.0 GiB.
- Resulting budget: 2.6 GiB.
- Approximate shortfall relative to the reported weights: 14.0 GiB.

The server never became available. No HTTP requests, tokens, tokens per second, TTFT, or generation-quality results were recorded.

### 3.5 Other historical Nemotron commands

These earlier commands also appeared in the history:

    "$TF" serve TensorFold/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-MLX-4bit --name nemotron-moe --parallel 1 --context 2048 --temperature 0 --no-thinking

    "$TF" serve TensorFold/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-MLX-4bit \
      --name nemotron-moe-113 --host 127.0.0.1 --port 18089 --backend auto \
      --parallel 1 --context 512 --temperature 0 --no-thinking

The complete original error for those earlier attempts is not available in this case record. They must not be confused with the controlled capture at 21:45:53.

## 4. Evidence B — Qwen3.6-35B-A3B checkpoint inspection

### 4.1 Identity and info command

- Model: `TensorFold/Qwen3.6-35B-A3B-MLX-4bit-MTP`
- Timestamp: `2026-10-24T21:48:59,552050510+02:00`
- Version: `tensorfold-native 1.1.3`
- Binary SHA-256: `a51ec99fa4f87ab12bd48261e1c1cbeb1e7b51f72755a71d4a7eda89712ff671`
- Log: [`qwen36-info-1.1.3.log`](artifacts/tensorfold-moe-forensic-2026-10-24/qwen36-info-1.1.3.log)
- Info exit code: 0.

Recorded command:

    TF="$HOME/tensorfold-1.1.3-check.aOKPG0/tensorfold-1.1.3-linux-x86_64/bin/tensorfold-native"
    OUT="$HOME/tensorfold-forensic-20261024"
    MODEL="TensorFold/Qwen3.6-35B-A3B-MLX-4bit-MTP"
    "$TF" info "$MODEL"

### 4.2 Info output

    family: qwen3_5_moe (qwen3_5_moe)
    format: 4-bit, group 64
    weights: 19.47 GiB (20904564068 bytes)
    memory floor: 21.47 GiB (weights plus a 2.00 GiB runtime margin)
    info_exit_code=0

Previously reported local snapshot path:

    /home/ssantos/.cache/huggingface/hub/models--TensorFold--Qwen3.6-35B-A3B-MLX-4bit-MTP/snapshots/f84b054c5677b6e59bdb969ae61915b0983d68bb

The earlier inventory estimated about 20 GiB in cache and reported four safetensors shards plus `mtp-4bit.safetensors`, configuration, tokenizer, and index. Individual shard hashes were not recorded in this case; therefore, no cryptographic verification of each checkpoint file is claimed.

An `info_exit_code=0` confirms that checkpoint metadata could be inspected. It does not mean the weights were loaded or that inference works.

## 5. Evidence C — Qwen3.6-35B-A3B controlled startup

### 5.1 Parameters and timing

- Start: `2026-10-24T21:50:01,153166636+02:00`
- End: `2026-10-24T21:50:03,917760790+02:00`
- Approximate duration: 2.765 seconds
- Service name: `qwen36-forensic`
- Host: `127.0.0.1`
- Port: `18090`
- Backend: `auto`
- Parallelism: 1
- Context: 256
- Temperature: 0
- Thinking: disabled
- Exit code: 1
- Log: [`qwen36-1.1.3-serve-context256.log`](artifacts/tensorfold-moe-forensic-2026-10-24/qwen36-1.1.3-serve-context256.log)

### 5.2 Exact command

    /home/ssantos/tensorfold-1.1.3-check.aOKPG0/tensorfold-1.1.3-linux-x86_64/bin/tensorfold-native serve TensorFold/Qwen3.6-35B-A3B-MLX-4bit-MTP --name qwen36-forensic --host 127.0.0.1 --port 18090 --backend auto --parallel 1 --context 256 --temperature 0 --no-thinking

The run was wrapped by:

    timeout --signal=INT --kill-after=5s 30s \
      "$TF" serve "$MODEL" \
      --name qwen36-forensic \
      --host 127.0.0.1 \
      --port 18090 \
      --backend auto \
      --parallel 1 \
      --context 256 \
      --temperature 0 \
      --no-thinking

Result:

    serve_exit_code=1

The process exited after about 2.76 seconds; it did not run out the 30-second timeout.

### 5.3 Full error, verbatim

    tensorfold: the checkpoint's 19.0 GiB of weights do not fit the 2.6 GiB the CUDA memory budget grants (3.6 GiB free less a 1.0 GiB reserve); free device memory or adjust TENSORFOLD_MEMORY_RESERVE_GIB / TENSORFOLD_CUDA_MEMORY_LIMIT_GB

The serve message rounds the weights to 19.0 GiB; `info` reported 19.47 GiB. This is a display-precision difference, not evidence of different checkpoints.

### 5.4 GPU before and after

Before:
- NVIDIA-SMI 580.178.04; driver 580.178.04; CUDA 13.0.
- RTX 3050, 4096 MiB total.
- 15 MiB used; GPU utilization 9%; 44 °C.
- Xorg PID 5911: 4 MiB.

After:
- NVIDIA-SMI 580.178.04; driver 580.178.04; CUDA 13.0.
- RTX 3050, 4096 MiB total.
- 15 MiB used; GPU utilization 0%; 44 °C.
- Xorg PID 5911: 4 MiB.

This is consistent with an early rejection rather than sustained weight loading.

## 6. Evidence D — TensorFold 1.1.3 capability audit

### 6.1 Timestamp, file, and command

- Timestamp: `2026-10-24T21:51:22,680971026+02:00`
- Log: [`offload-capability-audit.log`](artifacts/tensorfold-moe-forensic-2026-10-24/offload-capability-audit.log)

Command:

    TF="$HOME/tensorfold-1.1.3-check.aOKPG0/tensorfold-1.1.3-linux-x86_64/bin/tensorfold-native"
    OUT="$HOME/tensorfold-forensic-20261024"
    {
      echo "===== DATE ====="
      date --iso-8601=ns
      echo "===== SERVE HELP ====="
      "$TF" serve --help 2>&1
      echo "===== CAPABILITIES ====="
      "$TF" capabilities --json 2>&1
      echo "===== MEMORY AND OFFLOAD OPTIONS IN BINARY ====="
      strings "$TF" |
        grep -Ei 'offload|cpu.?memory|host.?memory|memory.?budget|TENSORFOLD_MEMORY_RESERVE_GIB|TENSORFOLD_CUDA_MEMORY_LIMIT_GB|TF_CUDA_SEGMENTS|segments' |
        sort -u
    } 2>&1 | tee "$OUT/offload-capability-audit.log"

### 6.2 Observed serve help

    usage: tensorfold serve [-h] [--host HOST] [--port PORT] [--name NAME] [--chat-template FILE] [--alias ALIAS] [--allowed-host NAME] [--allowed-origin ORIGIN] [--api-key API_KEY] [--api-key-file API_KEY_FILE] [--metrics-open] [--dashboard] [--context CONTEXT] [--speed-up SETTINGS] [--prompt-cache-gib PROMPT_CACHE_GIB] [--prompt-cache-over-cap] [--learn] [--learn-dir LEARN_DIR] [--learn-gib LEARN_GIB] [--learn-conversations] [--learn-daily-gib LEARN_DAILY_GIB] [--recall] [--recall-dir RECALL_DIR] [--recall-gib RECALL_GIB] [--recall-read-only] [--max-tokens MAX_TOKENS] [--temperature TEMPERATURE] [--top-p TOP_P] [--top-k TOP_K] [--min-p MIN_P] [--prompt-seed] [--thinking | --no-thinking] [--reasoning-effort {low,medium,high,xhigh}] [--thinking-budget THINKING_BUDGET] [--thinking-reserve THINKING_RESERVE] [--loop-guard] [--no-drafts] [--drafter DRAFTER] [--drafter-bits {0,4}] [--record RECORD] [--keep-warm SECONDS] [--compact-at COMPACT_AT] [--compact-keep COMPACT_KEEP] [--compact-memory COMPACT_MEMORY] [--slide] [--slide-graph SLIDE_GRAPH] [--parallel PARALLEL] [--cortheon] [--no-update-check] [--backend {auto,mlx,cuda}] [--device DEVICE] [--segments SEGMENTS] model

The displayed help does not show an obvious general `--cpu-offload` or `--offload` option for the main weights. This observation alone does not prove that every internal offload implementation is absent.

### 6.3 Relevant capability JSON fields

The output reported the Zig engine, version 1.1.3, chip `nvidia-sm86`, backend `cuda`, and the following relevant families/formats:

    {
      "schema": 1,
      "engine": "zig",
      "version": "1.1.3",
      "chip": "nvidia-sm86",
      "backends": ["cuda"],
      "families": {
        "nemotron_h": ["mlx-q4g64", "modelopt-nvfp4", "modelopt-ggml"],
        "nemotron_h_omni": ["mlx-q4g64", "modelopt-nvfp4", "modelopt-ggml"],
        "qwen3_5": ["mlx-q4g64"],
        "qwen3_5_moe": ["mlx-q4g64"]
      },
      "env": [
        "TENSORFOLD_API_KEY",
        "TENSORFOLD_NO_LIVE",
        "TENSORFOLD_SEED_SALT",
        "TENSORFOLD_REQUEST_LOG",
        "TENSORFOLD_NO_UPDATE_CHECK",
        "HF_HOME",
        "HF_HUB_CACHE",
        "HF_HUB_OFFLINE",
        "BRAVE_SEARCH_API_KEY",
        "TF_CUDA_DEVICE",
        "TF_CUDA_SEGMENTS",
        "TENSORFOLD_CUDA_KERNELS",
        "TENSORFOLD_MEMORY_RESERVE_GIB",
        "TENSORFOLD_CUDA_MEMORY_LIMIT_GB"
      ]
    }

The full JSON listed additional families, flags, and optional libraries. For this investigation, the relevant entries are the Nemotron-H family, Qwen3.5 MoE family, and memory-related environment variables. A family/format appearing in the capability list does not prove that a particular checkpoint fits in the GPU or that loading will complete.

The output also reported:
- cuBLASLt and cuBLAS found; actual use undetermined.
- NCCL not found.
- RDMA verbs found.
- TensorFold video / `libtfvideo.so` not found.
- libjpeg-turbo found but marked unusable because the resolver could not use `libturbojpeg.so.0`.
- libwebp not found.
- TensorFold grammar / `libtfgrammar.so` found; use undetermined.
- RCCL not found.
- MCDMA RPC and MCDMA fabric not found.

There is no evidence linking these optional libraries to the observed weight-budget errors.

### 6.4 Memory environment variables

The error messages name:
- `TENSORFOLD_MEMORY_RESERVE_GIB`
- `TENSORFOLD_CUDA_MEMORY_LIMIT_GB`

The earlier audit recorded these variables as empty or unset in the inspected environment. The error reports an effective reserve of 1.0 GiB.

Changing these variables alters the program's logical budget; it does not increase physical VRAM. Do not set the CUDA limit above actual VRAM or remove the reserve without justification: passing the initial check does not guarantee that weights, KV cache, buffers, and workspace fit in the real allocation.

### 6.5 Relevant internal strings

Strings extracted from the binary included:

    HostMemoryUnavailable
    BadSegments
    InvalidQwenSegments
    --segments
    TF_CUDA_SEGMENTS=
    TENSORFOLD_MEMORY_RESERVE_GIB
    TENSORFOLD_CUDA_MEMORY_LIMIT_GB
    the checkpoint's  GiB of weights do not fit the  GiB the CUDA memory budget grants
    the CUDA memory budget fits no stream beside the model
    the CUDA memory budget fits no stream
    Pinned host memory the engine holds now: staging buffers and windows; only where the backend counts it (CUDA).
    --slide runs a prompt one chunk at a time, its change's scratch shared by every layer: serve it without --segments or TF_CUDA_SEGMENTS
    --vision-offload

Caveats:
- `strings` extracts internal strings; it is not a complete interface specification and does not prove that every code path is active.
- `HostMemoryUnavailable` does not reveal exactly which host-memory functions are available.
- `--segments` must not be interpreted as weight offload. The `--slide` string refers to chunking prompt processing and scratch memory.
- `--vision-offload` appeared in binary strings but not in the copied normal `serve` help; it must not be treated as language-weight offload.
- No documented general CPU-offload option for the main weights was found in the displayed help.

### 6.6 Reference to an older Python engine

Another internal string said:

    is not served by the native engine; the Python engine 0.6.6 serves it:
    python -m pip install git+https://github.com/ashhart/TensorFold.git@v0.6.6

This is a generic internal message. It does not prove that these checkpoints require that version or that the Python engine can run them with 14 GiB RAM and 4 GiB VRAM. The Python engine was not installed or tested in this session.

## 7. Quantitative comparison

| Metric | Nemotron 3.5 Lightning | Qwen3.6 |
|---|---:|---:|
| Weights reported by serve | 16.6 GiB | 19.0 GiB |
| Weights from info | not preserved in shared output | 19.47 GiB |
| Info memory floor | not preserved in shared output | 21.47 GiB |
| Physical VRAM | 4 GiB | 4 GiB |
| Detected free VRAM | 3.6 GiB | 3.6 GiB |
| Reserve | 1.0 GiB | 1.0 GiB |
| CUDA budget | 2.6 GiB | 2.6 GiB |
| Approximate shortfall based on serve | 14.0 GiB | 16.4 GiB |
| Exit code | 1 | 1 |
| API confirmed ready | No | No |
| Inference completed | No | No |
| Tokens generated | No | No |
| Tokens/s / TTFT | Not measured | Not measured |

The serve weight figures are rounded; derived shortfalls are also approximate.

## 8. Demonstrated facts and open questions

### Demonstrated
- Both `serve` commands exited with code 1 after an explicit insufficient-CUDA-budget error.
- The reported weights greatly exceed the 2.6 GiB CUDA budget.
- Qwen info inspected the checkpoint and returned 19.47 GiB of weights and a 21.47 GiB memory floor.
- During the Qwen attempt, nvidia-smi showed 15 MiB used both before and after.
- The Qwen attempt did not reach the 30-second timeout.
- The displayed `serve` help does not document an obvious general CPU-offload flag.

### Not demonstrated
- General incompatibility of either model with TensorFold.
- Absolute absence of any internal offload mechanism.
- That `--segments` distributes weights between CPU and GPU.
- That lowering the reserve would make either model runnable.
- That TensorFold Python 0.6.6 works for these models.
- RAM/GPU OOM during generation.
- Performance, quality, or generated tokens.
- Cryptographic integrity of every checkpoint shard.
- That the earlier console transcripts are byte-for-byte copies of all original logs.

## 9. Recommendations and safe next steps

1. Do not repeat the identical startup: the rejection is already documented.
2. Do not artificially raise `TENSORFOLD_CUDA_MEMORY_LIMIT_GB` above physical VRAM. This does not create memory and may move the failure to a later allocation.
3. Do not assume `--segments` means offload; verify its semantics in the exact 1.1.3 source/documentation.
4. Audit the exact source tag to locate weight sizing, memory-budget calculation, `HostMemoryUnavailable`, `BadSegments`, and tensor loading. Record the tag/commit and hashes of examined files.
5. Treat Python engine 0.6.6 as a separate experiment in an isolated environment with pinned versions and hashes.
6. For practical inference on this hardware, use a checkpoint whose weights and runtime memory fit, or investigate a runtime with documented CPU offload. Do not label estimates as MEASURED.
7. Before any future trial, record timezone-aware timestamps, executable version and SHA-256, exact model, full command, RAM/swap, GPU processes, stdout/stderr, and exit code.

## 10. Reproducible commands

### Qwen info (inspection, not inference)

    TF="$HOME/tensorfold-1.1.3-check.aOKPG0/tensorfold-1.1.3-linux-x86_64/bin/tensorfold-native"
    "$TF" info "TensorFold/Qwen3.6-35B-A3B-MLX-4bit-MTP"

### Qwen serve (the command that produced the rejection; do not needlessly repeat it)

    TF="$HOME/tensorfold-1.1.3-check.aOKPG0/tensorfold-1.1.3-linux-x86_64/bin/tensorfold-native"
    MODEL="TensorFold/Qwen3.6-35B-A3B-MLX-4bit-MTP"
    timeout --signal=INT --kill-after=5s 30s \
      "$TF" serve "$MODEL" \
      --name qwen36-forensic \
      --host 127.0.0.1 \
      --port 18090 \
      --backend auto \
      --parallel 1 \
      --context 256 \
      --temperature 0 \
      --no-thinking

### Capability audit (does not load the model)

    "$TF" serve --help
    "$TF" capabilities --json
    strings "$TF" | grep -Ei 'offload|cpu.?memory|host.?memory|memory.?budget|TENSORFOLD_MEMORY_RESERVE_GIB|TENSORFOLD_CUDA_MEMORY_LIMIT_GB|TF_CUDA_SEGMENTS|segments' | sort -u

## 11. Original log index and checksums

The original host-side files from `/home/ssantos/tensorfold-forensic-20261024/` have been copied into the repository. The links below point to the files in this branch and will resolve on `main` after merge.

| Original file | Contents | SHA-256 |
|---|---|---|
| [`nemotron-1.1.3-preflight.log`](artifacts/tensorfold-moe-forensic-2026-10-24/nemotron-1.1.3-preflight.log) | Nemotron preflight: environment, binary hash, and resource snapshot | `a14bbc3ab48e01181b5c1643f68faed80aa99ca339b1f2296e774e445400fa4c` |
| [`nemotron-1.1.3-context512.log`](artifacts/tensorfold-moe-forensic-2026-10-24/nemotron-1.1.3-context512.log) | Nemotron startup command and error | `75f6246d9b132155f65a1f499d5f391dfe65f6b553f0f566b30630d2abc6b47b` |
| [`qwen36-info-1.1.3.log`](artifacts/tensorfold-moe-forensic-2026-10-24/qwen36-info-1.1.3.log) | Qwen checkpoint inspection and resource information | `09ccbbfc4222d230c95f2dd00738f83fe9ede965d695cb412c86d449c2165438` |
| [`qwen36-1.1.3-serve-context256.log`](artifacts/tensorfold-moe-forensic-2026-10-24/qwen36-1.1.3-serve-context256.log) | Qwen command, error, exit code, and final resource snapshot | `cb232b183b75689310e20f940c1334e45faf23a61d2ce48ae7a677c47feae1f4` |
| [`offload-capability-audit.log`](artifacts/tensorfold-moe-forensic-2026-10-24/offload-capability-audit.log) | Help output, capabilities, and filtered binary strings | `b83f80846b0b29643cf8ac405057fd9657bf5dc31b7c2babfa58080c1009f2ab` |
| [`tensorfold-1.1.3-memory-options.log`](artifacts/tensorfold-moe-forensic-2026-10-24/tensorfold-1.1.3-memory-options.log) | Memory-option, environment-variable, and string audit | `b54561e0d88c675ea0f87b2a85356864317d254511bfcaf95d80f53fe2405bc3` |
| [`preflight.log`](artifacts/tensorfold-moe-forensic-2026-10-24/preflight.log) | Additional preflight log; verify whether it duplicates or aliases the Nemotron preflight before treating it as independent evidence | `9c27f6c5c00a14732ab55eb14b3948d5e79873d03f7a3aba67f33bba1b727447` |

The [SHA-256 manifest](artifacts/tensorfold-moe-forensic-2026-10-24/SHA256SUMS-originals.txt) records the checksums above. They were computed over the copied files and verified with `sha256sum -c` on the host before the commit. The manifest establishes integrity of the copied bytes relative to those hashes; it does not independently establish when or how the source logs were produced.

### Earlier console transcripts (not original files)

The repository also retains the earlier `.console.log` transcripts:
- [Qwen serve transcript](artifacts/tensorfold-moe-forensic-2026-10-24/qwen36-1.1.3-serve-context256.console.log)
- [Nemotron startup transcript](artifacts/tensorfold-moe-forensic-2026-10-24/nemotron-1.1.3-context512.console.log)
- [Qwen info transcript](artifacts/tensorfold-moe-forensic-2026-10-24/qwen36-info-1.1.3.console.log)
- [Capability audit transcript](artifacts/tensorfold-moe-forensic-2026-10-24/offload-capability-audit.console.log)
- [Memory-options transcript](artifacts/tensorfold-moe-forensic-2026-10-24/tensorfold-1.1.3-memory-options.console.log)

These are transcripts assembled from output shared in the conversation, not certified byte-for-byte copies of the host-side logs. The original files listed above are now separately preserved with their SHA-256 manifest.

## 12. Final LEONES statement

This report records an observed and reproducible memory-admission result for two MoE models on a 4 GiB RTX 3050 Laptop GPU using TensorFold native 1.1.3. It is not a speed benchmark or a generation-quality test.

The LEONES distinction between **ESTIMATED** and **MEASURED** is preserved: model sizes, resource snapshots, and error messages come from actual runs; hypotheses about offload, compatibility on another GPU, or future performance remain unvalidated.

## 13. Related report

- Spanish version: [Análisis forense TensorFold MoE — RTX 3050 Laptop 4 GiB](analisis-forense-tensorfold-moe-2026-10-24.md)
- Original logs and checksum manifest are indexed in Section 11 above.
