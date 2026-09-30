# vllm-moe ↔ ODS ↔ LEONES
**Perfil:** variante de vLLM con CPU offload y GPU prefetch de expertos MoE.
**Estado LEONES:** 🟡 P2 · experimental.

## Resumen
vllm-moe explora una extensión directa de vLLM donde los expertos permanecen en CPU y los expertos activos se copian a GPU después del routing. Es relevante porque ODS ya podría considerar vLLM como backend general y esta variante apunta a convertir el offload MoE en una capacidad del runtime, no en un servicio separado.

## Arquitectura
`CPU expert store → routing → active experts → GPU`. El modo de prefetch intenta ocultar parte de la transferencia.

## Encaje ODS
La opción natural sería registrar una capability `moe_cpu_offload=true` bajo el backend vLLM. No conviene mantener un fork permanentemente si la funcionalidad no está upstream.

## Riesgos
Compatibilidad con versiones de vLLM, coste de mantener fork, y diferencias entre batching grande y batch=1. El beneficio puede cambiar radicalmente según modelo y tamaño de expertos.

## LEONES
Comparar vLLM upstream, vllm-moe y llama-server sobre idéntico modelo; medir VRAM, RAM, transferencia PCIe, TTFT, prefill, decode y calidad.

## Veredicto
| Área | Evaluación |
|---|---|
| Arquitectura | 🟢 |
| Integración vLLM | 🟢 |
| Madurez | 🟡 |
| Fork dependency | 🔴 |
| ODS | 🟡 |
**Clasificación:** P2 — seguir como vía experimental.
**Fuente:** https://github.com/leoustc/vllm-moe