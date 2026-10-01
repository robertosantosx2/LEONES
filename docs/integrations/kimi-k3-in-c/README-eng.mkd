# ODS Integration Report: Kimi K3 in C

## Executive summary

[Kimi K3 in C](https://github.com/FareedKhan-dev/kimi-k3-in-c) is a highly specialized C99 inference engine that demonstrates a different way to make extremely large models executable on constrained machines: stream the model trunk from storage and keep only a bounded routed-expert cache in RAM.

It is not a general-purpose replacement for ODS's llama.cpp/llama-server path. It is better treated as an experimental, model-specific runtime that could be exposed through the same OpenAI-compatible contract used by ODS consumers.

The project is especially relevant to LEONES because it expands the definition of "fits": execution can depend on RAM, CPU, storage capacity and storage bandwidth, not only GPU VRAM and model size.

## Project characteristics

The project targets the full Kimi K3 model:

- approximately 2.78T parameters;
- approximately 1.56 TB checkpoint on disk;
- 93 layers;
- 69 Kimi Delta Attention (KDA) layers and 24 Gated MLA layers;
- 896 routed experts, with top-16 expert selection;
- native MXFP4 expert weights;
- portable C99 implementation;
- no BLAS, ML framework or GPU requirement;
- Linux x86-64 reference target, with macOS arm64 and Windows x86-64 support reported by the project;
- AVX2/FMA are used; AVX-512 is not required.

The project reports a measured peak RSS of about 8.24 GB for its low-memory execution path. This is a project measurement, not an independent ODS benchmark.

## Core technique

The key mechanism is trunk streaming.

The full model trunk is not kept resident in RAM. Instead, layers are streamed from storage through a bounded buffer while routed expert weights are kept in a separate cache. The user can trade memory for storage traffic and execution time.

The project's tuning documentation describes:

- a `--trunk-gb` budget for the trunk ring buffer/pinned layers;
- a `--cache-gb` budget for the routed-expert arena;
- a low-memory execution mode capable of running with single-digit GB of RAM;
- substantially higher throughput as more trunk data remains resident;
- very high storage traffic at low memory budgets.

The project reports roughly 108.81 GB of trunk data reread per token and about 25.8 GB of routed expert bytes per token under its described low-memory execution strategy. Consequently, fast local NVMe storage is a central performance requirement.

Its published presets include an ultra proof-of-life mode and higher-memory laptop, desktop, workstation, server and max configurations. The project reports roughly 32 s/token around its laptop preset, about 31 s/token at a 32 GB-class configuration, and around 17 s/token at a 128 GB-class configuration. These figures are project-reported reference measurements and must not be treated as expected ODS performance.

## Relevance to ODS

ODS currently uses llama-server/llama.cpp as its principal local inference runtime and exposes OpenAI-compatible APIs through its surrounding services. Kimi K3 in C should therefore be integrated as an alternative runtime, not as a modification of llama.cpp.

A suitable architecture is:

    ODS
      |
      +-- Runtime registry / router
      |
      +-- llama-server -> GGUF / llama.cpp
      |
      +-- AirLLM -> Hugging Face / SafeTensors
      |
      +-- Kimi K3 in C -> Kimi K3-specific C99 runtime
      |
      +-- LiteLLM / OpenAI-compatible API
      |
      +-- Dashboard / Open WebUI / agents

The integration boundary should be the ODS backend contract rather than model-specific code scattered through the dashboard.

## Proposed ODS extension

A prototype could live at:

    extensions/services/kimi-k3/

with:

    manifest.yaml
    compose.yaml
    Dockerfile
    server/
      main.py
      process_manager.py
      openai_api.py
    README.md

The wrapper would launch the native Kimi K3 executable and expose:

- GET `/health`;
- GET `/v1/models`;
- POST `/v1/chat/completions`;
- optionally POST `/v1/completions`;
- optionally a metrics endpoint for process/resource measurements.

The wrapper should translate ODS chat messages into the Kimi K3 engine's conversation/prompt interface and translate generated output back to OpenAI-compatible responses.

Conversation-state support is particularly interesting because the current project includes save/load state functionality. That could eventually map onto persistent ODS conversations, but this should be implemented only after the basic stateless API is validated.

## Hardware-aware manifest

This backend should not be classified as an NVIDIA-only service. Its resource profile is fundamentally different from a GPU inference server.

The manifest should describe at least:

- CPU architecture and instruction requirements;
- minimum/available system RAM;
- required free storage capacity;
- preferred storage class (local NVMe);
- approximate sequential-read capability;
- GPU requirement: none;
- model-specific checkpoint size;
- supported model identifier: Kimi K3 only;
- runtime capabilities: trunk streaming, routed-expert caching, CPU inference.

This suggests a useful ODS evolution: hardware discovery should include storage capacity and storage performance alongside CPU, RAM and VRAM.

## Fit for the user's ODS machine

The user's ODS system has an Intel i7-12650H, approximately 14 GB RAM and an RTX 3050 Laptop GPU with 4 GB VRAM.

For this runtime, the 4 GB GPU is not the limiting resource because the engine is CPU-only. The relevant constraints are:

1. sufficient free disk space for the approximately 1.56 TB checkpoint and working data;
2. fast local storage, preferably NVMe;
3. available RAM;
4. CPU throughput.

Conceptually, the machine is much more interesting for this backend than its 4 GB VRAM would suggest. However, this does not mean Kimi K3 will be practically fast on that machine. At low memory budgets the workload is heavily storage-I/O-bound, and the project's own reference measurements show that latency can be measured in tens of seconds per generated token.

A local test would therefore be useful primarily as an evidence experiment, not as a practical daily-driver deployment.

## Comparison with AirLLM

| Property | AirLLM | Kimi K3 in C |
|---|---|---|
| General-purpose runtime | Yes | No |
| Kimi K3 support | Yes | Yes |
| CPU inference | Yes | Yes |
| GPU inference | Yes | No |
| Layer/trunk streaming | Yes | Yes |
| Routed-expert streaming | Yes | Yes |
| C99 implementation | No | Yes |
| Python/PyTorch dependency | Yes | No |
| Model scope | Broad HF models | Kimi K3-specific |
| OpenAI API | Adapter required | Adapter required |
| Very low RAM target | Yes | Yes |
| Huge storage dependency | Model-dependent | Central to design |
| Best role in ODS | General alternative backend | Specialized experimental backend |

The two projects should not be treated as substitutes. AirLLM is a general memory-constrained inference approach, while Kimi K3 in C is an extremely optimized implementation for one model family.

## LEONES integration and evidence plan

Kimi K3 in C is particularly valuable for LEONES because it provides a concrete test case for resource-aware model selection.

A future LEONES benchmark should record, at minimum:

- memory budget;
- startup time;
- time to first token;
- tokens/second;
- peak RSS;
- CPU utilization;
- storage read volume;
- storage throughput;
- temperature;
- generated-token count;
- exact model/checkpoint identifier;
- output reproducibility/identity where applicable.

A memory ladder such as 8 GB, 10 GB, 14 GB, 16 GB and 32 GB would make the storage-versus-memory trade-off measurable.

LEONES should keep estimated feasibility separate from measured evidence. In particular, the project's published RAM and speed numbers must remain labelled as upstream measurements until reproduced on the target hardware.

## Integration risks

### 1. Model-specific runtime

This is not a general inference engine. ODS must represent the supported model explicitly and avoid presenting the backend as a generic model runner.

### 2. Storage requirements

A checkpoint of roughly 1.56 TB is a major operational constraint. ODS's existing hardware discovery should be extended before this backend is considered installable.

### 3. Performance at low memory

Low-RAM execution can be technically successful while being operationally impractical. ODS should expose measured throughput and not equate "starts successfully" with "usable".

### 4. API adaptation

The native engine is not inherently an OpenAI-compatible HTTP server, so a thin adapter is required.

### 5. Containerization

A container image is possible, but the 1.56 TB checkpoint and high storage traffic mean that the model should normally live on a host-mounted persistent volume rather than inside an image layer.

### 6. Lifecycle management

ODS must handle long-running native processes, cancellation, health checks, model availability and clean shutdown.

## Recommended implementation sequence

1. Add a non-default experimental extension.
2. Build the native Kimi K3 in C executable in a reproducible container.
3. Mount the model/checkpoint from persistent host storage.
4. Add a minimal OpenAI-compatible adapter.
5. Implement health/model discovery.
6. Add resource and I/O telemetry.
7. Run a controlled LEONES benchmark on several memory budgets.
8. Only then decide whether the runtime should become a normal ODS backend.

## Assessment

| Dimension | Assessment |
|---|---|
| Technical interest | High |
| ODS architectural fit | High |
| LEONES relevance | Very high |
| Generality | Low |
| CPU-only value | High |
| Relevance of 4 GB GPU | Low |
| Low-RAM potential | High |
| Storage burden | Very high |
| Expected low-RAM speed | Low/variable |
| Integration effort | Medium |
| Production readiness as an ODS backend | Experimental |
| Replacement for llama.cpp | No |

## Conclusion

Kimi K3 in C is a strong experimental candidate for ODS because it demonstrates a complementary execution strategy that ODS does not currently cover: enormous model weights can be made executable by combining CPU computation, bounded RAM, routed-expert caching and aggressive storage streaming.

Its greatest value for ODS is therefore not simply "running Kimi K3". It is the architectural lesson that model fit should be expressed as a resource strategy rather than a binary VRAM/RAM threshold.

For ODS, the correct implementation is a specialized optional backend behind the existing OpenAI-compatible contract. For LEONES, it is an excellent candidate for a reproducible evidence benchmark because it makes memory, storage and compute trade-offs directly measurable.
