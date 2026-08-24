# Auditoría ficha por ficha — contrato de cuatro capas

**Fecha:** 2026-08-24  
**Contrato:** `KNOWLEDGE-FICHA-CONTRACT.v1`  
**Objetivo:** revisar las fuentes existentes de `docs/sources/`, identificar su papel real y asegurar que Fuente, Evidencia, Estimación y Medición LEONES no se confundan.

## Regla de auditoría

Cada ficha debe poder responder independientemente:

1. **Fuente / Descubrimiento:** qué existe y de dónde procede.
2. **Evidencia:** qué está respaldado y bajo qué condiciones.
3. **Estimación:** qué predice/recomienda una herramienta externa.
4. **Medición LEONES:** qué ha ejecutado y observado el pipeline propio.

`estado`, `clasificación`, `prioridad` y `próximo gate` son metadatos; no sustituyen ninguna de las cuatro capas.

## Resultado ficha por ficha

| Ficha | Capa arquitectónica real | Fuente | Evidencia | Estimación | Medición LEONES | Acción |
|---|---|---|---|---|---|---|
| FREETOKEN.md | selección/runtime | primaria | documental/código + resultados publicados | separada por claim | pendiente | runtime candidato de primera clase para MoE edge |
| FREETOKEN-EL-OTRO-FREETOKEN.md | runtime/serving MoE | primaria | código/docs + claims publicados | memoria/throughput/encaje separados | pendiente de reproducción | conservar ficha independiente |
| ODYSSEUS.md | workspace/harness | primaria | primaria + verificación documental | Cookbook como señal externa | pendiente | workload superior |
| LLMFIT.md | preselector | primaria | código/docs + bench externo | **central** | externa/comunitaria ≠ LEONES | estimador, no juez |
| LLMFIT-REAL-HARDWARE-2026-08-20.md | verificación técnica | primaria + observación | ejecución real de LLMFit | estimaciones de LLMFit | aún no benchmark de inferencia | calibración futura |
| AIRLLM.md | runtime memory-constrained | primaria | código/docs | hipótesis de capacidad/rendimiento | pendiente | benchmark Debian |
| ODS.md | despliegue/appliance | primaria | código/docs/installer | selección de stack externa | pendiente | capa de despliegue |
| MAGNITUDE.md | agente + runtime | primaria | código/docs | perfilado/recomendación | pendiente | benchmark agentivo |
| LOCAL-RUNTIMES-2026.md | radar/runtime | fuentes primarias por proyecto | consolidada por entrada | posibles estimaciones externas | por runtime | radar, nunca ranking |
| LOCAL-INFERENCE-2026.md | prospección | fuente de descubrimiento | verificaciones derivadas | separada | pendiente | radar estratégico |
| LOCAL-INFERENCE-2026-CANDIDATES.md | candidatos | derivada | estado por candidato | no equivale a medición | pendiente | promoción por gates |
| LOCAL-INFERENCE-2026-VERIFICATION.md | verificación | primaria/externa según entidad | foco principal | separada | pendiente salvo benchmark explícito | conservar condiciones |
| ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md | metodología benchmark | fuente metodológica | principios/resultados publicados | no es estimador principal | pendiente | diseño Agentic Benchmark V1 |
| BUDDY_HARNESS.md | harness | primaria | código/docs | hipótesis de workload | pendiente | comparar workloads |
| MOZILLA_OPEN_SOURCE_AI_ECOSYSTEM.md | ecosistema/metodología | publicación primaria | claims de la fuente | derivaciones conceptuales | no aplica directamente | fuente contextual |
| LLMS-DE-CERO-A-HEROE-2026.md | fundamentos | fuente compilada | contenido documental | hipótesis conceptuales | no aplica directamente | marco técnico |
| KNOWLEDGE-FICHA-CONTRACT.md | contrato LEONES | interna | contrato | n/a | n/a | autoridad editorial |
| KNOWLEDGE-REGISTRY.md | registro LEONES | interna | semántica de registro | n/a | n/a | índice documental |
| KNOWLEDGE-FOUR-LAYER-CARDS.md | normalización aplicada | interna derivada | síntesis por ficha | separada | n/a | referencia de lectura |

## Correcciones conceptuales cerradas

### FreeToken / «El otro FreeToken»

No se fusiona con Odysseus. FreeToken ocupa runtime/serving; Odysseus ocupa workspace/harness. La combinación solo aparece como hipótesis de integración y debe medirse.

### LLMFit

La existencia de benchmarks comunitarios dentro de LLMFit no cambia la semántica LEONES: son evidencia externa. La estimación de `estimated_tps` permanece separada de `measured_tps` propio. La captura de hardware real queda como observación de verificación hasta ejecutar un runtime.

### AirLLM

«Puede ejecutar un modelo» no equivale a «ofrece rendimiento útil». Capacidad, compatibilidad, estabilidad, I/O y latencia quedan separadas.

### ODS

ODS despliega y puede seleccionar automáticamente modelos/backend. LEONES conserva la autoridad sobre selección, benchmark y recomendación final.

### Magnitude

Magnitude combina agente y motor de inferencia. Sus señales de perfilado son estimaciones y sus workloads agentivos son potencialmente útiles como harness; ninguno sustituye al benchmark canónico.

### Runtimes

El radar de runtimes no es una tabla de ganadores. Cada runtime se evalúa como combinación **modelo × formato/cuanti × runtime × hardware × workload × harness**.

### Benchmarks

Un resultado publicado por un proyecto, leaderboard o tercero nunca entra automáticamente en `Medición LEONES`. Para ello debe existir ejecución reproducible del pipeline con executor, grader, benchmark y evidence.

## Estado de la web

`web/data/knowledge.json` es el registro único de consumo y ahora contiene todas las fichas documentales activas relevantes. `web/conocimiento.html` renderiza exactamente cuatro columnas contractuales y no reconstruye fichas manualmente.

Las cuatro columnas son exclusivamente:

1. **Fuente / Descubrimiento**
2. **Evidencia**
3. **Estimación**
4. **Medición LEONES**

Estado, clasificación y enlaces son metadatos de navegación y no forman una quinta capa semántica.

## Automatización cerrada

Se añadió `tests/contracts/test_knowledge_four_layers.py`, que comprueba:

- contrato `KNOWLEDGE-FICHA-CONTRACT.v1`;
- exactamente cuatro capas;
- presencia de las cuatro capas en cada registro web;
- estructura homogénea de cada capa;
- presencia de las fuentes estratégicas;
- prohibición de etiquetar evidencia externa como medición LEONES.

El workflow `.github/workflows/contract-tests.yml` ejecuta este test y se activa también cuando cambian `docs/sources/**`, `web/data/knowledge.json` o `web/conocimiento.html`.

## Gates ejecutables que quedan

La parte documental y de contrato queda cerrada. Lo que **no puede darse por hecho sin hardware/ejecución** permanece deliberadamente pendiente:

1. `runtime-selection.v1 → executor → grader → benchmark → evidence` para FreeToken.
2. La misma cadena para AirLLM.
3. Workloads superiores reproducibles con Odysseus/Buddy/Magnitude.
4. Correlación LLMFit/Magnitude/ODS frente a mediciones reales.
5. Promoción de cualquier resultado a `measured` únicamente tras ejecución reproducible.

Estos gates no se rellenan con cifras externas ni con estimaciones.
