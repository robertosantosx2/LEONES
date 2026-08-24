# LEONES LLMFit subproject

This directory is a Git submodule pinned to the upstream LLMFit repository.

- Upstream: https://github.com/AlexsJones/llmfit
- Pinned revision: `70fea7d2eb42d887700cb5d146879f463f37fc98`
- Role in LEONES: hardware-aware first-pass model selection and estimation.

## Documentation map

- [`../../integrations/LLMFIT/README.md`](../../integrations/LLMFIT/README.md) — canonical LEONES adapter boundary and data contract.
- [`../../sources/LLMFIT.md`](../../sources/LLMFIT.md) — source-of-knowledge ficha.
- [`../../sources/LLMFIT-REAL-HARDWARE-2026-08-20.md`](../../sources/LLMFIT-REAL-HARDWARE-2026-08-20.md) — technical verification with real hardware.
- [`../../phases/2026-08-atlas-recommendation-pipeline/`](../../phases/2026-08-atlas-recommendation-pipeline/) — route from fit to recommendation.
- [`../../phases/2026-08-hardware-matrix/`](../../phases/2026-08-hardware-matrix/) — hardware profiles.
- [`../../completed/H09-CABE-RULA.md`](../../completed/H09-CABE-RULA.md) — operational CABE/RULA boundary.
- [`../../../atlas/README.md`](../../../atlas/README.md) — canonical knowledge and evidence layer.
- [`../../../schemas/result.schema.json`](../../../schemas/result.schema.json) — canonical result contract.

## Integration boundary

LEONES does not fork or modify the upstream implementation here. The integration lives in LEONES adapters and contracts; this submodule provides the reproducible upstream source tree used by development, inspection and local validation.

```text
LEONES
  └── subprojects/LLMFit  (git submodule)
          ↓
     llmfit CLI / JSON / API / MCP
          ↓
     LEONES adapter
          ↓
     Atlas + evidence + measured performance
```

## Evidence boundary

LLMFit is an estimator, not a LEONES measurement system:

```text
LLMFit → reported / estimated
LEONES hardware observation → observed
LEONES benchmark → measured
```

The upstream result is never promoted automatically to `verified` or `measured`. Missing values remain `unknown`/`null`.

## Updating the pin

Update the submodule only after the LEONES adapter contract, offline tests and relevant smoke tests pass. Record the upstream revision in the corresponding integration documentation and source ficha.
