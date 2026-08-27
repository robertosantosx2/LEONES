# LEONES V1 — Estado de cierre y baseline reproducible

> **Build it. Measure it. Explain it. Preserve the evidence.**

## 1. Propósito

Este documento es el punto de entrada operativo para entender qué significa **V1** en LEONES, qué está demostrado, qué queda fuera del alcance y qué debe comprobarse antes de considerar una instalación local limpia.

V1 no significa que LEONES esté terminado. Significa que el **camino mínimo conocimiento → selección → autorización → ejecución → grading → medición → evidencia** tiene un contrato explícito, una implementación real, una prueba determinista y una validación física de referencia.

El objetivo de este baseline es que una persona distinta pueda leer la documentación, reproducir la prueba y distinguir sin ambigüedad entre una afirmación, una estimación y una medición.

---

## 2. Baseline de referencia

La integración A01 de referencia utiliza:

| Dimensión | Baseline |
|---|---|
| Tarea | `A01` |
| Modelo | `qwen2.5:0.5b-instruct-q4_K_M` |
| Cuantización | `Q4_K_M` |
| Runtime | Ollama |
| Versión | `0.33.1` |
| Endpoint | `127.0.0.1:11434` |
| Ejecución | CPU |
| Tool calls | `lookup_model → write_report` |
| Resultado | `success` |
| Grader | `passed` |
| Score | `1.0` |
| Medición de referencia | `47.9803 tok/s` |
| Wall time de referencia | `2.345202 s` |
| Execution ID | `a757ce94-0a2c-4042-95a2-39c89d8ba67c` |

La medición de referencia es **una observación de una ejecución concreta**. No debe convertirse en una cifra universal del modelo, de Ollama ni del hardware.

Existió una ejecución anterior de la misma integración con `52.7164 tok/s` y `2.147932 s`. Ambas deben conservarse como ejecuciones distintas; la segunda se utiliza como referencia documental de esta iteración. La variabilidad entre ejecuciones es normal y debe medirse antes de presentar un valor como representativo.

---

## 3. Camino que V1 fija

```text
conocimiento / candidatos
          ↓
selección de modelo
          ↓
runtime-selection.v1
          ↓
plan autorizado
          ↓
runtime confiable
          ↓
modelo real
          ↓
A01
          ↓
lookup_model → write_report
          ↓
grader
          ↓
runtime-benchmark.v1
          ↓
evidence.v1
          ↓
router / conocimiento posterior
```

La frontera importante es que **la selección no ejecuta directamente**. El selector produce un plan. El gate decide si ese plan puede ejecutarse. El adaptador recibe ese plan y utiliza el comando de runtime previamente confiado.

Esto evita convertir una respuesta textual del modelo en una instrucción de shell.

---

## 4. Qué está demostrado

### 4.1 Selección

- El modelo tiene una identidad explícita.
- La cuantización forma parte de la identidad de ejecución.
- El runtime y su versión quedan registrados.
- El plan atraviesa `runtime-selection.v1`.
- El plan queda `execution_authorized` antes de ejecutar.

### 4.2 Ejecución

- El ejecutor recibe un plan estructurado.
- Los comandos de runtime se proporcionan como listas `argv` confiables.
- Ollama se utiliza mediante su API local.
- A01 exige dos herramientas en orden.

### 4.3 Grading

El grader A01 comprueba:

1. orden de herramientas;
2. identidad del modelo objetivo;
3. resultado válido de `lookup_model`;
4. existencia del artefacto;
5. identidad del modelo dentro del artefacto.

Una ejecución rápida pero incorrecta no puede convertirse en evidencia válida.

### 4.4 Medición

Ollama proporciona `eval_count` y `eval_duration`. LEONES calcula throughput solamente cuando ambos están disponibles:

```text
eval_count / (eval_duration / 1e9)
```

Si un runtime no proporciona los datos necesarios, el campo permanece `null`. **No se fabrica una medición.**

### 4.5 Evidencia

La evidencia conserva, cuando están disponibles:

- modelo;
- cuantización;
- runtime y versión;
- tarea;
- timestamp;
- execution ID;
- resultado del grader;
- wall time;
- throughput medido;
- hash del resultado del ejecutor.

---

## 5. Qué NO está demostrado por V1

V1 no afirma que:

- todos los modelos estén benchmarkeados físicamente;
- Ollama sea el mejor runtime para todos los modelos;
- el modelo de referencia sea el mejor para todas las tareas;
- `47.9803 tok/s` sea una cifra universal;
- las mediciones de diferentes equipos sean comparables sin normalizar condiciones;
- todas las tareas agentivas estén cubiertas;
- todos los valores desconocidos del Atlas hayan desaparecido;
- las cifras de terceros sean mediciones LEONES;
- la recomendación automática completa esté terminada.

Estas limitaciones son parte del contrato, no defectos que deban ocultarse.

---

## 6. Fixture frente a runtime real

LEONES mantiene deliberadamente dos caminos.

### Fixture

El fixture sirve para CI. Debe ser:

- determinista;
- rápido;
- independiente de GPU;
- independiente de descargas de modelos;
- adecuado para regresiones de contratos.

### Runtime real

El runtime real sirve para validar físicamente la integración:

- runtime instalado;
- modelo real;
- endpoint real;
- inferencia real;
- medición devuelta por el runtime;
- artefacto real;
- grading real.

**No deben mezclarse.** Un fixture que pasa no demuestra rendimiento físico. Una ejecución física que pasa no sustituye la regresión determinista de CI.

---

## 7. Evidencia, estimación y fuente no son sinónimos

LEONES mantiene estas categorías separadas:

| Estado | Significado |
|---|---|
| `estimated` | cálculo o predicción; no se ha medido físicamente |
| `reported` | dato declarado por una fuente externa o runtime |
| `observed` | configuración o comportamiento observado sin constituir necesariamente una medición LEONES |
| `measured` | resultado obtenido mediante una ejecución de LEONES |
| `verified` | dato que ha superado el quality gate correspondiente |
| `unknown` | todavía no demostrado |

Una fuente de conocimiento puede aportar una excelente hipótesis sin convertirse por ello en evidencia experimental de LEONES.

---

## 8. Higiene del repositorio

El árbol versionado debe contener producto y conocimiento estable:

- código;
- tests;
- contratos;
- schemas;
- fixtures;
- workflows;
- documentación;
- decisiones arquitectónicas;
- descripciones reproducibles de mediciones.

No debe contener estado efímero de una ejecución local:

- `.leones/`;
- `artifacts/`;
- `__pycache__/`;
- `.pytest_cache/`;
- `.venv/`;
- clones temporales `upstream/`;
- logs temporales;
- archivos de IDE o del sistema.

La regla completa está en [`V1-CLEAN-ROOM.md`](V1-CLEAN-ROOM.md).

---

## 9. Procedimiento de reproducción local

Con Ollama instalado y el modelo disponible:

```bash
cd ~/leones-work/LEONES

ollama pull qwen2.5:0.5b-instruct-q4_K_M

rm -rf .leones/a01-real-workspace
mkdir -p .leones/a01-real-workspace artifacts

python3 scripts/a01_runtime_benchmark.py \
  --selection artifacts/real-a01-selection.json \
  --runtime-commands artifacts/real-a01-runtime-commands.json \
  --workspace .leones/a01-real-workspace \
  --out artifacts/a01-real-runtime-benchmark.v1.json

python3 -m json.tool artifacts/a01-real-runtime-benchmark.v1.json >/dev/null
cat .leones/a01-real-workspace/report.txt
```

La ejecución correcta debe producir un JSON válido, un resultado `success`, grader aprobado y un `report.txt` cuyo modelo coincida con la selección.

La disponibilidad del servicio puede comprobarse con:

```bash
curl -s http://127.0.0.1:11434/api/tags
ollama list
ollama ps
```

No es necesario arrancar un segundo `ollama serve` si el puerto `11434` ya está ocupado por el servicio correcto.

---

## 10. Checklist de cierre

### Código

- [x] Selector y runtime-selection conectados.
- [x] Adaptador A01 real.
- [x] Runtime Ollama real.
- [x] Fixture determinista.
- [x] Grader A01.
- [x] Medición runtime cuando el runtime la proporciona.

### Contratos

- [x] `runtime-selection.v1`.
- [x] `runtime-benchmark.v1`.
- [x] `evidence.v1`.
- [x] contrato de herramientas A01.
- [x] separación de fixture y runtime real.

### Evidencia

- [x] modelo identificado.
- [x] runtime y versión identificados.
- [x] tool order validado.
- [x] artefacto validado.
- [x] throughput real registrado.
- [x] execution ID registrado.
- [x] hash del resultado registrado.
- [x] historial de ejecuciones preservado conceptualmente.

### Documentación

- [x] criterio de cierre V1.
- [x] metodología A01 real.
- [x] política de limpieza.
- [x] contribución documentada.
- [x] README orientado a reproducción y límites.

### Fuera del cierre

- [ ] benchmark físico exhaustivo.
- [ ] comparación completa de runtimes.
- [ ] cobertura completa de tareas agentivas.
- [ ] automatización total del recomendador.
- [ ] desaparición de todos los `unknown`.

---

## 11. Regla de evolución después de V1

Todo nuevo runtime, adaptador o benchmark debe recorrer, como mínimo:

```text
identidad
→ selección
→ autorización
→ ejecución
→ trayectoria
→ grading
→ artefacto
→ medición
→ evidencia
```

Si una integración necesita saltarse una frontera, debe existir una **decisión arquitectónica explícita y una prueba que justifique la excepción**.

La regla editorial y técnica queda fijada así:

> **Build it. Measure it. Explain it. Preserve the evidence.**

Construir sin medir produce una hipótesis. Medir sin explicar produce un número. Explicar sin conservar la evidencia produce una afirmación difícil de auditar. LEONES necesita las cuatro cosas juntas.
