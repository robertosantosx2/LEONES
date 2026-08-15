# Validación — Ranking económico V1

**Resultado: 🟢 ACEPTADA**

## Criterios

| Criterio | Estado |
|---|---|
| Fórmula explícita | ✅ |
| JGB separado | ✅ |
| Precio observado | ✅ |
| Viabilidad antes de economía | ✅ |
| Control de cobertura | ✅ |
| Test de integración de precios | ✅ |
| Test del ranking económico | ✅ |
| Generación automática | ✅ |
| Publicación CSV | ✅ |
| Documentación metodológica | ✅ |

## Evidencia

`docs/atlas-economic-ranking.md` define el modelo, la fórmula, las reglas de cobertura y la evolución. El repositorio contiene `scripts/test_atlas_economic_rank.py` y `scripts/test_atlas_price_integration.py`, además de `data/prospection/atlas_economic_ranking.csv`.

El roadmap identifica explícitamente la V1 como validada.

## Alcance de la aceptación

Se acepta la **V1 del ranking económico**, no sus evoluciones futuras. La V1 no debe interpretarse como TCO, coste de PC completo ni optimización multiobjetivo.
