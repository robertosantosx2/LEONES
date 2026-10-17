# Runtime → Agentic Benchmark V1

## Propósito

Cerrar el contrato entre la selección canónica y el runner agentic sin mezclar predicción con medición.

El selector/runtime gate ya produce un plan con identidad de modelo, runtime, cuantización y estado de selección. El adaptador agentic consume ese plan y exige dos invariantes: `execution_authorized=true` y `measurement_required=true`.

## Flujo

```text
hardware
  ↓
LLMFit / Atlas
  ↓
model_selector
  ↓
runtime_gate
  ↓
RuntimePlan
  ↓
ModelRuntimeAdapter
  ↓
Agentic Runner
  ↓
trace + grader + result.json
  ↓
measured evidence
  ↓
Atlas
```

## Separación de responsabilidades

- **LLMFit:** estimación inicial de encaje.
- **model_selector:** decisión canónica y ranking.
- **runtime_gate:** autorización de ejecución y bloqueo de candidatos inválidos.
- **LLMServe / runtime backend:** descubrimiento, preparación y ejecución del modelo.
- **Agentic Runner:** límites, trazas, herramientas y contrato de resultados.
- **Graders:** determinación del resultado de cada tarea.
- **Atlas:** almacenamiento y relación de evidencia.

Ninguna capa convierte automáticamente `estimated` o `reported` en `measured`; el runner solo puede emitir `measured` cuando existe ejecución identificable. `verified` requiere un verificador independiente.

## Regla para LLMServe

Cuando el runtime elegido sea LLMServe, el adaptador debe tratar LLMServe como infraestructura de serving y conservar la configuración efectiva usada en la ejecución. El código upstream no se modifica dentro de LEONES.

## Primera integración

A01 es el primer objetivo de integración real. El `smoke_a01.py` existente sigue siendo únicamente una prueba determinista del arnés; no es evidencia del rendimiento de un modelo. La siguiente campaña debe sustituir el smoke por un adaptador real y conservar `execution_id`, versión del modelo, revisión del modelo, runtime, cuantización, hardware y trazas.
