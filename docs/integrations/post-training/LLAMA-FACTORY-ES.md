# Investigación: LLaMA-Factory como servicio de post-entrenamiento de ODS

## Resumen ejecutivo

LLaMA-Factory es un candidato muy sólido para integrarse en ODS, pero la frontera recomendada no es convertirlo en una dependencia directa del runtime de inferencia. La integración debería realizarse como un **servicio de post-entrenamiento de ODS**, con LLaMA-Factory como uno de sus providers.

La arquitectura propuesta es:

```text
                         ODS
                          │
        ┌─────────────────┼──────────────────┐
        │                 │                  │
     Inferencia         Agentes             RAG
        │                 │                  │
        └─────────────────┼──────────────────┘
                          │
                  Post-Training Service
                          │
                 ┌────────┴────────┐
                 │                 │
          LLaMA-Factory       otros providers
                 │
                 ▼
             Entrenamiento
                 │
                 ▼
             Artefactos
                 │
                 ▼
          Model Registry
                 │
                 ▼
              Runtime ODS
```

Principio central:

> **LLaMA-Factory debe ser un motor de entrenamiento detrás de un contrato de servicio de ODS. ODS debe gestionar el ciclo de vida del job, API, scheduling, artefactos, validación y despliegue; LLaMA-Factory debe aportar la implementación del post-entrenamiento.**

Esto mantiene ODS independiente de un framework concreto y permite añadir posteriormente Axolotl, Unsloth, TRL/PEFT o torchtune bajo el mismo contrato.

---

## 1. Perfil del proyecto

LLaMA-Factory es un framework open source de post-entrenamiento para una amplia variedad de modelos de lenguaje y multimodales. Entre sus capacidades documentadas se encuentran:

- supervised fine-tuning (SFT);
- LoRA y QLoRA;
- fine-tuning completo;
- continual pre-training;
- métodos de optimización de preferencias como DPO y otros relacionados;
- entrenamiento multimodal;
- cuantización y exportación;
- merge de adapters LoRA;
- evaluación;
- inferencia;
- entrenamiento distribuido;
- WebUI;
- integraciones orientadas a API/serving.

Utiliza un sistema unificado de configuración/CLI y ofrece vías de instalación basadas en Docker. El proyecto declara licencia Apache-2.0 en sus metadatos de paquete.

**Importante:** la licencia del framework, la licencia del modelo, la licencia del dataset y las condiciones del proveedor de infraestructura son cuestiones independientes.

---

## 2. Por qué importa la frontera de servicio

Una integración directa sería:

```text
ODS → LLaMA-Factory
```

La arquitectura recomendada es:

```text
ODS
 │
 └── Post-Training Service
       │
       └── Provider Adapter
              │
              └── LLaMA-Factory
```

Así la API de ODS permanece estable aunque cambie el backend.

ODS debería exponer conceptos como:

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

y no convertir las opciones específicas de la CLI de LLaMA-Factory en el contrato público.

---

## 3. Servicio Post-Training de ODS

Una primera API podría proporcionar conceptualmente:

```text
POST /api/post-training/jobs
GET  /api/post-training/jobs
GET  /api/post-training/jobs/{id}
POST /api/post-training/jobs/{id}/cancel
GET  /api/post-training/jobs/{id}/logs
GET  /api/post-training/jobs/{id}/artifacts
POST /api/post-training/jobs/{id}/benchmark
```

Una petición de alto nivel podría ser:

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

ODS traduciría esta petición a la configuración específica necesaria para LLaMA-Factory.

---

## 4. LLaMA-Factory como provider de ODS

El servicio debería definir una abstracción:

```text
PostTrainingProvider
│
├── LLaMA-Factory
├── Axolotl
├── Unsloth
├── TRL/PEFT
└── torchtune
```

Un registro de capacidades podría contener:

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

El registro debe distinguir entre **capacidad soportada en principio** y **capacidad validada para un modelo/runtime/entorno concreto**.

---

## 5. Ciclo de vida del job

Un training job debería ser un objeto de primera clase de ODS.

Por ejemplo:

```text
Training Job #184
│
├── Modelo base
├── Dataset
├── Objetivo: SFT
├── Adaptación: LoRA
├── Provider: LLaMA-Factory
├── Versión del provider
├── Configuración
├── Estado
├── Logs
├── Métricas
└── Artefactos
```

El ciclo debe ser explícito:

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
CONVERT (si es necesario)
  ↓
REGISTER
  ↓
BENCHMARK
  ↓
DEPLOY
```

Es preferible a exponer un proceso CLI largo y opaco.

---

## 6. Ejecución mediante contenedores

LLaMA-Factory proporciona vías de despliegue orientadas a Docker. Esto encaja con un servicio ODS que lance jobs de entrenamiento aislados.

El patrón preferido es una ejecución **orientada a jobs**, no mantener el framework activo permanentemente:

```text
ODS
 │
 │ crear job
 ▼
Post-Training Scheduler
 │
 │ asignar compute
 ▼
Contenedor LLaMA-Factory
 │
 │ entrenamiento
 ▼
artefacto
 │
 ▼
validación / registro
 │
 ▼
el contenedor puede terminar
```

Esto separa las cargas de entrenamiento de las cargas de inferencia y permite que ODS gestione explícitamente los recursos.

---

## 7. ODS debe gestionar el scheduling

El provider de entrenamiento no debería convertirse en el gestor de recursos de ODS.

Un scheduler futuro puede razonar sobre:

- aceleradores disponibles;
- CPU y memoria;
- almacenamiento;
- concurrencia;
- prioridad;
- aislamiento;
- ejecución local o remota;
- capacidades del provider;
- políticas del usuario;
- coste y restricciones de infraestructura.

Conceptualmente:

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

Posteriormente el scheduler podrá seleccionar otro provider sin cambiar la API de ODS.

---

## 8. Integración con Dataset Registry y Model Registry

Los datasets deberían ser artefactos gestionados por ODS y no simples rutas arbitrarias pasadas a un comando de entrenamiento.

Un dataset debería incluir metadatos como:

```text
identificador
versión
hash
formato
licencia
procedencia
proceso de creación
clasificación de privacidad
```

Igualmente, un modelo debería registrar:

```text
modelo base
provider
versión del provider
configuración de entrenamiento
versión del dataset
adapter/checkpoint
hash del artefacto
licencia/procedencia
```

Esto hace que el entrenamiento sea reproducible y auditable.

---

## 9. Los adapters como artefactos de primera clase

ODS no debería exigir que todos los jobs produzcan un modelo completamente fusionado.

Un job LoRA/QLoRA puede producir:

```text
Modelo base
    +
LoRA adapter
```

El adapter se registra independientemente:

```text
Adapter
├── referencia al modelo base
├── pesos del adapter
├── metadatos del tokenizer
├── configuración de entrenamiento
├── procedencia
└── resultados de validación
```

ODS puede decidir entonces:

- cargar el adapter directamente si el runtime seleccionado lo soporta;
- fusionarlo con el modelo base;
- convertir el modelo resultante;
- conservar el adapter como artefacto reutilizable.

---

## 10. Frontera de formatos de modelo

Esta es una frontera crítica.

LLaMA-Factory trabaja principalmente en el ecosistema Hugging Face/Transformers. ODS puede utilizar otros formatos y runtimes, incluido serving basado en GGUF mediante llama-server.

Por tanto no debemos asumir:

```text
salida de LLaMA-Factory = artefacto ejecutable por ODS
```

El servicio debe tener una fase explícita:

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

Una capa independiente de conversión puede gestionar:

```text
HF checkpoint → GGUF
LoRA adapter → modelo fusionado
modelo → artefacto específico del runtime
```

Esto mantiene la conversión de modelos separada del backend de entrenamiento.

---

## 11. Integración con llama-server

Un flujo representativo de ODS sería:

```text
LLaMA-Factory
      │
      ▼
LoRA / QLoRA / checkpoint completo
      │
      ▼
merge/export
      │
      ▼
artefacto compatible con Hugging Face
      │
      ▼
pipeline de conversión
      │
      ▼
GGUF
      │
      ▼
ODS llama-server
```

Debe considerarse un **pipeline que hay que validar**, no una compatibilidad garantizada por diseño.

El PoC debe verificar:

1. entrenamiento;
2. exportación del adapter o checkpoint;
3. merge cuando sea necesario;
4. conversión;
5. registro en ODS;
6. carga mediante llama-server;
7. corrección de inferencia;
8. equivalencia/regresión mediante benchmark.

---

## 12. Dashboard de ODS

La WebUI de LLaMA-Factory no debería ser la interfaz principal de integración.

ODS debería terminar ofreciendo:

```text
Dashboard
└── Post-Training
    ├── Crear job
    ├── Jobs
    ├── Datasets
    ├── Adapters
    ├── Modelos
    ├── Artefactos
    └── Benchmarks
```

La UI de LLaMA-Factory puede mantenerse disponible para debugging o workflows avanzados si resulta útil, pero la experiencia normal debería ser nativa de ODS.

---

## 13. Orquestación de workflows

TangleML y LLaMA-Factory tienen responsabilidades diferentes.

Un workflow de ODS podría ser:

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

En esta arquitectura:

- **TangleML** puede orquestar el workflow;
- **LLaMA-Factory** ejecuta la etapa de entrenamiento;
- **ODS** posee la frontera del servicio y el ciclo operativo.

Así ningún proyecto tiene que asumir responsabilidades que no le corresponden.

---

## 14. Separación ODS + LEONES

La integración debe preservar la separación arquitectónica definida en LEONES Evolution:

```text
LEONES
  │
  │ decide / perfila / evalúa
  ▼
ODS
  │
  │ opera
  ▼
Post-Training Service
  │
  ▼
LLaMA-Factory
  │
  │ entrena/adapta
  ▼
Artefacto
  │
  ▼
Validación + despliegue ODS
```

LEONES puede proporcionar un plan de ejecución de alto nivel:

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

ODS ejecuta ese plan.

ODS debe seguir siendo útil sin LEONES; LEONES aporta discovery, profiling, selección de provider y evidencia, no una dependencia obligatoria de ODS.

---

## 15. Ejecución híbrida e independencia

El servicio debe permitir diferentes ubicaciones de ejecución bajo la misma API:

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

La ejecución remota no debe considerarse automáticamente independiente.

ODS/LEONES debería registrar:

- propiedad de la infraestructura;
- destino de los datos;
- cifrado;
- propiedad/control de las claves;
- retención;
- requisitos de red;
- portabilidad del modelo y dataset;
- condiciones del proveedor;
- portabilidad del artefacto;
- posibilidad de reproducir el workflow en otra infraestructura.

El objetivo es **libertad e independencia**, no simplemente ejecución local.

---

## 16. Frontera de seguridad

El entrenamiento es una carga de seguridad diferente de la inferencia.

El contenedor del provider puede acceder a:

- modelos;
- datasets;
- paquetes Python;
- aceleradores;
- model hubs;
- object storage;
- outputs.

Por tanto, el servicio debería preferir:

```text
ods-post-training job
├── contenedor aislado
├── volúmenes explícitos
├── red controlada
├── secretos controlados
├── exportación explícita de artefactos
└── sin acceso implícito al filesystem del host
```

Los traces de producción no deben convertirse automáticamente en datos de entrenamiento. Cualquier dataset derivado de ODS debe pasar por política explícita, filtrado, redacción y consentimiento.

---

## 17. Observabilidad y evidencia

ODS debería capturar:

```text
estado del job
logs
métricas de entrenamiento
métricas de evaluación
uso de recursos
tiempo transcurrido
checkpoints
versiones de software
configuración
hashes de artefactos
```

Las categorías de evidencia deben permanecer separadas:

- **reported** — publicado por LLaMA-Factory u otro proyecto;
- **estimated** — calculado o previsto por ODS/LEONES;
- **observed** — observado durante una ejecución sin benchmark independiente;
- **measured** — producido por un benchmark controlado de ODS/LEONES.

Las afirmaciones publicadas por el framework no deben convertirse silenciosamente en mediciones de LEONES.

---

## 18. Licencia y procedencia

Los metadatos del paquete de LLaMA-Factory declaran Apache-2.0.

Para la integración en ODS, sin embargo, deben mantenerse separadas:

```text
licencia de LLaMA-Factory
        ≠
licencia del modelo base
        ≠
licencia del dataset
        ≠
procedencia de los datos
        ≠
condiciones de la infraestructura
```

Que un provider sea open source no garantiza por sí mismo independencia respecto de infraestructura alojada ni libertad de uso de cualquier modelo o dataset.

ODS debería conservar la procedencia a nivel de artefacto.

---

## 19. Fases recomendadas

### Fase 1 — Proof of Concept del provider

```text
ODS
 ↓
Post-Training API
 ↓
contenedor LLaMA-Factory
 ↓
job SFT/LoRA
 ↓
artefacto
```

### Fase 2 — Ciclo de vida del artefacto

```text
artefacto
 ↓
validación
 ↓
conversión
 ↓
ODS Model Registry
 ↓
despliegue
```

### Fase 3 — Dashboard nativo ODS

```text
Dashboard
 ↓
Post-Training
 ↓
crear / monitorizar / validar / desplegar
```

### Fase 4 — Servicio multi-provider

```text
Post-Training Service
├── LLaMA-Factory
├── Axolotl
├── Unsloth
└── TRL/PEFT
```

### Fase 5 — Integración con LEONES

```text
LEONES
 ↓
selección de provider
 ↓
ODS Post-Training
 ↓
entrenamiento
 ↓
benchmark
 ↓
evidencia
```

---

## 20. Criterios de aceptación del PoC

El primer PoC debería demostrar el recorrido completo:

```text
modelo
 ↓
dataset
 ↓
ODS job
 ↓
LLaMA-Factory
 ↓
artefacto LoRA/QLoRA
 ↓
validación
 ↓
merge/export
 ↓
conversión
 ↓
registro ODS
 ↓
llama-server u otro runtime ODS
 ↓
benchmark
```

Debe comprobar:

- configuración reproducible;
- aislamiento del provider/contenedor;
- integridad del artefacto;
- compatibilidad modelo/runtime;
- despliegue correcto;
- corrección de inferencia;
- resultados de benchmark;
- procedencia y metadatos de licencia;
- separación clara de evidencia estimated/reported/observed/measured.

---

## 21. Evaluación arquitectónica

| Área | Evaluación |
|---|---|
| ODS Post-Training Service | **Encaje muy alto** |
| Abstracción de providers | **Encaje muy alto** |
| SFT | **Encaje muy alto** |
| LoRA / QLoRA | **Encaje muy alto** |
| Preference optimization | **Encaje alto** |
| Post-training multimodal | **Encaje alto** |
| Jobs mediante contenedores | **Encaje alto** |
| Producción de artefactos | **Encaje alto** |
| ODS Model Registry | **Encaje alto; requiere adapter** |
| Dashboard nativo | **Buen encaje futuro** |
| Orquestación de workflows | **Complementario con TangleML** |
| Compatibilidad directa con llama-server | **Requiere validación/conversión** |
| Ejecución remota/híbrida | **Buen encaje, sujeto a independencia del provider** |
| Dependencia del core de ODS | **No recomendada** |

## Decisión

**Incluir LLaMA-Factory como primer provider experimental de un ODS Post-Training Service.**

No convertir LLaMA-Factory en una dependencia obligatoria del core de inferencia de ODS.

Arquitectura preferida:

```text
                 LEONES
                    │
             decisión / evidencia
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
       LLaMA-Factory    futuros providers
             │
             ▼
          artefacto
             │
       validar/convertir
             │
             ▼
        ODS Model Registry
             │
             ▼
         ODS Runtime
```

Esto proporciona a ODS capacidad de evolución de modelos manteniendo intercambiabilidad de providers y dejando a LEONES la selección, profiling y evidencia.

## Referencias

- LLaMA-Factory: https://github.com/hiyouga/LlamaFactory
- Ejemplos de LLaMA-Factory: https://github.com/hiyouga/LlamaFactory/tree/main/examples
- Documentación de datos: https://github.com/hiyouga/LlamaFactory/blob/main/data/README.md
