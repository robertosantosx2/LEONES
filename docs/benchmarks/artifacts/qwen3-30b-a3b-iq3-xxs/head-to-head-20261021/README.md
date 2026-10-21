# Qwen3-30B-A3B IQ3_XXS head-to-head artifacts (2026-10-21)

This directory contains the reproducible benchmark script and structured metrics transcribed from the console excerpts supplied for the LEONES report.

## Files

- `benchmark-strata-vs-llamacpp.sh`: benchmark script used for the six runs per engine.
- `results-summary.csv`: per-run throughput, output token count, elapsed time, maximum RSS, Strata cache metrics, and exit status.
- `extracted-console-evidence.txt`: excerpts from the supplied terminal output with the exact llama.cpp timing lines and Strata throughput/cache summaries.

## Test identity

- Model: `Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf`
- Model SHA-256: `292daa2b66aec59d075532d0bcf05010bf4a3b012a4216c28dc021b73d1e9ab4`
- llama.cpp: `0.7.0-dev (build 11740, commit 6fa4f6cd3)`
- RustingStrata: `1.0.1`
- Prompt: `Responde brevemente en español: ¿qué es la inferencia local?`
- Six runs per engine; all reported exit code 0.

## Evidence boundary

The original machine-local files `llama/rep-*.log`, `llama/time-*.txt`, `llama/rc-*.txt`, and corresponding `strata/*` files were **not attached to this conversation** and cannot be uploaded from the user's Ubuntu filesystem by this GitHub connection. Therefore, the CSV and console evidence are extracted/structured evidence, not a replacement for the complete original logs. Once the original output directory is uploaded or made available, these artifacts should be supplemented with the full raw logs and GNU time reports.

See also the benchmark report section 17.13 in the parent directory `docs/benchmarks/report-inferencia-dense_Octubre26.md` and its English counterpart.
