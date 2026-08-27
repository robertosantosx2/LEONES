# JALON 3 — Contrato operativo de medición real y evidencia V1.1

**Estado:** EN DESARROLLO / CONTRATO CERRABLE EN GITHUB
**Base de trabajo:** `947f61e4a65e9a34151999c8f94fd606295009f5` (cierre de JALON 2)
**Rama:** `jalon3-runtime-execution-contract-v1`
**Principio operativo:** todo lo que pueda diseñarse, codificarse, probarse y auditarse se hace en GitHub. Ubuntu/Debian solo interviene cuando una propiedad depende físicamente del equipo o de la ejecución real.

## 1. Propósito

JALON 3 convierte el protocolo de medición real en un contrato operativo común para que un runtime pueda producir evidencia LEONES reproducible, auditable y reutilizable.

La primera ejecución física objetivo sigue siendo `llama.cpp`, pero el contrato no queda acoplado a ese runtime.

**Importante:** implementar el harness y el contrato no cierra JALON 3. El cierre final requiere una primera ejecución real en Debian.

## 2. Qué se fija en GitHub

La rama debe contener, validar y documentar:

- schema machine-readable `runtime-benchmark-evidence.v1.1`;
- runner shell-free y determinista;
- captura separada de `stdout` y `stderr`;
- identidad inmutable de modelo y artefacto;
- identidad exacta del runtime;
- hardware y entorno;
- protocolo de prompt y sampling;
- warm-up y número de iteraciones;
- mediciones individuales;
- agregados reproducibles;
- hash SHA-256 de artefactos;
- reglas de validez y rechazo;
- tests automatizados;
- documentación de ejecución física.

El contrato canónico está en `schemas/runtime-benchmark-evidence.v1.1.json`.

## 3. Identidad de una ejecución

Una nueva combinación de cualquiera de estos elementos crea una nueva ejecución y requiere un nuevo `execution_id`:

`modelo + revisión + cuantización + artefacto + runtime + versión/revisión + backend + hardware + workload + protocolo`

No se permite corregir manualmente una evidencia ya generada. Si cambia una condición, se ejecuta de nuevo.

## 4. Modelo y artefacto

Se registran como mínimo:

- `model.id`;
- `model.name`;
- `model.revision`;
- `model.source` cuando exista;
- `model.artifact`;
- `model.artifact_sha256`;
- `model.artifact_size_bytes`;
- `model.quantization`;
- `model.context_length`.

El bloque `artifact` repite la identidad física usada por la ejecución (`path`, `sha256`, `size`) para facilitar ingestión y trazabilidad.

## 5. Protocolo

Se registran:

- `prompt_protocol_id`;
- `measurement_scope`;
- prompt/workload;
- SHA-256 del prompt cuando exista;
- tokens de entrada cuando puedan medirse de forma fiable;
- límite de salida;
- temperatura, `top_p` y seed cuando proceda;
- contexto;
- warm-up;
- número de iteraciones.

### Alcance de latencia

Para un proceso local como `llama-cli`, `first_output_ms`/`ttft_ms` significa **latencia hasta la primera salida observada desde el proceso local**. Puede incluir arranque y carga del modelo.

No se debe presentar como TTFT de una API remota ni mezclar con series de Artificial Analysis sin declarar la diferencia metodológica.

## 6. Métricas por iteración

Cada medición conserva, cuando sea observable:

- `first_output_ms` / `ttft_ms`;
- `generation_time_ms`;
- `output_tokens`;
- `tokens_per_second`;
- `total_time_ms`;
- `peak_memory_mb`;
- `peak_vram_mb`;
- `power_w`;
- `exit_code`;
- `stdout` completo;
- `stderr` completo.

La ausencia de telemetría opcional se representa como `null`. Nunca se inventa.

## 7. Agregación

Los valores observados se agregan por métrica con:

- media;
- mediana;
- mínimo;
- máximo;
- desviación estándar cuando hay más de una observación.

Las mediciones individuales permanecen siempre en el artefacto. Una media sin sus muestras no constituye evidencia suficiente.

## 8. Runtime y hardware

El runtime registra:

- nombre;
- versión exacta;
- revisión cuando exista;
- backend;
- binario;
- SHA-256 del binario cuando sea accesible;
- `argv` exacto como array, sin shell.

El hardware registra:

- host;
- sistema operativo;
- kernel;
- arquitectura;
- CPU;
- hilos y núcleos cuando puedan detectarse;
- RAM total;
- GPU/VRAM cuando exista;
- driver/almacenamiento cuando estén disponibles.

## 9. Seguridad de ejecución

El runner recibe el comando como array JSON y utiliza `subprocess.Popen` sin `shell=True`.

Por tanto:

- no se interpreta el comando como una cadena de shell;
- el `argv` queda preservado;
- el contrato puede reutilizarse entre runtimes;
- los planes no autorizados deben rechazarse antes de la ejecución en el runtime gate.

## 10. Regla de validez

Una evidencia no se publica como benchmark válido si:

- falta identidad obligatoria;
- falta el artefacto o su hash cuando se exige;
- no existe al menos una iteración;
- alguna iteración termina con error;
- faltan `stdout`/`stderr` del proceso;
- se han sustituido mediciones por una cifra manual;
- se han mezclado condiciones de ejecuciones distintas.

## 11. Relación con JALON 2

JALON 2 aportó la evidencia física de `llama.cpp` y el puente parser hacia V1.1.

JALON 3 convierte ese aprendizaje en un contrato común y reutilizable. No se modifica retroactivamente la evidencia histórica de JALON 2.

## 12. Qué NO depende de Ubuntu/Debian

Puede desarrollarse y verificarse en GitHub:

- schemas;
- modelos de datos;
- validadores;
- parser/normalización;
- runner;
- tests unitarios;
- tests de contrato;
- documentación;
- reglas de provenance;
- integración con runtime-selection;
- adapters de runtimes;
- CI.

## 13. Qué SÍ requiere ejecución física

Solo se reserva para Debian/Ubuntu u otro host apropiado aquello que no puede demostrarse desde GitHub:

1. disponibilidad real del runtime;
2. versión/build realmente instalado;
3. hardware real;
4. artefacto de modelo realmente accesible;
5. comportamiento real del runtime;
6. TTFT/first-output observado;
7. throughput real;
8. memoria/VRAM/potencia realmente observadas;
9. stdout/stderr de la ejecución;
10. hash del artefacto físico usado.

Por tanto, Ubuntu/Debian debe ser el **último paso**, no el lugar donde se diseña el protocolo.

## 14. Flujo final

```text
GitHub
  ↓
contrato V1.1
  ↓
schema + runner + tests + CI
  ↓
runtime-selection.v1
  ↓
execution plan autorizado
  ↓
──────────────────────────────
ÚNICA INTERVENCIÓN FÍSICA
Debian/Ubuntu
  ↓
runtime real
  ↓
warm-up
  ↓
N iteraciones
  ↓
captura de evidencia
──────────────────────────────
  ↓
validación
  ↓
evidence LEONES
  ↓
ingesta/recomendación
```

## 15. Criterio de cierre

JALON 3 tiene dos puertas:

### Puerta A — cierre de ingeniería en GitHub

Debe existir:

- contrato V1.1 estable;
- schema validado;
- runner probado;
- tests verdes;
- documentación coherente;
- integración preparada para `llama.cpp`;
- CI verde;
- rama/PR trazable desde JALON 2.

### Puerta B — cierre empírico

Requiere en Debian:

- runtime real;
- modelo/artefacto identificado;
- ejecución real;
- todas las condiciones registradas;
- evidencia V1.1 válida;
- stdout/stderr conservados;
- métricas individuales y agregadas;
- hashes y timestamps;
- reutilización por la capa de evidencia LEONES.

**Hasta cumplir la Puerta B, JALON 3 no se declara cerrado.**

## 16. Referencia metodológica

Artificial Analysis se utiliza como referencia conceptual para separar condiciones de workload, TTFT/first-output, velocidad de salida y tiempo end-to-end, pero LEONES mantiene explícitamente separadas las mediciones locales y las mediciones de API.

## 17. Frase de recuperación

> **JALON 3 = contrato V1.1 cerrado en GitHub + primera medición física reproducible en Debian.**
