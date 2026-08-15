# LEONES — Índice de fases

Los paquetes de fase son la unidad documental de cierre de las grandes etapas del proyecto.

## Estados

- 🟡 **PROVISIONAL / EN VALIDACIÓN** — implementación existente, pero todavía no aceptada.
- 🟢 **ACEPTADA** — implementación validada, documentada y aceptada explícitamente.
- ⚪ **PLANIFICADA** — todavía no implementada.
- 🔵 **SUSTITUIDA** — reemplazada por una fase posterior, conservando trazabilidad.

## Regla de cierre

```text
IMPLEMENTAR
    ↓
VALIDAR
    ↓
ACEPTAR
    ↓
DOCUMENTAR PROFUSAMENTE
    ↓
ENLAZAR DESDE README
    ↓
CERRAR FASE
```

## Fases documentadas

### 🟢 2026-08 — Prospección diaria automatizada

[`2026-08-daily-prospection/`](2026-08-daily-prospection/)

Automatización diaria de descubrimiento, filtro OSI, prioridad Copyleft, enriquecimiento, informes e integración con Atlas/web.

### 🟢 2026-08 — Bot mensual de precios de hardware

[`2026-08-hardware-pricing/`](2026-08-hardware-pricing/)

Infraestructura operativa de observación mensual de precios, normalización, calidad, histórico, resumen y publicación. La cobertura de mercado y la inteligencia avanzada siguen en desarrollo.

### 🟢 2026-08 — Ranking económico V1

[`2026-08-economic-ranking-v1/`](2026-08-economic-ranking-v1/)

Primera versión validada del ranking que combina rendimiento, JGB, hardware fit y coste observado, con viabilidad antes de economía y cobertura explícita.

### 🟡 2026-08 — Atlas → recomendador diario enriquecido

[`2026-08-atlas-recommendation-pipeline/`](2026-08-atlas-recommendation-pipeline/)

Estado actual: **en validación**. El workflow diario ha sido conectado al enriquecedor de recomendaciones y existe una ejecución manual de GitHub Actions pendiente de completar. No se marca como aceptada hasta comprobar el run real.

## Auditoría del estado anterior

La revisión del repositorio ha comparado las capacidades que el roadmap identifica como terminadas con los paquetes documentales. Las tres capacidades actualmente marcadas como operativas/validadas —**prospección automatizada, bot de precios e integración/ranking económico V1**— disponen ahora de paquete de fase con README, arquitectura, decisiones y validación.

Las áreas que el roadmap marca como **en evolución o en desarrollo** no se han falsificado como fases terminadas: Atlas, JGB, matriz hardware, CABE/RULA, benchmarks reales, agentic, router, web/app y Manada siguen fuera del estado ACEPTADA cuando la evidencia disponible no permite cerrarlas.

## Próximas fases

Se añadirán aquí únicamente cuando exista una unidad de trabajo suficientemente definida, validada y trazable.

## Plantilla conceptual de un paquete

Cada paquete debe cubrir, según proceda:

- `README.md` — contexto, alcance, estado y mapa documental.
- `ARCHITECTURE.md` — arquitectura y esquemas.
- `DECISIONS.md` — decisiones, motivaciones y alternativas.
- `VALIDATION.md` — pruebas, evidencia y aceptación.
- `DIAGRAMS.md` — diagramas mantenidos cuando su complejidad lo justifique.

Norma completa: [`../DOCUMENTATION_PROTOCOL.md`](../DOCUMENTATION_PROTOCOL.md).
