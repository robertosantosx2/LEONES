# Integración Atlas ↔ precios de hardware

## Estado

Integración implementada en `scripts/atlas_recommend_from_feed.py` y validada con `scripts/test_atlas_price_integration.py`.

## Principio

El precio pertenece al **perfil de hardware**, no al modelo LLM. Por tanto, el motor no intenta asociar el precio de una CPU/GPU/RAM al nombre de un modelo de IA.

La fuente de verdad es `data/hardware/hardware_prices.csv`, generado por el bot mensual después del control de calidad. Solo las observaciones aceptadas entran en esta capa.

## Qué produce

`data/prospection/atlas_recommendations.csv` incorpora:

- `cpu_price_eur` / `cpu_price_source`
- `ram_price_eur` / `ram_price_source`
- `gpu_price_eur` / `gpu_price_source`
- `hardware_price_eur`
- `price_coverage`
- `value_score`

`hardware_price_eur` solo es una suma de componentes cuando existen observaciones para esos componentes. No se completa un precio faltante mediante estimación.

## Reglas de correspondencia

- CPU: requiere una familia explícita en el `hardware_id` (`i3`, `i5`, `i7`, `i9`, `ryzen 3/5/7/9`).
- RAM: requiere generación DDR4/DDR5 y capacidad explícitas.
- GPU: requiere una familia RTX explícita en el `hardware_id`.
- Si el perfil no identifica suficientemente un componente, su precio queda vacío.
- El precio no modifica el `fit_score` técnico ni sustituye al Índice JGB.
- `value_score` es una métrica separada para estudiar relación entre ajuste técnico y coste observado.

## Flujo

```text
bot mensual de precios
        ↓
hardware_price_quality
        ↓
hardware_prices.csv
        ↓
Atlas recommender
        ↓
fit_score + JGB + evidencia de despliegue
        ↓
precio de hardware + cobertura
        ↓
value_score
```

## Actualización

El workflow de recomendaciones valida primero la integración de precios. El bot mensual sigue siendo la autoridad sobre los precios; el recomendador nunca los modifica.
