# Investigación: TangleML y post-entrenamiento en LEONES Evolution

**Estado:** Experimental / investigación  
**Rama:** `ods-evolution`  
**Ámbito:** post-training, workflows ML y computación híbrida  
**Fecha:** 2026-10-02

## Resumen

TangleML es una plataforma open source de orquestación de pipelines de machine learning. Su arquitectura permite construir grafos de componentes contenedorizados, ejecutarlos localmente o sobre infraestructura remota y conservar artefactos, logs, metadatos y resultados de las ejecuciones. El backend declara licencia Apache-2.0 y el frontend `tangle-ui` también declara Apache-2.0.

Para **LEONES Evolution**, TangleML encaja mejor como **capa de orquestación de workflows de entrenamiento, post-entrenamiento, datos y evaluación**, no como sustituto de ODS.

La separación propuesta es:

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

## 1. Contexto arquitectónico de LEONES

La evolución de LEONES no debe estar limitada a «IA local». El objetivo superior es **libertad, independencia y control del usuario**. La computación local es actualmente una consecuencia práctica de ese objetivo, pero no una condición absoluta.

Por tanto, LEONES debe poder seleccionar:

- ejecución local;
- ejecución remota sobre infraestructura controlada;
- ejecución cloud cuando resulte compatible con los requisitos de independencia;
- ejecución híbrida, repartiendo etapas entre varios recursos.

ODS se mantiene como **plataforma de ejecución de IA**. LEONES decide y evidencia; ODS ejecuta y opera los modelos y servicios.

## 2. ¿Qué aporta TangleML?

TangleML proporciona:

- editor visual de pipelines;
- grafos de tareas y componentes;
- componentes definidos mediante `ComponentSpec`;
- ejecución de programas dentro de contenedores;
- interfaces explícitas de inputs/outputs;
- ejecución local y remota;
- distintos launchers;
- caching basado en contenido;
- reutilización de ejecuciones;
- artefactos y logs;
- trazabilidad de ejecuciones;
- reproducibilidad mediante contenedores y versionado de componentes;
- componentes escritos en distintos lenguajes.

El repositorio oficial describe ejecución local mediante Docker/Podman y ejecución remota; la documentación también describe una arquitectura API Server + Orchestrator + Launcher. Esto permite que el workflow y el recurso de cómputo estén desacoplados.

## 3. Encaje con post-entrenamiento

TangleML es especialmente interesante para convertir el post-training en pipelines reproducibles:

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

Una biblioteca LEONES de componentes podría incluir:

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

Tangle no necesita conocer la lógica de LEONES: ejecuta los componentes y conecta sus artefactos.

## 4. Computación híbrida

El principal interés estratégico no es simplemente que Tangle pueda ejecutarse «en cloud», sino que permite separar **workflow** y **recurso de ejecución**.

Ejemplo:

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

Otro caso:

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

LEONES debería ser quien decida este reparto a partir de:

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

## 5. TangleML como capa de ejecución de workflows

La posición arquitectónica propuesta es:

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

### Frontera con ODS

**TangleML:**

- workflows ML;
- preparación de datos;
- entrenamiento;
- experimentación;
- evaluación;
- generación de artefactos.

**ODS:**

- model serving;
- inferencia;
- agentes;
- tools;
- RAG;
- workflows operativos;
- servicios de IA;
- interfaz de usuario.

No conviene introducir Tangle como un segundo runtime de inferencia dentro de ODS.

## 6. Componentes y reproducibilidad

El modelo `ComponentSpec` de Tangle resulta especialmente adecuado para LEONES porque permite encapsular cada etapa como una unidad con:

- implementación;
- imagen de contenedor;
- inputs;
- outputs;
- metadatos;
- versión/digest.

Esto permite construir recetas reproducibles de post-training sin convertir LEONES en un framework de ejecución distribuida propio.

El caching basado en contenido también es relevante:

```text
dataset
   ↓
preprocessing
   ↓
deduplication
   ↓
training
```

Si solamente cambia la configuración del entrenamiento, las etapas anteriores pueden reutilizar resultados compatibles en lugar de ejecutarse de nuevo.

## 7. Independencia y cloud

TangleML es compatible con la visión de computación híbrida de LEONES porque declara ejecución local y cloud-agnostic.

Sin embargo, **usar Tangle en cloud no equivale automáticamente a independencia**.

LEONES debe distinguir:

### Tangle autohospedado

```text
usuario
  ↓
Tangle propio
  ↓
infraestructura elegida
```

Es el modelo más coherente con independencia.

### Tangle sobre proveedor externo

```text
usuario
  ↓
Tangle
  ↓
cloud externo
```

Puede ser válido, pero LEONES debe registrar la dependencia concreta.

### Servicio Tangle de terceros

Debe evaluarse separadamente porque aparecen dependencias sobre:

- identidad;
- almacenamiento;
- autenticación;
- infraestructura;
- claves;
- políticas del proveedor;
- portabilidad.

La arquitectura permite separar estas cuestiones; no las resuelve por sí misma.

## 8. Licencia

El backend `TangleML/tangle` declara **Apache-2.0** y el frontend `TangleML/tangle-ui` también declara **Apache-2.0**.

Esto satisface el requisito de software libre/open source de LEONES, pero **no proporciona el copyleft fuerte ni la protección anti-captura de red que LEONES puede preferir para componentes propios centrales**, como AGPL o EUPL.

| Criterio | TangleML |
|---|---|
| Open source | Sí |
| Software modificable | Sí |
| Uso local | Sí |
| Ejecución remota | Sí |
| Cloud-agnostic | Sí, según launcher/infraestructura |
| Contenedores | Sí |
| Reproducibilidad | Sí |
| Caching | Sí |
| Componentes reutilizables | Sí |
| Copyleft fuerte | No |
| Anti-captura cloud por licencia | No |
| Autohospedable | Sí |
| Adecuado para componente experimental LEONES | Sí |

La licencia del proyecto no debe confundirse con la licencia de los componentes, contenedores, modelos o datasets que se ejecuten mediante Tangle. LEONES debe conservar un inventario de licencias y procedencia de cada artefacto.

## 9. Encaje con la filosofía de evidencia de LEONES

Tangle puede conservar:

- grafo;
- logs;
- artefactos;
- metadatos;
- configuración;
- resultados de ejecución.

LEONES debe añadir la capa de evidencia:

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

Una ejecución Tangle no convierte automáticamente una cifra en una medición LEONES. Deben mantenerse separados:

- `estimated`;
- `reported`;
- `observed`;
- `measured`.

## 10. Encaje con ODS

La integración propuesta:

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

El artefacto final debería incluir, cuando sea posible:

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

## 11. Encaje por área

| Área | Encaje |
|---|---|
| Dataset pipelines | Alto |
| SFT | Alto |
| LoRA / QLoRA | Alto |
| DPO | Alto |
| GRPO / RLVR | Experimental |
| Distillation | Alto |
| Synthetic data | Alto |
| Evaluation | Alto |
| Benchmarking | Alto |
| Reproducibilidad | Alto |
| Experimentación | Alto |
| Local execution | Alto |
| Remote execution | Alto |
| Hybrid execution | Alto |
| Model serving | No: ODS |
| Agent runtime | No: ODS |
| Tool runtime | No: ODS |
| Discovery | Complementario: LEONES |
| Hardware profiling | LEONES |
| Evidence governance | LEONES |
| License/provenance governance | LEONES |

## 12. Hardware

Tangle permite que LEONES trate el hardware como un recurso de ejecución variable:

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

LEONES puede mantener la decisión independiente de Tangle: Tangle es el ejecutor del workflow seleccionado.

## 13. Riesgos y puntos pendientes

Antes de convertir Tangle en una dependencia de producción deben verificarse:

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

Especial atención: Tangle proporciona orquestación, aislamiento y portabilidad de workflows, pero **no debe interpretarse como una garantía automática de sandbox cifrada, ejecución confidencial o end-to-end encryption**. Esas propiedades deben comprobarse y diseñarse en la infraestructura concreta.

## 14. Estado LEONES Evolution

**Clasificación:** Experimental / candidato de integración.

**Rol propuesto:**

> **TangleML — ML workflow orchestration / hybrid compute layer**

Posición:

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

### Decisión provisional

**Integrar en la investigación de post-entrenamiento de LEONES Evolution, no como dependencia estructural de ODS.**

La siguiente fase debería ser un PoC mínimo:

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

El PoC debe probar primero ejecución local y después un segundo backend remoto, comparando reproducibilidad, artefactos, transferencia de datos, coste y evidencia.

## Fuentes

- TangleML: https://tangleml.com/
- Tangle backend: https://github.com/TangleML/tangle
- Tangle UI: https://github.com/TangleML/tangle-ui
- Tangle documentation: https://tangleml.com/docs/
- Tangle installation: https://tangleml.com/docs/install/
