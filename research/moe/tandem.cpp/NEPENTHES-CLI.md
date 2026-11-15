# NEPENTHES: instalador, CLI y paquete de captura

## Objetivo

NEPENTHES se instala en user-space y se invoca antes del motor. Lanza el comando solicitado, activa la instrumentación de un motor que ya haya sido compilado con las sondas NEPENTHES, recoge telemetría de host/GPU disponible y genera un paquete de resultados. No requiere root para la instalación ni modifica drivers, CUDA, modelos o binarios del motor.

## Instalación y diagnóstico

```bash
./scripts/install_nepenthes.sh
export PATH="$HOME/.local/bin:$PATH"
nepenthes doctor
nepenthes self-test
```

Instala `nepenthes` en `~/.local/bin` y recursos en `~/.local/share/nepenthes`. El instalador incorpora el CLI, el importador y las migraciones 002/003. Requiere Python 3.10+.

## Invocación

```bash
nepenthes run --profile full -- ./llama-server -m /ruta/modelo.gguf -c 1024
```

El comando después de `--` se ejecuta como proceso hijo. NEPENTHES conserva stdout/stderr en el log de sesión, muestrea CPU/RSS del árbol de procesos, registra telemetría NVIDIA global si `nvidia-smi` está disponible y propaga el código de salida del motor.

Antes del arranque define `NEPENTHES_RUN_ID` y `NEPENTHES_TRACE_JSONL`. Un motor Tandem.cpp instrumentado puede emitir eventos internos a `raw/engine-events.jsonl`; el recolector de host escribe `raw/host-events.jsonl` y ambos flujos se consolidan en `raw/events.jsonl`. Un motor no instrumentado sigue permitiendo capturar host/GPU, pero no produce eventos internos. El CLI no parchea ni recompila el motor.

## Perfiles y Nsight

- `smoke`: muestreo ligero.
- `standard`: muestreo estándar (predeterminado).
- `full`: muestreo más frecuente y captura Nsight automática cuando está disponible.

Control:
- `--nsys auto`: selección automática según perfil y disponibilidad.
- `--nsys required`: falla antes de arrancar si Nsight no está disponible.
- `--nsys off`: desactiva Nsight, no el sink del motor.
- `--interval SECONDS`: cambia el intervalo de muestreo.

Nsight puede añadir overhead o fallar por incompatibilidad de driver, permisos o configuración. NEPENTHES no eleva privilegios automáticamente. Los artefactos nativos se conservan en `raw/`.

## Paquete de salida

```text
RUN_ID/
  manifest.json
  session.log
  environment/
  raw/
    host-events.jsonl
    engine-events.jsonl
    events.jsonl
    nsys.sqlite
    nsys.nsys-rep
  data/
    samples.csv
    observations.sqlite
    summary.json
    nsys-import.json
    nepenthes-import.sqlite
  reports/
    index.html
    report.md
  checksums.sha256
```

Los archivos que dependen de instrumentación o Nsight solo aparecen cuando están disponibles. El informe HTML/Markdown se construye desde las muestras y actividades efectivamente recogidas; las gráficas SVG no deben confundirse con datos simulados. `nepenthes verify RUN_DIR` valida hashes y estructura del paquete.

## Estado de validación en MSI — 2026-11-15

- Instalador user-space: correcto; comando instalado en `~/.local/bin/nepenthes`.
- `nepenthes doctor`: correcto; entorno Linux, Python, procfs, `nvidia-smi` y Nsight Systems detectados en la validación registrada.
- `nepenthes self-test`: correcto; 3 eventos, 1 muestra, 3 filas de eventos, `events_valid=true`, `report_html=true`, `checksums=true` y `errors=[]`.
- Ejecución real de un motor instrumentado: completada con Qwen3.5-4B Q4_K_M en CPU-only mediante `nepenthes run`; se capturaron 3.683 eventos del motor, incluidos `request_start/request_end`, y el proceso terminó con código 0.
- La captura C06 utilizó `--nsys off`; por tanto, no demuestra todavía una ejecución integrada con Nsight ni sustituye la aceptación de una captura emparejada JSONL+Nsight.
- Importación histórica Nsight-only real: 151.039 actividades importadas y auditadas; detalle en [informe histórico Qwen3.5](NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115.md).

**Pendiente:** verificar `nepenthes verify` y auditar el paquete completo de la inferencia real C06; ejecutar una captura emparejada JSONL+Nsight de una misma ejecución; medir overhead y completar la matriz de cobertura. El self-test y la importación Nsight-only histórica no sustituyen esas pruebas.

## Límites

La telemetría de `nvidia-smi` es global al dispositivo. Las sondas internas requieren un binario instrumentado. La captura Nsight tiene overhead. No se une `request_id` con CUPTI `correlationId` ni se mezclan relojes sin calibración. Las duraciones de kernels individuales proceden de Nsight/CUPTI.
