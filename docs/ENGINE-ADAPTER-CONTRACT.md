# Extensible inference-engine adapter contract

## Purpose

LEONES treats inference engines as replaceable implementations behind a stable measurement contract. Adding an engine must not require editing the benchmark loop. A new engine is registered in `configs/engines.registry.json`, receives an immutable source snapshot under `third_party/engines/<id>/source/`, and gets a launch/API adapter entry in the run configuration.

## Required engine identity

Every engine run records:
- registry ID and display name;
- canonical repository URL, requested ref, resolved commit and Git tree SHA;
- submodule commit state and Git LFS status;
- vendored source tree path and source snapshot status;
- build command, compiler/toolchain, feature flags and build log;
- executable path and SHA-256;
- full effective argv and environment (secret-like variables redacted);
- model file(s), tokenizer/config/chat-template files and SHA-256;
- runtime/backend/device, GPU offload, context, threads, batch, KV/cache and concurrency settings;
- stdout, stderr, API raw errors, responses and machine telemetry.

If any required provenance field is unknown, record it as UNKNOWN rather than inferring it.

## Adapter interface v1

The initial runner supports:
- `command`: argv array, never a shell string;
- `base_url`: local HTTP base URL with `{port}` substitution;
- `health_path`: readiness endpoint;
- `chat_path`: OpenAI-compatible streaming chat completions endpoint;
- `env`: explicit engine-specific environment overrides;
- `model`: optional engine-specific model artifact path;
- `source_meta`: path to `third_party/engines/<id>/SOURCE.json`.

All servers must bind to 127.0.0.1. A non-OpenAI API requires a dedicated adapter implementation; do not coerce response formats or silently drop unsupported sampling fields. The adapter must declare which controls it supports and return normalized timestamps, text, usage, errors and raw response metadata.

## Adding another engine

1. Add a unique engine object to `configs/engines.registry.json`. Include the official source URL, default immutable tag/ref, license family, model formats and protocol.
2. Run the GitHub Actions workflow **Vendor inference engine sources** from the LEONES repository. It copies the complete source tree into LEONES and records `SOURCE.json`.
3. Add the exact build recipe and toolchain notes under `docs/engines/<id>/`. Preserve all upstream license and attribution files. After building, capture the binary and build log with `scripts/capture_engine_build.py` and configure the resulting JSON as `build_meta`.
4. Add an engine config entry to `configs/engine-comparison.json`. Keep it disabled until its launch command and API semantics have been verified.
5. Add capability declarations (context limits, quantization support, backend, KV cache, speculative features, batching, concurrency).
6. Run smoke tests, then a single-engine baseline, then the full matrix.
7. The runner refuses to benchmark an engine without its pinned `SOURCE.json` and build-evidence JSON. Do not disable these gates for published runs.
8. Do not publish comparative rankings until model/tokenizer/template equivalence and backend identity are checked.

## Fairness rules

- Never silently replace a model, tokenizer, template, quantization, context or backend.
- Use the same model file and hash where all engines support it. Otherwise label the comparison as equivalent-checkpoint/format-specific and list every artifact hash.
- Separate cold-cache and warm-cache measurements.
- Separate single-request latency from concurrent throughput.
- Run all engines serially; unload, sample the host and require baseline recovery before the next engine/profile.
- Store every repetition. Never report best-of-N as the only result.
- Keep raw output and logs; summaries are derived artifacts, not substitutes.
- A failed/unsupported engine remains in the report with an explicit status.

## Versioning

The registry schema and adapter protocol are versioned. Breaking changes require a schema version increment and migration notes. Source snapshots are immutable; an upstream update creates a new snapshot commit and never overwrites historical benchmark artifacts.
