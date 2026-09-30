# ES-MoE ↔ ODS ↔ LEONES
**Perfil:** sistema de entrenamiento MoE con offload experto a host/SSD y gestión tipo memoria virtual.
**Estado LEONES:** 🟡 P3.

## Resumen
ES-MoE está orientado principalmente a entrenamiento más allá de la memoria GPU. Sus técnicas de offload, LRU y prefetch son relevantes conceptualmente, pero el objetivo no es serving local.

## Encaje ODS
No debe integrarse como backend. Sí debe formar parte de la base de conocimiento de técnicas de memoria virtual MoE.

## Aprovechamiento
- experto como unidad de paging;
- LRU;
- prefetch;
- host/SSD tiers;
- planificación basada en capacidad.

## Veredicto
**Clasificación:** P3 — fuente técnica, no backend.
**Fuente:** https://github.com/kaist-ina/es-moe