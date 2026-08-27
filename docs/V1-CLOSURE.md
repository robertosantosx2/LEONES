# LEONES V1 — Criterio de cierre

> **Build it. Measure it. Explain it. Preserve the evidence.**

## 1. Declaración

V1 no significa que todo LEONES esté terminado. Significa que las piezas que forman el **camino mínimo de conocimiento → selección → ejecución → medición → evidencia** tienen contratos explícitos, pruebas, regresión CI y una primera validación física reproducible.

El cierre es un **baseline reproducible**, no el final del proyecto.

## 2. Criterios alcanzados

### Selección

- El modelo seleccionado tiene identidad explícita.
- La cuantización forma parte de la identidad de ejecución.
- El runtime seleccionado y su versión se conservan.
- El plan pasa por `runtime-selection.v1`.
- El plan queda `execution_authorized` para ejecutar.

### Ejecución

- El ejecutor recibe un plan, no una decisión textual libre.
- Los comandos de runtime se proporcionan como argv confiable.
- A01 tiene un contrato explícito de herramientas.
- La secuencia mínima es `lookup_model → write_report`.

### Resultado

- La trayectoria registra el modelo, artefacto y grader.
- El artefacto `report.txt` existe y contiene la identidad del modelo.
- El grader A01 valida orden, objetivo, lookup y artefacto.
- El resultado se serializa como evidencia estructurada.

### Medición y procedencia

- `measured` y `verified` requieren ejecución identificable y timestamp.
- Una evidencia `measured`/`verified` exige `measurement_kind=real`.
- Una evidencia `synthetic` es rechazada explícitamente y **no puede promocionarse** a `measured` o `verified`.
- `measured_tps` se conserva únicamente cuando el runtime aporta los datos necesarios.
- Cuando el runtime no informa tokens evaluados, LEONES conserva `null` en lugar de fabricar una cifra.
- Las ejecuciones sucesivas conservan su identidad e historia; no se selecciona arbitrariamente la cifra mayor.

### CI y regresión

La regresión V1 está definida en `.github/workflows/v1-regression.yml` y ejecuta en GitHub Actions:

1. compilación de los caminos Python canónicos;
2. validación de todos los esquemas JSON;
3. suite completa `tests`;
4. prueba explícita de que una evidencia real es aceptada;
5. prueba explícita de que una evidencia sintética es rechazada.

La CI utiliza fixtures/runtime controlado para mantener la prueba determinista y portable. **La CI no convierte sus mediciones sintéticas en evidencia física.**

## 3. Runtime real — evidencia física de cierre

La validación física realizada en Debian utilizó:

- Ollama `0.33.1`;
- modelo `qwen2.5:0.5b-instruct-q4_K_M`;
- ejecución CPU-only;
- tarea A01;
- dos tool calls: `lookup_model → write_report`;
- cero errores de herramienta;
- resultado `success`;
- grader `passed`, score `1.0`;
- `measurement_status=reported_by_runtime`;
- **51.5798 tok/s**.

La ejecución canónica quedó identificada por:

```text
execution_id:     ba58d9dd-15ac-4a43-88d2-2aaf537efe5e
measured_at:      2026-08-27T06:02:24.821349+00:00
measurement_kind: real
evidence_type:    measured
```

El artefacto local validado fue:

```text
artifacts/h10-a01-runtime-selection-result.json
sha256: 6c99e6bd6c02c5d5d6062c731c4a30cbf380280791259fca93174db411c7d45d
```

El registro canónico preservado en el repositorio es `artifacts/h10-a01-runtime-selection-evidence.v1.json`.

## 4. Qué se fija como contrato

La arquitectura V1 establece estas fronteras:

```text
MODEL
  ≠ RUNTIME
  ≠ HARDWARE
  ≠ ESTIMATION
  ≠ MEASUREMENT
  ≠ GRADING
```

Una estimación no se convierte en medición. Una medición sintética no se convierte en medición real. Una cifra externa no se convierte en evidencia LEONES solo por aparecer en una fuente de conocimiento.

La regla mínima de promoción es:

```text
estimated ───────────────→ estimated
reported ────────────────→ reported
measured + real ─────────→ measured
verified + real ─────────→ verified
synthetic ───────────────→ REJECTED
```

No existe un camino implícito `synthetic → measured`.

## 5. Evidencia histórica y referencia canónica

Las mediciones son ejecuciones distintas y deben conservar su procedencia. Durante la integración se observaron varias ejecuciones A01; no deben combinarse ni presentarse como una única medición.

La referencia física canónica de este cierre V1 es la ejecución del 27 de agosto de 2026 con `51.5798 tok/s`. Las cifras anteriores permanecen históricas cuando sus artefactos y metadatos existen; **no se sustituyen silenciosamente por la cifra mayor**.

Esta medición tampoco debe tratarse como benchmark comparativo general. Para comparaciones entre modelos/runtimes habrá que fijar posteriormente una metodología con repeticiones, calentamiento, contexto, generación, versiones y condiciones de hardware controladas.

## 6. Camino E2E cerrado

```text
knowledge / candidate
        ↓
runtime-selection.v1
        ↓
execution_authorized
        ↓
A01 runtime adapter
        ↓
Ollama / CPU real
        ↓
lookup_model → write_report
        ↓
A01 grader
        ↓
measurement_kind=real
        ↓
evidence_type=measured
        ↓
artefacto canónico
```

Este camino queda protegido por tests de regresión y por el contrato de evidencia.

## 7. Reproducibilidad

En el entorno Debian con Ollama instalado:

```bash
cd ~/leones-work/LEONES

ollama list

rm -rf .leones/h10-a01-workspace
mkdir -p .leones/h10-a01-workspace

python3 scripts/run_a01_selected.py \
  --selection artifacts/real-a01-selection.json \
  --runtime-commands artifacts/real-a01-runtime-commands.json \
  --workspace .leones/h10-a01-workspace \
  --prompt 'Execute A01. Return only JSONL tool calls.' \
  --out artifacts/h10-a01-runtime-selection-result.json
```

Después debe validarse el artefacto con `scripts.validate_evidence` y comprobarse que contiene `measurement_kind=real`, `evidence_type=measured`, un `execution_id`, timestamp, resultado A01 satisfactorio y grader `passed`.

La evidencia generada **no debe copiarse ni editarse** para convertir una estimación o un fixture sintético en medición real.

## 8. Verificación de cierre V1

La última verificación física en Debian obtuvo:

```text
CANONICAL A01 REAL EVIDENCE: PASS
execution_id: ba58d9dd-15ac-4a43-88d2-2aaf537efe5e
measured_tps: 51.5798

177 passed

SCHEMAS: PASS (12)

REAL CPU evidence: ACCEPTED
SYNTHETIC evidence: REJECTED
```

La CI V1 añade la misma barrera como regresión permanente mediante `.github/workflows/v1-regression.yml`.

## 9. Higiene del repositorio

El estado generado durante una ejecución local queda fuera del árbol versionado mediante `.gitignore`, incluyendo:

- `.leones/`;
- `artifacts/` de ejecución;
- `__pycache__/`;
- `.pytest_cache/`;
- `.venv/`;
- clones temporales `upstream/`.

Los artefactos canónicos destinados a documentar evidencia se versionan explícitamente y deben conservar su hash/procedencia.

## 10. Lo que queda deliberadamente fuera de V1

V1 no declara cerrado:

- el benchmark físico de todos los modelos;
- la comparación exhaustiva de runtimes;
- la optimización de cada hardware;
- la cobertura completa de tareas agentivas;
- la automatización de toda la cadena de recomendación;
- la eliminación de todos los valores `unknown`;
- la equivalencia entre mediciones de terceros y mediciones LEONES;
- un ranking de rendimiento general basado en esta única ejecución.

Estas cuestiones pertenecen a las siguientes iteraciones.

## 11. Estado de cierre

**V1 queda técnicamente cerrada como baseline del camino E2E conocimiento → selección → ejecución → medición → evidencia**, con una validación física A01 CPU-only y una barrera CI que impide promocionar mediciones sintéticas a rendimiento real.

El cierre no afirma que el sistema esté terminado; afirma que el contrato mínimo queda **implementado, medido, explicado, preservado y protegido contra regresión**.

## 12. Regla de mantenimiento

Todo nuevo runtime, adaptador o benchmark que se incorpore después de V1 debe satisfacer el mismo contrato. Si necesita una excepción, esa excepción debe documentarse como decisión arquitectónica y acompañarse de una prueba.

> **Build it. Measure it. Explain it. Preserve the evidence.**

Construir sin medir produce una hipótesis. Medir sin explicar produce un número. Explicar sin conservar la evidencia produce una afirmación difícil de auditar. V1 exige las cuatro cosas juntas.
