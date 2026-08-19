# Contrato común de harnesses LEONES

Los harnesses de referencia son:

1. **DeepSeek Harness (DSH)**
2. **Buddy**
3. **Hermes**

El contrato permite comparar el comportamiento agéntico sin convertir la implementación de un harness en parte de la definición de la tarea.

## Interfaz conceptual

```text
Harness
├── start(config)
├── run(task)
├── stream_events()
├── stop()
└── export_trace()
```

## Evento normalizado

Cada adaptador debe poder representar, como mínimo:

```yaml
run_id: string
harness: dsh|buddy|hermes
model: string
hardware_profile: string
task_id: string
event:
  type: turn|step|model_request|model_response|tool_call|tool_result|error|stop
  timestamp: RFC3339
  sequence: integer
  payload: object
```

## Resultado

El resultado de benchmark mantiene separados:

- `outcome`: qué consiguió el agente;
- `trajectory`: cómo lo consiguió;
- `time_cost`: tiempo y tokens;
- `resource_cost`: CPU/RAM/GPU cuando estén disponibles;
- `security`: violaciones, inyecciones y acciones prohibidas;
- `artifacts`: ficheros, commits u otros productos verificables.

## Regla de equivalencia

Una comparación sólo es válida si la diferencia entre harnesses está explícitamente declarada. En particular, no se debe afirmar que DSH, Buddy y Hermes son equivalentes funcionalmente: son referencias de arquitectura y capacidades distintas.

La comparación debe mostrar qué capacidades estaban activas en cada ejecución.
