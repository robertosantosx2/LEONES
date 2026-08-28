# LEONES — Release Candidate 1: plan de ejecución hasta MANADA

> **Estado: PLAN NORMATIVO DE RC1**  
> **Punto de partida: JALÓN 3 cerrado**  
> **Objetivo: una versión mínima, operativa, reproducible, benchmarkeable y publicable de LEONES.**

Este documento complementa [`RELEASE-CANDIDATE-1.md`](RELEASE-CANDIDATE-1.md) y [`RELEASE-CANDIDATE-1-HERMES.md`](RELEASE-CANDIDATE-1-HERMES.md). No reabre JALÓN 1, JALÓN 2 ni JALÓN 3.

---

## 0. La meta real de RC1

RC1 no se considera terminada cuando "el código funciona".

Se considera terminada cuando LEONES puede recorrer, sobre una máquina real, un camino completo y conservar todo lo necesario para explicarlo:

```text
hardware real
    ↓
perfil hardware
    ↓
selección de modelo
    ↓
fit / restricciones
    ↓
runtime autorizado
    ↓
agent harness autorizado
    ↓
instalación / stack real
    ↓
tarea real
    ↓
benchmark
    ↓
medición física
    ↓
evidencia reproducible
    ↓
validación
    ↓
recomendación
    ↓
resultado estructurado
    ↓
publicación en MANADA
```

El objetivo de RC1 es, por tanto, **cerrar el primer circuito de conocimiento completo de LEONES**.

La definición de éxito no es "soportar muchas herramientas" sino:

> **una máquina → una selección → un stack → una tarea → una medición → una evidencia → una recomendación → una publicación.**

---

# 1. Arquitectura congelada

La arquitectura base queda congelada en este punto:

```text
                     LEONES
                       │
             ┌─────────┴─────────┐
             ↓                   ↓
        MODEL SELECTION       HARDWARE
             │                   │
             └─────────┬─────────┘
                       ↓
                RUNTIME GATE
                       ↓
             AGENT/HARNESS GATE
                       ↓
          ┌────────────┴────────────┐
          ↓                         ↓
      llama.cpp                  Hermes
    inference runtime          agent harness
          │                         │
          └────────────┬────────────┘
                       ↓
                    A01/task
                       ↓
                  benchmark
                       ↓
                 JALÓN 3
                       ↓
                   evidence
                       ↓
                 validation
                       ↓
                recommendation
                       ↓
                    MANADA
```

### Regla de separación

- **LEONES** decide y conserva procedencia.
- **LLMFit** ayuda al fit previo.
- **llama.cpp** proporciona la primera ruta de inferencia física canónica.
- **Hermes** proporciona la primera ruta agéntica canónica.
- **Osmantic ODS o Plenitude** se incorporan como stack/appliance de ejecución cuando uno de ellos pueda instalarse y validarse realmente.
- **JALÓN 3** sigue siendo la autoridad de medición física.
- **MANADA** es la superficie final de conocimiento/publicación.

Ningún stack externo puede convertirse en fuente de verdad simplemente porque su instalador funcione.

---

# 2. Dos niveles de integración de stack

RC1 debe distinguir dos cosas que pueden parecer iguales pero no lo son.

## Nivel A — integración directa

LEONES ejecuta su propio runtime/adaptador y mide directamente.

```text
LEONES → llama.cpp → modelo → medición
```

Este camino ya tiene la base de JALÓN 2–3.

## Nivel B — stack/appliance

LEONES instala o utiliza un stack externo que orquesta varios componentes.

```text
LEONES
   ↓
stack seleccionado
   ↓
servicios/runtime/harness
   ↓
modelo
   ↓
tarea
```

Aquí el stack debe ser tratado como **entorno de ejecución**, no como autoridad de rendimiento.

La medición final sigue teniendo que identificar qué runtime, modelo, configuración y hardware produjeron el resultado.

---

# 3. Osmantic ODS: candidato prioritario de integración

**Osmantic Deployment System (ODS)** queda incluido explícitamente en RC1 como candidato prioritario de instalación/appliance local.

Su documentación pública describe ODS como un stack local con instaladores para Linux, macOS y Windows, autodetección de hardware/GPU, selección de modelos, servicios opcionales y una ruta de instalación reproducible. También documenta artefactos de simulación de instaladores y un `release-gate`. citeturn0search2turn0search3

Referencia primaria:

- [`Osmantic/ODS`](https://github.com/Osmantic/ODS)
- documentación de soporte/plataformas;
- versiones conocidas/baselines;
- matriz de validación;
- artefactos de instalación.

### Qué debe demostrar LEONES

No basta con instalar ODS.

Debe demostrar:

1. instalación limpia;
2. detección del hardware real;
3. selección efectiva de modelo;
4. runtime realmente utilizado;
5. arranque del servicio;
6. ejecución de una inferencia;
7. ejecución de A01/Hermes cuando la ruta sea compatible;
8. captura de configuración;
9. medición física;
10. evidencia reproducible.

ODS documenta explícitamente que el throughput todavía requiere benchmark local después del primer lanzamiento; LEONES debe respetar esa separación. citeturn0search2

### Resultado esperado

```text
ODS installed
     ↓
ODS boot verified
     ↓
hardware detected
     ↓
model selected
     ↓
runtime identified
     ↓
A01 / benchmark
     ↓
JALÓN 3 evidence
```

---

# 4. Plenitude: segundo candidato de stack

**Plenitude** queda contemplado como segunda vía de instalación/integración cuando su identidad técnica, repositorio, versión y procedimiento de instalación estén fijados por LEONES.

La regla para incorporarlo es deliberadamente estricta:

> **No se añadirá una referencia ambigua a "Plenitude" como si fuese un producto ya identificado. Primero se fija el proyecto exacto, upstream, commit/release, licencia, plataforma y procedimiento de instalación.**

La búsqueda actual no permite identificar de forma inequívoca un repositorio público de software llamado simplemente "Plenitude" que deba convertirse en dependencia de RC1. Por tanto, RC1 conserva la vía abierta pero no inventa una integración.

Cuando el proyecto exacto quede identificado, deberá entrar por el mismo contrato que ODS:

```text
identity
  ↓
license
  ↓
version / commit
  ↓
install
  ↓
boot
  ↓
model/runtime detection
  ↓
A01
  ↓
benchmark
  ↓
evidence
```

Si Plenitude demuestra una ruta superior o complementaria a ODS, podrá convertirse en el stack principal de una ejecución RC1; si no, queda como integración posterior sin bloquear la entrega mínima.

---

# 5. Orden de trabajo: GitHub primero, Ubuntu sólo cuando sea imprescindible

El principio operativo de RC1 es:

> **Diseñar, contratar, probar y documentar en GitHub; instalar y medir físicamente sólo cuando la máquina real sea imprescindible.**

## Se hace primero en GitHub

- contratos;
- adaptadores;
- interfaces;
- manifests;
- versionado;
- tests unitarios;
- tests de contrato;
- fixtures;
- validadores;
- runners preparados;
- evidence schemas;
- benchmark definitions;
- documentación;
- CI;
- integración MANADA.

## Se reserva para Ubuntu

- instalación real de ODS/Plenitude;
- detección real del hardware;
- descarga/instalación real del modelo cuando sea necesaria;
- ejecución física;
- benchmark real;
- captura de sensores/memoria/energía si existe;
- evidencia de runtime real;
- validación final de A01.

Esto minimiza la intervención manual en Ubuntu.

---

# 6. Fases RC1

## RC1-0 — Freeze y baseline

### Objetivo

Partir exactamente del estado cerrado de JALÓN 3.

### Gate

- árbol limpio;
- branch sincronizada;
- contratos de JALÓN 3 intactos;
- tests verdes;
- documentación indexada.

### No tocar

JALÓN 1–3 salvo bug bloqueante.

---

## RC1-1 — Contrato del producto mínimo

### Construir

Un único recorrido canónico:

```text
hardware → selection → authorization → execution → evidence → recommendation
```

Debe existir un objeto/artefacto común que transporte:

- hardware;
- workload;
- model candidate;
- runtime;
- agent harness;
- configuration;
- authorization;
- execution identity;
- evidence references.

### Gate

Tests de contrato y E2E sintético.

**No Ubuntu.**

---

## RC1-2 — Hermes

Hermes entra como harness agéntico de referencia para A01, según [`RELEASE-CANDIDATE-1-HERMES.md`](RELEASE-CANDIDATE-1-HERMES.md).

### Construir primero

- `hermes-agent.v1`;
- adapter;
- runner;
- normalización de trayectoria;
- tool-call records;
- outcome;
- correlation con runtime evidence;
- tests con mocks/fixtures.

### Gate

Hermes puede ser seleccionado como harness sin contaminar el contrato de runtime.

**Todavía sin instalación física.**

---

## RC1-3 — LLMFit + selección realista

### Objetivo

Cerrar la preselección hardware-aware.

```text
hardware
  ↓
LLMFit / fit
  ↓
constraints
  ↓
model candidates
  ↓
runtime candidates
  ↓
agent candidate
```

### Gate

El selector produce un plan completo y explicable.

Debe distinguir:

- `estimated`;
- `reported`;
- `observed`;
- `measured`;
- `verified`.

**No Ubuntu.**

---

## RC1-4 — Stack installation bridge

Aquí aparecen **ODS y Plenitude**.

### Diseño

Crear un contrato abstracto de stack:

```text
stack.v1

id
name
upstream
version
commit
platform
installer
services
runtime_detection
model_detection
healthcheck
benchmark_entrypoint
```

### Adaptadores

```text
ods.v1
plenitude.v1
```

Un adaptador sólo debe describir y verificar la instalación; no inventar resultados de rendimiento.

### Gate sintético

Tests contra fixtures de:

- instalación correcta;
- versión incorrecta;
- runtime ausente;
- servicio caído;
- modelo no detectado;
- hardware incompatible.

**No Ubuntu todavía.**

---

# 7. Primer momento imprescindible de Ubuntu

Ubuntu sólo se necesita cuando los contratos anteriores estén verdes y haya que demostrar:

```text
stack installer
     ↓
real machine
     ↓
real hardware detection
     ↓
real runtime
```

### Procedimiento

No improvisar.

El runner debe recibir un plan ya generado por GitHub/LEONES y devolver evidencia.

```text
plan.json
   ↓
Ubuntu
   ↓
install/boot
   ↓
execution
   ↓
measurement
   ↓
evidence bundle
```

La intervención humana debe limitarse a:

- ejecutar el procedimiento;
- aceptar acciones inevitables del sistema;
- aportar credenciales sólo si son imprescindibles y nunca almacenarlas en evidencia;
- conservar el resultado.

---

# 8. RC1-5 — Instalación física ODS

### Primera opción

Instalar ODS en Ubuntu si el hardware/plataforma pertenece a una ruta soportada por su matriz vigente.

ODS documenta actualmente rutas Linux para NVIDIA, AMD/Strix Halo e Intel Arc, con diferentes niveles de soporte; las afirmaciones de release deben asociarse a hardware y versiones concretas. citeturn0search3

### Evidencia obligatoria

```text
ods-installation.json
ods-health.json
ods-runtime.json
ods-model.json
ods-hardware.json
```

Más:

- stdout/stderr relevante;
- versión/commit;
- configuración efectiva;
- timestamp;
- hash del manifest cuando proceda.

### Gate ODS-REAL

```text
INSTALL = PASS
BOOT = PASS
HARDWARE = PASS
RUNTIME = IDENTIFIED
MODEL = IDENTIFIED
INFERENCE = PASS
```

Sólo entonces puede pasar a benchmark.

---

# 9. RC1-6 — Instalación física Plenitude

Se ejecuta sólo después de fijar el upstream exacto y si su instalación es compatible con el hardware/objetivo de RC1.

### Gate

Exactamente el mismo que ODS:

```text
identity
install
boot
hardware
runtime
model
inference
```

### Decisión

Después de las pruebas:

- **ODS pasa y Plenitude no:** ODS es el stack RC1.
- **Plenitude pasa y ODS no:** Plenitude puede ser el stack RC1.
- **ambos pasan:** ambos quedan registrados y se comparan sólo bajo condiciones equivalentes.
- **ninguno pasa:** se mantiene el camino directo `llama.cpp + Hermes`; RC1 no queda bloqueada.

Esto evita que una integración externa convierta un proyecto mínimo en una dependencia frágil.

---

# 10. RC1-7 — Benchmark físico

Aquí comienza el benchmark real.

No debe empezar antes de que el stack esté identificado y sano.

## 10.1 Benchmark de runtime

Debe medir, cuando sea posible:

- TTFT;
- prompt processing/prefill;
- decode throughput;
- tokens/s;
- duración;
- memoria;
- VRAM;
- consumo/potencia si existe instrumentación fiable.

Siempre junto a:

- modelo;
- revisión;
- cuantización;
- contexto;
- prompt;
- warm-up;
- N de mediciones;
- runtime/version;
- hardware;
- comando;
- execution_id;
- timestamp;
- hashes.

JALÓN 3 sigue siendo el contrato de referencia.

---

# 11. Benchmark agentivo con Hermes

El segundo nivel mide la utilidad de la máquina, no sólo el runtime.

```text
Hermes
  ↓
A01
  ↓
tools
  ↓
trajectory
  ↓
grader
```

Registrar:

- tiempo total;
- turnos;
- tool calls;
- tool errors;
- recovery;
- resultado;
- score;
- artefactos.

### Regla

No sustituir el throughput por un score agéntico ni el score agéntico por throughput.

Son dimensiones diferentes.

---

# 12. Benchmark de stack

Cuando ODS o Plenitude estén instalados, la comparación debe separar:

```text
A. modelo/runtime
B. harness
C. stack/appliance
D. hardware
```

Por ejemplo:

| Capa | Variable |
|---|---|
| Hardware | CPU/GPU/RAM/VRAM |
| Modelo | identidad + quant |
| Runtime | llama.cpp/otro + versión |
| Harness | Hermes |
| Stack | ODS/Plenitude/directo |
| Task | A01 |
| Context | fijo |
| Prompt | fijo |
| N | fijo |

Sólo las celdas comparables pueden entrar en una comparación.

---

# 13. Inspiración metodológica externa: Osmantic/MMBT

La metodología de benchmarking de Osmantic es útil como referencia para RC1 porque separa explícitamente benchmarks de tareas de agente y caracterización del hardware, conserva artefactos, documenta límites y evita presentar una única tabla como verdad universal. citeturn0search0turn0search1

LEONES adoptará esas buenas prácticas sin copiar su metodología ni sus conclusiones:

- benchmark por workload;
- operating point explícito;
- hardware explícito;
- backend/runtime explícito;
- separación de benchmarks de agente y hardware;
- límites de validez;
- conservación de raw artifacts;
- reproducción de runs;
- failure modes como evidencia.

Esto encaja directamente con JALÓN 3.

---

# 14. Matriz mínima de benchmarks RC1

No necesitamos una matriz enorme.

### Celda mínima obligatoria

```text
1 hardware
×
1 modelo
×
1 quantización
×
1 runtime
×
1 harness
×
1 task
```

### Primera campaña recomendada

```text
Hardware real actual
   ×
Qwen pequeño ya validado
   ×
llama.cpp
   ×
Hermes
   ×
A01
```

Después:

```text
ODS
Plenitude
Direct
```

sólo si las rutas son técnicamente comparables.

### Repeticiones

La primera medición sirve para detectar funcionamiento.

Las siguientes sirven para caracterizar variación.

El N final debe quedar fijado en el protocolo de campaña antes de ejecutar la tanda.

---

# 15. Quality gates de benchmark

Una celda sólo puede publicarse como **measured** si:

- el modelo está identificado;
- la cuantización está identificada;
- el runtime está identificado;
- el hardware está identificado;
- la configuración está completa;
- el execution_id existe;
- el timestamp existe;
- el resultado procede de una ejecución real;
- el artefacto de evidencia está conservado;
- la validación del contrato pasa.

Una celda pasa a **verified** sólo después del quality gate correspondiente.

Una celda fallida no se elimina:

```text
FAIL
  ↓
failure evidence
  ↓
known limitation / backend status
```

Los fallos son datos.

---

# 16. Reproducción

Cada benchmark publicado debe poder reconstruirse desde un receipt.

El receipt debe apuntar a:

- commit LEONES;
- commit/runtime externo;
- modelo/revisión;
- artefacto/hash;
- hardware;
- configuración;
- comando;
- benchmark version;
- prompt/task version;
- execution_id;
- evidencia.

El objetivo es que otra máquina compatible pueda saber exactamente qué se hizo aunque no pueda reproducir exactamente el mismo rendimiento.

---

# 17. Preparación de publicación en MANADA

La publicación no debe ser una copia manual de resultados.

Debe existir un **publication bridge**:

```text
validated benchmark evidence
             ↓
      publication record
             ↓
          MANADA
```

El registro mínimo debe conservar:

- identidad del modelo;
- runtime;
- hardware;
- stack;
- workload;
- métricas;
- estado epistemológico;
- execution_id;
- evidencia;
- fecha;
- versión del benchmark;
- enlace al artefacto/receipt.

---

# 18. Qué significa "publicado en MANADA"

RC1 no termina al generar JSON local.

La publicación mínima debe conseguir que MANADA pueda presentar:

```text
Modelo
Runtime
Hardware
Task
Benchmark
Resultado
Estado de evidencia
Limitaciones
Procedencia
```

Y debe ser imposible confundir:

```text
estimated
reported
observed
measured
verified
```

La capa de presentación puede resumir, pero no alterar la semántica de la evidencia.

---

# 19. Publicación de resultados negativos

MANADA debe publicar también:

- runtime que no arranca;
- modelo que no cabe;
- backend que falla;
- benchmark incompleto;
- tool call que falla;
- timeout;
- ODS/Plenitude no compatibles;
- medición descartada por incumplir el contrato.

El resultado:

> **"no funciona en estas condiciones"**

es conocimiento útil y evita que el recomendador vuelva a probar el mismo camino.

---

# 20. Release Candidate 1 — Definition of Done

RC1 queda cerrada cuando se cumplen todos los puntos siguientes.

### Producto

- [ ] perfil hardware operativo;
- [ ] selección operativa;
- [ ] runtime gate operativo;
- [ ] llama.cpp físico operativo;
- [ ] Hermes integrado;
- [ ] A01 reproducible;
- [ ] recomendación explicable.

### Stack

- [ ] contrato `stack.v1`;
- [ ] ODS evaluado físicamente;
- [ ] Plenitude identificado/evaluado o formalmente diferido por falta de upstream verificable;
- [ ] al menos un stack externo realmente instalado y validado **o** justificación documentada de por qué el camino directo es suficiente para RC1.

### Benchmark

- [ ] benchmark runtime;
- [ ] benchmark agentivo;
- [ ] protocolo fijado;
- [ ] N fijado;
- [ ] evidencia conservada;
- [ ] fallos conservados;
- [ ] receipts reproducibles.

### Publicación

- [ ] publication schema;
- [ ] bridge LEONES → MANADA;
- [ ] primer resultado publicado;
- [ ] evidencia enlazada;
- [ ] límites publicados;
- [ ] resultado negativo si existe, publicado como tal.

### Calidad

- [ ] CI verde;
- [ ] tests completos verdes;
- [ ] diff check limpio;
- [ ] árbol limpio;
- [ ] commits sincronizados;
- [ ] documentación enlazada desde README;
- [ ] release candidate tag/commit fijado.

---

# 21. Secuencia exacta de ejecución

La secuencia recomendada queda congelada así:

```text
FASE 0
Freeze JALÓN 3
   ↓
FASE 1
Producto mínimo + contratos
   ↓
FASE 2
Hermes adapter + tests
   ↓
FASE 3
LLMFit + selection
   ↓
FASE 4
Stack contract
   ↓
FASE 5
ODS/Plenitude adapters + fixtures
   ↓
FASE 6
Ubuntu: instalar ODS
   ↓
FASE 7
Ubuntu: instalar/evaluar Plenitude si procede
   ↓
FASE 8
Benchmark runtime
   ↓
FASE 9
Benchmark Hermes/A01
   ↓
FASE 10
Correlacionar evidence
   ↓
FASE 11
Validar/promover
   ↓
FASE 12
Publication bridge
   ↓
MANADA
   ↓
RC1 RELEASE
```

**No saltar directamente al benchmark.** La arquitectura y los contratos deben estar cerrados antes de consumir tiempo de Ubuntu.

---

# 22. Lo que deliberadamente NO bloquea RC1

No bloquean RC1:

- soportar todos los runtimes;
- soportar todas las GPU;
- soportar todas las plataformas;
- construir una gran interfaz web;
- integrar todas las funciones de Hermes;
- ejecutar una batería masiva de modelos;
- reproducir benchmarks externos completos;
- resolver toda la economía/TCO;
- construir un leaderboard universal.

RC1 necesita una **prueba vertical completa**, no cobertura total.

---

# 23. La primera demostración pública de RC1

La demo ideal será una sola orden o flujo equivalente que permita contar esta historia:

```text
"Esta es mi máquina."
        ↓
LEONES la perfila.
        ↓
"Para A01, estos candidatos encajan."
        ↓
LEONES selecciona uno.
        ↓
"Este runtime/harness está autorizado."
        ↓
Se ejecuta Hermes.
        ↓
Se ejecuta la tarea real.
        ↓
Se mide físicamente.
        ↓
Se conserva la trayectoria.
        ↓
Se valida la evidencia.
        ↓
LEONES explica la recomendación.
        ↓
MANADA publica el resultado.
```

Ese recorrido es el verdadero producto mínimo.

---

# 24. Principio rector final

La RC1 debe preferir:

> **una medición real bien documentada a cien integraciones teóricas.**

Y, después de JALÓN 3:

> **una cadena completa reproducible vale más que otro subsistema aislado.**

Por eso el final de RC1 no es la instalación de Hermes, ODS o Plenitude.

El final de RC1 es:

```text
REAL HARDWARE
   ↓
REAL MODEL
   ↓
REAL RUNTIME
   ↓
REAL AGENT
   ↓
REAL TASK
   ↓
REAL BENCHMARK
   ↓
REAL EVIDENCE
   ↓
REAL RECOMMENDATION
   ↓
REAL MANADA PUBLICATION
```

Ese es el circuito que convierte LEONES de arquitectura preparada en **producto operativo mínimo**.
