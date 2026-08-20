# Selección de modelos: fuente canónica

## Regla

`scripts/model_selector.py` es la **única fuente de verdad** para elegibilidad,
fit y ranking técnico de modelos.

Atlas no mantiene una segunda fórmula de selección. El antiguo
`scripts/atlas_recommend_from_feed.py` es ahora un adaptador de compatibilidad:
consume el selector canónico y conserva el CSV histórico para consumidores que
aún no hayan migrado.

## Separación de responsabilidades

| Capa | Responsabilidad |
|---|---|
| Atlas/feed | datos y evidencia de modelos |
| Hardware profile | capacidades reales/observadas del equipo |
| `model_selector.py` | elegibilidad, scoring y TOP-N |
| LLMFit | estimación previa de fit/velocidad |
| Runtime gate | autorización de ejecución |
| GGUF resolver | localizar artefacto compatible |
| Acquisition | obtener y verificar artefacto |
| llama.cpp | ejecutar |
| Benchmark | medir |
| TCO/economía | análisis económico independiente |

## Consecuencia

No se debe añadir una nueva fórmula de `fit_score` en Atlas, ODS, Magnitude o
ningún runtime. Los consumidores deben usar el resultado canónico del selector.

Los precios pueden acompañar una recomendación como evidencia económica, pero
no entran en `fit_score`.

## Estados

`REJECTED` → `CANDIDATE` → `SELECTED` → `TOP_N` → `BENCHMARK_REQUIRED`

El runtime gate solo autoriza candidatos `TOP_N` que no hayan quedado marcados
como `BENCHMARK_REQUIRED`.
