# Research: TangleML and Post-Training in LEONES Evolution

**Status:** Experimental / research  
**Rama:** `ods-evolution`  
**Scope:** post-training, ML workflows and hybrid computing  
**Date:** 2026-10-02

## Summary

TangleML is an open-source platform for orchestrating machine-learning pipelines. Its architecture builds graphs of containerized components, executes them locally or on remote infrastructure, and retains artifacts, logs, metadata and execution results. The backend declares Apache-2.0 and the frontend `tangle-ui` also declares Apache-2.0.

For **LEONES Evolution**, TangleML fits best as an **orchestration layer for training, post-training, data and evaluation workflows**, not as a replacement for ODS.

The proposed separation is:

```text
LEONES
  ↓
discovery / profiling / planning / evidence
  ↓
TangleML
  ↓
training / data / evaluation workflows
  ↓
model artifacts
  ↓
ODS
  ↓
inference / agents / tools / services
```

## 1. LEONES architectural context

LEONES should not evolve around «local AI» as an end in itself. The higher-level objective is **freedom, independence and user control**. Local computing is currently a practical consequence of that objective, but not an absolute requirement.

Therefore LEONES should be able to select:

- local execution;
- remote execution on controlled infrastructure;
- cloud execution when compatible with independence requirements;
- hybrid execution, distributing stages across resources.

ODS remains the **AI execution platform**. LEONES decides and provides evidence; ODS executes and operates models and services.

## 2. What TangleML provides

TangleML provides:

- visual pipeline editor;
- task/component graphs;
- components defined through `ComponentSpec`;
- containerized program execution;
- explicit input/output interfaces;
- local and remote execution;
- multiple launchers;
- content-based caching;
- execution reuse;
- artifacts and logs;
- execution traceability;
- reproducibility through containers and component versioning;
- components written in multiple languages.

The official repository documents local Docker/Podman execution and remote execution; the documentation also describes an API Server + Orchestrator + Launcher architecture. This keeps workflow logic relatively decoupled from the compute resource.

## 3. Fit for post-training

TangleML is particularly suitable for turning post-training into reproducible pipelines:

```text
dataset
   ↓
prepare
   ↓
clean / deduplicate
   ↓
generate / filter
   ↓
SFT / LoRA / QLoRA
   ↓
preference tuning
   ↓
evaluation
   ↓
merge
   ↓
quantization
   ↓
benchmark
   ↓
evidence package
   ↓
ODS
```

A LEONES component library could include:

- `discover-model`
- `download-model`
- `prepare-dataset`
- `clean-dataset`
- `deduplicate`
- `synthetic-data`
- `sft`
- `lora`
- `qlora`
- `dpo`
- `grpo`
- `rlvr`
- `distillation`
- `merge`
- `quantize`
- `evaluate`
- `benchmark`
- `package-evidence`

Tangle does not need to understand LEONES policy: it executes components and connects their artifacts.

## 4. Hybrid computing

The strategic value is not merely that Tangle can run «in the cloud», but that it separates the **workflow** from the **execution resource**.

Example:

```text
dataset privado
      ↓
LOCAL
  preparación
  filtrado
      ↓
REMOTE GPU
  entrenamiento
      ↓
LOCAL
  evaluación sensible
  cuantización
  benchmark
      ↓
ODS
  serving
```

Another case:

```text
teacher grande
      ↓
remote GPU
      ↓
synthetic dataset
      ↓
local filtering
      ↓
student training
      ↓
ODS
```

LEONES should make this placement decision from:

- hardware disponible;
- memoria;
- aceleradores;
- coste;
- privacidad;
- tamaño del dataset;
- tamaño del modelo;
- tiempo;
- licencia;
- portabilidad;
- nivel de independencia requerido.

## 5. TangleML as workflow execution layer

The proposed architecture is:

```text
                         LEONES EVOLUTION
                                │
                discovery / profiling / planning
                                │
                                ▼
                           TANGLEML
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
            LOCAL             REMOTE            HYBRID
              │                 │                 │
              └─────────────────┼─────────────────┘
                                ▼
                         training / data
                         evaluation / R&D
                                │
                                ▼
                         MODEL ARTIFACT
                                │
                                ▼
                               ODS
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
                inference     agents       tools
```

### Boundary with ODS

**TangleML:**

- workflows ML;
- preparación de datos;
- entrenamiento;
- experimentación;
- evaluación;
- generación de artifacts.

**ODS:**

- model serving;
- inferencia;
- agentes;
- tools;
- RAG;
- workflows operativos;
- servicios de IA;
- interfaz de usuario.

Tangle should not be introduced as a second inference runtime inside ODS.

## 6. Components and reproducibility

Tangle's model `ComponentSpec` is particularly suitable for LEONES because it encapsulates each stage with:

- implementation;
- container image;
- inputs;
- outputs;
- metadata;
- version/digest.

This enables reproducible post-training recipes without turning LEONES into its own distributed execution framework.

Content-based caching is also relevant:

```text
dataset
   ↓
preprocessing
   ↓
deduplication
   ↓
training
```

If only the training configuration changes, compatible earlier stages can be reused instead of being executed again.

## 7. Independence and cloud

TangleML is compatible with LEONES' hybrid-computing vision because it documents local execution and cloud-agnostic deployment.

However, **running Tangle in the cloud does not automatically mean independence**.

LEONES should distinguish:

### Self-hosted Tangle

```text
usuario
  ↓
Tangle propio
  ↓
infraestructura elegida
```

This is the most consistent model with independence.

### Tangle on an external provider

```text
usuario
  ↓
Tangle
  ↓
cloud externo
```

This may be valid, but LEONES should record the concrete dependency.

### Third-party Tangle service

This must be evaluated separately because dependencies may include:

- identidad;
- almacenamiento;
- autenticación;
- infraestructura;
- claves;
- políticas del proveedor;
- portabilidad.

The architecture enables these distinctions; it does not solve them automatically.

## 8. Licensing

The backend `TangleML/tangle` declares **Apache-2.0**, and the frontend `TangleML/tangle-ui` also declares **Apache-2.0**.

This satisfies LEONES' open-source requirement, but **it does not provide the strong copyleft or network anti-capture protection that LEONES may prefer for core components**, such as AGPL or EUPL.

| Criterio | TangleML |
|---|---|
| Open source | Yes |
| Software modificable | Yes |
| Uso local | Yes |
| Ejecución remota | Yes |
| Cloud-agnostic | Yes, según launcher/infraestructura |
| Contenedores | Yes |
| Reproducibilidad | Yes |
| Caching | Yes |
| Componentes reutilizables | Yes |
| Copyleft fuerte | No |
| Anti-captura cloud por licencia | No |
| Autohospedable | Yes |
| Adecuado para componente experimental LEONES | Yes |

The project license must not be confused with the licenses of components, container images, models or datasets executed through Tangle. LEONES should maintain license and provenance records for each artifact.

## 9. Fit with LEONES evidence

Tangle can retain:

- graph;
- logs;
- artefactos;
- metadatos;
- configuration;
- execution results.

LEONES should add the evidence layer:

```text
Tangle execution
      ↓
observed execution data
      ↓
LEONES validation
      ↓
benchmark
      ↓
MEASURED evidence
```

A Tangle execution does not automatically turn a number into a LEONES measurement. Keep these categories separate:

- `estimated`;
- `reported`;
- `observed`;
- `measured`.

## 10. Fit with ODS

The proposed integration:

```text
LEONES
  │
  ├─ selecciona modelo
  ├─ perfila recursos
  ├─ diseña workflow
  ├─ selecciona compute target
  └─ define validación
          │
          ▼
       TangleML
          │
          ├─ data
          ├─ training
          ├─ evaluation
          └─ packaging
                  │
                  ▼
             MODEL PACKAGE
                  │
                  ▼
                 ODS
                  │
                  ├─ inference
                  ├─ agents
                  ├─ tools
                  ├─ RAG
                  └─ services
```

When possible, the resulting artifact should include:

- modelo;
- tokenizer;
- adapters;
- cuantización;
- recipe;
- dataset provenance;
- configuración;
- hardware utilizado;
- versiones de software;
- métricas;
- benchmarks;
- limitaciones;
- licencia.

## 11. Fit by area

| Area | Fit |
|---|---|
| Dataset pipelines | High |
| SFT | High |
| LoRA / QLoRA | High |
| DPO | High |
| GRPO / RLVR | Experimental |
| Distillation | High |
| Synthetic data | High |
| Evaluation | High |
| Benchmarking | High |
| Reproducibilidad | High |
| Experimentación | High |
| Local execution | High |
| Remote execution | High |
| Hybrid execution | High |
| Model serving | No: ODS |
| Agent runtime | No: ODS |
| Tool runtime | No: ODS |
| Discovery | Complementary: LEONES |
| Hardware profiling | LEONES |
| Evidence governance | LEONES |
| License/provenance governance | LEONES |

## 12. Hardware

Tangle allows LEONES to treat hardware as a variable execution resource:

```text
              TRAINING JOB
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
    laptop       server       cloud
       │           │           │
      CPU        NVIDIA      multi-GPU
      16 GB      24 GB       80 GB+
       │           │           │
       └───────────┼───────────┘
                   ▼
               artifact
                   │
                   ▼
                  ODS
```

LEONES remains responsible for the decision; Tangle executes the selected workflow.

## 13. Risks and open points

Before making Tangle a production dependency, verify:

1. Licencias transitivas de backend, frontend y componentes.
2. Licencias de las imágenes de contenedor utilizadas.
3. Seguridad de componentes de terceros.
4. Gestión de secretos.
5. Transferencia de datasets hacia infraestructura remota.
6. Cifrado en tránsito y en reposo.
7. Control de claves.
8. Aislamiento entre tenants.
9. Persistencia y eliminación de artefactos.
10. Portabilidad real entre launchers.
11. Reproducibilidad entre versiones de infraestructura.
12. Soporte GPU y passthrough para los trainers que LEONES necesite.
13. Coste y límites de los proveedores remotos.
14. Capacidad de ejecutar sin servicios externos.

In particular: Tangle provides workflow orchestration, container isolation and portability, but **it should not be interpreted as an automatic guarantee of encrypted sandbox execution, confidential computing or end-to-end encryption**. Those properties must be verified and designed in the actual infrastructure.

## 14. LEONES Evolution status

**Classification:** Experimental / integration candidate.

**Proposed role:**

> **TangleML — ML workflow orchestration / hybrid compute layer**

Position:

```text
LEONES Planner
      ↓
TangleML
      ↓
local / remote / hybrid compute
      ↓
training / evaluation artifacts
      ↓
ODS
```

### Provisional decision

**Include TangleML in LEONES Evolution's post-training research, but not as a structural ODS dependency.**

The next step should be a minimal PoC:

```text
LEONES-selected model
        ↓
Tangle pipeline
        ↓
dataset preparation
        ↓
QLoRA/SFT
        ↓
independent benchmark
        ↓
evidence package
        ↓
ODS deployment
```

The PoC should first validate local execution and then a second remote backend, comparing reproducibility, artifact handling, data transfer, cost and evidence.

## Sources

- TangleML: https://tangleml.com/
- Tangle backend: https://github.com/TangleML/tangle
- Tangle UI: https://github.com/TangleML/tangle-ui
- Tangle documentation: https://tangleml.com/docs/
- Tangle installation: https://tangleml.com/docs/install/
