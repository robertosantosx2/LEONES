# JALON3 — Protocolo de medición real y evidencia V1.1

**Estado:** CONTRATO FIJADO / PRUEBA FÍSICA PENDIENTE  
**Base de trabajo:** `jalon3-runtime-execution-contract-v3`  
**Objetivo físico:** primera ejecución reproducible de `llama.cpp` en Debian

## 1. Objetivo

Convertir la medición física de un runtime en una evidencia LEONES reproducible, auditable y machine-readable.

**JALON3 no declara una cifra real hasta que exista ejecución física.** GitHub fija contrato, harness, validación y protocolo; Debian aporta la ejecución y las mediciones reales.

## 2. Contrato canónico

El artefacto canónico es `schemas/runtime-benchmark-evidence.v1.1.json`.

Cada evidencia registra, como mínimo:

- identidad y timestamps;
- modelo, revisión, artefacto y cuantización;
- protocolo, prompt identificado y parámetros;
- runtime, versión, binario, SHA-256 y `argv` exacto;
- hardware disponible;
- mediciones individuales;
- agregados estadísticos;
- stdout/stderr;
- proceso y código de salida;
- artefacto de modelo, tamaño y SHA-256.

Los valores físicamente no observables son `null`. **No se estiman ni se inventan.**

## 3. Semántica de las mediciones

### First output / TTFT local

`first_output_ms` mide el tiempo hasta la primera salida no vacía observada en **stdout**.

`ttft_ms` conserva esa observación como métrica local. No debe presentarse como TTFT de una API remota salvo que el protocolo demuestre equivalencia.

La referencia metodológica de Artificial Analysis se utiliza para mantener separadas latencia inicial, velocidad de salida y tiempo end-to-end.

### Tokens y velocidad

`tokens_per_second` solo se registra cuando aparece una señal explícita del runtime.

`output_tokens` no se deduce de tokens/s ni de tiempo transcurrido. Para la primera ejecución con `llama.cpp`, el harness reconoce el contador explícito de tokens de la línea `eval time ... / N runs`.

### Memoria, VRAM y potencia

Solo se registran cuando existe una fuente de observación disponible. La memoria del proceso se trata como pico observado por el lifetime de los procesos hijos del harness, no como una muestra instantánea por iteración.

## 4. Reproducibilidad

Una combinación distinta de:

`modelo + revisión + cuantización + runtime + versión/revisión + hardware + workload + protocolo`

es una ejecución distinta y recibe un nuevo `execution_id`.

El prompt se identifica mediante `prompt_sha256` cuando se proporciona. Los timestamps conservan precisión de milisegundos.

## 5. Harness

`scripts/runtime_benchmark_evidence.py`:

1. acepta únicamente un `argv` JSON, sin shell;
2. ejecuta warm-up separado;
3. captura stdout y stderr por separado;
4. mide first-output únicamente desde stdout;
5. extrae métricas solo desde señales explícitas;
6. no inventa `output_tokens`;
7. identifica el binario y su SHA-256 cuando es un archivo local;
8. captura hardware disponible;
9. aplica timeout duro y termina el grupo de procesos;
10. genera `runtime-benchmark-evidence.v1.1`;
11. devuelve código no cero si falla alguna medición.

## 6. Validación automática

`tests/test_runtime_benchmark_evidence_v1_1.py` cubre:

- stdout/stderr separados;
- stderr de arranque sin contaminar first-output;
- extracción de tokens/s;
- tokens producidos solo con evidencia explícita;
- timeout y terminación del grupo de procesos;
- determinismo de agregados;
- SHA-256;
- timestamps con precisión de milisegundos;
- estructura estricta del schema;
- representación `null` de métricas no observables.

CI valida además el JSON Schema Draft 2020-12 y ejecuta la suite contractual.

La ejecución física queda deliberadamente fuera de CI.

## 7. Flujo canónico

```text
modelo candidato
    ↓
runtime-selection.v1
    ↓
runtime gate
    ↓
execution plan autorizado
    ↓
adapter llama.cpp
    ↓
harness runtime_benchmark_evidence.py
    ↓
warm-up
    ↓
N mediciones
    ↓
stdout/stderr + recursos
    ↓
normalización
    ↓
runtime-benchmark-evidence.v1.1
    ↓
schema validation
    ↓
SHA-256 + conservación
    ↓
evidence LEONES
```

## 8. Criterios de validez física

Una ejecución real solo será válida si:

- el runtime coincide con el registro;
- el `argv` conservado coincide con el comando ejecutado;
- el modelo/artefacto está identificado y hasheado;
- el protocolo permanece constante durante la serie;
- warm-up y mediciones están separados;
- existen mediciones individuales;
- stdout/stderr se conservan;
- el exit code es verificable;
- el JSON valida contra el schema;
- hardware y versión exacta del runtime quedan registrados;
- la evidencia no se modifica después de ejecutarse.

## 9. Qué queda para Debian

Solo trabajo físico, no rediseño:

1. actualizar `main`;
2. ejecutar la suite de tests;
3. verificar árbol limpio y `git diff --check`;
4. identificar hardware y runtime;
5. comprobar `llama-cli` y versión exacta;
6. seleccionar un GGUF concreto;
7. registrar revisión y SHA-256 del modelo;
8. ejecutar warm-up;
9. ejecutar las iteraciones reales;
10. generar la evidencia V1.1;
11. validar el JSON contra el schema;
12. revisar stdout/stderr y métricas;
13. conservar evidencia y hashes;
14. incorporar la evidencia al pipeline LEONES.

**La fase de diseño termina aquí. En Debian: ejecutar → medir → validar → conservar.**

## 10. Criterio de cierre

JALON3 quedará completamente cerrado cuando exista al menos una ejecución real de `llama.cpp` en Debian que cumpla todos los criterios de validez física y cuya evidencia V1.1 sea reutilizable por el pipeline de evidencia/recomendación.

Hasta entonces: **contrato fijado / prueba física pendiente**.

## 11. Referencia metodológica

Artificial Analysis — metodología de benchmarking de rendimiento: `https://artificialanalysis.ai/methodology/performance-benchmarking`

LEONES adopta sus principios de condiciones explícitas, workload reproducible, repetición y separación entre latencia inicial, velocidad de salida y rendimiento end-to-end, adaptándolos a ejecución local.

## 12. Frase de recuperación

> **JALON3 = contrato fijado; GitHub limpio; Debian solo para ejecutar → medir → validar → conservar.**
