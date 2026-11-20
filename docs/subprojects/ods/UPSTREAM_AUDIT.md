# ODS upstream audit — 2026-08-20

## Scope

This audit covers the **official `Osmantic/ODS` repository** used by LEONES. The canonical upstream snapshot is the immutable commit:

`5a4450765976e2ad2792b9ac8927f4873dac60f6`

This is **Osmantic Deployment System**, not the historical `sentient-agi/OpenDeepSearch` Python project that was previously inspected in a local Debian checkout. The latter must not be mixed into the ODS subproject.

## Identity and provenance

- Repository: `Osmantic/ODS`
- Branch at audit time: `main`
- LEONES snapshot: `5a4450765976e2ad2792b9ac8927f4873dac60f6`
- License advertised by the upstream README: Apache 2.0
- Stable release advertised upstream: `v2.6.0`
- Runtime/product directory: `ods/`

The upstream README explicitly distinguishes the fast-moving `main` branch from stable releases and recommends pinning a tagged release or audited commit for stable consumption.

## Architecture observed

ODS is a local/private AI server stack rather than a Python package exposing `opendeepsearch` modules. The repository root contains project coordination, installers, CI and documentation; the product runtime lives below `ods/`.

The installer entrypoint is `ods/install.sh`. It dispatches to the platform-specific installer and supports flags including `--dry-run`, `--skip-docker`, `--non-interactive` and model/runtime options.

## Important correction to the previous audit

The previous local Debian audit imported:

- `opendeepsearch`
- `BaseSemanticSearcher`
- `InfinitySemanticSearcher`
- `JinaReranker`
- Python dependencies such as `transformers`, `torch`, `langchain`, etc.

Those findings belong to a **different/historical OpenDeepSearch Python tree**. They are not defects in `Osmantic/ODS` and must not be presented to the ODS maintainers as defects in this repository.

LEONES therefore keeps that local tree out of the ODS submodule and does not patch it.

## Current ODS audit findings

### 1. Reproducibility

The upstream documentation correctly acknowledges that `main` moves quickly and recommends pinning an audited commit or tagged release for stable consumption. LEONES therefore pins the submodule to an immutable SHA.

**Proposal to upstream:** keep making every externally consumed installer/runtime reference explicit and auditable, especially when bootstrap paths resolve `main` dynamically.

### 2. Installer validation

`ods/install.sh` is a small dispatcher that resolves the platform-specific installer and delegates to it. This makes the entrypoint suitable for a lightweight syntax/smoke gate before any Docker or hardware-dependent validation.

**Proposal to upstream:** retain a zero-prerequisite syntax/dry-run gate for the dispatcher and platform dispatch paths, independent of GPU, Docker and model availability.

### 3. Platform matrix

The README documents Linux, Windows/WSL2 and macOS Apple Silicon support and lists tested distributions/hardware paths.

**Proposal to upstream:** continue maintaining the support and validation matrices as executable/reproducible evidence rather than relying only on prose claims.

### 4. Stable versus development consumption

The README states that `main` moves quickly while `v2.6.0` is the current stable release at the audited snapshot.

**LEONES policy:** development auditing may track an audited SHA; production-oriented integrations should prefer a release/tag once the corresponding compatibility gate is green.

### 5. Local hardware boundary

ODS explicitly targets heterogeneous local hardware and performs hardware/model selection during installation. LEONES will therefore not treat a single Debian laptop as the source of truth for ODS software correctness.

Debian is reserved for measured hardware validation after the upstream software contract passes in reproducible CI.

## Candidate upstream improvements to report

These are **proposals**, not claims that the upstream project is broken:

1. Add a documented minimal CI smoke command covering installer syntax, dispatcher resolution and `--dry-run` without Docker/GPU requirements.
2. Keep bootstrap/install provenance explicit when a command consumes `main`; provide a stable/audited-ref path in all supported installation instructions.
3. Continue separating release validation from machine-specific hardware validation.
4. Keep the support matrix and model-selection claims tied to machine-readable/versioned validation evidence.
5. Document the intended integration surface for downstream projects such as LEONES: supported install entrypoints, stable configuration interfaces and supported extension points.

## LEONES integration policy

1. The ODS submodule remains byte-for-byte upstream at its pinned commit.
2. LEONES-specific adapters, tests and documentation live outside the submodule.
3. Any genuine ODS defect discovered by LEONES is first reproduced against the pinned upstream tree.
4. If it is confirmed, LEONES reports it upstream rather than silently modifying the submodule.
5. A local workaround is permitted only in a clearly separated LEONES integration layer and must not be represented as an upstream fix.

## Debian finding

The local Debian experiment installed CPU-only PyTorch successfully after an attempted CUDA-enabled installation exhausted a temporary filesystem quota. That Python environment was useful for discovering that the local tree was not the same project as the official ODS snapshot.

It is **not** part of the ODS baseline and should now be removed from the Debian machine.
