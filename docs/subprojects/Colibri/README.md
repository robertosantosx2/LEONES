# Colibrì — documentación técnica

Documentación de investigación y validación del motor Colibrì, separando resultados medidos, análisis de código y propuestas pendientes.

## Investigación MoE / CUDA

- [Auditoría de tandem.cpp y adaptación a Colibrì (2026-11-10)](research/tandem-cpp-audit-2026-11-10.md): inventario completo del snapshot, revisión del patch, algoritmos transferibles, límites del MSI y plan de integración.
- [Protocolo de validación MoE v1](research/colibri-moe-validation-protocol-v1.md): gates de colocación atómica, matriz CPU/GPU, métricas, repetibilidad y reglas de publicación.
- [Especificación del planner atómico Qwen3.6 CUDA v1](research/qwen36-chain-placement-planner-spec-v1.md): contrato de inventario, presupuesto, selección de dispositivo, commit/rollback, telemetría y 18 casos de prueba unitaria.
- [JSON Schema del manifiesto MoE v1](../../../schemas/colibri-moe-benchmark-v1.schema.json): contrato versionado para registrar experimentos y recibos.
- [Rama de implementación en el fork Colibrì](https://github.com/robertosantosx2/colibri/tree/research/qwen36-cuda-chain-planner): cambios de código y diseño de planner.
- [Diseño de integración tandem.cpp → Colibrì](https://github.com/robertosantosx2/colibri/blob/research/qwen36-cuda-chain-planner/docs/research/tandem-cpp-moe-integration.md): fases, invariantes, criterios de aceptación y matriz de pruebas.

## Estado de validación

- Auditoría del código upstream: realizada sobre el snapshot `ewhacc/tandem.cpp` commit `e1acb8877bfcf92b4ae7c9f0e0f1d896dbf6c683`.
- Corrección de presupuesto de VRAM con `CUDA_EXPERT_GB` numérico: implementada en la rama del fork.
- Test fake-CUDA de regresión: añadido; ejecución pendiente.
- Colocación global indivisible de la cadena CUDA: especificación detallada v1 publicada en LEONES; implementación en el runtime Colibrì pendiente.
- Protocolo LEONES y esquema JSON v1: publicados; aún no hay recibos de ejecución asociados.
- Validación CUDA y benchmark en RTX 3050 sm_86: pendientes; no se atribuye rendimiento medido a esta integración.
