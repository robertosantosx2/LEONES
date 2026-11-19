## NEPENTHES RC1 — correlación, overhead y aceptación universal (2026-11-19)

Esta sección convierte las recomendaciones de arquitectura en gates verificables. Ninguna correlación temporal se inferirá por proximidad.

### A. Correlation token y calibración de relojes — P0

- Añadir `correlation_token` opcional por request, generado en el límite de entrada (UUID aleatorio o contador monotónico con scope de proceso/run y protección frente a reutilización).
- Emitirlo en `request_start` y conservarlo sin reemplazar `run_id`, `request_id`, `trace_id` ni IDs nativos.
- Propagarlo hacia workers/backend solo mediante contexto explícito y seguro. Si una capa no puede recibirlo, declarar `correlation_status=unavailable`; no reconstruirlo.
- Para Nsight, probar primero NVTX range/marker con el token como payload/metadata y verificar que la versión de Nsight Systems/CUPTI lo conserva en el artefacto importable. No afirmar que un env var por sí solo correlaciona kernels. CUPTI external correlation IDs solo si la API y el camino de ejecución permiten propagación real; documentar límites por backend.
- Añadir `clock_calibration` al inicio y fin de cada run: pares monotonic_ns, unix_epoch_ns y timestamp de referencia Nsight cuando esté disponible; incluir fuente, resolución, incertidumbre estimada, drift y método.
- No asumir transformación lineal válida durante todo el run: calibrar ambos extremos, estimar offset/drift, comprobar residual y marcar intervalos no calibrables.
- Toda relación request→GPU debe declarar `attribution_level`: `exact` (token compartido en evento/marker), `windowed` (ventana delimitada por eventos explícitos, sin identidad de kernel), `device_wide` (muestra global de dispositivo) o `estimated` (derivación documentada). `windowed` no equivale a atribución exacta de kernels.
- Regla dura: sin token compartido o calibración validada, no unir eventos de relojes distintos; reportar `uncorrelated`.

**Gate P0:** test de propagación token por cada límite instrumentado; round-trip en Nsight; calibración de ambos relojes con error residual cuantificado; casos de pérdida, token ausente, drift y relojes no sincronizados.

### B. Overhead como gate formal — P0

Protocolo baseline vs instrumentado:
1. Mismo commit del motor, modelo y SHA-256 del modelo, cuantización, prompt/dataset, tokenizer, sampling, contexto, hardware, driver, backend y flags.
2. Warm-up idéntico y excluido de la muestra; al menos 3 repeticiones por condición (objetivo recomendado: 5 cuando el tiempo lo permita).
3. Alternar orden baseline/instrumentado o usar bloques emparejados para reducir sesgo térmico y de carga.
4. Separar condiciones: OFF; sink JSONL sin Nsight; Nsight sin sink adicional cuando sea posible; ambos juntos; perfiles standard/full.
5. Reportar por repetición y agregado: tokens/s decode, TTFT, ITL, duración, RSS pico, VRAM pico, CPU y eventos perdidos; mediana, IQR y MAD.
6. Medir coste del sink y Nsight por separado. No sumar porcentajes de overhead si las interacciones no son aditivas.
7. Conservar manifiesto, logs y artefactos; declarar thermal/power state y ejecuciones excluidas.

**Gate standard inicial:** overhead relativo de decode <=5% como objetivo de aceptación; 5–8% requiere excepción explícita y perfilado; >8% bloquea la etiqueta ACCEPTED hasta optimización o reclasificación del perfil. TTFT y memoria se reportan como gates independientes; no ocultar regresiones aunque decode cumpla. Los umbrales son configurables por hardware y perfil, versionados en el manifiesto. Full/diagnostic puede aceptar overhead mayor, pero nunca llamarlo low-overhead.

### C. Contrato de eventos tipado — P0

Añadir campos opcionales versionados y validados:
- `backend`: cpu, cuda, metal, vulkan, rocm, sycl, other, unknown.
- `memory_kind`, `memcpy_kind`, `sync_type`, `kv_op`, `moe_op`, `operation_kind`.
- `correlation_token`, `clock_domain`, `attribution_level`.
- `source`, `source_version`, `native_enum_value`, `normalized_enum_name`, `enum_table_version`.
- `duration_ns`, `bytes`, `device_id`, `stream_id`, `queue_id` solo cuando la fuente los exponga.

Los enums Nsight/CUPTI se decodifican mediante tablas oficiales versionadas (incluida `ENUM_CUDA_MEMCPY_OPER` / tabla equivalente observada en el schema real), conservando siempre valor numérico original, nombre normalizado, versión de tabla y estado unknown. No asumir que `UINT64_MAX` es un enum válido: tratarlo como sentinel unsigned, preservarlo exactamente y marcarlo unknown/not_applicable según contexto. No convertirlo a signed ni mapearlo por proximidad.

### D. Perfiles y sampling adaptativo — P1

- `smoke`: mínimo de eventos, una petición, verificación de contrato.
- `standard`: request lifecycle, sink asíncrono, sondas de bajo coste; sin muestreo host agresivo ni Nsight por defecto.
- `full`: sondas extendidas y Nsight explícito; overhead medido.
- `moe-deep`: routing, expertos, cache, prefetch/residencia/eviction y esperas, solo donde existan hooks reales.
- `latency-critical`: sink del motor y request markers; desactiva muestreo host y Nsight, sin spans por token salvo opt-in.
- Sampling adaptativo puede elevar frecuencia al abrir/cerrar request o al detectar actividad, pero debe registrar frecuencia objetivo/real, reglas, transiciones y muestras descartadas. Nunca descartar eventos de ciclo de vida críticos; el sampling no puede alterar semántica ni bloquear el runtime.

### E. Pipeline de análisis — P1

Orden de entrega:
1. Decodificación de memcpy/memory enums, centinelas unsigned y cobertura de tablas.
2. Timeline dual host monotonic / Nsight-GPU, con calibración, incertidumbre y huecos visibles.
3. Hot path por request: prefill → decode/token → operaciones/kernels dominantes → transferencias y sincronizaciones dominantes; solo exact cuando la correlación lo permita.
4. Comparador de campañas con mediana, IQR, MAD, muestras individuales y protocolo; no solo medias.
5. Histogramas de latencia/bytes/duración y diagnósticos de outliers reproducibles.

### F. Integración y gobierno RC1 — P0

- Rama de integración creada en el fork: `nepenthes/rc1`. Se inicia desde el master del fork y será el candidato acumulativo; no altera master ni fusiona automáticamente PRs.
- La pila runtime sigue revisándose en orden #1 → #2 → #3. Antes de absorber cada PR: revisar base/head, diff, conflictos con upstream y CI. No actualizar gitlink LEONES hasta que la integración sea coherente y revisada.
- Cada incorporación a RC1 debe registrar SHA de origen, SHA resultante, PR, CI y diferencias respecto a upstream. La rama RC1 no sustituye los PRs de revisión.
- Manifiesto de campaña obligatorio generado al finalizar `nepenthes run`: schema/version, run_id, model identifier + SHA-256, motor y commit, LEONES commit, backend/driver/runtime, hardware, configuración completa redactada, comando efectivo sin secretos, perfil, seeds, warm-up, repeticiones, timestamps/calibración, hashes SHA-256 de todos los artefactos, versiones de AIPerf/Nsight/CUPTI y estado de gates.
- Privacidad: prompts/completions, API keys, headers, URLs con credenciales, hostname y datos personales excluidos por defecto. Identificadores de request pseudónimos; UUID de GPU permitido solo bajo configuración explícita. Retención configurable; el manifiesto declara política y fecha de expiración. No borrar evidencia histórica sin política y autorización.
- La retención por defecto debe ser configurable por instalación/campaña; documentar local-only como modo predeterminado y exportación externa siempre explícita.

### G. Universalidad — P2

Definir interfaces desacopladas:
- Backend plugin: capabilities, event source, clock domain, device enumeration y tests de contrato (CUDA, Metal, Vulkan, ROCm, CPU; otros se incorporan por evidencia).
- Sink plugin: JSONL canónico, OTLP, Prometheus remote-write y binario compacto. JSONL sigue siendo evidencia interoperable primaria en RC1; los sinks remotos/compactos son opt-in.
- Engine adapter: vLLM, TensorRT-LLM y motores no llama mediante adaptadores que traduzcan eventos nativos sin fingir instrumentación interna inexistente.
- Los plugins declaran versión, cobertura, semántica, coste, limitaciones y estado de correlación. No afirmar soporte universal hasta que cada backend pase sus fixtures y pruebas reales.

### H. Criterio de «funcional completo»

No se puede declarar funcional completo hasta superar:
- cobertura contractual de eventos y contadores de pérdida;
- C07: captura emparejada JSONL + Nsight con calibración/token y niveles de atribución verificables;
- `nepenthes verify` completo sobre artefactos limpios;
- C08: protocolo baseline/instrumentado con overhead por sink y Nsight separado, dentro del umbral del perfil o excepción aprobada;
- decodificación semántica de enums y preservación unsigned;
- manifest de campaña reproducible y hashes verificados;
- comparación multi-run con mediana/IQR;
- CI Linux limpia y builds requeridos;
- validación física CUDA/Nsight en RTX 3050 pendiente hasta ejecutar en el MSI. CI no sustituye esa prueba.

### Secuencia inmediata revisada (2–4 semanas)

1. Cerrar C07 y `nepenthes verify` completo.
2. Implementar correlation token mínimo y calibración dual de relojes.
3. Ejecutar C08 de overhead (baseline, sink, Nsight, combinado).
4. Decodificar enums Nsight/CUPTI, unsigned sentinels e histogramas.
5. Revisar e integrar ordenadamente PR #1 → #2 → #3 en `nepenthes/rc1`; resolver drift upstream antes de mover gitlink.
6. Completar manifest de campaña, privacidad/retención y comparador.
7. Habilitar adaptadores/plugins adicionales tras cerrar gates de RC1; no retrasar el núcleo por prometer universalidad sin pruebas.


### Implementación parcial publicada en llama.cpp PR #4

- PR runtime: https://github.com/robertosantosx2/llama.cpp/pull/4 (draft, apilada sobre #3).
- Token uint64 monotónico asignado por proceso a cada tarea/slot del servidor; request_start y request_end comparten el token y conservan el request_id nativo.
- Eventos clock_calibration al inicio y al cierre del sink JSONL.
- Los marcadores de calibración y request guardan el par host monotónico/Unix en el punto de emisión, evitando que la cola del writer desplace el timestamp.
- Los eventos hot-path no correlacionados conservan el reloj monotónico y no fuerzan una lectura de reloj de pared.
- **Límite actual:** el token aún no se propaga a graph/worker/kernel, deliberadamente por el batching multi-slot. No hay NVTX/CUPTI external correlation ni round-trip Nsight demostrado; C07 continúa abierto.
- Estado CI PR #4 al 2026-11-19: workflow NEPENTHES y CUDA compile en cola; no hay resultado de build para esta PR todavía.
- No se ha ejecutado MSI. La validación física sigue reservada para cuando C07/CI estén listos.

La implementación de PR #4 es una primera capa de identidad y calibración host, no la correlación request→kernel requerida para cerrar C07.


### NVTX/C07 implementation progress (2026-11-19)

The llama.cpp follow-up [PR #4](https://github.com/robertosantosx2/llama.cpp/pull/4) now adds optional NVTX v3 request-start/request-end markers in CUDA builds. Marker names carry the explicit correlation token; JSONL emits a companion nvtx_marker record with the host-monotonic call bracket. CPU-only builds remain independent of NVTX.

The LEONES importer follow-ups are:
- [PR #181](https://github.com/robertosantosx2/LEONES/pull/181): data-driven Nsight memcpy/memory enum decoding, preserving original values and sentinels.
- [PR #182](https://github.com/robertosantosx2/LEONES/pull/182): parse NVTX_EVENTS, match token+phase (not time proximity), calibrate host↔Nsight offset/drift, and assign GPU activity as windowed only when one explicit request window uniquely contains the full activity interval.

These are implementation branches under CI review. C07 is **not closed** until CI is green and a real Nsight SQLite capture on the MSI verifies marker schema, calibration and attribution. Overlapping windows stay ambiguous; no exact kernel attribution is inferred from NVTX alone.


### C07/C08 implementation status — 2026-11-19

- Runtime [llama.cpp PR #4](https://github.com/robertosantosx2/llama.cpp/pull/4): explicit request token, host clock calibration, optional NVTX v3 start/end markers with host-call brackets. CUDA CI is being repaired around Ubuntu mirror connectivity; real Nsight capture remains pending.
- [LEONES PR #181](https://github.com/robertosantosx2/LEONES/pull/181): data-driven Nsight memcpy/memory enum decoder; its importer regression checks are green.
- [LEONES PR #182](https://github.com/robertosantosx2/LEONES/pull/182): NVTX_EVENTS token parsing, host↔Nsight offset/drift, unique-window GPU attribution and overlap rejection; importer regression checks are green.
- [LEONES PR #183](https://github.com/robertosantosx2/LEONES/pull/183): correlation-aware verify and run-level C07/C08 status.
- [LEONES PR #184](https://github.com/robertosantosx2/LEONES/pull/184): C08 telemetry sampling, robust median/IQR/MAD and paired off/jsonl/nsys/combined gate. Synthetic tests are added; actual campaign remains MSI-dependent.

The comparator requires at least three paired repetitions, at least one warm-up and three measurement iterations per evidence file. Standard decode overhead ≤5% is the acceptance target; 5–8% requires an explicit exception; >8% blocks acceptance. The evidence records process RSS separately from system RAM and device-wide VRAM/power.

C07/C08 are implemented in GitHub branches/PRs, not accepted as physical results. The verifier distinguishes bundle integrity from run-level completion. The MSI is needed only for the real CUDA/Nsight capture, overhead campaign and final hardware-specific gates.
