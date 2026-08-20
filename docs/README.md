# LEONES — Documentación

Esta carpeta contiene la documentación técnica, arquitectónica, operativa, de decisiones y de diseño web de LEONES.

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

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`PILLARS.md`](PILLARS.md)
- [`PLATFORMS.md`](PLATFORMS.md)
- [`FROZEN_DECISIONS.md`](FROZEN_DECISIONS.md)
- [`ROADMAP.md`](ROADMAP.md)

### Fuentes de conocimiento

- [`sources/README.md`](sources/README.md) — registro de fuentes externas integradas.
- [`sources/MOZILLA_OPEN_SOURCE_AI_ECOSYSTEM.md`](sources/MOZILLA_OPEN_SOURCE_AI_ECOSYSTEM.md) — ecosistema de IA abierta identificado por Mozilla, convertido en fuente independiente para LEONES.
- [`sources/LLMFIT.md`](sources/LLMFIT.md) — LLMFit como preselector hardware-aware.
- [`sources/AIRLLM.md`](sources/AIRLLM.md) — AirLLM como runtime candidato para escenarios memory-constrained.

Regla: las fuentes externas conservan su procedencia y edición. Sus conclusiones no sustituyen las clasificaciones, contratos ni mediciones propias de LEONES.

### Diseño y desarrollo web

- [`WEB_DESIGN_SYSTEM.md`](WEB_DESIGN_SYSTEM.md) — **marco obligatorio de diseño y desarrollo de la web**.

> Antes de crear o modificar cualquier HTML, CSS, JavaScript, menú, componente visual o recurso de la web, este documento debe consultarse.

### Atlas y prospección

- [`../atlas/README.md`](../atlas/README.md)
- [`PROSPECTION.md`](PROSPECTION.md)
- [`DISCOVERY_POLICY.md`](DISCOVERY_POLICY.md)
- [`FROZEN_PROSPECTION.md`](FROZEN_PROSPECTION.md)

### Evaluación

- [`EVALUACION_AGENTIC_TESTS.md`](EVALUACION_AGENTIC_TESTS.md)
- [`RESULT_SCHEMA.md`](RESULT_SCHEMA.md)

### Fases aceptadas y en curso

- [`phases/README.md`](phases/README.md)
- [`completed/README.md`](completed/README.md) — **guías pedagógicas de mantenimiento de los componentes terminados**.

Estas guías complementan, no sustituyen, los paquetes normativos de cada fase.

## Regla de estado

Una página puede describir trabajo en curso, pero **solo una fase con validación y aceptación explícita puede aparecer como ACEPTADA**.

La documentación debe distinguir siempre entre implementación, evidencia y plan futuro.
