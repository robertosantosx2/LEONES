# LEONES — Runtime Selection Gate

La selección de modelos y la ejecución son capas distintas.

```text
usuario/tarea/hardware
        ↓
model_selector.py
        ↓
TOP_N / BENCHMARK_REQUIRED
        ↓
runtime_gate.py
        ↓
runtime + cuantización
        ↓
runner del runtime
        ↓
medición observada
```

## Regla de entrada

Solo `selection_status=TOP_N` autoriza la creación de un plan ejecutable.

`BENCHMARK_REQUIRED`, `CANDIDATE`, `SELECTED`, `REJECTED` e `INELIGIBLE` quedan
bloqueados hasta que la capa de selección produzca explícitamente un candidato
TOP-N.

## Responsabilidades

- `model_selector.py`: decide qué modelos son técnicamente candidatos.
- `runtime_gate.py`: convierte una selección autorizada en un plan de ejecución.
- adaptador de runtime: construye el comando concreto.
- runner: ejecuta y extrae la métrica observada.
- benchmark recorder: persiste la medición.

El gate no descarga modelos, no ejecuta procesos y no inventa `measured_tps`.
Las estimaciones de LLMFit se conservan como `estimated_tps` y permanecen
separadas de las mediciones.

## Contrato de salida

Cada plan contiene como mínimo:

- `model_id`
- `variant`
- `runtime`
- `quantization`
- `selection_status`
- `selection_rank`
- `fit_score`
- `evidence_level`
- `execution_authorized`
- `measurement_required`
- `estimated_tps`
- `measured_tps` (`null` antes de ejecutar el benchmark)

## Siguiente capa

Con este contrato cerrado, los runtimes pueden integrarse uno a uno sin
modificar la lógica de selección. El primer runtime de referencia sigue siendo
llama.cpp; posteriormente se pueden conectar vLLM, Transformers/CPU u otros
runtimes cuando exista un adaptador y un contrato de medición equivalente.
