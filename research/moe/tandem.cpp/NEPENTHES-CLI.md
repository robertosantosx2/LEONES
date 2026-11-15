# NEPENTHES: instalador, CLI y paquete de captura

## Objetivo

NEPENTHES es una capa de observabilidad del host. Se invoca antes del motor,
lanza el proceso solicitado, activa las sondas de un motor ya instrumentado,
registra telemetría disponible y genera un paquete portable al terminar.
No requiere modificar el código del motor en tiempo de ejecución.

## Instalación

Desde el checkout de LEONES:

```bash
./scripts/install_nepenthes.sh
```

Instala `nepenthes` en `~/.local/bin` y el importador Nsight más la migración
002 en `~/.local/share/nepenthes`. Solo necesita Python 3.10+, no requiere root
y no modifica CUDA, drivers, modelos ni binarios del motor.

## Invocación de una línea

```bash
nepenthes run --profile full -- ./llama-server -m /ruta/modelo.gguf -c 1024
```

El comando posterior a `--` se ejecuta como proceso hijo. NEPENTHES guarda
stdout/stderr en `session.log`, mide CPU/RSS agregados del árbol de procesos,
muestrea telemetría NVIDIA global si `nvidia-smi` está disponible y devuelve
el código de salida del motor.

Antes de lanzar el motor, el CLI define `NEPENTHES_RUN_ID` y
`NEPENTHES_TRACE_JSONL`. Si el motor ya está compilado con el sink y las sondas
NEPENTHES de Tandem.cpp, estos se activan automáticamente y escriben en
`raw/engine-events.jsonl`. El recolector del host escribe en
`raw/host-events.jsonl`; al terminar se consolidan ambos flujos en
`raw/events.jsonl`, con IDs únicos y preservando el ID original del motor.
Si el motor no está instrumentado, se mantiene la captura de host/GPU y el
informe indica que no hubo eventos internos. El CLI no parchea ni recompila
el motor por sí solo.

Perfiles:
- `smoke`: muestreo ligero, 2 s.
- `standard`: 1 s, predeterminado.
- `full`: 0,5 s y captura Nsight automática si `nsys` está en PATH.

Control Nsight:
- `--nsys auto`: se activa automáticamente en perfil `full` si está instalado.
- `--nsys required`: exige Nsight y aborta antes de arrancar el motor si falta.
- `--nsys off`: desactiva Nsight, pero no desactiva el sink del motor.
- `--interval SECONDS`: modifica el intervalo de muestreo.

Nsight se invoca con `nsys profile`, trazas CUDA/NVTX/OSRT, exportación SQLite
y opciones para reducir overhead (`--sample=none`, `--cpuctxsw=none`).
Los ficheros originales se conservan en `raw/`. La captura puede añadir
overhead o fallar por incompatibilidades de driver, permisos o configuración;
NEPENTHES no eleva privilegios automáticamente. Véase la
[documentación oficial de Nsight Systems CLI](https://docs.nvidia.com/nsight-systems/UserGuide/).

## Paquete de resultados

```text
RUN_ID/
  manifest.json
  session.log
  environment/
    system.json
    gpu-initial.json
  raw/
    host-events.jsonl
    engine-events.jsonl       # si el motor instrumentado emite eventos
    events.jsonl              # flujo combinado para el importador
    nsys.sqlite               # si Nsight exporta SQLite
    nsys.nsys-rep              # si Nsight genera el reporte nativo
  data/
    samples.csv
    observations.sqlite        # tablas samples y events
    summary.json
    nsys-import.json
    nepenthes-import.sqlite    # si la importación emparejada tiene éxito
  reports/
    index.html
    report.md
  checksums.sha256
```

El informe HTML contiene una tabla cuantitativa y gráficas SVG generadas desde
las muestras reales. `nepenthes verify RUN_DIR` comprueba hashes, contrato JSONL,
IDs únicos, integridad SQLite y presencia del informe sin modificar el paquete. CSV, SQLite y JSON quedan disponibles para análisis.
El importador LEONES se ejecuta automáticamente cuando hay un SQLite Nsight
reconocido; registra su estado en `data/nsys-import.json`. Si falla, conserva
el diagnóstico y no altera el código de salida del motor.

## Contrato de eventos y correlación

Los eventos de host y motor usan el contrato JSONL 1.0: `run_id`, `event_id`,
`source`, relojes wall/monotonic, `request_id`, tipo, etiqueta, valores,
duración y flags. Los IDs de motor se normalizan en el flujo combinado para
evitar colisiones entre procesos, preservando el ID original como
`source_event_id`.

El importador conserva los eventos JSONL y las actividades CUPTI, pero no une
`request_id` con CUPTI `correlationId` ni mezcla relojes sin calibración.
La GPU se muestrea a nivel de dispositivo, no se atribuye por PID. Los tiempos
de dispatch/host no se presentan como duraciones de ejecución de kernels.

## Evidencia y límites

La CLI mide el árbol de procesos lanzado mediante `/proc`, y utilización,
memoria y temperatura global NVIDIA mediante `nvidia-smi`. Las sondas internas
solo aparecen cuando el motor ha sido compilado con las capas de instrumentación
de Tandem.cpp. La cobertura prevista incluye lifecycle de request, graph compute,
sincronización, caché MoE, KV cache, workers CPU, prefetch, alloc/free, OOM/
fallback y transferencias; las duraciones de kernels individuales proceden de
Nsight/CUPTI.

La validación sintética y CI no sustituyen la compilación CUDA real ni una
captura de inferencia. La validación física en el MSI y Qwen3.5 sigue pendiente.

## Próximas fases

1. Completar la validación MSI del wrapper, activación de sondas y captura Nsight.
2. Ampliar la cobertura de runtime que aún no está instrumentada.
3. Analizar la correlación temporal sin inventar joins entre relojes o IDs.
4. Añadir tablas específicas de KV cache/MoE y comparativas de ejecuciones.
