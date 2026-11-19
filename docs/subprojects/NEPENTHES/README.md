# NEPENTHES — observabilidad de motores de inferencia

**Subproyecto de LEONES · Estado: en desarrollo · Prioridad inmediata: energía, latencia por token e interoperabilidad**

NEPENTHES es la infraestructura de observabilidad y benchmarking reproducible para motores de inferencia local. Su misión es capturar, preservar, correlacionar y analizar el comportamiento real del runtime, CPU, GPU, memoria, KV cache, MoE y servidor, sin confundir observaciones, estimaciones y mediciones.

Este directorio establece la arquitectura y el plan canónico del subproyecto. Conserva la implementación y las evidencias históricas en research/moe/tandem.cpp/; no duplica código ni sustituye esos registros.

## Objetivos

1. Instrumentación nativa y de bajo impacto en llama.cpp/GGML.
2. Captura host/GPU con procedencia, timestamps y pérdida de eventos explícita.
3. Medición energética y eficiencia tokens/julio.
4. Latencia individual e inter-token de generación, además de percentiles y dispersión.
5. Interoperabilidad mediante OpenTelemetry y OTLP.
6. Benchmark reproducible con AIPerf como runner primario y protocolo NEPENTHES versionado.
7. Adaptadores de métricas para llama.cpp, TensorFold y otros motores.
8. Importación y análisis reproducible en LEONES, con Nsight Systems/CUPTI como evidencia externa.

## Prioridades de producto

### P1 — Estudiar e integrar ideas de Inferscope (máximo interés inmediato)

Referencia principal: [MicheleCampi/inferscope](https://github.com/MicheleCampi/inferscope) (Apache-2.0). Estudiar arquitectura, decisiones de diseño, límites de atribución, captura token-stream, NVML, contador de energía y exportación OTLP. Adoptar ideas mediante una implementación NEPENTHES compatible con sus propios contratos; no copiar código sin revisión de licencia y dependencias.

- Muestreo NVML por dispositivo, con frecuencia configurable, timestamps monotónicos y detección de muestras perdidas.
- Potencia instantánea y energía acumulada real cuando el dispositivo/driver exponga un contador compatible.
- Cuando no exista contador de energía, integración numérica de muestras de potencia; etiquetar el resultado como energía derivada, nunca como contador físico directo.
- Energía incremental atribuible a la ventana de benchmark, baseline idle y, cuando sea viable, separación de GPU/CPU/sistema.
- Tokens/julio para tokens generados y, por separado, throughput energético de peticiones.
- Latencia por token: primer token, inter-token latency (ITL), distribución por posición y pausas.
- Estadísticas de dispersión: mediana, desviación estándar, MAD, coeficiente de variación, IQR y percentiles.
- Exportación OpenTelemetry sin hacer obligatoria esta dependencia para capturar.

La telemetría NVML es normalmente de dispositivo completo. No atribuir consumo a un proceso concreto si la fuente no ofrece esa atribución. Para energía derivada, conservar muestras, intervalo, método de integración y error/limitaciones.

### P2 — OpenTelemetry como formato de interoperabilidad

OpenTelemetry será la interfaz estándar de exportación e integración, no el formato único de almacenamiento ni un reemplazo de JSONL/SQLite.

- Exportación OTLP por HTTP/protobuf o gRPC, configurable.
- Trazas y spans para ejecución, petición, generación y operaciones relevantes.
- Identificadores de trace/span y correlación con run_id, request_id y motor.
- Métricas con histogramas para TTFT, ITL, duración, throughput, energía y memoria.
- Eventos/logs para transiciones de KV cache, MoE, transferencias, errores y anomalías.
- Compatibilidad de destino mediante OTLP con Jaeger, Grafana Tempo/stack y OpenLIT, según sus receptores y configuración.
- Exportación opcional, buffer acotado, backpressure y contadores de pérdida.

No crear un span por cada token por defecto: puede generar volumen y overhead excesivos. Registrar ITL como histograma/evento agregado y habilitar detalle token-a-token solo en perfiles de diagnóstico. No incluir prompts, respuestas ni datos sensibles en atributos por defecto. Evitar IDs de petición como etiquetas de métricas de alta cardinalidad; mantenerlos en trazas.

### P3 — AIPerf como runner primario

AIPerf es el runner externo predeterminado para nuevas campañas NEPENTHES. Se usa contra endpoints OpenAI-compatible, con streaming cuando se midan TTFT/ITL, perfiles de concurrencia o tasa de llegada y exportación por request. GenAI-Perf queda limitado a compatibilidad/importación de campañas históricas por estar en retirada según NVIDIA.

NEPENTHES conserva el protocolo y esquema canónicos: importa artefactos AIPerf, normaliza métricas, mantiene originales y correlaciona con NVML, energía, sondas host y métricas nativas solo cuando la evidencia lo permite. Primera integración: `llama-server`; TensorFold y otros motores tras descubrir y probar sus endpoints.

- Protocolo normalizado de benchmark y manifiesto completo.
- TTFT, ITL, latencia total, throughput de entrada/salida y percentiles.
- Concurrencia, tasa de llegada y duración/cantidad de solicitudes.
- Warm-up separado de las mediciones.
- Repeticiones y dispersión; resultados por petición además de agregados.
- Comparativas reproducibles entre commits, motores, modelos, cuantizaciones y configuraciones.
- Exportación de resultados a los contratos NEPENTHES y LEONES sin perder unidades ni procedencia.

No comparar campañas si difieren dataset/prompt, longitudes de entrada/salida, concurrencia/tasa de llegada, streaming, warm-up, hardware, motor o versión de AIPerf. Registrar comando, configuración, versión y artefactos originales.

### P4 — Adaptadores de métricas nativas

- llama.cpp: lector de /metrics (Prometheus) y /slots (estado por slot), además de eventos instrumentados.
- TensorFold: adaptador cuando exista una interfaz estable de métricas/estado; descubrir capacidades y no asumir endpoints que no estén documentados o disponibles.
- Otros motores: interfaz de adaptador versionada y basada en capacidades.
- Normalizar nombres, unidades, etiquetas, timestamps y semántica, conservando siempre el payload original.
- Diferenciar métricas nativas del motor, métricas del host/dispositivo y métricas calculadas por NEPENTHES.

/slots es una API de estado, no una fuente Prometheus: su adaptador debe tratarla como snapshot/evento y preservar el esquema de la versión del servidor.

## Arquitectura

~~~text
llama.cpp / GGML / TensorFold / otros motores
        |
        +-- sondas nativas (request, graph, KV, MoE, scheduler, CUDA)
        +-- adaptadores de métricas (/metrics, /slots, APIs futuras)
        +-- benchmark driver (AIPerf / protocolo NEPENTHES)
        |
        v
NEPENTHES Collector
  +-- eventos JSONL versionados
  +-- muestras host / NVML por dispositivo
  +-- latencia por token y estadísticas
  +-- correlación run_id / request_id / trace_id
  +-- buffer acotado + contadores de pérdida
        |
        +------------> OpenTelemetry SDK / OTLP
        |                +-- Jaeger
        |                +-- Grafana / Tempo
        |                +-- OpenLIT
        |
        v
LEONES
  +-- SQLite e importadores
  +-- Nsight Systems / CUPTI (fuente externa)
  +-- análisis y comparativas
  +-- informes HTML / Markdown / CSV / gráficos
~~~

### Separación de responsabilidades

| Componente | Responsabilidad |
|---|---|
| llama.cpp/GGML | Eventos de ejecución observados en el punto real |
| Adaptadores | Lectura de métricas expuestas por cada motor |
| Collector | Normalización, timestamps, IDs, buffers y procedencia |
| NVML sampler | Potencia/energía/telemetría por dispositivo |
| OpenTelemetry exporter | Traducción a spans, métricas, logs y OTLP |
| AIPerf | Runner primario de carga y métricas externas |
| GenAI-Perf | Importación de campañas históricas únicamente |
| LEONES | Persistencia, análisis, evidencia, comparativas e informes |
| Nsight Systems | Evidencia externa de actividad CUDA/CUPTI |

## Contratos de datos e invariantes

Todo registro debe conservar, cuando aplique:

- schema_version, event_id, run_id, request_id.
- trace_id, span_id y parent_span_id para exportación OTel.
- Timestamp monotónico y dominio de reloj; timestamp de pared solo como metadato adicional.
- Fuente: native, nvml, prometheus, slots_api, genai_perf, nsys o derived.
- Unidad, dispositivo, backend, modelo, motor y versión.
- Valor original y valor normalizado.
- Método de cálculo y estado de calidad para métricas derivadas.
- Pérdidas, huecos de muestreo, errores y cobertura.

Reglas obligatorias:

1. No inventar duración ni correlación entre relojes.
2. No presentar energía integrada como contador físico de energía.
3. No atribuir telemetría device-wide a un proceso sin soporte explícito.
4. No sumar muestras de energía solapadas ni contar dos veces el consumo.
5. No convertir timestamps o identificadores unsigned en valores con signo.
6. No tratar null, cero y centinelas como equivalentes.
7. No descartar silenciosamente eventos, muestras o tablas desconocidas.
8. No permitir que la exportación OTLP bloquee la inferencia.
9. Mantener JSONL/SQLite como evidencia local aun cuando OTLP esté desactivado.
10. Mantener prompts y respuestas fuera de la telemetría por defecto.

## Referencias externas

- [Inferscope — profiler OpenAI-compatible con NVML, energía, ITL y OTLP](https://github.com/MicheleCampi/inferscope).
- [NVIDIA AIPerf — CLI, perfiles y exportaciones](https://docs.nvidia.com/aiperf/reference/command-line-options).
- [NVIDIA AIPerf — guía de profiling](https://docs.nvidia.com/aiperf/getting-started/profiling-with-ai-perf).
- [NVIDIA AIPerf — referencia de métricas](https://docs.nvidia.com/aiperf/reference/ai-perf-metrics-reference).
- [NVIDIA GenAI-Perf — documentación y ciclo de vida](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/perf_analyzer/genai-perf/README.html) (legacy).
- [llama.cpp server — endpoint /metrics](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

## Enlaces canónicos

- [Roadmap detallado](ROADMAP.md)
- [Especificación de integración AIPerf](AIPERF-INTEGRATION.md)
- [Versión estable de AIPerf](AIPERF-UPSTREAM.json)
- [Pin y seguimiento del upstream llama.cpp](LLAMA-CPP-UPSTREAM.json)
- [Captura en vivo de llama-server](LLAMA-SERVER-CAPTURE.md)
- [Muestreador NVML y contabilidad energética](NVML-ENERGY.md)
- [Exportación OpenTelemetry / OTLP](OTEL-EXPORT.md)
- [Informe de benchmark y eficiencia](BENCHMARK-REPORT.md)
- [Índice histórico y estado de validación](../../research/moe/tandem.cpp/NEPENTHES-INDEX.md)
- [Roadmap histórico de implementación y gates](../../research/moe/tandem.cpp/NEPENTHES-ROADMAP.md)
- [Campañas y resultados](../../research/moe/tandem.cpp/NEPENTHES-CAMPAIGNS.md)
- [CLI e instalador](../../research/moe/tandem.cpp/NEPENTHES-CLI.md)
- [Importador Nsight/CUPTI](../../research/moe/tandem.cpp/NEPENTHES-IMPORTER.md)
- [Tandem.cpp PR #1](https://github.com/robertosantosx2/tandem.cpp/pull/1)
- [LEONES PR #153 — importación Nsight-only](https://github.com/robertosantosx2/LEONES/pull/153)

## Estado y criterio de aceptación

Este documento es un plan, no una declaración de que las nuevas capacidades estén implementadas. La situación de cada función debe etiquetarse como PLANNED, IMPLEMENTED, CAPTURED, MEASURED o ACCEPTED, con evidencia asociada.

NEPENTHES V1 no se considerará completo hasta que una ejecución real pueda producir una captura verificable, medir latencia y energía con semántica explícita, importar datos sin pérdida y comparar repeticiones con overhead conocido. La interoperabilidad OTLP y los adaptadores se aceptarán mediante pruebas de contrato y destinos reales.


## Repositorios y pin de llama.cpp

- **Fork de trabajo:** [robertosantosx2/llama.cpp](https://github.com/robertosantosx2/llama.cpp) (origin).
- **Upstream:** [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) (upstream).
- **Upstream actual:** `ggml-org/llama.cpp:master` en `4db8b7638f2fa2e5c092ee05d49999b56e8167c3`.
- **Fork personal:** `robertosantosx2/llama.cpp:master` en `5812201a81008977ea079eaf86a3f9166eef9f10`, tres commits por detrás. La actualización queda pendiente de rebase porque upstream modificó `src/llama-context.cpp` y estructuras de grafo usadas por la instrumentación.
- **Submódulo LEONES:** `subprojects/llama.cpp`, todavía fijado a `76f186df71a41abb3ee20fffedee31ca5dbc7d9f` hasta revisar y aceptar la pila.
- En la verificación del 2026-11-19, origin/master y upstream/master coincidían exactamente.
- El gitlink se actualiza mediante PR revisada; el seguimiento diario detecta drift, pero no mueve el pin automáticamente.

El manifiesto LLAMA-CPP-UPSTREAM.json conserva el SHA, estado del fork, commit del submódulo y política de sincronización. La CI valida que el gitlink, .gitmodules, el checkout del submódulo y el manifiesto sean coherentes.


## Instrumentación nativa de llama.cpp

El desarrollo del runtime se realiza directamente en el fork, no mediante parches aplicados en un checkout local:

- [PR #1 — NEPENTHES: opt-in runtime trace sink and core probes](https://github.com/robertosantosx2/llama.cpp/pull/1)
- Rama: feat/nepenthes-runtime-probes-20261119
- Cobertura inicial: ciclo de petición del servidor, graph compute, sincronización, MoE cache y operaciones principales de KV cache.
- CI propia: tests C++ del contrato/sink y build CPU de llama-server; las comprobaciones generales de upstream también se ejecutan.
- El submódulo de este PR permanece fijado al commit upstream limpio. No se moverá al branch de instrumentación hasta que los cambios estén revisados y exista una decisión de integración.

La instrumentación CUDA/backend adicional, los probes generales de memoria/transferencia y la captura real en GPU quedan en fases posteriores.

- [PR #2 — ggml backend and CUDA runtime probes](https://github.com/robertosantosx2/llama.cpp/pull/2), apilada sobre PR #1: ABI compartida en ggml-base, ciclo de buffers, CUDA alloc/OOM/pools/VMM/pinned-host, transferencias y dispatch.

**Validación PR #1:** los tests C++ del contrato/sink y el build CPU de llama-server han pasado en GitHub Actions. Los checks upstream de estilo, EditorConfig, WASM y WASI también han pasado; el resto de checks upstream continúa ejecutándose.


## Instrumentación nativa en llama.cpp

La instrumentación del motor se desarrolla en el fork [robertosantosx2/llama.cpp](https://github.com/robertosantosx2/llama.cpp), mediante una pila de PRs revisables:

1. [PR #1](https://github.com/robertosantosx2/llama.cpp/pull/1): contrato de eventos, sink JSONL acotado, ciclo de petición, graph compute, sincronización, MoE y KV.
2. [PR #2](https://github.com/robertosantosx2/llama.cpp/pull/2): ciclo de vida del modelo, buffers ggml, asignación y pools CUDA, OOM/fallback, transferencias, despacho de operaciones y sincronización de streams.
3. [PR #3](https://github.com/robertosantosx2/llama.cpp/pull/3): duración de trabajo por worker CPU y esperas dormidas por condición.

Las PRs están apiladas y en borrador; deben revisarse en orden y no se han fusionado. El manifiesto [LLAMA-CPP-UPSTREAM.json](LLAMA-CPP-UPSTREAM.json) conserva sus ramas, dependencias y alcances.

La captura nativa no reemplaza Nsight Systems/CUPTI: los tiempos de kernels reales y las transferencias completadas en dispositivo se obtienen de las actividades de Nsight y se correlacionan en LEONES. No se generan eventos de prefetch genéricos donde el camino upstream auditado no contiene ese trabajador. La correlación request_id se limita a los puntos donde el identificador real puede propagarse con seguridad.
