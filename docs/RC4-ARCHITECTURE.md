# LEONES RC4 — recommendation, evidence, runtime and measured evidence

**Estado:** 🟡 **RC4 EN DESARROLLO**  
**Predecesor:** RC3 (cerrada el 5 de septiembre de 2026)  
**Decisión:** 6 de septiembre de 2026

## 1. Decisión arquitectónica

RC4 mantiene la regla fundamental de que la recomendación debe conocer **para qué quiere usar la IA el humano**. La intención es obligatoria, múltiple y anterior a cualquier recomendación.

Hermes y OMH no forman parte del camino canónico RC4. Las referencias históricas se conservan donde sirven para trazabilidad de RC3.

La arquitectura canónica es:

```text
HARDWARE DETECTADO
        +
USER_INTENT[]                 obligatorio · selección múltiple · no vacío
        ↓
RESOURCE PREFLIGHT
        ↓
HUGGING FACE + ARTIFICIAL ANALYSIS
        ↓
LEONES EVIDENCE FEED · ≤100 modelos
        │
        ├──────────────────────────────┐
        │                              │
        ▼                              ▼
LLMFit/LLMFit CLI                 evidencia/procedencia
catálogo propio · ≤100                 HF + AA
        │                              │
        └──────── identidad ───────────┘
                       ↓
          EVIDENCE-BACKED INTERSECTION
                       ↓
              hasta 3 ESTIMATED
                       ↓
                SELECCIÓN HUMANA
                       ↓
             artifact resolution
                       ↓
              runtime físico Ubuntu
                       ↓
                   medición
                       ↓
                MEASURED evidence
```

### Regla esencial sobre LLMFit

La versión de LLMFit/LLMFit usada por RC4 no ofrece una opción soportada para inyectar un catálogo externo en `recommend`. **RC4 no inventa esa opción.**

Por ello, el feed HF + AA y el catálogo LLMFit son dos superficies independientes que se cruzan por identidad de modelo. Solo esa intersección puede producir candidatos RC4.

Esto es deliberado: evita afirmar que LLMFit puntuó directamente registros que nunca recibió.

## 2. Contrato de recomendación

```json
{
  "schema": "leones.rc4.recommendation-request.v1",
  "user_intent": {
    "required": true,
    "selection_mode": "multiple",
    "purposes": ["programming", "research", "reasoning"]
  }
}
```

### Gate obligatorio

```text
user_intent falta          → INVALID
selection_mode != multiple → INVALID
purposes falta             → INVALID
purposes == []             → INVALID
```

Regla maestra:

```text
NO USER INTENT
      ↓
NO RECOMMENDATION
```

La pantalla de intención debe aparecer antes de ejecutar la selección.

## 3. Propósitos y frontera LLMFit

RC4 conserva el array completo aunque LLMFit acepte un único `--use-case`.

| Intención RC4 | Frontera LLMFit |
|---|---|
| `programming` | `coding` |
| `reasoning` | `reasoning` |
| `research` | `general` |
| `chat` | `chat` |
| `multimodal` | `multimodal` |
| `embedding` | `embedding` |
| `general` | `general` |

La traducción ocurre exclusivamente en la frontera técnica. No reescribe `user_intent[]`.

## 4. Evidencia de Hugging Face

Hugging Face aporta principalmente evidencia de repositorio y viabilidad técnica. Cuando está disponible, RC4 puede conservar:

- identificador y revisión;
- autor, pipeline y librería;
- parámetros;
- arquitectura y configuración;
- dtype;
- contexto declarado;
- formatos GGUF, safetensors, AWQ, GPTQ y EXL2;
- cuantizaciones detectables;
- almacenamiento;
- descargas y adopción;
- likes/trending;
- fechas;
- tags;
- gated status.

Esta información es evidencia externa. No equivale a rendimiento medido en el equipo del usuario.

## 5. Evidencia de Artificial Analysis

Artificial Analysis aporta evidencia externa de capacidad, benchmarks y rendimiento en su infraestructura cuando los datos están disponibles.

El collector puede conservar, según disponibilidad:

- Intelligence Index;
- Coding Index;
- GPQA y otros benchmarks publicados;
- velocidad mediana de salida;
- TTFT y otras métricas de rendimiento;
- contexto, parámetros, modalidad y licencia.

La API de Artificial Analysis requiere autenticación para sus endpoints correspondientes. La ausencia de clave o de coincidencia no se convierte en un cero ni en una métrica inventada.

Los datos AA son **externos/hosted**. Nunca se copian a un campo de medición física LEONES.

## 6. Evidence feed RC4

El collector `scripts/collect_model_evidence.py` produce `leones.rc4.model-evidence.v1`.

Su bloque canónico es:

```text
hardware
user_intent[]
model_evidence[]             ≤100
    ├── hf
    ├── artificial_analysis
    └── hardware_prefilter
```

El feed se ordena mediante señales de evidencia para limitar un universo potencialmente grande. Esa ordenación es **evidence ranking/discovery**, no la autoridad final de recomendación.

El contrato de entrada declara siempre:

```json
{
  "max_models": 100,
  "model_count": 0
}
```

`model_count` refleja la cardinalidad real y puede ser menor que 100.

## 7. Por qué hay dos catálogos

La integración tiene una frontera explícita:

```text
              LEONES
                 │
        ┌────────┴────────┐
        │                 │
   HF + AA feed       LLMFit CLI
      ≤100               ≤100
        │                 │
        └───────┬─────────┘
                │
          identidad normalizada
                │
                ▼
       intersección verificable
                │
                ▼
        hasta 3 candidatos
```

No se dice que el catálogo HF/AA haya sido cargado dentro de LLMFit.

No se dice que LLMFit haya calculado sus puntuaciones sobre los campos AA.

Sí se dice que LEONES exige respaldo externo para que un resultado del catálogo LLMFit pueda entrar en la propuesta RC4.

## 8. Identidad de modelo

La comparación utiliza una clave conservadora:

1. Unicode NFKC.
2. minúsculas.
3. eliminación de prefijos de Hugging Face.
4. eliminación de caracteres no alfanuméricos.

La clave sirve solo para comparación. El `model_id` presentado al usuario se conserva sin alterar.

Se consideran `id`, `name`, `model` y `model_id` del resultado LLMFit y el identificador HF del feed.

No se utiliza un matching difuso final que pueda introducir una coincidencia ambigua.

## 9. Tres candidatos y estado ESTIMATED

El envelope RC4 fija:

```json
{
  "kind": "ESTIMATED",
  "evidence_level": "estimated",
  "selection_boundary": "evidence_backed_intersection",
  "execution_authorized": false,
  "measurement_authorized": false,
  "measured": false
}
```

Con tres coincidencias válidas:

```text
status = ok
candidate_count = 3
```

Con menos de tres:

```text
status = insufficient
candidate_count = N
```

Nunca se rellena artificialmente una tercera opción con un modelo sin evidencia.

## 10. Estados de evidencia

```text
DECLARED
   ↓
ESTIMATED
   ↓
OBSERVED
   ↓
MEASURED
```

- **DECLARED:** dato declarado por usuario, repositorio o fuente.
- **ESTIMATED:** inferencia, preselección o estimación previa a la ejecución local.
- **OBSERVED:** dato observado en una fuente externa o durante observación local, sin constituir necesariamente un benchmark final.
- **MEASURED:** resultado de una ejecución física protocolizada sobre el equipo real.

Solo el runtime físico y el protocolo de medición LEONES producen evidencia `MEASURED`.

## 11. Prefiltro de memoria

El collector usa un cálculo de pesos como prefiltro:

```text
weights ≈ parameters × bits_per_weight / 8
prefilter ≈ weights × 1.20
```

No es una predicción completa del consumo de runtime. No incorpora de forma suficiente KV cache, buffers, contexto efectivo, offload o particularidades del backend.

RAM y VRAM son magnitudes distintas.

**Swap no cuenta como RAM física.**

## 12. Resource preflight

El preflight separa capacidad física de presupuesto de instalación/actualización.

```text
RAM física disponible
swap separado
espacio libre de disco
ODS
Magnitude
FitLLM / LLMFit
runtime
modelo
margen de seguridad
```

La regla de disco es:

```text
disk_free >
ODS update/install
+ Magnitude update/install
+ FitLLM / LLMFit update/install
+ runtime
+ model artifact
+ safety margin
```

Si un tamaño de instalación o actualización es desconocido, se conserva como `null`. No se inventa una cifra.

## 13. Separación de responsabilidades

```text
hardware_profile
    → hechos del equipo

user_intent
    → objetivos del humano

resource_preflight
    → capacidad y presupuesto

Hugging Face
    → metadata / artifacts / adopción

Artificial Analysis
    → benchmarks externos / índices / rendimiento externo

evidence collector
    → feed ≤100 y trazabilidad

LLMFit
    → preselección desde su catálogo propio

intersection boundary
    → exige respaldo en el feed externo

human selection
    → autoridad sobre el candidato a ejecutar

runtime
    → ejecución real

benchmark/evidence bridge
    → medición y evidencia MEASURED
```

Ninguna fuente externa autoriza por sí sola una ejecución.

## 14. Ubuntu

El runner por defecto es RC4:

```text
./leones
   ↓
user_intent[]
   ↓
evidence feed HF + AA
   ↓
LLMFit ≤100
   ↓
intersección
   ↓
hasta 3 ESTIMATED
   ↓
selección humana
   ↓
artifact resolution / instalación
   ↓
runtime físico Ubuntu
   ↓
benchmark
   ↓
MEASURED evidence
```

La compatibilidad histórica sigue explícitamente disponible:

```text
./leones --rc2
```

La compatibilidad no convierte RC2 en la arquitectura canónica de RC4.

## 15. Qué no recupera RC4

RC4 no recupera:

- Hermes como selector u orquestador canónico;
- OMH como autoridad de selección;
- resultados externos tratados como `MEASURED`;
- recomendación antes de conocer la intención;
- flags inexistentes para inyectar catálogos en LLMFit;
- ejecución automática como consecuencia de una recomendación.

Las referencias históricas permanecen donde sean necesarias para preservar la trazabilidad de RC3.

## 16. Criterio de cierre de la capa de recomendación

La capa queda lista para pasar al siguiente gate cuando una validación reproducible demuestre:

1. intención múltiple obligatoria antes de recomendar;
2. rechazo de intención vacía;
3. hardware detectado sin capacidades inventadas;
4. feed HF + AA con máximo 100 registros;
5. ausencia explícita de métricas AA cuando no estén disponibles;
6. LLMFit consultado mediante su CLI real;
7. intersección por identidad verificable;
8. tres candidatos `ESTIMATED` cuando existen tres coincidencias;
9. `insufficient` cuando no existen tres;
10. ningún candidato marcado `MEASURED` en esta fase;
11. `execution_authorized=false`;
12. handoff a selección humana y posteriormente al runtime físico Ubuntu.

## 17. Documentación complementaria

- `docs/RC4-EVIDENCE-BRIDGE.md` — contrato y razonamiento del puente HF + AA → intersección LLMFit.
- `docs/completed/RC4-DECISION-FITLLM-RECOMMENDER-2026-09-06.md` — decisión arquitectónica.
- `scripts/collect_model_evidence.py` — collector de evidencia.
- `scripts/rc4_fitllm_recommend.py` — recomendador y frontera de intersección.
- `runtime_selection/llmfit.py` — límite de integración con la CLI LLMFit.
- `tests/test_rc4_fitllm_recommend.py` — pruebas contractuales del puente.

**Nota de estado:** la capa de recomendación queda endurecida, pero RC4 no se declara cerrada hasta validar físicamente la cadena completa en Ubuntu.
