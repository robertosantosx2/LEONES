# Inventario comparativo de pruebas locales de Qwen3.5 — 2026-10-20

**Estado del registro:** consolidación de resultados físicos previamente documentados en LEONES.  
**Equipo:** Ubuntu nativo, Intel Core i7-12650H, 14 GiB RAM, NVIDIA GeForce RTX 3050 Laptop (4 GiB VRAM), driver 580.178.04, CUDA indicada por `nvidia-smi` 13.0.

## Criterio de registro

- **MEASURED / completada:** el motor cargó el modelo en el equipo físico y produjo salida de inferencia.
- **Intento fallido:** un arranque o una configuración concreta falló; no invalida una prueba posterior completada.
- **ESTIMATED / pendiente:** una previsión o prueba no completada no se presenta como resultado medido.
- Los valores de VRAM se conservan tal como fueron capturados: VRAM del proceso y memoria total de GPU no son la misma métrica.
- Las velocidades proceden de muestras cortas, no de un benchmark sostenido. Los resultados entre motores son orientativos mientras no se ejecuten con un protocolo idéntico.

## Tabla comparativa de ejecuciones completadas

| Fecha | Motor / versión | Modelo y formato | Contexto | Generación medida | TTFT | VRAM del proceso | Resultado |
|---|---|---|---:|---:|---:|---:|---|
| 2026-10-19 | TensorFold native 1.1.1, CUDA | Qwen3.5-2B, `mlx-community/Qwen3.5-2B-MLX-4bit`, 4-bit group 64 | 1.024 | 95,08 tok/s (muestra 32 tokens); 105,71 tok/s (muestra 128 tokens) | 88,2 ms; 94,1 ms | aprox. 2.388 MiB | Inferencia real en español; ambas salidas limitadas por `max_tokens` |
| 2026-10-19 | TensorFold native 1.1.1, CUDA | Qwen3.5-4B, `mlx-community/Qwen3.5-4B-MLX-4bit`, 4-bit group 64 | 512 | 53,64 tok/s (64 tokens); 53,42 tok/s (128 tokens) | 193 ms; 212 ms | aprox. 3.120 MiB | Inferencia real en español; salidas limitadas por `max_tokens` |
| 2026-10-20 | llama.cpp CUDA, build `b11740-6fa4f6cd3` | Qwen3.5-4B GGUF `Q4_K_M` | 512 | 42,4 tok/s | No registrado en el documento de la prueba | 2.808 MiB | Respuesta coherente en español; SHA-256 del GGUF verificado |
 
### Otras métricas conservadas

- **TensorFold Qwen3.5-2B:** tiempo de generación reportado 0,326 s para la muestra de 32 tokens y 1,201 s para 128 tokens. VRAM total observada: 2.411 / 4.096 MiB.
- **TensorFold Qwen3.5-4B:** carga del modelo 6,4 s; prefill 190 ms y 209 ms en las dos muestras; VRAM total observada 3.143 / 4.096 MiB. API local en `http://127.0.0.1:18084/v1`.
- **TensorFold Qwen3.5-2B:** API local en `http://127.0.0.1:18083/v1`; `/v1/models` respondió correctamente.
- **llama.cpp Qwen3.5-4B:** velocidad de procesamiento del prompt 141,2 tok/s; contexto 512 y máximo solicitado de 128 tokens. En una captura posterior a la generación, la VRAM total ocupada era 2.831 / 4.096 MiB (proceso llama-cli 2.808 MiB); la utilización GPU de 0 % corresponde a esa captura en reposo, no a la fase de inferencia.
- **SHA-256 del GGUF Qwen3.5-4B:** `c3c2cf023efdbd913c2363a14d5c7266db5e05c4602f1c0790eaed567d8aff23`.

## Comparación directa disponible: Qwen3.5-4B

| Métrica | TensorFold CUDA | llama.cpp CUDA |
|---|---:|---:|
| Formato / cuantización | MLX-4bit, group 64 | GGUF Q4_K_M |
| Contexto configurado | 512 | 512 |
| Velocidad de generación | 53,42–53,64 tok/s | 42,4 tok/s |
| VRAM del proceso | 3.120 MiB | 2.808 MiB |
| Inferencia correcta | Sí | Sí |

En estas muestras, TensorFold registró aproximadamente un **26 % más de tokens/s** que llama.cpp. No debe presentarse como ventaja definitiva del motor: los formatos de pesos son diferentes y no consta que prompt, revisión exacta del modelo, plantilla, condiciones de caché y procedimiento de medida fueran idénticos. Hace falta un benchmark controlado antes de atribuir la diferencia al runtime.

## Intento fallido que no debe confundirse con el resultado completado

El registro TensorFold incluye un intento inicial de arranque del modelo 4B que fue rechazado porque el presupuesto CUDA disponible era insuficiente con `TENSORFOLD_CUDA_MEMORY_LIMIT_GB=3.4` y una reserva de 0,5 GiB. Posteriormente se documentó una ejecución CUDA completada del mismo modelo con contexto 512. Por tanto, el intento fallido se conserva como incidencia de configuración, no como resultado final de compatibilidad.

## Conclusiones verificadas

1. TensorFold 1.1.1 con CUDA ejecutó Qwen3.5-2B y Qwen3.5-4B en la RTX 3050 Laptop.
2. llama.cpp con CUDA ejecutó Qwen3.5-4B GGUF Q4_K_M en la misma GPU.
3. En las muestras registradas, Qwen3.5-2B en TensorFold alcanzó 95,08–105,71 tok/s; Qwen3.5-4B en TensorFold, 53,42–53,64 tok/s; y Qwen3.5-4B en llama.cpp, 42,4 tok/s.
4. La mayor velocidad observada en TensorFold para 4B viene acompañada de un mayor uso de VRAM del proceso en estas capturas.
5. No se ha validado mediante este conjunto de pruebas una integración con ODS, Magnitude, OpenBot ni LEONES Runtime. Son pruebas de inferencia de cada motor, no una prueba E2E de integración.

## Registros originales

- [TensorFold: pruebas locales Qwen3.5 en Ubuntu, 2026-10-19](https://github.com/robertosantosx2/LEONES/blob/docs/tensorfold-qwen35-local-results-2026-10-19/docs/TENSORFOLD-QWEN35-LOCAL-2026-10-19.md)
- [llama.cpp: Qwen3.5-4B GGUF con RTX 3050, 2026-10-20](https://github.com/robertosantosx2/LEONES/blob/main/docs/experimental/qwen3.5-4b-llama-cpp-rtx3050.md)

## Próximo benchmark recomendado

Para comparar los motores con rigor, fijar la misma pregunta/prompt, el mismo número de tokens de salida, el contexto 512, generación greedy, modelo Qwen3.5-4B, GPU sin otros procesos de inferencia, caché en estado documentado y al menos tres repeticiones por motor. Registrar TTFT, tokens/s, duración total, VRAM pico y versiones exactas. Como los formatos MLX-4bit y GGUF Q4_K_M no son idénticos, documentar esta diferencia incluso en una prueba controlada.
