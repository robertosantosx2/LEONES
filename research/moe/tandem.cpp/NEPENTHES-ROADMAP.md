# NEPENTHES — roadmap técnico subordinado

> **Aviso de gobernanza documental:** el documento maestro único es [NEPENTHES-INDEX.md](NEPENTHES-INDEX.md). El plan general, las prioridades y el estado de cada motor se mantienen exclusivamente allí. Este archivo se conserva como checklist técnico/histórico de tareas y criterios detallados; no debe utilizarse como estado global vigente. Al cerrar o cambiar un gate, actualizar primero el documento maestro.


**Fecha de actualización documental:** 2026-11-20.  
**Estado operativo:** consultar exclusivamente el [NEPENTHES-INDEX.md](NEPENTHES-INDEX.md). Este anexo conserva fases, criterios y evidencias históricas; sus checklists heredados no constituyen estado vigente si no están reconciliados en el INDEX. TensorFold host-only ya está aceptado: TensorFold PR #6 merge `50f1a34`; LEONES PR #217 merge `3c68c3a`; cinco checks exactos verdes sobre HEAD `c258ec9`. Tandem.cpp PR #5, LEONES PR #218 y #219 están fusionadas; sigue pendiente el productor NVTX batch de Tandem bajo LEONES issue #212. La prioridad actual y el orden de ejecución son exclusivamente los del INDEX. No implica aceptación física C07/C08.

Este roadmap separa implementación, validación CI y validación física. Una tarea no se considera terminada por existir un PR: necesita la evidencia indicada en su criterio de salida.

## Leyenda

- [x] Implementado y con evidencia suficiente para el alcance indicado.
- [~] Implementado o validado parcialmente; falta una prueba de aceptación.
- [ ] Pendiente.

## Fase A — Instrumentación del motor

- [x] Definir contrato universal de eventos y sink JSONL.
- [x] Implementar emisión segura ante concurrencia y barrera de apagado.
- [x] Añadir pruebas de formato JSONL y ciclo de vida del sink.
- [x] Integrar el aplicador determinista de sondas sobre la revisión fijada de llama.cpp.
- [x] Compilar CUDA en CI para la arquitectura de destino sm_86.
- [x] Ejecutar una inferencia real Qwen3.5-4B en MSI con binario parcheado; confirmar emisión de 3.683 eventos de motor.
- [~] Auditar la semántica y cobertura de cada familia observada; todos los eventos dentro de la ventana usan `request_id=0`.
- [~] Auditar cobertura real de eventos por subsistema: request/routing, KV cache, transfer, kernel, sync y allocation observados en Qwen3.5-4B; MoE cache, workers, prefetch, OOM/fallback y dispatch ggml_op aún sin aceptación específica.
- [ ] Medir overhead de instrumentación frente a una ejecución de control con protocolo idéntico.
- [ ] Definir y probar política de rotación/límites de tamaño del JSONL en ejecuciones largas.

**Salida de fase:** ejecución real con JSONL válido, eventos esperados, errores/pérdidas contabilizados y overhead medido.

### TensorFold 1.2.10 — conector host-only aceptado

- [x] Source audit 1.2.10 publicada en el fork.
- [x] ATC overlap completo desde el checkout correcto: `complete=true`, sin limitations ni overlaps, 3 worktrees.
- [x] Contrato común LEONES #207 aceptado; PR #210 merge `fcaf170`; post-merge CI 8/8 verde.
- [x] Contrato de diseño TensorFold #1 cerrado.
- [x] Implementar y fusionar el conector host-only mediante [TensorFold PR #6](https://github.com/robertosantosx2/TensorFold/pull/6), merge `50f1a34`; issue #3 cerrada.
- [x] Validar HEAD `c258ec930b4ea8f0d0bc785a984d2114bf041fb9` mediante cinco checks `completed/success` (`tensorfold-host`, `v1-complete`, `runtime-contracts`, `regression`, `gate`) en LEONES PR #217, merge `3c68c3a`.
- [x] Cubrir concurrencia, keep-alive, lifecycle background, drops/errors, summary final y fixtures mediante host CI y el importer común.
- [x] Mantener CUDA/NVTX/Nsight/MSI fuera de esta fase. No se afirma aceptación física ni overhead.

## Fase B — Instalación y CLI

- [x] Instalador user-space sin root.
- [x] Comando `nepenthes` en `~/.local/bin`.
- [x] Comandos `doctor`, `self-test`, `run/capture`, `inspect` y `verify`.
- [x] Wrapper de una línea con perfiles smoke/standard/full.
- [x] Variables `NEPENTHES_RUN_ID` y `NEPENTHES_TRACE_JSONL` para motores instrumentados.
- [x] Captura host de CPU/RSS y telemetría NVIDIA global cuando está disponible.
- [x] Logs, exit code, manifiesto, hashes, CSV, JSONL, SQLite y reportes HTML/Markdown/SVG.
- [x] Self-test ejecutado en MSI: 3 eventos, 1 muestra, HTML y checksums válidos.
- [x] Probar `nepenthes run` con proceso inocuo: exit code 0, paquete verificable.
- [x] Probar propagación de fallo controlado: exit code 23 preservado y paquete válido.
- [x] Probar `nepenthes run` con servidor instrumentado y Qwen3.5-4B: JSONL real con 3.683 eventos, request_start/end y exit code 0.
- [~] Verificar `nepenthes verify` y auditoría completa del paquete de inferencia real; Nsight estuvo desactivado en C06.
- [ ] Probar perfiles smoke/standard/full, `--nsys auto/required/off` y ausencia/fallo de Nsight.
- [ ] Ejecutar y archivar `nepenthes verify` sobre el paquete de inferencia C06.
- [ ] Probar fallo/terminación anticipada del motor, Ctrl-C, proceso hijo y captura parcial sin perder el manifiesto.
- [ ] Documentar actualización, reinstalación y desinstalación.

**Salida de fase:** instalación limpia y wrapper reproducible que deja paquete verificable incluso ante fallo controlado.

## Fase C — Importador LEONES

- [x] Importación emparejada JSONL + Nsight implementada y con tests sintéticos.
- [x] Preservación de SHA-256 y payload original.
- [x] Separación de dominios de reloj y política explícita de no correlación artificial.
- [x] Inspección Nsight solo lectura.
- [x] Importación standalone Nsight-only con migración 003 y tablas separadas.
- [x] Adaptadores de ocho familias presentes en la captura MSI.
- [x] Importación real MSI: 151.039 filas, integridad SQLite OK, sin duplicados ni anomalías temporales básicas.
- [x] Comprobación CUDA_EVENT: los 262 timestamps cero coinciden con la fuente y se conservan sin fabricar intervalos.
- [~] Validar importación emparejada real desde una sola ejecución del wrapper.
- [ ] Probar reimportación/idempotencia y comportamiento ante base de salida existente.
- [ ] Probar versiones distintas de Nsight/SQLite y tablas CUPTI no soportadas con filas.
- [ ] Verificar que resumen, coverage y manifest de salida reflejan errores parciales sin ocultarlos.

**Salida de fase:** importación emparejada y standalone repetible, trazable, íntegra y con cobertura honesta.

## Fase D — Captura Qwen3.5 y validación experimental

- [x] Preservar captura Nsight histórica del 14-11-2026 y su procedencia.
- [x] Inspeccionar e importar el SQLite histórico sin JSONL emparejado.
- [x] Construir el informe descriptivo de la captura histórica.
- [x] Aplicar `tandem.patch`, `runtime.patch` y probes sobre la revisión pinned llama.cpp `f5222f25c18da062ab2b8a2dbbfbf4feae398566` y compilar `llama-server` CUDA sm_86 en MSI. No se usó el checkout shallow cafe-llama.cpp.
- [x] Ejecutar Qwen3.5-4B Q4_K_M en CPU-only con contexto 512, 4 hilos, batch 128 y ubatch 64; capturar 3.683 eventos.\n- [ ] Ejecutar campaña Qwen3.5-35B con configuración y modelo registrados en manifest.
- [ ] Capturar simultáneamente JSONL NEPENTHES y Nsight SQLite de la misma ejecución (C06 usó `--nsys off`).
- [~] KV cache observado: 49 eventos dentro de la ventana C06. MoE cache, workers y prefetch deben verificarse con eventos explícitos; no inferirlos por proximidad temporal.
- [ ] Repetir ejecución al menos tres veces con misma configuración y guardar controles; incluir baseline sin sondas.
- [ ] Comparar overhead, tokens/s, memoria host/GPU, kernels y transferencias.
- [ ] Archivar logs, modelo identificado por hash, comandos, configuración, commit, JSONL, SQLite, NSYS report, respuesta y checksums.

**Salida de fase:** dataset emparejado reproducible y suficiente para responder preguntas de rendimiento/ciclo de vida sin sobreinterpretar correlaciones.

## Fase E — Informes y visualización

- [x] Plantilla HTML reutilizable y PDF/PNG del primer informe Qwen3.5-4B; resumen histórico Qwen3.5-35B con tablas de actividades.
- [x] Reglas de interpretación para timestamps, correlación y cobertura.
- [~] Informe HTML/Markdown/SVG generado por CLI: validado en self-test; primer dashboard Qwen3.5-4B generado a partir de métricas agregadas disponibles; generación automática desde JSONL/SQLite real pendiente.
- [ ] Panel temporal con CPU/RSS/GPU y marcas de request.
- [ ] Distribución de kernels por nombre, duración y stream.
- [ ] Transferencias H2D/D2H/D2D por bytes, dirección y duración Nsight.
- [ ] Actividad CUDA runtime/synchronization/graph por tipo.
- [ ] Vistas específicas de KV cache/MoE cache/worker/prefetch basadas en sondas reales.
- [ ] Comparativa entre runs y baseline.
- [ ] Exportación de tablas CSV y consultas reproducibles desde SQLite.

**Salida de fase:** informe que permite navegar datos brutos, resumen, tablas y gráficas; cada métrica identifica fuente, reloj, unidad y nivel de atribución.

## Fase E.1 — Análisis semántico y calidad de informes (prioridades nuevas)

La captura C07 de Qwen3.5-4B confirma que el importador puede exponer actividad CUDA útil, pero los informes deben decodificar los enums de Nsight y preservar los límites de atribución.

### Backlog priorizado

| Prioridad | Mejora | Beneficio |
|---|---|---|
| **P0** | Decodificación semántica de `cudaMemcpyKind` y tipos de memoria (`srcKind`/`dstKind`) usando las tablas enum de la propia captura. | Distinguir H2D, D2H, D2D, Host-to-Array, Unified Memory y demás modalidades; identificar además memoria pageable, pinned, device, array o managed. |
| **P0** | Validación y presentación segura de centinelas unsigned en todos los informes y exportaciones. | Evitar interpretar `-1` como una medida ordinaria cuando representa `UINT64_MAX`; conservar el valor original y su semántica. |
| **P1** | Histogramas de latencia, percentiles y detección de outliers para transferencias, runtime, overhead y sincronización. | Detectar colas largas, llamadas anómalas y eventos dominantes que las medias ocultan. |
| **P1** | Decodificación semántica de los tipos de sincronización. | Identificar qué clase de espera se observa, sin atribuir automáticamente el tiempo a CPU bloqueada o GPU ociosa. |
| **P1** | Timeline combinado con dominios de reloj independientes y calibración explícita cuando exista. | Visualizar host, motor y Nsight en paneles/timelines relacionados sin inventar correlaciones ni comparar timestamps incompatibles. |
| **P2** | Integración de Nsight Compute para perfiles selectivos de kernels. | Analizar eficiencia interna: ocupación, throughput, memoria, stalls y métricas de ejecución, más allá de duración y frecuencia. |
| **P2** | Comparación reproducible entre ejecuciones y baseline. | Detectar regresiones en KV cache, transferencias, sincronización, kernels y rendimiento global. |

### Separación obligatoria de métricas temporales

Los informes deben presentar por separado:

- Tiempo de CPU dentro de llamadas CUDA (duración host de las APIs, cuando esté instrumentada).
- Tiempo de ejecución de kernels (intervalos GPU de Nsight).
- Tiempo de transferencias (intervalos GPU de memcpy/memset).
- Tiempo de sincronización (actividad y tipo de sincronización observados).
- Tiempo total de la petición (reloj del servidor/motor).

**Regla de interpretación:** estas magnitudes no se suman directamente para producir un supuesto tiempo total. Pueden solaparse, representar esperas distintas o pertenecer a dominios temporales diferentes. Todo agregado debe declarar fuente, reloj, unidad, ventana y política de solapamiento.

### Evidencia C07 que motiva este trabajo

La captura C07 contiene las tablas `ENUM_CUDA_MEMCPY_OPER` y `ENUM_CUDA_MEM_KIND`; por tanto, el importador puede resolver los valores mediante los metadatos del propio SQLite, sin codificar etiquetas numéricas a ciegas. La distribución observada fue:

| Operación | Memoria origen → destino | Operaciones | Bytes | Duración acumulada |
|---|---|---:|---:|---:|
| Host-to-Device (`HTOD`) | Pageable → Device | 330 | 945.171.456 (901,3 MiB) | 113,028 ms |
| Device-to-Host (`DTOH`) | Device → Pinned | 260 | 20.590.592 (19,63 MiB) | 2,025 ms |
| Host-to-Device (`HTOD`) | Pinned → Device | 261 | 11.206.352 (10,69 MiB) | 1,328 ms |
| Device-to-Host (`DTOH`) | Device → Pageable | 8 | 8.781.824 (8,37 MiB) | 0,990 ms |

La primera categoría concentra aproximadamente el 95,9 % de los bytes y el 96,4 % de la duración acumulada de memcpy de esta captura. Es una prioridad de investigación, no una conclusión causal: hay que inspeccionar distribución, tamaños y outliers antes de atribuir el coste a pageable memory o a una ruta concreta.

## Fase F — Release y mantenimiento

- [x] PRs separados por responsabilidad y dependencias explícitas.
- [x] CI verde en los commits actuales de PR #150–#153 y Tandem.cpp #1.
- [ ] Resolver revisiones y fusionar PRs en orden: #150 → #151 → #152 → #153; integrar Tandem.cpp #1 en su repositorio según revisión. No fusionar sin autorización.
- [ ] Etiquetar versión y publicar notas de release.
- [ ] Probar instalación desde release/tag, no solo desde checkout.
- [ ] Definir compatibilidad Linux/Python/CUDA/Nsight y matriz de versiones.
- [ ] Documentar privacidad, permisos, overhead y datos capturados.
- [ ] Definir mantenimiento de esquemas y compatibilidad hacia atrás.
- [ ] Declarar NEPENTHES funcional completo solo después de superar todos los gates anteriores.

## Orden operativo subordinado al INDEX

Este ROADMAP es un anexo técnico: `research/moe/tandem.cpp/NEPENTHES-INDEX.md` gobierna prioridades, estado y decisiones. Si este documento diverge, prevalece el INDEX.

Orden vigente, siempre subordinado al INDEX:
1. Reconciliar la integración llama.cpp mediante [PR #10](https://github.com/robertosantosx2/llama.cpp/pull/10): revisar semántica/diff sobre upstream, lifecycle, concurrencia, JSONL/NVTX y conseguir CI CUDA verificable.
2. Implementar el productor NVTX batch de Tandem.cpp siguiendo LEONES issue #212 y la especificación draft [Tandem.cpp PR #6](https://github.com/robertosantosx2/tandem.cpp/pull/6); emitir markers en la misma frontera que `BatchScope`, opt-in y RAII.
3. Ejecutar tests/CI exactos y validar la cadena token → actividad GPU → miembros request con el importer común. No inventar correlación para workers sin identidad.
4. Solo después de cerrar gates remotos, MSI: C07 captura emparejada NVTX/Nsight/CUPTI y C08 baseline/tratamientos emparejados.
5. Aceptación por motor y release con evidencia, límites, overhead, cobertura y hashes.

Las campañas históricas de Tandem.cpp y MSI que aparecen en este anexo no adelantan ni sustituyen esos gates.

## Definición de «funcional completo»

NEPENTHES se considerará completo cuando una instalación limpia pueda envolver una inferencia real, activar las sondas del motor, capturar host/GPU/Nsight, conservar los artefactos y hashes, importar tanto eventos JSONL como actividades CUPTI, generar un informe navegable con tablas y gráficas, pasar su verificador y ofrecer resultados reproducibles sin atribuciones o correlaciones inventadas.


## Registro de campañas

El estado experimental, IDs C00–C09, resultados de la primera inferencia instrumentada y criterios de las campañas siguientes se mantiene en [NEPENTHES-CAMPAIGNS.md](NEPENTHES-CAMPAIGNS.md).


## P0 — decodificación de enums Nsight (implementación remota)

La rama `feat/nepenthes-nsys-enum-decode-20261119` añade lectura dinámica de `ENUM_CUDA_MEMCPY_OPER` y `ENUM_CUDA_MEM_KIND`, columnas consultables para copy kind/src/dst kind, metadatos de tablas y preservación de valores desconocidos/sentinelas en JSON original. Se aplica a importación emparejada y Nsight-only.

Estado: código y fixtures publicados en una rama GitHub; CI pendiente. La prueba contra la SQLite C07 real y la auditoría de versiones Nsight siguen pendientes. No se declara P0 aceptado hasta superar ambas.


## C07 — NVTX request markers and explicit clock pairing (implementation branch)

La rama `feat/nepenthes-nsys-nvtx-correlation-20261119` extiende el importador para leer `NVTX_EVENTS`, extraer tokens explícitos y emparejar los markers host/Nsight por `(token, phase)`. Calcula offset/drift host-monotonic↔Nsight con incertidumbre basada en el bracket de la llamada NVTX. Solo asigna kernels/transferencias a una petición como `windowed` cuando una única ventana explícita contiene todo el intervalo; ventanas solapadas se rechazan.

Estado: implementación y fixtures sintéticos en rama; CI pendiente. La captura C07 real sigue siendo necesaria para verificar la versión del schema Nsight, el texto de NVTX y la calibración del reloj en el MSI. No se declara C07 cerrado.


## Estado de aceptación actualizado — 2026-11-19

### Aceptado en GitHub (software/CI)

- [x] AIPerf-first C08: LEONES PR #197 fusionada (c2f0eb92fc50bbf8bb95d35f540927589f034544); 519 pruebas pasadas y gates de repositorio verdes.
- [x] Adaptadores de telemetría y C07 importer: LEONES PR #198 fusionada (8812aa6c0d2dea972acb8fd27508146d74fd0c2e); CI de importador, AIPerf/telemetría, monitor upstream y gates generales verdes.
- [x] Contrato de evidencia: command fingerprint, hash de artefactos, separación de duración de campaña y latencia por petición, RSS del proceso servidor, redacción de datos sensibles y retención opt-in del log bruto.

### Pendiente de aceptación física

- [ ] **C07 real en MSI:** compilar el llama.cpp rebased con sondas; ejecutar servidor con correlation token; capturar NVTX_EVENTS y CUPTI con Nsight; verificar al menos dos pares de calibración, bracket host y atribución windowed sin inferencia por proximidad.
- [ ] **C08 en MSI:** baseline off y tratamientos jsonl, nsys, combined; perfil standard; mínimo tres pares por condición; mismo modelo, hash, prompt/dataset, contexto y comando de workload; mediana e IQR.
- [ ] Gate C08: decode overhead ≤5 % para aceptación normal; 5–8 % requiere advertencia/revisión; >8 % no se acepta como perfil standard. Informar por separado throughput, TTFT, duración de campaña, latencia media de petición, RAM, RSS y VRAM.
- [ ] Cobertura física de MoE routing/experts, prefetch/cache, workers CPU, transferencias, OOM/fallback y sincronización.
- [ ] Aceptar decodificación de enums Nsight contra una SQLite real de la versión instalada; mantener valores desconocidos y sentinelas sin reinterpretarlos.

### Rebase llama.cpp

- [~] [Fork PR #6](https://github.com/robertosantosx2/llama.cpp/pull/6): rama RC1 actualizada hasta upstream `9a080f44b503c64f66c84a6274b9d9ee5d5b09d5` mediante [PR #7](https://github.com/robertosantosx2/llama.cpp/pull/7), ya fusionada. La rama RC1 contiene 31 commits por delante y 0 por detrás de `master`, con 23 archivos de diff. HEAD `d692b04bac286d89cc8ea394728e54149f5fa3c7`: incluye bypass de reloj cuando tracing está desactivado, test de regresión, filtros CI `push` CPU/C ABI y guard para que NVTX tampoco emita marcadores con tracing desactivado. CI para este HEAD ya se ha disparado (runs 44589790856, 44589790779 y asociados); runtime trace, CUDA dedicada/general, CPU, server, WASI/WASM y calidad estaban in progress en la última consulta. Aún no hay conclusiones. En el anterior `246fbbd4...`, runtime trace, CUDA dedicada/general, HIP, CPU, server, WASI/WASM y calidad pasaron; MUSA falló por descarga externa y runners self-hosted quedaron pendientes. PR #6 sigue en borrador; no fusionar ni actualizar el submódulo hasta cerrar gates y revisión final.
- [ ] Actualizar el fork master y el gitlink subprojects/llama.cpp solo tras aceptar PR #6.
- [ ] Cerrar los PRs de componentes duplicados únicamente después de que su contenido esté presente en la rama integrada y sus checks estén cubiertos.

**Regla de cierre:** el código integrado con CI verde no equivale a NEPENTHES funcional completo. La etiqueta funcional completo requiere C07 y C08 aceptados con artefactos físicos, auditoría de cobertura, overhead dentro del umbral y verificación del bundle.


### AIPerf warm-up provenance correction — 2026-11-19

Post-merge audit found that the wrapper had not explicitly passed AIPerf's warm-up request count. LEONES PR #199 is now merged as `109e3073cd0040a5ba86b906e71e003959f72d3c`: the runner defaults to one explicit warm-up request, records it in the workload command fingerprint and manifest, and the evidence builder rejects manifests without that field. CI passed **572 tests** plus all release/runtime gates. This is still software acceptance only; no C08 performance result is claimed.


### Perfiles adaptativos — 2026-11-19

LEONES PR #200 se integró como `ed0535c2bf1bc7025cde1534e395ed1c3bbac581` tras **575 pruebas pasadas** y gates de release/runtime verdes. `moe-deep` muestrea host a 100 ms mientras hay requests activos y a 1 s en reposo, usando únicamente eventos explícitos `request_start/request_end`; activa Nsight automáticamente si está instalado. `latency-critical` desactiva muestreo periódico de host y Nsight. La selección de sondas internas del motor aún no está filtrada por perfil; se mantiene como trabajo pendiente en la capa llama.cpp. Ninguno de estos perfiles tiene todavía medición física de overhead en MSI.

### Actualización RC1 — 2026-11-19

- [x] Sincronizar el fork `master` con upstream `ggml-org/llama.cpp` en `9a080f44b503c64f66c84a6274b9d9ee5d5b09d5`.
- [x] Integrar el commit upstream OpenVINO en la rama RC1 mediante PR #7.
- [x] Evitar lecturas de reloj monotónico en `ScopedEvent` cuando el tracing está desactivado; añadir regresión automatizada.
- [x] Corregir filtros del workflow para que cambios en el puente CPU C y el ABI NEPENTHES disparen CI al hacer push a master.
- [~] CI del HEAD `246fbbd4b81cb8c307fa12aeed6d86317f53d3cc` visible: NEPENTHES runtime trace y sus jobs CPU/CUDA (incluida comprobación NVTX v3), CUDA general, HIP, CPU, server, WASI/WASM, Behavior, Code Style y EditorConfig pasan. La ejecución combinada CUDA/HIP/MUSA falla únicamente en `musa/Dependencies`: timeout de `dl.mthreads.com` y paquetes MUSA no localizados; los jobs CUDA y HIP de esa misma ejecución pasan. Self-hosted CUDA/Vulkan/OpenVINO/WebGPU/CPU siguen queued/pending al último sondeo. No cerrar gates hasta que terminen o se clasifiquen.
- [ ] Revisión final de concurrencia, lifecycle del sink, JSONL y atribución request/NVTX.
- [ ] Fusionar PR #6 solo tras gates remotos aceptados; después actualizar gitlink en LEONES.
- [ ] MSI: build Linux/CUDA, C07 con NVTX+Nsight, y medición C08 de overhead. No ejecutar antes de cerrar los gates remotos.


### Hallazgo de auditoría y corrección RC1 — 2026-11-19

- [x] Restaurar `GGML_OP_CONV_2D` en `ggml_op_alloc_size_may_expand()`: el diff NEPENTHES lo había eliminado accidentalmente pese a que upstream lo conserva. Corrección en llama.cpp commit `33e0d0a578c48b0a31616fd1b72fd255f12e39a4`.
- [ ] Revalidar todos los checks contra el nuevo HEAD `33e0d0a578c48b0a31616fd1b72fd255f12e39a4`; los checks del HEAD anterior no cuentan como aceptación de este cambio.
- [ ] Continuar revisión final del diff y runtime; PR #6 sigue draft, sin merge ni actualización del gitlink.
- [ ] Solo tras aceptación remota: sincronizar gitlink y pasar al MSI para build Linux/CUDA, C07 NVTX+Nsight y C08 overhead medido.


### CI parcial del HEAD corregido — `33e0d0a578c48b0a31616fd1b72fd255f12e39a4` (2026-11-19)

- [x] Tests NEPENTHES de contrato, JSONL bounded sink y puente CPU.
- [x] Build instrumentado llama-server CPU.
- [x] Verificación NVTX v3 activa en configuración CUDA.
- [x] CUDA y HIP del workflow general.
- [x] Behavior Check Ubuntu/Windows, WASI, WASM, WebGPU, Code Style y EditorConfig.
- [~] CUDA llama-server específico, CPU general, Server y algunos runners backend: en curso al último sondeo.
- [!] MUSA Dependencies bloqueado por timeout de `dl.mthreads.com`; el build MUSA fue omitido. No tratar como fallo de código CUDA/NEPENTHES.
- [ ] Esperar el cierre de los jobs pendientes y clasificar resultados antes de aceptar la PR #6.

### Actualización de aceptación llama.cpp RC1 — HEAD `33e0d0a578c48b0a31616fd1b72fd255f12e39a4` (2026-11-19 19:16 UTC)

Esta actualización supersede los estados parciales anteriores de CI para este HEAD concreto.

- [x] NEPENTHES trace contract, bounded JSONL sink, CPU bridge y build instrumentado CPU.
- [x] Build CUDA instrumentado de `llama-server` y comprobación NVTX v3.
- [x] CUDA/HIP general, CPU general Ubuntu/Windows, Server Ubuntu/Windows y HIP quality.
- [x] Behavior Check, WASI, WASM, Code Style y EditorConfig.
- [!] MUSA: fallo en instalación de dependencias externas (`dl.mthreads.com` timeout y paquetes ausentes); compilación omitida. No clasificar como regresión de CUDA/NEPENTHES.
- [~] Self-hosted KleidiAI, CPU, IBM, Vulkan, OpenVINO, Metal, CUDA y WebGPU, y Models Backend Check: siguen queued. Reconsultar antes de aceptación.
- [ ] Revisión final runtime/diff y clasificación de todos los checks restantes.
- [ ] Merge de PR #6 solo tras cerrar gates y revisión; no actualizar gitlink antes del merge.
- [ ] MSI: build Linux/CUDA, C07 con NVTX+Nsight y C08 overhead emparejado. Sin pruebas físicas declaradas todavía.

Estado de PR #6: abierta, draft, no fusionada; HEAD `33e0d0a578c48b0a31616fd1b72fd255f12e39a4`; rama 33 ahead / 0 behind respecto a fork `master`; 23 archivos modificados.

## Secuencia de cierre validada — 2026-11-19

### 1. Datos LEONES y submódulo

- [x] #203/#205: confirmar 8/8 workflows post-merge del commit `28de2459a76433b90628bb5dff7e7703a789d9a1`; migración 006 e importador v1.1 presentes en `main`.
- [x] #206: añadir el fork como submódulo con gitlink independiente del HEAD de fork; merge `c98deebfc169b8d860d4e887b1f3ffb068342b00`; CI de integridad y release gates verdes.
- [x] Mantener el gitlink en `76f186df71a41abb3ee20fffedee31ca5dbc7d9f` hasta aceptar el runtime instrumentado.

### 2. Integración llama.cpp — gate actual

- [ ] Reconciliar la pila nativa #1 → #2 → #3 contra upstream `c406f4367e19bea7930e7f74e1984c9acc6d44bf`; fork master `9a080f44b503c64f66c84a6274b9d9ee5d5b09d5` está 3 commits detrás.
- [ ] Comparar la pila nativa con la rama acumulativa RC1/PR #6. Hay solapamiento de instrumentación y diferencias reales en sink, event header, CUDA, CPU y server; elegir una sola línea canónica antes de merge.
- [ ] Rebase secuencial, resolver conflictos y volver a ejecutar CI después de cada capa. No actualizar el gitlink durante esta fase.
- [ ] Revisar el contrato JSONL del productor frente a ambos importadores. El sink RC1 emite schema 1.0; el importador de trazas acepta 1.0 + correlation fields; el importador emparejado admite metadata tipada 1.1 y conserva `raw_json`.
- [ ] Revisar cobertura de eventos y semántica de labels, duración, IDs, unsigned, lifecycle, sink_summary, pérdidas y errores de escritura.

### 3. Cerrar el circuito de captura en GitHub

- [ ] Integrar el capturador de llama-server, NVML y recolector universal mediante un único `run_id`, timestamps monotónicos por fuente y calibración explícita; nunca inferir correlación por proximidad.
- [ ] Verificar que cada importador conserva originales, hashes, procedencia y campos desconocidos; no fabricar request/kernel links.
- [ ] Preparar un preflight reproducible que valide binario, endpoint, modelo/hash, perfil, permisos, Nsight/NVML disponibles, disco libre, configuración redactada y destino de artefactos.
- [ ] Preparar comando de campaña y manifiesto con motor/commit, modelo/hash, backend/driver, hardware, contexto, prompt/dataset, sampling, perfil, warm-up, repeticiones, relojes y hashes de artefactos.

### 4. Preparar C07 sin MSI

- [ ] Scripts y configuración para habilitar NVTX v3 solo con tracing activo.
- [ ] Validador que exija markers NVTX reales, al menos dos pares de calibración, brackets host y matching por token+phase.
- [ ] Rechazar ventanas solapadas/ambiguas; asignar actividad como windowed solo cuando una única ventana explícita contenga todo el intervalo.
- [ ] Comprobación automática de integridad SQLite, hashes, cobertura CUPTI, pérdidas JSONL y procedencia.
- [ ] Instrucciones de captura reproducible y criterios de aceptación visibles antes de pedir intervención física.

### 5. MSI — solo después de los gates remotos

- [ ] Sincronizar el commit exacto aceptado y compilar Linux/CUDA en la RTX 3050.
- [ ] Ejecutar C07 con llama-server instrumentado y Nsight Systems; conservar JSONL + SQLite de la misma ejecución.
- [ ] Revisar markers, calibración, integridad, pérdidas y atribución. C07 solo se acepta con evidencia real; CI sintética no sustituye esta prueba.

### 6. C08 y expediente final

- [ ] Baseline OFF y tres tratamientos instrumentados (JSONL, Nsight y combinado), mínimo tres pares por condición; misma identidad de modelo/engine/workload y warm-up excluido.
- [ ] Medir TTFT, decode tok/s, ITL si está disponible, duración de petición/campaña, RSS del servidor, RAM, VRAM device-wide y overhead por condición.
- [ ] Aplicar gate standard: decode overhead ≤5%; 5–8% requiere excepción/revisión; >8% bloquea aceptación standard.
- [ ] Archivar manifiestos, logs, hashes, capturas, resultados por repetición, medianas/IQR/MAD y limitaciones.
- [ ] Actualizar INDEX y roadmap únicamente con resultados físicos confirmados; no declarar NEPENTHES completo antes de cerrar C07/C08 y cobertura.

**Límite actual:** trabajo remoto en GitHub. No requiere el MSI para el rebase, revisión, pruebas contractuales, preflight, manifiestos ni scripts. El MSI se reserva para C07 real y C08 medido.


### Auditoría del delta upstream — 2026-11-19 (verificación commit a commit)

- [x] Confirmados los dos gates post-merge del manifiesto: V1 Complete Gate run `44612579699` y submodule integrity run `44612579719`, ambos `success`.
- [x] Inspeccionados los tres commits entre fork master `9a080f44b503c64f66c84a6274b9d9ee5d5b09d5` y upstream `c406f4367e19bea7930e7f74e1984c9acc6d44bf`:
  - `53ecea05a0728e133478b06b3d543b6fcfaa418e`: fix YuE2 en `tools/mtmd/mtmd.cpp`; no solapa con probes.
  - `7fce5439fe451cd48340b112ec37d2befe02c776`: soporte BF16 de ROPE/SET_ROWS en CPU y CUDA, capability checks y tests. Es funcionalidad upstream que debe conservarse; toca cuatro rutas instrumentadas por RC1: CPU `ggml-cpu.c`/ `ops.cpp`, CUDA `ggml-cuda.cu` y `tests/test-backend-ops.cpp`.
  - `c406f4367e19bea7930e7f74e1984c9acc6d44bf`: OpenCL int8 KQ para flash attention descompuesta; kernels/build OpenCL sin solapamiento directo con las sondas actuales.
- [x] La comparación fork→upstream arroja 3 commits y 18 archivos. Ocho rutas coinciden con el diff acumulativo RC1: CPU, CUDA, Metal, OpenVINO, Vulkan, ggml core y tests. La coincidencia de ruta no implica conflicto textual, pero sí exige rebase semántico y revisión del control flow.
- [x] Actualizado el manifiesto `docs/subprojects/NEPENTHES/LLAMA-CPP-UPSTREAM.json` en commit `f7974d20bf90348552e51c7ac284f6adca57bca1`, registrando commits, alcance, solapamientos, estado de CI y política de reconciliación.
- [ ] Reconciliar RC1 con upstream: aplicar primero la funcionalidad BF16 y sus tests, preservar YuE2/OpenCL sin cambios, reubicar/reaplicar sondas sobre el control flow final y revisar especialmente los límites de las funciones CPU/CUDA afectadas.
- [ ] Ejecutar CI completa sobre el HEAD reconciliado y comparar el contrato de eventos antes/después: no deben duplicarse eventos ni cambiar sus límites de ciclo de vida.
- [ ] Solo después decidir si RC1 sustituye definitivamente a #1–#3; cerrar la alternativa no elegida tras demostrar equivalencia de cobertura y conservar los cambios exclusivos útiles.
- [ ] Mantener el gitlink LEONES en `76f186df71a41abb3ee20fffedee31ca5dbc7d9f` hasta completar la aceptación remota. MSI sigue fuera del circuito.

**Decisión técnica:** conservar RC1 como línea de trabajo candidata, pero no declararla canónica ni fusionable todavía. El cambio BF16 es funcionalidad de upstream, no una modificación descartable; la integración debe mantenerla y recolocar las sondas. El fix YuE2 y las mejoras OpenCL se incorporan íntegramente.


### Revalidación de PR #6 contra upstream actual — 2026-11-19 (sondeo posterior)

- La API de GitHub confirma que PR #6 sigue abierta y draft; HEAD `33e0d0a578c48b0a31616fd1b72fd255f12e39a4`, base fork `master` en `9a080f44...`, 33 commits, 23 archivos, mergeable según GitHub.
- Comparación directa con upstream `c406f436...`: **33 commits ahead y 3 behind**, merge-base `9a080f44...`. Esto confirma que PR #6 no está rebased sobre el upstream actual, aunque esté al día con el fork master.
- CI asociada al HEAD consultado: runtime trace, CPU, server, WASI/WASM, HIP quality, Behavior y estilo pasan. En el workflow combinado, CUDA y HIP pasan; MUSA falla en el paso `Dependencies` antes de compilar por dependencia externa. Los runners self-hosted y Models Backend Check continúan queued.
- La lectura de los pasos del job MUSA confirma que `Build with native CMake MUSA support` fue omitido por fallo previo de dependencias; no clasificar como regresión de código NEPENTHES ni como build MUSA validado.
- La PR conserva un historial con commits de intentos anteriores de port/rebase, pero su relación efectiva con upstream se determina por el merge-base y la comparación anterior, no por los mensajes de esos commits. No se declara rebase completado.
- Próxima operación: preparar una rama de integración limpia cuyo padre sea exactamente `c406f436...`, portar solo los cambios NEPENTHES revisados, mantener intactos BF16/YuE2/OpenCL, ejecutar CI y comparar cobertura/eventos. No hacer merge de PR #6 ni de #1–#3 en su estado actual.


### Integración limpia sobre upstream actual — PR #10

- [x] Fast-forward seguro del fork `master`: `9a080f44...` → `c406f4367e19bea7930e7f74e1984c9acc6d44bf`. Sin force-push ni cambios NEPENTHES sobre master.
- [x] Creada rama `nepenthes/integration-upstream-c406f436` directamente desde el commit upstream actual.
- [x] Portadas las 23 rutas del candidato RC1 mediante aplicación de hunks sobre el contenido de cada archivo en upstream actual. Todos los contextos/hunks encontraron coincidencia exacta; no se sustituyeron archivos upstream completos.
- [x] Commit de integración: `0f3fa24ba4e417629ffebd7bbf6a7bcccb8c4659`.
- [x] PR #10 abierta en draft: https://github.com/robertosantosx2/llama.cpp/pull/10
- [x] Comparación contra upstream: 1 commit ahead, 0 behind, 23 archivos (+1252/-1). El diff no incluye los tres commits upstream porque la rama parte del SHA actual.
- [~] CI de PR #10 no está globalmente aceptada en el último estado verificado: `trace-and-cpu-build` y checks generales CPU/Windows/arm64 en éxito; varios jobs GPU, incluido `gpu-cuda`, y runners de alto rendimiento cancelados. Revisar/relanzar solo los checks relevantes sobre HEAD exacto `0f3fa24` y registrar resultados antes de merge.
- [ ] Revisar los resultados completos, especialmente la compilación CUDA/NVTX y las pruebas específicas NEPENTHES.
- [ ] Auditoría semántica del cambio BF16 en ROPE/SET_ROWS y confirmar que las sondas se limitan a observar sin alterar los resultados funcionales.
- [ ] Comparar cobertura de PR #10 con #1–#3 y #6; cerrar candidatos antiguos solo tras equivalencia demostrada.

**Estado:** integración limpia preparada en PR #10, todavía draft y no aceptada. HEAD `0f3fa24`, base `c406f43`; CI parcial con jobs GPU/CUDA cancelados. El gitlink de LEONES sigue en el pin estable anterior. La reconciliación remota precede cualquier intervención del MSI.
