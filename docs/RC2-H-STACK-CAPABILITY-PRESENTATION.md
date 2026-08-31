# RC2-H — ODS / Magnitude capability presentation

**Estado:** 🟢 Contrato fijado

Antes de elegir stack, LEONES debe presentar una comparación funcional basada en las capacidades y límites declarados por los contratos/adaptadores disponibles. No se presenta ODS y Magnitude como etiquetas equivalentes.

## ODS

Presentación mínima:
- stack local de inferencia;
- preparación de un plan de ejecución para el modelo seleccionado;
- separación entre selección, preparación y ejecución;
- integración con el contrato de runtime local;
- posibilidad de usar el pipeline común de medición/evidencia cuando el runtime esté soportado.

La implementación actual del adaptador ODS es deliberadamente de preparación y validación: no instala software ni arranca servicios por sí misma. fileciteturn78file0L1-L2

## Magnitude

Presentación mínima:
- integración orientada a agente/asistente;
- preparación de metadatos de ejecución;
- separación entre preparación y ejecución;
- reutilización del runner y de los contratos comunes de benchmark/evidencia.

La implementación actual de Magnitude prepara metadatos y deja la ejecución de agente y la medición a los componentes existentes. fileciteturn79file0L1-L2

## Regla de honestidad

La interfaz solo puede mostrar funcionalidades que estén respaldadas por el contrato o por evidencia versionada. Si una capacidad todavía no está implementada en el adaptador instalado, debe aparecer como **no disponible**, **pendiente** o **experimental**, nunca como capacidad garantizada.

## Decisión

La pantalla debe permitir:

```text
[1] Elegir ODS
[2] Elegir Magnitude
[3] Volver a candidatos
```

La selección se persiste antes de preparar la instalación. Elegir un stack no implica consentir su instalación ni autorizar un benchmark.
