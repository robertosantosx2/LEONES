# LEONES — Guía de scripts operativos

Esta guía está escrita para alguien que sabe ejecutar Python y shell, pero no conoce LEONES.

## Regla fundamental

Un script no define por sí mismo una nueva arquitectura. Su comportamiento está subordinado al contrato que consume o verifica.

Los scripts de auditoría son especialmente importantes: **comprueban el contrato; no lo reemplazan**.

## Selección y ejecución

### `scripts/selection_pipeline.py`

Orquesta la selección declarativa y mantiene la compatibilidad con el registro de runtimes.

**Hace:** enruta una selección hacia las identidades canónicas.  
**No hace:** no demuestra rendimiento físico.  
**No debe hacer:** crear ramas especiales para cada runtime cuando el registro común puede resolverlas.

### `scripts/runtime_gate.py`

Comprueba las condiciones que permiten pasar de una descripción de runtime a una ejecución autorizada.

La separación es deliberada: que un runtime aparezca en el catálogo no significa que el host actual pueda ejecutarlo.

### `scripts/runtimes/run_llama_cpp_selected.py`

Es la ruta concreta de ejecución seleccionada para `llama.cpp`.

Cuando se utiliza para medición real debe conservar la identidad del modelo, cuantización, runtime, comando y resultado. La evidencia posterior es la que permite afirmar que la ejecución ocurrió.

## Medición y evidencia

### `scripts/a01_runtime_benchmark.py`

Implementa el benchmark común de runtime dentro de los límites contractuales establecidos por la arquitectura.

La medición real debe permanecer diferenciada de cualquier estimación externa.

### `scripts/record_benchmark.py`

Registra el resultado del benchmark con la estructura de evidencia correspondiente.

Su responsabilidad es **registrar**, no reinterpretar el resultado ni fabricar métricas que el runtime no produjo.

### `scripts/runtime_evidence_bridge.py`

Conecta un benchmark medido con la frontera de evidencia de LEONES.

El bridge es una transformación controlada: no debe convertirse en un segundo benchmark.

## ODS / Magnitude

### `scripts/ods_magnitude_decision.py`

Aplica el contrato de decisión que une las señales de ODS/Magnitude con LEONES.

La separación importante es:

`señal externa → decisión contractual`

frente a:

`ejecución local → medición → evidencia`

No deben mezclarse ambas rutas hasta el punto definido por el contrato.

### `scripts/integrations/ods_adapter.py`

Adaptador de la información de ODS al formato que espera LEONES.

No es un benchmark local de sustitución.

### `scripts/integrations/magnitude_adapter.py`

Adaptador de la información de Magnitude al formato que espera LEONES.

No es un segundo sistema de scoring.

## Decisión y recomendación

### `scripts/jalon9_recommend.py`

Produce la recomendación canónica a partir de los contratos anteriores.

**No vuelve a puntuar.** Si una recomendación necesita una decisión distinta, esa decisión debe existir en la capa contractual correspondiente.

### `scripts/jalon10_output.py`

Genera la representación final de una recomendación ya establecida.

**No decide, no mide y no vuelve a puntuar.** Su función es transporte fiel.

### `scripts/task_result.py`

Representa el resultado de una tarea dentro del flujo canónico. Su existencia permite que una tarea completada sea trazable sin inventar una segunda semántica de benchmark.

## Trazabilidad

### `scripts/validate_e2e_trace.py`

Valida que la traza E2E respeta el ciclo de vida establecido.

Una traza explica qué ocurrió; no decide qué debería haber ocurrido.

## Runners de auditoría

Los siguientes runners tienen una función común: comprobar un jalón y producir un resultado legible y machine-readable.

- `run_jalon3_audit.sh` — protocolo y evidencia real.
- `run_jalon4_audit.sh` — taxonomía y adapters.
- `run_jalon5_audit.sh` — contrato de decisión.
- `run_jalon5_bridge_audit.sh` — bridge de decisión.
- `run_jalon6_audit.sh` — evidencia y recomendación.
- `run_jalon7_audit.sh` — validación, promoción y publicación.
- `run_jalon8_audit.sh` — trazabilidad E2E.
- `run_jalon10_audit.sh` — salida fiel.

Cuando aparezca un nuevo runner, debe documentarse aquí y en el `.md` del jalón correspondiente.

## Material deprecated

Los scripts trasladados a `scripts/deprecated/` no forman parte de la ruta canónica actual. Se conservan para historial, compatibilidad o migración cuando exista una razón explícita.

No se deben importar desde la ruta operativa nueva sólo porque sean cómodos.

## Cómo elegir qué ejecutar

1. Si quieres comprobar una regla: usa el test o audit runner del contrato.
2. Si quieres seleccionar un runtime: usa la selección y el registro.
3. Si quieres ejecutar físicamente: usa el runner autorizado y conserva evidencia.
4. Si quieres publicar una decisión: usa validation → promotion → publication.
5. Si quieres presentar la recomendación: usa la salida fiel.
6. Si quieres demostrar el recorrido completo: valida la traza E2E.

No hay que saltar directamente a un script inferior para esquivar una frontera contractual.