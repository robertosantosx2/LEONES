# RC2-H — ODS / Magnitude capability presentation

**Estado:** 🟢 Contrato actualizado (feedback beta 2026-09-02)

Antes de elegir stack, LEONES debe presentar una comparación funcional basada en las capacidades y límites declarados por los contratos/adaptadores disponibles. No se presenta ODS y Magnitude como etiquetas equivalentes ni como nombres sin explicación.

## Presentación obligatoria en el menú de elección

El menú de elección **debe incluir una descripción corta legible** en cada opción, no solo el nombre del proyecto:

```text
ELIGE TU STACK
┌──────────────────────────────────────────────────────────┐
│  [1] ODS — stack local de inferencia                     │
│      (modelos, UI y servicios en tu máquina)             │
│  [2] Magnitude — agente/asistente local                  │
│      orientado a tareas con el modelo elegido            │
└──────────────────────────────────────────────────────────┘
```

El beta tester no debe tener que salir del wizard para saber qué es cada opción.

## ODS

Resumen orientativo:
- stack local de inferencia;
- modelos, interfaz y servicios en la máquina del usuario;
- preparación de un plan de ejecución para el modelo seleccionado;
- separación entre selección, preparación y ejecución;
- integración con el contrato de runtime local;
- posibilidad de usar el pipeline común de medición/evidencia cuando el runtime esté soportado.

La implementación actual del adaptador ODS es deliberadamente de preparación y validación: no instala software ni arranca servicios por sí misma.

## Magnitude

Resumen orientativo:
- integración orientada a agente/asistente local;
- uso del modelo elegido para tareas asistidas;
- preparación de metadatos de ejecución;
- separación entre preparación y ejecución;
- reutilización del runner y de los contratos comunes de benchmark/evidencia.

La implementación actual de Magnitude prepara metadatos y deja la ejecución de agente y la medición a los componentes existentes.

## Regla de honestidad

La interfaz solo puede mostrar funcionalidades que estén respaldadas por el contrato o por evidencia versionada. Si una capacidad todavía no está implementada en el adaptador instalado, debe aparecer como **no disponible**, **pendiente** o **experimental**, nunca como capacidad garantizada.

## Decisión

La pantalla debe permitir elegir entre las opciones descritas y, si procede, volver a candidatos. La selección se persiste antes de preparar la instalación. Elegir un stack no implica consentir su instalación ni autorizar un benchmark.
