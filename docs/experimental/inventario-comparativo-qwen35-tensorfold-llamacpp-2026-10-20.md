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

| Fecha | Motor / versión | Modelo y formato | Contexto | Prefill / procesamiento del prompt | Generación medida | TTFT | VRAM del proceso | Resultado |
|---|---|---|---:|---|---:|---:|---:|---|
| 2026-10-19 | TensorFold native 1.1.1, CUDA | Qwen3.5-2B, `mlx-community/Qwen3.5-2B-MLX-4bit`, 4-bit group 64 | 1.024 | Velocidad de prefill no registrada | 95,08 tok/s (muestra 32 tokens); 105,71 tok/s (muestra 128 tokens) | 88,2 ms; 94,1 ms | aprox. 2.388 MiB | Inferencia real en español; ambas salidas limitadas por `max_tokens` |
| 2026-10-19 | TensorFold native 1.1.1, CUDA | Qwen3.5-4B, `mlx-community/Qwen3.5-4B-MLX-4bit`, 4-bit group 64 | 512 | Latencia de prefill: 190 ms y 209 ms; velocidad tok/s no registrada | 53,64 tok/s (64 tokens); 53,42 tok/s (128 tokens) | 193 ms; 212 ms | aprox. 3.120 MiB | Inferencia real en español; salidas limitadas por `max_tokens` |
| 2026-10-20 | llama.cpp CUDA, build `b11740-6fa4f6cd3` | Qwen3.5-4B GGUF `Q4_K_M` | 512 | **141,2 tok/s** | 42,4 tok/s | No registrado en el documento de la prueba | 2.808 MiB | Respuesta coherente en español; SHA-256 del GGUF verificado |
| 2026-10-20 | llama.cpp CUDA, build `b11740-6fa4f6cd3` | Qwen3.5-2B GGUF `Q4_K_M` (`~/ods/data/models/Qwen3.5-2B-Q4_K_M.gguf`) | 2.048 | **175,0 tok/s** | **81,2 tok/s** | No registrado | No registrado en esa captura | Respuesta coherente en español con `--chat-template-kwargs '{"enable_thinking":false}'`; primera ejecución sin ese ajuste no produjo una respuesta útil |
| 2026-10-20 | RustingStrata (build local; NVRTC 13.0.88 aislado) | Qwen3.5-4B GGUF `Q4_K_M` (mismo archivo que llama.cpp) | 1.024 | **915,3–986,5 tok/s** (prefill del benchmark; prompts 128/512) | **46,1–46,7 tok/s** (64 tokens, 3 repeticiones) | No registrado | 2.928 MiB durante la prueba HTTP del servidor; pico del benchmark no registrado | Benchmark GPU completado; servidor OpenAI-compatible HTTP 200 y respuesta coherente en español. No es comparación controlada con los otros motores |
 
### Otras métricas conservadas

- **TensorFold Qwen3.5-2B:** tiempo de generación reportado 0,326 s para la muestra de 32 tokens y 1,201 s para 128 tokens. VRAM total observada: 2.411 / 4.096 MiB.
- **TensorFold Qwen3.5-4B:** carga del modelo 6,4 s; latencia de prefill 190 ms y 209 ms en las dos muestras (la velocidad de prefill en tok/s no quedó registrada); VRAM total observada 3.143 / 4.096 MiB. API local en `http://127.0.0.1:18084/v1`.
- **TensorFold Qwen3.5-2B:** API local en `http://127.0.0.1:18083/v1`; `/v1/models` respondió correctamente.
- **llama.cpp Qwen3.5-4B:** velocidad de procesamiento del prompt (prefill) 141,2 tok/s; contexto 512 y máximo solicitado de 128 tokens. En una captura posterior a la generación, la VRAM total ocupada era 2.831 / 4.096 MiB (proceso llama-cli 2.808 MiB); la utilización GPU de 0 % corresponde a esa captura en reposo, no a la fase de inferencia.
- **llama.cpp Qwen3.5-2B:** prueba adicional el 2026-10-20 con contexto 2.048, máximo solicitado de 96 tokens y temperatura 0. La ejecución sin desactivar el modo de pensamiento no produjo una respuesta útil; al añadir `--chat-template-kwargs '{"enable_thinking":false}'` respondió coherentemente en español: prefill 175,0 tok/s y generación 81,2 tok/s. No se registraron VRAM ni TTFT para esta ejecución.
- **RustingStrata Qwen3.5-4B:** benchmark GPU con `--ctx 1024 --pp 128,512 --tg 64 --reps 3`: prefill 915,3 tok/s (128 tokens) y 986,5 tok/s (512 tokens); decode 46,6 y 46,1 tok/s, respectivamente. Plan reportado por el motor: 2.752 MB para pesos/estado/scratch; la captura de servidor mostró 2.928 MiB para el proceso. Esta última cifra no es un pico de VRAM del benchmark.
- **RustingStrata API:** `GET /v1/models` y `POST /v1/chat/completions` funcionaron en `127.0.0.1:18083`; la respuesta no-streaming fue HTTP 200 y coherente en español (32 tokens de completion, 30 de prompt). El servidor se detuvo después; una captura posterior mostró 15 MiB totales de GPU y solo Xorg.
- **SHA-256 del GGUF Qwen3.5-4B:** `c3c2cf023efdbd913c2363a14d5c7266db5e05c4602f1c0790eaed567d8aff23`.

## Comparación directa disponible: Qwen3.5-4B

| Métrica | TensorFold CUDA | llama.cpp CUDA |
|---|---:|---:|
| Formato / cuantización | MLX-4bit, group 64 | GGUF Q4_K_M |
| Contexto configurado | 512 | 512 |
| **Velocidad de prefill** | No registrada en tok/s | **141,2 tok/s** |
| Latencia de prefill | 190 ms y 209 ms | No registrada |
| TTFT | 193 ms y 212 ms | No registrado |
| Velocidad de generación | 53,42–53,64 tok/s | 42,4 tok/s |
| VRAM del proceso | 3.120 MiB | 2.808 MiB |
| Inferencia correcta | Sí | Sí |

En estas muestras, TensorFold registró aproximadamente un **26 % más de velocidad de generación** que llama.cpp. Para prefill, solo consta una velocidad en llama.cpp (141,2 tok/s); TensorFold conserva latencias de prefill, pero no una velocidad en tok/s. Por tanto, no puede compararse directamente la velocidad de prefill entre ambos motores con los datos actuales. No debe presentarse como ventaja definitiva del motor: los formatos de pesos son diferentes y no consta que prompt, revisión exacta del modelo, plantilla, condiciones de caché y procedimiento de medida fueran idénticos. Hace falta un benchmark controlado antes de atribuir la diferencia al runtime.

## Intento fallido que no debe confundirse con el resultado completado

El registro TensorFold incluye un intento inicial de arranque del modelo 4B que fue rechazado porque el presupuesto CUDA disponible era insuficiente con `TENSORFOLD_CUDA_MEMORY_LIMIT_GB=3.4` y una reserva de 0,5 GiB. Posteriormente se documentó una ejecución CUDA completada del mismo modelo con contexto 512. Por tanto, el intento fallido se conserva como incidencia de configuración, no como resultado final de compatibilidad.

## Conclusiones verificadas

1. TensorFold 1.1.1 con CUDA ejecutó Qwen3.5-2B y Qwen3.5-4B en la RTX 3050 Laptop.
2. llama.cpp con CUDA ejecutó Qwen3.5-4B GGUF Q4_K_M en la misma GPU.
3. En las muestras registradas, Qwen3.5-2B en TensorFold alcanzó 95,08–105,71 tok/s y en llama.cpp 81,2 tok/s; Qwen3.5-4B en TensorFold, 53,42–53,64 tok/s; y Qwen3.5-4B en llama.cpp, 42,4 tok/s. Los formatos y protocolos difieren, por lo que estas cifras no constituyen una comparación controlada.
4. La mayor velocidad observada en TensorFold para 4B viene acompañada de un mayor uso de VRAM del proceso en estas capturas.
5. RustingStrata ejecutó inferencia GPU y expuso una API HTTP compatible con OpenAI en una prueba local; el benchmark interno registró 46,1–46,7 tok/s de generación. No se ha probado todavía la conexión de esta API con ODS, Magnitude, OpenBot ni LEONES Runtime.
6. No se ha verificado aún si el GGUF Qwen3.5-4B contiene expertos MoE. La salida de `gguf_dump.py` filtrada por el usuario no devolvió metadatos; `resident experts 0/0` por sí solo no permite concluir si el modelo es denso ni evaluar la distribución CPU/GPU de expertos.

## Registros originales

- [TensorFold: pruebas locales Qwen3.5 en Ubuntu, 2026-10-19](https://github.com/robertosantosx2/LEONES/blob/docs/tensorfold-qwen35-local-results-2026-10-19/docs/TENSORFOLD-QWEN35-LOCAL-2026-10-19.md)
- [llama.cpp: Qwen3.5-4B GGUF con RTX 3050, 2026-10-20](https://github.com/robertosantosx2/LEONES/blob/main/docs/experimental/qwen3.5-4b-llama-cpp-rtx3050.md)

## Próximo benchmark recomendado

Para comparar los motores con rigor, fijar la misma pregunta/prompt, el mismo número de tokens de salida, el contexto 512, generación greedy, modelo Qwen3.5-4B, GPU sin otros procesos de inferencia, caché en estado documentado y al menos tres repeticiones por motor. Registrar TTFT, tokens/s, duración total, VRAM pico y versiones exactas. Como los formatos MLX-4bit y GGUF Q4_K_M no son idénticos, documentar esta diferencia incluso en una prueba controlada.


## RustingStrata: inferencia, API y benchmark GPU (2026-10-20)

La validación avanzó más allá de la carga de NVRTC: se obtuvo una respuesta coherente mediante la API HTTP y se ejecutó el benchmark integrado. El motor sigue siendo experimental y los datos no son una comparación controlada frente a llama.cpp o TensorFold.

- **Entorno:** Ubuntu nativo, Core i7-12650H, 14 GiB RAM, RTX 3050 Laptop 4 GiB, driver 580.178.04.
- **Modelo:** `~/llama.cpp-cuda/models/qwen3.5-4b-Q4_K_M.gguf`; SHA-256 `c3c2cf023efdbd913c2363a14d5c7266db5e05c4602f1c0790eaed567d8aff23`.
- **Compatibilidad CUDA:** NVRTC 13.0.88 se extrajo en `~/rusting-strata-test/vendor/nvrtc13/` y se cargó mediante `LD_LIBRARY_PATH`, sin instalar ni sustituir bibliotecas CUDA del sistema.
- **Prueba API:** `strata serve --model ... --gpu --ctx 1024 --addr 127.0.0.1:18083`. `GET /v1/models` respondió correctamente y `POST /v1/chat/completions` devolvió HTTP 200 con una respuesta coherente en español. Métricas de esa respuesta: 30 tokens de prompt, 32 de completion y 62 totales.
- **Benchmark GPU:** `strata bench --gpu --ctx 1024 --pp 128,512 --tg 64 --reps 3`.

| Prompt | Prefill medio (rango de tres repeticiones) | Decode medio (rango de tres repeticiones) |
|---:|---:|---:|
| 128 tokens | 915,3 (906,2–925,6) tok/s | 46,6 (46,5–46,7) tok/s |
| 512 tokens | 986,5 (985,6–988,0) tok/s | 46,1 (46,1–46,2) tok/s |

El plan del motor informó 2.752 MB para pesos/estado/scratch y 32 MB para KV a contexto 1.024. La prueba del servidor registró 2.928 MiB para el proceso; no se capturó el pico de VRAM del benchmark. Después de detener el servidor, una captura de `nvidia-smi` mostró 15 MiB de uso total y únicamente Xorg entre los procesos listados.

### Interpretación y límites

- **Inferencia local funcional:** confirmada por la respuesta HTTP coherente y el benchmark completado.
- **API compatible con OpenAI:** probados `GET /v1/models` y `POST /v1/chat/completions` no-streaming; streaming aún no probado.
- **Comparación con llama.cpp:** el resultado previo de llama.cpp para el mismo archivo Qwen3.5-4B Q4_K_M fue 42,4 tok/s de generación, mientras RustingStrata registró 46,1–46,7 tok/s en su benchmark interno. No atribuir la diferencia al motor todavía: los protocolos, contextos y métodos de medición no son idénticos.
- **Arquitectura MoE:** pendiente. La consulta del usuario a `gguf_dump.py` no produjo líneas de metadatos y el registro `resident experts 0/0` no basta para demostrar que el modelo sea denso.
- **Integración:** no se ha conectado la API a ODS, Magnitude, OpenBot ni LEONES Runtime. La prueba demuestra ejecución aislada del motor, no integración E2E.
- **Licencia:** no verificada; este informe no clasifica RustingStrata como Open Source.

## Próximas verificaciones

1. Leer los metadatos GGUF con una herramienta que realmente los imprima y confirmar `general.architecture`, `expert_count` y `expert_used_count`.
2. Ejecutar llama.cpp con un protocolo de benchmark comparable (mismo GGUF, contexto, prompt, salida greedy y repeticiones) y registrar TTFT, decode, VRAM pico y versiones exactas.
3. Probar streaming y luego una llamada real desde un cliente OpenAI-compatible; no declarar integración hasta comprobarlo de extremo a extremo.
