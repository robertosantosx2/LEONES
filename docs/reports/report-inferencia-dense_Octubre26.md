# Inferencia en RTX 3050 4Gb oct26 — informe reproducible

**Fecha de pruebas:** 22 de octubre de 2026  
**Estado:** benchmark inicial documentado; resultados locales aún no adjuntos a este commit.  
**Equipo:** Intel Core i7-12650H, 14 GiB RAM, NVIDIA RTX 3050 Laptop (4 GiB VRAM), CUDA 13.0, driver 580.178.04, compute capability sm_86.

## Resumen ejecutivo

Se midieron dos configuraciones distintas en el mismo equipo:

1. **llama.cpp + Qwen3-30B-A3B-Instruct-2507 IQ3_XXS**, mediante `llama-bench`, variando `--n-gpu-layers` entre 0, 1 y 8 con tres repeticiones por ajuste.
2. **TensorFold 1.1.1 + Qwen3.5-2B-MLX-4bit**, mediante cinco peticiones HTTP secuenciales a la API compatible con OpenAI.

No son modelos equivalentes ni usan el mismo protocolo; sus velocidades brutas no deben interpretarse como una clasificación directa de motores.

## Hardware y entorno

- CPU: Intel Core i7-12650H.
- Memoria del sistema: aproximadamente 14 GiB.
- GPU: NVIDIA RTX 3050 Laptop, 4 GiB VRAM.
- Driver NVIDIA: 580.178.04; CUDA reportada: 13.0.
- Compute capability: sm_86.
- Sistema: Ubuntu/Linux.
- En pruebas previas se observó un Xid 31 con llama-server; por prudencia, conviene repetir las pruebas críticas y registrar los errores de kernel/GPU.

## Experimento A — llama.cpp

### Configuración

- Modelo: `Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf`.
- SHA-256 del modelo: `292daa2b66aec59d075532d0bcf05010bf4a3b012a4216c28dc021b73d1e9ab4`.
- Tamaño informado por `llama-bench`: 11.37 GiB.
- Build: `6fa4f6cd3 (11740)`.
- Hilos: 8.
- Prefill: `pp128`; generación: `tg32`.
- Capas GPU: 0, 1 y 8.
- Repeticiones: 3 por configuración; nueve ejecuciones, todas con código de salida 0.
- `--repetitions 1` por invocación de benchmark; se repitió la invocación tres veces por configuración.

### Resultados por repetición

| Capas GPU | Repetición | pp128 (tok/s) | tg32 (tok/s) |
|---:|---:|---:|---:|
| 0 | 1 | 13.69 | 1.45 |
| 0 | 2 | 24.42 | 1.41 |
| 0 | 3 | 29.55 | 1.60 |
| 1 | 1 | 57.28 | 1.44 |
| 1 | 2 | 76.25 | 1.40 |
| 1 | 3 | 89.89 | 2.14 |
| 8 | 1 | 69.08 | 1.88 |
| 8 | 2 | 26.38 | 1.65 |
| 8 | 3 | 9.41 | 1.95 |

### Estadísticas

| Capas GPU | Prueba | Media tok/s | Mediana tok/s | Desv. estándar | Mín. | Máx. |
|---:|---|---:|---:|---:|---:|---:|
| 0 | pp128 | 22.553 | 24.420 | 8.093 | 13.69 | 29.55 |
| 0 | tg32 | 1.487 | 1.450 | 0.100 | 1.41 | 1.60 |
| 1 | pp128 | 74.473 | 76.250 | 16.377 | 57.28 | 89.89 |
| 1 | tg32 | 1.660 | 1.440 | 0.416 | 1.40 | 2.14 |
| 8 | pp128 | 34.957 | 26.380 | 30.746 | 9.41 | 69.08 |
| 8 | tg32 | 1.827 | 1.880 | 0.157 | 1.65 | 1.95 |

### Interpretación

- En esta muestra, `ngl=1` obtuvo la mayor mediana de prefill.
- `ngl=8` mostró una dispersión muy elevada en prefill (9.41–69.08 tok/s); no debe atribuirse una causa sin repetir bajo condiciones controladas.
- La generación `tg32` se mantuvo aproximadamente entre 1.40 y 2.14 tok/s.
- La instantánea de `nvidia-smi` se recogió después de la ejecución, no durante ella. No representa utilización máxima ni permite concluir que no hubiera offload.
- Las nueve ejecuciones finalizaron con código 0, pero esto no sustituye la comprobación de estabilidad, errores del driver y memoria durante la prueba.

## Experimento B — TensorFold

### Configuración

- Motor: TensorFold 1.1.1, backend CUDA.
- Modelo: `mlx-community/Qwen3.5-2B-MLX-4bit`.
- Nombre servido: `qwen35-2b-4bit`.
- Contexto del servidor: 2048 tokens; paralelismo 1.
- Thinking desactivado; temperatura 0; límite de salida 128 tokens.
- Cinco peticiones HTTP secuenciales con el mismo prompt.
- Entrada reportada por petición: 66 tokens; salida: 128 tokens.
- Cinco respuestas HTTP 200.

### Resultados por repetición

| Run | HTTP | Velocidad reportada (tok/s) | Tiempo cliente (s) | TTFT (s) | Prefill (s) |
|---:|---:|---:|---:|---:|---:|
| 1 | 200 | 107.068 | 1.249233 | 0.051058 | 0.048931 |
| 2 | 200 | 103.407 | 1.317400 | 0.084446 | 0.080437 |
| 3 | 200 | 106.496 | 1.280382 | 0.084646 | 0.080489 |
| 4 | 200 | 103.677 | 1.312622 | 0.084926 | 0.080445 |
| 5 | 200 | 106.455 | 1.280760 | 0.084702 | 0.080406 |

### Estadísticas

| Métrica | Media | Mediana | Mínimo | Máximo |
|---|---:|---:|---:|---:|
| Velocidad reportada (tok/s) | 105.421 | 106.455 | 103.407 | 107.068 |
| Tiempo HTTP cliente (s) | 1.288079 | 1.280760 | 1.249233 | 1.317400 |
| TTFT reportado (s) | 0.077956 | 0.084646 | 0.051058 | 0.084926 |
| Prefill reportado (s) | 0.074142 | 0.080437 | 0.048931 | 0.080489 |

Las cinco salidas tienen el mismo SHA-256: `942ca6d9de584e12bd4f207d8cafddcffb594924f5d781501b267b7a1ca9ddad`.

### Interpretación y limitaciones

- Todas las peticiones generaron exactamente 128 tokens, alcanzando el máximo configurado; las respuestas podrían estar truncadas por ese límite.
- La latencia del cliente mide la petición HTTP completa; no es equivalente al tiempo interno de generación.
- La tasa de aceptación especulativa reportada fue baja (1 token aceptado de 56 propuestos en cada petición, aceptación 0.01786). Debe investigarse en pruebas específicas y no extrapolarse a otras cargas.
- El hash idéntico indica salida textual idéntica para este prompt y configuración, no una validación general de calidad.
- La captura de GPU al final no mide el pico durante cada petición.

## Comparabilidad

Estos experimentos responden a preguntas distintas:

- `llama-bench` separa prefill (`pp128`) y generación (`tg32`) para un modelo MoE de 30B en formato IQ3_XXS.
- TensorFold mide solicitudes API de un modelo de 2B en formato MLX 4-bit, con 66 tokens de entrada y 128 de salida.

Por tanto, **no es válido concluir que TensorFold sea más rápido que llama.cpp comparando directamente sus tok/s**. Difieren el modelo, la cuantización, la longitud de generación, el motor, la instrumentación y el protocolo.

## Archivos de resultados locales

Los siguientes artefactos quedaron guardados en el equipo local durante la sesión; no están incluidos en este documento de GitHub salvo que se añadan explícitamente:

- `~/benchmarks/qwen3-30b-a3b-iq3-xxs/layer-sweep-20261022-115737/benchmark-report.md`
- `~/benchmarks/qwen3-30b-a3b-iq3-xxs/layer-sweep-20261022-115737/summary.tsv`
- `~/benchmarks/qwen3-30b-a3b-iq3-xxs/layer-sweep-20261022-115737/measurements.csv`
- `~/benchmarks/qwen3-30b-a3b-iq3-xxs/layer-sweep-20261022-115737/statistics.csv`
- Logs `ngl0-rep1.log` a `ngl8-rep3.log` dentro del directorio del barrido.
- `~/benchmarks/qwen3-30b-a3b-iq3-xxs/tensorfold-qwen35-2b-4bit-20261022-121705/benchmark-report.md`
- `~/benchmarks/qwen3-30b-a3b-iq3-xxs/tensorfold-qwen35-2b-4bit-20261022-121705/measurements.csv`
- JSON originales `responses/run-01.json` a `run-05.json`, junto con `environment.txt`, `config.txt` y `after.txt`.

## Siguientes pruebas recomendadas

1. Repetir el barrido llama.cpp con más repeticiones y condiciones de sistema estables.
2. Muestrear GPU/VRAM y RAM durante cada ejecución, no solo después.
3. Repetir TensorFold con varios límites de salida y prompts controlados, incluyendo salidas que no terminen exactamente en el límite.
4. Registrar errores de kernel/driver, swap y presión de memoria.
5. Evaluar calidad de respuesta separadamente de rendimiento.
6. Añadir al repositorio los logs/CSV/JSON como artefactos o paquete comprimido si se necesita auditoría completa.


---

## 7. Ensayos anteriores: Qwen3.5-4B, tres motores

Fecha: 20 de octubre de 2026. Resultados de ensayos previos documentados en conversaciones y salidas de terminal; no revalidados en esta actualización. El microbenchmark inicial de Strata usó contexto 1024 y salida tg64; un protocolo API posterior pretendía contexto 256 y máximo 32 tokens. No son el mismo protocolo.

| Motor | Modelo/formato | Prefill | Decode | VRAM aproximada | Observaciones |
|---|---|---:|---:|---:|---|
| TensorFold | Qwen3.5-4B MLX-4bit | No registrado | 53.42–53.64 tok/s | 3120 MiB | Carga observada 6.4 s; TTFT en logs 0.193–0.212 s; modelo 2.75 GiB, reserva 0.5 GiB, ventana 0.21 GiB. |
| llama.cpp CUDA | Qwen3.5-4B GGUF Q4_K_M | 141.2 tok/s | 42.4 tok/s | 2808 MiB | Se usó --n-gpu-layers 99. |
| Rusting Strata 1.0.1 | Qwen3.5-4B GGUF Q4_K_M | 915.3 tok/s pp128; 986.5 pp512 | 46.6 tok/s tg64; 46.1 tok/s tg64 | 2928 MiB | ctx=1024, 3 repeticiones; plan 2752 MB, KV 32 MB, prefill 116 MB, expertos 0/0. |

Comando registrado para el microbenchmark de Strata:

~~~bash
cd "$HOME/rusting-strata-test"
./target/release/strata bench --gpu \
  --model "$HOME/llama.cpp-cuda/models/qwen3.5-4b-Q4_K_M.gguf" \
  --pp 128,512 --tg 64 --reps 3 --ctx 1024
~~~

Verificar la sintaxis con strata bench --help si la CLI instalada ha cambiado.

### Protocolo API controlado previsto

Script base: ~/benchmarks/benchmark_qwen35_4b_three_engines_fixed_v2.sh. Configuración prevista: prompt en español sobre IA local, temperatura 0, contexto 256, salida máxima 32, 3 repeticiones más calentamiento, ejecución secuencial. TensorFold usa MLX-4bit; llama.cpp y Strata usan GGUF Q4_K_M. Artefactos previstos: benchmark.log, environment.txt, client.py, results.jsonl, results.csv, summary.md y logs de servidor.

Advertencia: en un intento previo TensorFold emitió 64 y 128 tokens aunque se configuró --max-tokens 32. No dar por válido el límite sin verificar el JSON y contar tokens reales. En otra prueba el contexto TensorFold observado fue 512, no 256.

## 8. MoE grande e intentos no concluyentes

### Qwen3.5-35B-A3B IQ2_XXS

- Archivo: Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf.
- Tamaño: 10,676,139,840 bytes.
- SHA-256: 479cc80b2500f7ba5f6131986da188ecb406cf7855094c5d8ae0ec332a715105.
- Inspección de Strata: arquitectura qwen35moe, 40 capas, 256 expertos, 8 activos, embedding 2048.
- Histograma tensorial registrado: IQ2_XXS 157, IQ2_XS 9, Q4_K 126, Q8_0 71 y otros tipos; el nombre de la cuantización no implica que todos los tensores sean IQ2_XXS.
- Equipo: 14 GiB RAM, 31 GiB swap, RTX 3050 Laptop 4 GiB, CUDA 13.0, driver 580.178.04; unos 620 GB libres de almacenamiento en el momento del ensayo.
- TensorFold MLX de unos 20.4 GB se consideró inviable con los recursos disponibles. No cuenta como benchmark ejecutado.
- No hay en este resumen una medición validada de TTFT o tok/s para el 35B; registrar como caracterización/prueba incompleta, no como ganador ni resultado de rendimiento.

### Error CUDA/PTX en Rusting Strata

Error observado en ensayos previos con Qwen3.5-4B:

~~~text
CUDA_ERROR_UNSUPPORTED_PTX_VERSION
~~~

Contexto: Rusting Strata 1.0.1, GPU sm_86, driver 580.178.04, CUDA reportada 13.0 y NVRTC observado 13.4.92. Cambiar cudarc de cuda-13010 a cuda-13000 permitió compilar, pero no eliminó el error. Caché PTX observado: ~/.cache/rusting_strata/3404abca2c636220.ptx, 623,784 bytes. Durante una inspección llama-cli ocupaba unos 2808 MiB de VRAM, por lo que procesos concurrentes pueden afectar las pruebas. Una compilación correcta no demuestra compatibilidad de ejecución.

## 9. Cuadro de conclusiones: MoE y no-MoE

| Modelo | Tipo | Motor | Medidas principales | Conclusión y confianza |
|---|---|---|---|---|
| Qwen3.5-2B MLX-4bit | No-MoE | TensorFold 1.1.1 CUDA | API 103.407–107.068 tok/s; TTFT 0.051–0.085 s; petición 1.249–1.317 s | 5/5 HTTP 200; las cinco salidas alcanzaron 128 tokens. Aceptación especulativa muy baja: 1/56. No comparable directamente con llama-bench. |
| Qwen3.5-4B MLX-4bit | No-MoE | TensorFold | Decode 53.42–53.64 tok/s; TTFT 0.193–0.212 s | Muestra anterior; formato MLX distinto de GGUF. Existe una advertencia de límite de tokens inconsistente. |
| Qwen3.5-4B GGUF Q4_K_M | No-MoE | llama.cpp CUDA | Prefill 141.2; decode 42.4 tok/s | Medida de benchmark; no equivale a TTFT de API. |
| Qwen3.5-4B GGUF Q4_K_M | No-MoE | Rusting Strata | Prefill 915.3 tok/s pp128 y 986.5 pp512; decode 46.6/46.1 tok/s tg64 | Prefill más alto de la muestra; decode solo moderadamente superior a llama.cpp. Métrica/protocolo pueden diferir. |
| Qwen3-30B-A3B-Instruct-2507 IQ3_XXS | MoE | llama.cpp CUDA | ngl 0/1/8: mediana prefill 24.42/76.25/26.38 tok/s; mediana decode 1.45/1.44/1.88 tok/s | ngl=1 tuvo la mejor mediana prefill; ngl=8 mostró gran dispersión. Decode lento. Repetir con telemetría durante la ejecución. |
| Qwen3.5-35B-A3B IQ2_XXS | MoE | Rusting Strata / llama.cpp | No hay rendimiento validado consolidado | Arquitectura inspeccionada, pero no se debe inferir rendimiento a partir de esa inspección. |
| Qwen3.5-35B-A3B IQ2_XXS | MoE | TensorFold MLX | No medido | Estimación de ~20.4 GB; no viable con RAM/VRAM actuales en ese formato. |

Los valores ngl=0,1,8 describen capas solicitadas para offload GPU en llama.cpp; no son el número total de capas del modelo ni el número de expertos activos. La variabilidad de ngl=8 no demuestra causalidad por sí sola. Hace falta repetir con condiciones controladas y telemetría en vivo.

## 10. Reproducibilidad y cadena de custodia

### Captura de entorno

~~~bash
mkdir -p "$HOME/benchmarks/inferencia-rtx3050-4gb-oct26"
OUT="$HOME/benchmarks/inferencia-rtx3050-4gb-oct26"
{
  date --iso-8601=seconds
  uname -a
  cat /etc/os-release
  lscpu
  free -h
  swapon --show
  nvidia-smi
  nvidia-smi -q
  nvcc --version 2>&1 || true
  command -v llama-bench
  command -v llama-cli
  command -v llama-server
  command -v tensorfold-native
  "$HOME/rusting-strata-test/target/release/strata" --version 2>&1 || true
  git -C "$HOME/llama.cpp-cuda" rev-parse HEAD 2>&1 || true
  git -C "$HOME/rusting-strata-test" rev-parse HEAD 2>&1 || true
} > "$OUT/environment.txt" 2>&1
~~~

### Inventario de scripts y datos

~~~bash
OUT="$HOME/benchmarks/inferencia-rtx3050-4gb-oct26"
find "$HOME/benchmarks" -maxdepth 5 -type f \
  \( -name '*.sh' -o -name '*.py' -o -name '*.csv' -o -name '*.jsonl' \
     -o -name '*.json' -o -name '*.log' -o -name '*.md' -o -name '*.tsv' \) \
  -print > "$OUT/artifact-inventory.txt"
find "$HOME/benchmarks/qwen3-30b-a3b-iq3-xxs" -type f -print0 \
  | sort -z | xargs -0 -r sha256sum > "$OUT/sha256-qwen3-30b.txt"
sha256sum "$HOME/llama.cpp-cuda/models/qwen3.5-4b-Q4_K_M.gguf" \
  > "$OUT/sha256-qwen35-4b.txt" 2>&1 || true
~~~

### Scripts originales registrados

- Barrido llama.cpp: ~/benchmarks/qwen3-30b-a3b-iq3-xxs/benchmark-layer-sweep.sh
- TensorFold API: ~/benchmarks/qwen3-30b-a3b-iq3-xxs/benchmark-tensorfold.sh
- Benchmark común Qwen3.5-4B: ~/benchmarks/benchmark_qwen35_4b_three_engines_fixed_v2.sh
- Resultados llama.cpp 30B: ~/benchmarks/qwen3-30b-a3b-iq3-xxs/layer-sweep-20261022-115737/
- Resultados TensorFold 2B: ~/benchmarks/qwen3-30b-a3b-iq3-xxs/tensorfold-qwen35-2b-4bit-20261022-121705/

Para preservar los scripts ejecutados, copiarlos y calcular sus hashes antes de volver a probar:

~~~bash
OUT="$HOME/benchmarks/inferencia-rtx3050-4gb-oct26"
cp "$HOME/benchmarks/qwen3-30b-a3b-iq3-xxs/benchmark-layer-sweep.sh" "$OUT/" 2>/dev/null || true
cp "$HOME/benchmarks/qwen3-30b-a3b-iq3-xxs/benchmark-tensorfold.sh" "$OUT/" 2>/dev/null || true
cp "$HOME/benchmarks/benchmark_qwen35_4b_three_engines_fixed_v2.sh" "$OUT/" 2>/dev/null || true
sha256sum "$OUT"/*.sh > "$OUT/script-sha256.txt" 2>&1
~~~

Los scripts originales, logs completos, CSV y JSON permanecen en el equipo local; GitHub no puede leer automáticamente rutas bajo el directorio home. Este informe no inventa el contenido íntegro de scripts cuyo texto fuente no está adjunto. Para un paquete reproducible auditable, añadir esos scripts, logs por ejecución, CSV/JSON originales, configuración completa, commits exactos de los motores, hashes de modelos y códigos de salida.

## 11. Protocolo recomendado para comparación válida

Fijar modelo y formato que todos los motores soporten, prompt/tokenizer común, contexto 256, salida real de 32 tokens, tres repeticiones más calentamiento, misma temperatura y ejecución secuencial. Registrar carga, TTFT, prefill tok/s, decode tok/s, duración total, tokens reales de entrada/salida, VRAM/RAM pico, swap, temperatura/potencia GPU, telemetría durante la ejecución, exit code y errores.

Separar resultados comparables, microbenchmarks nativos, intentos fallidos y evaluación de calidad. Para MoE registrar expertos totales/activos, offload de capas y expertos, tamaño KV y fallback CPU. No declarar ganador por prefill aislado si TTFT, decode, salida real o estabilidad no se midieron bajo el mismo protocolo.


## 12. Motores adicionales propuestos y estado de cobertura

En el plan de comparación del 20 de octubre se propuso ampliar el benchmark de Qwen3.5-4B a mistral.rs, vLLM, SGLang y KTransformers. Los datos consolidados disponibles en este informe no contienen una ejecución comparable, completada y validada para esos cuatro motores. Por tanto:

| Motor | Estado que puede afirmarse con la evidencia disponible | Qué falta |
|---|---|---|
| mistral.rs | Se registró instalación de mistralrs 0.9.5 CUDA en ~/.local/bin/mistralrs; no hay resultados comparables consolidados aquí. | Confirmar carga del modelo, versión/commit, VRAM, TTFT, prefill/decode y tres repeticiones. |
| vLLM | Propuesto para evaluación; sin mediciones validadas en este conjunto. | Verificar compatibilidad de arquitectura/cuanti­zación y disponibilidad de memoria; no asumir que entra en 4 GiB. |
| SGLang | Propuesto para evaluación; sin mediciones validadas en este conjunto. | Verificar soporte de modelo/cuanti­zación y recursos; capturar fallos si no inicia. |
| KTransformers | Propuesto para evaluación; sin mediciones validadas en este conjunto. | Verificar soporte para el modelo exacto, backend y memoria. |
| TensorFold | Sí medido con Qwen3.5-2B MLX-4bit y, en un ensayo anterior, Qwen3.5-4B MLX-4bit. | Igualar el protocolo y resolver/registrar límites reales de salida. |
| llama.cpp CUDA | Sí medido con Qwen3.5-4B GGUF Q4_K_M y Qwen3-30B-A3B IQ3_XXS; build y capas registrados para el 30B. | Repetir el barrido de capas con telemetría y mayor número de repeticiones. |
| Rusting Strata | Sí medido con Qwen3.5-4B GGUF Q4_K_M; se investigó incompatibilidad PTX; se inspeccionó arquitectura Qwen3.5-35B-A3B. | No hay rendimiento validado consolidado para 35B ni comparación API homogénea para todos los modelos. |

No incluir motores sin medición como si su velocidad fuera cero: usar “no medido”, “no compatible” o “falló al iniciar” y conservar el log de cada intento.


## 13. Recopilación de artefactos para reproducibilidad

Se añade el recolector [`scripts/benchmarks/collect-inferencia-rtx3050-oct26.sh`](https://github.com/robertosantosx2/LEONES/blob/docs/report-inferencia-denso-octubre-2026/scripts/benchmarks/collect-inferencia-rtx3050-oct26.sh). Está diseñado para ejecutarse en Ubuntu en la máquina probada. Reúne los scripts de benchmark conocidos, los directorios de resultados, los logs/CSV/JSON disponibles, información del sistema y versiones, hashes de artefactos y hashes de modelos. **No copia los pesos de los modelos**, el historial del shell ni credenciales.

Tras descargar o actualizar el checkout de LEONES, ejecuta:

~~~bash
cd "$HOME/leones-work/LEONES"
git pull
bash scripts/benchmarks/collect-inferencia-rtx3050-oct26.sh
~~~

Si el checkout activo de LEONES está en otra ruta, cambia solo el primer `cd` por la ruta real. El recolector crea un directorio fechado y un `.tar.gz` en `~/benchmarks/`, además del SHA-256 del archivo comprimido. Revisa `environment/missing-artifacts.txt` dentro de la colección: los archivos no encontrados quedan marcados como ausentes, sin fabricar datos.

Antes de compartir el paquete, comprueba que no contenga información privada y conserva el archivo `.sha256` para verificar la integridad tras la transferencia. El recolector **no ejecuta benchmarks ni cambia configuraciones del sistema**; captura el estado y reúne los resultados existentes. Para registrar telemetría en vivo, debe lanzarse un nuevo ensayo con muestreo de GPU/RAM/swap durante cada repetición.

La incorporación del recolector al repositorio no significa que los datos locales ya se hayan subido: el paquete se crea únicamente al ejecutar el script en la máquina de pruebas y transferir después el archivo resultante.
