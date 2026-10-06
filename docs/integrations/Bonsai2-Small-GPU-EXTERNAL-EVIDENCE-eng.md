# Bonsai 2 27B / small-GPU evidence — external experimental evidence source

Incorporation date: 2026-10-06

## LEONES classification

- Type: external experimental evidence source.
- Status: REPORTED / MEASURED BY EXTERNAL PROJECT; NOT REPRODUCED BY LEONES.
- Role: evidence for calibrating the LEONES + ODS selection model.
- Dependency: none. LEONES must not make bonsai2-small-gpu a structural dependency.
- Source project: sudoingX/bonsai2-small-gpu.
- Source model: Ternary Bonsai 2 27B PTQ1_0 with MTP.
- Relevant runtime: PrismML llama.cpp fork and bundles published by the project.
- Model: sudoingx/Ternary-Bonsai-2-27B-PTQ1_0-MTP-GGUF.
- Kernel: PrismML llama.cpp PR #218.

## 1. Strategic finding

The research requires LEONES + ODS to change its decision unit.

The old question is:

> Which model fits my GPU?

The target question becomes:

> Which inference configuration produces the best real capability on my GPU?

The selection unit is no longer only the model. It becomes an Inference Profile:

    hardware + model + quantization + runtime + kernel
    + GPU layers + context + KV-cache + MTP
    + vision + parallel slots + reasoning effort
    + flags + measured evidence

The same model can have radically different capabilities depending on runtime, kernel, context, cache and hardware.

## 2. Why Bonsai 2 is especially useful

Bonsai 2 demonstrates a chain of optimization:

    Qwen 3.8 27B
          |
          v
    ternary/PTQ1_0 compression
          |
          v
       ~5.95 GB
          |
          +--> PrismML llama.cpp
          +--> optimized kernel
          +--> Qwen 3.8 MTP head
          +--> q4_0/q8_0 KV cache
          |
          v
    hardware-specific serving profiles

The correct conclusion is not «27B needs 6 GB», but that a specific combination of representation, runtime, kernel, context, cache and hardware can make a 27B a viable capability for GPUs traditionally considered small.

## 3. Available external evidence

The repository publishes VRAM-tier serving lines, scripts, GPU sweeps, kernel results and reproducible procedures. Its main figures come from an RTX 3060 12 GB and an RTX 5060 Ti 16 GB, while other cards appear as contributions.

| Hardware | Configuration | Context | External result |
|---|---|---:|---:|
| RTX 3060 Ti 8 GB | Bonsai 2, MTP off | ~96K | ~42.8 tok/s |
| RTX 3060 12 GB | Bonsai 2 + kernel + MTP | 131K | ~50.1 tok/s |
| RTX 5060 Ti 16 GB | Bonsai 2 + MTP + vision | 262K | ~67.3 tok/s |
| RTX 3090 24 GB | Qwen 3.8 27B Q4 + MTP | 262K | ~41.3 tok/s |

These are external evidence figures, not LEONES measurements.

The source also documents an approximate RTX 3060 12 GB fresh-decode jump from 26.3 to 40.5 tok/s with the optimized kernel before MTP, and documents greedy-output equality in its MTP tests with batch invariance.

## 4. The kernel changes effective capability

The same GPU and weights can produce approximately:

    stock kernel       -> ~26 tok/s
    optimized kernel   -> ~40 tok/s
    kernel + MTP       -> ~50 tok/s

Therefore model + GPU does not determine performance by itself.

ODS should represent runtime and kernel variant as part of the execution profile.

## 5. MTP is not a binary model property

MTP/speculative decoding depends on the available head, compatible runtime, configuration, verification cost, context, batch and kernel.

Its benefit can be large at fresh context and decrease as context grows. Therefore MTP ON does not mean always faster. Future selection must be able to choose MTP ON/OFF from the complete profile.

## 6. Context is a capability dimension

VRAM does not define one capability. The 8 GB evidence shows a viable zone around 96K and a sharp drop around 112K on the RTX 3060 Ti.

A record such as «model -> 8 GB» is insufficient. It needs:

    hardware + model + context + KV + runtime
        -> measured capability

## 7. KV cache is part of the decision

The research shows that K/V quantization can free VRAM to increase context.

    weights + KV cache + context + runtime overhead
        = real memory requirement

ODS should not compare models only by file size.

## 8. 8 GB changes category

The source presents an 8 GB GPU as an agent card when the inference stack is optimized for it. This does not mean every 27B works on 8 GB; it means effective capability depends on:

    VRAM + compression + quantization + runtime
    + kernel + context strategy + KV + MTP

A simple 8 GB = small models classification is no longer sufficient.

## 9. 6 GB and 4 GB: experimental boundary

The source reports 6 GB as problematic for this Bonsai 2: some layers no longer fit on GPU and performance falls into a chat-useful but agent-poor range.

This matters for the 4 GB RTX 3050 Laptop in the LEONES reference environment. We must not extrapolate 8 GB evidence to 4 GB. LEONES must produce its own physical evidence at 4 GB.

## 10. New entity: Inference Profile

LEONES + ODS should evolve toward an explicit entity containing:

- hardware: GPU, VRAM, RAM, driver, accelerator;
- model: family, parameters, active parameters, modality, license;
- representation: format, quantization, compression;
- runtime: engine, version/ref, API;
- kernel: implementation and version/ref;
- execution: GPU layers, context, KV type, batch, slots, MTP, vision, reasoning effort;
- evidence: source, date, provenance, status and measurements.

## 11. New LEONES / ODS boundary

LEONES should discover hardware, define workload, generate candidates, preserve provenance, record configurations, run physical experiments, measure and preserve evidence.

ODS should install/serve, expose capabilities, select or compose execution strategy, apply runtime/configuration, operate local/hybrid/remote and consume available evidence.

The separation is:

    LEONES: prediction + experiment + evidence
                    |
                    v
    ODS: execution + orchestration
                    |
                    v
             physical inference
                    |
                    v
                measurement
                    |
                    v
                 LEONES

## 12. From model selector to capability selector

BEFORE:

    hardware -> model selector -> «Qwen 4B fits»

TARGET:

    hardware + workload
          |
          v
    candidate models
          |
          v
    candidate inference profiles
          |
          +--> runtime
          +--> quant
          +--> kernel
          +--> context
          +--> KV
          +--> MTP
          +--> flags
          |
          v
    estimated capability
          |
          v
    physical benchmark
          |
          v
    measured capability
          |
          v
    best real configuration

## 13. Integration with FATE + Edge0 + HOBBIT + HybriMoE

The evidence reinforces the existing strategic line:

    FATE -> prediction
             |
             v
          Edge0 -> prefetch
             |
             v
          HOBBIT -> cache / precision adaptation
             |
             v
          HybriMoE -> GPU / CPU / RAM-NVMe
             |
             v
          runtime
             |
             v
          measured capability

Bonsai 2 demonstrates that even before expert paging there is a representation, kernel, context and speculative-decoding optimization layer that belongs in the same capability reasoning.

## 14. External evidence vs LEONES evidence

The source must be recorded as:

    EXTERNAL
    COMMUNITY
    MEASURED
    NOT_REPRODUCED_BY_LEONES

It must never automatically become a LEONES measurement.

Correct chain:

    external report
          |
          v
    candidate configuration
          |
          v
    LEONES reproduction
          |
          v
    MEASURED

## 15. What ODS should learn from this source

ODS should be able to store or consume profiles by GPU and VRAM tier, context limits, runtime and kernel variants, KV quantization, MTP, vision, slots, reasoning effort, reproducible flags, expected and measured performance, provenance, date and reproduction status.

External information is not a guarantee.

## 16. LEONES benchmark protocol

Each Inference Profile should retain:

    hardware
    model / quant
    runtime / ref
    kernel / ref
    driver / CUDA
    context / KV
    GPU layers / batch / slots
    MTP / vision / reasoning effort
             |
             v
    TTFT
    prompt tok/s
    generation tok/s
    total latency
    VRAM peak
    RAM peak
    power
    temperature
    success / failure / OOM
    context limit
    agent workload result

The exact configuration must be reproducible.

## 17. Immediate LEONES case

On the 4 GB RTX 3050:

    baseline:   Qwen 3.5 2B Q4
    candidate:  Qwen 3.5 4B Q4
    candidate:  Nemotron 3 Nano 4B Q4
                    |
                    v
               A01 benchmark
                    |
                    v
             measured capability

Bonsai 2 remains an external experimental architecture reference, not a claim that the 27B is viable on 4 GB.

## 18. Consequence for MANADA

MANADA should aggregate results by GPU, VRAM tier, model, quant, runtime, kernel, context and workload, without automatically turning different machines into one measurement.

The correct comparison unit is the Inference Profile, not the model alone.

## 19. Incorporated architectural rule

> LEONES + ODS should not ask only which model fits a GPU. They should determine which inference configuration produces the best real capability for that GPU, workload and policy.

Capability must distinguish ESTIMATED, REPORTED, OBSERVED, MEASURED and REPRODUCED.

External evidence discovers candidates and guides experiments; LEONES evidence validates the real machine.

## 20. Integration status

- P0 architecture/methodology: incorporated into LEONES + ODS Evolution.
- P1 external evidence: incorporated with explicit provenance.
- P1 Inference Profile: architectural proposal.
- P1 physical benchmark: pending LEONES reproduction.
- P2 direct Bonsai 2 integration into ODS: not recommended as a dependency; treat it as an external provider/runtime/model profile.

## External sources

- https://github.com/sudoingX/bonsai2-small-gpu
- https://huggingface.co/sudoingx/Ternary-Bonsai-2-27B-PTQ1_0-MTP-GGUF
- https://github.com/PrismML-Eng/llama.cpp/pull/218
- https://github.com/sudoingX/llama.cpp
- https://github.com/sudoingX/qwen38-mtp
