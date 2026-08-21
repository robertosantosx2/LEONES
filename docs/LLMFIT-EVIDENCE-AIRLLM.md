# LEONES — LLMFit + evidencia técnica + AirLLM

## Estado

**🟢 Arquitectura cerrada para preselección y recomendación · 🟡 mediciones locales pendientes por máquina/modelo**

Este documento fija el contrato entre tres capas que no deben confundirse:

1. **LLMFit**: preselector hardware-aware.
2. **Evidencia técnica**: valida identidad, capacidad, soporte, rendimiento y procedencia.
3. **AirLLM**: backend de contingencia para configuraciones donde el cuello de botella principal es la memoria disponible, especialmente cuando el modelo no cabe de forma convencional.

La recomendación final de LEONES nunca es simplemente la recomendación de LLMFit ni una afirmación de AirLLM. Es una decisión trazable sobre **modelo + variante + cuantización/formato + runtime + hardware + carga de trabajo + evidencia**.

## Principio de separación

```text
                 HARDWARE REAL
                       │
                       ▼
              ┌─────────────────┐
              │ leones-hardware │
              └────────┬────────┘
                       │ perfil
                       ▼
              ┌─────────────────┐
              │     LLMFit      │
              │  PRESELECCIÓN   │
              └────────┬────────┘
                       │ TOP-N + hipótesis
                       ▼
          ┌───────────────────────────┐
          │ EVIDENCE / IDENTITY GATE  │
          └────────────┬──────────────┘
                       │ candidatos válidos
                       ▼
        ┌───────────────────────────────┐
        │ ROUTE / RUNTIME SELECTION     │
        │ convencional │ AirLLM         │
        └───────────────┬───────────────┘
                        ▼
              ┌─────────────────┐
              │  LEONES INFER   │
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │ LOTB / QUALITY  │
              └────────┬────────┘
                       ▼
                RECOMMENDATION
```

## 1. LLMFit: función y límites

LLMFit detecta RAM, CPU, GPU/VRAM y backend; mantiene un catálogo de modelos; estima memoria, velocidad, calidad y contexto; soporta MoE, cuantización dinámica y varios runtimes. Su salida debe tratarse como **estimación**, no como medición LEONES.

La documentación actual de LLMFit describe cuatro dimensiones de puntuación: `quality`, `speed`, `fit` y `context`, y permite obtener recomendaciones en JSON para consumo por scripts/agentes. También expone comandos de inspección y benchmark que permiten separar estimación de medición real.

Contrato LEONES: conservar siempre la salida original de LLMFit y no sobrescribirla con valores derivados de LEONES.

Campos mínimos:

- `llmfit_source_version`
- `llmfit_model_id`
- `llmfit_fit`
- `llmfit_quality_estimate`
- `llmfit_speed_estimate`
- `llmfit_context_fit`
- `llmfit_quantization`
- `llmfit_memory_estimate`
- `llmfit_runtime`
- `llmfit_run_mode`
- `llmfit_raw_json`
- `llmfit_timestamp`

### Regla de promoción

`LLMFIT_ESTIMATE` nunca puede convertirse automáticamente en `LEONES_VERIFIED`.

Una recomendación puede usar LLMFit para reducir el espacio de búsqueda, pero necesita evidencia adicional antes de presentarse como recomendación fuerte.

## 2. Evidencia técnica

La evidencia se almacena por afirmación, no como una única etiqueta de confianza.

### Tipos

| Tipo | Qué demuestra | Prioridad |
|---|---|---:|
| `PRIMARY` | documentación/repositorio/model card del proyecto | 100 |
| `LOCAL_MEASURED` | prueba reproducible en hardware real | 100 |
| `INDEPENDENT_MEASURED` | benchmark externo reproducible | 90 |
| `COMMUNITY_MEASURED` | medición comunitaria trazable | 70 |
| `VENDOR_CLAIM` | afirmación del proyecto/fabricante sin reproducción LEONES | 50 |
| `INFERENCE` | deducción de LEONES | 20 |

Una fuente no se convierte en medición por estar publicada en GitHub. Una afirmación comercial tampoco se convierte en benchmark.

### Estados de evidencia

```text
UNKNOWN
  │
  ├── CLAIM_ONLY
  ├── DOCUMENTED
  ├── REPORTED
  ├── REPRODUCIBLE
  └── VERIFIED
```

`VERIFIED` requiere protocolo reproducible y datos suficientes para reconstruir el resultado. `REPORTED` es válido para radar/investigación, pero no debe presentarse como rendimiento oficial LEONES.

### Campos mínimos de una evidencia

```text
claim_id
source_type
source_url
source_version_or_revision
observed_at
model_id
model_revision
hardware_id
runtime
runtime_version
quantization
context_tokens
input_tokens
output_tokens
concurrency
metric
value
unit
protocol
reproducibility_state
notes
```

## 3. AirLLM: papel arquitectónico

AirLLM no sustituye a LLMFit. Es una **ruta de ejecución** que debe activarse cuando el candidato puede ser útil pero la ejecución convencional queda limitada por memoria.

La implementación actual de AirLLM utiliza Transformers como camino de ejecución y hace *streaming* de pesos por capas: los pesos se preparan en disco y se llevan a GPU antes de ejecutar el módulo correspondiente, liberándolos después. Esto reduce el pico de memoria de GPU, pero desplaza parte del coste hacia almacenamiento, transferencia y tiempo de ejecución.

AirLLM declara soporte de modelos modernos y en su versión 3.1.0 incorpora, entre otras mejoras, FP8 nativo y soporte de arquitecturas/modelos recientes. Es importante distinguir esas capacidades documentadas de resultados de rendimiento obtenidos por LEONES.

### AirLLM no debe activarse por defecto

La ruta AirLLM se selecciona cuando:

- el modelo es elegible y está suficientemente identificado;
- la ejecución convencional no cabe o deja un margen insuficiente;
- existe suficiente RAM y almacenamiento local;
- el backend/modelo está soportado;
- la latencia esperada sigue siendo compatible con el objetivo del usuario;
- la evidencia no contiene una contradicción crítica.

### Costes que debe registrar LEONES

AirLLM cambia el cuello de botella. Por ello deben registrarse, además de los campos normales:

- memoria GPU pico;
- RAM pico;
- lectura de disco;
- tiempo de preparación/carga;
- TTFT;
- TPOT o tokens/s de decode;
- tokens/s efectivos;
- errores de transferencia/carga;
- temperatura/throttling cuando sea relevante;
- tamaño y ubicación del cache/checkpoint transformado.

## 4. AirLLM y afirmaciones de capacidad

Las afirmaciones de la documentación de AirLLM sobre ejecutar modelos muy grandes con poca VRAM son útiles como **capacidad declarada**, pero no deben entrar directamente como rendimiento LEONES.

Existe además una incidencia pública que cuestiona la reproducibilidad de algunas afirmaciones de memoria/rendimiento del proyecto y pide artefactos de benchmark reproducibles. LEONES debe conservar esta distinción: **claim del proyecto ≠ evidencia independiente ≠ medición local**.

Por tanto:

```text
AirLLM README claim
       │
       ▼
VENDOR_CLAIM
       │
       ├── si existe protocolo reproducible externo → INDEPENDENT_MEASURED
       └── si LEONES lo ejecuta → LOCAL_MEASURED
```

## 5. Selección de runtime

La recomendación debe producir una ruta de ejecución explícita:

| Situación | Ruta primaria | AirLLM |
|---|---|---|
| Modelo cabe holgadamente en memoria rápida | runtime nativo recomendado | no |
| Cabe justo | runtime con margen/quant adecuado | fallback |
| No cabe en VRAM pero hay RAM suficiente | CPU/offload o runtime apropiado | candidato |
| Modelo grande con streaming por capas viable | runtime compatible | candidato fuerte |
| Contexto/concurrencia altos | runtime con gestión KV/batching adecuada | normalmente penalizar |
| Agentes con latencia estricta | runtime medido | penalizar si AirLLM degrada TTFT/TPOT |

El selector no debe asumir que «menos VRAM» significa «mejor». Debe optimizar la experiencia objetivo.

## 6. Contrato de recomendación

La capa final recibe un conjunto de candidatos enriquecidos y devuelve:

```text
recommendation_id
hardware_profile
workload_profile
candidate_model
model_revision
runtime
quantization
execution_route
fit_state
evidence_state
estimated_score
measured_score
confidence
reasons[]
limitations[]
verification_commands[]
```

### Estados de `fit_state`

- `FIT_COMFORTABLE`
- `FIT_TIGHT`
- `FIT_OFFLOAD`
- `FIT_AIRLLM`
- `FIT_UNKNOWN`
- `DO_NOT_RUN`

### Estados de recomendación

- `MEASURED_RECOMMENDED`
- `EVIDENCE_SUPPORTED`
- `ESTIMATE_ONLY`
- `BLOCKED`

`MEASURED_RECOMMENDED` tiene prioridad sobre `EVIDENCE_SUPPORTED`, y este sobre `ESTIMATE_ONLY`.

## 7. Puntuación: no mezclar hechos con estimaciones

LEONES debe conservar componentes separados:

```text
quality_score
fit_score
speed_score
context_score
evidence_score
measured_score
agentic_score
```

El agregador puede producir un `recommendation_score`, pero debe poder reconstruirse desde sus componentes.

Regla de precedencia:

1. Restricciones duras: identidad, licencia/eligibilidad, soporte, memoria y errores críticos.
2. Evidencia: calidad/procedencia/reproducibilidad.
3. Ajuste al workload: coding, reasoning, general, agentic, multimodal, etc.
4. Rendimiento medido.
5. Estimaciones LLMFit como prior cuando no hay medición local.

No se permite que una puntuación alta de LLMFit compense un `BLOCKED` de evidencia o ejecución.

## 8. Flujo de recomendación de LEONES

```text
hardware probe
   ↓
normalized hardware profile
   ↓
LLMFit recommend --json
   ↓
TOP-N
   ↓
identity + model revision
   ↓
license/open-status gate
   ↓
technical evidence enrichment
   ↓
route selection
   ├── conventional runtime
   └── AirLLM fallback
   ↓
local benchmark when feasible
   ↓
LOTB for agentic candidates
   ↓
recommendation contract
   ↓
user-facing recommendation
```

## 9. Reglas de seguridad epistemológica

- No presentar estimaciones como mediciones.
- No presentar claims de AirLLM como pruebas de rendimiento LEONES.
- No sustituir la identidad exacta del modelo por el nombre de la familia.
- No mezclar cuantizaciones ni revisiones del modelo.
- No extrapolar tok/s de otro hardware como si fueran del hardware del usuario.
- No ocultar que AirLLM puede cambiar el cuello de botella de VRAM a RAM/IO.
- No recomendar un modelo solo porque «cabe».
- No usar benchmarks públicos contaminados o ambiguos como prueba única; el protocolo de evaluación debe conservarse.

## 10. Criterio de cierre

La arquitectura queda cerrada cuando el recomendador puede contestar, para cada candidato:

> **qué modelo exacto, en qué revisión, con qué cuantización/formato, mediante qué runtime, en qué hardware, con qué evidencia, con qué nivel de ajuste y con qué incertidumbre.**

El sistema puede recomendar con una estimación antes de medir, pero debe decir que es una estimación. Tras una medición reproducible, la recomendación se actualiza sin borrar la estimación original.
