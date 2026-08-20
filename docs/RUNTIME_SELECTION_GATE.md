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
adaptador llama.cpp
        ↓
runner
        ↓
medición observada
```

## Regla de entrada

Solo `selection_status=TOP_N` autoriza la creación de un plan ejecutable.
`BENCHMARK_REQUIRED`, `CANDIDATE`, `SELECTED`, `REJECTED` e `INELIGIBLE` quedan
bloqueados.

## llama.cpp

`llama_cpp_adapter.py` acepta únicamente un plan autorizado para `llama.cpp`.
La cuantización no se traduce automáticamente a una opción CLI: identifica el
artefacto seleccionado (por ejemplo, un GGUF) y no debe inventarse un flag.

`run_llama_cpp_selected.py` es el puente final local: recibe el plan, modelo,
prompt y perfil de ejecución; construye el comando sin shell, ejecuta llama.cpp
y registra exclusivamente el `tok/s` observado.

## Separación de señales

- `estimated_tps`: estimación externa, por ejemplo LLMFit.
- `measured_tps`: resultado de una ejecución real.
- El runtime no convierte una estimación en una medición.
- El benchmark recorder marca los resultados reales como `measurement_type=measured`.

## Siguiente integración

Los demás runtimes deben implementar el mismo contrato antes de conectarse al
selector. Esto permite añadir vLLM, Transformers/CPU u otros runtimes sin
duplicar la lógica de selección ni relajar sus controles.
