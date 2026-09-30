# llama.cpp.35B.moe ↔ ODS ↔ LEONES
**Perfil:** fork de llama.cpp con optimizaciones experimentales de offload/prefetch para MoE.
**Estado LEONES:** 🟡 P2.

## Resumen
El fork investiga mejoras de prefill y acceso a expertos para modelos Qwen MoE, utilizando pesos expertos memory-mapped/pinned y prefetch en un stream CUDA separado.

## Valor para ODS
La proximidad con llama.cpp lo convierte en candidato para estudiar qué optimizaciones pueden terminar upstream. El coste de mantener un fork debe evitarse si no existe una ventaja estable.

## LEONES
Comparar bit a bit calidad y rendimiento con llama.cpp upstream, midiendo especialmente prefill y comportamiento de cache.

## Veredicto
**Clasificación:** P2 — investigación directamente relevante para el backend llama-server.
**Fuente:** https://github.com/MaxDam/llama.cpp.35B.moe