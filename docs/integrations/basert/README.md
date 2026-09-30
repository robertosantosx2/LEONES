# baseRT ↔ ODS ↔ LEONES
**Perfil:** runtime de inferencia orientado a Apple Silicon y NVIDIA GB10/DGX Spark.
**Estado LEONES:** 🟡 P3.

## Resumen
baseRT es relevante para hardware NVIDIA específico de nueva generación y demuestra otra implementación de serving OpenAI-compatible. Su valor para el ODS actual con RTX 3050 es limitado.

## Encaje
Debe aparecer en el radar de runtimes y hardware targets, no en el camino por defecto. Puede resultar interesante si ODS amplía soporte a GB10/DGX Spark.

## Riesgos
Hardware target estrecho y poca relevancia para GPUs antiguas/modestas.

## Veredicto
**Clasificación:** P3 — radar de hardware/runtime.
**Fuente:** https://github.com/basecompute/baseRT