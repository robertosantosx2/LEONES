# Unsloth — ODS Post-Training Service Provider

## Executive summary

[Unsloth](https://github.com/unslothai/unsloth) is an open-source training and inference stack focused on efficient fine-tuning and model workflows. Its current project includes a desktop/Studio experience, code-based training, Docker deployment, model export and support for techniques including LoRA, QLoRA, full fine-tuning, DPO, GRPO and other post-training workflows.

For ODS, the recommended integration is **Unsloth as an interchangeable provider behind the ODS Post-Training Service**, not as a mandatory ODS inference-core dependency.

The architectural path is:

```text
LEONES
   ↓
ODS Post-Training Service
   ↓
Unsloth provider
   ↓
job-scoped training workload
   ↓
adapter/checkpoint/model artifact
   ↓
validation / conversion
   ↓
ODS Model Registry
   ↓
ODS Runtime
   ↓
benchmark / evidence
   ↓
LEONES
```

Unsloth's official repository currently describes Docker support, OpenAI-compatible serving, model export including GGUF and other formats, and training support across LoRA/QLoRA, full fine-tuning, DPO, GRPO and related workflows. These capabilities make it relevant to the same provider layer being investigated for LLaMA-Factory and Axolotl. citeturn0search3turn0search4

## Why Unsloth fits ODS

Unsloth is particularly relevant where the objective is to reduce the compute and memory cost of post-training while retaining a broad training workflow.

Relevant capabilities include:

- supervised fine-tuning;
- LoRA and QLoRA;
- full fine-tuning;
- preference optimization such as DPO;
- reinforcement-learning workflows including GRPO;
- model export/conversion;
- GGUF-related workflows;
- multimodal and non-text model workflows in the current stack;
- Docker execution;
- code-based and UI-based workflows;
- inference and OpenAI-compatible serving.

The exact capability for a given model, quantization, runtime and provider version must be validated rather than inferred from the general project capability list.

## Proposed ODS provider contract

ODS should expose a provider-neutral contract:

```text
PostTrainingProvider
├── LLaMA-Factory
├── Axolotl
├── Unsloth
├── TRL/PEFT
└── future providers
```

A conceptual job API should cover:

- create job;
- select model and dataset;
- select objective/method;
- select provider or allow `auto`;
- inspect status;
- stream/retrieve logs;
- cancel;
- collect artifacts;
- validate;
- benchmark;
- register/deploy.

Unsloth-specific configuration should remain inside the provider adapter and be retained as provenance, rather than becoming the public ODS API.

## Execution model: job service, not a permanently running training service

Unsloth should **not run continuously as an ODS training daemon**.

The ODS Post-Training Service may remain available as the control plane, but the Unsloth training workload should be created only when a job actually needs it.

```text
ODS Post-Training API
        │
        ▼
     Job Queue
        │
        ▼
 Provider Scheduler
        │
        ├── no pending job → no Unsloth training workload
        │
        └── pending job
                │
                ▼
        start isolated provider workload
                │
                ▼
          train / fine-tune
                │
                ▼
          export artifact
                │
                ▼
       validate / register / benchmark
                │
                ▼
          stop/remove workload
                │
                ▼
          release resources
```

The provider is therefore **ephemeral and job-scoped**.

This distinction is important because Unsloth Studio itself can be deployed as a persistent application for interactive use. That does not mean ODS should keep the training provider permanently running. The Studio/UI can remain an optional development/debugging surface, while the ODS Post-Training provider executes training jobs on demand. The official repository documents both the Studio launch model and Docker deployment. citeturn0search11

## Container integration

Unsloth publishes an official Docker image, `unsloth/unsloth`, and documents GPU-enabled Docker execution. This provides a practical isolation boundary for an ODS provider. citeturn0search3turn0search11

ODS should create the workload with:

- explicit model/dataset mounts;
- explicit cache locations;
- scoped credentials;
- controlled network access;
- resource limits;
- isolated temporary workspace;
- explicit artifact output;
- provider version capture.

No pending job should mean no provider training container.

## Job lifecycle

The ODS lifecycle should remain provider-neutral:

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

Unsloth owns the actual training/fine-tuning stage. ODS owns the operational lifecycle.

Cancellation, timeout or failure should terminate the job-scoped provider workload and release compute resources. Logs, metrics, configuration and resulting artifacts should remain associated with the ODS job record.

## Artifacts and model-format boundary

Adapters should be first-class artifacts:

```text
Base model
   +
LoRA adapter
   ↓
ODS artifact registry
```

ODS should record:

- base model identifier/version;
- dataset identifier/version;
- provider and provider version;
- training configuration;
- adapter/checkpoint;
- artifact hash;
- tokenizer/model metadata;
- provenance;
- validation results;
- license metadata.

Unsloth documents export workflows including GGUF and other model representations. ODS should nevertheless treat conversion as an explicit pipeline stage and validate compatibility with the selected ODS inference runtime. citeturn0search4

A successful Unsloth training run must not automatically be interpreted as a deployable ODS runtime artifact.

## Dataset integration

ODS should own the platform-level dataset abstraction.

A provider job should receive a reproducible dataset reference rather than arbitrary uncontrolled host paths:

```text
dataset id
version
hash
format/schema
license
provenance
privacy classification
access policy
```

Production traces should not automatically become training data. Any such workflow requires explicit policy, filtering/redaction, consent where applicable and provenance.

## Hybrid compute

Unsloth can participate in local, remote or hybrid execution. ODS should separate:

```text
Training Provider
      │
   Unsloth
      │
      ▼
Compute Provider
      ├── local
      ├── remote VM
      ├── Kubernetes
      ├── cloud GPU
      └── other execution substrate
```

This is important for LEONES: the framework selection and the compute-location decision should remain separate.

Remote execution should be evaluated for data destination, key ownership, retention, portability, provider terms and reproducibility. Open-source training software does not automatically imply infrastructure independence.

## Relationship with TangleML

The layers remain complementary:

```text
TangleML = workflow orchestration
Unsloth  = training/post-training execution
ODS      = service boundary + registry + operations
LEONES   = profiling + selection + evidence
```

TangleML can orchestrate dataset preparation, training, conversion and benchmarking, while ODS exposes the stable operational service and Unsloth performs the training stage.

## Relationship with LLaMA-Factory and Axolotl

Unsloth should enter the same provider abstraction:

```text
             ODS Post-Training Service
                       │
              Provider capability
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
 LLaMA-Factory      Axolotl         Unsloth
       │               │               │
       └───────────────┼───────────────┘
                       ▼
                  artifact
```

LEONES should compare providers using explicit workload requirements and evidence, not a permanent hard-coded preference.

Relevant dimensions include:

- supported training method;
- model architecture;
- quantization;
- multimodal support;
- distributed execution;
- artifact format;
- conversion path;
- measured performance;
- memory/resource use;
- reproducibility;
- infrastructure independence.

## Security and isolation

The provider should operate with least privilege:

```text
ODS job
├── isolated workload
├── explicit model access
├── explicit dataset access
├── scoped secrets
├── controlled network
├── resource limits
├── explicit artifact export
└── provenance
```

The training workload should not gain implicit access to unrelated ODS data, host files or credentials.

## Licensing and provenance

The current Unsloth repository describes a dual licensing structure: the core Unsloth package is Apache-2.0, while certain optional components including Unsloth Studio are AGPL-3.0. This distinction must be preserved when evaluating an ODS integration. citeturn0search3turn0search9

Licensing must also be tracked separately for:

```text
Unsloth component/license
        ≠
base model license
        ≠
dataset license
        ≠
training data provenance
        ≠
container/image terms
        ≠
cloud/infrastructure terms
```

LEONES should record the exact component and version used by each job.

## Evidence model

LEONES should keep evidence classes separate:

- **reported** — capability documented by Unsloth;
- **observed** — behavior observed during an integration;
- **measured** — independently benchmarked by LEONES/ODS;
- **estimated** — planner prediction before execution.

Published Unsloth speed or memory claims must not become LEONES measurements unless reproduced under a defined benchmark.

## Recommended proof of concept

The first ODS integration should be deliberately small:

```text
ODS API
  ↓
Unsloth provider
  ↓
isolated job workload
  ↓
SFT + LoRA
  ↓
adapter artifact
  ↓
validation
  ↓
optional merge / conversion
  ↓
ODS Model Registry
  ↓
ODS Runtime
  ↓
benchmark
  ↓
evidence
```

Acceptance criteria:

1. reproducible job creation;
2. no provider workload when no job is pending;
3. isolated execution;
4. clean cancellation/failure handling;
5. artifact capture;
6. provenance capture;
7. validated runtime compatibility;
8. independent benchmark;
9. resource release after job completion.

## Advanced integration path

After the basic PoC:

1. QLoRA;
2. additional SFT workflows;
3. DPO;
4. GRPO/RL workflows;
5. multimodal training;
6. export/conversion validation;
7. distributed execution;
8. comparison against LLaMA-Factory and Axolotl;
9. optional interactive Studio integration for advanced users.

Each stage should generate independent evidence.

## Architectural assessment

| Area | Assessment |
|---|---|
| ODS Post-Training Service | Strong fit |
| Provider abstraction | Strong fit |
| SFT / LoRA | Strong fit |
| QLoRA | Strong fit |
| DPO / GRPO | Strong fit, validate per workload |
| Containerized jobs | Strong fit |
| Model export | Strong fit |
| GGUF integration | Promising, requires runtime validation |
| Multimodal post-training | Promising, validate per model |
| Interactive Studio | Optional integration, not the ODS provider boundary |
| Hybrid execution | Strong fit, subject to infrastructure terms |
| Core ODS dependency | Not recommended |

## Decision

Include Unsloth as an **experimental first-class provider candidate** for the ODS Post-Training Service.

Do not make Unsloth Studio or the Unsloth training stack a mandatory dependency of the ODS inference core.

The preferred architecture is:

```text
LEONES
   │
   │ select / profile / evaluate
   ▼
ODS
   │
   ▼
Post-Training Service
   │
   ├── LLaMA-Factory
   ├── Axolotl
   └── Unsloth
          │
          ▼
     job-scoped workload
          │
          ▼
       artifact
          │
          ▼
 validation / conversion
          │
          ▼
   ODS Model Registry
          │
          ▼
      ODS Runtime
```

This preserves provider interchangeability, makes compute usage explicitly job-scoped and leaves LEONES responsible for selection and evidence.

## Official references

- [Unsloth GitHub](https://github.com/unslothai/unsloth)
- [Unsloth documentation](https://unsloth.ai/docs)
- [Unsloth Docker image](https://hub.docker.com/r/unsloth/unsloth)
- [Unsloth notebooks](https://github.com/unslothai/notebooks)
