# LEONES adapter layer

The adapter layer is the boundary between LEONES and optional external deployment/runtime projects.

## Current pins

- ODS: `v2.6.0` / `f461b3e5e6e3f21077eefb6ca39bc49a2f0b0838` — verified against the project's GitHub release page on 2026-08-20.
- Magnitude: **not pinned yet**. Active release automation is visible, but LEONES does not treat `main` as a benchmark version.

## Why Magnitude remains unpinned

A benchmark-grade integration needs a concrete release/tag or audited commit plus its runtime/package lock information. Until that exists, Magnitude may be researched and integrated structurally, but it cannot produce `VERIFIED` benchmark measurements.

## ODS installation boundary

ODS 2.6.0 documents a public installer and requires Docker. LEONES should not pipe an unpinned branch into a benchmark environment. The adapter must first resolve a pinned release, record the environment manifest, then perform installation/verification.

## Magnitude execution boundary

Magnitude documents local macOS/Linux support (Windows via WSL), local inference, hardware profiling, model configuration, file/command tools and long-running coding tasks. These capabilities make it a strong candidate for A07, but the benchmark must record the exact CLI/runtime/model configuration and grade the resulting artifact independently.

## Verification rule

```text
external claim
    !=
LEONES measurement
```

Only a reproducible run with a pinned environment, trace and versioned grader can become verified evidence.
