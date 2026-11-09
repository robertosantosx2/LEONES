# TensorFold PR #1879 — Qwen3.5-4B real CUDA context-capacity validation

**Date:** 2026-11-09  
**Target hardware:** MSI Thin 15 B12UC, NVIDIA GeForce RTX 3050 Laptop GPU (4 GiB, sm_86)  
**Runtime:** TensorFold Native 1.2.4, CUDA backend  
**Model:** `mlx-community/Qwen3.5-4B-MLX-4bit`  
**TensorFold PR:** https://github.com/ashhart/TensorFold/pull/1879  
**Validated source revision:** `a83afc3ded4617ce3ddb94dbe75e0b70da1e603d`  
**LEONES tracking:** PR #139, branch `research/atomic-chat-tensorfold-linux-cuda`

## Executive result

The PR #1879 build was exercised on the physical RTX 3050 with real, non-streaming OpenAI-compatible chat-completion requests. The largest context that has both passed server admission and completed a generation exactly to its configured token limit is **1670 tokens**:

- 120 prompt tokens
- 1550 completion tokens
- 1670 total tokens
- HTTP 200, curl exit 0
- `finish_reason=length`
- 28 seconds wall-clock request interval (20:47:44–20:48:12 local time)
- GPU monitor: 145 samples at 200 ms; 3238 MiB peak reported device memory; 65 °C maximum; 100% maximum utilization
- Server remained alive after the request (PID 539467).

This is an actual inference result, not merely a successful startup or advertised context length. A 1668-token context was independently proven with a separate exact-fill generation. Context 1672 was rejected by the CUDA admission check before serving; therefore 1670 is the **largest proven context in this campaign**, with 1671 not yet tested. Do not describe 1670 as the absolute mathematical maximum until 1671 is tested.

## 1. Host and software configuration

- OS: Ubuntu
- Machine: MSI Thin 15 B12UC
- CPU: Intel Core i7-12650H
- System RAM: 14 GiB
- GPU: NVIDIA GeForce RTX 3050 Laptop GPU, 4096 MiB, compute capability sm_86
- NVIDIA driver: 580.178.04
- CUDA runtime reported by `nvidia-smi`: 13.0
- CUDA Toolkit used to build: 13.4 (`nvcc 13.4.92`)
- TensorFold repository/worktree: `~/tensorfold-pr1879-real-validation-20261109/TensorFold`
- Native executable: `zig-out/native/bin/tensorfold-native`
- Model snapshot: `~/.cache/huggingface/hub/models--mlx-community--Qwen3.5-4B-MLX-4bit/snapshots/32f3e8ecf65426fc3306969496342d504bfa13f3`
- Backend: CUDA, device sm_86
- Memory reserve: `TENSORFOLD_MEMORY_RESERVE_GIB=0.5`
- Hugging Face mode: `HF_HUB_OFFLINE=1`
- Server: `127.0.0.1:18083`
- Server flags held constant: `--backend cuda --context N --port 18083 --no-thinking --no-drafts --no-update-check`
- Requests used `temperature=0`, `stream=false`; greedy sampling was reported by the runtime.

No model conversion or substitute checkpoint was used. The same model snapshot, backend, memory reserve, server port and generation prompt were retained across the context sweep.

## 2. Source revision and implementation under test

The tested TensorFold PR branch is `fix/qwen35-cuda-lazy-scratch`, at HEAD:

```
a83afc3ded4617ce3ddb94dbe75e0b70da1e603d
```

The PR's Qwen3.5 CUDA lazy-scratch work was tested after the rebase and host-side scratch changes. The implementation accounts for unallocated/pending scratch capacity during CUDA admission rather than allowing scratch growth to become an unaccounted late allocation. The relevant source work in the validation history includes `cuda_engine.zig`, `cuda.zig`, and the Qwen3.5 host-format tests.

The worktree also contains a deliberate local change in `zig/build/product.zig`:

```zig
build_options.addOption(bool, "is_release", o.version != null);
```

This local change must be preserved; it is not to be discarded as part of evidence collection.

Earlier checks recorded for this PR work included a successful CUDA native build (123/123 steps), host checks (7/7), and a host test run (113/113 tests). A later rebase/test record also reported 322/322 build steps and 113/113 tests passed. These build/host-test results are separate from the physical runtime tests below.

## 3. Controlled context sweep — successful real generations

All successful rows below refer to real `/v1/chat/completions` inference on the RTX 3050. Token counts are reported by the server response, not inferred from character counts.

| Configured context | Prompt tokens | Completion tokens | Total tokens | Result | Throughput / timing | Peak GPU memory |
|---:|---:|---:|---:|---|---|---:|
| 512 | — | up to 320 | — | Real generation succeeded | 56.32 tok/s | 3120 MiB |
| 768 | — | 512 | — | Real generation succeeded | 56.36 tok/s | 3146 MiB |
| 1024 | — | 768 and 820 in separate runs | — | Real generations succeeded | about 56.2 tok/s | 3172 MiB |
| 1024 | — | 900, three consecutive runs | — | All three completed | 56.21 / 55.99 / 55.80 tok/s; TTFT 187 / 113 / 113 ms | 3172 MiB |
| 1280 | 102 | 1100 | 1202 | `finish_reason=length` | 55.9613 tok/s; TTFT 0.191 s | 3198 MiB |
| 1536 | 90 | 1350 | 1440 | `finish_reason=length` | 55.9149 tok/s; TTFT 0.189 s | 3224 MiB |
| 1664 | 110 | 1500 | 1610 | `finish_reason=length` | 55.79798 tok/s; TTFT 0.192 s | 3236 MiB |
| 1668 | 120 | 1548 | 1668 | HTTP 200; exact context fill | 28 s wall-clock interval | 3238 MiB |
| 1670 | 120 | 1550 | 1670 | HTTP 200; exact context fill | 28 s wall-clock interval | 3238 MiB |

At context 1024, the three consecutive 900-token generations had prompt+completion totals of 979, 977 and 980 tokens. The monitoring run recorded 249 GPU samples, peak 3172 MiB, approximately 598 MiB free VRAM at peak, maximum temperature 69 °C, and about 6.1 GiB available system RAM.

For context 1664, the exact-fill generation used 110 prompt tokens and 1500 completion tokens. Its peak was 3236 MiB and the monitor collected 141 GPU samples.

For context 1668 and 1670, the observed 28-second interval is the request wall-clock duration measured by the shell timestamps. It is not presented as a separately instrumented token-decoding throughput measurement.

## 4. Admission boundary and rejected contexts

The following startup attempts were rejected by the CUDA memory-admission check before the server became ready:

- 1792
- 1728
- 1696
- 1680
- 1672

The diagnostic was `the CUDA memory budget fits no stream`. The rounded diagnostic fields showed approximately 0.22 GiB required and 0.22 GiB available; at the 1792 attempt the reported remaining margin was approximately 0.21 GiB. These are admission rejections, not evidence of an out-of-memory crash. The failed server attempts did not proceed to generation; after rejection, GPU usage returned to the low idle baseline.

The context 1668 server started successfully, then completed a real exact-fill generation. Context 1670 also started successfully and completed an exact-fill generation. Since 1672 was rejected and 1670 passed, the tested boundary is bracketed at 1670/1672. Context 1671 remains untested.

## 5. Detailed exact-fill evidence: context 1668

The 1668 server advertised both `context_length=1668` and `max_model_len=1668`. Its startup diagnostic reported:

- model footprint: 2.85 GiB
- one stream at a 1668-token window: 0.22 GiB
- approximately 0.2 GiB left after the configured 0.5 GiB reserve
- prompt cache: 3.8 GiB in host memory
- device staging for prompt cache: 0 MiB

The first request attempt was rejected with HTTP 400 because the request asked for 120 prompt tokens plus 1550 completion tokens (1670 total), exceeding the configured 1668-token context. This was a request/context-length mismatch, not an OOM or engine crash. The server stayed available. The request was corrected to 1548 completion tokens and then succeeded:

- HTTP 200; curl exit 0
- prompt 120; completion 1548; total 1668
- `finish_reason=length`
- response length 8221 characters
- response SHA-256: `2688438d6a92a0924e191e5a9207eb431855d4d5e4b615ad5e384af49536efab`
- 145 GPU samples at 200 ms
- peak 3238 MiB; max temperature 66 °C; max utilization 100%
- process PID 537152 remained active at the end of the test.

The failed first request and corrected retry must both remain in the record to show the request-limit correction transparently.

### Context 1668 retry SHA-256 manifest

```
9055a9005fabb596bbfc097beabe7b54b13328adea74202d1a05f9e2518794c6  extreme-1668-request-retry.json
977401978dee02c3d9a87420c51fc6f2278dae07a4fcd5fd9b3b61e60161e0cc  extreme-1668-generation-retry.json
a7b9753b2a61c7388da4f416d7b7050e3d62a1fc1e7d72405909e99c1d35381e  extreme-1668-metadata-retry.txt
a6342a023299f3576db97366a8921ed717a4ac1c36ce2859509ff0d6d3b56211  gpu-timeseries-context1668-retry.csv
```

Evidence filenames in `evidence-a83afc3-real-generation/`:

- `extreme-1668-request.json` — initial over-limit request
- `extreme-1668-generation.json` — initial HTTP 400 response
- `extreme-1668-metadata.txt` — initial attempt metadata
- `gpu-timeseries-context1668.csv` — initial attempt GPU telemetry
- `models-context1668-test.json` — model/server metadata captured during the test
- `SHA256-context1668.txt` — initial-attempt checksum manifest
- `extreme-1668-request-retry.json` — corrected exact-fill request
- `extreme-1668-generation-retry.json` — successful response
- `extreme-1668-metadata-retry.txt` — successful request timing/status
- `gpu-timeseries-context1668-retry.csv` — retry GPU telemetry
- `SHA256-context1668-retry.txt` — retry checksum manifest

## 6. Detailed exact-fill evidence: context 1670

The 1670 server advertised `context_length=1670` and `max_model_len=1670`. It started in 2.6 seconds and logged:

- model footprint: 2.85 GiB
- one stream at a 1670-token window: 0.22 GiB
- approximately 0.2 GiB remaining after the 0.5 GiB reserve
- prompt cache: 3.7 GiB in host memory
- device staging: 0 MiB

The exact-fill request used the same prompt as the 1668 retry and `max_tokens=1550`. Result:

- HTTP 200; curl exit 0
- prompt tokens: 120
- completion tokens: 1550
- total tokens: 1670
- `finish_reason=length`
- response length: 8226 characters
- response SHA-256: `416d9ab05c7e9ba8575de851c0093b1a63f8441211cd7d5cb5fcc51bb96970d2`
- start: 2026-11-09 20:47:44 +01:00
- end: 2026-11-09 20:48:12 +01:00
- wall-clock interval: 28 seconds
- GPU monitor: 145 samples
- peak device memory: 3238 MiB / 4096 MiB
- maximum temperature: 65 °C
- maximum utilization: 100%
- server PID 539467 remained active after completion.

### Context 1670 SHA-256 manifest

```
e8005ff495946d048b0bf76bc15a01d8a02f7eecc35c706fe14c464bf38fe436  extreme-1670-request.json
71402a0313108b2f90ba11a04d96f8777d5cc46720df5921836a4795fe995740  extreme-1670-generation.json
6ad62ffa552ff3f29640f297540cc1b5ec598d8622bb302c878549bd4c2213c2  extreme-1670-metadata.txt
a3baa95c1bd6db3cc5d546321c20df989343d3b8cc4d0cab42e3bc00afa64cde  gpu-timeseries-context1670.csv
```

Evidence filenames:

- `extreme-1670-request.json`
- `extreme-1670-generation.json`
- `extreme-1670-metadata.txt`
- `gpu-timeseries-context1670.csv`
- `SHA256-context1670.txt`

## 7. Repeatable procedure

The physical validation was performed as a controlled, sequential context sweep. For each candidate context:

1. Keep the same TensorFold binary, model snapshot, CUDA backend, `sm_86` device, 0.5 GiB reserve, no-thinking/no-drafts flags, and loopback port.
2. Stop only the previous TensorFold PID with SIGTERM; wait for it to exit and verify port 18083 is free. Do not use broad `pkill` commands.
3. Start the next context with `HF_HUB_OFFLINE=1` and `TENSORFOLD_MEMORY_RESERVE_GIB=0.5`.
4. Poll `GET /v1/models` until ready and preserve the complete startup log. Treat advertised context and successful admission as startup evidence only.
5. Submit a non-streaming `POST /v1/chat/completions` request with a known prompt and a `max_tokens` value that keeps prompt + completion within the candidate context.
6. Run `nvidia-smi --query-gpu=timestamp,memory.used,temperature.gpu,utilization.gpu --format=csv,noheader,nounits --loop-ms=200` during the request.
7. Preserve the exact request JSON, raw response JSON, timestamps, HTTP status, curl exit status and GPU time series.
8. Parse server-reported `prompt_tokens`, `completion_tokens`, `total_tokens` and `finish_reason`. A full-context pass requires HTTP 200, curl exit 0, total tokens equal to configured context, and `finish_reason=length`.
9. Generate SHA-256 hashes for every evidence artifact and verify them with `sha256sum -c`.
10. Confirm the server remains alive after the request and record final `nvidia-smi` and host memory.

For the 1670 exact-fill test, the request body was:

```json
{
  "model": "local-model",
  "messages": [{
    "role": "user",
    "content": "Write a detailed, continuous technical explanation of how a local language model performs inference on a GPU with limited video memory. Explain the model loading process, memory allocation, attention, transformer layers, tokenization, prompt processing, autoregressive decoding, cache management, CPU and GPU coordination, synchronization, numerical precision, and memory pressure. Develop every topic carefully, with concrete examples and connected paragraphs. Continue the explanation in depth until the output token limit is reached. Do not provide a short summary or stop voluntarily."
  }],
  "max_tokens": 1550,
  "temperature": 0,
  "stream": false
}
```

The 1668 retry used the same prompt with `max_tokens=1548`.

## 8. Interpretation and limitations

1. **Real inference is proven at 1670 tokens.** This is stronger than a successful `/v1/models` response or a startup log.
2. **The observed maximum is 1670, not yet a proven absolute ceiling.** 1672 was rejected; 1671 has not been tested.
3. **The 1668 HTTP 400 was a client request that exceeded the configured context.** The corrected request passed without restarting or changing the model/backend/reserve.
4. **Admission rejection is not OOM.** The higher contexts were refused before a stream was admitted; no CUDA OOM crash is claimed.
5. **VRAM margin is tight.** The highest observed system-wide usage was 3238 MiB of 4096 MiB (858 MiB nominally unoccupied in the `nvidia-smi` total, which includes display/driver allocations and is not all necessarily available to the TensorFold allocator). Do not translate this into a guaranteed allocatable margin.
6. **Temperature and utilization are telemetry maxima**, not averages.
7. **The 3.7–3.8 GiB prompt cache is host-memory cache**, not device VRAM. Device staging was reported as 0 MiB.
8. Startup reported a warning that `libtfgrammar.so` is required for structured output and required tool calls. This does not invalidate the plain-text generation tests; structured output/tool-call validation is outside this campaign.
9. These runs establish plain-text chat generation on this specific checkpoint, build, machine and configuration. They do not establish vision, speech, embeddings, structured tool calls, multi-stream concurrency, other GPUs, or other model families.
10. The 1670 test was performed with `stream=false`; it is not a streaming/SSE test.

## 9. Current runtime state at end of last test

At 20:48:12 on 2026-11-09:

- TensorFold server PID: 539467
- API: `http://127.0.0.1:18083/v1`
- configured context: 1670
- model snapshot ID: `32f3e8ecf65426fc3306969496342d504bfa13f3`
- GPU: 3238 MiB / 4096 MiB; 64 °C in the final `nvidia-smi` snapshot; 100% utilization
- TensorFold process attribution: 3214 MiB
- Xorg attribution: 4 MiB
- system memory snapshot: 14 GiB total, 7.6 GiB used, 3.7 GiB free, 7.2 GiB available; 31 GiB swap total, 3.7 GiB used.

The server was deliberately left running after the test. No cleanup or shutdown is implied by this report.

## 10. Raw evidence location and publication status

All raw test artifacts are retained on the Ubuntu host under:

```
~/tensorfold-pr1879-real-validation-20261109/evidence-a83afc3-real-generation/
```

This report records the raw filenames and the exact hashes available in the terminal transcript. The raw JSON/CSV/log files themselves are **not attached to this LEONES Markdown file by this commit**. They remain on the validation host until copied/committed as separate artifacts. Do not claim the raw files have been uploaded to GitHub unless that upload is performed and verified.

The original worktree and report must preserve the local `zig/build/product.zig` change noted above.

## 11. Next validation gate

The only next context-boundary test needed to refine the current bracket is context **1671**. If it is admitted, run an exact-fill real generation with the same prompt (120 prompt tokens) and `max_tokens=1551`, preserving all telemetry and checksums. If 1671 is rejected, 1670 becomes the maximum demonstrated integer context under this exact build/model/hardware/reserve configuration.

No memory reserve reduction, CUDA allocator change, GPU setting change, or unrelated workload termination is recommended for this validation.
