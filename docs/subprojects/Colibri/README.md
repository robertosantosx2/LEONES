# Colibrì — documentación técnica

Documentación de investigación y validación del motor Colibrì, separando resultados medidos, análisis de código y propuestas pendientes.

## Investigación MoE / CUDA

- [Auditoría de tandem.cpp y adaptación a Colibrì (2026-11-10)](research/tandem-cpp-audit-2026-11-10.md): inventario completo del snapshot, revisión del patch, algoritmos transferibles, límites del MSI y plan de integración.
- [Rama de implementación en el fork Colibrì](https://github.com/robertosantosx2/colibri/tree/research/qwen36-cuda-chain-planner): cambios de código y diseño de planner.
- [Diseño de integración tandem.cpp → Colibrì](https://github.com/robertosantosx2/colibri/blob/research/qwen36-cuda-chain-planner/docs/research/tandem-cpp-moe-integration.md): fases, invariantes, criterios de aceptación y matriz de pruebas.

## Estado de validación

- Auditoría del código upstream: realizada sobre el snapshot `ewhacc/tandem.cpp` commit `e1acb8877bfcf92b4ae7c9f0e0f1d896dbf6c683`.
- Corrección de presupuesto de VRAM con `CUDA_EXPERT_GB` numérico: implementada en la rama del fork.
- Test fake-CUDA de regresión: añadido; ejecución pendiente.
- Colocación global indivisible de la cadena CUDA: diseño identificado; implementación pendiente.
- Validación CUDA y benchmark en RTX 3050 sm_86: pendientes; no se atribuye rendimiento medido a esta integración.
