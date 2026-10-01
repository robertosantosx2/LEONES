# Magnitude ↔ ODS Integration Report

**Project:** Magnitude  
**Repository:** https://github.com/magnitudedev/magnitude  
**Target:** https://github.com/Osmantic/ODS  
**LEONES branch:** ods-evolution  
**Date:** 2026-10-01

## 1. Executive summary

Magnitude is best treated as an inference runtime and model-serving layer, not as an ODS frontend application.

Its OpenAI-compatible API makes an initial ODS integration possible without modifying the ODS dashboard or application layer. The first proof of concept can therefore use ODS's existing external-LLM path and LiteLLM gateway.

Recommended architecture:

    ODS
      |
    LiteLLM
      |
    Inference Router
      |-----------|-----------|
      v           v           v
    llama-server Magnitude  TensorFold
      default      optional    optional
      |-----------|-----------|
                  |
            ODS applications

Magnitude should be an optional inference backend, not a replacement for ODS's default llama-server.

Its strategic value is broader than raw inference: it combines runtime execution, hardware-aware behavior, model catalog/lifecycle concepts, speculative decoding and benchmark/telemetry capabilities. These signals can complement the future ODS Model Registry and LEONES evidence pipeline.

## 2. What Magnitude contributes

Relevant capabilities include:

- OpenAI-compatible inference API.
- Local model execution.
- Hardware-aware runtime behavior.
- Model catalog and lifecycle concepts.
- Model download/load/stop/remove operations.
- Lazy loading and unloading under memory pressure.
- Streaming responses.
- Runtime telemetry and benchmarking.
- Speculative decoding mechanisms including MTP, DFlash and DSpark.
- Multiple supported hardware/runtime paths.

Magnitude's own benchmark numbers are project-reported figures. They must be independently reproduced by LEONES before becoming measured ODS evidence.

Primary source:
https://github.com/magnitudedev/magnitude

## 3. ODS compatibility

The natural path is:

    Magnitude
        |
        | OpenAI-compatible HTTP API
        v
    ODS LiteLLM
        |
        v
    Open WebUI / Pixel / Hermes / OpenCode / n8n / other consumers

ODS already supports external LLM configuration through parameters such as:

    ./install.sh       --external-llm-url <URL>       --external-llm-provider openai-compatible       --external-llm-model <MODEL_ID>

The exact final URL composition must be verified because ODS/LiteLLM may add or expect a /v1 path.

## 4. First proof of concept

Run Magnitude independently from ODS and verify:

1. Magnitude starts correctly.
2. Health endpoint responds.
3. Model discovery works.
4. Chat completions work.
5. Streaming works where required.
6. LiteLLM can reach the endpoint.
7. Open WebUI/Pixel can issue a request through ODS.
8. Model identity remains correct end-to-end.
9. Failure and restart behavior are understood.

No ODS source modification should be necessary for this stage.

A host-running Magnitude can be reached from ODS containers through the Docker host gateway where supported, for example host.docker.internal:10100.

## 5. API and endpoint considerations

Magnitude documents an OpenAI-compatible serving endpoint around:

    http://127.0.0.1:10100/inference/v1

with model discovery and chat/completion-style operations.

ODS should treat the endpoint as runtime configuration rather than hard-code it.

The backend contract should normalize:

- base URL;
- model identifier;
- health endpoint;
- streaming;
- chat completions;
- responses API where supported;
- tool/function calling where supported;
- structured output where supported;
- authentication;
- runtime-specific options.

Applications should use a stable ODS model alias while backend-specific identifiers remain inside the inference layer.

## 6. Recommended ODS extension

After a successful POC, Magnitude can become an optional ODS inference extension:

    ods/extensions/services/magnitude/
    ├── manifest.yaml
    ├── compose.yaml
    ├── compose.nvidia.yaml
    ├── README.md
    └── ...

Conceptual manifest capabilities:

    id: magnitude
    category: inference-backend
    api: openai-compatible
    model_catalog: true
    hardware_detection: true
    speculative_decoding: true
    streaming: true
    tool_calling: true
    external_runtime: true

The exact field names must follow the current ODS manifest schema. This is an architectural proposal, not a drop-in manifest.

## 7. Docker strategy

### Stage 1 — external runtime

    Ubuntu host
    ├── Magnitude :10100
    └── ODS Docker stack
          └── LiteLLM

This is the preferred first step because it is reversible, easy to debug and keeps both projects independent.

### Stage 2 — ODS-managed extension

    ODS
    ├── LiteLLM
    ├── Magnitude
    └── applications

This provides ODS lifecycle management and reproducible deployment, but should only follow a validated POC.

## 8. Model Registry integration

Magnitude should not replace ODS's model library with a copied Magnitude catalog.

A better architecture is:

    ODS Model Registry
       ^        ^       ^
       |        |       |
    ODS data  Magnitude LEONES
              catalog    evidence

The registry should distinguish:

- model;
- revision;
- weights;
- quantization;
- backend;
- runtime;
- hardware requirements;
- estimated fit;
- configured state;
- measured performance;
- provenance.

Runtime-specific identifiers should not leak into stable application contracts.

## 9. Estimated fit versus measured evidence

This distinction is fundamental for LEONES.

Magnitude's hardware/model recommendation is useful for candidate generation and preselection.

LEONES remains responsible for:

    Discovery
       ->
    Hardware profile
       ->
    Runtime recommendation
       ->
    Candidate selection
       ->
    Consent
       ->
    Installation
       ->
    Physical verification
       ->
    Benchmark
       ->
    Measurement
       ->
    Evidence

Magnitude recommendations must remain reported/estimated until physically reproduced.

Example evidence model:

    model: example-model
    backend: magnitude
    fit:
      source: magnitude
      status: estimated
    evidence:
      source: leones
      status: measured

## 10. Hardware relevance

The current ODS development machine has approximately:

- Intel Core i7-12650H;
- 14 GB RAM;
- NVIDIA RTX 3050 Laptop GPU;
- 4 GB VRAM.

This machine is suitable for testing the integration path but is not an appropriate target for evaluating Magnitude's largest contemporary models.

Meaningful tests should focus on small quantized models and record:

- model size;
- quantization;
- VRAM usage;
- RAM usage;
- context length;
- CPU/GPU utilization;
- TTFT;
- prefill throughput;
- decode throughput;
- sustained throughput;
- peak memory;
- stability;
- errors/restarts.

Every measurement must identify the exact model revision, runtime version and configuration.

## 11. Speculative decoding

Magnitude's support for speculative decoding is relevant to ODS.

Potential methods include MTP, DFlash and DSpark.

ODS should not assume that speculative decoding improves every workload. LEONES should compare baseline and speculative configurations under identical conditions.

Useful evidence includes:

- TTFT;
- decode tok/s;
- accepted draft tokens;
- speculative rounds;
- acceptance ratio;
- memory overhead;
- total latency.

## 12. Telemetry

Magnitude runtime telemetry can complement ODS observability.

A normalized ODS backend contract could expose:

    request:
      prompt_tokens
      cached_tokens
      completion_tokens
      TTFT
      prefill_time
      decode_time
      total_time

    runtime:
      backend
      model
      hardware
      VRAM
      RAM
      speculative_rounds
      accepted_tokens

The normalized layer prevents the rest of ODS from becoming dependent on Magnitude-specific telemetry formats.

Prompts, private documents, secrets and user content should not be persisted merely for benchmarking.

## 13. Security and isolation

The preferred trust boundary remains:

    Client
      |
    LiteLLM
      |
    Inference backend

Magnitude should not receive unrestricted access to unrelated ODS services.

For an ODS-managed deployment:

- expose only required ports;
- use authenticated gateway access where appropriate;
- isolate model storage;
- define explicit volume permissions;
- keep credentials out of model metadata;
- treat plugins/skills as separate security surfaces.

## 14. Relationship with llama-server

Magnitude should not replace llama-server globally.

ODS currently uses llama-server as its default local inference foundation. Magnitude is better positioned as a complementary optimized runtime.

Future routing can select according to:

- model family;
- quantization;
- hardware;
- context size;
- latency target;
- throughput target;
- speculative decoding;
- vision/tool requirements;
- measured LEONES evidence.

## 15. Relationship with other runtimes

Magnitude should coexist with specialized runtimes.

| Backend | Primary role |
|---|---|
| llama-server | Default/general local inference |
| Magnitude | Optimized general inference plus runtime/model intelligence |
| TensorFold | Specialized optimized decoding |
| vLLM | High-throughput serving on suitable NVIDIA hardware |
| MoE runtimes | Large MoE/offload workloads |
| CPU/NVMe runtimes | Systems without practical GPU capacity |

The future router should select a compatible runtime rather than forcing every model through one engine.

## 16. LEONES integration

Magnitude can contribute at several stages:

- Discovery: available models and runtime capabilities.
- Profile: hardware/runtime information.
- Candidates: model/runtime recommendations.
- Choice: resource requirements shown to the user.
- Consent: explicit confirmation before large downloads.
- Physical verification: model files, checksums and runtime versions.
- Benchmark: independent LEONES benchmark.
- Measurement: real latency, memory and throughput.
- Evidence: provenance and reproducibility.

Magnitude is therefore a source of runtime/model intelligence, not the authority for measured compatibility.

## 17. Proposed ODS capability contract

A future backend contract should expose:

    backend.id
    backend.version
    backend.api.protocol
    backend.api.endpoint

    model.id
    model.revision
    model.source
    model.quantization

    hardware.cpu
    hardware.ram
    hardware.gpu
    hardware.vram

    capabilities.streaming
    capabilities.tool_calling
    capabilities.structured_output
    capabilities.speculative_decoding

    fit.status
    fit.source
    fit.estimated_memory

    measurement.status
    measurement.source
    measurement.ttft
    measurement.prefill_tps
    measurement.decode_tps
    measurement.peak_ram
    measurement.peak_vram

The key rule is that fit and measurement remain separate fields.

## 18. Risks and open questions

Before production integration, verify:

1. Exact API path handling through LiteLLM.
2. Model identifier translation.
3. Streaming compatibility.
4. Tool/function calling.
5. Structured output.
6. Authentication and network binding.
7. Docker-to-host networking.
8. GPU passthrough in an ODS-managed container.
9. Model download lifecycle.
10. Memory-pressure behavior.
11. Runtime restart/recovery.
12. Model compatibility coverage.
13. Speculative decoding compatibility by model.
14. Persistence and cache semantics.
15. License and redistribution implications of packaged runtime/model components.

## 19. Implementation roadmap

### MAG-ODS-0 — POC

Run Magnitude independently and connect it through ODS's existing external OpenAI-compatible path.

### MAG-ODS-1 — Contract

Define the backend capability and model metadata contract.

### MAG-ODS-2 — LEONES evidence

Add reproducible benchmark capture and distinguish estimated fit from measured results.

### MAG-ODS-3 — ODS extension

Package Magnitude as an optional ODS inference extension.

### MAG-ODS-4 — Model Registry

Normalize Magnitude catalog data into the ODS Model Registry without copying runtime-specific identifiers into application contracts.

### MAG-ODS-5 — Inference Router

Allow ODS to select between llama-server, Magnitude and other compatible inference engines.

### MAG-ODS-6 — Continuous evidence

Feed measured LEONES results back into runtime/model selection.

## 20. Final assessment

Magnitude has a strong architectural fit with ODS because its OpenAI-compatible serving model aligns with ODS's existing LiteLLM and external-LLM architecture.

The recommended integration is:

**Magnitude as an optional inference backend, not an ODS application and not a replacement for llama-server.**

Its additional value comes from combining inference execution with hardware/model intelligence, runtime lifecycle and benchmarking concepts. This creates a useful bridge between ODS, inference runtime selection, LEONES evidence and the future ODS Model Registry.

Immediate next step: perform a small, reversible POC using the external OpenAI-compatible endpoint. Only after API compatibility, model behavior and physical benchmarks are verified should Magnitude be packaged as a first-class ODS extension.

### Assessment

| Area | Assessment |
|---|---|
| OpenAI-compatible integration | Very high |
| ODS LiteLLM integration | Very high |
| Optional inference backend | Very high |
| Hardware-aware selection | Very high |
| Model Registry integration | Very high |
| LEONES integration | Very high |
| Benchmark/evidence potential | Very high |
| Dockerization | Medium |
| Replace llama-server | No |
| Recommended architecture | Optional backend |
| Immediate POC | Yes |

**Conclusion:** Magnitude is a strong candidate for the future ODS inference-backend layer and for integration with the ODS + LEONES model/evidence architecture. Production status remains pending until API path, model compatibility and physical benchmark results are verified.

## Sources

- Magnitude: https://github.com/magnitudedev/magnitude
- ODS: https://github.com/Osmantic/ODS
- LEONES: https://github.com/robertosantosx2/LEONES
