# NEPENTHES — especificación de integración AIPerf

**Estado:** diseño aprobado para implementación; no implica que el adaptador esté implementado ni que existan medidas nuevas.
**Rol:** AIPerf es el runner externo primario de benchmarking para campañas nuevas.
**Primera integración:** llama.cpp llama-server con API OpenAI-compatible.

## 1. Objetivos y límites

1. Lanzar AIPerf de forma reproducible contra un endpoint de inferencia local.
2. Preservar íntegramente los artefactos originales de AIPerf.
3. Importar y normalizar métricas por request y agregadas al esquema NEPENTHES.
4. Relacionar resultados con manifiesto, NVML/energía, sondas host y métricas nativas solo cuando exista correlación temporal demostrable.
5. Mantener AIPerf opcional y aislado del runtime del motor.
6. Mantener GenAI-Perf solo como formato/runner heredado para campañas antiguas.

No se reimplementará el generador de carga de AIPerf. Tampoco se asumirá que todos los motores soportan los mismos endpoints, métricas, streaming o semántica de tokens.

## 2. Flujo de ejecución

```text
NEPENTHES campaign manifest
        |
        v
AIPerf runner (pinned version)
        |
        +----> OpenAI-compatible endpoint (llama-server first)
        |
        +----> AIPerf artifacts (summary / records / raw)
        |         +-- metrics JSON/CSV
        |         +-- per-request JSONL
        |         +-- raw JSONL (opt-in)
        |         +-- GPU telemetry (if available)
        |         +-- server metrics (if available)
        |
        v
Read-only AIPerf importer
        |
        +----> original artifacts + checksums (immutable)
        +----> normalized NEPENTHES events/metrics
        +----> import report + coverage + warnings
        |
        +----> NVML / energy / host probes / engine adapter
        |
        v
NEPENTHES analysis, OTel and reports
```

## 3. Versionado y entorno

- Fijar una versión exacta de AIPerf por campaña; no usar latest implícito en campañas aceptadas.
- Registrar versión AIPerf, Python, sistema operativo, arquitectura, versión/commit de llama.cpp, backend y configuración.
- Preferir entorno virtual aislado para AIPerf; no modificar Python del sistema ni instalar paquetes en el entorno de inferencia.
- Comprobar disponibilidad con aiperf --version y registrar las opciones relevantes de aiperf profile --help.
- Validar instalación, versión y compatibilidad en CI/entorno de pruebas antes de campaña física. No instalar ni ejecutar automáticamente sobre el MSI sin fase de preflight.

## 4. Perfil base NEPENTHES

Perfil inicial conservador para el MSI (RTX 3050 Laptop 4 GiB, 14 GiB RAM):

- Endpoint local loopback y nombre exacto anunciado por el servidor.
- Endpoint type chat; ruta OpenAI-compatible descubierta y probada.
- Streaming activado para TTFT/ITL.
- Concurrencia inicial 1; aumentar solo tras observar estabilidad de RAM, swap, VRAM y errores.
- Dataset sintético determinista o dataset versionado con checksum; registrar longitudes de entrada/salida.
- Número de requests, warm-up, grace period, duración y timeout explícitos.
- Export level records como perfil normal: resumen y registros por petición.
- Export level raw solo en modo diagnóstico autorizado. Evitar exportar texto de respuestas por defecto.
- Guardar artefactos dentro del expediente de campaña.
- No activar request-rate, replay de trazas, concurrencia alta o carga sostenida larga sin dimensionamiento previo.

Los valores concretos del comando deben provenir de configuración/manifiesto versionado y capacidad del servidor; no se codifican como defaults universales.

## 5. Contrato de artefactos

El importador debe reconocer por versión, sin asumir nombres de archivos inmutables:

- Resumen agregado JSON/CSV.
- Registros JSONL por request.
- Datos raw JSONL opcionales y potencialmente sensibles.
- GPU telemetry JSONL cuando AIPerf la genere.
- Server metrics JSON/JSONL/CSV/Parquet cuando estén disponibles.
- Configuración y metadatos de ejecución AIPerf.

Reglas:
1. Preservar originales sin editarlos; generar SHA-256 por archivo.
2. Registrar inventario de artefactos, tamaño, checksum y versión del productor.
3. Parser read-only y fallo explícito ante schema desconocido.
4. Campos desconocidos preservados en source_fields; nunca descartados silenciosamente.
5. Artefacto ausente produce missing/unsupported, no métrica cero.
6. Importación idempotente: repetirla no duplica eventos ni campañas.
7. Registrar cobertura por campo: imported, missing, unsupported, malformed o derived.

## 6. Normalización de métricas

| Dominio | Métrica canónica | Reglas |
|---|---|---|
| Latencia | TTFT | Conservar unidad original y normalizar a ns/us/ms |
| Latencia | ITL | No confundir media de ITL con muestras individuales |
| Latencia | request latency | Definir punto final medido por AIPerf |
| Throughput | output tokens/s | Preservar denominador y ventana |
| Throughput | requests/s | Diferenciar tasa ofrecida y completada |
| Tokens | input/output token count | Registrar fuente/tokenizer y posibles diferencias |
| Distribución | P50/P90/P95/P99 | Conservar estadístico fuente; no recalcular sin muestras |
| Carga | concurrency/request rate | Registrar modalidad y configuración real |
| Calidad | goodput/SLO | Guardar umbral y criterio exactos |
| Recursos | GPU/server metrics | Conservar fuente, unidad, frecuencia y scope |

Cada punto normalizado incluye como mínimo: schema_version, run_id, request_id si existe, timestamp y dominio temporal, metric_name, value, unit, source_tool=aiperf, source_version, source_field, normalization_version y quality/status.

No reconstruir ITL token-a-token desde una media agregada. No atribuir GPU telemetry device-wide a un proceso. No unir timestamps de AIPerf, NVML, monotonic clock y Nsight sin calibración o marcador compartido.

## 7. Métricas de servidor y OpenTelemetry

- AIPerf puede recoger automáticamente el endpoint Prometheus /metrics derivado del endpoint base. Documentar si el servidor lo expone y si requiere --metrics.
- El adaptador llama.cpp NEPENTHES seguirá siendo independiente para validar versión, cobertura y semántica de /metrics y /slots.
- La exportación AIPerf a OTLP/HTTP es opcional; no sustituye la persistencia local de artefactos.
- Evitar doble conteo cuando una misma métrica aparezca en AIPerf, Prometheus y el sampler NEPENTHES. Mantener todas las fuentes y aplicar precedencia solo en vistas derivadas.
- No exportar prompts, respuestas, API keys ni headers sensibles por defecto.

## 8. Compatibilidad por etapas

### Etapa A — fixture e importador offline
- Fixtures pequeños anonimizados de summary JSON/CSV y records JSONL.
- Parser version-aware, normalización, cobertura, checksum e idempotencia.
- Tests de campos ausentes, unidades, null/zero, datos corruptos y schema desconocido.

### Etapa B — smoke de endpoint
- Endpoint local compatible con OpenAI.
- Una petición, streaming, concurrencia 1.
- Verificar que AIPerf detecta TTFT/ITL y genera artefactos.
- No declarar benchmark aceptado a partir de un smoke.

### Etapa C — llama.cpp server
- Probar /v1/chat/completions, streaming y /metrics cuando estén habilitados.
- Comparar conteo de tokens, requests y latencia con logs/telemetría independiente.
- Registrar diferencias de tokenizer y semántica.

### Etapa D — carga y repetibilidad
- Concurrencia 1 y escalado gradual.
- Request-rate y duración sostenida solo después del baseline.
- Tres o más repeticiones por configuración aceptada.
- Integrar NVML/energía y sondas host con ventanas y limitaciones explícitas.

### Etapa E — otros motores
- Descubrir endpoint, streaming, auth y métricas por motor.
- TensorFold solo cuando la API real de su versión esté documentada/observada.
- Fixtures de contrato por motor y versión.

## 9. Criterios de aceptación

- [ ] Versión AIPerf fijada y registrada.
- [ ] Manifiesto NEPENTHES completo y reproducible.
- [ ] Artefactos originales preservados y con SHA-256.
- [ ] Importación idempotente y parser version-aware.
- [ ] Métricas por request normalizadas sin pérdida de unidad/fuente.
- [ ] Campos ausentes y no soportados diferenciados de cero.
- [ ] TTFT/ITL contrastados con streaming real; sin inventar ITL individual.
- [ ] Métricas de servidor con endpoint/capacidades documentados.
- [ ] No hay prompts, respuestas ni secretos exportados por defecto.
- [ ] Overhead y presión de recursos medidos en hardware objetivo.
- [ ] CI con fixtures offline; smoke real registrado aparte.
- [ ] No se declara MEASURED/ACCEPTED sin expediente y evidencia.

## 10. Referencias

- [AIPerf command line options](https://docs.nvidia.com/aiperf/reference/command-line-options)
- [AIPerf profiling guide](https://docs.nvidia.com/aiperf/getting-started/profiling-with-ai-perf)
- [AIPerf metrics reference](https://docs.nvidia.com/aiperf/reference/ai-perf-metrics-reference)
- [AIPerf profile export files](https://docs.nvidia.com/aiperf/tutorials/metrics-analysis/working-with-profile-export-files)
- [GenAI-Perf legacy documentation](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/perf_analyzer/genai-perf/README.html)