# ExpertFlow ↔ ODS ↔ LEONES
**Perfil:** sistema de inferencia MoE centrado en predicción de routing, caching de expertos y token scheduling.
**Estado LEONES:** 🟡 P2 · fuente de arquitectura/investigación.

## 1. Resumen
ExpertFlow no es simplemente un loader: intenta predecir los próximos expertos para preparar sus pesos antes de necesitarlos. Soporta familias Switch, Mixtral, Qwen-MoE y DeepSeek-MoE y proporciona scripts de benchmark.

## 2. Arquitectura
`routing history → Routing Pattern Predictor → predicted experts → prefetch/offload → scheduling → generation`.
Esto complementa runtimes que ya tienen paging pero sufren latencia de lectura.

## 3. Encaje ODS
Más que un backend inmediato, es una fuente para una futura política de prefetch del Runtime Selector. Si su runtime de generación puede desacoplarse, podría convertirse en middleware.

## 4. Valor LEONES
Es especialmente útil para registrar una nueva capability: `predictive_prefetch`. El benchmark debe medir no sólo tok/s sino precisión de predicción, hit rate y coste del predictor.

## 5. Limitaciones
Mucho código está orientado a experimentos y datasets/predictors concretos. El soporte de serving generalista no es equivalente al de llama-server.

## 6. Veredicto
| Área | Evaluación |
|---|---|
| Predicción MoE | 🟢 |
| Prefetch | 🟢 |
| Modelos | 🟢 |
| Serving ODS | 🟡 |
| Integración directa | 🟡/🔴 |
| Valor arquitectónico | 🟢 |

**Clasificación:** P2 — estudiar e incorporar conceptos al runtime selector.
**Fuente:** https://github.com/expertflow-dac/expertflow