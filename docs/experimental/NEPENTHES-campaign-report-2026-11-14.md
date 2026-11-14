# NEPENTHES — campaña de instrumentación, rendimiento y capacidad

**Corte de evidencia:** 2026-11-14  
**Motor observado:** Tandem.cpp / llama.cpp base  
**Modelo principal:** Qwen3.5-35B-A3B-IQ2_XXS  
**Plataforma:** MSI Thin 15 B12UC, Ubuntu, i7-12650H, 14 GiB RAM, RTX 3050 Laptop 4 GiB (sm_86), driver 580.178.04, CUDA Toolkit 13.4.92  
**Estado:** informe de campaña y diseño de instrumentación. No representa una mejora de runtime implementada ni una comparación A/B controlada.

## 1. Objetivos de la campaña

NEPENTHES tiene dos líneas de éxito independientes:

1. **FAST PATH — velocidad:** reducir TTFT/prefill/decode y el tiempo total, cuando la máquina dispone de recursos suficientes.
2. **CAPACITY PATH — capacidad:** ejecutar modelos que excedan VRAM y RAM mediante memoria jerárquica y streaming, aceptando degradación extrema de velocidad antes que fallar por OOM, siempre que arquitectura, operadores, formato, almacenamiento y direccionamiento permitan una ruta válida.

La campaña debe producir evidencia completa por ejecución, no solo tokens/s: configuración efectiva, identidad de motor/modelo, respuestas, tiempos, telemetría, eventos, errores y hashes.

## 2. Evidencia ya archivada en LEONES

### 2.1 Comparación MoE 512 vs 768 MiB — 05-11-2026

El informe histórico y los nueve artefactos primarios están archivados en la rama `Experimental`: [informe de 05-11](https://github.com/robertosantosx2/LEONES/blob/Experimental/docs/experimental/tandem-qwen35-35b-a3b-rtx3050-2026-11-05.md) y [directorio de evidencia](https://github.com/robertosantosx2/LEONES/tree/Experimental/artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-05/). Incluye baseline 512 MiB, cinco respuestas JSON de 768 MiB, logs 512/768, manifiesto hardware/modelo y log de compilación. Resultado: 37,957 tok/s en la única muestra de 512 tokens a 512 MiB frente a 35,671 tok/s de media en dos muestras de 512 tokens a 768 MiB (~6% menos); VRAM observada 2.077 frente a 2.345 MiB. La muestra es pequeña; la recomendación histórica fue conservar 512 MiB, no una prueba estadística definitiva.

### 2.2 Expediente de la ejecución del 12-11-2026

Está publicado el paquete [tandem-qwen35-evidence-20261112-235030.tar.gz](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/evidence/tandem-qwen35-evidence-20261112-235030.tar.gz), de 288.463 bytes, con su sidecar SHA-256. Hash registrado: `82660fe04f665181285a3d81dd89e6b1f768a6be33cfaffa8db1730bb79d2548`.

### 2.3 Batería independiente del 13-11-2026

El expediente está publicado en:

- [Informe de la batería](nepenthes-tandem.cpp-qwen3.5-35b-a3b-2026-11-13.md)
- [Expediente primario completo](../../artifacts/benchmarks/tandem-qwen35-independent-2026-11-13/full-run/)

El expediente contiene manifiesto, diez respuestas JSON originales, resumen JSONL, 255 muestras de recursos y SHA256SUMS. El runner completó 10/10 peticiones; seis finalizaron con `stop` y cuatro con `length`. Se registraron 7.943 tokens generados, media simple de 33,90 tok/s, mediana 34,61 tok/s y tasa agregada ponderada por tiempo de 32,30 tok/s. Las cuatro respuestas con `length` son truncadas y no deben contarse como éxitos funcionales completos.

No es una comparación A/B controlada con cafe-llama.cpp. La corrección funcional se revisó estáticamente; no se ejecutó el código Python generado.

También se conserva el fragmento de terminal `terminal-tail-cases-06-10.txt` con su sidecar SHA-256 bajo `tandem-qwen35-independent-2026-11-13/evidence/`; es evidencia parcial y no sustituye las respuestas originales.

### 2.4 Sondas y scripts de campaña

En [repro/](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/) ya están versionados:

- `run_battery.py`: batería secuencial con ventana de medición por petición.
- `resource_monitor.py`: RAM, swap, CPU, RSS, disco, GPU, VRAM, temperatura, potencia, reloj y PCIe.
- `moe_runtime_probe.py`: I/O y scheduler del proceso, hilos, RSS/HWM, descriptores, PSI y frecuencia CPU.
- `inspect_NEPENTHES_moe_trace.py`: inspección de contadores agregados de caché y parser MCT1 para builds compatibles.
- `inspect_NEPENTHES_nsys_sqlite.py`: análisis offline y read-only de exportaciones Nsight SQLite.
- `inspect_NEPENTHES_independent_run.py`, `run_NEPENTHES_independent_two_sum.py`, `collect_evidence.sh` y scripts de repetición.
- Tests sintéticos para sondas MoE e inspector Nsight; workflow de GitHub Actions en esta rama.

La build de referencia de Tandem.cpp basada en llama.cpp `f5222f25c18da062ab2b8a2dbbfbf4feae398566` expone contadores agregados de caché, pero no implementa MCT1/`LLAMA_MOE_CACHE_TRACE`. Los contadores de caché pueden aparecer al destruirse el objeto; no se debe detener el servidor solo para forzar su volcado.

## 3. Hallazgos medidos

### 3.1 Ejecución 512 MiB, sin thinking

En el experimento local Qwen3.5-35B-A3B con caché MoE de 512 MiB y modo sin thinking se registraron 52 tokens de prompt y 512 generados, prefill aproximado de 46,5 tok/s y decode de 35,6 tok/s. RSS observado: 9,27 GiB; swap ocupado: 7,5 GiB; VRAM usada: 2.345 MiB.

Es una referencia descriptiva de una configuración concreta. No se compara directamente con la batería con thinking del 13-11 ni con la captura Nsight del 14-11.

### 3.2 Captura correlacionada Nsight Systems — 14-11-2026

Identidad de la ejecución:

- Binario Tandem.cpp: 0.8.0-dev, build 11962, commit `f5222f25c18da062ab2b8a2dbbfbf4feae398566`.
- Modelo: `Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf`.
- SHA-256 del modelo: `479cc80b2500f7ba5f6131986da188ecb406cf7855094c5d8ae0ec332a715105`.
- Petición: 39 tokens de prompt y 128 tokens generados.
- Prefill: 2.607,372 ms (14,9576 tok/s).
- Decode: 3.959,987 ms (32,0708 tok/s).
- Captura: incluye carga e inferencia; no incluye shutdown.

Recuentos de la exportación SQLite:

| Actividad | Recuento |
|---|---:|
| Kernels GPU | 8.982 |
| Memcpy | 44.488 |
| CUDA Runtime API | 84.116 |
| Sincronización | 7.864 |
| CUDA Graph | 5.207 |

Transferencias agregadas observadas: aproximadamente 6,807 GB H2D y 252,1 MB D2H. El volumen acumulado de transferencias no es memoria residente. H2D concentra 643,511 ms de actividad MemOps; D2H 39,969 ms. La API host registra 3,133 s acumulados en `cudaMemcpyAsync` y 3,040 s en `cudaStreamSynchronize`; estos intervalos de API no son tiempos de ejecución GPU.

Las 84.116 llamadas CUDA Runtime observadas se atribuyen en la exportación a un hilo llamado `llama-server`. Esto describe dónde CUPTI registró las llamadas; no demuestra que no existan workers CPU ni que ese hilo ejecute todo el trabajo de CPU.

### 3.3 Esperas híbridas MoE

Se observaron 159 instancias de `k_host_add_wait`, siempre con la secuencia GPU vecina:

`moe_weighted_reduction_f32 → k_host_add_wait → k_host_add`

La suma de intervalos fue 140,603 ms (44% del tiempo agregado de kernels de esa captura; no del tiempo total de petición). 123 esperas duraron menos de 100 µs. Las 36 restantes promediaron 3,887 ms y alcanzaron 10,344 ms.

- Ninguna de las 159 esperas se solapó con un evento memcpy registrado.
- 52 esperas se solaparon con intervalos host de `cudaStreamSynchronize` del mismo hilo; son dos representaciones correlacionadas del mismo fenómeno y no deben sumarse como eventos independientes.
- La copia anterior terminó entre 165 y 643 µs antes de las esperas largas observadas; la siguiente empezó normalmente cientos de microsegundos después.

La implementación inspeccionada usa un flag en memoria host fijada: el worker CPU publica el resultado y el kernel GPU espera el flag. La secuencia es compatible con una espera de resultado CPU, pero la captura no incluye muestreo CPU/scheduler. Por tanto, no permite atribuir el tiempo a cómputo CPU, desplanificación, publicación, contención o sincronización concreta.

### 3.4 Límites de instrumentación constatados

- `perf_event_paranoid=4`; `perf_event_open` no está disponible para la captura actual.
- La exportación SQLite no contiene tablas útiles de muestreo CPU/scheduler.
- La captura OSRT anterior falló en la inyección de herramientas (`libToolsInjection64.so` / señal 11); la captura CUDA sin OSRT sí produjo datos.
- No se observaron los contadores de instrumentación MoE en el log de esa sesión. Su ausencia no prueba por sí sola que la instrumentación estuviese desactivada: hay que comprobar las condiciones de emisión y el ciclo de vida del objeto.

## 4. Hipótesis que deben probarse

Estas hipótesis orientan experimentos; no son conclusiones causales:

1. **Coste de sincronización híbrida:** parte del decode puede estar limitada por la espera GPU a resultados CPU en la ruta `hybrid_add`. Medir duración por flag, worker, token y fase.
2. **Tráfico H2D:** el volumen alto de H2D podría reflejar pesos/expertos, buffers u otras transferencias. Separar por tamaño, dirección, memoria de origen, stream, capa y correlación temporal con routing/cache.
3. **Presión de memoria:** el uso de swap del experimento de 512 MiB puede afectar latencia y jitter. Separar swap preexistente de deltas por ejecución y distinguir capacidad de memoria de tráfico de almacenamiento.
4. **Localidad MoE:** una política de caché y prefetch sensible a la reutilización de expertos podría reducir fallos y transferencias, pero requiere trazas por capa/experto y A/B controlado.
5. **Coste de lanzamiento/sincronización:** los recuentos CUDA Runtime y Graph sugieren medir granularidad de kernels, reutilización de graph y sincronizaciones por token; los totales acumulados no bastan para identificar el cuello de botella.
6. **Degradación por capacidad:** una ruta L2/SSD y L3/swap puede evitar OOM a costa de latencia. Hay que medir progreso, integridad y recuperación bajo presión, no solo throughput.

## 5. Mejoras propuestas — campaña NEPENTHES

### Fase A — expediente universal por ejecución

Crear un recolector único, independiente del motor, que genere un directorio nuevo y nunca sobrescriba resultados:

- `run_manifest.json`: UUID, timestamps wall/monotonic, motor, commit/build/binario/hash, modelo/hash, argumentos efectivos, endpoint, prompt suite, parámetros, entorno y versiones de sondas.
- `requests/*.json`: petición y respuesta originales, usage, finish reason, TTFT, prefill/decode, latencias y errores.
- `samples/host.jsonl`: CPU, RAM, swap, PSI, proceso, hilos, RSS/HWM, scheduler, I/O y frecuencia.
- `samples/gpu.jsonl`: GPU/VRAM, clocks, temperatura, potencia, PCIe, errores y fuente de cada campo.
- `events/*.jsonl`: eventos discretos correlacionados (load/unload, cache hit/miss, evictions, prefetch, transferencias, alloc/free, fallback, OOM, stalls).
- `profiles/`: Nsight Systems/Compute, SQLite, logs de motor y diagnósticos.
- `SHA256SUMS` y `collection_report.json`: integridad, cobertura, huecos, permisos/errores de sondas y overhead estimado.

Cada muestra llevará `run_id`, `request_id`, reloj monotónico y timestamp UTC/local. Los contadores globales se marcarán como globales; los datos ausentes serán `null/unavailable`, nunca cero. Los originales serán inmutables; los agregados se regenerarán.

### Fase B — sondas de rendimiento

- Descomponer TTFT, prefill, decode, inter-token latency, throughput y tiempo total.
- CUDA API host, kernel GPU, memcpy/memset, graph capture/launch, alloc/free y sincronización.
- PCIe RX/TX con cadencia y semántica declaradas.
- CPU por proceso/hilo, scheduler runtime/wait, PSI, frecuencia y throttling cuando sea accesible.
- RAM/VRAM residente, picos, pinned/managed, swap y E/S de bloque.
- MoE: routing por capa/experto, hot/cold set, cache hit/miss, eviction, bytes transferidos, prefetch, cola y tiempo de espera.
- KV cache: bytes, ocupación, crecimiento, reutilización, presión y fallos.
- Overhead de cada sonda: ejecución con sondas activadas y desactivadas bajo protocolo idéntico.

### Fase C — CAPACITY PATH

Diseñar y medir memoria jerárquica:

- **L0 VRAM:** working set activo, kernels y buffers críticos.
- **L1 RAM:** caché de expertos/pesos, slabs pinned y buffers de staging.
- **L2 SSD/NVMe:** pesos mapeados/streaming y caché persistente.
- **L3 swap:** último recurso explícito, con límites, backpressure y advertencia de latencia.

El scheduler de memoria debe soportar admission control, eviction por coste/reutilización, prefetch, transferencias asíncronas cuando proceda, límites de memoria, cancelación, recuperación tras I/O/OOM y fallback degradado. La ruta de capacidad debe poder continuar a throughput muy bajo si el modelo y sus operadores lo permiten; no prometer compatibilidad universal.

### Fase D — campañas A/B y estrés

- Baseline sin sondas frente a instrumentación ligera y completa.
- Prefill y decode separados; caché fría/caliente; contextos crecientes.
- Tamaños de caché MoE, prefetch on/off y políticas LRU/recency/frequency.
- Presión de RAM/VRAM, swap y disco; modelos mayores que VRAM y RAM.
- Pruebas largas de estabilidad, errores de lectura, OOM, cancelación y recuperación.
- Comparación solo con mismo modelo/hash, prompt, parámetros, motor/build, estado de caché y condiciones de host.

## 6. Orden de implementación

1. Cerrar el archivo histórico y verificar hashes/cobertura.
2. Unificar el esquema de manifiesto y correlación temporal.
3. Implementar recolector universal y pruebas offline con fixtures.
4. Completar sondas de host/GPU/CUDA/MoE/KV y medición de overhead.
5. Implementar validadores de expediente y exportadores de informe.
6. Integrar eventos internos del motor en un parche separado de Tandem.cpp.
7. Implementar CAPACITY PATH por etapas y sus pruebas de estrés.
8. Ejecutar validación física en Ubuntu solo tras revisión del usuario.

## 7. Pendiente de archivo local

La captura correlacionada del 14-11-2026 está identificada localmente en `$HOME/NEPENTHES_QWEN35_CORRELATED_20261114`:

- `qwen35-correlated-20261114.nsys-rep` (SHA-256 `f5ced9493e2055dd1c28e7e3d6e5c0c03e0d445a52924a0a71c39339b7c35104`)
- `qwen35-correlated-20261114.sqlite`
- `qwen35-correlated-summary.txt`
- `server.log`
- `correlated-inference-response.json`
- `binary-inspection.txt`
- `moe-instrumentation-check.txt`
- `preflight.txt`
- `real-library-identities.txt`

Estos archivos siguen siendo **pendientes de subir**: esta sesión puede inspeccionar GitHub, pero no leer directamente el filesystem de tu Ubuntu. No se crean copias ficticias ni se reconstruyen logs a partir de resúmenes. El expediente 12-11, el full-run 13-11 y el fragmento de terminal 13-11 ya están presentes en LEONES. Queda cotejar el tarball local `NEPENTHES_TANDEM_QWEN35_20261113_full.tar.gz` y el piloto, si existen, para determinar si aportan archivos no duplicados; además, falta archivar `NEPENTHES_CUDA_TOOLING_20261114` y el expediente correlacionado del 14-11.


Para cerrar este pendiente se añadió el [script de entrada de archivo](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/archive_NEPENTHES_evidence.py). Desde la raíz del checkout LEONES se ejecuta `python3 artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/archive_NEPENTHES_evidence.py --stage`; copia los expedientes conocidos a una carpeta timestamped, valida hashes, registra rutas ausentes y solo prepara con Git el nuevo directorio. No hace commit ni push.

## 8. Criterio de aceptación de la campaña

Una ejecución solo se declara archivada cuando existen originales, manifiesto, hashes verificables, inventario de sondas, reporte de cobertura y resultado funcional. Una mejora solo se declara demostrada con A/B reproducible. Una ruta de capacidad solo se declara válida si completa la inferencia sin OOM bajo el perfil declarado, aunque su velocidad sea muy baja.

**Conclusión:** ya hay un primer conjunto útil de sondas y un inspector Nsight read-only. La prioridad inmediata es cerrar el hueco de evidencia local del 14-11, convertir la instrumentación existente en un recolector coherente por ejecución y ampliar las sondas antes de optimizar el runtime.
