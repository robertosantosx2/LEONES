# LEONES — Arquitectura canónica y reglas de limpieza

> Contrato de mantenimiento: una sola ruta de ejecución, evidencia separada de estimación y medición física reservada al runtime real.

## 1. Ruta canónica

```text
usuario / tarea
    ↓
selección declarativa
    ↓
RuntimeSelectionPlan
    ↓
adapter autorizado
    ↓
ExecutionSpec
    ↓
runner agentic existente
    ↓
runtime físico
    ↓
medición real
    ↓
evidence bridge
    ↓
evidencia canónica
    ↓
resultado de tarea
    ↓
recomendación canónica
```

## 2. Regla de no duplicación

LEONES **no crea un segundo runner** para medición, benchmarking o recomendación. El runner existente en `benchmarks/agentic/runner.py` es la frontera de ejecución. La selección se materializa mediante el adapter y produce un `ExecutionSpec`; la ejecución posterior recibe únicamente ese contrato.

La función `execute_selected_runtime()` debe seguir siendo el puente entre selección y ejecución. No debe contener lógica específica de un runtime concreto ni convertirse en un benchmark paralelo.

## 3. Separación de responsabilidades

| Capa | Responsabilidad | No debe hacer |
|---|---|---|
| Selección | Declarar runtime/modelo compatible | Ejecutar comandos |
| Adapter | Traducir selección a `ExecutionSpec` | Medir por su cuenta |
| Runner | Orquestar una ejecución y su trace | Inventar evidencia física |
| Runtime | Ejecutar realmente el modelo | Alterar la selección |
| Medición | Capturar métricas de ejecución real | Convertir estimaciones en mediciones |
| Evidence bridge | Normalizar evidencia válida | Fabricar runs |
| Recomendación | Consumir evidencia y decisión | Ejecutar otro benchmark oculto |

## 4. Evidencia

- `estimated`: estimación; nunca equivale a ejecución local.
- `reported`: dato reportado por una fuente externa.
- `measured`: ejecución real con identificador de ejecución y timestamp.
- `verified`: requiere verificador independiente; el runner no lo promociona automáticamente.

Una medición real debe conservar la identidad del modelo, revisión, cuantización, runtime, hardware, protocolo y artefactos necesarios para reproducibilidad.

## 5. JALÓN 3

JALÓN 3 queda definido como cierre del puente **selección → runner**, no como creación de otra infraestructura de ejecución. El test canónico debe demostrar como mínimo:

1. una selección válida se materializa una sola vez;
2. el adapter correcto es obligatorio;
3. el executor recibe el `ExecutionSpec`;
4. la traza conserva `selected → prepared → completed`;
5. una incompatibilidad de adapter se rechaza antes de ejecutar.

## 6. Trabajo pendiente que sí requiere Ubuntu

El repositorio puede preparar contratos, validadores, tests y documentación sin hardware físico. Ubuntu solo es imprescindible para:

```text
runtime real → ejecución → medición → artefactos → evidencia measured
```

No se debe introducir evidencia sintética para cerrar ese paso.

## 7. Criterio de limpieza

Antes de añadir una nueva abstracción hay que comprobar si el contrato ya existe. Si existe, se reutiliza. Si dos componentes expresan la misma responsabilidad, se conserva el contrato canónico y se elimina el duplicado solo después de comprobar referencias y CI.

La prioridad es **menos caminos, menos contratos y una única fuente de verdad**.
