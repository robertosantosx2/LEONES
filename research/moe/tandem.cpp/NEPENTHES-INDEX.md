# NEPENTHES — índice y roadmap de observabilidad

**Estado:** CI completa y verde: pruebas C++17, aplicación de parches y compilación CUDA superadas. La fase sigue sin aceptación funcional hasta completar una captura real y su ingestión en LEONES.

Última actualización: 2026-11-15.

## Fuente de verdad

- Repositorio de instrumentación: [robertosantosx2/tandem.cpp](https://github.com/robertosantosx2/tandem.cpp).
- PR de instrumentación universal: [PR #1 — NEPENTHES: active JSONL sink and full runtime probe applier](https://github.com/robertosantosx2/tandem.cpp/pull/1).
- Rama del PR: [nepenthes/universal-observability-20261114](https://github.com/robertosantosx2/tandem.cpp/tree/nepenthes/universal-observability-20261114).
- Rama de endurecimiento y pruebas: [nepenthes/universal-sink-lifecycle-20261115](https://github.com/robertosantosx2/tandem.cpp/tree/nepenthes/universal-sink-lifecycle-20261115).
- Revisión base fijada de llama.cpp: `f5222f25c18da062ab2b8a2dbbfbf4feae398566`.

El PR #1 conserva el contrato universal `EventType/Event`, el sink JSONL y el aplicador determinista de sondas. Las modificaciones posteriores endurecen el apagado concurrente del sink y verifican que cada evento ocupe una línea física JSONL.

## Roadmap por fases

| Fase | Objetivo | Estado |
|---|---|---|
| 0 | Preservar y correlacionar la evidencia Nsight/CUPTI de Qwen3.5-35B del 14-11-2026 | **Parcial** |
| 1 | Contrato universal de eventos, sink JSONL acotado y activación opt-in | **Implementado en PR #1** |
| 2 | Sondas de runtime: request, graph, KV cache, MoE cache, workers, prefetch, alloc/free, OOM/fallback y transferencias | **Implementadas en el aplicador; compilación CUDA superada** |
| 3 | Compilación CUDA del servidor sobre la revisión fijada | **Superada en GitHub Actions** |
| 4 | Captura real Qwen3.5-35B con JSONL + Nsight y comprobación de pérdida/errores | **Pendiente** |
| 5 | Importación y correlación en el recolector universal de LEONES | **Importación emparejada + modo Nsight-only implementados; inspección del SQLite histórico MSI completada; ingestión real pendiente** |
| 6 | Batería Qwen3.5-35B repetible, informe final y archivo íntegro de evidencias | **Pendiente** |
| 7 | Instalador user-space y CLI `nepenthes run` con paquete de captura e informe HTML | **Implementado en PR #152; CI verde; validación física MSI pendiente** |

## Cobertura prevista

- Ciclo de petición y duración de ejecución del grafo.
- KV cache: asignación, destrucción, clear, actualización, inserción de ubatch, reutilización/liberación de celdas y operaciones de secuencia.
- MoE cache: hit, miss, eviction.
- CPU workers: enqueue, espera, cómputo, finalización y publicación de salida.
- Prefetch/lookahead: enqueue, bytes estimados y espera del evento backend.
- Memoria: alloc/free de backend, CUDA y pinned-host; OOM y fallback.
- Transferencias: spans de submission H2D/D2H, copias 2D y D2D/peer.
- Dispatch por operación `ggml_op`.
- Kernel CUDA individual y actividad memcpy real: proceden de Nsight/CUPTI y su importador SQLite, no de los spans de host.

## Resultados y límites ya establecidos

- La captura correlacionada del 14-11-2026 registró inferencia Qwen3.5-35B: 39 tokens de prompt, 128 tokens generados, aproximadamente 14.96 tokens/s de prompt y 32.07 tokens/s de generación.
- Nsight registró actividad CUDA y transferencias, pero no había eventos NVTX ni identificador de tarea común para enlazar cada kernel con una petición. La coincidencia temporal no equivale a correlación exacta.
- Los eventos internos de worker/CUDA mantienen `request_id=0` cuando no existe correlación demostrable. No se inventa identidad entre hilos.
- Los spans de transferencias CUDA describen submission/dispatch en host; no son duración de ejecución GPU.
- No hubo evidencia suficiente para afirmar que lookahead estuviera activo en aquella captura ni para atribuir transferencias concretas a lookahead.
- No se observó OOM en la ejecución analizada; eso no demuestra ausencia de OOM en otras ejecuciones.
- Los eventos de asignación de KV cache necesitan validación en una captura instrumentada; los datos Nsight anteriores no proporcionaban por sí solos tamaño, tipo y ciclo de vida completos del KV.

## Validación GitHub Actions

- [Workflow NEPENTHES trace hook](https://github.com/robertosantosx2/tandem.cpp/actions/workflows/nepenthes-trace.yml).
- [Ejecución de validación del PR #1 — commit `170d3af9918e2cdf3b5c72f6bb61ab0c3b7b6b52`](https://github.com/robertosantosx2/tandem.cpp/actions/runs/43654679693): **conclusión `success`**. `trace-smoke` y `cuda-compile` finalizaron correctamente. Se compilaron y ejecutaron las pruebas C++17, el sink JSONL pasó sus pruebas, los parches se aplicaron sobre la revisión fijada y `llama-server` se compiló con CUDA para `sm_86`. Esto valida compilación, no una inferencia física ni la cobertura efectiva de todas las sondas.
- [Ejecución previa satisfactoria del PR #1 — commit 9c6b381](https://github.com/robertosantosx2/tandem.cpp/actions/runs/43649113505): CI verde antes de las últimas pruebas de ciclo de vida.

### Rama LEONES sink experimental

La rama [active-leones-sink-20261114](https://github.com/robertosantosx2/tandem.cpp/tree/nepenthes/active-leones-sink-20261114) tiene un contrato distinto (`EventKind/Event`, `Trace::emit` y esquema JSONL con `payload`). Se corrigieron allí el terminador de línea JSONL y el orden de inicialización C++, pero su parche `0001-runtime-worker-prefetch.patch` sigue sin aplicar después de `tandem.patch` (el último CI falló en `src/llama-moe-cache.cpp:2525`). No se debe mezclar ni adoptar esa rama como implementación del recolector universal hasta portar y validar sus sondas sobre el árbol Tandem ya parcheado.

## Preparación del importador LEONES

- [Diseño y contrato del importador Nsight/CUPTI](NEPENTHES-IMPORTER.md).
- Implementación inicial en `scripts/nepenthes_nsys_import.py`, con migración `db/migrations/002_nepenthes_observability.sql` y pruebas de fixtures SQLite/JSONL en `tests/test_nepenthes_nsys_import.py`.
- La primera versión conserva JSONL y actividades Nsight en tablas normalizadas, guarda SHA-256 de los artefactos y no une `request_id` con `correlationId` ni mezcla relojes sin calibración.
- El CLI de PR #152 activa el sink del motor mediante `NEPENTHES_RUN_ID` y `NEPENTHES_TRACE_JSONL`, consolida eventos de host/motor y lanza el importador automáticamente cuando existe SQLite Nsight. La integración completa pasa tests sintéticos con una SQLite CUPTI fixture.
- El importador incorpora `--inspect-nsys` para auditar en modo solo lectura el esquema del SQLite histórico Qwen3.5-35B sin inventar un JSONL emparejado. La inspección real del archivo se ejecutó en el MSI: SQLite de 7.913.472 bytes, con 8.982 kernels, 44.488 memcpy, 9 memset, 84.116 runtime, 5.207 graph trace, 7.864 synchronization, 262 CUDA events y 111 overhead. El modo `--nsys-only` añade la importación de capturas históricas sin JSONL emparejado, manteniendo `run_id=null` y procedencia separada. La ingestión completa de ese SQLite real y su validación en MSI siguen pendientes.

## Criterio de aceptación

La fase de observabilidad solo se marca como aceptada cuando se cumplan todos estos puntos:

1. CI pasa las pruebas C++17, el aplicador determinista y la compilación CUDA.
2. Una inferencia real produce JSONL parseable, sin pérdidas no explicadas ni errores de escritura.
3. La captura Nsight/CUPTI de la misma ejecución se importa en LEONES.
4. Se valida cobertura de categorías, límites de correlación y separación de tiempos host/GPU.
5. Se archivan modelo, configuración, commit, logs, JSONL, SQLite, Nsight report, respuesta y manifiesto reproducible.

**Regla de evidencia:** ESTIMATED, compilación, captura y medición son estados distintos. Ningún resultado se etiqueta MEASURED sin ejecución física registrada.


## Instalador y ejecutable NEPENTHES

- [Diseño del instalador, CLI y paquete de captura](NEPENTHES-CLI.md).
- Instalador: `scripts/install_nepenthes.sh` (instalación user-space, sin root).
- Ejecutable: `scripts/nepenthes.py`; uso de una línea: `nepenthes run -- <motor> <argumentos>`.
- La primera versión registra CPU/RSS agregados del árbol de procesos y telemetría GPU global si `nvidia-smi` está disponible; genera SQLite local y hashes SHA-256. Produce `manifest.json`, `raw/events.jsonl`, `data/samples.csv`, `data/observations.sqlite` (tablas `samples` y `events`), `data/summary.json`, `session.log`, `checksums.sha256` e informe HTML/Markdown con tablas y gráficas SVG.
- Esta entrega es una base funcional y portátil; el perfil `full` orquesta opcionalmente `nsys profile`, conserva SQLite/NSYS reportes y ejecuta automáticamente el importador LEONES si encuentra el artefacto SQLite. El JSONL del host usa el contrato 1.0 que valida el importador; el join request-kernel sigue desactivado por falta de calibración de relojes e IDs comunes. Las sondas internas del motor siguen siendo una fase posterior y no se simulan.
- Tests sintéticos añadidos en `tests/test_nepenthes_cli.py`. La validación física en el MSI sigue pendiente.


## Instalador y CLI de captura

- [NEPENTHES-CLI.md](NEPENTHES-CLI.md): contrato de instalación, invocación, perfiles, activación de sondas, paquete de resultados y límites.
- PR de integración: [LEONES #152](https://github.com/robertosantosx2/LEONES/pull/152), apilado sobre [LEONES #151](https://github.com/robertosantosx2/LEONES/pull/151).
- La batería GitHub Actions del árbol final (squash `e68c9be`; árbol probado en `efb2c124`) pasó: Contract Tests con **470 pruebas**, V1 regression, runtime-v11 regression, RC3 Release Gate y Agentic A01. La validación física y la captura Qwen3.5 en el MSI siguen pendientes.


## Importación Nsight histórica (sin JSONL)

- Nuevo modo de importación standalone: `--nsys-only SQLITE --output DB`; no exige JSONL ni inventa un `run_id`.
- Migración 003 separa los registros Nsight-only de las importaciones emparejadas.
- Se incorporan adaptadores para `GRAPH_TRACE`, `SYNCHRONIZATION`, `CUDA_EVENT` y `OVERHEAD`, además de las actividades CUDA ya normalizadas.
- El informe distingue tablas CUPTI importadas y tablas detectadas sin adaptador; no se declara cobertura completa cuando hay tablas desconocidas con filas.
- Desarrollo en [PR #153 — modo Nsight-only](https://github.com/robertosantosx2/LEONES/pull/153), apilado sobre PR #152. No fusionado.
