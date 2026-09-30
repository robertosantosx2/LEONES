# MoE CPU/GPU Collaborative Inference ↔ ODS ↔ LEONES
**Perfil:** investigación de caché de expertos, reutilización y colaboración CPU/GPU.
**Estado LEONES:** 🟡 P2/P3.

## Resumen
El proyecto explora mantener y transferir expertos entre CPU y GPU con caching asíncrono y LRU. Es relevante para equipos con VRAM limitada donde CPU/RAM pueden servir como segunda tier.

## ODS
No se recomienda como backend inmediato. Sí como fuente para el diseño de una política de expert residency y para comparar CPU/GPU collaborative inference con SSD paging.

## LEONES
Medir hit rate, bytes transferidos, latencia de transferencia, VRAM/RAM y calidad. Las cifras del trabajo deben quedar como reported.

## Veredicto
**Clasificación:** P2/P3 — investigación de caching MoE.
**Fuente:** https://github.com/elsa-lab/MoE-CPU-GPU-Collaborative-Inference