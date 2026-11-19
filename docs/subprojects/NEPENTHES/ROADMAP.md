# NEPENTHES — roadmap maestro de desarrollo

**Fecha de planificación:** 2026-11-19  
**Prioridad inmediata añadida:** AIPerf como runner primario de benchmark; NVML/energía, latencia por token, dispersión y OpenTelemetry como capas complementarias.  
**Estado:** plan de trabajo; las capacidades nuevas descritas aquí no se consideran implementadas hasta aportar pruebas y capturas.

Este roadmap amplía el trabajo histórico de instrumentación llama.cpp, Tandem.cpp, CLI, Nsight/CUPTI e importación LEONES. No sustituye ni reescribe los registros de campañas anteriores.

## Principios de ejecución

1. GitHub primero: auditoría, diseño, implementación, commits, PR y CI en remoto.
2. Sin desarrollo directo en checkouts locales salvo autorización expresa.
3. Validación física posterior en el MSI y en los equipos adicionales disponibles.
4. Cada PR pequeño, con alcance, contrato, pruebas, evidencia y límites.
5. Diferenciar siempre PLANNED, IMPLEMENTED, CAPTURED, MEASURED y ACCEPTED.
6. Las fuentes externas inspiran diseño, pero sus resultados no se convierten automáticamente en medidas LEONES.

## Prioridad 1 — Inferscope: energía, NVML y latencia por token

**Máximo interés inmediato.** Investigar primero las ideas y mecanismos de Inferscope y traducirlos a requisitos verificables de NEPENTHES. No copiar código o asumir compatibilidad sin revisar licencia, API y comportamiento. Fuente de estudio: [Inferscope](https://github.com/MicheleCampi/inferscope), Apache-2.0.

### 1.1 Muestreador NVML por dispositivo

- Crear un sampler independiente del colector de eventos del motor.
- Enumerar GPU por UUID, PCI bus ID e índice; usar UUID como identidad estable cuando esté disponible.
- Muestrear potencia, temperatura, utilización, memoria y relojes cuando el driver exponga esos campos.
- Configurar intervalo, timeout, política de reintentos y cierre.
- Registrar timestamp monotónico, timestamp de pared auxiliar, dispositivo, fuente, unidad y calidad.
- Detectar huecos, errores, reset de contador y cambios de dispositivo.
- No requerir privilegios root.
- Mantener NVML opcional; fallback explícito a nvidia-smi si NVML no está disponible, con fuente distinta.

**Aceptación:** prueba con GPU presente, sin GPU, NVML inaccesible y muestras incompletas; datos por dispositivo sin atribución falsa a proceso.

### 1.2 Energía y tokens/julio

Orden de preferencia:

1. Contador acumulado de energía NVML del dispositivo, si la GPU/driver lo soportan.
2. Integración numérica de potencia muestreada (regla trapezoidal), si no existe contador.
3. Fuente externa de energía del sistema (p. ej. RAPL) como medición separada, nunca mezclada silenciosamente con energía GPU.

Registrar por cada muestra: W o mW originales, J o mJ normalizados, método, frecuencia real, intervalos faltantes, dispositivo y procedencia.

Métricas derivadas:

- Energía GPU durante la ventana de ejecución.
- Energía incremental respecto a baseline idle.
- Energía por petición.
- Energía por token generado: J/token.
- Eficiencia: tokens/J.
- Energía por token de salida y, cuando el protocolo lo permita, por token total procesado.

Definición inicial: tokens_per_joule = generated_output_tokens / incremental_energy_joules. Publicar además la energía absoluta y el baseline. Si la energía incremental es cero, negativa, desconocida o está contaminada por otras cargas, el ratio debe ser null/invalid, no infinito ni cero.

**Precauciones:** consumo NVML normalmente device-wide; no es consumo exclusivo del proceso. La integración de potencia es una estimación derivada de muestras, no lectura directa del contador de energía. En GPU compartida, marcar atribución como device_shared o unknown.

**Aceptación:** contraste de contador y energía integrada cuando ambos estén disponibles; prueba de unidades, huecos, límites de ventana, baseline, repetición y cálculo tokens/J.

### 1.3 Latencia individual por token

Instrumentar el camino de generación donde el token se produce/entrega realmente:

- timestamp del primer token (TTFT).
- timestamp de cada token emitido.
- inter-token latency (ITL) entre tokens consecutivos.
- latencia de último token y duración de generación.
- pausas, buffering y streaming del servidor.
- separación entre tiempo de decode interno y tiempo de entrega al cliente cuando ambos puedan observarse.

No inferir latencia individual dividiendo el tiempo total por el número de tokens. Conservar la fuente temporal y el punto de observación.

Por defecto exportar histogramas y resumen por request; el detalle token-a-token será opt-in para no inflar archivos ni overhead.

**Aceptación:** secuencia de timestamps monotónicos, conteo igual al número de tokens emitidos, TTFT e ITL reproducibles y contraste con streaming observado por cliente.

### 1.4 Estadística de dispersión

Para latencias, throughput y energía:

- count, min, max, mean, median.
- desviación estándar y varianza.
- MAD (median absolute deviation).
- IQR.
- coeficiente de variación.
- P50, P90, P95, P99.
- outliers con método documentado.
- distribución por posición del token, request y repetición.

No resumir una campaña solo con media. Publicar muestras y protocolo; definir tratamiento de warm-up, fallos, timeouts y ejecuciones descartadas antes de medir.

**Aceptación:** resultados de referencia con dataset sintético y validación numérica independiente.

## Prioridad 2 — OpenTelemetry y OTLP

OpenTelemetry será la capa de interoperabilidad, manteniendo JSONL/SQLite como registro local y evidencia íntegra.

### 2.1 Modelo de trazas

Jerarquía propuesta:

~~~text
nepenthes.run
  +-- engine.startup
  +-- server.request
  |     +-- prompt.prefill
  |     +-- generation
  |     +-- token.first
  |     +-- request.complete
  +-- runtime.graph
  +-- kv_cache.operation
  +-- moe.operation
  +-- backend.operation
~~~

- Propagar trace_id, span_id, parent_span_id, run_id y request_id.
- Mantener IDs del motor y del servidor sin reemplazarlos.
- No unir relojes monotónicos, wall clock y timestamps CUPTI sin calibración explícita.
- Spans para run/request/fases; eventos para operaciones puntuales.
- ITL como histogramas/eventos agregados por defecto; spans por token solo en modo detallado.
- No exportar prompt, completion ni secretos por defecto.

### 2.2 Métricas OTel

Instrumentar histogramas y gauges/counters para:

- TTFT, ITL y latencia total.
- tokens de entrada/salida y throughput.
- energía J, W y tokens/J.
- utilización, memoria y temperatura GPU.
- memoria host/RSS y swap.
- duración de operaciones, transferencias y sincronizaciones.
- eventos perdidos, muestras perdidas y errores del exporter.

Evitar cardinalidad ilimitada: request_id y trace_id van en spans, no como labels de métricas. Etiquetas de métrica solo con dimensiones acotadas (engine, backend, device class, model family cuando proceda).

### 2.3 Exportación OTLP

- Exporter OTLP HTTP/protobuf y/o gRPC, seleccionado por configuración.
- Endpoint, headers, TLS, timeout, batch, retry y shutdown configurables.
- Cola acotada y política de overflow; no bloquear inferencia.
- Exportación local desactivada por defecto o a endpoint explícito.
- Tests con collector OTLP de referencia y validación de payload.
- Compatibilidad de destino con Jaeger, Grafana Tempo/stack y OpenLIT según soporte OTLP de cada despliegue.

**Aceptación:** trace completa run/request, métricas visibles en backend de prueba, shutdown con flush, pérdida contabilizada y ausencia de prompts en exportación.

## Prioridad 3 — AIPerf como runner primario de benchmark

**Decisión:** AIPerf es el runner externo predeterminado para todas las campañas nuevas de NEPENTHES. GenAI-Perf queda relegado a importación y reproducción de campañas históricas; no se desarrollarán nuevas capacidades específicas para él salvo necesidad demostrada. NVIDIA indica que GenAI-Perf está en retirada y recomienda AIPerf para nuevos trabajos.

NEPENTHES no delegará su modelo de datos ni sus criterios de aceptación en AIPerf: AIPerf genera carga y métricas externas; el adaptador NEPENTHES importa y normaliza sus artefactos, conserva los originales y los relaciona con energía/NVML, sondas host, métricas nativas y Nsight cuando exista correlación demostrable. La versión de AIPerf y el esquema de exportación se registran en cada campaña.

### 3.1 AIPerf: ejecución y exportación

- Fijar versión explícita de AIPerf por campaña; registrar versión, Python, plataforma y comando efectivo. Mantenerlo en un entorno aislado del runtime de inferencia.
- Primera vía de compatibilidad: `aiperf profile` contra endpoint OpenAI-compatible de `llama-server`, `--endpoint-type chat` y `--streaming` para TTFT/ITL.
- Configurar endpoint, modelo servido, headers/API key y ruta custom; secretos fuera de manifiestos y logs.
- `--export-level records` como perfil estándar para métricas por request. `raw` solo para diagnóstico autorizado; no exportar texto generado por defecto. `summary` para smoke o informes compactos.
- Preservar artefactos originales AIPerf; ingerir summary JSON/CSV y records JSONL. Importar GPU telemetry y server metrics cuando existan.
- Usar la captura de `/metrics` de AIPerf cuando esté disponible, manteniendo el adaptador nativo NEPENTHES independiente para validar cobertura y semántica.
- Soportar concurrencia fija, request-rate, duración sostenida, replay de trazas y goodput/SLO cuando el escenario esté definido.
- La exportación AIPerf a OTLP/HTTP es opcional; la evidencia primaria seguirá siendo el artefacto local más el expediente NEPENTHES.

### 3.2 Métricas y protocolo normalizado

Normalizar cuando el endpoint lo permita: TTFT, ITL, latencia total, time-to-last-token, throughput, tokens de entrada/salida, request throughput, P50/P90/P95/P99, concurrencia, tasa de llegada, duración, goodput/SLO, warm-up, timeouts, cancelaciones y errores. Registrar dataset, longitudes, tokenizer, sampling, thinking, motor/commit, backend, flags y hardware.

Los nombres y unidades del esquema NEPENTHES no dependerán de los nombres internos de AIPerf. Cada campo importado conserva herramienta/versión, campo original, unidad original y valor normalizado; lo no disponible permanece null/unsupported, nunca cero.

### 3.3 Cargas concurrentes

Diseñar perfiles:
- single-request baseline.
- concurrencia fija (1, 2, 4, ... dentro de capacidad).
- tasa de llegada controlada.
- carga sostenida.
- ráfaga y recuperación.

En el MSI de 14 GiB RAM y RTX 3050 Laptop 4 GiB, dimensionar las pruebas para no confundir presión de memoria, swap u OOM con latencia propia del motor. La matriz de concurrencia será adaptativa al modelo y configuración.

### 3.4 Comparativas reproducibles

- AIPerf (runner primario) frente a protocolo nativo NEPENTHES; GenAI-Perf solo para importar o reproducir campañas históricas.
- llama.cpp frente a TensorFold y futuros motores.
- baseline sin instrumentación frente a BASIC/FULL.
- commit anterior frente a commit candidato.
- exportar manifiesto, resultados por request, resumen y checksums.

**Aceptación:** tres o más repeticiones por configuración aceptada, protocolo idéntico, diferencias de entorno declaradas y resultados raw preservados.

## Prioridad 4 — Adaptadores de métricas nativas

### 4.1 llama.cpp

- Adaptador de /metrics para métricas Prometheus disponibles en la versión del servidor.
- Adaptador de /slots para snapshot de slots, secuencias y estado de requests que exponga la versión.
- Descubrir endpoints y capacidades; manejar 404, cambios de schema, campos opcionales y servidor sin métricas.
- Capturar timestamp de consulta y latencia de scraping.
- Evitar duplicar métricas ya obtenidas por sondas: mantener fuente y política de precedencia.

### 4.2 TensorFold

- Auditar primero qué endpoints, métricas o APIs de diagnóstico expone la versión instalada.
- Crear adaptador solo para capacidades reales documentadas/observadas.
- Si no existe interfaz estable, registrar unsupported/not_exposed y proponer upstream API por separado.
- No inventar /metrics ni /slots para TensorFold.

### 4.3 Otros motores

Contrato de adaptador:
- discover_capabilities()
- collect_snapshot()
- collect_counters()
- normalize()
- health()

Cada adaptador declara versión, fuente, unidad, frecuencia, semántica, limitaciones y tests de contrato. Los campos nativos se preservan junto a los normalizados.

**Aceptación:** adaptadores con fixtures de cada versión soportada, pruebas de errores y comparación con salida original.

## Prioridad 5 — Consolidación de instrumentación llama.cpp/GGML

Continuar el roadmap existente, sin volver a implementar los componentes ya aceptados.

1. Auditar ramas y diferencias Tandem.cpp / llama.cpp / cafe-llama.cpp.
2. Consolidar nepenthes_trace.hpp, contrato y JSONL.
3. Cerrar ciclo de vida, buffer acotado, concurrencia, pérdidas y flush.
4. Integrar request lifecycle, batches y graph.
5. Instrumentar KV cache, memoria, allocator y fallbacks.
6. Instrumentar scheduler y asignación de backend.
7. Instrumentar MoE: selección, carga, residencia, eviction, prefetch, hit/miss y espera.
8. Instrumentar CPU workers y sincronización.
9. Instrumentar CUDA: submission host, kernels observados por Nsight, eventos, streams, memcpy y sincronización.
10. Integrar server: slots, requests concurrentes, cancelaciones y streaming token a token.

No confundir dispatch con ejecución de kernel; solicitud de transferencia con finalización; selección de experto con carga/residencia/uso. Cada evento declara si es nativo, externo o derivado.

## Prioridad 6 — Nsight Systems/CUPTI y semántica de datos

Conservar la importación histórica de LEONES y completar:

- Captura emparejada JSONL + Nsight de una misma ejecución.
- Captura Nsight-only con procedencia separada.
- Decodificación semántica de cudaMemcpyKind y enums de memoria.
- Preservación de uint64 y centinelas unsigned en SQLite, JSON y HTML.
- Detección de tablas CUPTI no soportadas y cobertura parcial explícita.
- Correlación request-kernel solo con IDs compartidos o calibración de reloj demostrada.
- Importación idempotente, checksums y auditoría de integridad.

## Prioridad 7 — Análisis, informes y diagnósticos

- Timeline de request, token, CPU, GPU, KV y MoE.
- Histograma y percentiles de latencia/transferencia/sincronización.
- Energía y tokens/J por ejecución y dispositivo.
- Comparación de dispersión entre runs.
- Correlación de métricas nativas, OTel y Nsight con dominios temporales explícitos.
- Diagnóstico de saturación KV, MoE thrashing, transferencias excesivas, esperas y presión de memoria.
- Informes HTML/Markdown/CSV/SQLite con procedencia y limitaciones.
- Detección determinista de anomalías antes de introducir modelos ML.

## Secuencia de PR sugerida

PRs pequeños y dependencias explícitas; no crear un mega-PR.

| Orden | PR | Contenido |
|---|---|---|
| 0 | Reconciliation & architecture | Auditoría de ramas, contratos, inventario y decisiones |
| 1 | NVML sampler | Muestreo por UUID/dispositivo y fixtures |
| 2 | Energy accounting | Contador/energía integrada, baseline y tokens/J |
| 3 | Token latency | TTFT, timestamp por token, ITL y dispersión |
| 4 | OTel core | Modelo spans/métricas y correlación IDs |
| 5 | OTLP exporter | HTTP/protobuf y/o gRPC, tests con collector |
| 6 | llama.cpp adapters | /metrics, /slots, scraping y fixtures |
| 7 | TensorFold adapter discovery | Auditoría de capacidades y adaptador solo si existe API |
| 8a | AIPerf artifact importer | Importador offline summary/records, hashes, privacidad, eventos normalizados y fixtures (PR #160) |
| 8b | AIPerf runner + llama-server | Entorno aislado, manifiesto, comando reproducible y smoke streaming con concurrencia 1 |
| 8c | AIPerf telemetry adapters | Importación de GPU telemetry, server metrics y phase-aware artifacts |
| 8d | GenAI-Perf legacy import | Compatibilidad de campañas antiguas solo cuando exista evidencia que lo requiera |
| 9 | llama.cpp instrumentation | Lifecycle, graph, KV, scheduler, MoE, CPU/CUDA/server |
| 10 | Nsight semantic correctness | enums, uint64, cobertura y correlación |
| 11 | Reports & release gates | informes, comparación y aceptación integral |

### Estado de la línea AIPerf (2026-11-19)

- PR #159: subproyecto y especificación AIPerf-first, pendiente de revisión/merge.
- PR #160: importador offline de artefactos AIPerf y tests; CI específico con 6 tests offline en success. Depende de PR #159.
- PR #161: wrapper AIPerf-first para llama-server, fijado a AIPerf 0.13.0 y CLI contrastada contra el tag estable; defaults conservadores, manifiesto, protección de secretos y dry-run. CI offline actualizado con 14 tests de runner/importer en success.
- PR #165: parser offline de `/metrics` y `/slots`, pin de llama.cpp master y workflow diario de drift upstream; CI con 23 tests offline en success.
- PR #166: importador de server metrics JSONL y GPU telemetry JSONL de AIPerf; CI con 25 tests offline en success.
- PR #167: importador del agregado `server_metrics_export.json`, incluyendo profiling/warmup, histogram estimates y timeslices; CI con 27 tests offline en success. CSV/Parquet permanecen preservados para otra etapa.
- PR #168: sampler NVML directo, contador energético preferente, integración trapezoidal con control de gaps y normalización de baseline; CI con 36 tests offline en success usando NVML simulado.
- PR #169: generador OTLP/JSON para trazas por request y métricas de run/server/GPU/NVML, con allowlist de atributos y protección de privacidad; CI con 42 tests offline en success.
- PR #170: informe JSON/Markdown de latencias, dispersión, tokens, baseline energética y tokens/J/J-token; CI con 48 tests offline en success.
- PR #171: actualiza el pin llama.cpp al head actual de upstream master `95b09b62beb95c40fc6b317a0c1473c27b5f27fa` (3 commits por delante del pin anterior) y exige coincidencia exacta en CI al revisar el manifiesto.
- PR #172: transporte OTLP/HTTP con HTTPS remoto, auth por entorno, retries/backoff y tests offline; CI con 54 tests en success.
- PR #173: capturador en vivo llama-server `/metrics` + `/slots`, con timestamps wall/monotonic, checksums sin persistir payloads raw y tests HTTP simulados; CI con 59 tests en success.
- PR #162 fue sustituida por PR #164 porque la rama original había quedado divergida tras corregir la base del runner; no integrar ambas.
- No existe todavía fork personal `robertosantosx2/llama.cpp` ni submódulo llama.cpp en LEONES. Incidencia #163 documenta el paso pendiente.
- Todavía no se ha instalado ni ejecutado AIPerf contra llama-server en el MSI; no hay smoke físico y no se declara compatibilidad MEASURED.
- Próximo hito GitHub-only: completar importación CSV/Parquet cuando justifique dependencias, contratos de eventos y OTel mapping; enlazar el sampler NVML con manifests/campañas y contrastar sus lecturas contra AIPerf; validar el transporte OTLP contra un Collector externo con TLS/auth y completar batching/backpressure y ejecutar una campaña de benchmark con repeticiones. Paso externo pendiente: crear fork/submódulo llama.cpp (issue #163). Después, instalar AIPerf 0.13.0 en entorno aislado del MSI, ejecutar dry-run y smoke real con concurrencia 1 y cinco requests.

El orden puede solapar documentación/fixtures, pero no se debe declarar una fase aceptada si depende de otra incompleta.

## Validación en hardware real

Perfil primario disponible: MSI Thin 15 B12UC, Intel Core i7-12650H, NVIDIA RTX 3050 Laptop 4 GiB, 14 GiB RAM, Ubuntu y CUDA toolkit instalado. Es el entorno de validación de baja memoria; no debe suponerse que soporta concurrencia alta ni modelos que excedan sus recursos.

Matriz mínima:
- CPU-only y CUDA.
- GPU presente/ausente, NVML soportado/no soportado.
- contador energético disponible/no disponible.
- ejecución idle y ejecución bajo carga.
- llama.cpp CLI y server.
- /metrics y /slots presentes/ausentes.
- TensorFold con capacidades descubiertas.
- concurrencia 1 y escalado gradual hasta el límite estable.
- OFF/BASIC/FULL y OTLP enabled/disabled.
- Nsight off y captura emparejada.
- fallos de red/exporter, collector saturado y cierre abrupto.

Modelos:
- Qwen3.5-2B para smoke.
- Qwen3.5-4B para CUDA/KV y latencia.
- Qwen3.5-35B-A3B para pruebas MoE híbridas, solo como campaña de estrés cuando la configuración sea viable.

## Gates de aceptación

### Gate A — Integridad
- esquema versionado y payload original conservado.
- IDs y uint64 sin pérdida.
- unidades y timestamps correctos.
- muestras perdidas visibles.

### Gate B — Energía
- fuente y método de energía identificados.
- baseline y ventana definidos.
- tokens/J calculado solo con energía válida.
- atribución device-wide declarada.

### Gate C — Latencia
- TTFT e ITL medidos desde puntos de observación explícitos.
- token count consistente.
- percentiles y dispersión reproducibles.

### Gate D — OpenTelemetry
- trace/run/request correlacionados.
- OTLP exportado a collector de prueba.
- no bloquear inferencia ni exponer prompts.
- backpressure y errores contabilizados.

### Gate E — Benchmark
- manifiesto completo.
- warm-up y repeticiones.
- concurrencia y carga registradas.
- comparaciones equivalentes.

### Gate F — Adaptadores
- endpoints descubiertos, no asumidos.
- fixtures por versión.
- payload original y normalizado.
- fallos/ausencia soportados.

### Gate G — Rendimiento y release
- baseline OFF vs BASIC/FULL.
- overhead medido con repeticiones.
- sin regresiones funcionales.
- paquete reproducible, checksums, documentación y CI.

Los límites de overhead se fijarán después de una línea base. Como objetivos iniciales sujetos a medición: BASIC <2% y FULL <5%; no son resultados ya demostrados ni criterios para ocultar una desviación.

## Registro de riesgos

| Riesgo | Mitigación |
|---|---|
| NVML no expone energía acumulada en la GPU | Integrar potencia y etiquetar método derivado |
| GPU compartida | Declarar medición device-wide y no atribuir al proceso |
| Muestreo lento frente a picos | Intervalo configurable, registrar frecuencia efectiva y límites |
| Spans por token generan overhead | Histograma por defecto; detalle opt-in |
| Cardinalidad OTel excesiva | IDs en trazas, no labels métricos |
| Cambios de /metrics y /slots | Discovery, fixtures versionados y parser tolerante |
| TensorFold no ofrece métricas públicas | No inventar endpoints; documentar brecha y proponer API |
| AIPerf y protocolo propio difieren | Manifiesto común, importador versionado y comparación controlada |
| Relojes incompatibles | Dominios separados y calibración demostrada |
| Exporter ralentiza inferencia | Buffer acotado, envío asíncrono y drop counters |

## Referencias externas verificadas

- [Inferscope](https://github.com/MicheleCampi/inferscope): profiler de inferencia con ITL por token, muestreo NVML por GPU, contador de energía NVML con fallback de integración trapezoidal, tokens/J y exportación OTLP opcional. Revisar versión, licencia y validación real antes de adoptar detalles.
- [AIPerf — opciones de CLI y artefactos](https://docs.nvidia.com/aiperf/reference/command-line-options): runner primario; perfiles streaming, concurrencia/tasa de llegada, exportación summary/records/raw, GPU telemetry, server metrics y OTLP/HTTP.
- [AIPerf — profiling](https://docs.nvidia.com/aiperf/getting-started/profiling-with-ai-perf): ejecución contra endpoints OpenAI-compatible.
- [AIPerf — métricas](https://docs.nvidia.com/aiperf/reference/ai-perf-metrics-reference): semántica y unidades.
- [GenAI-Perf](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/perf_analyzer/genai-perf/README.html): compatibilidad heredada; NVIDIA señala que está en retirada.
- [llama.cpp server metrics](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md): documentación del endpoint /metrics, habilitado mediante la opción --metrics.

## Entregables documentales

- README.md: misión, arquitectura y contratos.
- ROADMAP.md: este plan maestro.
- Contrato de eventos y métricas.
- Especificación NVML/energía.
- Esquema de spans/atributos OpenTelemetry.
- Contrato de adaptadores.
- Especificación de integración AIPerf y protocolo NEPENTHES.
- Importador de artefactos AIPerf con fixtures por versión.
- Importador legacy GenAI-Perf, solo si existen campañas históricas que lo requieran.
- Matriz de cobertura y gates.
- Manifiestos y evidencias por campaña.

## Regla final

Una cifra solo es MEASURED si procede de una ejecución identificada, con fuente, unidad, método, configuración, timestamp, hardware y artefactos verificables. Una energía integrada es una estimación derivada de muestras; una métrica NVML device-wide no es consumo por proceso; una latencia inferida del promedio no es ITL individual. NEPENTHES debe hacer visibles estas diferencias en cada informe.


## Estado de integración del fork llama.cpp (2026-11-19)

- Fork personal creado y accesible: robertosantosx2/llama.cpp.
- Upstream `ggml-org/llama.cpp:master`: `4db8b7638f2fa2e5c092ee05d49999b56e8167c3`.
- Fork `robertosantosx2/llama.cpp:master`: `5812201a81008977ea079eaf86a3f9166eef9f10`, tres commits por detrás. Rebase pendiente: upstream tocó `src/llama-context.cpp` y los parámetros/contexto de grafo, por lo que no se debe avanzar el fork sin integrar esas modificaciones y repetir CI.
- El gitlink `subprojects/llama.cpp` permanece fijado en `76f186df71a41abb3ee20fffedee31ca5dbc7d9f`; no se avanza hasta revisar la pila y repetir CI.
- Comparación respecto al pin anterior 95b09b62beb95c40fc6b317a0c1473c27b5f27fa: 1 commit ahead, 0 behind.
- LEONES incorpora el gitlink subprojects/llama.cpp con modo Git 160000, fijado al mismo SHA.
- La política es revisión explícita de cada actualización del submódulo; el monitor upstream no modifica automáticamente el gitlink.
- CI comprueba URL, modo gitlink, SHA resuelto y manifiesto.
- Esta integración es GitHub-only: no implica compilación, ejecución de llama.cpp ni validación en la RTX 3050. Esas pruebas quedan para la fase MSI.


### llama.cpp runtime instrumentation — active

- PR de fork abierto: [robertosantosx2/llama.cpp#1](https://github.com/robertosantosx2/llama.cpp/pull/1).
- Primera capa en revisión: sink JSONL acotado, eventos de petición, graph compute/sync, MoE cache y KV cache.
- Siguiente capa: allocator/OOM/fallback, transferencias y dispatch CUDA, con límites de semántica documentados.
- No se declara validado hasta que CI compile el server CPU y después se realice build CUDA y captura reproducible en MSI.

- Segunda PR de llama.cpp abierta: [#2 ggml backend y CUDA](https://github.com/robertosantosx2/llama.cpp/pull/2), apilada sobre la primera; CI CPU/CUDA pendiente.

- PR #1: CI propia completa con éxito (tests C++ y build CPU llama-server); estilo, EditorConfig, WASM y WASI upstream también verdes. Otros checks upstream aún en curso.
- PR #2: instrumentación ggml/CUDA apilada sobre PR #1; CI de CPU/CUDA en cola.


## Integración runtime nativa llama.cpp (2026-11-19)

- [PR #1](https://github.com/robertosantosx2/llama.cpp/pull/1): sink JSONL y sondas core, en borrador.
- [PR #2](https://github.com/robertosantosx2/llama.cpp/pull/2): backend ggml y CUDA, en borrador; la compilación CUDA sm_86 de GitHub Actions pasó en su head verificado.
- [PR #3](https://github.com/robertosantosx2/llama.cpp/pull/3): workers CPU y esperas, en borrador; CI en ejecución tras corregir un error de declaración C linkage detectado por CI.
- Orden de integración: #1 → #2 → #3. No fusionar ni mover el pin del submódulo automáticamente.
- Pendiente tras revisión CI: comprobar build CPU/CUDA en GitHub, inspeccionar diffs y actualizar el gitlink en una PR separada.
- Pendiente MSI: captura real de JSONL + NVML + Nsight Systems, overhead de instrumentación, integridad de contadores y comportamiento de la RTX 3050 de 4 GiB.


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
5. Revisar e integrar ordenadamente PR #1 → #2 → #3 → #4 en `nepenthes/rc1`; resolver drift upstream antes de mover gitlink.
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
