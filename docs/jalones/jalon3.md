# JALON3 — Protocolo de medición real y evidencia V1.1

**Estado:** EN DESARROLLO — contrato congelado, ejecución física pendiente  
**Base:** `jalon2-evidence-bridge` (`947f61e4a65e9a34151999c8f94fd606295009f5`)  
**Rama de trabajo:** `jalon3-runtime-execution-contract-v2`

## 1. Objetivo

Convertir la medición física de un runtime en una evidencia LEONES reproducible, auditable y machine-readable. La primera ejecución objetivo es `llama.cpp`.

**JALON3 no declara una cifra real hasta que exista ejecución física.** Todo lo que se hace en GitHub es contrato, harness, validación y preparación.

## 2. Contrato congelado

El artefacto canónico es `schemas/runtime-benchmark-evidence.v1.1.json`.

Cada evidencia contiene obligatoriamente:

- identidad: `schema`, `execution_id`, timestamps;
- modelo: id, nombre, revisión, fuente, artefacto, cuantización y contexto;
- protocolo: identificador, hash del prompt cuando exista, tokens de entrada, límite de salida, sampling, seed, contexto, warm-up e iteraciones;
- runtime: nombre, versión, revisión, backend, binario, SHA-256 del binario y `argv` exacto;
- hardware: host, OS, kernel, arquitectura, CPU, hilos/núcleos, RAM, GPU y VRAM;
- mediciones individuales: first-output latency/TTFT local, generación, tokens producidos cuando estén explícitamente disponibles, tokens/s, tiempo total, memoria, VRAM, potencia, exit code, stdout y stderr;
- agregados: media, mediana, mínimo, máximo y desviación estándar cuando proceda;
- proceso completo y hash/tamaño del artefacto de modelo.

Los campos opcionales físicamente no observables se representan como `null`; **no se inventan valores**.

## 3. Regla de TTFT

En runtime local, `ttft_ms`/`first_output_ms` significa **latencia hasta la primera salida observada por el harness**. No se presenta como equivalente al TTFT de una API alojada.

## 4. Reproducibilidad

Una combinación diferente de:

`modelo + revisión + cuantización + runtime + versión/revisión + hardware + workload + protocolo`

es una ejecución distinta y recibe un nuevo `execution_id`.

El prompt se identifica además mediante `prompt_sha256` cuando se proporciona.

## 5. Harness

`scripts/runtime_benchmark_evidence.py`:

1. acepta únicamente un `argv` JSON, sin shell;
2. ejecuta warm-up separado de las mediciones;
3. conserva stdout/stderr por iteración;
4. mide first-output latency y tiempo total;
5. extrae tokens/s únicamente cuando el runtime lo declara explícitamente;
6. no estima `output_tokens` a partir de tokens/s;
7. identifica binario y SHA-256 cuando el ejecutable es un archivo local;
8. captura hardware disponible;
9. genera `runtime-benchmark-evidence.v1.1`;
10. devuelve código no cero si alguna medición falla.

## 6. Validación automática

`tests/test_runtime_benchmark_evidence_v1_1.py` fija las invariantes del contrato:

- captura simultánea de stdout/stderr;
- extracción de tokens/s;
- determinismo de agregados;
- SHA-256;
- estructura estricta del schema;
- campos obligatorios de ejecución, modelo, protocolo, runtime, hardware, mediciones, proceso y artefacto.

La ejecución física todavía queda fuera de CI: requiere hardware/runtime/modelo reales.

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

- el runtime es el que declara el registro;
- el comando ejecutado coincide con el `argv` conservado;
- el modelo/artefacto está identificado y hasheado;
- el protocolo queda congelado durante la serie;
- warm-up y mediciones están separados;
- existen mediciones individuales;
- stdout/stderr se conservan íntegros;
- el exit code de las mediciones es verificable;
- el JSON valida contra el schema;
- el hardware y versión del runtime quedan registrados;
- la evidencia no se modifica después de la ejecución.

## 9. Qué queda para Ubuntu/Debian

Solo lo que no puede demostrarse de forma honesta desde GitHub:

1. hardware físico;
2. runtime/binario realmente instalado;
3. modelo GGUF realmente disponible;
4. ejecución real;
5. métricas reales;
6. consumo/VRAM/potencia si el host permite medirlos;
7. stdout/stderr reales;
8. validación final de la evidencia producida.

**No se utilizará Ubuntu/Debian para seguir diseñando el contrato.** Cuando llegue ese punto será ejecutar → medir → validar → conservar.

## 10. Criterio de cierre de JALON3

JALON3 se cerrará cuando exista al menos una ejecución real de `llama.cpp` en el host objetivo que cumpla todos los criterios de validez física y cuya evidencia `runtime-benchmark-evidence.v1.1` sea reutilizable por el pipeline de evidencia/recomendación.

Hasta entonces, el estado correcto es **contrato congelado / ejecución pendiente**.

## 11. Referencia metodológica

Artificial Analysis se utiliza como referencia metodológica para separar condiciones de prueba, latencia inicial, velocidad de salida, rendimiento end-to-end y reproducibilidad. LEONES conserva explícitamente la distinción entre medición local y benchmark de API.

## 12. Frase de recuperación

> **JALON3 = contrato congelado; primera medición real reproducible → evidencia LEONES V1.1.**
