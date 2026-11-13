# Medición de recursos por petición — Tandem.cpp

Estos scripts añaden telemetría por petición a la batería existente. El cliente no inicia, detiene, reinicia ni reconfigura el servidor de inferencia.

## Archivos

- \`run_battery.py\`: ejecuta la batería y abre/cierra una ventana de medición para cada petición.
- \`resource_monitor.py\`: muestrea Linux \`/proc\`, \`/proc/diskstats\` y \`nvidia-smi\`.

Ambos deben permanecer en el mismo directorio \`repro/\`.

## Uso

Desde el checkout de los scripts:

\`\`\`bash
python3 run_battery.py \\
  --base-url http://127.0.0.1:18086 \\
  --model Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf \\
  --engine tandem.cpp \\
  --mode same-engine-new-model \\
  --model-path "$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf" \\
  --monitor-interval 1.0 \\
  --output "$HOME/Descargas/tandem-monitored-$(date +%Y%m%d-%H%M%S)"
\`\`\`

Para una prueba corta de validación, añadir \`--limit 1\`. Si la autodetección del proceso no encuentra el servidor, pasar \`--server-pid PID\`. El detector busca un proceso \`llama-server\` cuya línea de órdenes contenga el puerto de la API.

## Datos por petición

Cada respuesta JSON y cada línea de \`summary.jsonl\` incorporan \`resource_metrics\`. Se generan además:

- \`resources/resource_samples.jsonl\`: muestras brutas con hora, identificador local de petición y PID.
- \`responses/*.json\`: respuesta, métricas de tokens y resumen de recursos de esa petición.
- \`run_manifest.json\`: configuración, endpoint y cadencia del monitor.

El resumen contiene:

| Área | Datos |
|---|---|
| RAM | Usada y disponible en el host; RSS del proceso servidor; mínimo, máximo y media de las muestras. |
| Swap | Ocupación; deltas de páginas intercambiadas hacia/desde swap durante la ventana. |
| CPU | Porcentaje de CPU del sistema y porcentaje del proceso servidor calculados sobre el intervalo de la petición. El proceso puede superar 100% si usa varios núcleos. |
| GPU / VRAM | Utilización GPU y de memoria, VRAM usada, temperatura, potencia y reloj gráfico; mínimo, máximo y media de las muestras NVIDIA disponibles. |
| SSD / bloque | Deltas de bytes y operaciones leídas/escritas y tiempo de E/S por dispositivo de bloque completo. Se registra también el montaje que contiene la ruta local del modelo. |

## Interpretación y límites

1. La cadencia predeterminada es un segundo. Se guardan muestras al principio y al final; una petición muy corta puede tener solo dos muestras y no capturar un pico transitorio.
2. \`nvidia-smi\` se consulta en cada muestra. Su latencia forma parte del coste del monitor y puede añadir una pequeña carga; mantener la misma cadencia en todas las comparaciones.
3. CPU, RAM y swap del host son métricas globales. RSS y CPU del proceso corresponden al PID detectado.
4. Los contadores de swap y disco son del sistema/dispositivo, no exclusivos del proceso de inferencia. Si hay otros trabajos de E/S simultáneos, también aparecerán. Los deltas se calculan por dispositivo, sin sumar dispositivos virtuales y físicos entre sí.
5. \`findmnt\` identifica el montaje que contiene el GGUF, pero los contadores de E/S se presentan por dispositivo de bloque. En configuraciones LVM, cifradas o con varios discos hay que interpretar la topología para evitar contar dos veces capas del mismo almacenamiento.
6. La ausencia de muestras NVIDIA se informa como tal; no se inventan valores. Hace falta que \`nvidia-smi\` esté instalado y accesible.
7. El monitor no mide temperatura del SSD, latencia por petición a nivel de archivo, IOPS exclusivos del proceso ni energía de CPU. Para eso haría falta instrumentación adicional específica del dispositivo.

## Validación recomendada

Primero ejecutar solo una petición con \`--limit 1\`, comprobar que el PID no sea nulo y que \`resource_samples.jsonl\` contenga varias muestras. Revisar después que \`resource_metrics\` aparezca tanto en el JSON de la petición como en \`summary.jsonl\`. Solo entonces lanzar la batería completa. No ejecutar simultáneamente dos baterías contra el mismo servidor de un solo slot.



## MoE runtime probe (added 2026-11-14)

`run_battery.py` now starts [`moe_runtime_probe.py`](moe_runtime_probe.py) for every request and adds the summary to `moe_runtime_metrics`. This probe samples process I/O/scheduler counters, thread count, RSS/HWM, file descriptors, kernel CPU/memory/I/O PSI, and CPU frequency. The shared `resource_monitor.py` captures NVIDIA utilization/VRAM/temperature/power/clocks and PCIe RX/TX throughput when exposed by `nvidia-smi`. Raw samples are written to `resources/moe_runtime_samples.jsonl`; the GPU/PCIe time series remains in `resources/resource_samples.jsonl`.

Use `--monitor-interval 0.5` for the next controlled run. PCIe counters are device-wide; PSI is host-wide. Neither is attributable to the server alone. Keep cadence constant across all A/B runs.

## MoE cache and routing log inspector

`inspect_NEPENTHES_moe_trace.py` reads the saved server log and/or an MCT1 routing trace:

```bash
python3 inspect_NEPENTHES_moe_trace.py --server-log "$HOME/path/to/tandem.log" --output "$HOME/moe-cache-summary.json"
python3 inspect_NEPENTHES_moe_trace.py --trace "$HOME/path/to/moe.trace" --server-log "$HOME/path/to/tandem.log"
```

The exact Tandem.cpp llama.cpp submodule commit used for the reference build (`f5222f25c18da062ab2b8a2dbbfbf4feae398566`) has aggregate cache hit/miss/upload logging but does not implement `LLAMA_MOE_CACHE_TRACE`/MCT1. Thus routing-per-layer data will be unavailable in the next run unless the engine is separately instrumented or upgraded. The inspector supports MCT1 for compatible future builds; it does not generate a trace itself.
