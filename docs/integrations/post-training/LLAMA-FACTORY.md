# Research: LLaMA-Factory as an ODS Post-Training Service

## Executive summary

LLaMA-Factory is a strong candidate for integration into ODS, but the recommended integration boundary is **an ODS Post-Training Service**, not a direct dependency of the ODS inference runtime.

The proposed architecture is:

```text
                         ODS
                          │
        ┌─────────────────┼──────────────────┐
        │                 │                  │
     Inference          Agents             RAG
        │                 │                  │
        └─────────────────┼──────────────────┘
                          │
                  Post-Training Service
                          │
                 ┌────────┴────────┐
                 │                 │
          LLaMA-Factory       other providers
                 │
                 ▼
             Training
                 │
                 ▼
             Artifacts
                 │
                 ▼
          Model Registry
                 │
                 ▼
              ODS Runtime
```

The key principle is:

> **LLaMA-Factory should be a training provider behind an ODS service contract. ODS should own the job lifecycle, API, scheduling, artifact management, validation and deployment integration; LLaMA-Factory should provide the post-training implementation.**

This keeps ODS independent from a particular training framework and allows future providers such as Axolotl, Unsloth, TRL/PEFT or torchtune to implement the same service contract.

---

## 1. Project profile

LLaMA-Factory is an open-source post-training framework for a broad range of language and multimodal models. Its documented capabilities include:

- supervised fine-tuning (SFT);
- LoRA and QLoRA;
- full-parameter fine-tuning;
- continual pre-training;
- preference optimization methods such as DPO and related methods;
- multimodal training;
- quantization and export workflows;
- LoRA adapter merging;
- evaluation;
- inference;
- distributed training;
- WebUI;
- API-oriented serving integrations.

The project uses a unified configuration/CLI model and provides Docker-based installation paths. The project declares Apache-2.0 licensing in its package metadata.

**Important:** framework licensing, model licensing, dataset licensing and infrastructure-provider terms remain separate concerns.

---

## 2. Why the ODS service boundary matters

A direct integration would be:

```text
ODS → LLaMA-Factory
```

The recommended architecture is:

```text
ODS
 │
 └── Post-Training Service
       │
       └── Provider Adapter
              │
              └── LLaMA-Factory
```

This makes the ODS API stable even if the implementation changes.

ODS should therefore expose concepts such as:

```text
Training Job
Dataset
Base Model
Training Method
Provider
Artifact
Benchmark
Deployment
```

rather than exposing LLaMA-Factory-specific CLI options as the public contract.

---

## 3. Proposed ODS Post-Training Service

A first API could conceptually provide:

```text
POST /api/post-training/jobs
GET  /api/post-training/jobs
GET  /api/post-training/jobs/{id}
POST /api/post-training/jobs/{id}/cancel
GET  /api/post-training/jobs/{id}/logs
GET  /api/post-training/jobs/{id}/artifacts
POST /api/post-training/jobs/{id}/benchmark
```

A high-level job request could look like:

```json
{
  "base_model": "model-id",
  "dataset": "dataset-id",
  "task": "sft",
  "adaptation": "lora",
  "provider": "auto",
  "output": {
    "format": "ods"
  }
}
```

ODS translates this request into the provider-specific configuration required by LLaMA-Factory.

---

## 4. LLaMA-Factory as an ODS provider

The service should define a provider abstraction:

```text
PostTrainingProvider
│
├── LLaMA-Factory
├── Axolotl
├── Unsloth
├── TRL/PEFT
└── torchtune
```

A provider capability record could contain:

```yaml
provider: llamafactory

capabilities:
  sft: true
  lora: true
  qlora: true
  full_finetuning: true
  preference_optimization: true
  multimodal: true
  distributed_training: true

artifacts:
  adapter: true
  checkpoint: true
  merged_model: true

execution:
  containerized: true
  local: true
  remote: true

integration:
  ods_post_training_api: true
```

The capability registry should distinguish **supported in principle** from **validated for a particular model/runtime/environment**.

---

## 5. Job lifecycle

A training job should be a first-class ODS object.

Example:

```text
Training Job #184
│
├── Base model
├── Dataset
├── Objective: SFT
├── Adaptation: LoRA
├── Provider: LLaMA-Factory
├── Provider version
├── Configuration
├── Status
├── Logs
├── Metrics
└── Artifacts
```

The lifecycle should be explicit:

```text
CREATE
  ↓
PREPARE
  ↓
RUN
  ↓
VALIDATE
  ↓
EXPORT
  ↓
CONVERT (if required)
  ↓
REGISTER
  ↓
BENCHMARK
  ↓
DEPLOY
```

This is preferable to exposing an opaque long-running CLI process.

---

## 6. Containerized execution

LLaMA-Factory provides Docker-oriented deployment paths. This makes it suitable for an ODS service that launches isolated training jobs.

The preferred model is **job-oriented execution**, rather than keeping the training framework permanently active:

```text
ODS
 │
 │ create job
 ▼
Post-Training Scheduler
 │
 │ allocate compute
 ▼
LLaMA-Factory container
 │
 │ training
 ▼
artifact
 │
 ▼
validation / registration
 │
 ▼
container can terminate
```

This separates training workloads from inference workloads and allows ODS to manage resources explicitly.

---

## 7. ODS should own scheduling

The training provider should not become the resource manager for ODS.

A future scheduler can reason about:

- available accelerators;
- CPU and memory;
- storage;
- concurrency;
- workload priority;
- isolation;
- local versus remote execution;
- provider capabilities;
- user policies;
- cost and infrastructure constraints.

Conceptually:

```text
ODS Post-Training Service
           │
           ▼
        Scheduler
           │
     ┌─────┼─────┐
     │     │     │
   local remote  hybrid
     │     │     │
     ▼     ▼     ▼
 LLaMA-Factory providers
```

The scheduler can later select another provider without changing the ODS API.

---

## 8. Dataset and model registry integration

Datasets should be ODS-managed artifacts rather than arbitrary paths passed to a training command.

A dataset artifact should carry metadata such as:

```text
dataset identifier
version
hash
format
license
provenance
creation process
privacy classification
```

Likewise, a model artifact should record:

```text
base model
provider
provider version
training configuration
dataset version
adapter/checkpoint
artifact hash
license/provenance
```

This makes training reproducible and auditable.

---

## 9. Adapters as first-class artifacts

ODS should not require every training job to produce a fully merged model.

A LoRA/QLoRA job may produce:

```text
Base model
    +
LoRA adapter
```

The adapter should be registered independently:

```text
Adapter
├── base model reference
├── adapter weights
├── tokenizer metadata
├── training configuration
├── provenance
└── validation results
```

ODS can then decide whether to:

- load the adapter directly if the selected runtime supports it;
- merge it into a base model;
- convert the resulting model;
- keep the adapter as a reusable artifact.

---

## 10. Model-format boundary

This is a critical integration boundary.

LLaMA-Factory operates heavily in the Hugging Face/Transformers ecosystem. ODS may use different serving formats or runtimes, including GGUF-based serving through llama-server.

Therefore the service must not assume:

```text
LLaMA-Factory output = ODS runtime artifact
```

Instead:

```text
TRAIN
  ↓
EXPORT
  ↓
VALIDATE
  ↓
CONVERT
  ↓
REGISTER
  ↓
DEPLOY
```

A separate artifact-conversion layer can handle operations such as:

```text
HF checkpoint → GGUF
LoRA adapter → merged model
model → runtime-specific artifact
```

This keeps model conversion independent of the training backend.

---

## 11. llama-server integration

A representative ODS path can be:

```text
LLaMA-Factory
      │
      ▼
LoRA / QLoRA / full checkpoint
      │
      ▼
merge/export
      │
      ▼
Hugging Face-compatible artifact
      │
      ▼
conversion pipeline
      │
      ▼
GGUF
      │
      ▼
ODS llama-server
```

This must be treated as a **validated pipeline**, not an assumed compatibility guarantee.

A PoC should verify:

1. training;
2. adapter or checkpoint export;
3. merge where required;
4. conversion;
5. ODS registration;
6. llama-server loading;
7. inference correctness;
8. benchmark equivalence/regression.

---

## 12. ODS Dashboard

The LLaMA-Factory WebUI should not be the primary ODS integration surface.

ODS should eventually expose:

```text
Dashboard
└── Post-Training
    ├── Create job
    ├── Jobs
    ├── Datasets
    ├── Adapters
    ├── Models
    ├── Artifacts
    └── Benchmarks
```

The provider UI can remain available for advanced/debugging workflows if useful, but the normal user experience should be ODS-native.

---

## 13. Workflow orchestration

TangleML and LLaMA-Factory should have different responsibilities.

A possible ODS workflow is:

```text
Dataset
  ↓
clean
  ↓
deduplicate
  ↓
split
  ↓
LLaMA-Factory
  ↓
merge/export
  ↓
convert
  ↓
benchmark
  ↓
register
  ↓
deploy
```

In this architecture:

- **TangleML** can orchestrate the workflow;
- **LLaMA-Factory** performs the training stage;
- **ODS** owns the service boundary and operational lifecycle.

This avoids making any one tool responsible for the entire stack.

---

## 14. ODS + LEONES separation

The integration should preserve the architectural division already established by LEONES Evolution:

```text
LEONES
  │
  │ decides / profiles / evaluates
  ▼
ODS
  │
  │ operates
  ▼
Post-Training Service
  │
  ▼
LLaMA-Factory
  │
  │ trains/adapts
  ▼
Artifact
  │
  ▼
ODS validation + deployment
```

LEONES can supply a high-level execution plan:

```json
{
  "provider": "llama-factory",
  "method": "lora",
  "objective": "sft",
  "dataset": "dataset-id",
  "model": "model-id",
  "execution_policy": "selected-by-leones"
}
```

ODS executes that plan.

ODS must also remain useful without LEONES; LEONES adds discovery, profiling, provider selection and evidence rather than becoming a mandatory ODS dependency.

---

## 15. Hybrid execution and independence

The service should support different execution locations behind the same API:

```text
              ODS Post-Training
                      │
              execution policy
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
        local       remote       hybrid
          │           │           │
          └───────────┼───────────┘
                      ▼
                training job
```

Remote execution must not automatically be treated as independent execution.

LEONES/ODS should track:

- infrastructure ownership;
- data destination;
- encryption;
- key ownership;
- retention;
- network requirements;
- model/data portability;
- provider terms;
- artifact portability;
- ability to reproduce the workflow elsewhere.

The goal is **freedom and independence**, not merely locality.

---

## 16. Security boundary

Training is a different security workload from inference.

The provider container may access:

- models;
- datasets;
- Python packages;
- GPUs/accelerators;
- model hubs;
- object storage;
- training outputs.

Therefore the service should prefer:

```text
ods-post-training job
├── isolated container
├── explicit volumes
├── controlled network
├── controlled secrets
├── explicit artifact export
└── no implicit host filesystem access
```

Production traces should never automatically become training data. Any ODS-derived training dataset should pass through explicit policy, filtering, redaction and consent controls.

---

## 17. Observability and evidence

ODS should capture:

```text
job status
logs
training metrics
evaluation metrics
resource usage
elapsed time
checkpoint information
software versions
configuration
artifact hashes
```

Evidence categories must remain separate:

- **reported** — published by LLaMA-Factory or another project;
- **estimated** — calculated or predicted by ODS/LEONES;
- **observed** — seen during an execution without being independently benchmarked;
- **measured** — produced by a controlled ODS/LEONES benchmark.

Published framework claims must not be silently converted into LEONES measurements.

---

## 18. License and provenance

LLaMA-Factory's package metadata declares Apache-2.0.

For ODS integration, however, the following must remain separate:

```text
LLaMA-Factory license
        ≠
base model license
        ≠
dataset license
        ≠
training-data provenance
        ≠
cloud/infrastructure terms
```

A provider being open source does not by itself guarantee independence from hosted infrastructure or unrestricted use of every model and dataset.

ODS should therefore preserve provenance at artifact level.

---

## 19. Recommended implementation phases

### Phase 1 — Provider proof of concept

```text
ODS
 ↓
Post-Training API
 ↓
LLaMA-Factory container
 ↓
SFT/LoRA job
 ↓
artifact
```

### Phase 2 — Artifact lifecycle

```text
artifact
 ↓
validation
 ↓
conversion
 ↓
ODS Model Registry
 ↓
deployment
```

### Phase 3 — Native ODS dashboard

```text
Dashboard
 ↓
Post-Training
 ↓
create / monitor / validate / deploy
```

### Phase 4 — Multi-provider service

```text
Post-Training Service
├── LLaMA-Factory
├── Axolotl
├── Unsloth
└── TRL/PEFT
```

### Phase 5 — LEONES integration

```text
LEONES
 ↓
provider selection
 ↓
ODS Post-Training
 ↓
training
 ↓
benchmark
 ↓
evidence
```

---

## 20. Initial PoC acceptance criteria

The first PoC should demonstrate the complete path:

```text
model
 ↓
dataset
 ↓
ODS job
 ↓
LLaMA-Factory
 ↓
LoRA/QLoRA artifact
 ↓
validation
 ↓
merge/export
 ↓
conversion
 ↓
ODS registration
 ↓
llama-server or another ODS runtime
 ↓
benchmark
```

Acceptance should verify:

- reproducible job configuration;
- provider/container isolation;
- artifact integrity;
- model/runtime compatibility;
- successful deployment;
- inference correctness;
- benchmark results;
- provenance and license metadata;
- clear separation of estimated/reported/observed/measured evidence.

---

## 21. Architectural assessment

| Area | Assessment |
|---|---|
| ODS Post-Training Service | **Very strong fit** |
| Provider abstraction | **Very strong fit** |
| SFT | **Very strong fit** |
| LoRA / QLoRA | **Very strong fit** |
| Preference optimization | **Strong fit** |
| Multimodal post-training | **Strong fit** |
| Containerized jobs | **Strong fit** |
| Artifact production | **Strong fit** |
| ODS Model Registry | **Strong fit, requires adapter layer** |
| Native Dashboard | **Strong future fit** |
| Workflow orchestration | **Complementary with TangleML** |
| Direct llama-server compatibility | **Requires validation/conversion** |
| Remote/hybrid execution | **Strong fit, subject to provider independence** |
| Core ODS dependency | **Not recommended** |

## Decision

**Include LLaMA-Factory as a first-class experimental provider for an ODS Post-Training Service.**

Do **not** make LLaMA-Factory a mandatory dependency of the ODS inference core.

The preferred architecture is:

```text
                 LEONES
                    │
             decision / evidence
                    │
                    ▼
                   ODS
                    │
          Post-Training Service
                    │
              Provider API
                    │
             ┌──────┴──────┐
             │             │
       LLaMA-Factory    future providers
             │
             ▼
          artifact
             │
       validate/convert
             │
             ▼
        ODS Model Registry
             │
             ▼
         ODS Runtime
```

This gives ODS a model-evolution capability while preserving provider interchangeability and keeping LEONES responsible for selection, profiling and evidence.

## References

- LLaMA-Factory: https://github.com/hiyouga/LlamaFactory
- LLaMA-Factory examples: https://github.com/hiyouga/LlamaFactory/tree/main/examples
- LLaMA-Factory data documentation: https://github.com/hiyouga/LlamaFactory/blob/main/data/README.md
