# RC1 — Stack integration contract

> **ODS first. Magnitude second. LEONES measures both.**

## 1. Purpose

LEONES must exploit existing local-AI stacks instead of rebuilding them.

The RC1 stack contract therefore treats ODS and Magnitude as **systems under integration and measurement**, not as codebases to duplicate.

## 2. Canonical decision point

```text
research / Atlas
      ↓
LLMFit
      ↓
LEONES selection
      ↓
┌─────┴─────┐
│           │
ODS       Magnitude
SOHO      personal assistant
│           │
└─────┬─────┘
      ↓
 LEONES task
      ↓
 LEONES measurement
      ↓
 evidence
      ↓
 MANADA
```

## 3. ODS

ODS is the first stack to install and validate.

The current upstream documentation describes:

- `llama-server` as the local inference API;
- OpenAI-compatible API access;
- Hermes Agent as the default local-first agent;
- Hermes talking to `llama-server` through an OpenAI-compatible endpoint;
- hardware detection and model selection in the ODS installation path.

LEONES therefore does not create an ODS-specific inference protocol.

The physical hypothesis to verify is:

```text
LEONES
  → ODS
  → Hermes
  → OpenAI-compatible endpoint
  → llama-server
  → model
```

The endpoint, model identifier, effective context and actual runtime version must be captured from the running installation rather than assumed from documentation.

## 4. Magnitude

Magnitude is the second path.

LEONES must first identify its actual native inference path on the target release. If it exposes an OpenAI-compatible endpoint, LEONES may use that endpoint as an interoperability path; it must not silently replace Magnitude's native engine with another runtime.

The physical evidence must distinguish:

```text
magnitude-native
```

from:

```text
magnitude-openai-compatible-external
```

when both are available.

## 5. Stack manifest

Each integration is described by a minimal manifest:

```text
id
upstream
version
commit
platform
install_method
services
agent
inference_interface
healthcheck
model_discovery
benchmark_entrypoint
```

Only observed fields may be promoted to `observed` or `verified`.

## 6. Health gate

A stack is benchmarkable only if:

```text
INSTALL = PASS
BOOT = PASS
HARDWARE = OBSERVED
MODEL = OBSERVED
RUNTIME = IDENTIFIED
INFERENCE = PASS
```

Agentic benchmarking additionally requires:

```text
AGENT = READY
TASK = READY
GRADER = READY
```

## 7. What LEONES never does

- does not fork ODS to add LEONES logic;
- does not fork Magnitude to add LEONES logic;
- does not claim benchmark performance from an installer/model selector;
- does not infer hardware capabilities from a tier name;
- does not call a result `measured` until LEONES has executed it;
- does not merge results from incompatible runtimes into one number.

## 8. AirLLM and FreeToken

These remain future contributions to ODS/Magnitude.

Preferred order:

1. upstream contribution;
2. minimal connector if upstream is not immediately possible;
3. physical benchmark;
4. evidence;
5. upstream proposal/PR.

They are not additional mandatory LEONES runtime layers for RC1.

## 9. Ubuntu gate

Ubuntu is required only after this contract, the RC1 task fixture and the adapters/runners are ready.

The first physical session must answer one question only:

> **Can the selected stack, on the real consumer machine, execute the canonical task and produce evidence that LEONES can validate?**

If yes, continue to measurement. If no, capture the failure as evidence and repair the smallest responsible layer in GitHub before repeating.
