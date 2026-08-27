# LEONES V1 — Criterio de cierre

## 1. Declaración

V1 no significa que todo LEONES esté terminado. Significa que las piezas que forman el **camino mínimo de conocimiento → selección → ejecución → medición → evidencia** tienen contratos explícitos, pruebas y una primera validación física.

El cierre debe entenderse como un **baseline reproducible**, no como el final del proyecto.

## 2. Criterios alcanzados

### Selección

- El modelo seleccionado tiene identidad explícita.
- La cuantización forma parte de la identidad de ejecución.
- El runtime seleccionado y su versión se conservan.
- El plan pasa por `runtime-selection.v1`.
- El plan debe quedar `execution_authorized` para ejecutar.

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

### Medición

- El runtime puede aportar `eval_count` y `eval_duration`.
- `measured_tps` se calcula únicamente cuando los datos necesarios están disponibles.
- Cuando el runtime no informa tokens evaluados, LEONES conserva `null` en lugar de fabricar una cifra.
- Las ejecuciones sucesivas no sobrescriben conceptualmente la historia.

### CI

La integración quedó respaldada por tres gates verdes:

- `Agentic A01 contract`;
- `LEONES Contract Tests`;
- `LEONES V1 Complete Gate`.

La CI utiliza el runtime fixture para mantener la prueba determinista y portable.

### Runtime real

La validación física utilizó:

- Ollama `0.33.1`;
- `qwen2.5:0.5b-instruct-q4_K_M`;
- endpoint local `127.0.0.1:11434`;
- ejecución CPU;
- A01 score `1.0`;
- dos tool calls;
- segunda medición registrada: **47.9803 tok/s** en `2.345202 s`.

## 3. Qué se fija como contrato

La arquitectura V1 establece estas fronteras:

```text
MODEL
  ≠ RUNTIME
  ≠ HARDWARE
  ≠ ESTIMATION
  ≠ MEASUREMENT
  ≠ GRADING
```

Un modelo no hereda automáticamente el rendimiento de otro runtime. Una estimación no se convierte en medición. Una cifra externa no se convierte en evidencia LEONES solo por aparecer en una fuente de conocimiento.

## 4. Higiene del repositorio

El estado generado durante una ejecución local queda fuera del árbol versionado mediante `.gitignore`, incluyendo:

- `.leones/`;
- `artifacts/`;
- `__pycache__/`;
- `.pytest_cache/`;
- `.venv/`;
- clones temporales `upstream/`.

Esto permite ejecutar pruebas y benchmarks localmente sin ensuciar el repositorio ni convertir resultados efímeros en código accidentalmente versionado.

## 5. Evidencia histórica

La evidencia de una ejecución debe poder ser auditada posteriormente. Para A01, el registro de referencia conserva:

- identidad del modelo;
- runtime y versión;
- timestamp;
- execution ID;
- resultado del grader;
- wall time;
- throughput cuando lo reporta el runtime;
- hash del resultado del ejecutor.

La medición de `52.7164 tok/s` y la posterior de `47.9803 tok/s` no son contradictorias por sí mismas: son ejecuciones distintas. La variación debe conservarse y analizarse antes de convertir una cifra en benchmark representativo.

## 6. Lo que queda deliberadamente fuera del cierre V1

No se declara cerrado por esta prueba:

- el benchmark físico de todos los modelos;
- la comparación exhaustiva de runtimes;
- la optimización de cada hardware;
- la cobertura completa de tareas agentivas;
- la automatización de toda la cadena de recomendación;
- la eliminación de todos los valores `unknown`;
- la equivalencia entre mediciones de terceros y mediciones LEONES.

Esas cuestiones pertenecen a las siguientes iteraciones.

## 7. Regla de mantenimiento

Todo nuevo runtime, adaptador o benchmark que se incorpore después de V1 debe intentar satisfacer el mismo contrato. Si necesita una excepción, esa excepción debe documentarse como decisión arquitectónica y acompañarse de una prueba.

La regla editorial y técnica para las siguientes versiones es:

> **Build it. Measure it. Explain it. Preserve the evidence.**

Construir sin medir produce una hipótesis. Medir sin explicar produce un número. Explicar sin conservar la evidencia produce una afirmación difícil de auditar. V1 exige las cuatro cosas juntas.
