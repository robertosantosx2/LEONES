# Companion Hub Integration Proposal for ODS

**Experimental track:** `ods-evolution`  
**Project:** LEONES  
**Date:** 2026-09-30  
**Status:** Architecture and integration study — no code integration

## 1. Executive summary

Companion Hub is interesting to ODS primarily as an **orchestration and local AI platform pattern**, not as a replacement for ODS inference.

Its strongest reusable ideas are:

- first-run hardware discovery and onboarding;
- hardware-aware model recommendations;
- one-click installation and supervision of local apps;
- a unified app/model/agent catalogue;
- OpenAI-compatible and Ollama-compatible access;
- a single MCP surface for agents;
- custom Docker Compose applications;
- multi-machine Hub pooling;
- a dashboard that treats apps, models and agents as one local ecosystem.

ODS already has many of the underlying building blocks, so the most useful result is to compare the two architectures and selectively bring the missing product-level orchestration ideas into ODS.

The recommended direction is:

```text
                         ODS
                          |
                 ODS Runtime Layer
                          |
          +---------------+----------------+
          |               |                |
       llama.cpp        AirLLM            vLLM
          |               |                |
          +---------------+----------------+
                          |
                    LiteLLM / API
                          |
             +------------+------------+
             |            |            |
           WebUI        Hermes       Agents
                          |
                    ODS Dashboard
                          |
                  App / Model Catalog
                          |
                       LEONES
```

Companion Hub should therefore be treated as an **architectural reference for ODS evolution**, especially around lifecycle management, discovery, onboarding and app orchestration.

## 2. What Companion Hub provides

The current project describes itself as a local app runtime that installs and supervises applications as Docker Compose deployments.

Important features include:

- app-store/catalog model;
- first-launch setup wizard;
- hardware inspection;
- model recommendations;
- local agents;
- shared memory;
- MCP endpoint;
- custom containers;
- networking via Tailscale/Cloudflare;
- multi-Hub pooling;
- OpenAI-compatible API;
- Ollama-compatible API;
- CLI control.

This is broader than an inference engine.

## 3. Relationship with ODS

A useful comparison is:

| Area | ODS | Companion Hub |
|---|---|---|
| Local inference | Strong | Strong through managed engines |
| Hardware-aware inference | Strong | Strong product-level UX |
| Model/runtime logic | Strong | Catalogue-oriented |
| Docker services | Strong | Core abstraction |
| App marketplace | Extension-oriented | Core feature |
| First-run wizard | Present | Major product surface |
| Agents | Hermes and ecosystem | Agents treated as apps |
| MCP | Available in ecosystem | Unified Hub MCP surface |
| OpenAI API | Yes | Yes |
| Ollama API | Compatibility path | Native API |
| Multi-machine pooling | Not primary | Explicit feature |
| Custom apps | Extensions | First-class |
| LEONES-style evidence | Not the primary goal | Not the primary goal |

ODS is more inference/platform-oriented; Companion Hub is more application-orchestration-oriented.

## 4. Features worth adapting to ODS

### 4.1 Hardware-aware onboarding

ODS already performs hardware discovery. The improvement would be to turn that into a visible onboarding flow:

```text
First boot
   |
Detect CPU / RAM / GPU / disk
   |
Detect available runtimes
   |
Detect installed models
   |
Calculate compatible options
   |
Show model/runtime choices
   |
User selects
   |
Install only what was selected
```

This aligns particularly well with LEONES.

### 4.2 Unified app catalogue

ODS could expose a catalogue containing:

- inference engines;
- models;
- agents;
- observability;
- vector stores;
- voice services;
- automation services;
- experimental runtimes.

Each item should contain machine-readable metadata rather than only UI text.

Example:

```yaml
id: airllm
type: runtime
format:
  - safetensors
capabilities:
  layer_streaming: true
  moe_expert_streaming: true
install:
  mode: optional
```

### 4.3 Lifecycle management

Companion Hub's model of installing, starting, stopping and monitoring apps maps naturally onto ODS.

ODS could expose:

```text
install
start
stop
restart
upgrade
remove
status
logs
health
open
```

for every extension.

### 4.4 Custom app support

A controlled "bring your own Compose service" capability would make ODS much more extensible.

It should remain sandboxed and explicit rather than turning the dashboard into an unrestricted Docker control plane.

## 5. MCP opportunity

Companion Hub's unified MCP surface is especially relevant.

ODS could expose a controlled MCP surface for:

- model discovery;
- runtime selection;
- starting/stopping services;
- querying hardware;
- checking benchmark evidence;
- launching installed applications.

This could make Hermes and external agents ODS-aware without each agent needing a bespoke integration.

## 6. Multi-machine evolution

Companion Hub's Hub Pool concept suggests a future ODS capability:

```text
ODS Node A
 RTX 3050
     |
     +------+
            |
          ODS Pool
            |
     +------+------+
     |             |
ODS Node B      ODS Node C
 RTX 4090       CPU / RAM
```

A scheduler could route inference according to:

- model compatibility;
- VRAM;
- RAM;
- queue depth;
- measured throughput;
- latency;
- user-selected constraints.

LEONES could provide the hardware/model evidence used by the scheduler.

## 7. Recommended ODS architecture

The strongest combination is:

```text
                    ODS Control Plane
                           |
        +------------------+------------------+
        |                  |                  |
   App Manager        Model Manager      Runtime Manager
        |                  |                  |
   Compose apps       Model catalog       llama.cpp
                                           AirLLM
                                           vLLM
                                           ...
        |                  |                  |
        +------------------+------------------+
                           |
                      LiteLLM/API
                           |
                 Dashboard / Agents / WebUI
                           |
                         LEONES
```

This separates orchestration from inference.

## 8. License consideration

Companion Hub's repository currently identifies its license as **PolyForm Noncommercial 1.0**.

That makes direct code reuse a separate legal question from architectural reuse. The safe engineering approach for an ODS project is to:

- reuse public architectural ideas;
- avoid copying substantial implementation code unless licensing permits it;
- review individual components and dependencies before incorporating code;
- prefer clean-room ODS implementations of desired behaviour.

This is important if ODS is intended for broad upstream distribution.

## 9. What not to copy

Do not make ODS dependent on Companion Hub.

In particular:

- do not replace ODS's existing inference stack;
- do not couple ODS to the Hub desktop application;
- do not assume Companion Hub's catalogue is the ODS source of truth;
- do not import its proprietary/noncommercial implementation without license review;
- do not replace LEONES' ESTIMATED/MEASURED distinction with opaque recommendations.

## 10. LEONES relationship

The strongest architecture is complementary:

```text
Companion-style discovery
          |
          v
        ODS
          |
   runtime candidates
          |
          v
       LEONES
          |
   ESTIMATED candidates
          |
    human selection
          |
      installation
          |
       benchmark
          |
       MEASURED
```

LEONES remains the evidence authority.

## 11. Conclusion

Companion Hub is best treated as a **product and orchestration reference for ODS evolution**.

The highest-value ideas are:

1. unified local app/model/agent catalogue;
2. first-run hardware-aware onboarding;
3. lifecycle management;
4. unified MCP;
5. custom Compose applications;
6. multi-machine inference pooling;
7. simple OpenAI/Ollama compatibility.

ODS already has substantial infrastructure for these ideas. The likely path is to evolve the ODS dashboard/control plane rather than importing Companion Hub itself.

**Verdict:** high architectural relevance; low need for direct code dependency; particularly valuable as a reference for ODS's control plane and user experience.

## References

- https://github.com/companionintelligence/CI-Hub
- https://docs.ci.computer
