# JALÓN 4 — Contrato de decisión LEONES → ODS | Magnitude

**Estado:** cerrado para ejecución física; no requiere Ubuntu hasta la orden explícita `AHORA NECESITO UBUNTU`.

## 1. Propósito

LEONES debe decidir **qué medir**, no inventar un segundo sistema de selección de hardware/modelos.

La cadena canónica queda:

```text
usuario
  ↓
selección explícita (si existe)
  ↓
LEONES decision contract
  ├── LLMFit → fit / quant / run mode / speed estimate / runtime provider
  ├── ODS    → stack de servidor y hardware tier nativo cuando el perfil sea ODS
  └── Magnitude → perfil/recomendación de asistente y ejecución agentic local
  ↓
preflight
  ↓
runtime real
  ↓
benchmark de rendimiento
  ↓
benchmark de tareas completadas
  ↓
evidence
  ↓
recomendación LEONES
```

LEONES **no sustituye** a LLMFit, ODS ni Magnitude:

- LLMFit es la autoridad para el *fit* local de modelos sobre RAM/CPU/GPU/VRAM, cuantización, modo de ejecución y estimación de velocidad.
- ODS es la autoridad para su propio `hardware tier`, catálogo y selección de stack/modelo de servidor.
- Magnitude es la autoridad para su perfilado/recomendación de modelos y configuración de su agente local.
- LEONES es la capa de **consentimiento, decisión, orquestación, validación, medición, evidencia y comparación**.

## 2. Regla de precedencia

1. **Elección explícita del usuario** gana sobre cualquier recomendación automática.
2. Si el usuario fija modelo + revisión + cuantización + runtime, LEONES debe validar si esa configuración es ejecutable; no reemplazarla silenciosamente.
3. Si el usuario fija hardware pero no modelo, LEONES consulta la fuente apropiada:
   - LLMFit para selección general de modelo/runtimes locales.
   - ODS para perfil de servidor ODS.
   - Magnitude para perfil de agente Magnitude.
4. Una recomendación de LLMFit/ODS/Magnitude es `recommended` o `estimated`; nunca se convierte automáticamente en `measured`.
5. Un benchmark físico LEONES es la única fuente de verdad para rendimiento local observado.

## 3. Entrada canónica

El objeto de decisión debe contener, como mínimo:

- `decision_id`
- `created_at`
- `user_intent`: `chat | coding | reasoning | agent | server | multimodal | custom`
- `selection_mode`: `explicit | assisted | automatic`
- `hardware_target` (si el usuario lo fija)
- `model_target` (si el usuario lo fija)
- `runtime_target` (si el usuario lo fija)
- `context_target`
- `concurrency_target`
- `benchmark_profile`
- `consent`

Los valores descubiertos por herramientas externas se conservan por procedencia, nunca se mezclan con los valores introducidos por el usuario.

## 4. Salida de decisión

```json
{
  "schema": "leones-ods-magnitude-decision.v1",
  "decision_id": "...",
  "selection": {
    "authority": "user|llmfit|ods|magnitude",
    "model": "...",
    "revision": "...",
    "quantization": "...",
    "runtime": "...",
    "run_mode": "GPU|CPU+GPU|CPU|MoE",
    "context": 8192
  },
  "sources": {
    "llmfit": {"status": "observed|queried|unavailable"},
    "ods": {"status": "observed|queried|unavailable"},
    "magnitude": {"status": "observed|queried|unavailable"}
  },
  "decision": "proceed|validate|blocked|user_confirmation_required",
  "benchmark_profile": "performance|task_completion|combined"
}
```

Los nombres concretos de modelos, cuantizaciones y runtimes son datos, no categorías LEONES.

## 5. Integración con LLMFit

LEONES consume, cuando esté disponible, la salida JSON de LLMFit. No reproduce su algoritmo.

Campos relevantes:

- hardware detectado;
- `score` y `score_components`;
- `fit_level`: `Perfect | Good | Marginal | TooTight`;
- `run_mode`;
- `best_quant`;
- `estimated_tps`;
- `memory_required_gb`;
- `memory_available_gb`;
- `utilization_pct`;
- `use_case`;
- `context_length`.

El significado de `Perfect/Good/Marginal/TooTight` permanece el de LLMFit. LEONES no crea otra escala equivalente.

**Regla:** `estimated_tps` sirve para planificación/preflight; nunca para afirmar rendimiento medido.

## 6. Integración con ODS

ODS mantiene su clasificación de hardware y su selector de catálogo. LEONES no copia el mapa `tier → modelo`.

Para un perfil ODS se conserva:

- tier ODS detectado/seleccionado;
- plataforma/arquitectura;
- memoria relevante;
- modelo y GGUF realmente seleccionados por ODS;
- contexto seleccionado;
- `MODEL_RECOMMENDATION_*` si ODS lo expone;
- versión/ref de ODS.

Los campos `MODEL_RECOMMENDED_*` son recomendación/configuración, no medición. ODS ya documenta que el throughput requiere un benchmark local posterior al primer lanzamiento.

## 7. Integración con Magnitude

Magnitude mantiene su flujo de:

```text
hardware profiling
→ recommendation mode
(Balanced | Best Quality | Fastest | Lightweight)
→ model download/configuration
→ local agent execution
```

LEONES registra el modo solicitado por el usuario y la recomendación/configuración resultante. No reconstruye el algoritmo de recomendación de Magnitude.

Cuando Magnitude exponga datos de memoria, configuración o rendimiento nativos, se conservan como `observed`/`recommended` según procedencia. El benchmark profundo de LEONES sigue siendo independiente.

## 8. Tiers de hardware de consumo

LEONES **no crea tiers de hardware propietarios**.

Para interoperabilidad se usa una vista de dos capas:

### Capa A — clasificación nativa

- `ods.hardware_tier` cuando el flujo es ODS.
- `magnitude.hardware_profile` cuando el flujo es Magnitude.
- hardware real detectado por LLMFit cuando el flujo es LLMFit.

### Capa B — capacidad de ejecución LLMFit

`fit_level + run_mode + memory_required + memory_available + estimated_tps`.

Si se necesita presentar una tabla amigable al usuario, los nombres `Entry / Mid / High / Enthusiast / Multi-GPU` son **etiquetas de presentación**, nunca criterios de selección ni una segunda fórmula. La fila debe mostrar siempre la clasificación nativa que la sustenta.

### Referencia de consumo para presentación

| Vista humana | Base real | No significa |
|---|---|---|
| Entry | ODS tier bajo + LLMFit `Marginal/Good` según caso | un modelo fijo |
| Mainstream | ODS tier 1–2 / hardware equivalente + LLMFit fit | una puntuación LEONES |
| Enthusiast | ODS tier 3 / ~24 GB-class o equivalente | un límite universal |
| High-memory | ODS tier 4 / ~48 GB-class o memoria unificada equivalente | una promesa de tok/s |
| Multi-GPU / Ultra | ODS `NV_ULTRA` u otra clasificación nativa equivalente | escalado lineal |

Estas etiquetas no se persisten como autoridad de decisión. Solo se derivan al presentar resultados.

## 9. Benchmark profundo orientado a tareas completadas

Una vez fijados modelo/runtime/hardware, LEONES ejecuta dos capas separadas.

### A. Performance

Métricas mínimas:

- TTFT;
- time to first answer token cuando aplique;
- output tok/s;
- TPOT;
- end-to-end response time;
- p50/p95/p99 cuando haya suficientes muestras;
- memoria pico;
- contexto;
- concurrencia;
- versión exacta del runtime;
- comando;
- hardware;
- artefacto y SHA-256.

Para comparabilidad entre runtimes, cuando sea viable LEONES puede registrar tokens canónicos además de tokens nativos. La evidencia debe conservar ambos cuando existan.

### B. Task completion

El objetivo es medir **trabajo terminado**, no solo generación de tokens.

El perfil se estructura por familias:

1. conocimiento/respuesta;
2. razonamiento;
3. coding;
4. uso de terminal/herramientas;
5. agente de larga duración;
6. transformación/producción de artefactos;
7. multimodal si el hardware/runtime lo soporta.

Cada tarea debe tener:

- `task_id` y versión;
- prompt/fixture versionado fuera de la evidencia pública cuando sea necesario;
- recursos de entrada;
- herramientas permitidas;
- límite de turnos/tiempo;
- criterio objetivo de éxito;
- resultado `pass|fail|invalid|blocked`;
- evidencia del artefacto producido;
- tiempo total;
- tokens consumidos si están disponibles;
- errores y recuperaciones;
- `execution_id`.

## 10. Alineación con Artificial Analysis

LEONES adopta **principios metodológicos**, no afirma reproducir el benchmark privado de Artificial Analysis.

La referencia actual de Coding Agent Index usa tareas end-to-end y separa familias como ingeniería de software de larga duración, terminal y repository Q&A; publica `pass@1` y métricas de eficiencia de coste, tokens y tiempo. La Intelligence Index también da peso importante a tareas agentic.

Por tanto LEONES debe:

- medir resultado final de la tarea;
- usar verificación objetiva cuando sea posible;
- mantener `pass@1` como métrica primaria de una ejecución/configuración;
- repetir tareas en fases de desarrollo sin contaminar el conjunto final;
- separar suite de desarrollo y suite congelada de auditoría;
- registrar tiempo, tokens y errores junto al resultado;
- no optimizar prompts/scaffolds contra una prueba que luego se presente como limpia;
- informar de versión, cobertura, incertidumbre y limitaciones.

No se debe llamar `Artificial Analysis score` al índice local LEONES.

## 11. Profundidad adaptativa

La profundidad del benchmark depende de la selección del usuario y de la carga:

- `performance`: medición rápida y reproducible;
- `task_completion`: suite de tareas de la categoría solicitada;
- `combined`: ambas capas.

Si el usuario selecciona coding, se priorizan coding + terminal + repository tasks. Si selecciona agent, se priorizan tool use + long-horizon + artefactos. Si selecciona chat/general, se priorizan QA + reasoning + transformación. Multimodal añade tareas visuales solo si la ruta real las soporta.

No se ejecutan suites irrelevantes por defecto.

## 12. Estado y procedencia

Todo dato debe quedar clasificado como exactamente uno de:

- `user_selected`
- `observed`
- `recommended`
- `configured`
- `estimated`
- `measured`
- `derived`

Prohibido convertir silenciosamente `recommended` o `estimated` en `measured`.

## 13. Gate antes de Ubuntu

El contrato se considera preparado cuando existen:

- schema JSON del contrato;
- schema JSON del plan de benchmark;
- reglas de precedencia;
- integración explícita LLMFit/ODS/Magnitude;
- separación recommendation vs measurement;
- definición de task completion;
- evidencia y provenance;
- reglas de tiers sin sistema paralelo;
- criterios de bloqueo/confirmación;
- suite de ejecución preparada.

**Ninguna ejecución física es necesaria para cerrar este jalón.**

La ejecución física empieza únicamente cuando el usuario diga explícitamente:

> **AHORA NECESITO UBUNTU**
