# LEONES + ODS — Inference Configuration Discovery (ICD)

**Date:** 2026-10-06  
**Status:** EVOLUTION / RESEARCH  
**Scope:** LEONES + ODS execution architecture

## Conclusion

LEONES + ODS should evolve from model/backend selection toward **Inference Configuration Discovery (ICD)**.

The question changes from “what model can this GPU run?” to:

> **What inference configuration produces the best real capability on this hardware, for this workload and this objective?**

A complete configuration includes model, quantization, engine, GPU/CPU/RAM/SSD placement, context, KV-cache, expert cache, prefetch, offload, speculative decoding/MTP, runtime flags and measurements.

## Why Strata is relevant evidence

Research on the original **Strata (Niko1221/Strata)** repository shows a different approach to large MoE inference: total parameter count alone does not determine whether a model is useful on a consumer GPU.

The published data motivating this research describe Qwen3.8-Flash-Next, a 125B-parameter model, with heterogeneous placement and adaptive expert management. Reported external figures include approximately:

| Hardware | Rendimiento comunicado | Estado |
|---|---:|---|
| RTX 5070 12 GB | ~94 tok/s | external evidence |
| RX 9070 XT 16 GB | ~60 tok/s | evidencia externa |
| GPUs de 24 GB | ~100–140 tok/s | evidencia externa |

The material also describes a reference configuration of 12 GB+ GPU memory, 32 GB+ RAM and about 80 GB of disk, keeping hot model parts on the GPU and other parts in system memory with low-bit compression.

**These figures are not LEONES measurements.** They are external evidence motivating ICD and must be reproduced before entering the LEONES measured-evidence layer.

## Architectural change

The traditional approach is: VRAM suficiente → FIT.

ICD proposes: modelo + hardware + almacenamiento + capacidades del runtime + estrategia → configuraciones candidatas → benchmark → capacidad real medida.

For MoE, relevant variables include active parameters, expert count, experts/token, routing behaviour, expert residency, caching, memory tiers and transfer costs.

## Strata within ODS

Strata should be incorporated as an **experimental execution provider / capability profile**, not merely another backend.

Capabilities of interest for the ODS registry:

- ejecución sparse-MoE;
- colocación heterogénea GPU + CPU/RAM;
- asistencia/paging desde SSD;
- caché adaptativa de expertos;
- cuantización de pocos bits;
- ejecución de modelos cuyo peso total supera la VRAM;
- API local compatible con OpenAI;
- API compatible con Anthropic;
- capacidades de gestión mediante MCP;
- soporte multi-GPU cuando corresponda.

The registry must always separate engine capabilities from model licence and weight availability.

## ICD in the LEONES methodology

The existing sequence is extended:

**DISCOVERY → PROFILE → CANDIDATES → CHOICE + CONSENT → INSTALL → PHYSICAL VERIFICATION → INFERENCE CONFIGURATION DISCOVERY → BENCHMARK → MEASUREMENT → EVIDENCE**

ICD discovers and compares execution configurations; it does not automatically turn an external claim into a measurement.

## Configuration dimensions

ODS should be able to compare, for example:

- mismo modelo + Q4 + llama-server;
- mismo modelo + offload CPU/RAM;
- cuantización Q3 + caché adaptativa de expertos;
- expertos calientes en GPU y fríos en RAM;
- paging de expertos mediante NVMe;
- speculative decoding;
- configuración híbrida/remota como fallback.

The best configuration depends on the objective: interactive latency, throughput, quality, context, privacy, energy, storage or cost.

## Evolved architecture

The chain becomes:

**Usuario/carga → perfil hardware/workload → Capability Registry → ICD → búsqueda de configuraciones → benchmark controlado → evidencia → mejor configuración real**

In this architecture:

- **FATE** aporta predicción de expertos.
- **Edge0** aporta prefetch/streaming.
- **HOBBIT** aporta caché adaptativa y precisión.
- **HybriMoE** aporta colaboración CPU/GPU.
- **Strata** aporta ejecución MoE heterogénea.
- **WARP** aporta una estrategia especializada de paging/NVMe.
- **TensorFold** aporta un runtime especializado de alto rendimiento.

These projects do not need to become independent backends: their capabilities can participate in configuration composition and discovery.

## Evidence and status

LEONES preserves the separation:

- **REPORTED** → project/community claim.
- **ESTIMATED** → prediction/model.
- **OBSERVED** → physically observed state/configuration.
- **MEASURED** → controlled LEONES benchmark.

Therefore, Strata throughput figures remain **REPORTED / EXTERNAL** until reproduced.

## Impact on fit

Future recommendation should distinguish:

**MODEL FIT → CONFIGURATION FIT → PERFORMANCE FIT → TASK FIT → PRIVACY/COST FIT**

A model that starts but provides unusable latency is not a good recommendation. Likewise, total weights exceeding VRAM do not automatically make a model infeasible if a heterogeneous configuration can provide useful capability.

## Planned evolution

1. Define a canonical **Inference Profile** schema.
2. Extend the ODS Capability Registry with execution capabilities.
3. Represent VRAM → RAM → NVMe → remote explicitly.
4. Add MoE-specific properties.
5. Generate candidate configurations, not only model/runtime candidates.
6. Run comparable LEONES benchmarks.
7. Store measured configurations as reusable evidence.
8. Feed future discovery with configurations that have worked.
9. Treat remote providers as another configuration, with explicit privacy and cost.

## Decision

**ICD becomes a first-class concept in LEONES+ODS evolution.**

Strata is incorporated as external experimental evidence and as a candidate heterogeneous MoE execution provider. Its published figures are not considered LEONES measurements until reproduced.

The strategic evolution is summarized as:

> **LEONES discovers what is possible; ODS discovers how to execute it best.**

The goal is no longer only to expand the supported-model list, but to build reusable evidence for:

**modelo + hardware + configuración de inferencia → capacidad real**

## Primary source

Strata — original repository: https://github.com/Niko1221/Strata