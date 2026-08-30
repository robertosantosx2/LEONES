# JALÓN 14 — V1 physical execution handoff

**Estado:** CONTRATO FIJADO · EJECUCIÓN FÍSICA PENDIENTE

## Objetivo

Convertir la V1 declarativa ya preparada en una operación física reproducible, sin crear otra arquitectura.

JALÓN 14 no inventa un benchmark nuevo. Utiliza la cadena canónica ya existente:

```text
selección / decisión
        ↓
runtime-selection.v1
        ↓
run_a01_selected.py
        ↓
A01
        ↓
a01_runtime_benchmark.py
        ↓
runtime-benchmark.v1
        ↓
evidencia
```

## Qué debe aportar la máquina física

La máquina real debe demostrar, para una ejecución concreta:

- runtime realmente instalado y utilizado;
- modelo y revisión/artefacto realmente utilizados;
- configuración de ejecución;
- tarea A01 ejecutada;
- resultado del agente;
- tiempo y rendimiento medidos por la ruta canónica;
- evidencia conservada con identidad y procedencia.

Una prueba de CI o un `preflight` no sustituye esta demostración.

## Regla de no duplicación

JALÓN 14 sólo orquesta componentes existentes. No contiene:

- un nuevo selector;
- un nuevo sistema de scoring;
- un segundo sistema de scoring;
- un benchmark alternativo;
- una segunda medición de tok/s;
- una traducción de estimaciones externas a `measured`.

Estas prohibiciones son deliberadas: LEONES debe tener una única cadena canónica de decisión, ejecución, medición y evidencia. Este jalón no crea una vía paralela para obtener, transformar o volver a puntuar resultados.

## Criterio de cierre

El jalón queda cerrado cuando una ejecución física real atraviesa la ruta canónica y produce evidencia válida que pueda ser auditada y reproducida. Hasta entonces, el estado correcto es **pendiente de ejecución física**.

## Uso previsto

La preparación de la máquina se hace una sola vez. La ejecución final debe ser una operación explícita, con los archivos de selección y comandos de runtime que ya exige `a01_runtime_benchmark.py`.

No se deben introducir cambios de código para ocultar una dependencia que falte en la máquina: una dependencia física ausente debe aparecer como condición de preflight o de ejecución.

## Para quien tiene pocos conocimientos de programación

Piensa en este jalón como la prueba de carretera. Los jalones anteriores han comprobado que las piezas encajan; aquí se arranca el vehículo real. El resultado sólo es válido si el vehículo realmente se mueve y conservamos el registro de lo ocurrido.
