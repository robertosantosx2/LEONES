# Qwen3.5-4B: three-runtime benchmark (2026-10-20)

## Status and scope

This report records a physical-hardware, single-request API comparison of three local inference runtimes on the same Ubuntu workstation. It is a practical runtime comparison, not a controlled model-quality evaluation and not a fully apples-to-apples engine microbenchmark.

- Run directory: `~/qwen35-4b-benchmark-fixed-20261020-215243`
- Benchmark script: `~/benchmarks/benchmark_qwen35_4b_three_engines_fixed_v2.sh`
- Host: Ubuntu x86_64; Intel Core i7-12650H (16 logical CPUs); 14 GiB RAM; NVIDIA RTX 3050 Laptop GPU (4 GiB VRAM); NVIDIA driver 580.178.04; CUDA 13.0.
- Requests: 3 measured trials per runtime, 32 generated completion tokens per request; warm-up was recorded separately and excluded from the measured JSONL.
- Output: Spanish response, HTTP 200 for every measured request, all responses stopped at the 32-token limit (`finish_reason=length`).
- Prompt, parameters, server logs and environment details are retained in the local run directory listed above.

## Results

| Runtime | Model / quantization | Median total request time | Median output speed | Median TTFT |
|---|---|---:|---:|---:|
| TensorFold (CUDA backend) | `mlx-community/Qwen3.5-4B-MLX-4bit` (MLX-4bit) | 0.7066 s | 54.708 tok/s | 0.1303 s |
| llama.cpp CUDA | `qwen3.5-4b-Q4_K_M.gguf` (GGUF Q4_K_M) | 0.8680 s | 47.646 tok/s | Not available as a comparable client-side measurement |
| RustingStrata (CUDA) | `qwen3.5-4b-Q4_K_M.gguf` (GGUF Q4_K_M) | 0.8384 s | ~38.17 tok/s estimated as 32 tokens / total request time | Not exposed by the API |

TensorFold prefill was approximately 228–232 tok/s in these trials. llama.cpp also returned backend prompt/prediction metadata; client-side TTFT was not available from the parser used in this run.

### Per-trial observations

| Runtime | Trial | Output tok/s | Total request time | TTFT |
|---|---:|---:|---:|---:|
| TensorFold | 1 | 54.663 | 0.7094 s | 0.1324 s |
| TensorFold | 2 | 54.708 | 0.7066 s | 0.1303 s |
| TensorFold | 3 | 54.771 | 0.7058 s | 0.1302 s |
| llama.cpp CUDA | 1 | 47.498 | 0.9544 s | Not available |
| llama.cpp CUDA | 2 | 47.646 | 0.8680 s | Not available |
| llama.cpp CUDA | 3 | 47.723 | 0.7578 s | Not available |
| RustingStrata | 1 | Not exposed | 0.8384 s | Not available |
| RustingStrata | 2 | Not exposed | 0.8381 s | Not available |
| RustingStrata | 3 | Not exposed | 0.8384 s | Not available |

The RustingStrata estimate of ~38.17 tokens/s is computed from the fixed 32-token output divided by the median total request time. It is **not** the engine's internal decode throughput and must not be compared as if it were the same metric as the output-speed figures exposed by the other runtimes.

## Interpretation

- TensorFold was fastest in this particular short, warm API request, with a median output speed of 54.708 tok/s.
- Its reported output speed was about 14.8% higher than llama.cpp CUDA's 47.646 tok/s in this run.
- This is a practical comparison rather than a strict same-artifact comparison: TensorFold used an MLX-4bit model, while llama.cpp and RustingStrata used the GGUF Q4_K_M artifact.
- Three trials and a 32-token output cap are sufficient for an initial latency snapshot, not for claims about long generation, long context, quality, concurrent load, energy use, or broad statistical significance.
- RustingStrata's API did not expose internal output-speed or TTFT measurements to the client, so those metrics are marked unavailable rather than fabricated.
- The llama.cpp response included an empty `<think>...</think>` wrapper despite the reasoning-off/template settings. The generated answer itself was coherent Spanish.

## Execution and report-generation note

All three runtime tests completed successfully with HTTP 200 and 32 completion tokens per trial. The benchmark script then failed only while generating its summary due to an extra closing parenthesis in the Python report-generation snippet (line 302). The CSV and Markdown summary were regenerated from the existing `results.jsonl`; the engines were not rerun to repair the report.

## Reproducibility and local artifacts

The local run directory contains the original `results.jsonl`, regenerated `results.csv` and `summary.md`, server logs (`tensorfold-server.log`, `llama-cpp-server.log`, `rusting-strata-server.log`), `environment.txt`, `nvidia-smi-before.txt`, `nvidia-smi-after.txt`, and `benchmark.log`.

Only the per-trial measurements and documented interpretation above are transcribed into this repository report. The full raw JSONL and machine logs are still local in the run directory; they are not represented here as uploaded raw artifacts.

## Next validation step

Run a follow-up profile with a fixed 128- or 256-token output limit, the same prompt and sampling parameters, and capture peak GPU memory. For strict cross-runtime comparisons, align model artifact/quantization and collect engine-internal generation metrics for RustingStrata. Keep these results as a separate execution rather than overwriting this record.

## Prefill and model-load time (separate measurements)

These figures come from earlier runtime-specific runs on the same workstation, not from the three-trial API table above. They are included as reference only; the prompts, context lengths and measurement boundaries differ.

| Runtime | Prefill measurement | Model load / startup measurement | Scope and caveat |
|---|---:|---:|---|
| TensorFold, Qwen3.5-4B MLX-4bit | ~228–232 tok/s in the 2026-10-20 short API run | ~9.9 s to load the model in a separate startup observation | The ~9.9 s is model-load/startup observed in TensorFold logs; not included in the warm API request latency. |
| llama.cpp CUDA, Qwen3.5-4B GGUF Q4_K_M | Earlier runs varied by prompt: ~118.14, 51.99 and 22.31 tok/s in one run; a separate run reported ~141.2 tok/s | ~1.83 s from `load_model` starting at ~0.188 s to the “model loaded” log at ~2.019 s | Prefill varies with prompt/workload; these values are from a separate historical run and should not be treated as the current API test's prefill result. |
| RustingStrata, Qwen3.5-4B GGUF Q4_K_M | `strata bench`: 915.3 tok/s at PP=128; 986.5 tok/s at PP=512 | Not recorded in the available log evidence | Separate `strata bench` run with context 1024, `--tg 64 --reps 3`; not comparable directly to API prefill figures. |

### Interpretation

- **Prefill** measures processing prompt/input tokens; it is not generation speed.
- **Model-load time** measures the startup/model initialization phase and is distinct from the time for a request sent to an already-running server.
- RustingStrata's high prefill figures came from its own benchmark harness and different prompt batch sizes (PP=128/512). Do not rank them directly against API-derived TensorFold or llama.cpp figures.
- The three-runtime API test above did not capture a comparable model-load duration for all three engines. Missing load timing is marked as not recorded rather than inferred.

