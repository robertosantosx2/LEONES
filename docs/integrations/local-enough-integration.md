# local-enough Integration Analysis for LEONES

Repository: https://github.com/B0yko/local-enough
Reviewed upstream commit: 32f207e5770c857ddf23b3d1226dd6864ce0744d
Latest release: v0.1.0 (2026-09-29)
Licence: Apache-2.0
Target branch: Experimental

## Executive summary

local-enough is best integrated into LEONES as an empirical evaluation, measurement, evidence and optional routing layer, not as another inference engine.

Its core question is whether an AI task can run on owned hardware at the required quality, latency, capacity and cost. That maps closely to the LEONES evidence-first workflow.

Recommended flow:

`text
LEONES discovery/profile/candidates
        |
        v
physical runtime verification
        |
        v
local-enough bench + measurement
        |
        v
quality / latency / throughput / memory / power / cost
        |
        v
LEONES evidence artifact
        |
        v
choice / consent / deployment
`

## What local-enough provides

### Benchmark runner

The bench subsystem runs the same workload against several candidates and records quality, confidence intervals, invalid-output rate, p50/p95 latency, throughput, memory, power information where available, cost and execution metadata.

The bundled examples cover CRM extraction, BANKING77 classification, PII redaction, summarisation and entity matching. More importantly for LEONES, it supports bring-your-own tasks through task.yaml.

### OpenAI-compatible provider abstraction

Local models can either be launched by local-enough or exposed through an existing OpenAI-compatible endpoint. The latter is the important path for LEONES.

Supported by configuration examples are llama.cpp, Ollama, LM Studio and other compatible servers. This means LEONES does not need to adopt the MLX launcher.

### Measurement and economics

The project models hardware amortisation, electricity, recurring cost, workload volume, capacity, energy per task and cloud price. It can calculate break-even volumes and dedicated/shared-machine scenarios.

### Evidence/reporting

report produces Markdown and HTML reports including quality-vs-cost frontiers, per-task measurements, break-even analysis, capacity checks and routing decisions. Runs are stored in reproducible run directories.

### Router

route exposes an OpenAI-compatible POST /v1/chat/completions interface. It can select candidates that passed a calibration quality bar, apply deterministic gates, fall back along a chain and enforce data_must_stay_local constraints.

## Fit with LEONES

| LEONES area | Fit | Proposed role |
|---|---|---|
| Discovery | Medium | Candidate evaluation metadata |
| Hardware profiling | High | Measurement inputs and resource evidence |
| Candidate generation | Medium | Validate candidates already discovered by LEONES |
| Runtime selection | High | Empirical runtime comparison |
| Installation | Low/Medium | Not the main responsibility |
| Physical verification | High | Endpoint readiness + benchmark |
| Benchmarking | Very high | Core integration |
| Measurement | Very high | Core integration |
| Evidence | Very high | Core integration |
| Routing | High | Optional task-aware router |
| User consent | Low | Keep in LEONES |

## Linux/NVIDIA compatibility

The current upstream launcher is MLX-only and MLX is conditionally installed for macOS arm64. That launcher is therefore not the relevant path for the LEONES Ubuntu/NVIDIA target.

The relevant abstraction is LocalModel.base_url. LEONES can point local-enough at an already-running OpenAI-compatible endpoint.

For an ODS/llama-server deployment the conceptual configuration is:

`yaml
models:
  - id: ods-local
    kind: local
    base_url: http://127.0.0.1:8080/v1
    model: <model-id>
`

This is a major architectural advantage: LEONES/ODS owns runtime installation and startup; local-enough measures the resulting endpoint.

## ODS + local-enough

ODS can therefore sit behind local-enough as the local inference endpoint:

`text
LEONES
  |
  +-- hardware profile
  +-- model candidate
  +-- runtime profile
  |
  v
ODS / llama-server
  |
  | OpenAI-compatible API
  v
local-enough
  |
  +-- bench
  +-- measurement
  +-- report
  +-- route (optional)
  |
  v
LEONES evidence
`

The key test is not merely whether ODS answers a request. The evidence should establish whether the selected model/runtime satisfies the workload's quality, latency, throughput, memory, power, cost and capacity constraints.

## FitLLM / MANADA integration

local-enough should operate after candidate discovery and preselection.

`text
MANADA
  |
  +-- discover models/runtimes
  +-- hardware profile
  +-- FitLLM candidate filtering
  |
  v
candidate set
  |
  v
local-enough empirical evaluation
  |
  +-- quality
  +-- latency
  +-- memory
  +-- power
  +-- cost
  +-- capacity
  |
  v
evidence-backed candidates
  |
  v
LEONES choice / consent
`

This preserves an important LEONES rule: estimates and evidence remain separate. FitLLM can estimate/filter; local-enough can measure; LEONES records the evidence.

## Calibration versus test

local-enough separates calibration data from held-out test data. Calibration determines quality bars and routing choices; the test split is used for reported results.

LEONES should preserve this separation in generated task datasets:

`text
task dataset
   |
   +-- calib -> quality bar / routing decision
   |
   +-- test  -> final reported evidence
`

This is preferable to using one dataset for both selection and claimed performance.

## Deterministic gates

local-enough combines model scores with deterministic validation. For structured extraction this can include schema, required fields and grounding checks. The router can escalate after a gate failure.

This is strongly compatible with LEONES because a benchmark record can contain both model quality and validation/gate status.

Recommended evidence fields include candidate, runtime, model revision, quantisation, hardware profile, task, metric, quality score, threshold, invalid-output rate, p50/p95 latency, throughput, memory, power, cost, gate result and evidence revision.

## Router integration

The router is useful as an optional second-stage component:

`text
                    LEONES
                       |
                    task/workload
                       |
                       v
              local-enough router
                 /            \
                /              \
          local ODS           cloud
          endpoint           fallback
`

However, LEONES should own higher-level privacy and consent policy. The upstream data_must_stay_local option is a routing control, not a GDPR/compliance certification.

## Important limitations

1. Router security: upstream documents no authentication, rate limiting or multi-tenancy. Keep it on localhost or behind an authenticated gateway.
2. Router scope: it intentionally serves benchmarked task prompts, not arbitrary general-purpose prompts.
3. Streaming: the current router does not support streaming.
4. Local launcher: current launch support is MLX-only; Linux/NVIDIA should use base_url.
5. Python: upstream requires Python >=3.12. Prefer an isolated uv environment/container rather than coupling all LEONES dependencies.
6. Reference measurements: the upstream reference run is on a Mac Studio M4 Max 128 GB and must not be reused as Ubuntu/NVIDIA evidence.

## Licence and data

The software is Apache-2.0. The bundled BANKING77 data is CC-BY-4.0; other bundled benchmark datasets include synthetic data identified by the project as Apache-2.0.

LEONES should preserve upstream attribution and NOTICE requirements and should record dataset provenance for any custom benchmark.

## Recommended integration levels

### Level 0 — knowledge source
Keep the project as a methodology/reference source.

### Level 1 — evidence adapter
Recommended first implementation. Run local-enough against an already-running local OpenAI-compatible endpoint and import the measurements into LEONES evidence.

### Level 2 — automated runtime benchmark
LEONES generates task/config/route files from its own workload and hardware profile, then executes the benchmark after physical verification.

### Level 3 — multi-runtime comparison
Benchmark the same model/workload through ODS, Ollama, llama.cpp or other compatible runtimes. This separates model effects from runtime effects.

### Level 4 — task router
Use local-enough route only where measured quality and deterministic gates justify task-aware routing.

### Level 5 — upstream enhancements
Potential future contributions include generic launcher interfaces, Linux/NVIDIA launchers, vLLM/llama.cpp launchers, machine-readable evidence output, streaming and authenticated routing.

## Proposed LEONES evidence contract

`json
{
  "tool": "local-enough",
  "version": "0.1.0",
  "commit": "32f207e5770c857ddf23b3d1226dd6864ce0744d",
  "hardware_profile": "<LEONES profile id>",
  "runtime": {
    "name": "ods",
    "model": "<model>",
    "revision": "<revision>",
    "quantization": "<quantization>"
  },
  "task": "<LEONES task id>",
  "calibration": {
    "quality_bar": null,
    "candidate_score": null,
    "passed": null
  },
  "test": {
    "quality": null,
    "invalid_output_rate": null,
    "p50_latency_s": null,
    "p95_latency_s": null,
    "throughput": null
  },
  "resources": {
    "memory": null,
    "power_watts": null
  },
  "economics": {
    "usd_per_1000_tasks": null,
    "break_even_tasks_per_month": null
  },
  "evidence_status": "measured"
}
`

The exact schema should be aligned with existing LEONES evidence contracts if one already covers these fields; do not create a parallel contract unnecessarily.

## Implementation recommendation

Start without modifying local-enough.

1. Add a LEONES adapter that accepts an already-running OpenAI-compatible runtime.
2. Use ODS/llama-server as the first Ubuntu/NVIDIA endpoint.
3. Generate local-enough configuration from LEONES hardware, model and workload records.
4. Run calibration and held-out measurement after physical verification.
5. Normalise the resulting run into a LEONES evidence artifact.
6. Use the measured result to update candidate/runtime evidence, keeping estimates and measurements distinct.
7. Only later consider deploying the local-enough router.

## Assessment

Integration value: HIGH.

The strongest value is architectural: local-enough provides a concrete implementation of the distinction between a deployment that merely appears runnable and one that has been measured on the target hardware for a defined workload.

Recommended LEONES status:

`EXPERIMENTAL — HIGH VALUE / INTEGRATE AS EVIDENCE ADAPTER`

Sources:

- https://github.com/B0yko/local-enough
- https://github.com/B0yko/local-enough/releases/tag/v0.1.0
- https://github.com/B0yko/local-enough/blob/main/README.md
- https://github.com/B0yko/local-enough/blob/main/docs/configuration.md
- https://github.com/B0yko/local-enough/blob/main/src/local_enough/providers/openai_compat.py
- https://github.com/B0yko/local-enough/blob/main/src/local_enough/providers/mlx.py
- https://github.com/B0yko/local-enough/blob/main/src/local_enough/route/server.py
- https://github.com/B0yko/local-enough/blob/main/LICENSE