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
- Todavía no se ha instalado ni ejecutado AIPerf contra llama-server, no hay smoke físico y no se declara compatibilidad MEASURED.
- Próximo hito: runner aislado y smoke con concurrencia 1 en llama-server; después ampliar telemetría y soporte phase-aware.

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
