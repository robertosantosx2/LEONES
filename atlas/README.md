# 🦁 LEONES Atlas

Atlas is the structured knowledge layer used by LEONES to explain recommendations.

## Documentation protocol

Atlas follows the project-wide phased documentation rule: when a phase is completed and accepted, its architecture, rules, decisions, validation and traceability must be documented and linked from the relevant READMEs.

- [`../docs/DOCUMENTATION_PROTOCOL.md`](../docs/DOCUMENTATION_PROTOCOL.md) — project-wide rule.
- [`../docs/phases/README.md`](../docs/phases/README.md) — phase index and stable Hxx identifiers.
- [`../docs/phases/2026-08-atlas-expanded/`](../docs/phases/2026-08-atlas-expanded/) — **H06: Open LLM Atlas ampliado**.
- [`../docs/phases/2026-08-atlas-recommendation-pipeline/`](../docs/phases/2026-08-atlas-recommendation-pipeline/) — **H10 accepted**: daily Atlas → recommender pipeline.

## Status

**H10 🟢 ACEPTADA. H06 🟢 ACEPTADA / OPERATIVA.**

Atlas v0.2 has an expanded schema and an operational daily pipeline. H06 establishes the knowledge-governance boundary between the operational feed and the canonical Atlas: identity, evidence, quality, normalization and verified-only promotion.

The latest H06 closure audit recorded 193 feed rows and 193 unique identities according to the current auditor, all 193 with `unverified` quality flags, and therefore 0 canonical records promoted. This is intentional: the canonical catalogue is not populated without sufficient verified evidence.

### H06 documentation

- [`../docs/phases/2026-08-atlas-expanded/README.md`](../docs/phases/2026-08-atlas-expanded/README.md) — scope and acceptance criteria.
- [`../docs/phases/2026-08-atlas-expanded/COVERAGE-AUDIT.md`](../docs/phases/2026-08-atlas-expanded/COVERAGE-AUDIT.md) — coverage audit.
- [`../docs/phases/2026-08-atlas-expanded/IDENTITY-RULES.md`](../docs/phases/2026-08-atlas-expanded/IDENTITY-RULES.md) — canonical identity rules.
- [`../docs/phases/2026-08-atlas-expanded/EVIDENCE-RULES.md`](../docs/phases/2026-08-atlas-expanded/EVIDENCE-RULES.md) — evidence boundary.
- [`../docs/phases/2026-08-atlas-expanded/DECISIONS.md`](../docs/phases/2026-08-atlas-expanded/DECISIONS.md) — architecture decisions.
- [`../docs/phases/2026-08-atlas-expanded/H06_FINAL.md`](../docs/phases/2026-08-atlas-expanded/H06_FINAL.md) — technical closure report.

## H06 — Open LLM Atlas ampliado

### Objective

Turn the current Atlas into a more complete and auditable knowledge base for local/open LLM research without confusing catalogue coverage with empirical validation.

### The canonical boundary

```text
PROSPECCIÓN / FEED OPERATIVO
            ↓
       IDENTIDAD
            ↓
        EVIDENCIA
            ↓
        QUALITY GATE
            ↓
   VERIFIED-ONLY PROMOTION
            ↓
      ATLAS CANÓNICO
```

The operational feed is not the canonical Atlas. A record becomes canonical only through the documented promotion boundary. `atlas/catalog.json` is therefore allowed to remain empty when no feed record has sufficient verified evidence.

### Scope

```text
MODELOS
  ↓
FAMILIAS / ORGANIZACIONES
  ↓
VARIANTES / PESOS / FORMATOS
  ↓
RUNTIMES / BACKENDS
  ↓
BENCHMARKS
  ↓
PROCEDENCIA / EVIDENCIA
  ↓
JGB
  ↓
HARDWARE / RECOMENDACIÓN
```

H06 focuses first on quality and completeness of the knowledge layer. It does **not** mean that every model becomes benchmarked or verified automatically.

### Automated H06 gate

The workflow [`../.github/workflows/atlas-h06.yml`](../.github/workflows/atlas-h06.yml) executes identity and quality audits, promotes only verified feed records, validates every canonical record against `schema.json`, and publishes machine-readable audit reports.

The publication path is protected against concurrent writers. Future workflows that write to `main` must also follow the project-wide `leones-main-writers` concurrency rule with `cancel-in-progress: false`.

## Knowledge layers

- **Knowledge** — concepts and technical relationships relevant to local LLM execution.
- **Models** — models, families, variants and organizations.
- **Software** — runtimes, backends, formats and quantization.
- **Hardware** — CPU/GPU, RAM/VRAM, storage, interconnects, compute and measured bandwidth.
- **Experiments** — inference and agentic measurements.
- **Evidence** — provenance, retrieval date, reproducibility and verification state.
- **Recommendations** — facts consumed by Router when their evidence is suitable.

## External evidence

The first discovery evidence for a model should be collected from:

1. Hugging Face
2. LM Arena
3. Artificial Analysis
4. Manufacturer's official site/blog

External evidence is discovery/research evidence. It is not automatically official LEONES measurement or verified Atlas knowledge.

## MANADA

**MANADA** is the LEONES community/experiment contribution layer. It replaces the former `metaLEONES` terminology throughout the project.

MANADA submissions describe experiments without publishing operator identity or other private identifiers. They can enter the evidence pipeline as `reported`, become `reproducible` when enough information is supplied, and become `verified` only after independent checking by LEONES.

## CABE and RULA

Atlas distinguishes:

- **CABE** — whether a configuration can fit/run within the available resources.
- **RULA** — whether the configuration runs usefully under the relevant workload.

CABE considers weights, quantization, KV cache, context, runtime overhead and offloading. RULA additionally considers compute, memory bandwidth, storage behaviour, interconnect and software stack.

A configuration can therefore `CABE = yes` and still `RULA = no`.

## Evidence boundary

Atlas distinguishes at least:

- `reported` — submitted information;
- `reproducible` — enough information to reproduce the claim;
- `verified` — independently checked by LEONES;
- `rejected` — must not enter official aggregates.

External evidence and MANADA reports are never silently promoted to `verified`.

## Privacy

Atlas public records must never contain operator identity, hostname, serial number, UUID, MAC/IP, exact location, credentials, tokens or private paths.

## Integration

```text
External evidence (HF / LM Arena / Artificial Analysis / Manufacturer)
                         │
MANADA ──────────────────┤
                         ↓
                 normalization
                         ↓
                    evidence
                         ↓
                       Atlas
                         ↓
              H10 daily pipeline 🟢
                         ↓
                       Router
                         ↓
                      Runtime
```

The Router may use Atlas only when the relevant fact is present and its evidence state is suitable. Otherwise it must return `unknown` rather than inventing a recommendation.
