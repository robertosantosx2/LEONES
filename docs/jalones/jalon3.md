# JALON3 — Protocolo de medición real y evidencia V1.1

**Estado:** EN DESARROLLO — contrato congelado, ejecución física pendiente  
**Base:** `jalon2-closed` (`73b741bc3a53f6a5ea9d5c08eec5c5da6c4ee384`), cuya genealogía contiene el cierre físico `947f61e4a65e9a34151999c8f94fd606295009f5`  
**Rama actual:** `jalon3-runtime-execution-contract-v3`

## 1. Objetivo

Convertir la medición física de un runtime en una evidencia LEONES reproducible, auditable y machine-readable. La primera ejecución objetivo es `llama.cpp`.

**JALON3 no declara una cifra real hasta que exista ejecución física.** Todo lo que se hace en GitHub es contrato, harness, validación y preparación.

## 2. Contrato congelado

El artefacto canónico es `schemas/runtime-benchmark-evidence.v1.1.json`. Cada evidencia contiene obligatoriamente identidad, modelo, protocolo, runtime, hardware, mediciones individuales, agregados, proceso y artefacto hasheado. Los campos físicamente no observables son `null`; **no se inventan valores**. fileciteturn18file0L1-L6

El runtime conserva el `argv` exacto y la identidad criptográfica del binario cuando el ejecutable es un archivo local. La evidencia queda separada de la capa de selección y de cualquier estimación previa.

## 3. Regla de latencia local

`first_output_ms` es la latencia hasta la primera salida no vacía observada en **stdout**. El harness no utiliza stderr para marcar el comienzo porque los runtimes suelen escribir allí logs de arranque y rendimiento.

`ttft_ms` puede conservar ese mismo valor como observación local, pero LEONES no lo presenta como TTFT de una API alojada salvo que se demuestre que stdout corresponde al primer token generado. Esta distinción sigue la definición de TTFT de Artificial Analysis: tiempo desde el envío hasta recibir el primer token; su benchmark de rendimiento separa además output speed y end-to-end response time. citeturn0search0turn0search1

## 4. Reproducibilidad

Una combinación diferente de:

`modelo + revisión + cuantización + runtime + versión/revisión + hardware + workload + protocolo`

es una ejecución distinta y recibe un nuevo `execution_id`.

El prompt se identifica mediante `prompt_sha256` cuando se proporciona. Los timestamps del harness conservan precisión de milisegundos para no colapsar ejecuciones cortas al mismo segundo.

## 5. Harness

`scripts/runtime_benchmark_evidence.py`:

1. acepta únicamente un `argv` JSON, sin shell;
2. ejecuta warm-up separado de las mediciones;
3. conserva stdout/stderr por iteración;
4. mide first-output latency únicamente desde stdout;
5. extrae tokens/s únicamente cuando aparece una señal explícita del runtime;
6. no estima `output_tokens` desde tokens/s ni desde tiempo transcurrido;
7. identifica binario y SHA-256 cuando el ejecutable es un archivo local;
8. captura hardware disponible;
9. genera `runtime-benchmark-evidence.v1.1`;
10. devuelve código no cero si alguna medición falla.

La memoria de proceso se conserva como observación de `ru_maxrss` del proceso hijo; por tanto, se trata como pico observado del lifetime del harness y no como muestra instantánea por iteración. GPU/VRAM/potencia solo se registran cuando el host ofrece una fuente de medición.

## 6. Validación automática

`tests/test_runtime_benchmark_evidence_v1_1.py` fija las invariantes del contrato:

- captura separada de stdout/stderr;
- stderr de arranque no contamina first-output latency;
- extracción de tokens/s;
- no invención de `output_tokens`;
- determinismo de agregados;
- SHA-256;
- precisión subsegundo de timestamps;
- estructura estricta del schema;
- representación `null` de métricas no observables.

La ejecución física queda fuera de CI: requiere hardware/runtime/modelo reales.

## 7. Gate físico Ubuntu — resultado

El gate físico se ha ejecutado sobre el host Ubuntu real con intervención mínima. El entorno verificó:

- `llama-cli` disponible y ejecutable;
- llama.cpp `0.3.0-dev`, build `10655`, commit `cb300598d`;
- SHA-256 del binario: `5c8abc6bd1604fabf743e5863e837fbcb2a01a4f8fdfbd66287a6ea213457aa8`;
- Intel Core i5-1035G1, 8 hilos;
- sin `nvidia-smi`/GPU NVIDIA;
- **ningún GGUF/GGML localizado en `$HOME`**;
- el test específico solicitado en Ubuntu falló porque `tests/test_runtime_benchmark_evidence_v1_1.py` aún no existía en la copia local anterior al desarrollo V3.

Conclusión: **no se ejecuta todavía el benchmark físico**. El único bloqueo físico restante es disponer de un artefacto de modelo real y ejecutar la suite contractual ya preparada. No se seguirá diseñando el contrato en Ubuntu.

## 8. Flujo canónico

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

## 9. Criterios de validez física

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

## 10. Qué queda para Ubuntu/Debian

Solo lo que no puede demostrarse de forma honesta desde GitHub:

1. disponer del modelo GGUF real;
2. ejecutar el `llama-cli` real con el `argv` congelado;
3. obtener las mediciones reales;
4. capturar recursos disponibles;
5. validar y conservar la evidencia producida.

**No se utilizará Ubuntu/Debian para seguir diseñando el contrato.** Cuando llegue ese punto será ejecutar → medir → validar → conservar.

## 11. Criterio de cierre de JALON3

JALON3 se cerrará cuando exista al menos una ejecución real de `llama.cpp` en el host objetivo que cumpla todos los criterios de validez física y cuya evidencia `runtime-benchmark-evidence.v1.1` sea reutilizable por el pipeline de evidencia/recomendación.

Hasta entonces, el estado correcto es **contrato congelado / ejecución pendiente**.

## 12. Referencia metodológica

Artificial Analysis se utiliza como referencia metodológica para separar condiciones de prueba, TTFT, output speed y rendimiento end-to-end. Su metodología de rendimiento usa cargas de trabajo explícitas, repeticiones y representación estadística de resultados; LEONES adapta esos principios al runtime local y conserva la distinción entre medición local y benchmark de API. citeturn0search1

## 13. Frase de recuperación

> **JALON3 = contrato congelado; GitHub cerrado; Ubuntu solo para ejecutar → medir → validar → conservar.**
