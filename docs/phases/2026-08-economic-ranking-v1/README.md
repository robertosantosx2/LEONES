# Fase 2026-08 — Ranking económico V1

**Estado: 🟢 ACEPTADA**

## Objetivo

Combinar evidencia técnica, apertura JGB, adecuación al hardware y coste observado para producir un ranking económico auditable.

## Arquitectura

```text
ATLAS
 │
 ├── JGB
 ├── rendimiento
 └── requisitos
       ↓
  HARDWARE FIT
       ↓
 ¿VIABLE?
  ├─ NO → excluir
  └─ SÍ
       ↓
 PRECIOS OBSERVADOS
       ↓
 COSTE HARDWARE
       ↓
 RANKING ECONÓMICO
```

## Fórmula V1

```text
calidad_técnica =
    0,35 × rendimiento_normalizado
  + 0,25 × JGB_normalizado
  + 0,40 × hardware_fit

ranking_económico =
    calidad_técnica / (coste_hardware / 100)
```

Los pesos son parametrizables y experimentales.

## Reglas

1. La viabilidad precede al precio.
2. JGB es independiente.
3. El precio procede de observaciones reales.
4. `partial`/`unknown` no producen un score económico ficticio.
5. El coste de componentes no se presenta como PC completo.
6. La salida debe conservar la procedencia de precio y evidencia.

## Criterios de cierre

- [x] fórmula V1;
- [x] integración de precios;
- [x] test de integración;
- [x] generación del ranking;
- [x] publicación del CSV;
- [x] documentación de la metodología;
- [x] separación JGB/rendimiento/precio.

## Evidencia

La V1 está descrita en `docs/atlas-economic-ranking.md` y forma parte del workflow de generación de recomendaciones. El roadmap del proyecto la identifica como **validada**, con evolución posterior hacia V1.1.

## Evolución

```text
V1 → CPU/RAM observados
V1.1 → CPU/RAM/GPU/VRAM con cobertura mayor
V2 → PC completo
V3 → TCO
V4 → optimización multiobjetivo
```

## Documentación relacionada

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`DECISIONS.md`](DECISIONS.md)
- [`VALIDATION.md`](VALIDATION.md)
- [`../../atlas-economic-ranking.md`](../../atlas-economic-ranking.md)
- [`../../atlas-hardware-price-integration.md`](../../atlas-hardware-price-integration.md)
- [`../../ROADMAP.md`](../../ROADMAP.md)
