# DSpine en llama.cpp — investigación e integración

**Estado:** investigación reproducible; todavía no hay ejecución MEASURED en el MSI.

## Objetivo

Evaluar e integrar, de forma aislada y reversible, el soporte comunitario de DSpine para llama.cpp. La rama de trabajo de LEONES no modifica el llama.cpp instalado ni afirma compatibilidad que no haya sido probada.

- Rama LEONES: `research/dspine-llama-cpp`
- Fork de referencia: [Ajay9o9/llama.cpp, rama dspine](https://github.com/Ajay9o9/llama.cpp/tree/dspine)
- Implementación original: [Tencent/DSpine](https://github.com/tencent/dspine)
- Modelo GGUF de referencia: [aj9o9/Qwen3.8-27B-DSpine-b16-GGUF](https://huggingface.co/aj9o9/Qwen3.8-27B-DSpine-b16-GGUF)
- Artículo: [arXiv:2609.36173](https://arxiv.org/abs/2609.36173)

## Qué es DSpine

DSpine significa *Draft in Parallel, Condition Through Depth*. Es un drafter para decodificación especulativa: propone un bloque de tokens en paralelo y transmite dependencias causales entre posiciones a través de la profundidad de sus capas. El modelo objetivo verifica las propuestas. No es un modelo conversacional autónomo ni una cuantización del modelo objetivo.

La implementación publicada para Qwen3.8-27B describe cinco capas de drafter, estados ocultos extraídos de cinco capas del modelo objetivo y bloques de 16 tokens. La selección de propuestas incluye una tabla de transiciones y una verificación especulativa. Por tanto, el drafter está acoplado a una familia/configuración de modelo objetivo; no se puede emparejar arbitrariamente con cualquier GGUF pequeño.

## Estado de compatibilidad verificado en fuentes públicas

| Elemento | Estado |
|---|---|
| llama.cpp oficial | La ficha del GGUF indica que todavía no incorpora DSpine |
| Fork Ajay9o9 | Rama `dspine` anunciada como llama.cpp master más soporte DSpine |
| DSpine oficial | Implementación de inferencia publicada para SGLang; también hay paquete MLX |
| Qwen3-8B | Pareja objetivo/drafter publicada por Tencent |
| Qwen3.8-27B | Pareja objetivo/drafter y conversión GGUF publicadas |
| Qwen3.5 / MiniCPM / modelos arbitrarios | No asumir compatibilidad |

La rama debe auditarse por SHA y por los cambios reales frente al upstream antes de compilarla o recomendarla. La disponibilidad de un GGUF de drafter no prueba por sí sola que cualquier binario llama.cpp pueda cargarlo.

## Evaluación para MSI Thin 15 B12UC

Perfil de referencia LEONES: i7-12650H, RTX 3050 Laptop de 4 GiB (SM 8.6), 14 GiB RAM, Ubuntu.

**No se autoriza todavía una prueba de generación en el MSI.** Primero deben completarse la auditoría de código, la compilación limpia y las pruebas automáticas fuera del equipo. Después se preparará un paquete mínimo de validación.

El modelo GGUF Qwen3.8-27B-DSpine publicado es únicamente el drafter (Q4_K_M: alrededor de 1.26 GB); también hace falta el modelo objetivo Qwen3.8-27B. La suma de objetivo, drafter, buffers, KV y contexto hace que esta pareja no sea una candidata razonable para 4 GiB de VRAM. Podría estudiarse ejecución híbrida CPU/GPU, pero 14 GiB de RAM y swap no convierten esa configuración en una ejecución recomendable ni rápida.

La pareja Qwen3-8B merece una auditoría separada, pero no se presupone que exista una conversión GGUF compatible ni que el fork la implemente con el mismo grado de soporte.

## Fases y criterios de salida

1. **Fuentes y procedencia:** fijar upstream, fork, rama, SHA, licencia y diferencias.
2. **Auditoría del código:** localizar parser GGUF, arquitectura/tensor types, carga del drafter, extracción de hidden states, algoritmo de verificación, sampler y rutas CPU/CUDA.
3. **Compilación CI:** compilar el fork en runner Linux CPU; registrar SHA y logs. La CI no equivale a validación CUDA.
4. **Pruebas sin GPU:** ejecutar tests existentes y añadir tests de metadatos/errores si el código lo permite. No fabricar resultados de rendimiento.
5. **Preparación MSI:** matriz de modelos, hashes, comandos, límites de memoria y rollback.
6. **Gate físico:** solo entonces pedir intervención en el MSI para compilar CUDA, cargar modelos y medir tokens/s, aceptación, VRAM/RAM y estabilidad.

## Reglas de evidencia

- `ESTIMATED`: cálculos y predicciones; nunca presentarlos como mediciones.
- `SOURCE-VERIFIED`: afirmaciones confirmadas en código/documentación upstream.
- `CI-PASSED`: pruebas ejecutadas en CI, con SHA y logs.
- `MSI-MEASURED`: únicamente resultados recogidos en el MSI real.
- No descargar modelos grandes ni ejecutar generación en el MSI sin revisar antes memoria y almacenamiento.
- No sustituir ni sobrescribir la instalación llama.cpp existente.
- No fusionar ni abrir PR upstream hasta tener una implementación reproducible y una comparación válida.

## Primer gate

Ejecutar `scripts/dspine-llama-cpp-audit.sh` en CI o en una máquina de desarrollo. La salida registra el commit del fork y comprueba que se puede configurar y compilar una build CPU. La auditoría CUDA y la validación del modelo se reservan para una fase posterior.
