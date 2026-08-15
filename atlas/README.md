# 🦁 LEONES Atlas

Atlas is the structured knowledge layer used by LEONES to explain recommendations.

## Status

**v0.2 — schema expanded; migration and validation in progress.**

Atlas is not a static model catalogue. It connects models, software, hardware, knowledge and reproducible experiments while keeping provenance explicit.

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
                       Router
                         ↓
                      Runtime
```

The Router may use Atlas only when the relevant fact is present and its evidence state is suitable. Otherwise it must return `unknown` rather than inventing a recommendation.
