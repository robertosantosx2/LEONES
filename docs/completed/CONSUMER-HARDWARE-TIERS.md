# Consumer hardware tiers — LEONES v1

## Principle

LEONES does **not** own a new hardware scoring model.

The authoritative inputs are:

1. **ODS hardware tiers** for ODS deployments.
2. **LLMFit hardware detection + fit analysis** for general local model selection.
3. **Magnitude hardware profiling/recommendation** for Magnitude agent deployments.

The LEONES UI may group these into human-readable consumer bands, but those bands are aliases/views only.

## ODS native NVIDIA envelope

ODS currently documents:

| ODS tier | Memory envelope | Example | ODS role |
|---|---:|---|---|
| 0 | CPU fallback / low memory | CPU-only | bootstrap/lightweight |
| 1 | 8 GB discrete VRAM | RTX 4060-class | local entry |
| 2 | 12 GB discrete VRAM | RTX 4070-class | local mainstream |
| 3 | 24 GB discrete VRAM | RTX 4090/A6000 | enthusiast |
| 4 | 48 GB discrete VRAM | A6000 Ada/L40S | high-memory |
| NV_ULTRA | 90+ GB discrete VRAM | multi-GPU A100/H100 | ultra / multi-GPU |

These are **ODS's current classification and catalog-selection envelopes**, not LEONES thresholds.

ODS also documents Apple Silicon, AMD Strix Halo and Intel Arc native tiers. LEONES preserves those names rather than flattening them into NVIDIA-like buckets.

## LLMFit capability state

For each selected model/configuration, LEONES records the LLMFit result instead of calculating a parallel score:

- `Perfect`
- `Good`
- `Marginal`
- `TooTight`

and:

- `GPU`
- `MoE`
- `CPU+GPU`
- `CPU`

plus memory requirement/availability, selected quantization and estimated speed where supplied.

`Perfect`/`Good`/`Marginal`/`TooTight` retain LLMFit semantics. In particular, CPU-only does not become `Perfect`, and `TooTight` is not a candidate for execution.

## Magnitude capability state

Magnitude is not converted into a LEONES numeric tier. Its own onboarding modes remain:

- Balanced
- Best Quality
- Fastest
- Lightweight

Magnitude profiles the machine, recommends models and configures its local agent. LEONES records the chosen mode and resulting model/configuration as source-attributed data.

## LEONES presentation bands

For a consumer-facing table, LEONES may show:

| Presentation band | Source-backed interpretation |
|---|---|
| Entry | ODS low tier or equivalent detected hardware; LLMFit determines actual model fit |
| Mainstream | ODS tier 1–2 or equivalent; model selection remains LLMFit/ODS/Magnitude-owned |
| Enthusiast | ODS tier 3 / ~24 GB-class or equivalent |
| High-memory | ODS tier 4 / ~48 GB-class or equivalent |
| Ultra / multi-GPU | ODS NV_ULTRA or another native high-memory/multi-GPU classification |

These labels MUST NOT be used as inputs to model scoring.

## Why this is intentionally not a new tier system

The model catalog changes. Quantization changes. Runtime support changes. Unified-memory platforms do not map cleanly to discrete VRAM. MoE models further break a simplistic parameter-to-tier mapping.

LLMFit already handles dynamic quantization, MoE fitting, run modes and speed estimation. ODS already owns deterministic deployment tiers and catalog selection. Magnitude already owns agent-oriented hardware profiling and model setup.

Therefore LEONES stores the source facts and presents them; it does not create a fourth competing selector.

## Benchmark implication

A hardware tier is never evidence of performance.

After selection/configuration, LEONES must measure the actual model/runtime/hardware combination. The benchmark result records the exact hardware, runtime, model revision, quantization, context and command.

Task-completion benchmarks then measure whether the selected system actually completes the user's intended work. This is the decisive layer for recommendations.
