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

La orden `nepenthes verify RUN_DIR` valida ahora:

- SHA-256 de todos los artefactos, ausencia de ficheros sin hash y rutas contenidas en el bundle.
- Manifest terminal, run_id, schema_version, recuento de eventos y consistencia con summary.json.
- Contrato tipado de correlation_token y attribution_level; exact exige token explícito y nunca se infiere por proximidad.
- Balance request_start/request_end y ciclos NVTX request.start/request.end por token.
- Ciclos NVTX batch.start/batch.end: exactamente un inicio y un fin por token, `request_id=0` en los marcadores y correspondencia del conjunto de tokens con los eventos `server.batch_member`.
- clock_calibration start/end, timestamps monotónicos/Unix y estimación de offset/drift host.
- Integridad SQLite de observaciones y de la importación Nsight; run_id de importación debe coincidir con el manifest.
- Correlación host↔Nsight separada por scope request/batch. Para C07 batch, cada marcador start/end debe tener pareja NVTX en Nsight y cada token debe tener actividad CUDA atribuida `windowed` bajo el mismo proceso e hilo.
- Rechazo de atribución GPU exact, ventanas batch solapadas, actividad sin token, identidad de hilo ausente/discrepante y marcadores NVTX que no conserven su token.

Si no hay NVTX o Nsight no fue solicitado, el verificador informa esa limitación sin inventar correlación. Un bundle íntegro no equivale por sí solo a C07 aceptado: la captura real y la validación física siguen siendo necesarias.

## Gates C07/C08 y significado de verify

El resultado separa tres estados:

- `ok`: el bundle es íntegro, sus hashes/SQLite/manifest/eventos son coherentes y los contratos presentes no son inválidos.
- `acceptance.c07_request`: ciclo NVTX request y calibración request host↔Nsight válidos.
- `acceptance.c07_batch`: ciclo NVTX batch, membresía many-to-many, calibración batch host↔Nsight y actividad CUDA `windowed` por proceso+hilo válidos.
- `acceptance.c07`: solo pasa cuando C07 request y C07 batch pasan.
- `functional_complete`: exige C07 request + C07 batch y el informe paired-overhead C08 en `data/c08-overhead-report.json`, perfil `standard`, al menos tres pares y estado `accepted` para JSONL, Nsight y combinado.

Si C07 batch o C08 todavía no se han ejecutado, el bundle puede ser válido (`ok=true`) pero `functional_complete=false` y el estado se muestra como pendiente. Una captura batch-only puede tener `c07_batch_correlation=true` mientras `c07_request_correlation` permanece pendiente; la aceptación request-level previa se mantiene en el INDEX maestro y no se degrada por no repetirse en este run. Un informe C08 con excepción o bloqueo impide la aceptación. Los gates de campaña no sustituyen la CI del repositorio ni la validación física del MSI.

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

## Gate remoto cerrado — 2026-11-20

La compilación remota exacta ya está aceptada para los conectores actuales:

- llama.cpp PR #10 merge `d4d0b9eeb2bd0035f525a90aefed111e5d74edcb`; CPU/CUDA SM86 + importer LEONES en workflow `44682285336`.
- Tandem.cpp PR #7 merge `7c4300eb754d94737c6aa8d7ffa0077aac7ddcb9`; patch application + `trace-smoke` + CUDA SM86 en workflow `44682021976`.
- El productor NVTX Tandem es opt-in (`NEPENTHES_NVTX=1`) y está disabled por defecto. No añadir sincronización CUDA.
- La atribución batch del importer sigue `windowed`, many-to-many y no causal.

**El siguiente gate requiere el MSI:** C07 debe demostrar una captura emparejada de la misma ejecución (JSONL del motor + NVTX + Nsight/CUPTI), con calibración host↔Nsight y token/ventanas válidas. C08 requiere baseline y condiciones instrumentadas emparejadas, al menos tres pares y el gate standard (decode overhead ≤5%; 5–8% requiere excepción; >8% bloquea). Ningún build remoto sustituye estas mediciones físicas.

## Estado MSI pendiente

Los gates remotos actuales están cerrados mediante llama.cpp PR #10 y Tandem.cpp PR #7. El siguiente paso físico no es un self-test: sincronizar los commits fusionados, compilar el runtime instrumentado en el MSI, lanzar una inferencia real, capturar NVTX/CUPTI con Nsight, importar el bundle y ejecutar `nepenthes verify` y el gate C08 sobre las repeticiones. No declarar `functional_complete` antes de ello.


### AIPerf warm-up provenance correction — 2026-11-19

The runner now passes AIPerf's explicit --warmup-request-count (default 1). The evidence manifest and command fingerprint record this value, and the evidence builder rejects a missing warm-up count. LEONES PR #199 is now merged as `109e3073cd0040a5ba86b906e71e003959f72d3c`: the runner defaults to one explicit warm-up request, records it in the workload command fingerprint and manifest, and the evidence builder rejects manifests without that field. CI passed **572 tests** plus all release/runtime gates. This is still software acceptance only; no C08 performance result is claimed.


## Perfiles de captura

- `smoke`: captura ligera para comprobar que el bundle y el contrato funcionan.
- `standard`: muestreo host regular; perfil de referencia para C08.
- `full`: muestreo más frecuente y Nsight automático cuando está disponible.
- `moe-deep`: muestreo adaptativo basado en marcadores explícitos del motor; 100 ms mientras hay una request activa y 1 s en reposo. Nsight se activa automáticamente si está instalado. No correlaciona por proximidad.
- `latency-critical`: desactiva el muestreo periódico host y Nsight; el wrapper espera al proceso y conserva el sink de eventos. No usar para C08 porque no aporta RSS/RAM/VRAM muestreados.

Ejemplos:

```bash
# Muestreo adaptativo MoE
nepenthes run --profile moe-deep --adaptive-sampling -- python -m your_engine

# Captura de latencia sin muestreo host ni Nsight
nepenthes run --profile latency-critical --nsys off -- python -m your_engine
```

**Límite actual:** los perfiles gobiernan el recolector host y la política Nsight. La capa C++ todavía no filtra el conjunto de sondas internas según `NEPENTHES_PROFILE`; esa separación (especialmente reducir latency-critical a request markers) debe implementarse y probarse antes de afirmar que el perfil elimina todo overhead de sondas no esenciales.
