# Auditoría ficha por ficha — contrato de cuatro capas

**Fecha:** 2026-08-24  
**Contrato:** `KNOWLEDGE-FICHA-CONTRACT.md`  
**Objetivo:** revisar las fuentes existentes de `docs/sources/`, identificar su papel real y asegurar que Fuente, Evidencia, Estimación y Medición LEONES no se confunden.

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
| FREETOKEN.md | selección/runtime | primaria | documental/código | separada por claim | pendiente | mantener independiente |
| FREETOKEN-EL-OTRO-FREETOKEN.md | runtime/serving MoE | primaria | código/docs + claims publicados | sí: memoria/throughput/encaje | pendiente de reproducción | prioridad alta |
| ODYSSEUS.md | workspace/harness | primaria | primaria + verificación documental | Cookbook como señal externa | pendiente | evaluar como workload superior |
| LLMFIT.md | preselector | primaria | código/docs | **central** | externa/comunitaria ≠ LEONES | integrar como estimador, no juez |
| LLMFIT-REAL-HARDWARE-2026-08-20.md | verificación técnica | primaria + observación | verificación | estimaciones conservadas | solo si existe ejecución registrada | mantener histórico |
| AIRLLM.md | runtime memory-constrained | primaria | código/docs | hipótesis de capacidad/rendimiento | pendiente | benchmark Debian |
| ODS.md | despliegue/appliance | primaria | código/docs/installer | selección de stack externa | pendiente | usar como capa de despliegue |
| MAGNITUDE.md | agente + runtime | primaria | código/docs | perfilado/recomendación | pendiente | benchmark agentivo |
| LOCAL-RUNTIMES-2026.md | radar/runtime | fuentes primarias por proyecto | consolidada por entrada | posibles estimaciones externas | por runtime | no convertir radar en ranking |
| LOCAL-INFERENCE-2026.md | prospección | fuente de descubrimiento | verificaciones derivadas | separada | pendiente | mantener como radar |
| LOCAL-INFERENCE-2026-CANDIDATES.md | candidatos | derivada | estado por candidato | no equivale a medición | pendiente | promoción por gates |
| LOCAL-INFERENCE-2026-VERIFICATION.md | verificación | primaria/externa | foco principal | separada | solo si benchmark explícito | conservar condiciones |
| ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md | metodología benchmark | primaria + externa | resultados/metodología publicados | no es estimador principal | pendiente de reproducción | usar para diseño |
| BUDDY_HARNESS.md | harness | primaria | código/docs | hipótesis de workload | pendiente | comparar workloads |
| MOZILLA_OPEN_SOURCE_AI_ECOSYSTEM.md | ecosistema/metodología | publicación primaria | claims de la fuente | derivaciones conceptuales | no aplica directamente | mantener como fuente |
| LLMMS-DE-CERO-A-HEROE-2026.md | fundamentos | fuente compilada | contenido documental | hipótesis conceptuales | no aplica directamente | usar como marco |
| KNOWLEDGE-FICHA-CONTRACT.md | contrato LEONES | interna | contrato | n/a | n/a | autoridad editorial |
| KNOWLEDGE-REGISTRY.md | registro LEONES | interna | semántica de registro | n/a | n/a | sincronizar con fichas |

## Correcciones conceptuales aplicadas

### FreeToken / «El otro FreeToken»

No se fusiona con Odysseus. FreeToken ocupa runtime/serving; Odysseus ocupa workspace/harness. La combinación solo aparece como hipótesis de integración y debe medirse.

### LLMFit

La existencia de benchmarks comunitarios dentro de llmfit no cambia la semántica LEONES: son evidencia externa. La estimación de `estimated_tps` permanece separada de `measured_tps` propio.

### AirLLM

«Puede ejecutar un modelo» no equivale a «ofrece rendimiento útil». Capacidad, compatibilidad, estabilidad, I/O y latencia deben quedar separadas.

### ODS

ODS despliega y puede seleccionar automáticamente modelos/backend. LEONES conserva la autoridad sobre selección, benchmark y recomendación final.

### Magnitude

Magnitude combina agente y motor de inferencia. Por ello sus señales de perfilado son estimaciones y sus workloads agentivos son potencialmente útiles como harness; ninguno sustituye al benchmark canónico.

### Runtimes

El radar de runtimes no es una tabla de ganadores. Cada runtime debe evaluarse como combinación **modelo × formato/cuanti × runtime × hardware × workload**.

### Benchmarks

Un resultado publicado por un proyecto, leaderboard o tercero nunca entra automáticamente en `Medición LEONES`. Para ello debe existir ejecución reproducible del pipeline con executor, grader, benchmark y evidence.

## Estado de la web

`web/data/knowledge.json` es ahora el registro de consumo. `web/conocimiento.html` renderiza únicamente las cuatro capas contractuales y mantiene los metadatos fuera de ellas.

La web no debe volver a incrustar fichas manualmente dentro del HTML. Las ampliaciones se hacen en la ficha documental y en el registro JSON; la presentación solo consume ambos.

## Próximos gates

1. Homogeneizar, si aún falta, las cuatro secciones en las fichas históricas restantes.
2. Conectar cada candidato runtime con `runtime-selection.v1`.
3. Conectar executor → grader → benchmark → evidence para FreeToken y AirLLM.
4. Ejecutar workload superior Odysseus/Buddy/Magnitude cuando el endpoint esté fijado.
5. Correlacionar estimaciones LLMFit/Magnitude/ODS con mediciones reales sin reescribir el histórico.
