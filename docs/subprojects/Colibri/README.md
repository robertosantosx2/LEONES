# Colibrì — documentación técnica

Documentación de investigación y validación del motor Colibrì, separando resultados medidos, análisis de código y propuestas pendientes.

## Investigación MoE / CUDA

- [Auditoría de tandem.cpp y adaptación a Colibrì (2026-11-10)](research/tandem-cpp-audit-2026-11-10.md): inventario completo del snapshot, revisión del patch, algoritmos transferibles, límites del MSI y plan de integración.
- [Auditoría del ciclo de vida del setup CUDA Qwen3.6 (2026-11-10)](research/qwen36-chain-setup-lifecycle-audit-2026-11-10.md): hallazgo de salidas parciales, ownership y limpieza común implementada.
- [Protocolo de validación MoE v1](research/colibri-moe-validation-protocol-v1.md): gates de colocación atómica, matriz CPU/GPU, métricas, repetibilidad y reglas de publicación.
- [Especificación del planner atómico Qwen3.6 CUDA v1](research/qwen36-chain-placement-planner-spec-v1.md): contrato de inventario, presupuesto, selección de dispositivo, commit/rollback, telemetría y 18 casos de prueba unitaria.
- [JSON Schema del manifiesto MoE v1](../../../schemas/colibri-moe-benchmark-v1.schema.json): contrato versionado para registrar experimentos y recibos.
- [Rama de implementación en el fork Colibrì](https://github.com/robertosantosx2/colibri/tree/research/qwen36-cuda-chain-planner): cambios de código y diseño de planner.
- [PR de revisión en el fork (draft #1)](https://github.com/robertosantosx2/colibri/pull/1): presupuesto explícito y admisión atómica de la cadena Qwen3.6.
- [Diseño de integración tandem.cpp → Colibrì](https://github.com/robertosantosx2/colibri/blob/research/qwen36-cuda-chain-planner/docs/research/tandem-cpp-moe-integration.md): fases, invariantes, criterios de aceptación y matriz de pruebas.

## Estado de validación

- Auditoría del código upstream: realizada sobre el snapshot `ewhacc/tandem.cpp` commit `e1acb8877bfcf92b4ae7c9f0e0f1d896dbf6c683`.
- Corrección de presupuesto de VRAM con `CUDA_EXPERT_GB` numérico: implementada en la rama del fork.
- Admisión automática indivisible del trunk de la cadena: implementada como decisión de tamaño (todas las ofertas en un dispositivo o todas en CPU); tests fake-CUDA añadidos, ejecución pendiente.
- Limpieza de fallos de inicialización de `q36cc_setup()`: implementada en el fork; todas las salidas posteriores a publicar `m->cchain` pasan por `q36cc_discard_setup()`, que libera recursos propios y tablas auxiliares y limpia el puntero; el cierre del backend queda registrado inmediatamente tras `cc_init()`, incluso si una reserva posterior falla. Compilación y tests pendientes.
- Límite conocido: la admisión no convierte las subidas CUDA del tier en una transacción. La limpieza de fallos de setup ya está implementada, pero la liberación ante fallos asíncronos de upload y el rollback de operaciones del tier requieren validación de runtime.
- `COLI_PLACE` explícito sigue siendo una política manual del usuario; la admisión atómica descrita se aplica a la colocación automática.
- Protocolo LEONES y esquema JSON v1: publicados; aún no hay recibos de ejecución asociados.
- Validación CUDA y benchmark en RTX 3050 sm_86: pendientes; no se atribuye rendimiento medido a esta integración.

## Estado del PR

- PR de revisión creado en el fork: [robertosantosx2/colibri#1](https://github.com/robertosantosx2/colibri/pull/1), en borrador.
- La creación directa del PR contra `JustVugg/colibri` fue rechazada por GitHub con HTTP 403 (`Resource not accessible by integration`). Por tanto, no existe todavía PR upstream.
