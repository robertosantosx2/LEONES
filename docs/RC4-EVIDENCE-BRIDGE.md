# LEONES RC4 — puente de evidencia HF + Artificial Analysis → FitLLM/LLMFit

**Fecha:** 6 de septiembre de 2026  
**Estado:** implementado en `rc4-fitllm-recommender`  
**Ámbito:** capa declarativa de selección y preselección; no sustituye el runtime físico.

## 1. Objetivo

RC4 necesita que una recomendación no aparezca como una lista aislada producida por un catálogo externo. La recomendación debe conservar trazabilidad: qué quería hacer el usuario, qué hardware fue detectado, qué evidencia externa se consultó y qué frontera separa estimación de medición.

El puente implementado establece esa frontera sin atribuir a LLMFit una capacidad que su CLI no ofrece.

```text
USER_INTENT[]
   │
   ├── obligatorio
   ├── selección múltiple
   └── no vacío
   │
   ▼
HARDWARE DETECTADO
   │
   ▼
HUGGING FACE + ARTIFICIAL ANALYSIS
   │
   ▼
feed LEONES ≤ 100 modelos
   │
   ├── metadatos HF
   ├── benchmarks/índices AA cuando disponibles
   └── prefiltro de memoria de pesos
   │
   ├──────────────────────────────┐
   ▼                              ▼
LLMFit/LLMFit CLI              feed de evidencia
--limit 100                    LEONES
   │                              │
   └──────── identidad ───────────┘
                  │
                  ▼
        INTERSECCIÓN VERIFICADA
                  │
                  ▼
        hasta 3 candidatos
                  │
                  ▼
             ESTIMATED
                  │
                  ▼
          elección humana
                  │
                  ▼
        runtime físico Ubuntu
                  │
                  ▼
          medición MEASURED
```

## 2. Por qué no se inyecta el feed en LLMFit

La versión instalada de LLMFit/LLMFit usada por RC4 no ofrece una opción soportada para pasar un catálogo externo como entrada de `recommend`. Por tanto, LEONES **no inventa un flag**, no altera el significado de `--limit` y no declara que LLMFit haya puntuado directamente los registros HF/AA.

La solución es deliberadamente conservadora:

1. LEONES construye su feed de evidencia.
2. El feed queda limitado a 100 modelos.
3. LLMFit ejecuta su propio catálogo con `--limit 100` y el `--use-case` compatible con la intención.
4. LEONES normaliza las identidades de ambos lados.
5. Solo la intersección puede llegar a la lista de candidatos.
6. La evidencia HF/AA se conserva como `evidence_provenance`; no se transforma en una supuesta puntuación interna de LLMFit.

Esta decisión evita una integración aparentemente elegante pero semánticamente falsa.

## 3. Identidad de modelo

La intersección utiliza una clave de comparación normalizada:

- Unicode NFKC.
- minúsculas.
- eliminación de prefijos de Hugging Face (`https://huggingface.co/`).
- eliminación de caracteres no alfanuméricos.

La normalización **solo sirve para comparar**. El `model_id` mostrado al usuario permanece intacto.

Se consideran las siguientes posibilidades en la salida LLMFit:

- `id`
- `name`
- `model`
- `model_id`

Y en el feed:

- `model_id` del registro de evidencia.
- `hf.model_id`.
- `hf.name`, si existe.

No se hace matching difuso adicional en la última frontera de selección: una recomendación debe poder vincularse a un registro de evidencia inequívoco.

## 4. Límite de 100

El contrato `EVIDENCE_INPUT_LIMIT = 100` se aplica a la entrada de selección. El envelope declara:

- `evidence_input_limit = 100`.
- `evidence.model_count`.
- `fitllm_input.max_models = 100` en el feed producido por el collector.
- LLMFit se consulta con `--limit 100`.

El límite es una frontera de control, no una promesa de que siempre existan 100 modelos coincidentes.

## 5. Resultado de selección

El resultado RC4 utiliza:

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

Cuando existen tres coincidencias válidas, se devuelven tres candidatos.

Cuando existen menos de tres, el estado es `insufficient`. No se añaden modelos del catálogo LLMFit que carezcan de respaldo en el feed.

## 6. Artificial Analysis: disponible frente a ausente

Artificial Analysis requiere credenciales para su API. El collector lee `ARTIFICIAL_ANALYSIS_API_KEY` y, cuando no está disponible, no fabrica métricas.

El resultado conserva el estado de la fuente mediante `sources.artificial_analysis` y `artificial_analysis_available`. Un valor ausente significa **dato no disponible**, nunca cero ni benchmark inventado.

Por tanto:

- HF disponible + AA disponible → feed con ambas fuentes cuando existe correspondencia.
- HF disponible + AA no disponible → feed degradado, con la ausencia explícita de AA.
- ninguna evidencia → `insufficient`.

El sistema no etiqueta datos externos como `MEASURED`.

## 7. Prefiltro de hardware

El collector conserva un prefiltro de memoria de pesos con margen 1,20×. Es únicamente un filtro previo.

No representa:

- memoria KV real,
- buffers del runtime,
- overhead del backend,
- offload,
- contexto efectivo durante ejecución,
- rendimiento físico.

RAM y VRAM permanecen separadas. Swap no se convierte en RAM física.

## 8. Intención del usuario

La intención pública de RC4 permanece completa:

```json
"user_intent": {
  "required": true,
  "selection_mode": "multiple",
  "purposes": ["programming", "reasoning"]
}
```

LLMFit solo acepta un `--use-case`. La traducción es una frontera técnica, no una sustitución de la intención:

| RC4 | LLMFit |
|---|---|
| programming | coding |
| reasoning | reasoning |
| research | general |
| chat | chat |
| multimodal | multimodal |
| embedding | embedding |
| general | general |

La primera coincidencia de la tabla se utiliza para la consulta LLMFit, mientras que el array RC4 original permanece en el envelope.

## 9. Seguridad semántica de estados

RC4 distingue cuatro estados relevantes:

| Estado | Significado |
|---|---|
| `DECLARED` | intención, hardware u otra declaración inicial |
| `ESTIMATED` | estimación de catálogo/evidencia externa/LLMFit |
| `OBSERVED` | observación local todavía no equivalente a benchmark final |
| `MEASURED` | resultado de una ejecución física protocolizada |

El puente HF/AA → LLMFit solo puede producir `ESTIMATED`.

La medición LEONES comienza después de la elección humana, resolución del artefacto y ejecución física.

## 10. Qué queda fuera

No forman parte del camino canónico de RC4:

- Hermes como orquestador de recomendación.
- OMH como autoridad de selección.
- benchmarks físicos anticipados.
- autorización automática de ejecución.
- conversión de estimaciones en mediciones.
- flags no soportados por la versión instalada de LLMFit.

Las referencias históricas de RC3 se conservan donde corresponda para trazabilidad y no se borran globalmente.

## 11. Pruebas contractuales

`tests/test_rc4_fitllm_recommend.py` cubre específicamente:

1. límite máximo de 100 registros;
2. traducción de propósito a `coding`;
3. salida de exactamente tres candidatos cuando la intersección lo permite;
4. exclusión de candidatos LLMFit sin respaldo en el feed;
5. estado `insufficient` sin padding cuando faltan coincidencias;
6. permanencia de `ESTIMATED`;
7. `execution_authorized == false`;
8. `measured == false`;
9. rechazo de intención vacía.

Las pruebas usan dobles/mocks y no dependen de red ni de una clave de Artificial Analysis.

## 12. Criterio de aceptación de RC4

Esta capa se considera correctamente integrada cuando una ejecución real pueda demostrar, en este orden:

- el usuario selecciona uno o varios propósitos;
- se obtiene hardware sin inventar capacidades desconocidas;
- se prepara un feed de hasta 100 registros HF/AA;
- LLMFit recibe únicamente opciones de su CLI real;
- la selección se restringe a la intersección con evidencia;
- aparecen hasta tres propuestas `ESTIMATED`;
- el usuario decide;
- la resolución/instalación queda separada del presupuesto de RAM física;
- Ubuntu ejecuta el runtime elegido;
- el benchmark produce evidencia `MEASURED`.

**RC4 no debe declararse cerrada antes de validar físicamente esta cadena completa.**
