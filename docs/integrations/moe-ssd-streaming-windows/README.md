# moe-ssd-streaming-windows ↔ ODS ↔ LEONES
**Perfil:** implementación Windows/NVIDIA de streaming de expertos desde SSD.
**Estado LEONES:** 🟡 P2.

## Resumen
Es útil porque aporta evidencia de portabilidad de la idea de SSD streaming fuera de Linux/Apple. El proyecto documenta pruebas con Qwen3-30B-A3B y almacenamiento SSD.

## ODS
No debe incorporarse como servicio Linux directamente. Su valor es validar que la arquitectura de expert streaming puede sobrevivir a diferentes stacks.

## LEONES
Comparar throughput y latencia con equivalentes Linux, registrando filesystem y API de almacenamiento.

## Veredicto
**Clasificación:** P2 — evidencia de portabilidad.
**Fuente:** https://github.com/tonbistudio/moe-ssd-streaming-windows