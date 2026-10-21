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
| RustingStrata CUDA API | Qwen3.5-4B, GGUF Q4_K_M | 3/3 peticiones HTTP 200 | Mediana 0,8384 s por petición; API sin tok/s interno ni TTFT |
| RustingStrata bench | Qwen3.5-4B, GGUF Q4_K_M | Medición de prefill separada | 915,3 tok/s PP=128; 986,5 tok/s PP=512 |

### Intentos sin inferencia completada o descartados

- **Magnitude 0.2.10 + Qwen3.5-4B:** artefactos descargados y hashes verificados; la CLI no reconoció el modelo en el catálogo. Se cerró sin inferencia y sin métricas de rendimiento.
- **KTransformers:** descartado explícitamente para esta ronda; no compilar ni instalar. No se encontró una ruta documentada/operativa para Qwen3.5-4B en la rama examinada.
- **SGLang:** descartado explícitamente; no instalar, no descargar el checkpoint AWQ ni ejecutar benchmark.
- **Mistral.rs:** se consideró dentro del plan de comparación de cuatro motores, pero la evidencia consolidada disponible no contiene una ejecución medida atribuible a Mistral.rs. No se le asignan resultados.
- **Qwen3.5-4B AWQ W4A16:** se inspeccionó la ficha del candidato, pero no se debe interpretar como inferencia ejecutada ni como checkpoint descargado.
- **Qwen3-30B-A3B-Instruct IQ3_XXS:** se inició la descarga del artefacto GGUF para una futura prueba MoE; no hay en la evidencia disponible una inferencia completada ni métricas atribuibles a este modelo.
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

Se inició una descarga del artefacto GGUF para una futura prueba MoE:

~~~bash
hf download bartowski/Qwen_Qwen3-30B-A3B-Instruct-2507-GGUF \
  Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf \
  --local-dir "$HOME/benchmarks/qwen3-30b-a3b-iq3-xxs"
~~~

En el registro de terminal visible, Hugging Face avisó que las solicitudes eran anónimas. No hay evidencia consolidada de que la descarga terminara, de que se verificara el hash o de que el modelo llegara a cargar. No se debe confundir **Qwen3-30B-A3B** con **Qwen3.5-4B**: son modelos diferentes, y el primero es MoE.

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
8. La descarga de Qwen3-30B-A3B-Instruct IQ3_XXS es una pista de trabajo para una prueba posterior, no un benchmark concluido.
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
**Estado final de este informe:** consolidado con la evidencia disponible a 2026-10-21. No se han inventado mediciones para motores o modelos que no completaron inferencia. Las pruebas futuras deben añadirse como nuevas ejecuciones, manteniendo los registros históricos y sus limitaciones.
