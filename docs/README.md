# LEONES — Índice documental canónico

Esta carpeta contiene la documentación técnica, arquitectónica, operativa, de decisiones y de diseño web de LEONES. Este README es el **mapa documental canónico**: cada subsistema importante debe poder localizarse desde aquí y, a su vez, su README debe enlazar con sus fases, contratos, validación y piezas de implementación relevantes.

## Regla de documentación por fases

Toda fase que se declare **completada y aceptada** debe dejar un paquete documental profundo y enlazado. El protocolo está en [`DOCUMENTATION_PROTOCOL.md`](DOCUMENTATION_PROTOCOL.md).

```text
fase → implementación → validación → aceptación
                         ↓
                 documentación
                         ↓
                 enlaces / índice
                         ↓
                    cierre
```

## Índice principal

### Arquitectura y fundamentos

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — arquitectura global, pipeline y vocabulario.
- [`PILLARS.md`](PILLARS.md) — pilares del sistema.
- [`PLATFORMS.md`](PLATFORMS.md) — plataformas y perfiles.
- [`FROZEN_DECISIONS.md`](FROZEN_DECISIONS.md) — decisiones congeladas.
- [`ROADMAP.md`](ROADMAP.md) — evolución prevista.
- [`DOCUMENTATION_PROTOCOL.md`](DOCUMENTATION_PROTOCOL.md) — protocolo obligatorio de cierre y navegación documental.

### Fuentes de conocimiento

- [`sources/README.md`](sources/README.md) — registro y fichas de fuentes externas integradas.
- [`sources/KNOWLEDGE-FICHA-CONTRACT.md`](sources/KNOWLEDGE-FICHA-CONTRACT.md) — contrato editorial de las fichas.
- [`sources/KNOWLEDGE-REGISTRY.md`](sources/KNOWLEDGE-REGISTRY.md) — inventario semántico y estado de homogeneización.
- [`sources/FREETOKEN.md`](sources/FREETOKEN.md) — FreeToken.
- [`sources/FREETOKEN-EL-OTRO-FREETOKEN.md`](sources/FREETOKEN-EL-OTRO-FREETOKEN.md) — «El otro FreeToken» / Odysseus.
- [`sources/LLMFIT.md`](sources/LLMFIT.md) — LLMFit como preselector hardware-aware.
- [`sources/LLMFIT-REAL-HARDWARE-2026-08-20.md`](sources/LLMFIT-REAL-HARDWARE-2026-08-20.md) — verificación técnica de LLMFit con hardware real.
- [`sources/AIRLLM.md`](sources/AIRLLM.md) — AirLLM como runtime candidato memory-constrained.
- [`sources/ODS.md`](sources/ODS.md) — ODS como capa de despliegue.
- [`sources/MAGNITUDE.md`](sources/MAGNITUDE.md) — Magnitude como agente e inference engine local.
- [`sources/LOCAL-RUNTIMES-2026.md`](sources/LOCAL-RUNTIMES-2026.md) — radar de runtimes locales.
- [`sources/LOCAL-INFERENCE-2026.md`](sources/LOCAL-INFERENCE-2026.md) — infraestructura de inferencia.
- [`sources/LOCAL-INFERENCE-2026-CANDIDATES.md`](sources/LOCAL-INFERENCE-2026-CANDIDATES.md) — candidatos de infraestructura.
- [`sources/LOCAL-INFERENCE-2026-VERIFICATION.md`](sources/LOCAL-INFERENCE-2026-VERIFICATION.md) — verificación primaria de infraestructura.
- [`sources/ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md`](sources/ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md) — benchmarks y evaluación agentiva.
- [`sources/BUDDY_HARNESS.md`](sources/BUDDY_HARNESS.md) — referencia de harness/evaluación.
- [`sources/MOZILLA_OPEN_SOURCE_AI_ECOSYSTEM.md`](sources/MOZILLA_OPEN_SOURCE_AI_ECOSYSTEM.md) — ecosistema Open Source AI identificado por Mozilla.

Las cuatro capas de conocimiento permanecen separadas: **fuente → evidencia → estimación → medición LEONES**. Una ficha puede enlazar las cuatro, pero nunca presentarlas como equivalentes.

### Atlas y recomendación

- [`../atlas/README.md`](../atlas/README.md) — Atlas como capa canónica de conocimiento.
- [`RESULT_SCHEMA.md`](RESULT_SCHEMA.md) — contrato de resultados.
- [`phases/2026-08-atlas-expanded/`](phases/2026-08-atlas-expanded/) — H06: Atlas ampliado.
- [`phases/2026-08-atlas-recommendation-pipeline/`](phases/2026-08-atlas-recommendation-pipeline/) — H10: Atlas → recomendador.
- [`completed/H10-ATLAS-RECOMMENDER-PIPELINE.md`](completed/H10-ATLAS-RECOMMENDER-PIPELINE.md) — guía de mantenimiento del pipeline cerrado.

### Hardware, fit, precios y economía

- [`phases/2026-08-hardware-matrix/`](phases/2026-08-hardware-matrix/) — matriz hardware.
- [`completed/H08-HARDWARE-MATRIX.md`](completed/H08-HARDWARE-MATRIX.md) — guía de mantenimiento de la matriz.
- [`integrations/LLMFIT/README.md`](integrations/LLMFIT/README.md) — integración documental de LLMFit.
- [`phases/2026-08-hardware-pricing/`](phases/2026-08-hardware-pricing/) — precios de hardware.
- [`atlas-hardware-price-integration.md`](atlas-hardware-price-integration.md) — conexión de precios con hardware/Atlas.
- [`phases/2026-08-economic-ranking-v1/`](phases/2026-08-economic-ranking-v1/) — ranking económico.

### Prospección y apertura

- [`PROSPECTION.md`](PROSPECTION.md) — prospección.
- [`DISCOVERY_POLICY.md`](DISCOVERY_POLICY.md) — política de descubrimiento.
- [`FROZEN_PROSPECTION.md`](FROZEN_PROSPECTION.md) — reglas congeladas de prospección.
- [`SOURCE-DISCOVERY.md`](SOURCE-DISCOVERY.md) — descubrimiento de fuentes.
- [`phases/2026-08-daily-prospection/`](phases/2026-08-daily-prospection/) — H04.
- [`phases/2026-08-jgb-systematic/`](phases/2026-08-jgb-systematic/) — H07 / JGB.
- [`../web/proyectos/atlas/openness/JGB-INDEX.md`](../web/proyectos/atlas/openness/JGB-INDEX.md) — índice JGB publicado en la web.

### Evaluación, benchmarks y evidencia física

- [`EVALUACION_AGENTIC_TESTS.md`](EVALUACION_AGENTIC_TESTS.md) — evaluación agentiva.
- [`AGENT_HARNESSES.md`](AGENT_HARNESSES.md) — harnesses.
- [`AGENTIC-INVENTORY-2026.md`](AGENTIC-INVENTORY-2026.md) — inventario agentivo.
- [`RESULT_SCHEMA.md`](RESULT_SCHEMA.md) — resultado canónico.
- [`completed/BENCHMARK-MEASURED-EVIDENCE.md`](completed/BENCHMARK-MEASURED-EVIDENCE.md) — evidencia de benchmarks medidos.
- [`completed/PHYSICAL-BENCHMARK-VALIDATION.md`](completed/PHYSICAL-BENCHMARK-VALIDATION.md) — validación física.
- [`completed/JALON-3-MEASUREMENT-PROTOCOL.md`](completed/JALON-3-MEASUREMENT-PROTOCOL.md) — **JALÓN 3 🟢: contrato operativo de medición real, hardware, ejecución, evidencia y validación.**
- [`completed/H09-CABE-RULA.md`](completed/H09-CABE-RULA.md) — CABE/RULA.

### Integraciones

- [`integrations/README.md`](integrations/README.md) — índice de integraciones.
- [`integrations/LLMFIT/README.md`](integrations/LLMFIT/README.md) — LLMFit.
- [`integrations/ODS/README.md`](integrations/ODS/README.md) — ODS.
- [`integrations/Magnitude/README.md`](integrations/Magnitude/README.md) — Magnitude.
- [`integrations/DATA-CONTRACT.md`](integrations/DATA-CONTRACT.md) — contrato de datos.
- [`integrations/E2E.md`](integrations/E2E.md) — validación E2E.
- [`integrations/IN-DEVICE-INSTALLATION-MATRIX.md`](integrations/IN-DEVICE-INSTALLATION-MATRIX.md) — matriz de instalación por dispositivo.

### CI/CD, automatización y operación

- [`CI-CD-AUTOMATIZACION.md`](CI-CD-AUTOMATIZACION.md) — automatización.
- [`CI-WORKFLOW-RULES.md`](CI-WORKFLOW-RULES.md) — reglas de workflows.
- [`ACTUALIZACION-CONTINUA.md`](ACTUALIZACION-CONTINUA.md) — actualización continua.
- [`ALERTAS-NOTIFICACIONES.md`](ALERTAS-NOTIFICACIONES.md) — alertas y notificaciones.
- [`ARTIFACT_ACQUISITION.md`](ARTIFACT_ACQUISITION.md) — adquisición de artefactos.

### Diseño y desarrollo web

- [`../web/README.md`](../web/README.md) — referencia obligatoria de la web.
- [`WEB_DESIGN_SYSTEM.md`](WEB_DESIGN_SYSTEM.md) — marco obligatorio de diseño y desarrollo.
- [`UX_OPTIMIZATION.md`](UX_OPTIMIZATION.md) — optimización de UX.

### Fases aceptadas y en curso

- [`phases/README.md`](phases/README.md) — índice de fases e hitos.
- [`completed/README.md`](completed/README.md) — guías pedagógicas de mantenimiento de componentes terminados.

## Mapa de relación entre piezas

```text
PROSPECCIÓN
    ↓
ATLAS / IDENTIDAD / EVIDENCIA
    ↓
JGB + LICENCIAS + HARDWARE
    ↓
LLMFIT → FIT INICIAL
    ↓
MODELO + CUANTIZACIÓN + RUNTIME
    ↓
BENCHMARK LEONES → MEDICIÓN
    ↓
CABE / RULA
    ↓
RECOMENDADOR / ROUTER
    ↓
AGENTES / HARNESS
    ↓
WEB / MANADA
```

ODS y Magnitude se mantienen como integraciones externas medibles; FreeToken, Odysseus, AirLLM, LLMFit y los runtimes documentados en `sources/` son fuentes de conocimiento/referencia que pueden alimentar hipótesis y adaptadores, pero nunca convierten por sí mismos sus claims en mediciones LEONES.

## Regla de estado

Una página puede describir trabajo en curso, pero **solo una fase con validación y aceptación explícita puede aparecer como ACEPTADA**. La documentación debe distinguir siempre entre implementación, fuente, evidencia, estimación, medición y plan futuro.
