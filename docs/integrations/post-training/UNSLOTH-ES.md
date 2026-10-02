# Unsloth — proveedor del servicio Post-Training de ODS

## Resumen ejecutivo

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

## Encaje de Unsloth con ODS

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

## Contrato propuesto para el provider de ODS

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

## Modelo de ejecución: job service, no servicio de entrenamiento permanente

Unsloth **no debería ejecutarse continuamente como daemon de entrenamiento de ODS**.

El ODS Post-Training Service puede permanecer disponible como plano de control, pero el workload de entrenamiento de Unsloth debe crearse únicamente cuando exista un job que lo necesite.

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

Por tanto, el provider es **efímero y limitado al job**.

Esta distinción es importante porque Unsloth Studio puede desplegarse como aplicación persistente para uso interactivo. That does not mean ODS should keep the training provider permanently running. El Studio/UI puede mantenerse como superficie opcional de desarrollo/debug, mientras que el provider de Post-Training de ODS ejecuta los jobs de entrenamiento bajo demanda. The official repository documents both the Studio launch model and Docker deployment. citeturn0search11

## Integración mediante contenedores

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

## Ciclo de vida del job

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

## Artefactos y frontera de formatos

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

## Integración de datasets

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

## Computación híbrida

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

## Relación con TangleML

The layers remain complementary:

```text
TangleML = workflow orchestration
Unsloth  = training/post-training execution
ODS      = service boundary + registry + operations
LEONES   = profiling + selection + evidence
```

TangleML can orchestrate dataset preparation, training, conversion and benchmarking, while ODS exposes the stable operational service and Unsloth performs the training stage.

## Relación con LLaMA-Factory y Axolotl

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

## Seguridad y aislamiento

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

## Licencia y procedencia

El repositorio actual de Unsloth describe una estructura de doble licencia: el paquete core de Unsloth es Apache-2.0, mientras que determinados componentes opcionales, incluido Unsloth Studio, están bajo AGPL-3.0. This distinction must be preserved when evaluating an ODS integration. citeturn0search3turn0search9

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

## Modelo de evidencia

LEONES should keep evidence classes separate:

- **reported** — capability documented by Unsloth;
- **observed** — behavior observed during an integration;
- **measured** — independently benchmarked by LEONES/ODS;
- **estimated** — planner prediction before execution.

Published Unsloth speed or memory claims must not become LEONES measurements unless reproduced under a defined benchmark.

## Prueba de concepto recomendada

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

## Ruta avanzada de integración

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

## Evaluación arquitectónica

| Area | Assessment |
|---|---|
| ODS Post-Training Service | Buen encaje |
| Provider abstraction | Strong fit |
| SFT / LoRA | Strong fit |
| QLoRA | Strong fit |
| DPO / GRPO | Buen encaje, validar por workload |
| Containerized jobs | Strong fit |
| Model export | Strong fit |
| GGUF integration | Prometedor, requiere validación del runtime |
| Multimodal post-training | Prometedor, validar por modelo |
| Interactive Studio | Integración opcional, no es la frontera del provider de ODS |
| Hybrid execution | Buen encaje, sujeto a los términos de infraestructura |
| Core ODS dependency | No recomendado |

## Decisión

Incluir Unsloth como **candidato experimental de provider de primera clase** para el ODS Post-Training Service.

No convertir Unsloth Studio ni el stack de entrenamiento de Unsloth en una dependencia obligatoria del core de inferencia de ODS.

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

Esto preserva la intercambiabilidad de providers, hace explícito que el uso de cómputo está limitado al job y mantiene en LEONES la selección y la evidencia.

## Referencias oficiales

- [Unsloth GitHub](https://github.com/unslothai/unsloth)
- [Unsloth documentation](https://unsloth.ai/docs)
- [Unsloth Docker image](https://hub.docker.com/r/unsloth/unsloth)
- [Unsloth notebooks](https://github.com/unslothai/notebooks)
