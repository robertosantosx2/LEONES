# Fase 2026-08 — Bot mensual de precios de hardware

**Estado: 🟢 ACEPTADA**

## Objetivo

Crear una capa económica independiente que observe mensualmente precios de CPU, RAM y GPU NVIDIA y entregue datos trazables al recomendador.

## Alcance aceptado

- cuatro fuentes activas;
- extracción y normalización;
- fallback de adquisición;
- control de calidad;
- histórico de observaciones;
- resumen vigente;
- automatización mensual;
- publicación en el repositorio;
- integración posterior con el recomendador.

## Fuentes activas

1. Coolmod
2. PcComponentes
3. MediaMarkt España
4. LDLC España

Amazon está actualmente **fuera de la cobertura activa** y no debe aparecer como fuente operativa hasta una decisión explícita.

## Arquitectura

```text
FUENTES
  ↓
ADAPTADORES
  ↓
EXTRACCIÓN
  ↓
NORMALIZACIÓN
  ↓
CONTROL DE CALIDAD
  ├─ válido → histórico/resumen
  └─ rechazado → trazabilidad de calidad
                    ↓
              RECOMENDADOR
```

## Datos

- `hardware_price_observations.csv`: observaciones históricas.
- `hardware_prices.csv`: resumen utilizable.
- `hardware_price_market_summary.csv`: agregación por producto.
- `hardware_price_quality.csv`: resultado de controles.

## Regla económica principal

> **No se inventa un precio que no haya sido observado.**

El precio es una dimensión económica independiente del JGB, del rendimiento y de la viabilidad técnica.

## Criterios de cierre

- [x] fuentes activas configuradas;
- [x] extracción;
- [x] normalización;
- [x] calidad;
- [x] histórico;
- [x] resumen;
- [x] workflow mensual;
- [x] publicación;
- [x] documentación.

## Evolución no incluida en el cierre

Aumentar cobertura por tienda, resolver variantes y marketplaces, anomalías, precio habitual/promocional y TCO son evolución posterior.

## Documentación relacionada

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`DECISIONS.md`](DECISIONS.md)
- [`VALIDATION.md`](VALIDATION.md)
- [`../../hardware-price-bot.md`](../../hardware-price-bot.md)
- [`../../hardware-price-sources.md`](../../hardware-price-sources.md)
- [`../../hardware-price-quality.md`](../../hardware-price-quality.md)
- [`../../atlas-hardware-price-integration.md`](../../atlas-hardware-price-integration.md)
- **Guía pedagógica de mantenimiento:** [`../../completed/H01-H02-HARDWARE-PRICES.md`](../../completed/H01-H02-HARDWARE-PRICES.md)
