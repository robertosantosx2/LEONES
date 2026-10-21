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

The clean archive `head-to-head-20261021-raw-no-cache.tar.gz` was uploaded and verified. Its SHA-256 is `95496a42dd5816908d03fc373d8ef2b6f6630f84d2fd4c373287d6dbcdad6fdb` (273,761 bytes). It contains 36 original per-run files: six `rep-*.log`, six `time-*.txt`, and six `rc-*.txt` for each engine, with all recorded exit codes equal to zero. The earlier archive including a generated RustingStrata PTX/profile cache had SHA-256 `60a752fb09cf3774aec0f051bc349ee9677780fbf9c56a9ea46600952efb72dc` (1,494,277 bytes).

The checksum manifest is committed here. The clean archive itself is **not yet stored in this GitHub directory**: the available GitHub connector can create UTF-8 text files but does not expose a binary upload operation for repository files. To commit the archive from the Ubuntu checkout, copy it into this directory and run `git add head-to-head-20261021-raw-no-cache.tar.gz && git commit -m 'benchmarks: preserve raw head-to-head logs' && git push`. The CSV and console excerpt remain useful structured evidence, but are not substitutes for complete raw logs.

See also report section 17.13 in `docs/benchmarks/report-inferencia-dense_Octubre26.md` and its English counterpart.
