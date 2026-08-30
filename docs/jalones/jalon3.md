# JALON3 — Protocolo de medición real y evidencia V1.1

**Estado:** FIJADO
**Fecha:** 2026-08-27
**Base:** `main`
**Commit de implementación asociado:** `21d23496cb6ff727002bbdeb35f804c7b850722b`
**PR asociado:** #63 — runtime benchmark evidence v1.1 and llama.cpp protocol

## 1. Propósito

JALON3 fija el punto de continuación para la primera prueba real de un runtime en **Ubuntu**. La prueba no debe producir solamente una cifra de rendimiento: debe producir una evidencia LEONES estructurada, reproducible, auditable y reutilizable.

La primera ejecución objetivo es `llama.cpp`.

## 2. Referencia metodológica

La metodología de Artificial Analysis se toma como referencia conceptual, no como copia del protocolo. Su metodología actual mide el rendimiento end-to-end experimentado por el usuario/sistema y separa TTFT, velocidad de salida y tiempo end-to-end. Para sus benchmarks de LLM usa workloads explícitos, prompts variables, mediciones repetidas y representación estadística por mediana/P50. También distingue los tokens usados para medir rendimiento de los tokens nativos del modelo.

Para LEONES se adopta especialmente:

- condiciones de prueba explícitas;
- workload/prompt identificado;
- separación de TTFT y velocidad posterior al primer token;
- medición end-to-end;
- repetición de mediciones;
- conservación de datos y condiciones;
- identificación estable del modelo/runtime;
- resultados estructurados y machine-readable;
- distinción entre medición local y medición de API;
- prohibición de convertir estimaciones de terceros en mediciones físicas.

**Importante:** Artificial Analysis usa actualmente workloads de 1k/10k/100k tokens y su benchmark web por defecto usa 10k de entrada. LEONES no copiará esos tamaños automáticamente para una ejecución local: el workload local queda fijado mediante `prompt_protocol_id` y forma parte de la identidad experimental.

## 3. Contrato de medición

Cada ejecución debe registrar:

### Modelo

- `model_id`
- `model_name`
- `model_revision`
- `model_source`
- `model_artifact`
- `quantization`
- parámetros
- contexto

### Protocolo

- `prompt_protocol_id`
- prompt/workload
- tokens de entrada
- límite de salida
- parámetros de sampling
- seed cuando proceda
- warm-up
- número de iteraciones
- contexto

### Métricas

Por iteración:

- TTFT / first-output latency, claramente etiquetado para ejecución local;
- output tokens/s;
- tiempo de generación;
- tiempo total;
- tokens producidos.

Cuando sea posible:

- memoria RAM máxima;
- VRAM máxima;
- consumo/potencia;
- energía.

Agregados:

- media;
- mediana;
- mínimo;
- máximo;
- desviación estándar.

### Entorno

- CPU;
- núcleos/hilos;
- RAM;
- GPU;
- VRAM;
- almacenamiento;
- sistema operativo;
- kernel;
- arquitectura;
- driver cuando proceda.

### Runtime

- nombre;
- versión exacta;
- revisión/commit cuando sea posible;
- backend;
- build/configuración;
- dependencias relevantes;
- comando ejecutado.

### Ejecución

- `execution_id` único;
- timestamp de inicio;
- timestamp de finalización;
- duración;
- exit code;
- `stdout` completo;
- `stderr` completo.

### Artefactos

- ruta/identificador;
- tamaño;
- SHA-256;
- revisión del artefacto cuando exista.

## 4. Regla fundamental de TTFT

En una ejecución local con `llama-cli`, LEONES no debe presentar automáticamente la primera salida como equivalente al TTFT de una API remota.

Se conservará el concepto como **first-output latency / TTFT local**, indicando su ámbito experimental.

Las comparaciones con datos de Artificial Analysis deben respetar esta diferencia metodológica.

## 5. Principio de reproducibilidad

Una combinación distinta de cualquiera de estos elementos constituye una nueva ejecución:

`modelo + revisión + cuantización + runtime + versión + hardware + workload + protocolo`

Por tanto debe recibir un nuevo `execution_id`.

## 6. Flujo de ejecución

```text
LLM selector
    ↓
runtime-selection.v1
    ↓
runtime gate
    ↓
execution plan autorizado
    ↓
llama.cpp adapter
    ↓
warm-up
    ↓
N mediciones
    ↓
captura de recursos + stdout/stderr
    ↓
normalización
    ↓
runtime-benchmark-evidence.v1.1
    ↓
validación
    ↓
artifact de evidencia LEONES
```

## 7. Runner canónico de auditoría

El punto operativo de JALON3 queda fijado en:

`scripts/run_jalon3_audit.sh`

El runner es el único mecanismo canónico para auditar y publicar el estado del jalón desde Ubuntu. Su contrato operativo es:

1. exigir una rama Git válida y rechazar `detached HEAD`;
2. impedir dos runners simultáneos mediante lock local;
3. rechazar cambios ajenos al runner antes de comenzar;
4. sincronizar con `origin/<branch>` antes de auditar;
5. ejecutar los gates de contrato, tests, `git diff --check`, evidencia física y reproducibilidad;
6. generar un transcript completo en `artifacts/jalon3-audit/`;
7. mantener una única copia compacta rastreada en `docs/audits/jalon3/latest.txt`;
8. no declarar cierre operacional si falla cualquier gate;
9. publicar también los resultados `FAIL`, para que el fallo sea auditable;
10. si el remoto avanza durante la auditoría, intentar únicamente `fetch + pull --rebase --autostash + push`;
11. no utilizar nunca `push --force`;
12. devolver un código de salida no cero cuando el jalón no esté operacionalmente cerrado.

La carrera de publicación remota se considera un problema de sincronización, no una razón para rebajar los gates de evidencia.

## 8. Implementación ya integrada

JALON3 se apoya en la implementación fusionada en `main` mediante PR #63:

- `schemas/runtime-benchmark-evidence.v1.1.json`
- `scripts/runtime_benchmark_evidence.py`
- `tests/test_runtime_benchmark_evidence.py`
- `docs/runtime-benchmark-evidence-v1.1.md`

El adaptador de `llama.cpp` ya está conectado al runtime-selection gate y construye comandos sin shell, rechazando planes no autorizados o de otro runtime.

## 9. Qué NO se debe hacer al continuar

- No copiar manualmente una cifra del terminal.
- No convertir una estimación de LLMFit/Magnitude en una medición real.
- No mezclar una medición de API con una medición local.
- No eliminar stdout/stderr.
- No sustituir las iteraciones por una única media.
- No cambiar el prompt, cuantización o contexto sin crear una nueva ejecución.
- No declarar un benchmark válido si faltan los campos obligatorios del contrato.
- No usar `git push --force` para resolver una carrera del runner.

## 10. Punto exacto de continuación en Ubuntu

Cuando se retome JALON3 delante del equipo Ubuntu:

1. actualizar la rama de trabajo de forma no destructiva;
2. ejecutar el runner canónico;
3. comprobar tests y estado limpio;
4. identificar hardware y runtime instalados;
5. comprobar disponibilidad/versionado de `llama.cpp`;
6. seleccionar modelo y artefacto GGUF concretos;
7. obtener y registrar su revisión/hash;
8. ejecutar warm-up;
9. ejecutar las iteraciones reales;
10. generar `runtime-benchmark-evidence.v1.1`;
11. validar el JSON contra el schema;
12. revisar stdout/stderr y métricas;
13. conservar el artefacto y SHA-256;
14. incorporar la evidencia al flujo LEONES;
15. documentar el resultado sin modificar retroactivamente las condiciones.

## 11. Criterio de cierre de JALON3

JALON3 queda completamente cerrado cuando exista al menos una ejecución real de `llama.cpp` en Ubuntu que:

- haya pasado por `runtime-selection.v1`/runtime gate;
- utilice un artefacto de modelo identificado;
- ejecute el runtime real;
- produzca evidencia `runtime-benchmark-evidence.v1.1` válida;
- conserve las mediciones individuales;
- conserve stdout/stderr;
- tenga `execution_id`, timestamps y hash;
- registre hardware y versión exacta del runtime;
- y pueda ser reutilizada por el sistema de evidencia/recomendación de LEONES.

**JALON3 no se considera cerrado por haber implementado el harness ni por tener tests verdes. El cierre operacional requiere la primera medición real en Ubuntu.**

## 12. Referencias externas

Artificial Analysis — Benchmarking Methodology: https://artificialanalysis.ai/methodology

Artificial Analysis — Language Model API Performance Benchmarking: https://artificialanalysis.ai/methodology/performance-benchmarking

Artificial Analysis — Data API: https://artificialanalysis.ai/data-api

## 13. Frase de recuperación

> **JALON3 = primera medición real reproducible de runtime → evidencia LEONES V1.1.**

Al continuar, no hay que rediseñar el protocolo: hay que ejecutar la prueba real y cerrar la evidencia.
