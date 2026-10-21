# Dense Inference Report — October 2026

**Master file:** `report-inferencia-dense_Octubre26.md`  
**Consolidated:** 2026-10-21  
**Project:** LEONES  
**Scope:** Local Qwen/Qwen3.5 model tests on Ubuntu, inference engines, quantization formats, configurations, retained commands, results, and evidence limitations.

> This report consolidates repository evidence and test-conversation records. It is not a full transcript of every terminal session: some complete logs remain only on the local machine. Missing commands or metrics are identified rather than guessed.

## 1. Executive summary

### Completed inference

| Engine | Model / artifact | Result |
|---|---|---|
| TensorFold native 1.1.1, CUDA | Qwen3.5-2B, MLX 4-bit | 95.08 tok/s (32 tokens); 105.71 tok/s (128 tokens) |
| TensorFold native 1.1.1, CUDA | Qwen3.5-4B, MLX 4-bit | 53.64 tok/s (64 tokens); 53.42 tok/s (128 tokens) |
| llama.cpp CUDA CLI | Qwen3.5-4B, GGUF Q4_K_M | 141.2 tok/s prefill; 42.4 tok/s generation |
| TensorFold API | Qwen3.5-4B, MLX 4-bit | 3/3 HTTP 200; median 54.708 tok/s, 0.7066 s/request, TTFT 0.1303 s |
| llama.cpp CUDA API | Qwen3.5-4B, GGUF Q4_K_M | 3/3 HTTP 200; median 47.646 tok/s, 0.8680 s/request |
| RustingStrata CUDA API | Qwen3.5-4B, GGUF Q4_K_M | 3/3 HTTP 200; median 0.8384 s/request; API did not expose internal tok/s or TTFT |
| llama.cpp CUDA | Qwen3-30B-A3B-Instruct-2507 IQ3_XXS | Offload sweep completed | 1.97–2.00 tok/s median at 12–14 layers in the longer batch; 15 layers was the highest functional offload tested |
| RustingStrata CUDA/NVRTC 13.0 | Qwen3-30B-A3B-Instruct-2507 IQ3_XXS | Completed | 7.74 tok/s in one real 64-token generation; not yet a controlled comparison with llama.cpp |
| RustingStrata bench | Qwen3.5-4B, GGUF Q4_K_M | Separate prefill test: 915.3 tok/s PP=128; 986.5 tok/s PP=512 |

### Incomplete or excluded attempts

- **Magnitude 0.2.10 + Qwen3.5-4B:** artifacts downloaded and hashes verified, but CLI/catalog did not accept the model. No inference or performance metrics.
- **KTransformers:** explicitly excluded from this round; do not build or install. No documented working Qwen3.5-4B path was identified in the examined branch.
- **SGLang:** explicitly excluded; do not install, download the AWQ checkpoint, or benchmark it.
- **Mistral.rs:** considered in the four-engine plan, but no measured run is present in the consolidated evidence.
- **Qwen3.5-4B AWQ W4A16:** candidate metadata inspected only; not an executed inference or confirmed download.
- **Qwen3-30B-A3B-Instruct IQ3_XXS:** MoE inference was later completed with llama.cpp CUDA and RustingStrata; see §17. Cross-engine results are not yet strictly comparable.
- **TensorFold Qwen3.5-4B initial startup:** rejected by the CUDA memory budget; a later run with context 512 succeeded.

## 2. Hardware and common environment

- OS: native Ubuntu, x86_64.
- CPU: Intel Core i7-12650H, 12th generation, 16 logical CPUs.
- RAM: 14 GiB; a Magnitude report displayed 14.8 GB.
- GPU: NVIDIA GeForce RTX 3050 Laptop, 4 GiB VRAM (4096 MiB).
- NVIDIA driver: 580.178.04.
- CUDA reported by `nvidia-smi`: 13.0.
- During one Magnitude check, the app reported about 3.7 GiB VRAM; RAM usage was 9.3/14.8 GB with 5.5 GB free.
- Total GPU memory, process VRAM, and free memory are different measures. Post-run snapshots do not show peak generation usage.

General checks:

~~~bash
free -h
nvidia-smi
pgrep -af 'magnitude|Magnitude' || true
systemctl is-active magnitude.service || true
~~~

These checks were used to detect an active Magnitude service or residual processes before switching engines, not to measure performance.

## 3. Models, artifacts, and quantization

### 3.1 Qwen3.5-2B on TensorFold

- Model: `mlx-community/Qwen3.5-2B-MLX-4bit`.
- MLX 4-bit weights; group size 64 in the test record.
- Local endpoint: `http://127.0.0.1:18083/v1`; `/v1/models` responded successfully.
- Context: 1024; output bounded by `max_tokens`.

### 3.2 Qwen3.5-4B on TensorFold

- Model: `mlx-community/Qwen3.5-4B-MLX-4bit`.
- MLX 4-bit weights; group size 64.
- Local endpoint: `http://127.0.0.1:18084/v1`.
- Reference context: 512.
- Model load time: 6.4 s in one run; a separate startup/API record estimated about 9.9 s. These are different records and must not be merged.
- Prefill latency was recorded in milliseconds, but prefill tok/s was not consistently retained.

### 3.3 Qwen3.5-4B on llama.cpp CUDA

- File: `~/llama.cpp-cuda/models/qwen3.5-4b-Q4_K_M.gguf`, approximately 2.59 GiB.
- Quantization: GGUF Q4_K_M / Q4_K - Medium.
- Verified SHA-256: `c3c2cf023efdbd913c2363a14d5c7266db5e05c4602f1c0790eaed567d8aff23`.
- Project: `~/llama.cpp-cuda`; binary: `build-cuda/bin/llama-cli`.
- Build: `b11740-6fa4f6cd3`.

Retained CLI command:

~~~bash
cd ~/llama.cpp-cuda

./build-cuda/bin/llama-cli \
  -m "$PWD/models/qwen3.5-4b-Q4_K_M.gguf" \
  -ngl 99 \
  -c 512 \
  -n 128 \
  --temp 0 \
  --no-display-prompt \
  -p "Responde en español en una frase: ¿qué ventajas tiene ejecutar un modelo de IA localmente?" \
  --chat-template-kwargs '{"enable_thinking":false}'
~~~

### 3.4 Qwen3.5-4B on RustingStrata

- Artifact: `qwen3.5-4b-Q4_K_M.gguf`, GGUF Q4_K_M.
- Used in the API comparison and a separate prefill benchmark.
- API did not expose internal generation speed or TTFT.
- 32 tokens divided by total request time is retained only as a wall-clock estimate, not internal engine tok/s.

### 3.5 Qwen3.5-4B on Magnitude

Downloaded from `unsloth/Qwen3.5-4B-MTP-GGUF`, revision `86835bf9949e4d14d6860f7910b1340ad4f271a9`:

| File | Size | SHA-256 |
|---|---:|---|
| `Qwen3.5-4B-UD-Q4_K_XL.gguf` | 2,990,664,000 bytes | `d2bfbee4de17c74e6308a4dc750be4c2271f92ae2df1e28f5c5afa0dcdb6fccc` |
| `mmproj-BF16.gguf` | 675,569,216 bytes | `169ee40fb1e234ff38b2d814eb8633611a54b6f941f11b700d96dec02cb44ddf` |

Combined size: 3,666,233,216 bytes. DFlash dependency also downloaded:

- Repository: `magnitudedev/Qwen3.5-4B-DFlash-GGUF`, revision `0094e74a88676605d53b79c7c3d26096335c9746`.
- File: `Qwen3.5-4B-DFlash-Q8_0.gguf`, 685,134,176 bytes.

Hashes were checked with `sha256sum`, and snapshot links pointed to valid blobs. **Q4_K_XL is not the same quantization as Q4_K_M** used by llama.cpp/RustingStrata.

### 3.6 Qwen3.5-4B AWQ candidate

Candidate inspected: `matchachoco/Qwen3.5-4B-QuantStudy-AWQ-W4A16`.

- Declared architecture: `Qwen3_5ForConditionalGeneration`.
- Repository size: 3.81 GB.
- `model.safetensors`: 3,786,643,328 bytes.
- Declared quantization: compressed-tensors, pack-quantized INT4, group 128, with excluded layers.

This was metadata inspection only. The SGLang/AWQ route was explicitly ruled out; do not download the checkpoint or install SGLang for this round.

### 3.7 Qwen3-30B-A3B-Instruct IQ3_XXS

The artifact was downloaded and executed during the MoE session on 2026-10-21:

- Model: Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf.
- Path: ~/benchmarks/qwen3-30b-a3b-iq3-xxs/.
- GGUF architecture: qwen3moe; approximately 30.53B parameters, 48 blocks, 128 experts, and 8 active experts per token.
- Quantization: IQ3_XXS; approximately 12.2 GB / 11.37 GiB.
- SHA-256: 292daa2b66aec59d075532d0bcf05010bf4a3b012a4216c28dc021b73d1e9ab4.
- Real inference was verified with llama.cpp CUDA and RustingStrata CUDA. Commands, offload failures, parameters, and results are documented in §17.

Do not confuse this 30B MoE model with Qwen3.5-4B.

## 4. TensorFold results: Qwen3.5-2B and 4B

### 4.1 Qwen3.5-2B

| Metric | Short sample | Long sample |
|---|---:|---:|
| Requested output tokens | 32 | 128 |
| Generation | 95.08 tok/s | 105.71 tok/s |
| Recorded generation time | 0.326 s | 1.201 s |
| TTFT | 88.2 ms | 94.1 ms |
| Process-associated VRAM | approx. 2,388 MiB | approx. 2,388 MiB |
| Total VRAM in snapshots | 2,411 / 4,096 MiB | 2,411 / 4,096 MiB |
| Context | 1024 | 1024 |

Real inference in Spanish; both samples were capped by `max_tokens`. Prefill tok/s was not recorded.

### 4.2 Qwen3.5-4B

| Metric | Sample A | Sample B |
|---|---:|---:|
| Requested output tokens | 64 | 128 |
| Generation | 53.64 tok/s | 53.42 tok/s |
| Prefill latency | 190 ms | 209 ms |
| TTFT | 193 ms | 212 ms |
| Process-associated VRAM | approx. 3,120 MiB | approx. 3,120 MiB |
| Total VRAM in snapshots | 3,143 / 4,096 MiB | 3,143 / 4,096 MiB |
| Context | 512 | 512 |

Prefill tok/s was not recorded. One run recorded 6.4 s model loading. The response was a real Spanish inference.

### 4.3 Initial rejected startup

The first TensorFold Qwen3.5-4B startup was rejected with `TENSORFOLD_CUDA_MEMORY_LIMIT_GB=3.4` and a 0.5 GiB reserve. A later CUDA run with context 512 succeeded. This indicates a memory-budget/configuration issue, not absolute incompatibility.

## 5. llama.cpp CUDA results

CLI run dated 2026-10-20:

| Field | Result |
|---|---|
| Model | Qwen3.5-4B GGUF Q4_K_M |
| Context | 512 |
| Maximum output | 128 tokens |
| Temperature | 0 |
| Requested GPU layers | `-ngl 99` |
| Prefill / prompt processing | **141.2 tok/s** |
| Generation | **42.4 tok/s** |
| Total VRAM in post-run snapshot | 2,831 / 4,096 MiB |
| `llama-cli` process VRAM | 2,808 MiB |
| GPU temperature in snapshot | 42 °C |
| Instantaneous utilization | 0%; snapshot was taken after generation |
| GGUF SHA-256 | Verified; see §3.3 |

The Spanish answer was coherent. The 0% utilization snapshot was taken after generation and does not describe utilization during inference. This confirms local CUDA inference with `llama-cli`, not integration with Magnitude, TensorFold, ODS, or LEONES Runtime.

Other historical llama.cpp prompt-processing figures were approximately 118.14, 51.99, and 22.31 tok/s, from runs/workloads whose complete protocols are not available here. Another run recorded 141.2 tok/s. Do not average or directly compare these figures as if the prompts and conditions were identical.

A log recorded model loading at approximately 1.83 s, from `load_model` start (about 0.188 s) to “model loaded” (about 2.019 s). This is distinct from request latency through an already-started server.

## 6. Three-engine API benchmark — 2026-10-20

### Protocol

- Script: `~/benchmarks/benchmark_qwen35_4b_three_engines_fixed_v2.sh`.
- Run directory: `~/qwen35-4b-benchmark-fixed-20261020-215243`.
- Hardware: Ubuntu x86_64, i7-12650H, 16 logical CPUs, 14 GiB RAM, RTX 3050 Laptop 4 GiB, driver 580.178.04, CUDA 13.0.
- Three measured iterations per engine; separate warm-up excluded from measured JSONL.
- 32 output tokens per request.
- All nine measured requests returned HTTP 200 and stopped at the 32-token limit (`finish_reason=length`).
- Prompt and parameters were retained in local artifacts; the GitHub report does not contain raw JSONL or complete logs.

Retained command:

~~~bash
cd ~/benchmarks
bash ~/benchmarks/benchmark_qwen35_4b_three_engines_fixed_v2.sh
~~~

### Median summary

| Engine | Artifact | Median total time | Median output speed | Median TTFT |
|---|---|---:|---:|---:|
| TensorFold CUDA | `mlx-community/Qwen3.5-4B-MLX-4bit` | **0.7066 s** | **54.708 tok/s** | **0.1303 s** |
| llama.cpp CUDA | `qwen3.5-4b-Q4_K_M.gguf` | 0.8680 s | 47.646 tok/s | No comparable client-side measurement |
| RustingStrata CUDA | `qwen3.5-4b-Q4_K_M.gguf` | 0.8384 s | Not exposed by API | Not exposed by API |

TensorFold prefill was approximately 228–232 tok/s for these requests. Do not confuse this with prefill latency in the earlier local tests.

### Per-iteration results

| Engine | Iteration | Output speed | Total time | TTFT |
|---|---:|---:|---:|---:|
| TensorFold | 1 | 54.663 tok/s | 0.7094 s | 0.1324 s |
| TensorFold | 2 | 54.708 tok/s | 0.7066 s | 0.1303 s |
| TensorFold | 3 | 54.771 tok/s | 0.7058 s | 0.1302 s |
| llama.cpp CUDA | 1 | 47.498 tok/s | 0.9544 s | N/A |
| llama.cpp CUDA | 2 | 47.646 tok/s | 0.8680 s | N/A |
| llama.cpp CUDA | 3 | 47.723 tok/s | 0.7578 s | N/A |
| RustingStrata | 1 | Not exposed | 0.8384 s | N/A |
| RustingStrata | 2 | Not exposed | 0.8381 s | N/A |
| RustingStrata | 3 | Not exposed | 0.8384 s | N/A |

The approximate RustingStrata estimate of 38.17 tok/s is 32 tokens divided by median total request time. **It is not internal decoding speed** and must not be compared with output tok/s exposed by the other engines.

### Script issue and local artifacts

The three tests per engine completed. The script then failed while generating the summary due to an extra closing parenthesis in the Python report-generation section (line 302). CSV and Markdown were regenerated from the existing `results.jsonl`; the engines were not rerun.

Artifacts in the local run directory:

- `results.jsonl`, `results.csv`, `summary.md`
- `tensorfold-server.log`, `llama-cpp-server.log`, `rusting-strata-server.log`
- `environment.txt`, `nvidia-smi-before.txt`, `nvidia-smi-after.txt`, `benchmark.log`

The raw records and logs are documented as local and are not claimed to be committed to GitHub.

### Comparability

TensorFold used an MLX-4bit artifact; llama.cpp and RustingStrata used GGUF Q4_K_M. This is a practical runtime comparison, not a strict same-artifact benchmark. Three iterations and a 32-token output cap are an initial snapshot, not a sustained-generation, long-context, concurrency, quality, energy, or statistical-significance test.

The llama.cpp response contained an empty `<think>...</think>` wrapper despite settings intended to disable reasoning; the Spanish response text was coherent.

## 7. Separate RustingStrata prefill benchmark

A separate `strata bench` run was documented:

- Context: 1024.
- `--tg 64 --reps 3`.
- PP=128: **915.3 tok/s**.
- PP=512: **986.5 tok/s**.
- Load time: not recorded.

These figures come from RustingStrata's own harness and different prompt/batch sizes. They should not be ranked directly against TensorFold API prefill or historical llama.cpp figures; the same measurement phase and protocol have not been established.

## 8. Magnitude 0.2.10: blocked attempt

### Runtime state

- CLI version: `0.2.10`.
- `magnitude update check` and `magnitude update status`: CLI reported itself up to date.
- Service: `Runtime Ready`.
- Local address: `http://127.0.0.1:10100`.
- Active model: `None`.
- `magnitude models status`: no local models.
- `/var/lib/magnitude/state/models.json`: `slots: {}`, empty `recentModels`, and `favorites: []`.

### Recorded commands

~~~bash
magnitude --version
magnitude update check
magnitude update status
magnitude models status
magnitude status
magnitude catalog show qwen3.5-4b
magnitude catalog show 'qwen3.5-4b:gguf:q4'
magnitude models load 'hf:unsloth/Qwen3.5-4B-MTP-GGUF/Qwen3.5-4B-UD-Q4_K_XL.gguf'
~~~

Results:

- `magnitude catalog show qwen3.5-4b`: `Invalid catalog model ID`.
- `magnitude catalog show 'qwen3.5-4b:gguf:q4'`: `Unknown catalog model`.
- Loading via the `hf:...` path: `Invalid catalog model ID`.
- `magnitude models status`: “No local models are on this computer”.
- `magnitude status`: runtime ready, active model `None`.
- Internal inventory listed Qwen3.5-4B as `available`, architecture `qwen35`, 4,326,350,848 parameters, with declared `load/unload/delete` operations. This does not mean the CLI could load it.
- The published catalog reported 73/73 models evaluated but listed only Gemma 4 E2B Q4 QAT and MiniCPM5 1B Q4/Q8 as compatible. Qwen was absent.

**Conclusion:** artifacts were verified, but the model was not activated. No Magnitude prefill, tok/s, TTFT, inference duration, or VRAM figures can be attributed to a Qwen inference. The exact cause was not proven; do not automatically blame memory or intrinsic model incompatibility.

Maintenance constraints: do not delete verified blobs, unnecessarily redownload artifacts, manually edit `models.json` or `catalog-affiliations.json`, or blindly reinstall a CLI that reports itself up to date. Reopen the test only after a corrected catalog/load path is available, then measure a real request.

## 9. KTransformers and SGLang: explicit exclusions

### KTransformers

- Examined branch: `qwen3.5`.
- No documented working path was found for Qwen3.5-4B in the local configuration.
- Visible documentation focused on Qwen3.5 MoE-400B/SGLang-KT; the classic `optimize_and_load_gguf` workflow did not demonstrate compatibility with `Qwen3_5ForConditionalGeneration` / Qwen3.5-4B.
- Resources during the check: 14 GiB RAM, about 8.3 GiB available at that moment; RTX 3050 4 GiB with around 3.75 GiB free.
- Explicit decision: exclude KTransformers for this round. Do not build or install it, and do not count it as a measured engine.

No successful KTransformers inference command or Qwen3.5-4B measurement was found. No tok/s, prefill, TTFT, or VRAM result is therefore reported.

### SGLang

Explicitly excluded. Do not install SGLang, download the AWQ checkpoint, or benchmark it. No SGLang inference was measured in this round.

## 10. Mistral.rs evidence status

A four-engine comparison was planned: TensorFold, llama.cpp CUDA, RustingStrata, and Mistral.rs. The reproducible three-runtime report contains only TensorFold, llama.cpp, and RustingStrata. The consolidated material contains no logs, final command, or results certifying a completed Mistral.rs run. It is recorded as **no confirmed measurement**, not as a technical failure or incompatibility.

## 11. Additional commands and diagnostics

### Magnitude inspection

~~~bash
magnitude docs cli
magnitude catalog recommendations
magnitude hardware
magnitude catalog show qwen3.5-4b
~~~

CLI documentation, recommendations, hardware, and catalog metadata were inspected. The catalog entry did not provide a working load path; the CLI rejected the ID.

### Help and model-state inspection

~~~bash
magnitude models --help
magnitude docs --help
magnitude models load --help
magnitude catalog pull --help
magnitude models status
cat /var/lib/magnitude/config.json
~~~

The `/var/lib/magnitude/state/models.json` file and service state were also inspected. The CLI reported no active local models.

### Process/resource check before switching engines

~~~bash
sudo systemctl stop magnitude.service

echo "===== SERVICE STATE ====="
systemctl is-active magnitude.service || true

echo
echo "===== RESIDUAL PROCESSES ====="
pgrep -af 'magnitude|Magnitude' || true

echo
echo "===== RAM AND SWAP ====="
free -h

echo
echo "===== VRAM ====="
nvidia-smi
~~~

This sequence stopped Magnitude and checked for residual RAM/VRAM-consuming processes before proceeding. The terminal requested sudo authentication. This diagnostic check does not itself provide benchmark results.

## 12. Overall interpretation

1. In local TensorFold samples, Qwen3.5-2B reached 95.08–105.71 tok/s and Qwen3.5-4B reached 53.42–53.64 tok/s.
2. The retained llama.cpp CLI run reached 42.4 tok/s generation and 141.2 tok/s prompt processing for Qwen3.5-4B Q4_K_M.
3. In the 32-token API comparison, TensorFold had the highest median output speed among exposed metrics (54.708 tok/s), versus 47.646 tok/s for llama.cpp.
4. RustingStrata returned valid responses, but its API exposed neither internal tok/s nor TTFT. Total-request-time estimates are not decoding throughput.
5. MLX-4bit and GGUF Q4_K_M artifacts differ. The results do not prove that every performance difference is caused solely by the engine.
6. Magnitude did not complete inference; this is a catalog/CLI blockage, not a speed of zero.
7. KTransformers and SGLang were excluded by explicit decision. No confirmed Mistral.rs measurement exists in the consolidated evidence.
8. Qwen3-30B-A3B-Instruct IQ3_XXS has measured inference results from llama.cpp CUDA and RustingStrata (§17); a controlled cross-engine comparison remains pending.
9. These records do not demonstrate end-to-end integration with ODS or LEONES Runtime; they cover individual model/engine tests.

## 13. Evidence limitations and missing data

- Complete logs and API JSONL remain in local directory `~/qwen35-4b-benchmark-fixed-20261020-215243`; this report does not claim they were uploaded.
- The full text of every generated response is not retained here.
- Some historical tests lack a complete exact prompt, artifact revision, temperature, context, or timing method.
- TensorFold prefill tok/s was not recorded in the local 2B/4B tests.
- llama.cpp TTFT in the API comparison was unavailable from the client-side parser/measurement.
- RustingStrata TTFT and internal tok/s were not exposed by its API.
- Peak VRAM throughout generation is unavailable for every engine.
- Energy use, quality, long-context behavior, concurrency, and sustained performance have not been measured under a common protocol.
- Model load time, TTFT from an already-warm server, total request time, and CLI process execution time have different measurement boundaries and must not be conflated.

## 14. Recommended protocol for the next comparable round

Preserve existing evidence and create a new run directory/execution ID; do not overwrite historical results.

- Fix the same prompt, context 256 or 512, temperature 0, output limit, and template.
- Record hash, size, quantization, revision, and path for each artifact.
- Separate loading/warm-up and run at least three measured iterations per engine.
- Record load time, TTFT, prefill tok/s, generation tok/s, and total duration separately.
- Capture VRAM before, during, and after inference, plus RAM, version/build, backend, and arguments.
- Run engines sequentially, with only one inference engine active.
- Mark unexposed metrics N/A; do not substitute estimates unless clearly labelled.
- For strict comparisons, use the same artifact and quantization where supported. Otherwise label the result a practical comparison of different configurations.
- Do not reopen KTransformers or SGLang in this round, respecting the exclusion decision.
- Treat Qwen3-30B-A3B IQ3_XXS as a separate MoE experiment, not part of the Qwen3.5-4B table.

LEONES benchmark evidence methodology: `docs/runtime-benchmark-evidence-v1.1.md`.

## 15. Related reports and evidence

- [TensorFold + llama.cpp comparison inventory and Magnitude closure](../experimental/inventario-comparativo-qwen35-tensorfold-llamacpp-2026-10-20.md)
- [Three-runtime API benchmark and per-iteration results](qwen35-4b-three-runtimes-2026-10-20.md)
- [CSV for the nine measured requests](qwen35-4b-three-runtimes-2026-10-20.csv)
- [Magnitude Qwen3.5-4B test — 2026-10-21](magnitude-qwen35-4b-2026-10-21.md)
- [Qwen3.5-4B llama.cpp CUDA CLI test](../experimental/qwen3.5-4b-llama-cpp-rtx3050.md)
- [LEONES benchmark evidence contract/methodology](../runtime-benchmark-evidence-v1.1.md)

## 16. GitHub consolidation history

Related LEONES commits:

- [e595852 — initial TensorFold and llama.cpp consolidation](https://github.com/robertosantosx2/LEONES/commit/e595852ede8f5708bab96e20f171a37f870f8274)
- [661b545 — prefill metrics](https://github.com/robertosantosx2/LEONES/commit/661b545dd0ee2a2d4654d1bb4687daed41e96398)
- [fddc904 — local Qwen3.5-4B llama.cpp CUDA test](https://github.com/robertosantosx2/LEONES/commit/fddc904e5a8f7b23ab0ed6583bf4ef57a394458d)
- [2db5093 — three-runtime results](https://github.com/robertosantosx2/LEONES/commit/2db50934017e3ab4257395cd9f27424a40f74e3e)
- [d34aff0 — per-iteration results CSV](https://github.com/robertosantosx2/LEONES/commit/d34aff0625d4124fe7fe3f6ba2fa616dd25bc2bb)
- [6d23a60 — runtime evidence index](https://github.com/robertosantosx2/LEONES/commit/6d23a604d20fad6cd0bee32c5db818cfbd5de6f6)
- [75f93ce — blocked Magnitude attempt](https://github.com/robertosantosx2/LEONES/commit/75f93ce440445231b83d6b153b9f779c56737b3a)
- [cc7b6c4 — Magnitude attempt closure](https://github.com/robertosantosx2/LEONES/commit/cc7b6c42faa7266c3941022b3d216f278e7f95fe)

---
**Final status:** consolidated from evidence available as of 2026-10-21, including the Qwen3-30B-A3B MoE test with llama.cpp CUDA and RustingStrata (§17). No metrics are invented for engines without completed inference. Future tests should be added as new runs, preserving historical evidence and its limitations.


## 17. MoE experiment: Qwen3-30B-A3B IQ3_XXS on llama.cpp CUDA and RustingStrata — 2026-10-21

### 17.1 Goal and scope

This section adds actual Qwen3-30B-A3B-Instruct-2507 IQ3_XXS runs. The session focused on verifying llama.cpp CUDA, measuring generation across --n-gpu-layers values, finding the RTX 3050 Laptop 4 GiB offload limit, running RustingStrata with driver-compatible NVRTC, and retaining both successful and failed attempts.

This is not yet a perfectly controlled cross-engine comparison: initial tests used different commands and output lengths, and the two automated llama.cpp batches ran at different times. Results are retained per batch rather than merged into one median.

### 17.2 Hardware and artifact

| Field | Observed value |
|---|---|
| OS | Native Ubuntu, x86_64 |
| CPU | Intel Core i7-12650H, 12th generation |
| Logical CPUs | 16 |
| Physical RAM | 14 GiB |
| Swap | 32 GiB |
| GPU | NVIDIA RTX 3050 Laptop |
| Physical VRAM | 4096 MiB |
| VRAM reported usable by llama.cpp | approximately 3768 MiB |
| NVIDIA driver | 580.178.04 |
| CUDA from nvidia-smi | 13.0 |
| System CUDA Toolkit | 13.4 |
| Model | Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf |
| Path | ~/benchmarks/qwen3-30b-a3b-iq3-xxs/Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf |
| Approximate size | 12.2 GB / 11.37 GiB |
| GGUF architecture | qwen3moe |
| Parameters | approximately 30.53B |
| Blocks | 48 |
| Experts | 128; 8 active per token |
| Quantization | IQ3_XXS |
| SHA-256 | 292daa2b66aec59d075532d0bcf05010bf4a3b012a4216c28dc021b73d1e9ab4 |

System checks used:

~~~bash
free -h
nvidia-smi
pgrep -af 'magnitude|Magnitude' || true
systemctl is-active magnitude.service || true
~~~

Before loading the large model, the procedure was to stop Magnitude and check for residual processes. Memory snapshots are samples, not continuous telemetry; peak /usr/bin/time RSS is distinct from VRAM.

### 17.3 Software and paths

- llama.cpp checkout: ~/llama.cpp-cuda.
- Binaries: ~/llama.cpp-cuda/build-cuda/bin/llama-cli, llama-server, and llama-bench.
- Version: 0.7.0-dev, build 11740, commit 6fa4f6cd3.
- RustingStrata checkout: ~/rusting-strata-test.
- Binary: ~/rusting-strata-test/target/release/strata, version 1.0.1.
- TensorFold checkout: ~/tensorfold-test; no comparable TensorFold run with this 30B model was confirmed in this session.

### 17.4 Initial llama.cpp validation: CPU and small offload

| Test | Main configuration | Prompt / prefill | Generation | Outcome |
|---|---|---:|---:|---|
| llama-bench CPU | ngl=0, PP=128, TG=32, reps=3, threads=8 | 42.14 ± 24.48 tok/s | 1.39 ± 0.03 tok/s | RC 0 |
| llama-bench one layer | ngl=1, PP=128, TG=32, reps=3, threads=8 | 50.93 ± 30.10 tok/s | 1.43 ± 0.04 tok/s | RC 0 |
| CLI CPU | ngl=0 | 3.1 tok/s | 1.4 tok/s | 84.79 s; RC 0 |
| CLI one layer, first run | ngl=1 | 0.7 tok/s | 1.4 tok/s | 116.04 s; RC 0 |
| Monitored CLI one layer | ngl=1 | 2.9 tok/s | 1.4 tok/s | 83.18 s; RC 0 |

Prefill varied substantially. Do not average llama-bench and CLI as if they were the same harness.

Retained local logs:
- llama-bench-cpu-20261021.log
- llama-bench-ngl1-20261021.log
- llama-cpp-generate-cpu-20261021.log
- llama-cpp-generate-ngl1-20261021.log
- llama-cpp-ngl1-monitored-20261021.log
- llama-cpp-ngl1-gpu-20261021.csv

These files remain on the test machine; this report does not claim they were uploaded to GitHub.

### 17.5 Controlled llama-cli configuration

Controlled attempts used the same parameters, changing --n-gpu-layers:

~~~bash
cd "$HOME/llama.cpp-cuda" || exit 1

LLAMA="$HOME/llama.cpp-cuda/build-cuda/bin/llama-cli"
M="$HOME/benchmarks/qwen3-30b-a3b-iq3-xxs/Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf"

"$LLAMA" \
  --model "$M" \
  --n-gpu-layers 14 \
  --fit off \
  --ctx-size 1024 \
  --batch-size 64 \
  --ubatch-size 32 \
  --threads 8 \
  --predict 16 \
  --temp 0 \
  --seed 42 \
  --prompt "Responde brevemente en español: ¿qué es la inferencia local?" \
  --single-turn \
  --simple-io \
  --verbose
~~~

To repeat another configuration, change only --n-gpu-layers (0, 1, 8, 10, 12, 14, 15, or 16). The automated sweep held seed, prompt, context, batch, ubatch, and threads constant, saving a log for each repetition.

Common parameters:
- context: 1024;
- batch: 64;
- ubatch: 32;
- CPU threads: 8;
- temperature: 0;
- seed: 42;
- output: 128 tokens in batch 1 and 256 in batch 2;
- --fit off to prevent automatic fitting from changing requested offload.

### 17.6 Offload and VRAM limit

Verbose logs confirmed actual GPU layer allocation.

| Requested layers | GPU layers reported | CUDA model buffer | CUDA KV | CUDA compute | Status |
|---:|---:|---:|---:|---:|---|
| 8 | 8/49 | 1885.45 MiB | 14 MiB | 86.25 MiB | Loaded |
| 12 | 12/49 | 2819.27 MiB | 22 MiB | 86.25 MiB | Loaded |
| 14 | 14/49 | 3290.68 MiB | 26 MiB | 86.25 MiB | Loaded |
| 15 | 15/49 | 3521.88 MiB | 28 MiB | 86.25 MiB | Loaded |
| 16 | — | 3753.09 MiB allocation failed | — | — | CUDA OOM |

With 8 layers, the CPU-mapped model buffer was 9759.88 MiB. The log contained a nonfatal CUDA_Host compute buffer size mismatch warning: 4.1376 MiB versus 1.0636 MiB expected.

The 16-layer attempt failed in both an initial llama-server startup and a controlled llama-cli run with cudaMalloc failed: out of memory. The controlled run requested 3753.09 MiB, nearly all CUDA memory llama.cpp reported as usable. Empirically, 15 was the highest layer count tested that loaded under this configuration; that does not make it the fastest option or guarantee enough margin at other contexts or with other GPU processes.

Controlled failure log: llama-cli-ngl16-controlled-20261021.log.

### 17.7 Automated layer sweep

Local script: ~/benchmarks/qwen3-30b-a3b-iq3-xxs/benchmark-ngl.sh. It swept layer counts (0 1 8 10 12 14 15 16), writing individual logs, CSV, and a summary. It ran in two batches:

- benchmark-ngl-20261021-212122: 2 repetitions, configured for 128 output tokens.
- benchmark-ngl-20261021-213920: 3 repetitions, configured for 256 output tokens.

Commands to run the sweep and analyze local logs:

~~~bash
bash "$HOME/benchmarks/qwen3-30b-a3b-iq3-xxs/benchmark-ngl.sh"
python3 "$HOME/benchmarks/qwen3-30b-a3b-iq3-xxs/analyze-benchmarks.py"
~~~

The complete original benchmark-ngl.sh source and logs were not versioned in this change. Effective parameters and observed results are recorded here. The local analyzer writes benchmark-results-corrected.csv.

#### Batch 1: 2 repetitions, 128 output tokens

| GPU layers | Rep 1 tok/s | Rep 2 tok/s | Median tok/s | Median prefill tok/s | Max RSS |
|---:|---:|---:|---:|---:|---:|
| 0 | 1.33 | 1.40 | 1.36 | 4.51 | 11.32 GiB |
| 1 | 1.39 | 1.61 | 1.50 | 6.17 | 11.62 GiB |
| 8 | 1.74 | 1.73 | 1.73 | 7.28 | 11.68 GiB |
| 10 | 1.80 | 1.78 | 1.79 | 5.28 | 11.36 GiB |
| 12 | 1.71 | 1.92 | 1.81 | 6.42 | 11.48 GiB |
| 14 | 1.90 | 2.02 | 1.96 | 8.50 | 11.58 GiB |
| 15 | 2.21 | 2.10 | 2.16 | 7.56 | 11.63 GiB |
| 16 | Failed | — | — | — | Not comparable |

#### Batch 2: 3 repetitions, 256 output tokens

| GPU layers | Rep 1 tok/s | Rep 2 tok/s | Rep 3 tok/s | Median tok/s | Median prefill tok/s | Max RSS |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 1.40 | 1.70 | 1.63 | 1.63 | 7.82 | 11.85 GiB |
| 1 | 1.64 | 1.51 | 1.50 | 1.51 | 11.33 | 11.74 GiB |
| 8 | 1.66 | 1.88 | 1.74 | 1.74 | 7.61 | 11.74 GiB |
| 10 | 1.86 | 1.76 | 1.74 | 1.76 | 7.24 | 11.54 GiB |
| 12 | 1.78 | 2.00 | 2.15 | 2.00 | 8.28 | 11.73 GiB |
| 14 | 2.03 | 1.97 | 1.95 | 1.97 | 8.05 | 11.74 GiB |
| 15 | 1.93 | 1.94 | 1.86 | 1.93 | 10.18 | 11.74 GiB |
| 16 | Failed | — | — | — | — | Not comparable |

Prefill figures are the speeds printed in each log. Maximum RSS comes from /usr/bin/time, not VRAM. Failed 16-layer runs are excluded from medians.

#### Analyzer bug and fix

The first analyzer returned identical prefill and generation values because its eval time pattern also matched prompt eval time. Those initial medians were invalid and must not be cited.

A real run was checked:
- prompt: 24 tokens, 2326.72 ms, 10.31 tok/s;
- generation: 76 tokens, 38761.43 ms, 1.93 tok/s.

The analyzer was replaced to parse separate lines: one containing prompt eval time and another containing | eval time =, excluding the prompt line. The corrected CSV also separates batches so 128- and 256-token runs are not mixed. The tables above are from the corrected analyzer output.

#### Provisional interpretation

- 8 layers improves on CPU-only; larger gains appear at 12–15 layers.
- In the longer batch, 12 layers has the highest median: 2.00 tok/s, range 1.78–2.15.
- 14 layers is more consistent in that batch: 1.95–2.03 tok/s, median 1.97.
- 15 layers reaches 2.16 tok/s median in the shorter batch but drops to 1.93 in the longer batch; it is not a universal winner.
- 16 layers fails with OOM.
- RSS of 11.5–11.9 GiB out of 14 GiB suggests possible memory pressure. Per-run swap telemetry was not retained, so variation is not attributed solely to swapping.
- Next step: use 14 layers as a conservative reference and compare 12 versus 14 over at least five repetitions, alternating order. Do not repeat the full sweep unless context, model, or memory state changes.

### 17.8 RustingStrata: NVRTC fix and measurements

The first RustingStrata GPU run encountered a PTX mismatch: system NVRTC 13.4 generated PTX .version 9.4, rejected by the driver with CUDA_ERROR_UNSUPPORTED_PTX_VERSION. This was resolved by isolating NVRTC 13.0 libraries at:

~/rusting-strata-test/vendor/nvrtc13/root/usr/local/cuda-13.0/targets/x86_64-linux/lib/

The fix used temporary LD_LIBRARY_PATH and XDG_CACHE_HOME values; system libraries were not replaced. No git clean/reset was run and vendor/ was not deleted.

| Test | Parameters / configuration | Prefill | Generation | Outcome |
|---|---|---:|---:|---|
| Strata CPU smoke | PP=128, TG=32, reps=1, threads=8 | 0.4 tok/s | 0.4 tok/s | RC 0 |
| Strata GPU benchmark | NVRTC 13.0, reps=3 | PP=128: 48.0 tok/s (35.8–55.1) | TG=32: 11.6 tok/s (10.2–12.7) | RC 0 |
| Strata GPU generation | 25-token prompt; 64 output tokens | 6.78 tok/s | 7.74 tok/s | RC 0; 18.35 s total |

Logs:
- strata-gpu-nvrtc13-reps3-20261021.log
- strata-generate-gpu-nvrtc13-20261021.log
- strata-cpu-smoke-20261021.log

During GPU generation, the plan reported:
- weights + state + scratch: 832 MB;
- KV: 96 MB for context 1024;
- prefill: 36 MB;
- expert slots: 2039 MB;
- resident experts: 1160 of 6144;
- expert hit rate: approximately 24.9% (25,681 misses);
- 64 cache swaps;
- CPU expert computation: 90.1% of generation time;
- maximum RSS: 8,089,292 KiB (approximately 7.72 GiB).

The strata bench run and 64-token generation are not the same workload as the llama.cpp sweep. The 7.74 tok/s result is promising for this MoE/cache strategy, but is one real generation run, not a directly comparable median.

### 17.9 Other offload and server attempts

- An initial llama-server attempt with 16 layers failed during VRAM allocation. That log did not retain all CLI arguments precisely enough, so no additional parameters are inferred from it.
- The case was repeated with controlled llama-cli settings (fit disabled, context 1024, batch 64, ubatch 32, 8 threads, 16 output tokens, temperature 0, seed 42). Sixteen layers failed again.
- 12 and 14 layers loaded successfully in verbose CLI logs.
- With 8 layers, most of the model remained on CPU (CPU-mapped buffer 9759.88 MiB, CUDA buffer 1885.45 MiB). More offload helps, but MoE expert computation and bandwidth remain bottlenecks.

### 17.10 Qwen3-30B-A3B-specific conclusion

1. Real local inference is verified with llama.cpp CUDA and RustingStrata CUDA.
2. The highest functional llama.cpp offload observed was 15/49 layers, but the best median in the longer batch was 12 layers; 14 layers showed lower variability.
3. 16 layers exceeds the VRAM budget for this GPU/configuration.
4. RustingStrata reached 7.74 tok/s in one real 64-token generation, with the main cost in CPU expert computation and approximately 25% cache hit rate. This is one-run evidence, not a directly comparable median.
5. The next controlled comparison must fix prompt, output length, context, warm-up, repetitions, and generation timing; RAM/swap and VRAM should also be recorded during each run.
6. Logs, CSVs, and scripts remain in ~/benchmarks/qwen3-30b-a3b-iq3-xxs. This report incorporates available textual evidence but does not automatically upload those local files.


### 17.11 RustingStrata: controlled 16-token generation test (2026-10-21)

A short controlled test used the same GGUF file, Spanish prompt, and 16-token output limit as the controlled llama.cpp test. It ran on GPU with context 1024, 8 threads, temperature 0, isolated NVRTC 13.0, and a dedicated XDG_CACHE_HOME. The purpose was to validate generation and observe expert-cache behavior; **16 output tokens are too few for a robust sustained-performance comparison**.

Model SHA-256: `292daa2b66aec59d075532d0bcf05010bf4a3b012a4216c28dc021b73d1e9ab4`.

Command used for each repetition:

~~~bash
/usr/bin/time -v -o "$OUT/time-$REP.txt" \
  ./target/release/strata generate \
    --model "$M" --gpu --ctx 1024 --threads 8 \
    --prompt "Responde brevemente en español: ¿qué es la inferencia local?" \
    -n 16 --temp 0 2>&1 | tee "$OUT/rep-$REP.log"
~~~

CUDA environment: `LD_LIBRARY_PATH` prepends `~/rusting-strata-test/vendor/nvrtc13/root/usr/local/cuda-13.0/targets/x86_64-linux/lib`; `XDG_CACHE_HOME=$OUT/cache`. Output directory: `~/benchmarks/qwen3-30b-a3b-iq3-xxs/rustingstrata-controlled-20261021`.

| Repetition | Prefill (tok/s) | Generation (tok/s) | Expert hit rate | Cache misses | Cache swaps | Maximum RSS |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2.99 | 6.67 | 19.9% | 9,846 | 32 | 7,055,728 KiB (6.73 GiB) |
| 2 | 24.41 | 31.32 | 81.7% | 2,248 | 0 | 6,062,680 KiB (5.78 GiB) |
| 3 | 26.44 | 25.66 | 81.8% | 2,238 | 0 | 6,065,568 KiB (5.78 GiB) |

All three runs exited with code 0. The median of the three generation speeds is 25.66 tok/s, but it is not a stable estimate of sustained performance: each run generated only 16 tokens and the first had a cold or much less effective cache. Repetitions 2–3, with about 81.8% cache hits, reached 31.32 and 25.66 tok/s; two warm samples are not enough to claim a definitive average. Strata reported CPU expert computation at 91.7%, 61.4%, and 67.7% of generation time, respectively.

The measurements show that cache state radically changes the result. Do not directly compare this 16-token test with the llama.cpp sweep at 128/256 tokens or the earlier 64-token Strata generation. For a final comparison, perform an explicit warm-up and at least five repetitions at a common output length, reporting the first run and warm-cache runs separately.

### 17.12 RustingStrata: PP128/TG32 benchmark with three repetitions

Exact command:

~~~bash
LD_LIBRARY_PATH="$NVRTC${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
XDG_CACHE_HOME="$HOME/benchmarks/qwen3-30b-a3b-iq3-xxs/strata-bench-cache" \
/usr/bin/time -v ./target/release/strata bench \
  --model "$M" --gpu --pp 128 --tg 32 --reps 3 --threads 8
~~~

Observed results:

| Metric | Result |
|---|---:|
| Prefill PP=128 | 58.7 tok/s |
| Reported prefill range | 13.3–91.2 tok/s |
| Decode TG=32 | 12.3 tok/s |
| Reported decode range | 8.7–14.3 tok/s |
| Expert hit rate | 19.9% |
| Cache misses | 29,536 |
| Cache swaps | 96 |
| Wall-clock time | 24.79 s |
| Maximum RSS | 8,976,260 KiB (8.56 GiB) |
| Status | Exit status 0 |

The plan reported 1,568 MB for weights+state+scratch, 384 MB KV for context 4096, 479 MB prefill, 1,557 MB expert slots, and 886/6,144 resident experts. The broad PP and TG ranges confirm substantial variability; preserve the ranges rather than presenting only the central figure.

Local log: `~/benchmarks/qwen3-30b-a3b-iq3-xxs/rustingstrata-bench-20261021.log`.

**Updated conclusion:** RustingStrata successfully completes both the benchmark and controlled generation. The PP128/TG32 benchmark reports 12.3 tok/s decode (range 8.7–14.3) and 58.7 tok/s prefill (range 13.3–91.2), while the short generation test exhibits a strong cache effect. These are not yet a strict head-to-head comparison with llama.cpp: output length, context, and execution mode differ. The 25–31 tok/s warm result with only 16 output tokens must not be extrapolated to long generations.
