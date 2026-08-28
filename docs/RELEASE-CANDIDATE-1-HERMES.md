# LEONES — Release Candidate 1: integración de Hermes

> **Anexo normativo del plan `docs/RELEASE-CANDIDATE-1.md`.**
>
> **Estado: CONGELADO junto con RC1.**
>
> Hermes entra en RC1 como **harness agéntico**, no como sustituto del runtime de inferencia ni como nueva capa de medición.

**Fecha:** 2026-08-28  
**Base:** JALÓN 3 cerrado  
**Plan principal:** [`RELEASE-CANDIDATE-1.md`](RELEASE-CANDIDATE-1.md)  
**Proyecto de referencia:** [NousResearch/Hermes-Agent](https://github.com/NousResearch/hermes-agent)

---

## 1. Decisión arquitectónica

RC1 incorpora **Hermes Agent** como candidato prioritario y harness agéntico de referencia para demostrar la capacidad de LEONES de ejecutar **tareas reales con herramientas**, no únicamente inferencia de texto.

La distinción fundamental es:

```text
LEONES
  │
  ├── selección de modelo
  ├── selección/autorización de runtime
  ├── protocolo de medición
  └── evidencia
          │
          ↓
       HERMES
       harness agéntico
          │
          ├── modelo/proveedor autorizado
          ├── tools
          ├── skills
          ├── memoria
          ├── terminal / MCP
          └── trayectoria
```

**Hermes no sustituye a `llama.cpp`.**

En RC1:

- `llama.cpp` continúa siendo el **runtime físico canónico de inferencia local** heredado de JALÓN 2–3;
- Hermes pasa a ser el **harness agéntico canónico de referencia** para el vertical A01;
- el adaptador de runtime sigue siendo responsable de la ejecución de inferencia;
- Hermes es responsable de la interacción agente → herramientas → modelo → trayectoria;
- LEONES sigue siendo responsable de selección, autorización, medición, evidencia y recomendación.

Esto evita mezclar tres conceptos diferentes:

```text
modelo       ≠ runtime       ≠ agent harness
Qwen/...       llama.cpp        Hermes
```

---

# 2. Por qué Hermes entra en RC1

Hermes es especialmente adecuado para el objetivo de RC1 porque es un agente local/generalista con interfaz CLI/TUI, herramientas, memoria persistente, sistema de skills, subagentes, MCP y scheduling, y admite distintos proveedores/modelos. Su repositorio oficial está publicado bajo licencia MIT. citeturn0search0

Para LEONES esto permite probar una hipótesis más importante que "¿cuántos tokens por segundo produce el runtime?":

> **¿Puede LEONES recomendar una combinación modelo + runtime + hardware que sea realmente útil para una tarea agentiva?**

La respuesta de RC1 debe poder apoyarse en una trayectoria reproducible y en evidencia física, no solamente en una ficha de modelo.

---

# 3. Papel exacto de Hermes en RC1

Hermes tendrá cuatro responsabilidades dentro del producto mínimo.

## 3.1 Harness de ejecución agentiva

Hermes proporcionará el bucle de agente para A01:

```text
prompt/tarea
    ↓
Hermes
    ↓
modelo
    ↓
tool call
    ↓
resultado de herramienta
    ↓
Hermes
    ↓
respuesta / siguiente acción
    ↓
outcome
```

LEONES no debe reimplementar este bucle dentro del selector.

## 3.2 Superficie de herramientas

Las herramientas necesarias para A01 se tratarán como parte explícita del entorno de evaluación.

Cada ejecución debe poder identificar:

- herramientas habilitadas;
- herramientas realmente invocadas;
- número de llamadas;
- errores de herramientas;
- recuperación, si existe;
- artefactos producidos;
- resultado final.

## 3.3 Contexto y memoria del agente

Hermes dispone de memoria persistente y mecanismos de skills/contexto. Para RC1 no se pretende evaluar toda su arquitectura de memoria.

La política mínima será:

- contexto inicial controlado;
- skills explícitamente declaradas;
- memoria persistente desactivada o aislada cuando pueda contaminar la reproducibilidad de A01;
- cualquier estado persistente relevante debe formar parte de la evidencia;
- no reutilizar silenciosamente una sesión anterior como entrada experimental.

La prioridad es **reproducibilidad antes que riqueza funcional**.

## 3.4 Adaptador de agente

LEONES debe tener una frontera explícita entre el contrato de selección y Hermes.

Conceptualmente:

```text
runtime-selection.v1/v1.1
          ↓
agent-execution-plan
          ↓
Hermes adapter
          ↓
Hermes
          ↓
trajectory
          ↓
agentic evidence
```

El adaptador no debe modificar el significado del contrato de medición de JALÓN 3.

---

# 4. Hermes NO es un runtime de inferencia de RC1

Esta decisión debe quedar congelada para evitar deriva arquitectónica.

Hermes puede utilizar distintos proveedores y modelos, incluidos endpoints propios/locales, pero esa flexibilidad no significa que LEONES deba convertirlo en una implementación de runtime. El propio proyecto documenta el cambio de proveedor/modelo mediante su configuración y CLI. citeturn0search0

Por tanto:

| Componente | Responsabilidad RC1 |
|---|---|
| Modelo | pesos/checkpoint/identidad |
| llama.cpp | inferencia local física canónica |
| Hermes | harness agéntico |
| LEONES selector | elegir candidato |
| LEONES runtime gate | autorizar ejecución |
| JALÓN 3 | medir y conservar evidencia |
| A01 grader | evaluar outcome/trajectory |

No se permitirá una implementación en la que Hermes sea utilizado para ocultar qué runtime, modelo o endpoint produjo la inferencia.

---

# 5. Camino canónico RC1 con Hermes

El vertical slice objetivo pasa a ser:

```text
hardware
   ↓
hardware profile
   ↓
model candidates
   ↓
fit / constraints
   ↓
runtime authorization
   ↓
agent authorization
   ↓
Hermes
   ↓
model endpoint/runtime
   ↓
tools
   ↓
trajectory
   ↓
A01 grader
   ↓
JALÓN 3 measurement
   ↓
evidence
   ↓
recommendation
```

El camino de inferencia física sigue siendo independiente:

```text
model + config + hardware
            ↓
         llama.cpp
            ↓
      raw execution
            ↓
      runtime evidence
```

El camino agéntico añade:

```text
Hermes
  ↓
task + tools + trajectory
  ↓
agentic evidence
```

Ambos registros deben poder relacionarse mediante un identificador de ejecución o correlación explícito cuando formen parte de la misma prueba.

---

# 6. A01 pasa a ser el punto de integración Hermes

A01 será el primer caso de uso donde Hermes tenga presencia obligatoria en RC1.

La ejecución debe demostrar al menos:

1. Hermes arranca correctamente;
2. recibe la tarea A01;
3. utiliza el modelo/proveedor autorizado;
4. puede utilizar las herramientas requeridas;
5. completa la trayectoria esperada;
6. produce el outcome esperado;
7. el grader puede evaluar la trayectoria;
8. LEONES conserva evidencia suficiente;
9. la ejecución queda asociada a un `execution_id`;
10. la recomendación final puede explicar qué combinación fue utilizada.

La prueba no debe depender de una sesión histórica de Hermes.

---

# 7. Contrato mínimo `hermes-agent.v1`

RC1 debe introducir un contrato pequeño y verificable, sin intentar modelar toda la API interna de Hermes.

### Identidad

```text
agent_runtime: hermes
agent_adapter: hermes.v1
agent_version: observed|unknown
```

### Entrada

- `task_id`;
- prompt/tarea;
- modelo/proveedor autorizado;
- configuración relevante;
- herramientas permitidas;
- contexto inicial;
- política de memoria;
- timeout.

### Ejecución

- `execution_id`;
- timestamp de inicio;
- timestamp de finalización;
- comando/entrypoint efectivo;
- entorno;
- configuración material;
- stdout/stderr o equivalente disponible;
- código/estado de salida.

### Trayectoria

- número de turnos;
- tool calls;
- tool errors;
- recuperaciones;
- subagentes, si se habilitan;
- artefactos;
- outcome.

### Resultado

- `status`;
- score/grading;
- duración;
- métricas observadas;
- evidencia asociada;
- procedencia.

### Regla de desconocido

Si Hermes no expone un dato de forma fiable, se registra como `unknown`. No se reconstruye por inferencia.

---

# 8. Seguridad y aislamiento

La incorporación de Hermes aumenta la superficie de ejecución porque un agente puede utilizar terminal, navegador, MCP y otras herramientas. El proyecto Hermes documenta controles de aprobación de comandos, emparejamiento de mensajes y aislamiento mediante contenedores. citeturn0search0

Para RC1:

- herramientas mínimas necesarias para A01;
- sin credenciales personales;
- sin acceso innecesario al sistema de archivos;
- sin secretos dentro de prompts o artefactos;
- entorno de prueba aislado cuando la herramienta lo requiera;
- lista explícita de herramientas permitidas;
- timeouts y límites de ejecución;
- conservación de errores y abortos como evidencia.

**No se considerará válida una prueba agentiva que sólo funcione porque el agente posee permisos ilimitados.**

---

# 9. Hermes y la medición

Hermes no define el benchmark físico.

La medición sigue perteneciendo a JALÓN 3.

Debe mantenerse una separación entre:

### Métricas del runtime

- tokens/s;
- TTFT si está disponible;
- duración de inferencia;
- memoria/VRAM cuando sea observable;
- versión del runtime;
- configuración.

### Métricas del agente

- duración total de tarea;
- número de turnos;
- tool calls;
- tool errors;
- recovery count;
- outcome score;
- artefactos producidos.

### Métricas combinadas

Cuando sea útil:

```text
tarea útil / tiempo total
coste / tarea
éxito / tarea
éxito / segundo
```

Pero estas métricas derivadas nunca deben sobrescribir las mediciones primarias.

---

# 10. Hermes y el modelo selector

El selector de LEONES debe tratar Hermes como una **restricción/capacidad del workload**, no como una razón para seleccionar automáticamente un modelo concreto.

Ejemplo:

```text
workload = agentic_A01
agent_harness = hermes
hardware = perfil local
context = objetivo
        ↓
 candidatos compatibles
        ↓
 runtime autorizado
        ↓
 ejecución
```

La selección debe poder expresar:

- Hermes compatible/no compatible;
- modelo compatible/no compatible;
- runtime compatible/no compatible;
- herramientas requeridas;
- memoria requerida;
- contexto requerido;
- evidencia física disponible.

---

# 11. Hermes y LLMFit

La cadena de preselección queda:

```text
hardware
   ↓
LLMFit
   ↓
model fit estimado
   ↓
LEONES selection
   ↓
Hermes compatibility
   ↓
runtime compatibility
   ↓
physical benchmark
```

LLMFit responde principalmente a:

> ¿Puede este hardware alojar razonablemente este modelo/configuración?

Hermes responde a otra cuestión:

> ¿Puede este stack ejecutar el comportamiento agéntico requerido?

El benchmark de LEONES responde finalmente:

> ¿Qué ocurre realmente en esta máquina bajo estas condiciones?

No se mezclan esas tres respuestas.

---

# 12. Hermes y evidencia

Una ejecución Hermes válida para RC1 debe producir como mínimo dos perspectivas cuando proceda:

```text
runtime evidence
       +
agentic evidence
       ↓
correlated evidence
```

La evidencia agéntica debe poder responder:

- qué tarea se ejecutó;
- qué modelo/proveedor se utilizó;
- qué herramientas estaban habilitadas;
- qué herramientas se utilizaron;
- qué errores ocurrieron;
- cuál fue la trayectoria;
- cuál fue el outcome;
- cuándo ocurrió;
- qué `execution_id` la identifica.

La evidencia de runtime debe responder a las preguntas de JALÓN 3.

Si ambas pertenecen a la misma ejecución experimental, se relacionan mediante una correlación explícita; no se supone identidad por proximidad temporal.

---

# 13. Installation ≠ execution ≠ benchmark ≠ measurement

La integración Hermes adopta expresamente esta separación:

```text
integración declarada
       ↓
instalación disponible
       ↓
arranque verificado
       ↓
tarea ejecutada
       ↓
benchmark agentivo
       ↓
medición LEONES
       ↓
evidencia verificada
```

Que Hermes pueda instalarse o que exista una receta de integración **no demuestra** que:

- el entorno arranque;
- el modelo seleccionado funcione;
- A01 funcione;
- las herramientas funcionen;
- el rendimiento sea aceptable;
- la medición sea reproducible.

Esta distinción es obligatoria para el selector/harness V1.2.

---

# 14. Qué queda fuera de RC1

Para mantener el objetivo mínimo, RC1 **no** intentará:

- soportar todos los proveedores de Hermes;
- evaluar todos los toolsets;
- evaluar Telegram/Discord/Slack/WhatsApp/Signal;
- evaluar cron/scheduling como producto;
- evaluar todo el sistema de memoria a largo plazo;
- medir todas las modalidades de voz/visión;
- integrar simultáneamente todos los runtimes de LEONES;
- convertir Hermes en una dependencia obligatoria de todo el proyecto;
- reproducir toda la arquitectura interna de Hermes.

RC1 necesita demostrar el **camino agentivo mínimo**, no certificar Hermes completo.

---

# 15. Gates específicos Hermes RC1

Hermes queda sujeto a los siguientes gates.

## H-R0 — Contract

Existe `hermes-agent.v1` y tests de contrato.

## H-R1 — Install

Hermes puede instalarse en el entorno objetivo siguiendo la ruta oficial o una receta versionada de LEONES.

## H-R2 — Boot

Hermes arranca y responde a una operación mínima.

## H-R3 — Model

Hermes utiliza exactamente el modelo/proveedor autorizado por el plan.

## H-R4 — Tools

Las herramientas de A01 se ejecutan y quedan registradas.

## H-R5 — A01

A01 completa una tarea reproducible bajo Hermes.

## H-R6 — Evidence

La trayectoria y el outcome generan evidencia normalizada.

## H-R7 — Correlation

La evidencia agentiva puede relacionarse con la evidencia de runtime cuando forman parte de la misma prueba.

## H-R8 — Repeat

La prueba puede repetirse produciendo un nuevo `execution_id` y sin depender de estado oculto de una ejecución anterior.

---

# 16. Orden de implementación

La integración se realizará en este orden y no al revés:

```text
1. contrato hermes-agent.v1
       ↓
2. adapter puro
       ↓
3. tests unitarios/contract
       ↓
4. runner Hermes mínimo
       ↓
5. boot real
       ↓
6. modelo autorizado
       ↓
7. tools A01
       ↓
8. trayectoria
       ↓
9. grader
       ↓
10. evidencia
       ↓
11. correlación runtime ↔ agente
       ↓
12. repetición física
       ↓
13. integración con recomendador
```

Hasta el punto 5–6 se debe trabajar preferentemente en GitHub/CI y fixtures.

Los puntos que exijan instalación, hardware, runtime local o herramientas reales se trasladan a Ubuntu únicamente cuando sean imprescindibles.

---

# 17. Definition of Done Hermes para RC1

Hermes se considera integrado en RC1 cuando:

- [ ] existe contrato `hermes-agent.v1`;
- [ ] existe adaptador probado;
- [ ] existe runner mínimo;
- [ ] Hermes arranca en el entorno objetivo;
- [ ] el modelo/proveedor utilizado coincide con el plan autorizado;
- [ ] A01 puede ejecutarse con Hermes;
- [ ] las tool calls quedan registradas;
- [ ] los errores quedan registrados;
- [ ] la trayectoria puede evaluarse;
- [ ] el outcome puede evaluarse;
- [ ] existe `execution_id`;
- [ ] existe evidencia normalizada;
- [ ] runtime y agente pueden correlacionarse;
- [ ] una segunda ejecución produce nueva evidencia;
- [ ] ningún dato estimado se promociona automáticamente a medido;
- [ ] los tests de RC1 siguen verdes.

---

# 18. Efecto sobre el plan RC1

La introducción de Hermes modifica el vertical slice, pero **no reabre JALÓN 1, JALÓN 2 ni JALÓN 3**.

La arquitectura congelada queda conceptualmente así:

```text
                ┌───────────────┐
                │   HARDWARE    │
                └───────┬───────┘
                        ↓
                ┌───────────────┐
                │   SELECTION   │
                └───────┬───────┘
                        ↓
                ┌───────────────┐
                │ RUNTIME GATE  │
                └───────┬───────┘
                        ↓
              ┌─────────┴─────────┐
              ↓                   ↓
        llama.cpp             HERMES
       inferencia            agent harness
              │                   │
              └─────────┬─────────┘
                        ↓
                   A01 / TASK
                        ↓
                 GRADING + EVIDENCE
                        ↓
                 JALÓN 3 MEASUREMENT
                        ↓
                  RECOMMENDATION
```

La clave es que **Hermes añade capacidad agéntica al vertical slice sin convertirse en una nueva autoridad de verdad**.

---

# 19. Resultado esperado de RC1

Al finalizar RC1 queremos poder demostrar algo mucho más potente que una demo:

> **LEONES recibe un hardware y una tarea agentiva; selecciona un candidato; autoriza un stack; ejecuta Hermes con el modelo/runtime correspondiente; realiza las herramientas necesarias; evalúa la trayectoria; mide lo que realmente ocurrió; conserva evidencia y devuelve una recomendación explicable.**

Ese es el primer producto mínimo operativo.

Todo lo demás —más runtimes, más agentes, más modalidades, más benchmarks, más canales de Hermes, más automatización— queda después de que esta cadena sea real.

---

## Referencias oficiales

- [Hermes Agent — repositorio oficial](https://github.com/NousResearch/hermes-agent)
- [Hermes Agent — documentación oficial](https://hermes-agent.nousresearch.com/docs)
- [LEONES — Release Candidate 1](RELEASE-CANDIDATE-1.md)
- [LEONES — JALÓN 3: Protocolo de medición real](completed/JALON-3-MEASUREMENT-PROTOCOL.md)
