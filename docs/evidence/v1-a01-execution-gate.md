# V1: contrato completo runtime-selection → A01 → grader → evidence

## Propósito

Este documento fija el contrato de integración que debe permanecer estable para V1. La prueba no consiste simplemente en que una función devuelva `success`: debe existir una cadena verificable desde la selección hasta la evidencia.

```text
selección
   ↓
runtime-selection.v1
   ↓
execution plan
   ↓
trusted runtime boundary
   ↓
A01 adapter
   ↓
tool trajectory
   ↓
artifact
   ↓
grader
   ↓
measurement/evidence
   ↓
router/benchmark evidence
```

## Capas

### 1. Selección

El selector determina `runtime_id`, `adapter_id`, `model_ref` y las capacidades. No debe introducir comandos arbitrarios ni convertir una medición en una recomendación.

### 2. Gate de ejecución

`runtime_gate` transforma una selección en planes autorizables. La autorización depende de que exista un runtime confiable y una representación de ejecución válida.

Un plan no autorizado debe permanecer bloqueado; la ausencia de un comando confiable no se resuelve inventando uno.

### 3. Adaptador A01

El adaptador ejecuta exclusivamente una lista `argv` confiable con `shell=False`. El prompt se añade como argumento, nunca como shell script.

El adaptador exige exactamente dos llamadas A01:

```text
lookup_model → write_report
```

El `model_id` de la primera llamada debe coincidir exactamente con el modelo seleccionado.

### 4. Artefacto

`write_report` genera `report.txt` dentro del workspace autorizado. La trayectoria no puede escapar del workspace mediante rutas arbitrarias.

### 5. Grader

El grader canónico es `benchmarks/agentic/a01_grader.py`, versión `1.1`. Comprueba:

- orden de herramientas;
- identidad del modelo solicitado;
- resultado de `lookup_model`;
- existencia del artefacto;
- presencia del nombre del modelo en el artefacto.

El grader es deliberadamente relativo al modelo seleccionado; no debe quedar fijado a una identidad de fixture como `demo-2`.

### 6. Medición

Cuando existe ejecución real, el adaptador conserva el tiempo de ejecución y la medición resultante. La medición se etiqueta como tal y no se convierte automáticamente en `verified`.

### 7. Evidencia

`build_result` separa `status` de `evidence_type`. Una ejecución puede ser `success` y aportar evidencia `measured`; eso no equivale a una verificación independiente.

## CI sin GPU

El gate V1 de GitHub no depende de una GPU, de Ollama instalado ni de un modelo descargado. Utiliza un runtime controlado/fixture para demostrar la arquitectura completa de forma determinista.

La existencia de una prueba real de Ollama es una segunda capa de evidencia: demuestra que el mismo contrato también ha sido atravesado por un runtime real en Debian.

Esta separación es intencionada:

```text
CI = regresión determinista de arquitectura
REAL = evidencia empírica de ejecución
```

No deben mezclarse.

## Gate V1 actual

El workflow `v1-complete-gate.yml` ejecuta:

1. validación de documentos JSON;
2. suite Python completa;
3. benchmark sintético controlado;
4. integración selector → A01;
5. comprobación de que el camino CI no depende de modelos reales.

El workflow específico de A01 debe compilar y ejecutar el camino canónico, incluyendo el grader que realmente consume el adaptador. No debe compilar un duplicado histórico del grader.

## Corrección aplicada al gate A01

Se eliminó del workflow la referencia al antiguo:

```text
benchmarks/agentic/graders/a01_grader.py
```

y se fijó como canónico:

```text
benchmarks/agentic/a01_grader.py
```

Además, el workflow A01 ahora cubre `benchmarks/agentic/**`, instala pytest y ejecuta directamente:

```bash
python -m pytest -q benchmarks/agentic/test_selection_to_a01.py
```

También se alinearon las acciones de checkout/setup-python con las versiones actuales utilizadas por el gate V1.

## Evidencia CI observada

En el commit `63d76f5ba8c71ad236f145823e77e9af31ff8451` se observó:

- **LEONES V1 Complete Gate: SUCCESS**;
- **V1 regression: SUCCESS**;
- el workflow específico `A01 runtime benchmark contract` terminó en `failure` sin jobs visibles.

Esto se considera una señal de higiene del CI, no un fallo del contrato A01 en Debian: el gate completo sí atravesó el camino controlado y la ejecución real de Ollama fue validada independientemente.

La corrección del workflow A01 se ha fijado en el commit posterior y debe quedar confirmada por su siguiente ejecución automática.

## Criterio de cierre V1

V1 no se marca como definitivamente cerrada hasta que todos estos elementos estén satisfechos:

- [x] contrato A01 explícito;
- [x] selector → adaptador;
- [x] grader canónico y parametrizado por selección;
- [x] evidencia separada de medición;
- [x] regresión completa local;
- [x] integración CI controlada;
- [x] ejecución real Ollama;
- [x] documentación de la evidencia real;
- [x] gate A01 específico sin referencias históricas al grader duplicado;
- [ ] ejecución CI específica A01 confirmada como `success` tras la corrección;
- [ ] prueba real global V1 final;
- [ ] cierre formal V1.

## Regla de preservación

La evidencia real no sustituye la regresión determinista y la regresión determinista no sustituye la evidencia real.

**CI demuestra que la arquitectura sigue siendo reproducible.**

**La prueba real demuestra que la arquitectura atraviesa un runtime real.**

**La evidencia conserva qué ocurrió, cuándo ocurrió y de dónde procede la medición.**
