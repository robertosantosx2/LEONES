# H06 — Auditoría inicial de cobertura y contrato

**Estado: 🟡 AUDITORÍA INICIAL COMPLETADA / H06 ABIERTA**

## 1. Objetivo

Determinar qué conocimiento estructurado existe ya en Atlas, qué contrato define `atlas/schema.json`, qué información contiene el feed operativo y qué dimensiones requieren normalización antes de ampliar cobertura.

Esta auditoría es deliberadamente previa a la incorporación masiva de modelos. El objetivo no es contar nombres sino identificar la calidad y utilidad del dato.

## 2. Contratos auditados

### Schema canónico

`atlas/schema.json` exige como mínimo `id`, `kind`, `name` y `evidence`. Define entidades para modelos, familias, organizaciones, runtimes, backends, cuantizaciones, herramientas, benchmarks, hardware, conocimiento y experimentos. También separa apertura, ejecución, hardware, evidencia externa, evaluación, recomendaciones, flags de calidad y ciclo de vida.

### Feed operativo

`data/prospection/atlas_feed.csv` ya contiene un contrato operativo amplio: identidad, organización, repositorio, runtime, formato, cuantización, hardware, workload, JGB, calidad, rendimiento, memoria, contexto y campos de evidencia técnica.

El feed es una fuente operativa; no sustituye al registro Atlas canónico.

## 3. Matriz inicial de cobertura

| Dimensión | Schema | Feed operativo | Observación |
|---|---|---|---|
| Identidad | `id`, `name`, `kind` | `model_id`, `model_name`, `source_id` | Existe en ambos, pero debe normalizarse a identidad canónica. |
| Familia | `family` | no garantizado como campo independiente en todas las filas | Prioridad de normalización. |
| Organización | `organization` | `organization` | Disponible; requiere validación de identidad. |
| Versión | `version` | no garantizada | Debe separarse de nombre/variante cuando exista evidencia. |
| Apertura | `openness.classification` | JGB separado | Debe preservarse la clasificación de apertura; JGB no la sustituye. |
| Arquitectura | `architecture` | `architecture` | Disponible en feed; normalización pendiente. |
| Artefactos | `artifacts` | repositorio/pesos/formato distribuidos | Requiere consolidación. |
| Ejecución | `execution` | runtime/backend/formato/cuantización | Buena cobertura operativa, pendiente de normalización. |
| Sistema del modelo | `model_system` | parámetros, memoria, contexto, runtime | Existe información útil; deben mantenerse semánticas distintas. |
| Hardware | `hardware` | `hardware_id` y campos asociados | El feed sirve como entrada operativa, pero el Atlas necesita entidad hardware estructurada. |
| Evidencia externa | `external_evidence[]` | URLs y estados dispersos | Requiere objeto de evidencia canónico por afirmación. |
| Experimentos | `experiments[]` | rendimiento observado cuando existe | No debe confundirse evidencia externa con medición LEONES. |
| Evaluación | `evaluation[]` | benchmark/quality en distintas capas | Requiere normalización por benchmark, resultado, fuente y fecha. |
| Calidad | `quality_flags[]` | flags/campos de calidad en distintas capas | Debe converger en el contrato canónico. |
| Evidencia | `evidence.state` | `evidence_status` + evidencia técnica | Debe existir una semántica única de estados. |
| Recomendación | `recommendation` | columnas de recomendación | El feed no debe convertirse automáticamente en registro canónico sin trazabilidad. |
| Lifecycle | `lifecycle` | no garantizado | Debe incorporarse en la normalización. |

## 4. Hallazgos principales

### 4.1 El Atlas ya tiene un esquema suficientemente rico

No corresponde ampliar indiscriminadamente el schema antes de comprobar su uso. La primera necesidad es crear una ruta estable de normalización desde los datos operativos hacia las entidades canónicas.

### 4.2 Existe una diferencia de nivel entre Atlas y feed

El feed es fundamentalmente tabular y orientado al pipeline. El schema es documental/entidad-relación y permite representar relaciones, evidencia, evaluación y calidad. No deben tratarse como si fueran el mismo objeto.

```text
FEED OPERATIVO
  ↓ extracción / enriquecimiento
NORMALIZADOR
  ↓
ATLAS CANÓNICO
  ├── entidades
  ├── relaciones
  ├── evidencia
  ├── evaluación
  └── quality_flags
```

### 4.3 Evidencia es una dimensión propia

El schema exige `evidence.state`, mientras que el feed mantiene estados y campos de evidencia técnica. La normalización debe impedir que una fuente externa se convierta automáticamente en `verified`.

### 4.4 Memoria y contexto requieren semántica explícita

El Atlas ya distingue `weight_memory_gb`, `kv_cache_gb`, `runtime_overhead_gb` y `memory_margin_gb`. Debemos evitar volver a introducir un único campo ambiguo de memoria total.

Del mismo modo, `context_length` debe representar capacidad soportada/descrita, no una afirmación de rendimiento bajo esa longitud.

### 4.5 Apertura y recomendación permanecen separadas

`openness.classification` y `recommendation` son dimensiones distintas. JGB tampoco debe convertirse en sustituto de la clasificación de apertura.

## 5. Prioridades resultantes

### P0 — Identidad canónica
Definir claves y reglas para model/family/organization/variant/version/repository/artifact.

### P1 — Evidencia canónica
Convertir procedencia, fecha, afirmación y estado en objetos trazables.

### P2 — Normalización técnica
Mapear arquitectura, parámetros, pesos, contexto, runtime, backend, cuantización y formatos al contrato Atlas.

### P3 — Benchmarks y evaluación
Separar benchmark, resultado, fuente, fecha y naturaleza de la medición.

### P4 — Hardware/recomendación
Consumir el conocimiento Atlas normalizado sin mezclar CABE/RULA, rendimiento, apertura y economía.

## 6. Decisión

**No se amplía todavía masivamente el catálogo.** Primero se construye y valida el normalizador/contrato de identidad y evidencia. Esto reduce duplicados y evita que los datos descubiertos entren en Atlas con una semántica que después haya que rehacer.

## 7. Próximo entregable H06

Crear `ARCHITECTURE.md` y `DECISIONS.md` con el modelo canónico de identidad y evidencia, seguido de una implementación de normalización sobre una muestra representativa del feed. La validación deberá demostrar trazabilidad desde la fuente hasta el registro Atlas.

## 8. Relación con H10

H10 queda cerrada y estable. H06 no debe modificar H10 salvo que aparezca una incompatibilidad de contrato demostrada.
