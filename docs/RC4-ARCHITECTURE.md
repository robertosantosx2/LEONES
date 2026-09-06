# LEONES RC4 — recommendation, runtime and measured evidence

**Estado:** 🟡 **RC4 EN DESARROLLO**  
**Predecesor:** RC3 (fase cerrada el 5 de septiembre de 2026)  
**Decisión:** 6 de septiembre de 2026

## 1. Decisión arquitectónica

RC4 conserva la idea útil de RC3 de que la recomendación debe conocer **para qué quiere usar la IA el humano**, pero no recupera Hermes/OMH como arquitectura de selección u orquestación.

La entrada canónica de recomendación deja de ser solamente `hardware → candidate-set → FitLLM`.

Es:

```text
HARDWARE
   +
USER_INTENT[]                 obligatorio y anterior a recomendar
   ↓
FITLLM / LLMFIT
   +
HUGGING FACE EVIDENCE
   +
ARTIFICIAL ANALYSIS EVIDENCE
   ↓
10 candidatos orientativos / evidence-ranked
   ↓
3 candidatos ESTIMATED
   ↓
selección humana
   ↓
runtime físico
   ↓
medición
   ↓
MEASURED evidence
```

**HF y Artificial Analysis son entradas de evidencia de FitLLM/LLMFit; no son la recomendación final ni sustituyen la medición local.**

## 2. Contrato de recomendación RC4

El request canónico es:

```json
{
  "schema": "leones.rc4.recommendation-request.v1",
  "user_intent": {
    "required": true,
    "selection_mode": "multiple",
    "purposes": [
      "programming",
      "research",
      "reasoning"
    ]
  }
}
```

### Gate obligatorio

Una recomendación RC4 es inválida si:

```text
user_intent falta              → INVALID
selection_mode != multiple     → INVALID
purposes falta                 → INVALID
purposes == []                 → INVALID
```

Regla maestra:

```text
NO USER INTENT
      ↓
NO RECOMMENDATION
```

La pantalla de intención debe aparecer **antes** de ejecutar la selección de modelos.

## 3. Flujo Ubuntu

El preflight físico no puede saltarse la intención del usuario:

```text
Ubuntu preflight
      ↓
hardware_profile
      ↓
preguntar al humano
      ↓
user_intent[]
      ↓
validación RC4
      ↓
HF + Artificial Analysis
      ↓
FitLLM / LLMFit
      ↓
10 candidatos orientativos
      ↓
3 candidatos ESTIMATED
      ↓
elección del usuario
      ↓
artifact resolution
      ↓
consentimiento
      ↓
runtime / backend
      ↓
ejecución física
      ↓
medición
      ↓
MEASURED evidence
```

**El preflight nunca recomienda antes de preguntar al humano.**

## 4. Papel de Hugging Face

Hugging Face aporta principalmente **viabilidad técnica y señales de ecosistema**. El collector RC4 puede extraer:

- identificador y revisión del repositorio;
- autor, pipeline y librería;
- número de parámetros cuando el Hub lo expone;
- arquitectura/configuración;
- `torch_dtype`/dtype;
- contexto declarado por configuración;
- formatos disponibles o detectables: GGUF, safetensors, AWQ, GPTQ, EXL2;
- cuantizaciones detectables, por ejemplo Q4/Q4_K_M/Q8;
- almacenamiento declarado;
- descargas recientes y acumuladas;
- likes y trending score;
- fecha de modificación y creación;
- tags;
- estado gated;
- información específica de Transformers/Safetensors/GGUF cuando está disponible.

Estas señales sirven para determinar **qué modelos/artifacts son técnicamente plausibles y mantenidos**, no para afirmar rendimiento local medido. La API oficial de `huggingface_hub` expone `ModelInfo` con campos como configuración, parámetros de Safetensors, GGUF, descargas, likes, última modificación, tags y demás metadatos. 

## 5. Papel de Artificial Analysis

Artificial Analysis aporta señales independientes de **capacidad, calidad comparativa y rendimiento observado en su infraestructura**. El collector conserva, cuando están disponibles:

- Artificial Analysis Intelligence Index;
- Coding Index;
- benchmarks específicos publicados por AA, por ejemplo GPQA, MATH, LiveCodeBench, SciCode o TerminalBench;
- versión del Intelligence Index;
- velocidad mediana de salida;
- TTFT mediano;
- tiempo hasta primer token de respuesta cuando esté disponible;
- tiempo end-to-end cuando esté disponible;
- contexto, parámetros, modalidad y licencia cuando el nivel de API los expone.

Los valores de Artificial Analysis son **evidencia externa/hosted**. Nunca se copian a `measured_tps` ni se presentan como velocidad del equipo Ubuntu. La API de AA documenta el endpoint de modelos de lenguaje, sus índices, benchmarks y medianas de rendimiento. urlArtificial Analysis API Referencehttps://artificialanalysis.ai/api-reference/

## 6. Entrada de evidencia a FitLLM

El collector produce `leones.rc4.model-evidence.v1` y un bloque explícito `fitllm_input`:

```text
hardware
user_intent[]
model_evidence[]
    ├── huggingface
    └── artificial_analysis
          ↓
     FitLLM / LLMFit
```

El collector puede ordenar un conjunto amplio de candidatos para alimentar la selección. Esa ordenación es **evidence-ranked**, no una medición local ni una autorización de ejecución.

El objetivo operativo es llegar primero a un conjunto orientativo de **10 modelos** y, tras el razonamiento de FitLLM/LLMFit con hardware + intención + evidencia, producir los **3 candidatos ESTIMATED** que verá el usuario.

## 7. Prefiltro de memoria

El collector utiliza una estimación conservadora de memoria de pesos como **prefiltro**, no como cálculo final de runtime:

```text
weights ≈ parameters × bits_per_weight / 8
prefilter ≈ weights × 1.20
```

No se afirma que esto sea la VRAM/RAM final necesaria: KV cache, contexto efectivo, buffers, runtime, offload y arquitectura concreta pertenecen a FitLLM/runtime y deben resolverse posteriormente.

## 8. Estados de evidencia

```text
DECLARED
   ↓
ESTIMATED
   ↓
OBSERVED
   ↓
MEASURED
```

- **DECLARED:** información declarada por una fuente o repositorio.
- **ESTIMATED:** inferencia/selección previa a la ejecución física.
- **OBSERVED:** dato externo observado, por ejemplo rendimiento publicado por AA.
- **MEASURED:** resultado de una ejecución controlada sobre el equipo real.

Solo el runtime físico y el protocolo de medición de LEONES pueden producir `MEASURED`.

## 9. Separación de responsabilidades

```text
hardware_profile
    → hechos del equipo

user_intent
    → objetivos del humano

Hugging Face
    → metadata / artifacts / viabilidad técnica / adopción

Artificial Analysis
    → benchmarks externos / capacidad / rendimiento externo

FitLLM / LLMFit
    → adecuación y selección para hardware + intención + evidencia

runtime
    → ejecución real

benchmark/evidence bridge
    → medición y evidencia MEASURED
```

Ninguna fuente externa puede autorizar por sí sola una ejecución ni convertir una estimación en una medición.

## 10. Qué no recupera RC4

RC4 **no** recupera:

- Hermes como autoridad o selector;
- OMH como capa de orquestación;
- duplicación de runtimes;
- resultados externos tratados como `measured`;
- una recomendación generada antes de conocer la intención del usuario.

El `candidate-set` puede permanecer como representación interna/propuesta, pero deja de ser la frontera conceptual `hardware → candidate-set → FitLLM`.

## 11. Camino completo hasta la recomendación final

```text
                    ┌─────────────────┐
                    │    HARDWARE     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  USER INTENT[]  │
                    │    obligatorio  │
                    └────────┬────────┘
                             │
                ┌────────────▼────────────┐
                │     FITLLM / LLMFIT     │
                │ hardware + intent +    │
                │ external evidence       │
                └───────┬─────────┬───────┘
                        │         │
               ┌────────▼───┐ ┌──▼──────────────┐
               │ Hugging    │ │ Artificial      │
               │ Face       │ │ Analysis        │
               └────────────┘ └─────────────────┘
                        │         │
                        └────┬────┘
                             ▼
                    10 candidatos
                       orientativos
                             │
                             ▼
                     3 ESTIMATED
                             │
                       humano elige
                             │
                             ▼
                      runtime físico
                             │
                             ▼
                         medición
                             │
                             ▼
                     MEASURED evidence
```

Esta es la arquitectura de recomendación RC4 que debe utilizarse como baseline antes de continuar con el flujo físico de Ubuntu.
