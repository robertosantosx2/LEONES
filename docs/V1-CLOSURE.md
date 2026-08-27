# LEONES V1 — Criterio de cierre

> **Build it. Measure it. Explain it. Preserve the evidence.**

## 1. Declaración

V1 no significa que todo LEONES esté terminado. Significa que las piezas que forman el **camino mínimo de conocimiento → selección → ejecución → medición → evidencia** tienen contratos explícitos, pruebas y una primera validación física.

El cierre debe entenderse como un **baseline reproducible**, no como el final del proyecto.

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

### Medición

- El runtime puede aportar `eval_count` y `eval_duration`.
- `measured_tps` se calcula únicamente cuando los datos necesarios están disponibles.
- Cuando el runtime no informa tokens evaluados, LEONES conserva `null` en lugar de fabricar una cifra.
- Las ejecuciones sucesivas no sobrescriben conceptualmente la historia.

### CI

La integración está respaldada por los gates definidos para V1 y la suite local de regresión permanece verde.

La CI utiliza el runtime fixture para mantener la prueba determinista y portable.

### Runtime real

La validación física de cierre utilizó:

- Ollama `0.33.1`;
- `qwen2.5:0.5b-instruct-q4_K_M`;
- endpoint local `127.0.0.1:11434`;
- tarea A01;
- dos tool calls;
- cero errores de herramienta;
- resultado `success`;
- grader `passed`, score `1.0`;
- **40.7666 tok/s medidos en `5.744973 s`**.

La ejecución de cierre quedó identificada por `execution_id` `378854c5-8147-47a3-8e1b-33b078424d00` y por el hash `ae11c085b986ef1c7a88983c4deaeb82cd714e72de36c3bff81e8eff7fa3f02b` del resultado del ejecutor.

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

## 5. Evidencia histórica y referencia de cierre

La evidencia de una ejecución debe poder ser auditada posteriormente. Para A01, el registro de referencia conserva:

- identidad del modelo;
- runtime y versión;
- timestamp;
- execution ID;
- resultado del grader;
- wall time;
- throughput cuando lo reporta el runtime;
- hash del resultado del ejecutor.

Durante la integración se obtuvieron tres mediciones válidas:

| Ejecución | Wall time | Throughput | Estado |
|---|---:|---:|---|
| histórica 1 | `2.147932 s` | `52.7164 tok/s` | histórica |
| histórica 2 | `2.345202 s` | `47.9803 tok/s` | histórica |
| **cierre V1** | **`5.744973 s`** | **`40.7666 tok/s`** | **referencia de cierre** |

Las diferencias no son contradictorias: son ejecuciones distintas. **La última ejecución válida es la referencia de cierre de esta validación.** No se debe escoger la mayor cifra para representar el sistema.

Estas mediciones tampoco deben tratarse como un benchmark comparativo general. Para ello habrá que fijar posteriormente una metodología con repeticiones, calentamiento, contexto, generación, versión del runtime y condiciones de hardware.

## 6. Reproducibilidad del cierre

El camino canónico de reproducción es:

```bash
cd ~/leones-work/LEONES

ollama pull qwen2.5:0.5b-instruct-q4_K_M

rm -rf .leones/a01-real-workspace
mkdir -p .leones/a01-real-workspace artifacts

python3 scripts/a01_runtime_benchmark.py \
  --selection artifacts/real-a01-selection.json \
  --runtime-commands artifacts/real-a01-runtime-commands.json \
  --workspace .leones/a01-real-workspace \
  --prompt 'Execute A01. Return only JSONL tool calls.' \
  --out artifacts/a01-real-runtime-benchmark.v1.json

python3 -m json.tool artifacts/a01-real-runtime-benchmark.v1.json >/dev/null
cat .leones/a01-real-workspace/report.txt
```

La selección y los comandos de runtime deben corresponder al modelo que se pretende medir. La evidencia generada no debe copiarse ni editarse para convertir una estimación en una medición.

## 7. Verificación de cierre

La revisión de cierre local obtuvo:

```text
A01 REAL: ALL ASSERTIONS PASSED
174 passed
ALL 12 SCHEMAS OK
```

Esto verifica simultáneamente la evidencia estructurada de A01, la suite completa de regresión y la sintaxis de los doce esquemas JSON presentes en `schemas/`.

El repositorio local quedó limpio después de restaurar los artefactos compilados que habían sido detectados por Git. Los resultados efímeros de la ejecución permanecen excluidos por `.gitignore`.

## 8. Lo que queda deliberadamente fuera del cierre V1

No se declara cerrado por esta prueba:

- el benchmark físico de todos los modelos;
- la comparación exhaustiva de runtimes;
- la optimización de cada hardware;
- la cobertura completa de tareas agentivas;
- la automatización de toda la cadena de recomendación;
- la eliminación de todos los valores `unknown`;
- la equivalencia entre mediciones de terceros y mediciones LEONES.

Estas cuestiones pertenecen a las siguientes iteraciones.

## 9. Regla de mantenimiento

Todo nuevo runtime, adaptador o benchmark que se incorpore después de V1 debe intentar satisfacer el mismo contrato. Si necesita una excepción, esa excepción debe documentarse como decisión arquitectónica y acompañarse de una prueba.

La regla editorial y técnica para las siguientes versiones es:

> **Build it. Measure it. Explain it. Preserve the evidence.**

Construir sin medir produce una hipótesis. Medir sin explicar produce un número. Explicar sin conservar la evidencia produce una afirmación difícil de auditar. V1 exige las cuatro cosas juntas.
