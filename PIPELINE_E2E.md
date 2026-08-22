# 🦁 LEONES — PIPELINE E2E

## 1. Propósito de este documento

`PIPELINE_E2E.md` define el recorrido completo que debe seguir una ejecución de LEONES desde la descripción de la máquina, el modelo y la tarea hasta una conclusión que pueda ser medida, graduada, auditada y, únicamente después de pasar los controles correspondientes, convertida en evidencia publicable.

No es una lista de scripts. Es el **contrato de extremo a extremo** del sistema.

La idea fundamental es separar cuatro cosas que con frecuencia se mezclan:

1. **Recomendación**: qué modelo/runtime creemos que conviene.
2. **Ejecución**: qué se ejecutó realmente.
3. **Evaluación**: qué resultado produjo esa ejecución y si cumplió la tarea.
4. **Evidencia**: qué parte de la afirmación está respaldada por datos observados y con qué procedencia.

Por tanto, LEONES no debe convertir una predicción del selector en un supuesto benchmark, ni un benchmark en evidencia verificada sin una etapa explícita de verificación.

La regla maestra es:

> **Un componente puede proponer el siguiente paso, pero nunca puede declarar que ese paso ocurrió hasta recibir su resultado real.**

Esta separación es especialmente importante porque la arquitectura de LEONES está evolucionando desde recomendaciones basadas en catálogo hacia selección de runtime, ejecución real y benchmarks agentic reproducibles.

---

## 2. El recorrido completo

El recorrido conceptual del MVP es:

```text
                         ┌──────────────────────┐
                         │      USER / TASK      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   TASK INTELLIGENCE  │
                         │ objetivo + límites   │
                         └──────────┬───────────┘
                                    │
                                    ▼
┌─────────────────┐       ┌──────────────────────┐
│ HARDWARE        │──────▶│ MODEL / CANDIDATES   │
│ Intelligence    │       │ + evidence           │
└─────────────────┘       └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │        ATLAS         │
                         │ identity + metadata  │
                         │ + evidence           │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │       SELECTOR       │
                         │ model + quant +      │
                         │ runtime candidates   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ runtime-selection.v1 │
                         │ executable contract  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      EXECUTOR        │
                         │ actual run           │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │       GRADER         │
                         │ success / score /    │
                         │ failure reasons      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   RUNTIME BENCHMARK  │
                         │ TTFT / TPOT / tok/s  │
                         │ memory / errors      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      EVIDENCE        │
                         │ provenance + trace   │
                         │ + artifacts          │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │       REPORT         │
                         │ reproducible result  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ PRIVACY / PUBLISHING │
                         │       / MANADA       │
                         └──────────────────────┘
```

El recorrido funcional del MVP se expresa también como:

```text
Hardware Intelligence
        ↓
Model Identity
        ↓
Task Intelligence
        ↓
Atlas
        ↓
Router
        ↓
Runtime
        ↓
Inference
        ↓
LOTB
        ↓
Report
        ↓
Privacy
        ↓
Publish / Manada
```

La primera representación hace explícita la nueva frontera que necesitamos cerrar para que una recomendación desemboque en una **ejecución verificable**.

---

## 3. Qué entra y qué sale del pipeline

### Entrada mínima

Una ejecución reproducible necesita, como mínimo:

- descripción del hardware disponible;
- identificación del modelo candidato;
- versión/revisión del modelo;
- formato y cuantización;
- runtime elegido;
- versión del runtime;
- configuración relevante;
- definición versionada de la tarea;
- límites de herramientas, tiempo, memoria o llamadas;
- entorno de ejecución;
- política de evaluación;
- política de privacidad.

No basta con decir «Qwen funciona en esta máquina».

La unidad correcta es:

```text
hardware + model_revision + artifact/quant + runtime + runtime_version
+ configuration + task_version + environment
        ↓
     execution
        ↓
 measured result
```

### Salida mínima

La salida debe permitir responder:

1. ¿Qué máquina se utilizó?
2. ¿Qué modelo exacto se utilizó?
3. ¿Qué runtime exacto se utilizó?
4. ¿Qué tarea exacta se ejecutó?
5. ¿Qué herramientas pudo utilizar el agente?
6. ¿Qué ocurrió durante la trayectoria?
7. ¿Terminó correctamente?
8. ¿Cómo lo determinó el grader?
9. ¿Cuánto tardó?
10. ¿Qué recursos consumió?
11. ¿Qué artefactos produjo?
12. ¿Qué evidencia respalda cada afirmación?
13. ¿Qué datos deben permanecer privados?

---

# 4. Fase 0 — Task Intelligence

La tarea es el punto de partida semántico. No debe confundirse con el prompt libre que finalmente recibe el modelo.

Task Intelligence convierte una petición en una especificación ejecutable:

```text
user request
   ↓
intent / objective
   ↓
task family
   ↓
constraints
   ↓
allowed tools
   ↓
success criteria
   ↓
task_id + task_version
```

La tarea debe ser **versionada**. Si cambia el objetivo, las herramientas, las restricciones o el criterio de éxito, cambia la tarea aunque el texto parezca similar.

Esto es esencial para benchmarks. El catálogo agentic actual establece que las especificaciones de tareas no son puntuaciones y que el entorno y el grader deben versionarse antes de publicar resultados oficiales.

Por ejemplo, A01-001 está definido como una tarea de uso de herramientas: seleccionar la única herramienta permitida para satisfacer una petición restringida, sin usar shell y sin acceder fuera del sandbox. Sus criterios son selección correcta, operación completada y ausencia de acceso prohibido.

La tarea, por tanto, no dice «el modelo respondió bien». Define qué comportamiento observable debe producir el sistema.

---

# 5. Fase 1 — Hardware Intelligence

Hardware Intelligence describe el sistema real sobre el que se va a ejecutar la inferencia.

Debe distinguir entre:

- CPU y arquitectura;
- número de núcleos/hilos;
- GPU(s);
- VRAM;
- RAM disponible y total;
- memoria unificada cuando exista;
- ancho de banda de memoria cuando sea conocido;
- almacenamiento;
- velocidad/respuesta del almacenamiento cuando sea medible;
- backend disponible;
- instrucciones de CPU relevantes;
- drivers;
- sistema operativo;
- aceleradores/NPU cuando realmente sean utilizables por el runtime.

No debe limitarse a «tengo 16 GB de RAM».

Para selección de LLM interesan especialmente dos dimensiones:

```text
CAPACIDAD
¿Cabe el modelo + KV cache + runtime + margen?

RENDIMIENTO
¿Puede mover los pesos/KV suficientemente rápido?
```

La serie de conocimiento incorporada al proyecto resume esta relación como:

```text
VRAM ≈ parámetros × (bits por peso / 8)
```

pero esa fórmula solo estima el coste de los pesos. La ejecución real también necesita caché KV, activaciones, batching/concurrencia y overhead del runtime. Por ello el selector debe tratar la capacidad como un presupuesto, no como una simple comparación de tamaño de archivo.

También debe considerar el ancho de banda. La capacidad determina si algo cabe; el ancho de banda es uno de los factores principales que determinan la velocidad de decode.

---

# 6. Fase 2 — Model Identity

Model Identity establece exactamente qué candidato estamos considerando.

Un nombre de familia no es suficiente.

La identidad debe poder distinguir:

- organización;
- familia;
- nombre exacto;
- arquitectura;
- parámetros totales;
- parámetros activos si es MoE;
- contexto soportado;
- modalidad;
- base/instruct/reasoning/tool;
- revisión/commit/version;
- licencia;
- formato;
- cuantización;
- tokenizer;
- chat template;
- fuentes de evidencia;
- estado de disponibilidad.

Esto evita un error crítico: «modelo X» no identifica necesariamente el artefacto que se ejecutó.

En un benchmark reproducible necesitamos distinguir:

```text
model_id
model_revision
artifact_id
quantization
runtime_compatibility
```

La plantilla de chat y el tokenizer forman parte del contrato práctico del modelo. Un runtime correctamente instalado puede producir resultados incorrectos si se aplica una plantilla incompatible.

---

# 7. Fase 3 — Atlas

Atlas es la capa de conocimiento estructurado que conecta identidad, capacidades, compatibilidad y evidencia.

Su función no es ejecutar el modelo.

Su función es permitir que LEONES pueda preguntar:

> «Dados este hardware y esta tarea, ¿qué candidatos existen y qué sabemos de ellos?»

Atlas debe poder reunir:

```text
modelo
  ├── identidad
  ├── familia
  ├── organización
  ├── licencia
  ├── arquitectura
  ├── tamaños
  ├── cuantizaciones
  ├── runtimes compatibles
  ├── benchmarks externos
  ├── evidencia empírica
  ├── evidencia local
  └── historial/versiones
```

La distinción fundamental es:

```text
Atlas = conocimiento y candidatos
Benchmark = observación de una ejecución
```

Un resultado externo puede ayudar a seleccionar un candidato, pero no sustituye la medición local sobre el hardware concreto del usuario.

---

# 8. Fase 4 — Selector / Router

Aquí aparece la primera decisión operativa.

El selector no debería decir simplemente «usa el modelo A». Debe producir **candidatos de ejecución**.

Conceptualmente:

```text
Task
  +
Hardware
  +
Atlas evidence
  +
User constraints
       ↓
Candidate generation
       ↓
Compatibility filtering
       ↓
Ranking
       ↓
Recommendation candidates
```

Un candidato completo debería poder expresar:

```text
model
quantization
artifact
runtime
runtime configuration
expected resource envelope
selection rationale
confidence
source/evidence
```

El selector puede utilizar estimaciones. Lo que no puede hacer es convertirlas en mediciones.

Ejemplo:

```text
estimated: 12 tok/s
```

significa «estimamos». No significa:

```text
measured: 12 tok/s
```

hasta que una ejecución real lo haya observado.

---

# 9. Fase 5 — runtime-selection.v1

Esta es la frontera entre **recomendación** y **ejecución**.

El contrato debe recibir un candidato y convertirlo en una selección ejecutable y explícita.

```text
selector
   ↓
recommendation candidate
   ↓
runtime-selection.v1
   ↓
resolved executable configuration
```

El resultado debe resolver, como mínimo:

- modelo/artifact exacto;
- runtime;
- backend;
- versión;
- dispositivo(s);
- cuantización/formato;
- parámetros necesarios;
- contexto solicitado;
- límites de memoria;
- límites de tiempo;
- modo de serving/inference;
- capacidades de herramientas;
- información suficiente para reproducir la selección.

### Por qué debe ser un contrato versionado

Si el selector cambia mañana su algoritmo, un resultado antiguo debe seguir siendo interpretable. Por ello debemos poder distinguir:

```text
selection_schema_version
selector_version
runtime_selection_version
model_revision
runtime_version
```

### Regla de seguridad

Si el runtime seleccionado no puede satisfacer una precondición crítica, el pipeline debe detenerse o seleccionar un fallback explícito.

Nunca debe saltarse silenciosamente al siguiente runtime y después presentar el resultado como si procediera del runtime elegido originalmente.

---

# 10. Fase 6 — Executor

El executor es el punto donde la recomendación se convierte en hecho observable.

Su responsabilidad es **ejecutar**, no interpretar el resultado.

Debe:

1. preparar el entorno;
2. resolver el artefacto;
3. comprobar dependencias;
4. inicializar el runtime;
5. cargar el modelo;
6. aplicar la configuración;
7. ejecutar la tarea;
8. registrar eventos;
9. capturar errores;
10. conservar los artefactos necesarios;
11. devolver un resultado estructurado.

El executor debe producir una trayectoria suficientemente rica para reconstruir qué sucedió.

El runner agentic actual del repositorio ya establece esta idea mediante un `Trace` append-only y un vocabulario de eventos que incluye `model`, `tool_call`, `tool_result`, `error`, `recovery`, `artifact` y `grader`. Además, limita las llamadas a herramientas y registra tanto la invocación como el resultado y el tiempo empleado.

Por tanto, un benchmark agentic no es solamente:

```text
input → output
```

sino:

```text
input
 ↓
model decision
 ↓
tool call
 ↓
tool result
 ↓
next decision
 ↓
...
 ↓
artifact / final state
```

---

# 11. Fase 7 — A01 y el executor/grader real

A01 es el primer punto de integración natural porque es pequeño, determinista y auditable.

El catálogo define A01-001 como:

- familia: `tool_use`;
- objetivo: elegir la única herramienta permitida;
- herramienta: `filesystem`;
- prohibición: no usar shell;
- frontera: no acceder fuera del sandbox;
- éxito: herramienta correcta + operación completada + ausencia de acceso prohibido;
- grader declarado: `deterministic-v1`.

La implementación actual del benchmark agentic contiene:

```text
benchmarks/agentic/tasks.yaml
benchmarks/agentic/runner.py
benchmarks/agentic/graders.py
benchmarks/agentic/smoke_a01.py
benchmarks/agentic/adapters/
benchmarks/agentic/graders/
```

El workflow `agentic-a01-contract.yml` ejecuta los tests del contrato A01 sobre GitHub Actions. Esto es **validación del contrato**, no una medición de rendimiento del modelo.

La distinción es:

```text
A01 contract tests
        ≠
A01 model execution benchmark
```

El primero demuestra que el contrato y sus adaptadores son coherentes. El segundo debe ejecutar realmente el sistema bajo prueba y generar una trayectoria y un resultado evaluable.

La conexión que debe cerrar LEONES es:

```text
selector
   ↓
runtime-selection.v1
   ↓
A01 executor
   ↓
A01 grader
   ↓
runtime measurements
   ↓
evidence
   ↓
router/report
```

No se debe sustituir esta conexión por un script que simplemente rellene un JSON con valores esperados.

---

# 12. Fase 8 — Grader

El grader responde a una pregunta diferente de la que responde el executor.

Executor:

> ¿Qué ocurrió?

Grader:

> ¿Cumple lo ocurrido los criterios de éxito de esta tarea?

El grader debe ser tan determinista como sea posible.

El repositorio ya dispone de gradadores deterministas básicos para comprobar:

- existencia de archivo;
- igualdad exacta de texto;
- presencia de un conjunto de archivos;
- protección contra rutas fuera del root.

Un `Grade` contiene:

```text
status
score
checks
```

Esto debe evolucionar hacia un resultado que permita explicar el fallo, no solo decir «0.0».

Por ejemplo:

```json
{
  "status": "failed",
  "score": 0.0,
  "checks": [
    "correct_tool",
    "operation_completed",
    "sandbox_boundary"
  ],
  "failed_checks": ["correct_tool"]
}
```

El grader no debe mirar información que el agente no habría tenido disponible durante la ejecución si eso altera la naturaleza de la prueba.

---

# 13. Fase 9 — Runtime Benchmark

Una ejecución correcta no equivale automáticamente a una ejecución rápida.

Por eso el benchmark debe medir separadamente calidad y rendimiento.

## Métricas de inferencia

Como mínimo interesa conservar:

- tiempo de carga del modelo;
- TTFT — tiempo hasta el primer token;
- TPOT — tiempo por token de salida;
- tokens/s de generación;
- tokens de entrada;
- tokens de salida;
- duración total;
- memoria máxima;
- errores/OOM;
- llamadas a herramientas;
- duración de cada herramienta;
- duración de cada etapa.

Para serving multiusuario también pueden interesar:

- throughput;
- requests/s;
- p50;
- p95;
- p99;
- utilización de memoria;
- KV-cache;
- concurrencia.

La serie técnica de conocimiento insiste en no comparar runtimes únicamente por tokens/s con un único usuario. El benchmark debe fijar modelo, cuantización, runtime, hardware, carga de trabajo y configuración.

---

# 14. Prefill y Decode

El benchmark debe separar dos comportamientos diferentes.

### Prefill

Procesa el prompt y construye la caché KV. Es especialmente importante para documentos largos, RAG y contexto grande.

### Decode

Genera tokens de salida uno a uno. Es especialmente sensible a ancho de banda de memoria, tamaño de modelo, cuantización, caché KV y batching/concurrencia.

Por eso una única métrica «tokens/s» puede ocultar un comportamiento completamente diferente entre dos cargas de trabajo.

---

# 15. Fase 10 — Evidence

Evidence es una capa de procedencia, no un sinónimo de resultado.

El runner actual distingue explícitamente:

```text
estimated
reported
measured
verified
```

Esta clasificación debe mantenerse.

### `estimated`

Proviene de una predicción, modelo matemático, catálogo o herramienta de recomendación.

### `reported`

Un valor declarado por una fuente o por un componente que todavía no constituye una medición independiente del pipeline.

### `measured`

Existe una ejecución real que produjo el dato. Debe conservarse un identificador de ejecución y una marca temporal.

### `verified`

Requiere una verificación explícita e independiente.

El runner actual impide que una ejecución se promocione automáticamente a `verified`.

La cadena correcta es:

```text
executor
   ↓
measured
   ↓
independent verification
   ↓
verified
```

---

# 16. Provenance: de dónde salió cada número

Cada afirmación relevante debe poder contestar:

```text
¿quién lo dijo?
¿cuándo?
¿sobre qué versión?
¿cómo se obtuvo?
¿fue estimado, reportado, medido o verificado?
```

Para una ejecución local, la evidencia debe relacionar como mínimo:

```text
execution_id
benchmark_id
benchmark_version
task_id
task_version
model_revision
runtime
runtime_version
hardware
configuration
timestamp
result
trajectory
artifacts
grader
```

La evidencia externa de Atlas debe mantenerse separada de la evidencia empírica local.

Esto permite afirmar:

> «Atlas indica que este modelo es candidato y una fuente externa reporta determinado rendimiento»

sin convertirlo incorrectamente en:

> «LEONES midió ese rendimiento en esta máquina».

---

# 17. Fase 11 — LOTB

LOTB es la capa donde el resultado operativo debe quedar preparado para ser comparado, almacenado y reutilizado como benchmark.

El concepto importante es que un benchmark debe convertirse en un **artefacto reproducible**, no desaparecer en los logs de una ejecución.

Debe conservar:

- identificación del benchmark;
- versión;
- tarea;
- modelo;
- runtime;
- hardware;
- configuración;
- métricas;
- score;
- trayectoria;
- artefactos;
- evidencia;
- errores;
- limitaciones.

Esto permite comparar:

```text
modelo A + runtime X
vs
modelo A + runtime Y
vs
modelo B + runtime X
```

sin mezclar variables.

---

# 18. Fase 12 — Report

El report transforma el resultado técnico en una conclusión legible.

Debe distinguir tres niveles.

### Hecho observado

> El runtime X ejecutó A01-001 en la ejecución `...`.

### Resultado de evaluación

> El grader determinista obtuvo `success` y puntuación 1.0.

### Interpretación

> Para esta máquina y esta configuración, el candidato resultó apto para esta tarea.

La tercera afirmación es una inferencia y debe estar sustentada por las dos primeras.

Nunca debemos presentar como hecho una recomendación que todavía no haya sido ejecutada.

---

# 19. Fase 13 — Privacy

Antes de publicar un resultado, LEONES debe separar lo que es evidencia útil de lo que es información privada del usuario.

Una ejecución local puede contener:

- nombre de usuario;
- rutas personales;
- nombres de archivos;
- hostname;
- IPs;
- identificadores de hardware;
- variables de entorno;
- tokens o secretos;
- contenido de prompts;
- documentos privados;
- resultados de herramientas.

La capa de privacidad debe decidir qué se puede:

```text
publicar
anonimizar
redactar
retener localmente
eliminar
```

La privacidad se ejecuta **después de disponer del resultado**, pero **antes de convertirlo en evidencia pública**.

---

# 20. Fase 14 — Publish / Manada

La publicación no debe ser una escritura directa de los logs del runtime.

La cadena correcta es:

```text
execution
 ↓
grade
 ↓
measurements
 ↓
evidence
 ↓
report
 ↓
privacy review
 ↓
public artifact
 ↓
Manada / web
```

Manada debe recibir únicamente el artefacto que haya pasado los controles establecidos.

Esto mantiene separadas:

- conocimiento;
- recomendación;
- ejecución;
- evidencia privada;
- evidencia publicable.

---

# 21. Contrato de estado del pipeline

Cada etapa debe tener un estado explícito.

Estados recomendados:

```text
pending
selected
prepared
running
succeeded
failed
blocked
measured
verified
published
```

No deben confundirse:

```text
selected ≠ running
running ≠ succeeded
succeeded ≠ verified
verified ≠ published
```

Un pipeline robusto puede representarse como:

```text
PENDING
  ↓
SELECTED
  ↓
PREPARED
  ↓
RUNNING
  ├──────────────→ FAILED
  │
  ↓
SUCCEEDED
  ↓
MEASURED
  ↓
VERIFIED
  ↓
PUBLISHABLE
  ↓
PUBLISHED
```

No todas las ejecuciones tienen que llegar a `published`. Una ejecución puede ser perfectamente válida como diagnóstico local sin ser publicable.

---

# 22. Contrato de fallo

Los fallos también son resultados.

El pipeline debe distinguir al menos:

```text
selection_failure
model_unavailable
artifact_failure
runtime_install_failure
runtime_start_failure
load_failure
out_of_memory
execution_timeout
tool_failure
constraint_violation
grade_failure
measurement_failure
privacy_block
verification_failure
publish_failure
```

No debemos transformar todos estos estados en «modelo malo».

Por ejemplo, `OOM` puede significar modelo demasiado grande, contexto demasiado largo, KV cache demasiado grande, runtime con demasiado overhead, batching incorrecto o cuantización incompatible.

El diagnóstico pertenece a la capa de evidencia/operaciones, no a una intuición del selector.

---

# 23. Artefactos y reproducibilidad

Una ejecución reproducible debe guardar referencias a los artefactos importantes, no solo al resultado final.

Ejemplos:

```text
result.json
trace.json
metrics.json
stdout.log
stderr.log
config.json
model-manifest.json
runtime-manifest.json
grade.json
artifacts/
```

No todos deben publicarse.

La existencia de estos artefactos permite reconstruir la cadena de causalidad:

```text
selección
   ↓
configuración
   ↓
ejecución
   ↓
trayectoria
   ↓
artefacto final
   ↓
grader
   ↓
métricas
```

---

# 24. Benchmark agentic: por qué la trayectoria importa

En una tarea agentic, el resultado final puede ser correcto por una razón incorrecta o puede parecer incorrecto aunque el artefacto final sea válido.

Por eso la trayectoria debe registrar, cuando corresponda:

```text
model decision
↓
tool call
↓
tool result
↓
recovery
↓
artifact
↓
grader
```

Esto permite estudiar selección de herramientas, número de llamadas, errores, recuperación, pasos innecesarios, violaciones de límites, eficiencia y coste temporal.

La métrica de éxito ya no es simplemente «texto correcto».

---

# 25. Coste y latencia

Una recomendación útil de LEONES debe tener en cuenta que el modelo más capaz no es necesariamente el mejor modelo para una máquina concreta.

El selector debe poder comparar:

```text
quality
×
latency
×
memory
×
reliability
×
cost
×
privacy
```

El benchmark real proporciona las variables que el selector inicialmente solo podía estimar.

Por eso el pipeline forma un bucle de aprendizaje operativo:

```text
Atlas / external evidence
          ↓
      recommendation
          ↓
      real execution
          ↓
       benchmark
          ↓
        evidence
          ↓
      Atlas / Router
          ↓
 better recommendation
```

Los resultados locales son nuevo conocimiento empírico que puede mejorar futuras recomendaciones, siempre conservando su procedencia y evitando sobreajustar los benchmarks.

---

# 26. Cómo debe comportarse el Router después de un benchmark

El Router no debe recibir simplemente un número.

Debe recibir un objeto con contexto.

Ejemplo conceptual:

```json
{
  "model": "candidate-A",
  "runtime": "runtime-X",
  "hardware": "machine-profile-1",
  "task": "A01-001",
  "result": {
    "status": "success",
    "score": 1.0
  },
  "performance": {
    "ttft_ms": 420,
    "tpot_ms": 85,
    "tokens_per_second": 11.7
  },
  "evidence": {
    "type": "measured",
    "execution_id": "..."
  }
}
```

El Router puede entonces diferenciar:

```text
candidate A
  → compatible
  → measured
  → succeeds on task family X
  → 11.7 tok/s
```

frente a:

```text
candidate B
  → estimated only
  → unknown on this hardware
```

La primera evidencia debe pesar más que la segunda para ese hardware/tarea, sin asumir automáticamente que el resultado generaliza a todas las máquinas.

---

# 27. Principio de no contaminación del benchmark

Las pruebas que se utilizan para seleccionar o ajustar un sistema no deben confundirse con una evaluación final independiente.

El pipeline debe mantener:

```text
development / smoke
        ≠
benchmark de selección
        ≠
auditoría final
```

Los smoke tests sirven para comprobar infraestructura; los contract tests para comprobar contratos; los benchmarks de selección para elegir candidatos; las evaluaciones de auditoría deben permanecer protegidas frente a la optimización sobre sus resultados.

Esto evita que LEONES termine seleccionando el modelo que mejor explota exactamente la prueba que utilizamos para elegirlo.

---

# 28. Diferencia entre CI y benchmark real

GitHub Actions puede demostrar que:

```text
código instala
código importa
contratos pasan
graders pasan
adaptadores pasan
```

Pero eso no demuestra que un modelo concreto sea rápido o bueno en el hardware del usuario.

El workflow actual de A01 es un ejemplo de esta distinción: ejecuta el contrato de A01 sobre `ubuntu-latest` y sus tests de adaptador. Eso es una garantía de integración del contrato.

El benchmark real necesita:

```text
hardware target
+
model artifact
+
runtime
+
task
+
actual inference
```

y debe producir mediciones.

---

# 29. Smoke → Contract → Execution → Benchmark → Evidence

El pipeline debe tener varios niveles de validación.

### Nivel 1 — Smoke

¿El componente arranca?

### Nivel 2 — Contract

¿Cumple la interfaz esperada?

### Nivel 3 — Execution

¿Se puede ejecutar realmente sobre el entorno objetivo?

### Nivel 4 — Benchmark

¿Qué rendimiento y resultado produce?

### Nivel 5 — Evidence

¿Podemos demostrar cómo se obtuvo?

### Nivel 6 — Verification

¿Existe una comprobación independiente?

### Nivel 7 — Publication

¿Puede publicarse sin exponer información privada?

Esto evita el error clásico:

```text
pytest passed
     ↓
"el modelo funciona"
```

El significado correcto es:

```text
pytest passed
     ↓
"el contrato probado por esos tests pasa"
```

---

# 30. Qué significa que el pipeline esté realmente cerrado

No consideraremos cerrado el E2E cuando existan muchos scripts independientes.

Está cerrado cuando una ejecución puede hacer esto sin intervención manual:

```text
1. detectar hardware
2. interpretar tarea
3. consultar Atlas
4. producir candidatos
5. resolver runtime-selection.v1
6. preparar runtime
7. ejecutar el modelo
8. ejecutar la tarea
9. registrar trayectoria
10. ejecutar grader
11. medir rendimiento
12. generar evidence
13. generar report
14. aplicar privacidad
15. producir artefacto publicable
```

Y, sobre todo, cuando cada transición esté respaldada por un artefacto o resultado verificable.

---

# 31. Criterios de aceptación del E2E MVP

El MVP puede considerarse operacional cuando exista al menos una ruta completa reproducible:

```text
hardware real
   +
modelo accesible
   +
tarea A01-001
   ↓
selector
   ↓
runtime-selection.v1
   ↓
executor real
   ↓
grader determinista
   ↓
mediciones runtime
   ↓
resultado canónico
   ↓
evidence measured
   ↓
report
```

Debe ser posible repetir la ejecución y obtener un resultado que conserve identidad suficiente para explicar cualquier diferencia.

El primer objetivo no es soportar todos los modelos ni todos los runtimes.

El primer objetivo es demostrar que **una sola ruta funciona de verdad de extremo a extremo**.

---

# 32. Qué no debe hacer LEONES

LEONES no debe:

- inventar una medición que no existe;
- presentar una estimación como benchmark;
- declarar un modelo «óptimo» sin haber fijado tarea y hardware;
- mezclar versiones de runtime;
- mezclar revisiones de modelo;
- perder la cuantización utilizada;
- ocultar un OOM como «modelo incompatible» sin diagnóstico;
- convertir contract tests en resultados de modelo;
- publicar logs privados;
- promover automáticamente `measured` a `verified`;
- comparar dos resultados obtenidos con cargas de trabajo diferentes como si fueran equivalentes;
- cambiar silenciosamente de runtime durante una ejecución;
- modificar el benchmark después de observar resultados y continuar llamándolo evaluación limpia.

---

# 33. Arquitectura de datos recomendada

La unidad fundamental de intercambio debe ser un resultado estructurado, no texto libre.

Conceptualmente:

```json
{
  "schema_version": "1.x",
  "status": "reported",
  "evidence": {
    "evidence_type": "measured",
    "source": "...",
    "execution_id": "...",
    "measured_at": "..."
  },
  "hardware": {},
  "model": {},
  "runtime": {},
  "task": {},
  "inference": {},
  "benchmark": {},
  "lotb": {},
  "agentic": {
    "trajectory": [],
    "metrics": {},
    "tools": [],
    "outcome": {},
    "grader": {},
    "artifacts": []
  }
}
```

El runner existente ya utiliza `schema_version`, `evidence`, `hardware`, `model`, `inference` y una sección `agentic` con benchmark, tarea, ejecución, runtime, entorno, herramientas, outcome, trayectoria, métricas, seguridad, artefactos y grader.

La evolución del pipeline debe conservar esta filosofía de resultado canónico.

---

# 34. Flujo de decisión completo

```text
                    ┌──────────────┐
                    │    TASK      │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   HARDWARE   │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │    ATLAS     │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   SELECTOR   │
                    └──────┬───────┘
                           │ candidate
                           ▼
              ┌─────────────────────────┐
              │ runtime-selection.v1    │
              └────────────┬────────────┘
                           │ executable config
                           ▼
                    ┌──────────────┐
                    │   EXECUTOR   │
                    └──────┬───────┘
                           │ trace + result
                           ▼
                    ┌──────────────┐
                    │    GRADER    │
                    └──────┬───────┘
                           │ grade
                           ▼
                    ┌──────────────┐
                    │   BENCHMARK  │
                    └──────┬───────┘
                           │ metrics
                           ▼
                    ┌──────────────┐
                    │   EVIDENCE   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │    REPORT    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   PRIVACY    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ MANADA / WEB │
                    └──────────────┘
                           │
                           ▼
                    feedback to Atlas
```

El último enlace es deliberado: los resultados locales no son solamente el final del pipeline. Son nuevo conocimiento empírico que puede mejorar futuras recomendaciones, siempre conservando su procedencia y evitando sobreajustar los benchmarks.

---

# 35. Estado actual y siguiente cierre técnico

El repositorio ya contiene piezas importantes del circuito: catálogo versionado de tareas agentic, runner con trazas y separación de evidencia, graders deterministas, smoke tests, adaptadores y workflows de CI. La estructura de benchmarks agentic incluye explícitamente runner, graders, tareas, adaptadores y pruebas.

Lo que **no debe darse por cerrado solo porque existan esas piezas** es el enlace físico completo entre el selector de modelos/runtimes y el executor que ejecuta el modelo real.

Por eso el siguiente bloque de implementación debe concentrarse en localizar y fijar el ejecutor real de A01 y conectar:

```text
selector
   ↓
runtime-selection.v1
   ↓
A01 executor
   ↓
A01 grader
   ↓
runtime benchmark
   ↓
evidence
   ↓
Router / Report
```

La prioridad es **cerrar una ruta real**, no añadir más documentación conceptual ni más candidatos de modelos antes de que esa ruta produzca una medición auténtica.

---

# 36. Principio final

LEONES no debe ser simplemente un catálogo que recomienda modelos.

Debe convertirse en un sistema que:

```text
CONOCE
  ↓
RECOMIENDA
  ↓
EJECUTA
  ↓
MIDE
  ↓
GRADA
  ↓
DEMUESTRA
  ↓
APRENDE
```

La diferencia entre una recomendación y una plataforma de conocimiento empírico está precisamente aquí:

> **LEONES debe poder demostrar qué recomendó, qué ejecutó, qué ocurrió, cómo lo evaluó y qué evidencia permite sostener la conclusión.**

Ese es el objetivo real del pipeline E2E.
