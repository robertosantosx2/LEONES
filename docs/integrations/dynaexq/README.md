# DynaExQ / DynaQuant ↔ ODS ↔ LEONES
**Perfil:** investigación de precisión/residencia dinámica para MoE según routing y presupuesto de memoria.
**Estado LEONES:** 🟡 P2/P3 — algoritmo experimental.

## Resumen
DynaExQ estudia asignar dinámicamente precisión y residencia a expertos de acuerdo con el comportamiento de routing y el presupuesto de GPU. No es simplemente un servidor listo para ODS, sino una fuente para futuras políticas del Runtime Selector.

## Aprovechamiento
La capability podría expresarse como `dynamic_precision_residency=true`. El selector podría elegir una estrategia distinta según VRAM disponible, importancia del experto y calidad objetivo.

## Riesgos
La integración directa exigiría portar algoritmo, validarlo en modelos actuales y comprobar calidad. Los resultados de investigación no equivalen a un backend estable.

## LEONES
Medir calidad/perplexity además de memoria y throughput. No aceptar una reducción de precisión sin un registro explícito del impacto.

## Veredicto
**Clasificación:** P2/P3 — investigación para una futura capa de optimización.
**Fuente:** https://github.com/kexinchu/DynaQuant