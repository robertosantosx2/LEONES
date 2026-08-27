# JALÓN 5 — CIERRE

## Estado

**CERRADO — ejecución física parcial verificable.**

JALÓN 5 convierte la selección de JALÓN 4 en un plan de ejecución física y conserva evidencia local cuando el host es compatible.

## Evidencia física cerrada

- `llama.cpp` + Qwen3-0.6B Q4_K_M: evidencia física local conservada.
- `Ollama` + Qwen2.5-0.5B Q4_K_M: evidencia física local conservada.

## CPD preparado

- `vLLM`: runner físico preparado y contrato verificado.
- `SGLang`: runner físico preparado y contrato verificado.

La ejecución física CPD queda **pendiente de host adecuado**. El Ubuntu utilizado para la validación final no dispone de GPU NVIDIA y sólo presenta ~7 GiB de RAM, además de no tener instalados `vllm` ni `sglang`. Por tanto, no se registra ninguna cifra CPD como `measured`.

## Validación

- Suite completa: **261 tests OK**.
- Contrato de plan físico validado.
- JSON de contratos y evidencias validado.
- `git diff --check` limpio.
- Rama: `jalon5-physical-runtime-execution-v1`.

## Criterio de cierre

El jalón queda cerrado porque la arquitectura, contratos, runners, gates y evidencia física disponible están fijados y reproducibles. La ausencia de un host CPD apropiado es una **condición externa de ejecución**, no un hueco de diseño.

## Siguiente intervención

No se requiere más intervención sobre Ubuntu para JALÓN 5. Cuando exista un host CPD compatible, sólo habrá que ejecutar los runners de `vLLM` y `SGLang` y conservar su evidencia bajo el mismo contrato.
