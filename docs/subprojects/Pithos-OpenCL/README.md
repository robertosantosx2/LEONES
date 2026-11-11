# Pithos — Intel OpenCL dense logits reliability

Estado: **parche aplicado en el fork personal; pendiente de compilación y validación física**.

## Objetivo

Desarrollar en LEONES una corrección reproducible para el fallo de lectura de logits del backend Intel OpenCL observado con Pithos 0.6.0 y LFM3-1.7B Q4_K_M en Intel UHD integrada.

Repositorio upstream: https://github.com/benmaster82/Pithos

## Evidencia de referencia

Equipo de validación: MSI Thin 15 B12UC, Ubuntu, Intel Core i7-12650H, Intel UHD integrada, RTX 3050 Laptop 4 GiB, 14 GiB RAM.

Modelo: `LFM3-1.7B-Q4_K_M.gguf`.

- La lectura OpenCL de logits con staging pinned falló con `CL_OUT_OF_RESOURCES (-5)`.
- El A/B con `PITHOS_CL_LOGITS_HOST=malloc` evitó el error observado.
- Dos ejecuciones con staging malloc: PP128 92.87 / 105.63 tok/s warm; TG64 11.71 / 11.59 tok/s warm.
- Generación real: 256 tokens completados, 10.74 tok/s, sin error OpenCL.
- El A/B y la generación son evidencia de una mitigación local, no demuestran la causa raíz del driver ni validan el parche de propagación de errores.

## Diseño del cambio

1. La espera de eventos debe detectar evento nulo, error de consulta y estado de ejecución negativo.
2. `gpu_dense_logits()` debe devolver éxito/fallo y nunca copiar datos host si el readback ha fallado.
3. `forward_token_gpu()` debe marcar `gpu_lost` y salir sin avanzar posición/contadores.
4. `ctx_forward()` ya dispone de `lost_state()`: resetea el contexto perdido y devuelve `NULL`, permitiendo que el llamador detecte el fallo.
5. Los consumidores de `ctx_forward()`, especialmente benchmark TG, deben comprobar `NULL` antes de leer logits.

## Implementación en el fork

- Fork: https://github.com/robertosantosx2/Pithos
- Rama: `fix/intel-opencl-dense-logits-fail-closed`
- PR de validación en el fork: https://github.com/robertosantosx2/Pithos/pull/1 (Draft)
- Base: `0a05458599d3bc3a7bd470ae28b59aa457b79b90` (sin divergencia respecto al upstream en el momento de crear la rama).
- Cambios: API de logits con retorno de estado, comprobación del evento OpenCL, salida fail-closed, reset del contexto perdido y protección del benchmark TG.
- `ctx_forward()` procesa `lost_state()` antes de llamar a `gpu_rebalance()`, evitando reutilizar la ruta GPU después del fallo.

No se ha modificado `benmaster82/Pithos`.

## Aplicación y validación pendientes

- Compilar la rama del fork en Ubuntu con OpenCL Intel y Vulkan NVIDIA.
- Compilar en Ubuntu con OpenCL Intel y Vulkan NVIDIA.
- Repetir A/B pinned/malloc y comprobar que el fallo devuelve `NULL`, nunca logits stale.
- Verificar fallback CPU después de pérdida del contexto.
- Ejecutar tests y benchmark; no publicar cifras del parche hasta medirlo físicamente.
- Actualizar el PR Draft del fork con los resultados.
- Abrir PR upstream solo después de validar ambos backends y los callsites.

## Reglas LEONES

- Evidencia física separada de estimaciones y propuestas.
- No declarar corregido el bug hasta ejecutar las pruebas.
- No modificar ni hacer push a upstream sin autorización.
