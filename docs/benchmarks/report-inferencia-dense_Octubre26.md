# Report de inferencia densa — Octubre 2026

**Archivo maestro:** `report-inferencia-dense_Octubre26.md`  
**Fecha de consolidación:** 2026-10-21  
**Proyecto:** LEONES  
**Alcance:** intentos y mediciones locales de modelos Qwen/Qwen3.5 en Ubuntu, motores de inferencia, cuantizaciones, configuración, comandos conservados y límites de la evidencia.

> Este informe consolida evidencia disponible en el repositorio y en los registros de las conversaciones de pruebas. No equivale a una transcripción íntegra de cada terminal: los logs completos de algunas ejecuciones siguen únicamente en el equipo local. Cuando no se conservó un comando exacto o una métrica, se indica expresamente.

## 1. Resumen ejecutivo

### Ejecuciones de inferencia completadas

| Motor | Modelo / artefacto | Estado | Resultado principal conservado |
|---|---|---|---|
| TensorFold native 1.1.1, backend CUDA | Qwen3.5-2B, MLX 4-bit | Completada | 95,08 tok/s (32 tokens); 105,71 tok/s (128 tokens) |
| TensorFold native 1.1.1, backend CUDA | Qwen3.5-4B, MLX 4-bit | Completada | 53,64 tok/s (64 tokens); 53,42 tok/s (128 tokens) |
| llama.cpp CUDA | Qwen3.5-4B, GGUF Q4_K_M | Completada | 141,2 tok/s de prefill; 42,4 tok/s de generación en ejecución CLI |
| TensorFold API | Qwen3.5-4B, MLX 4-bit | 3/3 peticiones HTTP 200 | Mediana 54,708 tok/s; 0,7066 s por petición; TTFT 0,1303 s |
| llama.cpp API/CUDA | Qwen3.5-4B, GGUF Q4_K_M | 3/3 peticiones HTTP 200 | Mediana 47,646 tok/s; 0,8680 s por petición |
| llama.cpp CUDA | Qwen3-30B-A3B-Instruct-2507 IQ3_XXS | Barrido de offload completado | Mediana 1,97–2,00 tok/s con 12–14 capas en la tanda larga; 15 capas fue el máximo offload funcional probado |
| RustingStrata CUDA/NVRTC 13.0 | Qwen3-30B-A3B-Instruct-2507 IQ3_XXS | Completada | 7,74 tok/s en una generación real de 64 tokens; aún no es una comparación controlada con llama.cpp |
| RustingStrata CUDA API | Qwen3.5-4B, GGUF Q4_K_M | 3/3 peticiones HTTP 200 | Mediana 0,8384 s por petición; API sin tok/s interno ni TTFT |
| RustingStrata bench | Qwen3.5-4B, GGUF Q4_K_M | Medición de prefill separada | 915,3 tok/s PP=128; 986,5 tok/s PP=512 |

### Intentos sin inferencia completada o descartados

- **Magnitude 0.2.10 + Qwen3.5-4B:** artefactos descargados y hashes verificados; la CLI no reconoció el modelo en el catálogo. Se cerró sin inferencia y sin métricas de rendimiento.
- **KTransformers:** descartado explícitamente para esta ronda; no compilar ni instalar. No se encontró una ruta documentada/operativa para Qwen3.5-4B en la rama examinada.
- **SGLang:** descartado explícitamente; no instalar, no descargar el checkpoint AWQ ni ejecutar benchmark.
- **Mistral.rs:** se consideró dentro del plan de comparación de cuatro motores, pero la evidencia consolidada disponible no contiene una ejecución medida atribuible a Mistral.rs. No se le asignan resultados.
- **Qwen3.5-4B AWQ W4A16:** se inspeccionó la ficha del candidato, pero no se debe interpretar como inferencia ejecutada ni como checkpoint descargado.
- **Qwen3-30B-A3B-Instruct IQ3_XXS:** la prueba MoE se completó posteriormente en llama.cpp CUDA y RustingStrata; véase §17. La comparación entre motores todavía no es estrictamente equivalente.
- **Primer arranque TensorFold Qwen3.5-4B:** hubo un intento rechazado por el presupuesto de memoria CUDA; una ejecución posterior con contexto 512 sí completó la inferencia.

## 2. Equipo y entorno común

Configuración observada durante las pruebas principales:

- Sistema operativo: Ubuntu nativo, arquitectura x86_64.
- CPU: Intel Core i7-12650H, 12.ª generación; 16 CPU lógicas.
- RAM: 14 GiB (en otra salida de Magnitude, 14,8 GB según su propia presentación).
- GPU: NVIDIA GeForce RTX 3050 Laptop, 4 GiB VRAM (4096 MiB).
- Driver NVIDIA: 580.178.04.
- CUDA indicada por `nvidia-smi`: 13.0.
- En una comprobación de Magnitude: aproximadamente 3,7 GiB de VRAM reportados por la aplicación; 9,3/14,8 GB de RAM usados y 5,5 GB libres en ese momento.
- Los valores de memoria total de GPU, VRAM asociada al proceso y memoria libre no son métricas intercambiables. Las capturas instantáneas posteriores a inferencia tampoco representan el pico durante generación.

Comprobaciones generales utilizadas durante la sesión:

~~~bash
free -h
nvidia-smi
pgrep -af 'magnitude|Magnitude' || true
systemctl is-active magnitude.service || true
~~~

El comando de estado de servicio anterior se usó para comprobar si Magnitude seguía activo y si quedaban procesos residuales antes de continuar con pruebas de otros motores. No se debe deducir de ello una comparación de rendimiento.

## 3. Modelos, artefactos y cuantizaciones

### 3.1 Qwen3.5-2B — TensorFold

- Repositorio/modelo: `mlx-community/Qwen3.5-2B-MLX-4bit`.
- Formato: pesos MLX cuantizados a 4 bits; group size 64 según la ficha de la prueba.
- Endpoint local observado: `http://127.0.0.1:18083/v1`.
- La ruta `/v1/models` respondió correctamente.
- Contexto configurado en la prueba documentada: 1024.
- Salidas limitadas mediante `max_tokens`.

### 3.2 Qwen3.5-4B — TensorFold

- Repositorio/modelo: `mlx-community/Qwen3.5-4B-MLX-4bit`.
- Formato: pesos MLX 4-bit, group size 64 según el registro de prueba.
- Endpoint local observado: `http://127.0.0.1:18084/v1`.
- Contexto de la prueba local de referencia: 512.
- Tiempo de carga observado en una ejecución: 6,4 s.
- En otro registro separado de arranque/API, la carga se estimó en aproximadamente 9,9 s. No mezclar ambos tiempos como si fueran la misma ejecución o el mismo límite de medida.
- La latencia de prefill se registró en milisegundos, pero no siempre se conservó la velocidad de prefill en tok/s.

### 3.3 Qwen3.5-4B — llama.cpp CUDA

- Archivo: `~/llama.cpp-cuda/models/qwen3.5-4b-Q4_K_M.gguf`.
- Tamaño aproximado: 2,59 GiB.
- Cuantización: GGUF Q4_K_M / Q4_K - Medium.
- SHA-256 verificado: `c3c2cf023efdbd913c2363a14d5c7266db5e05c4602f1c0790eaed567d8aff23`.
- Proyecto: `~/llama.cpp-cuda`.
- Binario: `build-cuda/bin/llama-cli`.
- Build registrada: `b11740-6fa4f6cd3`.

Comando de inferencia CLI conservado:

~~~bash
cd ~/llama.cpp-cuda

./build-cuda/bin/llama-cli \
  -m "$PWD/models/qwen3.5-4b-Q4_K_M.gguf" \
  -ngl 99 \
  -c 512 \
  -n 128 \
  --temp 0 \
  --no-display-prompt \
  -p "Responde en español en una frase: ¿qué ventajas tiene ejecutar un modelo de IA localmente?" \
  --chat-template-kwargs '{"enable_thinking":false}'
~~~

### 3.4 Qwen3.5-4B — RustingStrata

- Artefacto: `qwen3.5-4b-Q4_K_M.gguf`.
- Cuantización GGUF Q4_K_M.
- Se usó para la comparación por API y en un benchmark separado de prefill.
- La API no expuso la velocidad interna de generación ni TTFT al cliente de la prueba.
- La estimación de 32 tokens / tiempo total de petición se conserva solo como estimación de pared, nunca como tok/s interno del motor.

### 3.5 Qwen3.5-4B — Magnitude

Artefactos descargados desde `unsloth/Qwen3.5-4B-MTP-GGUF`, revisión `86835bf9949e4d14d6860f7910b1340ad4f271a9`:

| Archivo | Tamaño | SHA-256 |
|---|---:|---|
| `Qwen3.5-4B-UD-Q4_K_XL.gguf` | 2.990.664.000 bytes | `d2bfbee4de17c74e6308a4dc750be4c2271f92ae2df1e28f5c5afa0dcdb6fccc` |
| `mmproj-BF16.gguf` | 675.569.216 bytes | `169ee40fb1e234ff38b2d814eb8633611a54b6f941f11b700d96dec02cb44ddf` |

Total de ambos: 3.666.233.216 bytes. También se descargó la dependencia DFlash:

- Repositorio: `magnitudedev/Qwen3.5-4B-DFlash-GGUF`.
- Revisión: `0094e74a88676605d53b79c7c3d26096335c9746`.
- Archivo: `Qwen3.5-4B-DFlash-Q8_0.gguf`.
- Tamaño: 685.134.176 bytes.

Los hashes se verificaron con `sha256sum`; los snapshots apuntaban a blobs válidos. **Q4_K_XL no es la misma cuantización que Q4_K_M** usada por llama.cpp/RustingStrata.

### 3.6 Candidato Qwen3.5-4B AWQ

Se inspeccionó el candidato `matchachoco/Qwen3.5-4B-QuantStudy-AWQ-W4A16`:

- Arquitectura declarada: `Qwen3_5ForConditionalGeneration`.
- Repositorio de 3,81 GB.
- `model.safetensors`: 3.786.643.328 bytes.
- Cuantización declarada: compressed-tensors, pack-quantized INT4, grupo 128, con capas excluidas.

Esta ficha solo registra el examen de metadatos del candidato. No se presenta como modelo ejecutado. La ruta SGLang/AWQ quedó descartada por decisión expresa; no descargar ese checkpoint ni instalar SGLang para esta ronda.

### 3.7 Qwen3-30B-A3B-Instruct — IQ3_XXS

El artefacto se descargó y ejecutó en la sesión MoE del 2026-10-21:

- Modelo: Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf.
- Ruta: ~/benchmarks/qwen3-30b-a3b-iq3-xxs/.
- Arquitectura GGUF: qwen3moe; aproximadamente 30,53 B parámetros, 48 bloques, 128 expertos y 8 activos por token.
- Cuantización: IQ3_XXS; tamaño aproximado 12,2 GB / 11,37 GiB.
- SHA-256: 292daa2b66aec59d075532d0bcf05010bf4a3b012a4216c28dc021b73d1e9ab4.
- Se verificó inferencia real con llama.cpp CUDA y RustingStrata CUDA. Los comandos, fallos de offload, parámetros y resultados se recogen en §17.

No debe confundirse este modelo MoE de 30B con Qwen3.5-4B.

## 4. Resultados TensorFold: Qwen3.5-2B y 4B

### 4.1 Qwen3.5-2B

| Métrica | Muestra corta | Muestra larga |
|---|---:|---:|
| Tokens de salida solicitados | 32 | 128 |
| Generación | 95,08 tok/s | 105,71 tok/s |
| Tiempo de generación registrado | 0,326 s | 1,201 s |
| TTFT | 88,2 ms | 94,1 ms |
| VRAM asociada al proceso | aprox. 2.388 MiB | aprox. 2.388 MiB |
| VRAM total ocupada en capturas | 2.411 / 4.096 MiB | 2.411 / 4.096 MiB |
| Contexto configurado | 1024 | 1024 |

La respuesta fue una inferencia real en español; las muestras acabaron limitadas por `max_tokens`. La velocidad de prefill en tok/s no quedó registrada.

### 4.2 Qwen3.5-4B

| Métrica | Muestra A | Muestra B |
|---|---:|---:|
| Tokens de salida solicitados | 64 | 128 |
| Generación | 53,64 tok/s | 53,42 tok/s |
| Latencia de prefill | 190 ms | 209 ms |
| TTFT | 193 ms | 212 ms |
| VRAM asociada al proceso | aprox. 3.120 MiB | aprox. 3.120 MiB |
| VRAM total ocupada en capturas | 3.143 / 4.096 MiB | 3.143 / 4.096 MiB |
| Contexto configurado | 512 | 512 |

La velocidad de prefill en tok/s no quedó registrada en estas muestras. Se documentó una carga de modelo de 6,4 s en una ejecución. La respuesta fue una inferencia real en español.

### 4.3 Intento inicial rechazado

Un primer arranque de Qwen3.5-4B en TensorFold fue rechazado con el presupuesto de memoria configurado en `TENSORFOLD_CUDA_MEMORY_LIMIT_GB=3.4` y una reserva de 0,5 GiB. Después se registró una ejecución CUDA completada con contexto 512. El primer fallo es una incidencia de configuración/presupuesto, no evidencia de incompatibilidad absoluta del modelo con TensorFold.

## 5. Resultados llama.cpp CUDA

Ejecución CLI del 2026-10-20:

| Campo | Resultado |
|---|---|
| Modelo | Qwen3.5-4B GGUF Q4_K_M |
| Contexto | 512 |
| Máximo de salida | 128 tokens |
| Temperatura | 0 |
| Capas GPU solicitadas | `-ngl 99` |
| Prefill / procesamiento del prompt | **141,2 tok/s** |
| Generación | **42,4 tok/s** |
| VRAM total ocupada en captura posterior | 2.831 / 4.096 MiB |
| VRAM del proceso `llama-cli` | 2.808 MiB |
| Temperatura GPU en la captura | 42 °C |
| Utilización instantánea | 0 %, captura posterior a la generación |
| SHA-256 del GGUF | Verificado; véase §3.3 |

La respuesta en español fue coherente. La utilización instantánea del 0 % no describe la fase de inferencia: la captura se tomó después. La ejecución confirma inferencia local CUDA con `llama-cli`, no por sí sola la integración con Magnitude, TensorFold, ODS o LEONES Runtime.

### Variación de prefill en ejecuciones históricas

Se conservaron otras cifras de procesamiento de prompt para llama.cpp: aproximadamente 118,14, 51,99 y 22,31 tok/s en una ejecución/histórico con cargas diferentes; otra ejecución registró 141,2 tok/s. No se dispone aquí del protocolo completo de cada valor para normalizarlos. Por tanto, no deben promediarse ni compararse como si provinieran del mismo prompt y condiciones.

Tiempo de carga observado en un log: aproximadamente 1,83 s desde el inicio de `load_model` (cerca de 0,188 s) hasta el mensaje “model loaded” (cerca de 2,019 s). Es una medida separada de la latencia de una petición servida por un proceso ya iniciado.

## 6. Benchmark API de tres motores — 2026-10-20

### Protocolo y alcance

- Script: `~/benchmarks/benchmark_qwen35_4b_three_engines_fixed_v2.sh`.
- Directorio de ejecución: `~/qwen35-4b-benchmark-fixed-20261020-215243`.
- Equipo: Ubuntu x86_64, i7-12650H, 16 CPU lógicas, 14 GiB RAM, RTX 3050 Laptop 4 GiB, driver 580.178.04, CUDA 13.0.
- Tres iteraciones medidas por motor, con warm-up separado y excluido del JSONL medido.
- 32 tokens de salida por petición.
- Las nueve peticiones medidas respondieron HTTP 200 y terminaron en el límite de 32 tokens (`finish_reason=length`).
- Prompt y parámetros estaban en los artefactos locales de esa ejecución; el informe de GitHub no incluye el JSONL crudo ni los logs completos.

Comando de ejecución conservado:

~~~bash
cd ~/benchmarks
bash ~/benchmarks/benchmark_qwen35_4b_three_engines_fixed_v2.sh
~~~

### Resumen de medianas

| Motor | Artefacto | Tiempo total mediano | Velocidad de salida mediana | TTFT mediano |
|---|---|---:|---:|---:|
| TensorFold CUDA | `mlx-community/Qwen3.5-4B-MLX-4bit` | **0,7066 s** | **54,708 tok/s** | **0,1303 s** |
| llama.cpp CUDA | `qwen3.5-4b-Q4_K_M.gguf` | 0,8680 s | 47,646 tok/s | No disponible como medición cliente comparable |
| RustingStrata CUDA | `qwen3.5-4b-Q4_K_M.gguf` | 0,8384 s | No expuesta por API | No expuesto por API |

TensorFold registró prefill aproximado de 228–232 tok/s en este conjunto de peticiones. No confundir esta métrica con la latencia de prefill de las pruebas locales anteriores.

### Resultados por iteración

| Motor | Iteración | Velocidad de salida | Tiempo total | TTFT |
|---|---:|---:|---:|---:|
| TensorFold | 1 | 54,663 tok/s | 0,7094 s | 0,1324 s |
| TensorFold | 2 | 54,708 tok/s | 0,7066 s | 0,1303 s |
| TensorFold | 3 | 54,771 tok/s | 0,7058 s | 0,1302 s |
| llama.cpp CUDA | 1 | 47,498 tok/s | 0,9544 s | N/D |
| llama.cpp CUDA | 2 | 47,646 tok/s | 0,8680 s | N/D |
| llama.cpp CUDA | 3 | 47,723 tok/s | 0,7578 s | N/D |
| RustingStrata | 1 | No expuesta | 0,8384 s | N/D |
| RustingStrata | 2 | No expuesta | 0,8381 s | N/D |
| RustingStrata | 3 | No expuesta | 0,8384 s | N/D |

La estimación aproximada de 38,17 tok/s para RustingStrata se calcula como 32 tokens divididos por el tiempo total mediano. **No es la velocidad interna de decodificación** y no se compara con el tok/s de salida expuesto por los otros motores.

### Incidencia del script

Las tres pruebas por motor sí terminaron correctamente. El script falló después, al generar el resumen, por un paréntesis de cierre extra en el fragmento Python de generación del informe (línea 302). El CSV y el Markdown se regeneraron a partir del `results.jsonl` ya existente; no se relanzaron los motores para reparar el resumen.

Artefactos locales del directorio de ejecución:

- `results.jsonl`
- `results.csv`
- `summary.md`
- `tensorfold-server.log`
- `llama-cpp-server.log`
- `rusting-strata-server.log`
- `environment.txt`
- `nvidia-smi-before.txt`
- `nvidia-smi-after.txt`
- `benchmark.log`

Los registros crudos y logs se han documentado como locales; no se afirma que estén versionados en GitHub.

### Comparabilidad

TensorFold usó un artefacto MLX-4bit; llama.cpp y RustingStrata usaron GGUF Q4_K_M. Es una comparación práctica de runtime, no una comparación estricta con artefacto idéntico. Tres iteraciones y una salida limitada a 32 tokens son una instantánea inicial, no una prueba de generación larga, contexto largo, concurrencia, calidad, consumo energético ni significación estadística.

En la respuesta de llama.cpp apareció un envoltorio vacío `<think>...</think>` pese a los ajustes de plantilla/razonamiento desactivado; el texto de respuesta fue coherente en español.

## 7. Benchmark separado RustingStrata: prefill

Se documentó una ejecución separada de `strata bench`:

- Contexto: 1024.
- `--tg 64 --reps 3`.
- PP=128: **915,3 tok/s**.
- PP=512: **986,5 tok/s**.
- Tiempo de carga: no registrado en la evidencia disponible.

Estas cifras proceden del harness propio de RustingStrata y tamaños de prompt/batch distintos. No se deben ordenar directamente frente a las cifras de prefill API de TensorFold ni a las cifras históricas de llama.cpp: no se ha demostrado que midan la misma fase con el mismo protocolo.

## 8. Magnitude 0.2.10: intento bloqueado

### Estado del runtime

- CLI instalada: `0.2.10`.
- `magnitude update check` y `magnitude update status`: la CLI se declaraba actualizada.
- Servicio: `Runtime Ready`.
- Dirección local: `http://127.0.0.1:10100`.
- Modelo activo: `None`.
- `magnitude models status`: no había modelos locales.
- `/var/lib/magnitude/state/models.json`: `slots: {}`, `recentModels` vacío y `favorites: []`.

### Comprobaciones registradas

~~~bash
magnitude --version
magnitude update check
magnitude update status
magnitude models status
magnitude status
magnitude catalog show qwen3.5-4b
magnitude catalog show 'qwen3.5-4b:gguf:q4'
magnitude models load 'hf:unsloth/Qwen3.5-4B-MTP-GGUF/Qwen3.5-4B-UD-Q4_K_XL.gguf'
~~~

Resultados relevantes:

- `magnitude catalog show qwen3.5-4b`: `Invalid catalog model ID`.
- `magnitude catalog show 'qwen3.5-4b:gguf:q4'`: `Unknown catalog model`.
- Intento de carga por ruta `hf:...`: `Invalid catalog model ID`.
- `magnitude models status`: “No local models are on this computer”.
- `magnitude status`: runtime listo, modelo activo `None`.
- El inventario interno sí contenía Qwen3.5-4B como `available`, arquitectura `qwen35`, 4.326.350.848 parámetros y operaciones declaradas `load/unload/delete`; eso no implica que la CLI pudiera cargarlo.
- El catálogo publicado evaluó 73/73 modelos, pero listaba solo Gemma 4 E2B Q4 QAT y MiniCPM5 1B Q4/Q8 como compatibles. Qwen no aparecía.

**Conclusión:** se verificó la integridad de los artefactos, pero no se activó el modelo. No hay métricas Magnitude de prefill, tok/s, TTFT, duración de inferencia o VRAM atribuibles a una inferencia Qwen. La causa exacta no quedó demostrada; no atribuir el fallo automáticamente a memoria o incompatibilidad intrínseca del modelo.

Restricciones de mantenimiento registradas: no borrar los blobs verificados, no volver a descargar innecesariamente los artefactos, no editar manualmente `models.json` ni `catalog-affiliations.json`, y no reinstalar a ciegas una CLI que declara estar actualizada. Reabrir solo cuando haya una ruta de carga/catalogación corregida y medir una petición real.

## 9. KTransformers y SGLang: descartes explícitos

### KTransformers

- Rama inspeccionada: `qwen3.5`.
- No se identificó una ruta operativa/documentada para ejecutar Qwen3.5-4B en la configuración local.
- La documentación visible se centraba en Qwen3.5 MoE-400B/SGLang-KT; el flujo clásico `optimize_and_load_gguf` no demostró compatibilidad con `Qwen3_5ForConditionalGeneration`/Qwen3.5-4B.
- Recursos disponibles en la comprobación: 14 GiB RAM, aproximadamente 8,3 GiB disponibles en ese momento; RTX 3050 4 GiB con alrededor de 3,75 GiB libres.
- Decisión explícita: KTransformers descartado para esta ronda. No compilar ni instalar, y no contarlo como motor medido.

No se encontró en el registro consolidado un comando de inferencia exitoso ni una medición de Qwen3.5-4B con KTransformers. Por ello, no se publican tok/s, prefill, TTFT ni VRAM como resultados de ese motor.

### SGLang

Decisión explícita: descartado. No instalar SGLang, no descargar el checkpoint AWQ y no ejecutar benchmark. No hay inferencia medida con SGLang en esta ronda.

## 10. Mistral.rs: estado de la evidencia

En la planificación se habló de una comparación con cuatro motores: TensorFold, llama.cpp CUDA, RustingStrata y Mistral.rs. Sin embargo, el informe reproducible de tres runtimes contiene únicamente TensorFold, llama.cpp y RustingStrata. En el material consolidado no hay logs, comando final ni resultados de Mistral.rs que permitan certificar una ejecución completada. Se registra como **sin medición confirmada**, no como fallo técnico ni como incompatibilidad.

## 11. Otros comandos y observaciones de diagnóstico

### Inspección de Magnitude

~~~bash
magnitude docs cli
magnitude catalog recommendations
magnitude hardware
magnitude catalog show qwen3.5-4b
~~~

Se consultaron la documentación de CLI, recomendaciones, hardware y ficha del catálogo. La ficha del catálogo no resolvió la ruta de carga: el ID no fue aceptado por la CLI.

### Inspección de la ayuda y estado de modelos

~~~bash
magnitude models --help
magnitude docs --help
magnitude models load --help
magnitude catalog pull --help
magnitude models status
cat /var/lib/magnitude/config.json
~~~

También se inspeccionaron `/var/lib/magnitude/state/models.json` y el estado de servicio. La CLI reportó ausencia de modelos locales activos.

### Comprobación de proceso y recursos antes de cambiar de motor

~~~bash
sudo systemctl stop magnitude.service

echo "===== ESTADO DEL SERVICIO ====="
systemctl is-active magnitude.service || true

echo
echo "===== PROCESOS RESIDUALES ====="
pgrep -af 'magnitude|Magnitude' || true

echo
echo "===== RAM Y SWAP ====="
free -h

echo
echo "===== VRAM ====="
nvidia-smi
~~~

La secuencia se usó para parar Magnitude y comprobar que no quedaran procesos consumiendo RAM/VRAM antes de continuar. La autenticación de `sudo` se solicitó en la terminal. No se deben inferir de esta comprobación cifras de benchmark.

## 12. Interpretación conjunta

1. En las muestras locales de TensorFold, Qwen3.5-2B alcanzó 95,08–105,71 tok/s y Qwen3.5-4B 53,42–53,64 tok/s.
2. En la ejecución CLI conservada de llama.cpp, Qwen3.5-4B Q4_K_M alcanzó 42,4 tok/s de generación y 141,2 tok/s de procesamiento de prompt.
3. En la comparación API de 32 tokens, TensorFold obtuvo la mediana de velocidad de salida más alta entre las métricas expuestas (54,708 tok/s), frente a 47,646 tok/s en llama.cpp.
4. RustingStrata devolvió respuestas correctas, pero la API no expuso el tok/s interno ni TTFT. La estimación a partir del tiempo total no equivale a throughput de decodificación.
5. Los artefactos MLX-4bit y GGUF Q4_K_M son distintos. Los resultados no demuestran que toda diferencia se deba únicamente al motor.
6. Magnitude no completó inferencia; su caso es un bloqueo observable de catálogo/CLI, no un resultado de velocidad cero.
7. KTransformers y SGLang quedaron fuera por decisión explícita. Mistral.rs no tiene una ejecución medida confirmada en el material consolidado.
8. Qwen3-30B-A3B-Instruct IQ3_XXS cuenta con inferencia medida en llama.cpp CUDA y RustingStrata (§17); las métricas entre motores siguen pendientes de una comparación controlada.
9. No hay evidencia en estos registros de integración E2E con ODS o LEONES Runtime; son pruebas de motores/modelos individuales.

## 13. Límites de la evidencia y datos que faltan

- Los logs completos y el JSONL de la ejecución API siguen en el directorio local `~/qwen35-4b-benchmark-fixed-20261020-215243`; el informe no afirma que estén subidos al repositorio.
- No se conserva en este informe el texto íntegro de cada respuesta generada.
- Algunas pruebas históricas no tienen el prompt exacto, revisión del artefacto, temperatura, contexto o método de temporización completamente documentados.
- La velocidad de prefill de TensorFold en las pruebas locales 2B/4B no quedó registrada como tok/s.
- TTFT de llama.cpp en la comparación API no estaba disponible en el parser/medición de cliente utilizada.
- TTFT y tok/s interno de RustingStrata no fueron expuestos por la API.
- No se dispone de medición pico de VRAM durante toda la generación para todos los motores.
- No se han medido de forma homogénea consumo energético, calidad, contexto largo, concurrencia ni rendimiento sostenido.
- No se debe mezclar tiempo de carga del modelo, TTFT de un servidor ya caliente, tiempo total de petición y tiempo de ejecución de un proceso CLI: son límites de medida distintos.

## 14. Protocolo recomendado para una siguiente ronda comparable

La próxima ronda debe conservar el estado de las pruebas anteriores y generar un nuevo directorio/ID de ejecución, sin sobrescribir la evidencia histórica.

- Fijar el mismo prompt, contexto 256 o 512, temperatura 0, límite de salida y plantilla.
- Registrar hash, tamaño, cuantización, revisión y ruta de cada artefacto.
- Hacer una carga/warm-up separado y al menos tres iteraciones medidas por motor.
- Separar tiempo de carga, TTFT, prefill tok/s, generación tok/s y duración total.
- Capturar VRAM antes, durante y después, además de RAM, versión/build, backend y argumentos.
- Ejecutar secuencialmente, con un solo motor de inferencia activo.
- Marcar como N/D toda métrica que la API o el runtime no exponga; no sustituirla por una estimación sin etiquetarla.
- Para comparación estricta, usar el mismo artefacto y cuantización siempre que cada runtime lo soporte. Si no, etiquetar el resultado como comparación práctica de configuraciones distintas.
- No reabrir KTransformers ni SGLang durante esta ronda, respetando la decisión de descartarlos.
- Tratar Qwen3-30B-A3B IQ3_XXS como experimento aparte de MoE y no como parte de la tabla Qwen3.5-4B.

La metodología interna de LEONES para evidencias de benchmark está documentada en `docs/runtime-benchmark-evidence-v1.1.md`.

## 15. Índice de informes y evidencias relacionados

- [Inventario comparativo TensorFold + llama.cpp + cierre Magnitude](../experimental/inventario-comparativo-qwen35-tensorfold-llamacpp-2026-10-20.md)
- [Benchmark API de tres runtimes y resultados por iteración](qwen35-4b-three-runtimes-2026-10-20.md)
- [CSV de las nueve peticiones medidas](qwen35-4b-three-runtimes-2026-10-20.csv)
- [Prueba Magnitude Qwen3.5-4B — 2026-10-21](magnitude-qwen35-4b-2026-10-21.md)
- [Prueba CLI llama.cpp CUDA Qwen3.5-4B](../experimental/qwen3.5-4b-llama-cpp-rtx3050.md)
- [Contrato/metodología de evidencias de benchmark LEONES](../runtime-benchmark-evidence-v1.1.md)

## 16. Historial de consolidación en GitHub

Commits de LEONES relacionados con la consolidación y las pruebas:

- [e595852 — consolidación inicial TensorFold y llama.cpp](https://github.com/robertosantosx2/LEONES/commit/e595852ede8f5708bab96e20f171a37f870f8274)
- [661b545 — métricas de prefill](https://github.com/robertosantosx2/LEONES/commit/661b545dd0ee2a2d4654d1bb4687daed41e96398)
- [fddc904 — prueba local Qwen3.5-4B con llama.cpp CUDA](https://github.com/robertosantosx2/LEONES/commit/fddc904e5a8f7b23ab0ed6583bf4ef57a394458d)
- [2db5093 — resultados de tres runtimes](https://github.com/robertosantosx2/LEONES/commit/2db50934017e3ab4257395cd9f27424a40f74e3e)
- [d34aff0 — CSV de resultados por iteración](https://github.com/robertosantosx2/LEONES/commit/d34aff0625d4124fe7fe3f6ba2fa616dd25bc2bb)
- [6d23a60 — índice de evidencias de runtime](https://github.com/robertosantosx2/LEONES/commit/6d23a604d20fad6cd0bee32c5db818cfbd5de6f6)
- [75f93ce — registro del intento Magnitude bloqueado](https://github.com/robertosantosx2/LEONES/commit/75f93ce440445231b83d6b153b9f779c56737b3a)
- [cc7b6c4 — cierre del intento Magnitude](https://github.com/robertosantosx2/LEONES/commit/cc7b6c42faa7266c3941022b3d216f278e7f95fe)

---
**Estado final de este informe:** consolidado con la evidencia disponible a 2026-10-21, incluida la prueba MoE de Qwen3-30B-A3B con llama.cpp CUDA y RustingStrata (§17). No se han inventado métricas para motores sin inferencia completada. Las pruebas futuras deben añadirse como nuevas ejecuciones, manteniendo los registros históricos y sus limitaciones.


## 17. Experimento MoE: Qwen3-30B-A3B IQ3_XXS en llama.cpp CUDA y RustingStrata — 2026-10-21

### 17.1 Objetivo y alcance

Esta sección añade las pruebas reales del modelo Qwen3-30B-A3B-Instruct-2507 IQ3_XXS al barrido previo. El foco fue verificar llama.cpp CUDA, medir generación con distintos valores de --n-gpu-layers, localizar el límite de offload de la RTX 3050 Laptop de 4 GiB, ejecutar RustingStrata con NVRTC compatible y conservar tanto los éxitos como los fallos.

No es aún una comparación perfectamente controlada entre motores: las pruebas iniciales usaron comandos y longitudes de salida distintos, y las dos tandas automatizadas de llama.cpp se ejecutaron en momentos diferentes. Los resultados se conservan por tanda y no se mezclan en una única mediana.

### 17.2 Hardware y artefacto

| Campo | Valor observado |
|---|---|
| SO | Ubuntu nativo, x86_64 |
| CPU | Intel Core i7-12650H, 12.ª generación |
| CPU lógicas | 16 |
| RAM física | 14 GiB |
| Swap | 32 GiB |
| GPU | NVIDIA RTX 3050 Laptop |
| VRAM física | 4096 MiB |
| VRAM utilizable informada por llama.cpp | aproximadamente 3768 MiB |
| Driver | NVIDIA 580.178.04 |
| CUDA de nvidia-smi | 13.0 |
| CUDA Toolkit del sistema | 13.4 |
| Modelo | Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf |
| Ruta | ~/benchmarks/qwen3-30b-a3b-iq3-xxs/Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf |
| Tamaño aproximado | 12,2 GB / 11,37 GiB |
| Arquitectura GGUF | qwen3moe |
| Parámetros | aproximadamente 30,53 B |
| Bloques | 48 |
| Expertos | 128; 8 activos por token |
| Cuantización | IQ3_XXS |
| SHA-256 | 292daa2b66aec59d075532d0bcf05010bf4a3b012a4216c28dc021b73d1e9ab4 |

Comprobaciones de sistema utilizadas:

~~~bash
free -h
nvidia-smi
pgrep -af 'magnitude|Magnitude' || true
systemctl is-active magnitude.service || true
~~~

Antes de cargar el modelo grande se indicó detener Magnitude y comprobar procesos residuales. Las capturas de memoria son muestras, no telemetría continua; el RSS máximo de /usr/bin/time es distinto de la VRAM.

### 17.3 Software y rutas

- Checkout llama.cpp: ~/llama.cpp-cuda.
- Binarios: ~/llama.cpp-cuda/build-cuda/bin/llama-cli, llama-server y llama-bench.
- Versión: 0.7.0-dev, build 11740, commit 6fa4f6cd3.
- Checkout RustingStrata: ~/rusting-strata-test.
- Binario: ~/rusting-strata-test/target/release/strata, versión 1.0.1.
- Checkout TensorFold: ~/tensorfold-test; no se confirmó en esta sesión una ejecución comparable de TensorFold con este modelo de 30B.

### 17.4 Validación inicial llama.cpp: CPU y offload pequeño

| Prueba | Configuración principal | Prefill / prompt | Generación | Resultado |
|---|---|---:|---:|---|
| llama-bench CPU | ngl=0, PP=128, TG=32, reps=3, threads=8 | 42,14 ± 24,48 tok/s | 1,39 ± 0,03 tok/s | RC 0 |
| llama-bench 1 capa | ngl=1, PP=128, TG=32, reps=3, threads=8 | 50,93 ± 30,10 tok/s | 1,43 ± 0,04 tok/s | RC 0 |
| CLI CPU | ngl=0 | 3,1 tok/s | 1,4 tok/s | 84,79 s; RC 0 |
| CLI 1 capa, primer intento | ngl=1 | 0,7 tok/s | 1,4 tok/s | 116,04 s; RC 0 |
| CLI 1 capa monitorizada | ngl=1 | 2,9 tok/s | 1,4 tok/s | 83,18 s; RC 0 |

El prefill varía considerablemente. No promediar llama-bench y CLI como si fueran el mismo harness.

Logs locales registrados:
- llama-bench-cpu-20261021.log
- llama-bench-ngl1-20261021.log
- llama-cpp-generate-cpu-20261021.log
- llama-cpp-generate-ngl1-20261021.log
- llama-cpp-ngl1-monitored-20261021.log
- llama-cpp-ngl1-gpu-20261021.csv

Estos archivos permanecen en el equipo de pruebas; este informe no afirma que se hayan subido a GitHub.

### 17.5 Configuración controlada de llama-cli

Los intentos controlados usaron los mismos parámetros, cambiando el valor de --n-gpu-layers:

~~~bash
cd "$HOME/llama.cpp-cuda" || exit 1

LLAMA="$HOME/llama.cpp-cuda/build-cuda/bin/llama-cli"
M="$HOME/benchmarks/qwen3-30b-a3b-iq3-xxs/Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf"

"$LLAMA" \
  --model "$M" \
  --n-gpu-layers 14 \
  --fit off \
  --ctx-size 1024 \
  --batch-size 64 \
  --ubatch-size 32 \
  --threads 8 \
  --predict 16 \
  --temp 0 \
  --seed 42 \
  --prompt "Responde brevemente en español: ¿qué es la inferencia local?" \
  --single-turn \
  --simple-io \
  --verbose
~~~

Para repetir otra configuración, cambiar solo --n-gpu-layers (0, 1, 8, 10, 12, 14, 15 o 16). El barrido automatizado mantuvo semilla, prompt, contexto, batch, ubatch e hilos constantes, y guardó un log por repetición.

Parámetros comunes:
- contexto: 1024;
- batch: 64;
- ubatch: 32;
- CPU threads: 8;
- temperatura: 0;
- semilla: 42;
- salida: 128 tokens en la primera tanda y 256 en la segunda;
- --fit off para impedir que el ajuste automático altere el offload solicitado.

### 17.6 Offload y límite de VRAM

Los logs verbose confirmaron la asignación real de capas a GPU.

| Capas solicitadas | Capas GPU reportadas | Buffer de modelo CUDA | KV CUDA | Cómputo CUDA | Estado |
|---:|---:|---:|---:|---:|---|
| 8 | 8/49 | 1885,45 MiB | 14 MiB | 86,25 MiB | Carga correcta |
| 12 | 12/49 | 2819,27 MiB | 22 MiB | 86,25 MiB | Carga correcta |
| 14 | 14/49 | 3290,68 MiB | 26 MiB | 86,25 MiB | Carga correcta |
| 15 | 15/49 | 3521,88 MiB | 28 MiB | 86,25 MiB | Carga correcta |
| 16 | — | reserva de 3753,09 MiB fallida | — | — | CUDA OOM |

Con 8 capas, el buffer del modelo mapeado en CPU fue de 9759,88 MiB. El log mostró una advertencia no fatal de discrepancia en CUDA_Host compute buffer: 4,1376 MiB frente a 1,0636 MiB esperados.

El intento de 16 capas falló tanto en un primer arranque de llama-server como en llama-cli controlado, con cudaMalloc failed: out of memory. La ejecución controlada pidió 3753,09 MiB, casi todo el presupuesto CUDA utilizable informado por llama.cpp. Empíricamente, 15 fue el mayor número de capas probado que cargó en esta configuración; eso no significa que sea la opción más rápida ni que tenga margen suficiente para otros contextos/procesos.

Log del fallo controlado: llama-cli-ngl16-controlled-20261021.log.

### 17.7 Barrido automatizado de capas

Script local usado: ~/benchmarks/qwen3-30b-a3b-iq3-xxs/benchmark-ngl.sh. Barrió las capas (0 1 8 10 12 14 15 16), guardó logs individuales, CSV y resumen. Se ejecutó en dos tandas:

- benchmark-ngl-20261021-212122: 2 repeticiones, salida configurada en 128 tokens.
- benchmark-ngl-20261021-213920: 3 repeticiones, salida configurada en 256 tokens.

Comandos de ejecución y análisis:

~~~bash
bash "$HOME/benchmarks/qwen3-30b-a3b-iq3-xxs/benchmark-ngl.sh"
python3 "$HOME/benchmarks/qwen3-30b-a3b-iq3-xxs/analyze-benchmarks.py"
~~~

El código original completo de benchmark-ngl.sh y los logs no se versionaron en este cambio. Los parámetros efectivos y resultados observados se registran aquí. El analizador local genera benchmark-results-corrected.csv.

#### Tanda 1: 2 repeticiones, 128 tokens de salida

| Capas GPU | Rep. 1 tok/s | Rep. 2 tok/s | Mediana tok/s | Prefill mediano tok/s | RSS máximo |
|---:|---:|---:|---:|---:|---:|
| 0 | 1,33 | 1,40 | 1,36 | 4,51 | 11,32 GiB |
| 1 | 1,39 | 1,61 | 1,50 | 6,17 | 11,62 GiB |
| 8 | 1,74 | 1,73 | 1,73 | 7,28 | 11,68 GiB |
| 10 | 1,80 | 1,78 | 1,79 | 5,28 | 11,36 GiB |
| 12 | 1,71 | 1,92 | 1,81 | 6,42 | 11,48 GiB |
| 14 | 1,90 | 2,02 | 1,96 | 8,50 | 11,58 GiB |
| 15 | 2,21 | 2,10 | 2,16 | 7,56 | 11,63 GiB |
| 16 | Fallo | — | — | — | No comparable |

#### Tanda 2: 3 repeticiones, 256 tokens de salida

| Capas GPU | Rep. 1 tok/s | Rep. 2 tok/s | Rep. 3 tok/s | Mediana tok/s | Prefill mediano tok/s | RSS máximo |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 1,40 | 1,70 | 1,63 | 1,63 | 7,82 | 11,85 GiB |
| 1 | 1,64 | 1,51 | 1,50 | 1,51 | 11,33 | 11,74 GiB |
| 8 | 1,66 | 1,88 | 1,74 | 1,74 | 7,61 | 11,74 GiB |
| 10 | 1,86 | 1,76 | 1,74 | 1,76 | 7,24 | 11,54 GiB |
| 12 | 1,78 | 2,00 | 2,15 | 2,00 | 8,28 | 11,73 GiB |
| 14 | 2,03 | 1,97 | 1,95 | 1,97 | 8,05 | 11,74 GiB |
| 15 | 1,93 | 1,94 | 1,86 | 1,93 | 10,18 | 11,74 GiB |
| 16 | Fallo | — | — | — | — | No comparable |

Las velocidades de prefill son las impresas por cada log. El RSS procede de /usr/bin/time, no de VRAM. Las ejecuciones fallidas de 16 capas se excluyen de las medianas.

#### Error del analizador y corrección

El primer analizador devolvió el mismo valor para prefill y generación porque el patrón eval time también coincidía con prompt eval time. Aquellas medianas iniciales eran inválidas y no deben citarse.

Se verificó una ejecución real:
- prompt: 24 tokens, 2326,72 ms, 10,31 tok/s;
- generación: 76 tokens, 38761,43 ms, 1,93 tok/s.

El analizador se reemplazó para procesar líneas diferentes: una que contiene prompt eval time y otra que contiene | eval time =, excluyendo la línea del prompt. El CSV corregido también separa las tandas, para no mezclar ejecuciones de 128 y 256 tokens. Las tablas anteriores son la salida del analizador corregido.

#### Interpretación provisional

- 8 capas mejora respecto a CPU puro; las ganancias mayores aparecen entre 12 y 15 capas.
- En la tanda larga, 12 capas logra la mediana más alta: 2,00 tok/s, rango 1,78–2,15.
- 14 capas es más consistente en esa tanda: 1,95–2,03 tok/s, mediana 1,97.
- 15 capas logra 2,16 tok/s de mediana en la tanda corta, pero cae a 1,93 en la larga; no es ganador universal.
- 16 capas falla por OOM.
- RSS de 11,5–11,9 GiB de 14 GiB sugiere posible presión de memoria. No se conservó telemetría de swap por repetición, por lo que no se atribuye la variabilidad exclusivamente al swap.
- Siguiente paso: usar 14 capas como referencia conservadora y comparar 12 frente a 14 con al menos cinco repeticiones, alternando el orden. No repetir el barrido entero salvo que cambien contexto, modelo o estado de memoria.

### 17.8 RustingStrata: solución NVRTC y mediciones

La primera ejecución GPU de RustingStrata encontró una incompatibilidad PTX: NVRTC 13.4 del sistema generó PTX .version 9.4, rechazado por el driver con CUDA_ERROR_UNSUPPORTED_PTX_VERSION. Se resolvió aislando bibliotecas NVRTC 13.0 de:

~/rusting-strata-test/vendor/nvrtc13/root/usr/local/cuda-13.0/targets/x86_64-linux/lib/

La solución usó LD_LIBRARY_PATH y XDG_CACHE_HOME temporales; no sustituyó bibliotecas del sistema. No se ejecutaron git clean/reset ni se eliminó vendor/.

| Prueba | Parámetros / configuración | Prefill | Generación | Resultado |
|---|---|---:|---:|---|
| Strata CPU smoke | PP=128, TG=32, reps=1, threads=8 | 0,4 tok/s | 0,4 tok/s | RC 0 |
| Strata GPU benchmark | NVRTC 13.0, reps=3 | PP=128: 48,0 tok/s (35,8–55,1) | TG=32: 11,6 tok/s (10,2–12,7) | RC 0 |
| Strata GPU generación | prompt 25 tokens; salida 64 tokens | 6,78 tok/s | 7,74 tok/s | RC 0; 18,35 s total |

Logs:
- strata-gpu-nvrtc13-reps3-20261021.log
- strata-generate-gpu-nvrtc13-20261021.log
- strata-cpu-smoke-20261021.log

Durante generación GPU, el plan registró:
- pesos + estado + scratch: 832 MB;
- KV: 96 MB para contexto 1024;
- prefill: 36 MB;
- slots de expertos: 2039 MB;
- expertos residentes: 1160 de 6144;
- hit rate de expertos: aproximadamente 24,9 % (25.681 misses);
- 64 cambios de caché;
- cómputo CPU de expertos: 90,1 % del tiempo de generación;
- RSS máximo: 8.089.292 KiB (aprox. 7,72 GiB).

strata bench y la generación de 64 tokens no son el mismo workload que el barrido llama.cpp. Los 7,74 tok/s son prometedores para este MoE y esta estrategia de caché, pero corresponden a una generación real individual, no a una mediana directamente comparable.

### 17.9 Otros intentos de offload y servidor

- Un primer intento de llama-server con 16 capas falló durante la reserva de VRAM. Ese log no conserva todos los argumentos con precisión suficiente; no se infieren otros parámetros a partir de él.
- El caso se repitió con llama-cli controlado (fit desactivado, contexto 1024, batch 64, ubatch 32, 8 hilos, salida 16 tokens, temperatura 0, semilla 42). 16 capas volvió a fallar.
- 12 y 14 capas cargaron correctamente en logs verbose de CLI.
- Con 8 capas, la mayor parte del modelo permaneció en CPU (buffer CPU mapeado 9759,88 MiB, buffer CUDA 1885,45 MiB). Más offload ayuda, pero el cálculo de expertos MoE y el ancho de banda siguen siendo cuellos de botella.

### 17.10 Conclusión específica de Qwen3-30B-A3B

1. La inferencia local real está verificada con llama.cpp CUDA y RustingStrata CUDA.
2. El máximo offload funcional observado en llama.cpp fue 15/49 capas, pero la mejor mediana de la tanda larga fue 12 capas; 14 capas presentó menor variabilidad.
3. 16 capas supera el presupuesto de VRAM para esta GPU/configuración.
4. RustingStrata llegó a 7,74 tok/s en una generación real de 64 tokens, con el coste principal en cálculo CPU de expertos y un hit rate de caché de aproximadamente 25 %. Es una observación de una ejecución, no una mediana directamente comparable.
5. La siguiente comparación controlada debe fijar prompt, longitud de salida, contexto, warm-up, repeticiones y método de medida de generación; además, registrar RAM/swap y VRAM durante cada ejecución.
6. Los logs, CSV y scripts permanecen en ~/benchmarks/qwen3-30b-a3b-iq3-xxs. Este informe incorpora la evidencia textual disponible, pero no sube automáticamente esos ficheros locales.


### 17.11 RustingStrata: repetición controlada de 16 tokens (21-10-2026)

Se añadió una prueba corta con el mismo archivo GGUF, el mismo prompt en español y un límite de 16 tokens de salida que la prueba controlada de llama.cpp. La ejecución usó GPU, contexto 1024, 8 hilos, temperatura 0, NVRTC 13.0 aislado y un directorio XDG_CACHE_HOME propio. El objetivo fue validar generación y observar caché; **16 tokens son insuficientes para una comparación robusta de rendimiento sostenido**.

SHA-256 del modelo: `292daa2b66aec59d075532d0bcf05010bf4a3b012a4216c28dc021b73d1e9ab4`.

Comando ejecutado en cada repetición:

~~~bash
/usr/bin/time -v -o "$OUT/time-$REP.txt" \
  ./target/release/strata generate \
    --model "$M" --gpu --ctx 1024 --threads 8 \
    --prompt "Responde brevemente en español: ¿qué es la inferencia local?" \
    -n 16 --temp 0 2>&1 | tee "$OUT/rep-$REP.log"
~~~

Entorno CUDA: `LD_LIBRARY_PATH` antepone `~/rusting-strata-test/vendor/nvrtc13/root/usr/local/cuda-13.0/targets/x86_64-linux/lib`; `XDG_CACHE_HOME=$OUT/cache`. Directorio de resultados: `~/benchmarks/qwen3-30b-a3b-iq3-xxs/rustingstrata-controlled-20261021`.

| Repetición | Prefill (tok/s) | Generación (tok/s) | Hit rate de expertos | Fallos de caché | Cambios de caché | RSS máximo |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2,99 | 6,67 | 19,9 % | 9.846 | 32 | 7.055.728 KiB (6,73 GiB) |
| 2 | 24,41 | 31,32 | 81,7 % | 2.248 | 0 | 6.062.680 KiB (5,78 GiB) |
| 3 | 26,44 | 25,66 | 81,8 % | 2.238 | 0 | 6.065.568 KiB (5,78 GiB) |

Las tres ejecuciones terminaron con código 0. La mediana aritméticamente correcta de las tres velocidades de generación es 25,66 tok/s, pero no representa una estimación estable de rendimiento sostenido: cada repetición generó solo 16 tokens y la primera tuvo una caché fría o mucho menos efectiva. Las repeticiones 2–3, con aproximadamente 81,8 % de aciertos, dieron 31,32 y 25,66 tok/s; con solo dos muestras calientes no debe presentarse su promedio como resultado definitivo. Strata informó que el cálculo CPU de expertos representó 91,7 %, 61,4 % y 67,7 % del tiempo de generación, respectivamente.

El resultado muestra que el estado de la caché cambia radicalmente la medición. No se debe comparar directamente la mediana de este test de 16 tokens con el barrido llama.cpp de 128/256 tokens ni con el test anterior de Strata de 64 tokens. Para comparación final, realizar warm-up explícito y al menos cinco repeticiones de una longitud común, reportando por separado primera ejecución y estado caliente.

### 17.12 RustingStrata: benchmark PP128/TG32 con tres repeticiones

Comando exacto:

~~~bash
LD_LIBRARY_PATH="$NVRTC${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
XDG_CACHE_HOME="$HOME/benchmarks/qwen3-30b-a3b-iq3-xxs/strata-bench-cache" \
/usr/bin/time -v ./target/release/strata bench \
  --model "$M" --gpu --pp 128 --tg 32 --reps 3 --threads 8
~~~

Resultado observado:

| Métrica | Resultado |
|---|---:|
| Prefill PP=128 | 58,7 tok/s |
| Rango de prefill reportado | 13,3–91,2 tok/s |
| Decode TG=32 | 12,3 tok/s |
| Rango de decode reportado | 8,7–14,3 tok/s |
| Hit rate de expertos | 19,9 % |
| Fallos de caché | 29.536 |
| Cambios de caché | 96 |
| Tiempo de pared | 24,79 s |
| RSS máximo | 8.976.260 KiB (8,56 GiB) |
| Estado | Exit status 0 |

El plan registró pesos+estado+scratch de 1.568 MB, KV de 384 MB para contexto 4096, prefill de 479 MB, slots de expertos de 1.557 MB y 886/6.144 expertos residentes. El rango amplio de PP y TG confirma variabilidad considerable; conservar los rangos es importante y no presentar solo la cifra central.

Log local: `~/benchmarks/qwen3-30b-a3b-iq3-xxs/rustingstrata-bench-20261021.log`.

**Conclusión actualizada:** RustingStrata completa correctamente tanto el benchmark como la generación controlada. El benchmark PP128/TG32 da 12,3 tok/s de decode (rango 8,7–14,3) y 58,7 tok/s de prefill (rango 13,3–91,2), mientras que la prueba corta de generación exhibe un gran efecto de caché. Estas pruebas no son todavía un cara a cara estricto con llama.cpp: cambian la longitud, el contexto y el modo de ejecución; el resultado caliente de 25–31 tok/s con solo 16 tokens no debe extrapolarse a generaciones largas.


### 17.13 Comparación controlada de generación: llama.cpp CUDA vs RustingStrata — 2026-10-21

#### Objetivo y protocolo

Se ejecutó el script local `~/benchmarks/benchmark-strata-vs-llamacpp.sh` para comparar ambos motores con el mismo GGUF y el mismo prompt visible. El script guardó logs, códigos de salida y `/usr/bin/time -v` por repetición en:

`~/benchmarks/qwen3-30b-a3b-iq3-xxs/head-to-head-20261021/`

Modelo y SHA-256 verificado:

- `Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf`
- `292daa2b66aec59d075532d0bcf05010bf4a3b012a4216c28dc021b73d1e9ab4`

Prompt visible común: `Responde brevemente en español: ¿qué es la inferencia local?`

Configuración llama.cpp:
- build `0.7.0-dev (11740, 6fa4f6cd3)`;
- `--n-gpu-layers 14 --fit off --ctx-size 1024`;
- `--batch-size 64 --ubatch-size 32 --threads 8`;
- `--predict 128 --temp 0 --seed 42 --single-turn --simple-io --verbose`.

Configuración RustingStrata:
- versión `1.0.1`;
- `generate --model "$M" --gpu --ctx 1024 --threads 8 --prompt "$PROMPT" -n 128 --temp 0`;
- NVRTC 13.0 vendorizado antepuesto a `LD_LIBRARY_PATH`;
- `XDG_CACHE_HOME` aislado bajo el directorio de resultados.

Se realizaron seis ejecuciones por motor, primero todas las de llama.cpp y luego todas las de Strata. Las doce terminaron con código 0. No se intercaló el orden entre motores, así que no se elimina el posible efecto de temperatura/carga del equipo.

#### Velocidad de generación y tokens producidos

| Motor | Rep. 1 | Rep. 2 | Rep. 3 | Rep. 4 | Rep. 5 | Rep. 6 | Mediana |
|---|---:|---:|---:|---:|---:|---:|---:|
| llama.cpp (tok/s) | 1,95 | 1,86 | 2,29 | 2,02 | 1,95 | 2,04 | 1,98 |
| RustingStrata (tok/s) | 14,34 | 29,94 | 30,08 | 30,90 | 31,89 | 29,33 | 30,01 |

La mediana de Strata en las ejecuciones 2–6 es **30,08 tok/s**. Frente a la mediana completa de llama.cpp (aprox. 1,98 tok/s), las cifras observadas corresponden a una razón de aproximadamente **15,1×** para las repeticiones posteriores de Strata. Es una comparación del rendimiento observado en este protocolo, no una garantía general para otros modelos o cargas.

Los tokens producidos no fueron iguales en todas las repeticiones:
- llama.cpp: 73 tokens en las seis ejecuciones; terminó por EOS antes del máximo de 128.
- RustingStrata: 128, 98, 128, 104, 128 y 128 tokens.

Por ello, `--predict 128` / `-n 128` es un límite, no una garantía de igual número de tokens emitidos. La velocidad tok/s se toma de la métrica de generación de cada motor; no se calcula dividiendo el límite solicitado por el tiempo total.

#### Datos por repetición

| Motor / rep. | Prefill registrado (tok/s) | Generación (tok/s) | Tokens generados | Tiempo total | RSS máximo |
|---|---:|---:|---:|---:|---:|
| llama.cpp 1 | 8,56 | 1,95 | 73 | 60,15 s | 11.769.532 KiB |
| llama.cpp 2 | 6,79 | 1,86 | 73 | 57,10 s | 11.826.788 KiB |
| llama.cpp 3 | 5,04 | 2,29 | 73 | 75,16 s | 11.959.852 KiB |
| llama.cpp 4 | 9,08 | 2,02 | 73 | 61,47 s | 12.281.072 KiB |
| llama.cpp 5 | 10,97 | 1,95 | 73 | 43,35 s | 12.312.544 KiB |
| llama.cpp 6 | 10,83 | 2,04 | 73 | 65,50 s | 12.308.524 KiB |
| Strata 1 | 11,71 | 14,34 | 128 | 17,71 s | 8.379.540 KiB |
| Strata 2 | 19,67 | 29,94 | 98 | 5,82 s | 7.337.164 KiB |
| Strata 3 | 20,03 | 30,08 | 128 | 6,84 s | 7.585.856 KiB |
| Strata 4 | 18,91 | 30,90 | 104 | 5,83 s | 7.289.712 KiB |
| Strata 5 | 18,96 | 31,89 | 128 | 6,47 s | 7.548.684 KiB |
| Strata 6 | 17,98 | 29,33 | 128 | 6,94 s | 7.504.556 KiB |

El tiempo total incluye carga y trabajo que no equivale exclusivamente a la decodificación. Los valores de RSS proceden de GNU `time` (KiB); no son VRAM. llama.cpp estuvo entre aproximadamente 11,22 y 11,74 GiB de RSS máximo. Strata estuvo en aproximadamente 7,99 GiB en la primera ejecución y entre 6,98 y 7,24 GiB en las ejecuciones 2–6.

#### Caché de expertos y efecto de calentamiento de Strata

| Repetición | Hit rate | Fallos de caché | Cambios de caché | CPU expert compute, proporción del tiempo de generación |
|---:|---:|---:|---:|---:|
| 1 | 30,8 % | 38.272 | 128 | 83,1 % |
| 2 | 79,0 % | 9.178 | 16 | 63,6 % |
| 3 | 77,9 % | 12.194 | 1 | 64,2 % |
| 4 | 80,2 % | 9.125 | 1 | 62,1 % |
| 5 | 78,6 % | 11.856 | 1 | 61,2 % |
| 6 | 78,8 % | 11.716 | 1 | 64,5 % |

La primera ejecución de Strata fue sustancialmente más lenta y tuvo una tasa de aciertos inferior. Las cinco siguientes rondaron el 78–80 % de aciertos. Esto es evidencia de un fuerte efecto del estado de caché en esta serie. No debe suponerse que el uso de un mismo `XDG_CACHE_HOME` por sí solo garantiza persistencia de caché entre procesos; lo demostrado son las métricas observadas en los logs de cada proceso.

#### Interpretación y límites

1. **Resultado principal:** mediana de generación de llama.cpp de aproximadamente 1,98 tok/s; mediana de RustingStrata de 30,01 tok/s incluyendo la primera ejecución y 30,08 tok/s para las repeticiones 2–6.
2. **Memoria:** Strata mostró menor RSS máximo en esta prueba: aproximadamente 7,0–7,24 GiB en las repeticiones posteriores, frente a 11,22–11,74 GiB en llama.cpp. RSS no equivale a RAM física exclusiva ni a VRAM.
3. **Entrada:** el texto visible del prompt fue igual, pero los motores contabilizaron 24 tokens en llama.cpp y 16 en Strata; las plantillas/tokenizadores internos no se han demostrado equivalentes.
4. **Terminación:** el número real de tokens difirió porque ambos motores pudieron detenerse antes del límite.
5. **Orden de ejecución:** se ejecutó primero la serie completa de llama.cpp y luego la de Strata, sin alternancia aleatoria ni medición de temperatura continua.
6. **Configuración:** ambos usaron GPU, contexto 1024 y ocho hilos, pero los controles de offload, batching y gestión de expertos son propios de cada motor. Es una comparación práctica de runtimes, no una comparación de kernels idénticos.
7. **Siguiente validación:** alternar el orden de los motores, registrar temperatura/uso GPU durante cada prueba, separar carga de decodificación, conservar salida/tokenización y ejecutar una tanda larga con un criterio explícito para EOS y caché fría/caliente.

Artefactos locales:
- Script: `~/benchmarks/benchmark-strata-vs-llamacpp.sh`
- Resultados: `~/benchmarks/qwen3-30b-a3b-iq3-xxs/head-to-head-20261021/`
- Logs: `llama/rep-*.log`, `strata/rep-*.log`
- Mediciones de recursos: `llama/time-*.txt`, `strata/time-*.txt`
- Códigos de salida: `llama/rc-*.txt`, `strata/rc-*.txt`

Estos artefactos permanecen en el equipo local; este apartado transcribe los resultados compartidos y no afirma que los logs se hayan subido al repositorio.
