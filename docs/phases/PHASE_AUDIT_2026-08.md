# Auditoría documental de fases — 2026-08

## Objetivo

Comprobar que las capacidades que el proyecto declara terminadas/operativas tienen una unidad documental de cierre conforme al protocolo permanente.

## Criterio

Una fase aceptada debe tener, como mínimo:

- objetivo y alcance;
- arquitectura/esquema;
- reglas e invariantes;
- decisiones y motivaciones;
- validación/evidencia;
- limitaciones y evolución;
- enlaces desde el índice documental.

## Resultado

| Capacidad declarada operativa | Paquete | README | Arquitectura | Decisiones | Validación | Estado |
|---|---|---:|---:|---:|---:|---|
| Prospección automatizada | `2026-08-daily-prospection` | ✅ | ✅ | ✅ | ✅ | 🟢 ACEPTADA |
| Bot mensual de precios | `2026-08-hardware-pricing` | ✅ | ✅ | ✅ | ✅ | 🟢 ACEPTADA |
| Ranking económico V1 | `2026-08-economic-ranking-v1` | ✅ | ✅ | ✅ | ✅ | 🟢 ACEPTADA |
| Atlas → recomendador enriquecido | `2026-08-atlas-recommendation-pipeline` | ✅ | ✅ | ✅ | ✅ | 🟡 EN VALIDACIÓN |

## Hallazgos

### 1. Prospección

La documentación existente `docs/PROSPECTION.md` ya definía el objetivo, filtro OSI, prioridad Copyleft, flujo de evidencia y separación entre descubrimiento y recomendación. Se ha convertido esa documentación en un paquete formal de fase.

### 2. Precios

La infraestructura del bot estaba documentada y el roadmap la marcaba como operativa. Durante la auditoría se detectó una discrepancia: `docs/hardware-price-bot.md` todavía describía Amazon España como fuente activa, mientras `data/hardware/price_sources.csv` y el estado actual del proyecto mantienen cuatro fuentes activas y Amazon fuera. El documento ha sido corregido para que la documentación coincida con la configuración efectiva.

### 3. Ranking económico

La metodología ya estaba descrita en `docs/atlas-economic-ranking.md`, y el roadmap identifica la V1 como validada. Se ha creado el paquete de fase para separar explícitamente la aceptación de V1 de las evoluciones V1.1, PC completo, TCO y optimización multiobjetivo.

### 4. Atlas → recomendador enriquecido

No se ha marcado como aceptado. Existe implementación y documentación, pero la ejecución de GitHub Actions debe completar la validación real antes del cierre.

## Áreas no marcadas como terminadas

La auditoría no ha convertido en fases aceptadas las áreas que el roadmap identifica como en evolución o en construcción: Atlas como fuente única de verdad, JGB completo, matriz hardware completa, CABE/RULA, benchmarks reales, evaluación agentiva LB, router, web/app y Manada.

## Regla posterior a esta auditoría

Cuando una nueva capacidad sea declarada terminada, debe añadirse primero al índice de fases con estado provisional, completar validación y después pasar a ACEPTADA con su paquete documental.

## Trazabilidad

- Protocolo: [`../DOCUMENTATION_PROTOCOL.md`](../DOCUMENTATION_PROTOCOL.md)
- Índice: [`README.md`](README.md)
- Roadmap: [`../ROADMAP.md`](../ROADMAP.md)
