# NEPENTHES — Exportación OpenTelemetry / OTLP

## Objetivo

Convertir los eventos normalizados de NEPENTHES a cuerpos JSON compatibles con OTLP/HTTP, sin exportar prompts, texto generado, credenciales ni payloads raw. La generación de ficheros es offline; no abre conexiones de red.

## Uso

```bash
python3 scripts/nepenthes_otel_export.py \
  --events artifacts/nepenthes/aiperf-smoke-001-import/aiperf_events.jsonl \
  --output-dir artifacts/nepenthes/aiperf-smoke-001-otel
```

Genera:
- `otlp-traces.json`: benchmark span padre y spans cliente por petición.
- `otlp-metrics.json`: métricas OTLP con atributos de cardinalidad acotada.
- `otlp-export-report.json`: cobertura, omisiones y política de privacidad/temporality.

Para enviarlos con el transporte integrado (HTTPS obligatorio para collectors remotos; HTTP solo loopback):

```bash
python3 scripts/nepenthes_otel_transport.py \\
  --input-dir artifacts/nepenthes/aiperf-smoke-001-otel \\
  --endpoint http://127.0.0.1:4318
```

El transporte envía `/v1/traces` y `/v1/metrics` en secuencia, reintenta fallos transitorios (429/5xx y errores de red) con backoff exponencial y registra un informe sin secretos. Para autenticación, exporta el valor completo del header Authorization desde una variable de entorno, por ejemplo `NEPENTHES_OTLP_AUTH_HEADER='Bearer …'`; no lo pases por argumentos ni lo guardes en manifiestos.

Para envío manual con curl, después de revisar los payloads:

```bash
curl -X POST -H 'Content-Type: application/json' \
  --data-binary @artifacts/nepenthes/aiperf-smoke-001-otel/otlp-traces.json \
  http://127.0.0.1:4318/v1/traces

curl -X POST -H 'Content-Type: application/json' \
  --data-binary @artifacts/nepenthes/aiperf-smoke-001-otel/otlp-metrics.json \
  http://127.0.0.1:4318/v1/metrics
```

## Trazas

- Trace ID determinista por `run_id`; span padre `aiperf.benchmark`.
- Span cliente `llm.request` por request cuando existen timestamps de inicio y fin válidos.
- TTFT, ITL y otras métricas escalares se adjuntan como span events.
- Vectores ITL se resumen en count/mean/min/max/P50/P95/P99; no se crea un span por token.
- Los errores marcan el span como ERROR y exportan solo código/tipo, nunca el mensaje raw.

Los spans sin timestamps completos se omiten y cuentan en el informe. No se sintetizan duraciones.

## Métricas

- Métricas de run, request, server y GPU se convierten a OTLP Gauge.
- Los identificadores de petición no se usan como atributos de métricas.
- Se permiten labels acotadas como model/status/backend y la identidad de GPU.
- Los histogramas Prometheus de `/metrics` se representan como snapshots gauge por bucket/sum/count; no se convierten en histogramas OTLP porque no se ha demostrado la temporality/delta necesaria.
- Los percentiles de agregados conservan sufijos `*_estimate`.
- Energía acumulada AIPerf/NVML se exporta como Gauge con su semántica de contador acumulado; el exportador no inventa deltas.
- No se mezclan relojes monotónicos con epoch timestamps.

## Destinos

Los payloads pueden enviarse a cualquier collector que acepte OTLP/HTTP JSON, por ejemplo OpenTelemetry Collector, Grafana Tempo/Prometheus vía Collector, Jaeger con soporte OTLP u OpenLIT. La configuración TLS y autenticación se aplica en el transporte HTTP integrado. Batching y backpressure adaptativo siguen pendientes; el transporte actual envía un payload por señal.

## Privacidad y límites

- No exporta prompts, respuestas, secretos, URLs completas ni request IDs como labels métricas.
- Request IDs aparecen solo en spans para correlación de trazas.
- No se añaden atributos de alta cardinalidad a las métricas.
- La exportación es una representación interoperable, no evidencia de que un Collector externo haya recibido los datos.
- Tests offline validan la estructura OTLP/JSON y las políticas sin necesitar Jaeger, Grafana ni un collector activo.
