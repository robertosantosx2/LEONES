# NEPENTHES — Captura en vivo de llama-server

## Uso

Con llama-server ya iniciado, capturar `/metrics` y `/slots`:

```bash
python3 scripts/nepenthes_llama_server_capture.py \
  --url http://127.0.0.1:8080 \
  --duration-seconds 30 \
  --interval-ms 500 \
  --output-dir artifacts/nepenthes/llama-server-smoke-001
```

El capturador consulta GET `/metrics` y GET `/slots`, normaliza las respuestas y genera:
- `llama_server_events.jsonl`: eventos NEPENTHES con timestamps de pared y monotónicos.
- `llama_server_capture_manifest.json`: run ID, estados de endpoint, duración, cobertura, checksums y warnings.

## Endpoints

- `/metrics` requiere iniciar llama-server con `--metrics`. Si no está disponible, el capturador registra el warning y continúa con `/slots`.
- Añadir `--require-metrics` para fallar si `/metrics` no está disponible.
- `/slots` está habilitado por defecto en la revisión upstream fijada; solo se exportan `id` e `is_processing`.

## Privacidad y preservación

- No se guardan cuerpos raw de `/slots` ni de `/metrics`; se conservan tamaño y SHA-256 de cada snapshot para trazabilidad.
- El parser de `/metrics` conserva valores de labels allowlisted y solo nombres de labels descartadas.
- El parser de `/slots` no exporta prompts, next tokens ni valores de campos desconocidos.
- No se recogen PID ni métricas por proceso.
- HTTP remoto se rechaza; para endpoints remotos se exige HTTPS. El caso normal de workstation es loopback.

## Límites

No inicia, detiene ni configura llama-server. No realiza inferencia. No correlaciona por sí mismo el reloj monotónico de llama.cpp con NVML/AIPerf. La correlación temporal debe basarse en timestamps calibrados y manifests de campaña.

## Validación

`tests/test_nepenthes_llama_server_capture.py` usa respuestas HTTP simuladas y comprueba endpoints, timestamps, hashes, endpoint metrics deshabilitado, rechazo de HTTP remoto y ausencia de prompt/token values en los eventos.
