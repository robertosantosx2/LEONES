# Fase 2026-08 — Prospección diaria automatizada

**Estado: 🟢 ACEPTADA**

## Objetivo

Mantener una prospección diaria del ecosistema de IA local orientada a descubrir modelos, repositorios, runtimes, agentes, herramientas, benchmarks, técnicas de eficiencia y componentes de hardware relevantes para LEONES.

La prospección es descubrimiento: no convierte automáticamente un hallazgo en recomendación ni en evidencia verificada.

## Alcance

La fase comprende:

- descubrimiento automatizado;
- filtrado por licencia OSI;
- priorización Copyleft;
- enriquecimiento y clasificación;
- generación de informes;
- integración con Atlas y la web;
- ejecución automatizada mediante GitHub Actions.

## Arquitectura

```text
FUENTES
  ↓
DESCUBRIMIENTO
  ↓
SPDX / LICENCIA
  ↓
¿OSI APROBADA?
 ├─ NO → fuera del conjunto principal
 └─ SÍ
      ↓
Copyleft prioritario / normal
      ↓
REVISIÓN TÉCNICA
      ↓
EVIDENCIA
      ↓
ATLAS
      ↓
RECOMENDADOR / ROUTER
```

## Regla fundamental

La licencia OSI es la puerta de entrada del conjunto principal de prospección. Dentro de ese conjunto, GPL/AGPL/LGPL tienen prioridad visual y analítica, pero **Copyleft prioritario no significa automáticamente recomendado**.

## Decisiones

1. La prospección debe ser diaria.
2. OSI es el filtro de entrada del conjunto principal.
3. El SPDX declarado por GitHub es evidencia de descubrimiento, no revisión jurídica integral.
4. Los pesos de modelos requieren revisión específica de sus términos.
5. `prospector descubre; no valida`.
6. El hallazgo pasa por estados antes de alimentar recomendaciones.

## Evidencia de aceptación

La funcionalidad está respaldada por el workflow diario de prospección, los scripts de descubrimiento y los artefactos publicados en `data/prospection` y `web/data/prospeccion.json`.

La documentación normativa existente define el filtro OSI, el tratamiento Copyleft, el flujo de evidencia y la separación entre descubrimiento y recomendación.

## Criterios de cierre

- [x] ejecución automática diaria;
- [x] filtro OSI;
- [x] prioridad Copyleft;
- [x] enriquecimiento/clasificación;
- [x] informes;
- [x] publicación de resultados;
- [x] documentación del proceso;
- [x] integración con Atlas/web.

## Limitaciones que permanecen

La fase está aceptada como **prospección automatizada**, no como validación automática universal de todos los candidatos. Persisten tareas de reducción de duplicados, seguimiento de cambios, mejora de fuentes y revisión técnica.

## Documentación relacionada

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`DECISIONS.md`](DECISIONS.md)
- [`VALIDATION.md`](VALIDATION.md)
- [`../../PROSPECTION.md`](../../PROSPECTION.md)
- [`../../PROSPECTION_LICENSE_POLICY.md`](../../PROSPECTION_LICENSE_POLICY.md)
- [`../../../scripts/prospection/PROCEDIMIENTO_DESCUBRIMIENTO_NUEVAS_FUENTES.md`](../../../scripts/prospection/PROCEDIMIENTO_DESCUBRIMIENTO_NUEVAS_FUENTES.md)
