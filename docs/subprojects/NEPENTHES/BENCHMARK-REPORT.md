# NEPENTHES — Informe reproducible de benchmark y eficiencia

## Uso

El informe agrega métricas por request, estadísticas de dispersión, errores y, si se proporcionan dos resúmenes NVML comparables, energía incremental y tokens/J.

```bash
python3 scripts/nepenthes_benchmark_report.py \
  --events artifacts/nepenthes/run-001-import/aiperf_events.jsonl \
  --nvml-run-summary artifacts/nepenthes/run-001/nvml_energy_summary.json \
  --nvml-baseline-summary artifacts/nepenthes/baseline-001/nvml_energy_summary.json \
  --output-dir artifacts/nepenthes/run-001-report
```

El informe crea `nepenthes-benchmark-report.json` y `.md`. La baseline se escala por duración a la duración del run antes de restarse.

## Métricas y estadística

- Request latency, TTFT, ITL, ICL, output token count y output sequence length.
- Count, min, max, mean, median, desviación estándar poblacional, MAD, IQR, CV, P50/P90/P95/P99.
- Percentiles por interpolación lineal en `(n-1)*q`; MAD calculada alrededor de la mediana.
- AIPerf `inter_token_latency` es un promedio por request según su definición; el informe no lo presenta como cada intervalo individual de token. Si un artefacto trae un vector explícito, se analiza como vector.
- `output_token_count` representa tokens de contenido excluyendo reasoning; `output_sequence_length` incluye output + reasoning. El informe muestra ambos.

## Energía

- Solo utiliza resúmenes del sampler NVML directo.
- Requiere UUID de GPU coincidentes en run y baseline y calidad `measured_counter` o `estimated` sin gaps.
- Escala energía idle: `E_idle_scaled = E_idle * (T_run / T_idle)`.
- Calcula `E_incremental = E_run - E_idle_scaled`; si no es estrictamente positivo, los ratios quedan null.
- Reporta tokens/J y J/token para contenido y para secuencia completa cuando los contadores de tokens están disponibles.
- La energía es device-level, no atribuida al proceso; campañas con otros procesos concurrentes no se pueden interpretar como consumo de llama.cpp.
- Sin baseline comparable, informa energía bruta y deja tokens/J sin calcular.

## Límites

No declara benchmark ACCEPTED por sí mismo. Para aceptación hacen falta varias repeticiones, configuración completa, hashes, hardware, overhead y validación física del MSI.
