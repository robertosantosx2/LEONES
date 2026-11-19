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

- Rama instalada: `feat/nepenthes-nsys-only-20261115`, commit `6889e967`.
- Instalador: correcto; comando instalado en `~/.local/bin/nepenthes`.
- `nepenthes doctor`: correcto; Linux 7.0.0-43, Python 3.14.4, procfs, `/usr/bin/nvidia-smi`, Nsight Systems en `/usr/local/cuda-13.4/bin/nsys`.
- `nepenthes self-test`: correcto; run `20261115_084802_self-test_2ee4af8e`; 3 eventos, 1 muestra, 3 filas de eventos, `events_valid=true`, `report_html=true`, `checksums=true`, `errors=[]`.
- Importación Nsight-only real: 151.039 actividades; detalle en [informe histórico Qwen3.5](NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115.md).

**Pendiente:** una ejecución real de un motor instrumentado mediante `nepenthes run`, con comprobación de variables de activación, exit code, eventos del motor, Nsight y `nepenthes verify` sobre el paquete resultante. El self-test no sustituye esta prueba.

## Límites

La telemetría de `nvidia-smi` es global al dispositivo. Las sondas internas requieren un binario instrumentado. La captura Nsight tiene overhead. No se une `request_id` con CUPTI `correlationId` ni se mezclan relojes sin calibración. Las duraciones de kernels individuales proceden de Nsight/CUPTI.


## Verificación ampliada del paquete y correlación

`nepenthes verify RUN_DIR` valida ahora:

- SHA-256 de todos los artefactos, ausencia de ficheros sin hash y rutas contenidas en el bundle.
- Manifest terminal, run_id, schema_version, recuento de eventos y consistencia con summary.json.
- Contrato tipado de correlation_token y attribution_level; exact exige token explícito y nunca se infiere por proximidad.
- Balance request_start/request_end y NVTX start/end por token.
- clock_calibration start/end, timestamps monotónicos/Unix y estimación de offset/drift host.
- Integridad SQLite de observaciones y de la importación Nsight; run_id de importación debe coincidir con el manifest.
- Cuando hay NVTX y Nsight: al menos dos pares token+fase para calibrar host↔Nsight, ausencia de atribución exacta falsa a kernels y consistencia de la atribución windowed.

Si no hay NVTX o Nsight no fue solicitado, el verificador informa esa limitación sin inventar correlación. Un bundle íntegro no equivale por sí solo a C07 aceptado: la captura real y la validación física siguen siendo necesarias.


## Gates C07/C08 y significado de verify

El resultado separa dos conceptos:

- `ok`: el bundle es íntegro, sus hashes/SQLite/manifest/eventos son coherentes y los contratos presentes no son inválidos.
- `functional_complete`: los gates de esta campaña han pasado: C07 exige marcadores NVTX emparejados y calibración host↔Nsight válida; C08 exige el informe paired-overhead en `data/c08-overhead-report.json`, perfil `standard`, al menos tres pares y estado `accepted` para JSONL, Nsight y combinado.

Si C07 o C08 todavía no se han ejecutado, el bundle puede ser válido (`ok=true`) pero `functional_complete=false` y el estado se muestra como pendiente. Un informe C08 con excepción o bloqueo impide la aceptación. Los gates de campaña no sustituyen la CI del repositorio ni la validación física del MSI.


El informe C08 puede mantenerse como artefacto de campaña externo. Para verificarlo sin incorporarlo al checksum del run, se acepta `nepenthes verify RUN_DIR --c08-report REPORT.json`; el resultado incluye la ruta y SHA-256 del informe. El comparador registra además los SHA-256 de cada evidencia emparejada.


## AIPerf-first C08 — flujo de evidencia aceptado en CI

La integración está en scripts/nepenthes_aiperf_run.py, scripts/nepenthes_aiperf_import.py, scripts/nepenthes_aiperf_evidence.py y scripts/nepenthes_overhead_gate.py. El runner fija AIPerf **0.13.0** y no guarda credenciales ni texto generado.

Ejemplo de campaña (ejecutar solo cuando el servidor de inferencia ya esté activo y su PID sea conocido):

```bash
RUN="$HOME/NEPENTHES-runs/c08-pair-001"
mkdir -p "$RUN"

python scripts/nepenthes_aiperf_run.py \
  --model "$MODEL_ID" \
  --url "http://127.0.0.1:8080" \
  --artifact-dir "$RUN/aiperf" \
  --target-pid-file "$RUN/server.pid" \
  --request-count 5 \
  --input-tokens 128 \
  --output-tokens 32 \
  --random-seed 42

python scripts/nepenthes_aiperf_import.py \
  --artifacts-dir "$RUN/aiperf" \
  --output-dir "$RUN/import"

python scripts/nepenthes_aiperf_evidence.py \
  --artifacts-dir "$RUN/aiperf" \
  --import-dir "$RUN/import" \
  --output "$RUN/evidence.json" \
  --model-artifact "$MODEL_PATH" \
  --model-id "$MODEL_ID" \
  --model-name "$MODEL_NAME" \
  --model-revision "$MODEL_REVISION" \
  --quantization "$QUANTIZATION" \
  --context 1024 \
  --engine-version "$ENGINE_VERSION" \
  --engine-revision "$LLAMA_CPP_COMMIT" \
  --backend cuda \
  --hardware-id "$HARDWARE_ID" \
  --condition off \
  --pair-id pair-001 \
  --profile standard
```

Repetir el flujo con el mismo pair-id para jsonl, nsys y combined, cambiando únicamente la condición de instrumentación. Mantener constantes modelo, dataset/prompt, contexto, seed, configuración y comando de workload. El wrapper necesita --target-pid o --target-pid-file para que RSS corresponda al servidor y no al cliente AIPerf.

El wrapper registra el SHA-256 del comando normalizado y de la salida bruta; el log AIPerf se elimina por defecto. --store-aiperf-log lo conserva de forma explícita y debe tratarse como potencialmente sensible. La URL no puede contener credenciales, query tokens ni fragmentos.

Gate sobre todas las evidencias de los pares:

```bash
python scripts/nepenthes_overhead_gate.py \
  --evidence "$RUNS"/*/evidence.json \
  --profile standard \
  --min-pairs 3 \
  --max-decode-overhead 5 \
  --warn-decode-overhead 8 \
  --output c08-overhead-report.json
```

El gate usa mediana e IQR y exige TTFT, duración total de campaña, throughput, RSS del servidor, RAM de sistema y VRAM device-wide. Distingue request_latency_mean_ms de total_time_ms (duración de campaña). La CI demuestra el contrato del pipeline; solo una campaña real en MSI puede producir aceptación de overhead.

## Estado MSI pendiente

Los PRs LEONES #197 y #198 están integrados y sus gates CI pasaron. El siguiente paso físico no es un self-test: es compilar el fork llama.cpp rebased, lanzar una inferencia real, capturar NVTX/CUPTI con Nsight, importar el bundle y ejecutar nepenthes verify y el gate C08 sobre las repeticiones. No declarar functional_complete antes de ello.
