# RC2-F — Benchmark Consent and Execution Contract

**Estado:** 🟢 Contrato fijado

## Objetivo

Permitir que el beta tester decida explícitamente si quiere ejecutar un benchmark real después de instalar y verificar el stack elegido.

## Flujo

```text
READY_FOR_BENCHMARK
        ↓
 explicación del benchmark
        ↓
 consentimiento explícito
     ┌──┴──┐
    NO     SÍ
    ↓       ↓
   FIN    execution plan
             ↓
          runtime
             ↓
        task benchmark
             ↓
          grader
             ↓
        measurement
             ↓
          evidence
```

## Antes de preguntar

LEONES debe explicar:

- qué tarea o conjunto de tareas se ejecutará;
- qué métrica se medirá;
- diferencia entre estimación y medición real;
- duración aproximada cuando pueda conocerse;
- qué modelo, cuantización, runtime y configuración se usarán;
- qué archivos de evidencia se conservarán;
- qué información del hardware aparecerá en el resultado;
- si habrá descargas, red o consumo relevante de recursos;
- que cancelar o responder `no` no invalida la instalación.

## Respuestas

- `benchmark_declined`: el usuario no quiere medir; no se ejecuta el runtime.
- `benchmark_authorized`: el usuario acepta la ejecución definida por el plan.
- `benchmark_blocked`: no puede ejecutarse por un requisito no satisfecho.
- `benchmark_completed`: ejecución terminada y evidencia conservada.
- `benchmark_failed`: ejecución intentada pero sin resultado válido.

## Reglas

1. No ejecutar benchmark por defecto.
2. No interpretar una aceptación genérica de instalación como autorización de benchmark.
3. El benchmark solo puede ejecutarse sobre un plan de ejecución autorizado.
4. La medición real debe conservar execution_id, timestamps, modelo, runtime, configuración y evidencia.
5. Una ejecución fallida no debe publicarse como medición válida.
6. Las estimaciones de LLMFit, ODS, Magnitude u otras fuentes permanecen diferenciadas de las mediciones LEONES.
7. El resultado debe ser reproducible en la medida permitida por el entorno local.

## Alcance RC2

RC2-F cierra la decisión humana. La ejecución física y la validación de resultados reutilizan el pipeline de RC1 en lugar de crear un segundo sistema de benchmark.
