# LEONES — Índice documental canónico

Esta carpeta contiene la documentación técnica, arquitectónica, operativa, de decisiones y de diseño web de LEONES. Este README es el **mapa documental canónico**.

## 🧭 Nueva orientación después de JALÓN 3

**LEONES deja de orientarse a reimplementar capacidades que ya existen.** A partir de RC1 es la capa mínima de **decisión, integración, evidencia, comparación y recomendación** que coordina herramientas especializadas.

- [`LEONES-POST-JALON3-ARCHITECTURE.md`](LEONES-POST-JALON3-ARCHITECTURE.md) — **arquitectura normativa nueva**.
- [`RC1-MINIMAL-EXECUTION-PLAN.md`](RC1-MINIMAL-EXECUTION-PLAN.md) — **plan activo de ejecución hasta MANADA**.
- [`DEPRECATION-MAP.md`](DEPRECATION-MAP.md) — qué se archiva, qué se conserva y cómo se evita duplicar producto.
- [`completed/JALON-3-MEASUREMENT-PROTOCOL.md`](completed/JALON-3-MEASUREMENT-PROTOCOL.md) — contrato de medición física cerrado.

La cadena canónica RC1 es:

```text
hardware
  ↓
Magnitude / perfil hardware
  ↓
LEONES
  ↓
LLMFit + Atlas
  ↓
selección
  ↓
runtime autorizado
  ↓
llama.cpp u ODS
  ↓
Hermes
  ↓
A01
  ↓
benchmark + medición
  ↓
evidence
  ↓
validation
  ↓
recommendation
  ↓
MANADA
```

### Regla fundamental

> **Si una herramienta externa ya resuelve bien una capacidad, LEONES la integra; no la reconstruye.**

LEONES aporta lo que falta entre ellas: contratos, gates, procedencia, clasificación de evidencia, comparación y decisión.

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

## Integraciones externas prioritarias de RC1

- [`sources/MAGNITUDE.md`](sources/MAGNITUDE.md) / [`integrations/Magnitude/README.md`](integrations/Magnitude/README.md) — Magnitude para caracterización/medición de hardware y capacidades relacionadas.
- [`sources/LLMFIT.md`](sources/LLMFIT.md) / [`integrations/LLMFIT/README.md`](integrations/LLMFIT/README.md) — LLMFit como preselector hardware-aware.
- [`sources/ODS.md`](sources/ODS.md) / [`integrations/ODS/README.md`](integrations/ODS/README.md) — ODS como stack/appliance local.
- [`EVALUACION_AGENTIC_TESTS.md`](EVALUACION_AGENTIC_TESTS.md) / [`AGENT_HARNESSES.md`](AGENT_HARNESSES.md) — evaluación y harnesses, con Hermes como referencia RC1.

## Índice principal

### Arquitectura y fundamentos

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — arquitectura histórica/global.
- [`LEONES-POST-JALON3-ARCHITECTURE.md`](LEONES-POST-JALON3-ARCHITECTURE.md) — **autoridad arquitectónica post-JALÓN 3 para RC1**.
- [`PILLARS.md`](PILLARS.md) — pilares del sistema.
- [`PLATFORMS.md`](PLATFORMS.md) — plataformas y perfiles.
- [`FROZEN_DECISIONS.md`](FROZEN_DECISIONS.md) — decisiones congeladas.
- [`ROADMAP.md`](ROADMAP.md) — evolución prevista.
- [`DOCUMENTATION_PROTOCOL.md`](DOCUMENTATION_PROTOCOL.md) — protocolo obligatorio de cierre y navegación documental.
- [`DEPRECATION-MAP.md`](DEPRECATION-MAP.md) — política de deprecación pre-RC1.

### RC1

- [`RC1-MINIMAL-EXECUTION-PLAN.md`](RC1-MINIMAL-EXECUTION-PLAN.md) — **plan activo: núcleo mínimo → adapters → Ubuntu → benchmark → MANADA**.
- [`RELEASE-CANDIDATE-1.md`](RELEASE-CANDIDATE-1.md) — plan histórico/maestro anterior.
- [`RELEASE-CANDIDATE-1-HERMES.md`](RELEASE-CANDIDATE-1-HERMES.md) — integración Hermes.
- [`RELEASE-CANDIDATE-1-ENDGAME.md`](RELEASE-CANDIDATE-1-ENDGAME.md) — plan anterior; sus decisiones deben interpretarse conforme a la nueva arquitectura post-JALÓN 3.

### Fuentes de conocimiento

- [`sources/README.md`](sources/README.md) — registro y fichas de fuentes externas integradas.
- [`sources/LLMFIT.md`](sources/LLMFIT.md) — LLMFit.
- [`sources/ODS.md`](sources/ODS.md) — ODS.
- [`sources/MAGNITUDE.md`](sources/MAGNITUDE.md) — Magnitude.
- [`sources/ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md`](sources/ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md) — benchmarks y evaluación agentiva.

Las capas de conocimiento permanecen separadas: **fuente → evidencia → estimación → medición LEONES**.

### Atlas y recomendación

- [`../atlas/README.md`](../atlas/README.md) — Atlas como capa canónica de conocimiento.
- [`RESULT_SCHEMA.md`](RESULT_SCHEMA.md) — contrato de resultados.
- [`phases/2026-08-atlas-expanded/`](phases/2026-08-atlas-expanded/) — Atlas ampliado.
- [`phases/2026-08-atlas-recommendation-pipeline/`](phases/2026-08-atlas-recommendation-pipeline/) — Atlas → recomendador.
- [`completed/H10-ATLAS-RECOMMENDER-PIPELINE.md`](completed/H10-ATLAS-RECOMMENDER-PIPELINE.md) — guía de mantenimiento del pipeline cerrado.

### Hardware, fit, precios y economía

- [`phases/2026-08-hardware-matrix/`](phases/2026-08-hardware-matrix/) — matriz hardware.
- [`completed/H08-HARDWARE-MATRIX.md`](completed/H08-HARDWARE-MATRIX.md) — guía de mantenimiento.
- [`integrations/LLMFIT/README.md`](integrations/LLMFIT/README.md) — LLMFit.
- [`integrations/Magnitude/README.md`](integrations/Magnitude/README.md) — Magnitude.
- [`phases/2026-08-hardware-pricing/`](phases/2026-08-hardware-pricing/) — precios de hardware.
- [`atlas-hardware-price-integration.md`](atlas-hardware-price-integration.md) — conexión de precios.
- [`phases/2026-08-economic-ranking-v1/`](phases/2026-08-economic-ranking-v1/) — ranking económico.

### Prospección y apertura

- [`PROSPECTION.md`](PROSPECTION.md) — prospección.
- [`DISCOVERY_POLICY.md`](DISCOVERY_POLICY.md) — política de descubrimiento.
- [`FROZEN_PROSPECTION.md`](FROZEN_PROSPECTION.md) — reglas congeladas.
- [`SOURCE-DISCOVERY.md`](SOURCE-DISCOVERY.md) — descubrimiento de fuentes.
- [`phases/2026-08-daily-prospection/`](phases/2026-08-daily-prospection/) — prospección diaria.
- [`phases/2026-08-jgb-systematic/`](phases/2026-08-jgb-systematic/) — JGB.

### Evaluación, benchmarks y evidencia física

- [`EVALUACION_AGENTIC_TESTS.md`](EVALUACION_AGENTIC_TESTS.md) — evaluación agentiva.
- [`AGENT_HARNESSES.md`](AGENT_HARNESSES.md) — harnesses.
- [`AGENTIC-INVENTORY-2026.md`](AGENTIC-INVENTORY-2026.md) — inventario agentivo.
- [`RESULT_SCHEMA.md`](RESULT_SCHEMA.md) — resultado canónico.
- [`completed/BENCHMARK-MEASURED-EVIDENCE.md`](completed/BENCHMARK-MEASURED-EVIDENCE.md) — evidencia de benchmarks.
- [`completed/PHYSICAL-BENCHMARK-VALIDATION.md`](completed/PHYSICAL-BENCHMARK-VALIDATION.md) — validación física.
- [`completed/JALON-3-MEASUREMENT-PROTOCOL.md`](completed/JALON-3-MEASUREMENT-PROTOCOL.md) — **JALÓN 3 🟢 cerrado**.

### Integraciones

- [`integrations/README.md`](integrations/README.md) — índice de integraciones.
- [`integrations/LLMFIT/README.md`](integrations/LLMFIT/README.md) — LLMFit.
- [`integrations/ODS/README.md`](integrations/ODS/README.md) — ODS.
- [`integrations/Magnitude/README.md`](integrations/Magnitude/README.md) — Magnitude.
- [`integrations/DATA-CONTRACT.md`](integrations/DATA-CONTRACT.md) — contrato de datos.
- [`integrations/E2E.md`](integrations/E2E.md) — validación E2E.
- [`integrations/IN-DEVICE-INSTALLATION-MATRIX.md`](integrations/IN-DEVICE-INSTALLATION-MATRIX.md) — matriz de instalación.

### CI/CD, automatización y operación

- [`CI-CD-AUTOMATIZACION.md`](CI-CD-AUTOMATIZACION.md) — automatización.
- [`CI-WORKFLOW-RULES.md`](CI-WORKFLOW-RULES.md) — reglas de workflows.
- [`ACTUALIZACION-CONTINUA.md`](ACTUALIZACION-CONTINUA.md) — actualización continua.
- [`ARTIFACT_ACQUISITION.md`](ARTIFACT_ACQUISITION.md) — adquisición de artefactos.

### Diseño y desarrollo web

- [`../web/README.md`](../web/README.md) — referencia de la web.
- [`WEB_DESIGN_SYSTEM.md`](WEB_DESIGN_SYSTEM.md) — sistema de diseño.
- [`UX_OPTIMIZATION.md`](UX_OPTIMIZATION.md) — UX.

### Fases aceptadas y en curso

- [`phases/README.md`](phases/README.md) — índice de fases e hitos.
- [`completed/README.md`](completed/README.md) — documentación de componentes terminados.

## Mapa post-JALÓN 3

```text
PROSPECCIÓN / FUENTES
        ↓
ATLAS / IDENTIDAD / EVIDENCIA
        ↓
MAGNITUDE → HARDWARE
        ↓
LLMFIT → FIT INICIAL
        ↓
LEONES → DECISIÓN / GATES
        ↓
LLAMA.CPP / ODS
        ↓
HERMES → TAREA AGENTIVA
        ↓
BENCHMARK → MEDICIÓN
        ↓
EVIDENCE → VALIDATION
        ↓
RECOMMENDATION
        ↓
MANADA
```

## Regla de estado

Una página puede describir trabajo en curso, pero **solo una fase con validación y aceptación explícita puede aparecer como ACEPTADA**. La documentación debe distinguir siempre entre implementación, fuente, evidencia, estimación, medición y plan futuro.
