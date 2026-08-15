# 🦁 LEONES Atlas

Atlas is the structured knowledge layer used by LEONES to explain recommendations.

## Documentation protocol

Atlas follows the project-wide phased documentation rule: when a phase is completed and accepted, its architecture, rules, decisions, validation and traceability must be documented and linked from the relevant READMEs.

- [`../docs/DOCUMENTATION_PROTOCOL.md`](../docs/DOCUMENTATION_PROTOCOL.md) — project-wide rule.
- [`../docs/phases/README.md`](../docs/phases/README.md) — phase index and stable Hxx identifiers.
- [`../docs/phases/2026-08-atlas-recommendation-pipeline/`](../docs/phases/2026-08-atlas-recommendation-pipeline/) — **H10 accepted**: daily Atlas → recommender pipeline.

## Status

**H10 🟢 ACEPTADA. H06 🔵 SIGUIENTE.**

Atlas v0.2 has an expanded schema and an operational daily pipeline, but the Atlas knowledge layer itself remains under active expansion and validation. H06 is the next work unit: improve model/family/organization/benchmark/provenance coverage and strengthen the evidence contracts that feed JGB, hardware and recommendation layers.

## H06 — Open LLM Atlas ampliado

### Objective

Turn the current Atlas into a more complete and auditable knowledge base for local/open LLM research without confusing catalogue coverage with empirical validation.

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

H06 will focus first on the quality and completeness of the knowledge layer. It does **not** mean that every model becomes benchmarked or verified automatically.

### Acceptance direction

H06 should be considered complete only after its own implementation, validation, documentation and evidence are accepted according to the project-wide phase protocol. Its acceptance must be independent of the already-accepted H10 pipeline.

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

## Hardware discovery

A hardware profile must go beyond RAM/VRAM capacity. Where possible it records or measures:

- CPU/GPU compute capability, including FLOPS/MFLOPS/GFLOPS measurement or a clearly identified estimate;
- memory type, capacity, channels, theoretical and measured bandwidth and latency;
- storage type, protocol/interface, bus/link, sequential/random throughput and latency;
- bandwidth for relevant data paths rather than one generic bandwidth number;
- interconnects and offloading paths.

Storage performance therefore depends not only on whether a device is SSD/NVMe/SATA, but also on its protocol, bus, link and connection to the motherboard.

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
