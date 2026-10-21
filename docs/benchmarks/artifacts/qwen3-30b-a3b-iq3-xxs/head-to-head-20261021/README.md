# Qwen3-30B-A3B IQ3_XXS head-to-head artifacts (2026-10-21)

This directory contains the reproducible benchmark script, structured metrics, extracted console evidence, and a checksum manifest for the original raw run files supplied after the report was published.

## Files

- `benchmark-strata-vs-llamacpp.sh`: benchmark script used for the six runs per engine.
- `results-summary.csv`: per-run throughput, output token count, elapsed time, maximum RSS, Strata cache metrics, and exit status.
- `extracted-console-evidence.txt`: excerpts from terminal output with llama.cpp timing lines and Strata throughput/cache summaries.
- `raw-archive-manifest.md`: SHA-256 and byte size for all 36 original per-run logs, GNU time reports, and exit-code files in the supplied archive.

## Test identity

- Model: `Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf`
- Model SHA-256: `292daa2b66aec59d075532d0bcf05010bf4a3b012a4216c28dc021b73d1e9ab4`
- llama.cpp: `0.7.0-dev (build 11740, commit 6fa4f6cd3)`
- RustingStrata: `1.0.1`
- Prompt: `Responde brevemente en español: ¿qué es la inferencia local?`
- Six runs per engine; all 12 recorded exit codes are zero.

## Raw evidence status

The original archive `head-to-head-20261021-raw.tar.gz` was uploaded in the conversation and verified. Its SHA-256 is `60a752fb09cf3774aec0f051bc349ee9677780fbf9c56a9ea46600952efb72dc` (1,494,277 bytes). It contains 36 original per-run files: six `rep-*.log`, six `time-*.txt`, and six `rc-*.txt` for each engine. The archive also includes a generated RustingStrata PTX/profile cache; that cache is not primary benchmark evidence and should not be versioned as a raw log.

The checksum manifest is committed here, but the archive itself and its raw log files are **not yet stored in this GitHub directory**. The benchmark report and CSV should therefore be read alongside the supplied archive when full raw output is required. The CSV and console excerpt file remain useful structured evidence, but are not substitutes for complete raw logs.

See also report section 17.13 in `docs/benchmarks/report-inferencia-dense_Octubre26.md` and its English counterpart.
