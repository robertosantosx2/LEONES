# LEONES — Release Candidate 1

> **Estado: PLAN CONGELADO**  
> **Objetivo: obtener una versión mínima, operativa, reproducible y demostrable de LEONES.**

**Fecha de congelación:** 2026-08-28  
**Punto de partida:** JALÓN 3 cerrado  
**Rama de trabajo:** `jalon3-measurement-protocol`

---

## 1. Propósito de RC1

RC1 no pretende terminar todo LEONES.

Pretende hacer algo más importante: **cerrar una primera versión pequeña que funcione de verdad de principio a fin**.

La pregunta que RC1 debe poder contestar es:

> **Dado un hardware y una tarea, ¿puede LEONES producir una recomendación técnicamente justificada, ejecutar un runtime autorizado, medir una ejecución real y conservar evidencia suficiente para explicar por qué recomienda ese resultado?**

RC1 será, por tanto, una versión de producto mínima y no un inventario completo de todas las capacidades del proyecto.

La regla de alcance es:

> **menos superficie, más realidad.**

---

# 2. Qué significa "operativa"

LEONES RC1 será considerada operativa cuando exista un camino canónico que pueda ejecutarse sin intervención arquitectónica manual entre sus etapas principales.

```text
hardware
   ↓
perfil hardware
   ↓
selección de candidatos
   ↓
plan runtime autorizado
   ↓
runtime local
   ↓
ejecución real
   ↓
medición
   ↓
evidencia
   ↓
validación
   ↓
recomendación explicable
```

No es suficiente que cada componente exista por separado. El criterio de RC1 es que **la cadena completa sea coherente**.

---

# 3. Punto de partida congelado

RC1 parte de una base que no debe volver a diseñarse salvo que aparezca un defecto bloqueante.

## 3.1 JALÓN 1

JALÓN 1 queda tratado como infraestructura base ya cerrada: CI, contratos y merge de la base correspondiente.

## 3.2 JALÓN 2

JALÓN 2 queda cerrado como evidencia física de ejecución con llama.cpp.

La evidencia física de referencia demostró el recorrido runtime → ejecución → medición → conservación de evidencia.

## 3.3 JALÓN 3

JALÓN 3 queda cerrado como **contrato operativo de medición real**.

La auditoría final registrada antes de su cierre obtuvo:

- **256 tests pasando**;
- `git diff --check` limpio;
- árbol de trabajo limpio;
- `HEAD` idéntico a `origin/jalon3-measurement-protocol`;
- contrato por defecto de llama.cpp verificado;
- contrato acotado de llama.cpp verificado con `--simple-io`, `--single-turn`, contexto y límite de salida;
- artefacto A01 real validado;
- evidencia marcada como `measured` y `measurement_kind = real`;
- consistencia de hardware entre evidencia y plan de ejecución.

La documentación canónica de JALÓN 3 es [`completed/JALON-3-MEASUREMENT-PROTOCOL.md`](completed/JALON-3-MEASUREMENT-PROTOCOL.md).

**Decisión:** no reabrir JALÓN 1–3 para ampliar RC1. Las mejoras posteriores deben entrar como trabajo de RC1 o de una versión posterior, según impacto.

---

# 4. El producto mínimo que queremos construir

RC1 debe ofrecer cuatro capacidades visibles y verificables.

### A. Entender la máquina

LEONES debe obtener un perfil hardware suficientemente bueno para tomar decisiones iniciales:

- CPU;
- arquitectura;
- núcleos/hilos cuando estén disponibles;
- RAM;
- GPU cuando esté disponible;
- VRAM cuando esté disponible;
- sistema operativo;
- capacidades adicionales relevantes cuando puedan observarse de forma fiable.

Cuando un dato no pueda medirse o detectarse con fiabilidad, debe conservarse como `unknown` o ausente. **No se inventa.**

### B. Seleccionar un candidato

LEONES debe ser capaz de producir una lista o candidato seleccionado teniendo en cuenta, como mínimo:

- tarea/workload;
- hardware;
- memoria disponible;
- contexto solicitado;
- runtime requerido o compatible;
- cuantización/configuración;
- evidencia disponible;
- restricciones de ejecución.

La selección puede utilizar estimaciones, pero debe conservar su naturaleza.

### C. Ejecutar y medir

Cuando el candidato esté autorizado, LEONES debe poder:

1. preparar el plan;
2. invocar el runtime mediante el adaptador autorizado;
3. ejecutar la tarea;
4. recoger el resultado y las métricas observadas;
5. asociar la ejecución con un `execution_id`;
6. conservar timestamps y configuración;
7. generar evidencia normalizada;
8. validar el resultado.

### D. Explicar la recomendación

La salida mínima de RC1 debe poder explicar:

- qué modelo se recomienda;
- con qué runtime;
- con qué configuración;
- para qué hardware;
- qué evidencia sustenta la recomendación;
- si el dato es estimado, observado, medido o verificado;
- y qué límites o incertidumbres permanecen.

---

# 5. Arquitectura mínima de RC1

El sistema se organizará alrededor de seis capas. No se añadirán capas nuevas salvo necesidad demostrada.

```text
┌──────────────────────────────────────┐
│ 1. INPUT                             │
│ hardware + tarea + preferencias      │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│ 2. SELECTION                         │
│ candidatos + fit + restricciones     │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│ 3. RUNTIME AUTHORIZATION             │
│ plan + runtime + configuración       │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│ 4. EXECUTION                         │
│ ejecución local real                 │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│ 5. EVIDENCE                          │
│ medición + hardware + procedencia    │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│ 6. RECOMMENDATION                    │
│ resultado explicable                 │
└──────────────────────────────────────┘
```

Atlas, LLMFit, CABE/RULA, fuentes externas, precios y otros subsistemas alimentan estas capas, pero **no deben convertirse todos en bloqueadores del primer producto operativo**.

---

# 6. Alcance funcional de RC1

## 6.1 Perfilado de hardware

### Objetivo

Convertir la máquina local en un perfil normalizado consumible por el selector.

### Aceptación

Debe existir una función/CLI que produzca un perfil estable y serializable y que:

- no dependa de texto humano ambiguo;
- diferencie valores conocidos de desconocidos;
- no convierta una estimación en una observación;
- pueda ser utilizado directamente por la selección.

### No hacer todavía

No intentar soportar todas las GPU, aceleradores, sensores de energía y métricas de plataforma del mercado en RC1.

---

## 6.2 Selección de modelos

### Objetivo

Partiendo del hardware y del workload, obtener candidatos razonables antes de ejecutar.

### Orden lógico

```text
hardware
  ↓
restricciones duras
  ↓
fit / memoria / contexto
  ↓
runtime compatible
  ↓
evidencia disponible
  ↓
ranking de candidatos
```

### Regla

La selección **no debe afirmar que un modelo funciona físicamente solo porque encaja en una estimación**.

La salida debe distinguir:

- candidato estimado;
- candidato autorizado para ejecución;
- resultado medido;
- resultado verificado.

---

## 6.3 LLMFit como preselector

LLMFit queda integrado en RC1 únicamente en el papel que le corresponde: **estimación inicial de model fit hardware-aware**.

No será fuente de verdad de rendimiento.

```text
hardware
   ↓
LLMFit / fit estimado
   ↓
LEONES selection
   ↓
runtime autorizado
   ↓
medición LEONES
```

Si la integración no resulta imprescindible para cerrar la cadena mínima, puede quedar como señal opcional sin bloquear la RC1. La prioridad es el camino funcional, no la integración por sí misma.

Referencia documental: [`sources/LLMFIT.md`](sources/LLMFIT.md) y [`integrations/LLMFIT/README.md`](integrations/LLMFIT/README.md).

---

# 7. Runtime mínimo: llama.cpp

RC1 utilizará **llama.cpp como primer runtime físico canónico**.

No se ampliará simultáneamente a todos los runtimes.

La razón es operativa: JALÓN 2 y JALÓN 3 ya han demostrado el camino físico con llama.cpp y existe un adaptador y un runner sometidos a contratos y tests.

El contrato mínimo de ejecución debe garantizar:

- ejecutable explícito/autorizado;
- modelo explícito;
- prompt explícito;
- contexto explícito cuando corresponda;
- límite de generación explícito;
- ejecución no interactiva cuando el protocolo lo exija;
- captura de stdout/stderr;
- código de salida;
- identificación del runtime;
- identificación de la ejecución;
- captura de la medición observada.

La forma exacta del comando debe seguir el adaptador y los tests existentes, no una nueva convención paralela.

---

# 8. Protocolo de medición RC1

JALÓN 3 ya fija el contrato. RC1 debe **usarlo**, no redefinirlo.

Como mínimo, cada medición física debe poder asociarse con:

### Identidad del modelo

- `model_id`/nombre;
- revisión o identidad concreta cuando esté disponible;
- cuantización;
- artefacto;
- tamaño y hash cuando formen parte del contrato aplicable.

### Configuración

- contexto;
- límite de salida;
- prompt/protocolo;
- warm-up;
- número de mediciones;
- parámetros relevantes del runtime.

### Runtime

- nombre;
- versión cuando esté disponible;
- adaptador;
- comando ejecutado;
- entorno de ejecución.

### Hardware

- CPU;
- RAM;
- GPU/VRAM cuando estén disponibles;
- sistema operativo;
- demás campos soportados por el perfil hardware.

### Resultado

- throughput observado;
- TTFT u otras métricas solo cuando el runtime las produzca de forma fiable;
- duración;
- código de salida;
- estado de ejecución;
- `execution_id`;
- timestamp UTC;
- evidencia asociada.

La regla es:

> **Si no se observó, no se etiqueta como medido.**

---

# 9. Evidencia y procedencia

RC1 debe tratar la evidencia como un producto de primera clase.

## 9.1 Estados semánticos

Se mantendrá la separación ya establecida:

| Estado | Significado |
|---|---|
| `estimated` | cálculo o inferencia técnica |
| `reported` | dato declarado por una fuente externa |
| `observed` | configuración o comportamiento observado |
| `measured` | ejecución física medida por LEONES |
| `verified` | resultado que superó el quality gate correspondiente |
| `unknown` | todavía no demostrado |

Nunca debe producirse la promoción implícita:

```text
reported → measured
estimated → measured
observed → verified
```

Cada promoción requiere evidencia y validación correspondientes.

## 9.2 Artefactos

RC1 debe conservar, según el contrato aplicable:

- registro de ejecución;
- registro de benchmark/evidencia;
- logs relevantes;
- identidad del modelo;
- hardware;
- configuración;
- timestamps;
- identificador de ejecución;
- hashes de artefactos cuando estén definidos por el contrato.

---

# 10. A01 como prueba vertical

La tarea agentiva **A01** será el principal vertical slice de RC1.

No se trata de crear una batería gigantesca de agentes antes de tener producto.

A01 sirve para demostrar que LEONES puede recorrer:

```text
selección
   ↓
plan
   ↓
runtime
   ↓
modelo
   ↓
tarea agentiva
   ↓
herramientas
   ↓
resultado
   ↓
grading
   ↓
medición
   ↓
evidencia
```

La referencia real ya validada debe conservarse como evidencia histórica, no reutilizarse como si fuera una medición universal.

RC1 debe ser capaz de repetir el flujo bajo el contrato vigente y producir un nuevo `execution_id` para cada ejecución física.

---

# 11. Recomendador mínimo

El recomendador de RC1 no necesita resolver toda la economía de IA.

Debe responder de forma determinista a una pregunta acotada:

> **¿Cuál es el mejor candidato disponible para esta tarea en este hardware bajo estas restricciones?**

La recomendación mínima debe utilizar, cuando estén disponibles:

1. compatibilidad hardware;
2. memoria/contexto;
3. runtime compatible;
4. evidencia de calidad;
5. rendimiento medido;
6. estado de apertura/evidencia relevante;
7. restricciones del usuario.

## Prioridad de evidencia

Cuando existan resultados físicos comparables, RC1 debe preferirlos frente a simples estimaciones de rendimiento.

Ejemplo conceptual:

```text
medido + comparable
        >
verificado de fuente primaria
        >
observado
        >
estimado
        >
unknown
```

Esto no significa que una medición aislada gane siempre a toda fuente externa; significa que el origen y las condiciones deben formar parte explícita de la decisión.

---

# 12. CABE/RULA

CABE/RULA queda como capa de interpretación operativa del throughput.

El número continuo debe conservarse siempre.

```text
tokens/s real
      ↓
clasificación CABE/RULA
      ↓
interpretación para usuario
```

RC1 no debe convertir CABE/RULA en un sustituto del benchmark.

---

# 13. Interfaz mínima de usuario

La RC1 no necesita una aplicación web completa para ser válida.

Debe existir, como mínimo, una interfaz de uso clara, preferentemente CLI o una superficie web mínima ya existente, que permita:

1. identificar hardware;
2. seleccionar/recibir workload;
3. obtener candidatos;
4. seleccionar uno;
5. ejecutar si está autorizado;
6. mostrar resultado;
7. mostrar evidencia/procedencia.

La interfaz debe evitar presentar una estimación como una garantía.

Una salida ideal de RC1 tendrá conceptualmente esta forma:

```text
RECOMENDACIÓN LEONES
────────────────────────────────
Modelo:       <modelo>
Runtime:      llama.cpp
Cuantización: <quant>
Hardware:     <hardware>
Contexto:     <context>

Fit:          <estimated/observed>
Rendimiento:  <measured tok/s>
CABE/RULA:    <categoría>

Evidencia:    <execution_id>
Estado:       measured / verified

Limitaciones:
<qué no se ha demostrado>
```

---

# 14. Qué queda fuera de RC1

Para evitar que RC1 se convierta en otro ciclo infinito de arquitectura, quedan explícitamente fuera del camino crítico:

- soporte físico completo de vLLM;
- SGLang;
- MLX/MLX-LM;
- ExLlama;
- OpenVINO;
- ONNX Runtime GenAI;
- TensorRT-LLM;
- integración completa de todas las plataformas macOS/Windows/Linux;
- batería exhaustiva de benchmarks;
- sistema económico/TCO completo;
- cobertura exhaustiva de precios;
- ingestión masiva de todo el ecosistema;
- UI web definitiva;
- sistema distribuido de ejecución;
- medición energética universal;
- soporte de todos los aceleradores;
- automatización de todo el descubrimiento diario;
- publicación de un ranking global universal.

Estos elementos pueden continuar desarrollándose en paralelo, pero **no bloquean RC1** salvo que una dependencia concreta resulte imprescindible para el camino mínimo.

---

# 15. Segunda oleada de runtimes

Los contratos/adaptadores ya preparados para la segunda oleada se consideran **arquitectura futura preparada**, no trabajo que deba ejecutarse ahora.

Orden previsto después de RC1:

```text
RC1 / llama.cpp
      ↓
vLLM
      ↓
SGLang
      ↓
MLX / MLX-LM
      ↓
ExLlama
      ↓
OpenVINO
      ↓
ONNX Runtime GenAI
      ↓
TensorRT-LLM
```

Cada runtime futuro deberá demostrar el mismo contrato de selección → autorización → ejecución → medición → evidencia antes de entrar en la superficie de recomendaciones físicas.

---

# 16. Fases de ejecución hacia RC1

## RC1-A — Congelar base

### Objetivo

Convertir JALÓN 3 cerrado en base inmutable de trabajo.

### Acciones

- no modificar contratos cerrados sin causa bloqueante;
- registrar esta hoja de ruta;
- registrar el estado del repositorio;
- identificar el camino canónico;
- eliminar duplicaciones que interfieran con dicho camino.

### Gate

- árbol limpio;
- tests verdes;
- documentación navegable;
- JALÓN 3 localizable desde documentación principal.

---

## RC1-B — Cerrar el vertical slice CLI/E2E

### Objetivo

Conectar las piezas existentes en un único recorrido ejecutable.

### Acciones

- entrada de hardware/workload;
- selección;
- plan autorizado;
- runner llama.cpp;
- captura de resultado;
- evidencia;
- recomendación.

### Gate

Una ejecución desde el punto de entrada hasta la recomendación sin editar manualmente artefactos intermedios.

---

## RC1-C — Robustecer evidencia

### Objetivo

Evitar que una ejecución exitosa pueda generar una recomendación sin procedencia suficiente.

### Acciones

- validar identidad;
- validar hardware;
- validar runtime;
- validar `execution_id`;
- validar timestamps;
- validar estado `measured`;
- rechazar evidencia incompleta cuando el contrato lo exija.

### Gate

Tests de aceptación positivos y negativos.

---

## RC1-D — Repetibilidad física

### Objetivo

Demostrar que el camino no depende de una ejecución histórica concreta.

### Acciones

- ejecutar varias veces;
- conservar cada `execution_id`;
- conservar cada medición individual;
- producir resumen sin destruir los datos originales;
- comprobar que hardware/configuración son coherentes.

### Gate

El sistema produce evidencia nueva y trazable en cada ejecución.

---

## RC1-E — Recomendación explicable

### Objetivo

Transformar la evidencia en una recomendación comprensible para una persona.

### Acciones

- mostrar modelo;
- runtime;
- configuración;
- hardware;
- rendimiento;
- procedencia;
- límites;
- alternativa si existe.

### Gate

Un tercero puede leer la salida y reconstruir por qué se hizo la recomendación.

---

## RC1-F — Higiene y documentación

### Objetivo

Convertir la implementación en un candidato publicable.

### Acciones

- eliminar artefactos accidentales;
- revisar enlaces internos;
- revisar README;
- revisar documentación de ejecución;
- revisar nombres de contratos;
- comprobar que no hay instrucciones obsoletas;
- ejecutar suite completa;
- ejecutar `git diff --check`;
- comprobar sincronización con remoto.

### Gate

Repositorio limpio y documentación navegable de extremo a extremo.

---

# 17. Definition of Done de RC1

RC1 **NO** estará terminada porque haya muchos tests o muchos adaptadores.

Estará terminada cuando se cumplan simultáneamente estas condiciones:

### DOD-01 — Instalación/arranque

Un usuario con el entorno soportado puede iniciar el flujo siguiendo una documentación corta y reproducible.

### DOD-02 — Hardware

LEONES puede producir un perfil hardware consumible por el selector.

### DOD-03 — Selección

Existe al menos un camino de selección que produce un candidato y explica sus restricciones principales.

### DOD-04 — Autorización

La ejecución real solo ocurre a través de un plan/runtime autorizado.

### DOD-05 — Runtime

llama.cpp puede ejecutar el candidato mediante el adaptador canónico.

### DOD-06 — Medición

La ejecución produce métricas observadas bajo el contrato JALÓN 3.

### DOD-07 — Evidencia

Cada ejecución física produce evidencia trazable y un `execution_id` único.

### DOD-08 — Validación

La evidencia inválida no puede promocionarse como resultado medido/verified.

### DOD-09 — Recomendación

El sistema puede transformar el resultado en una recomendación explicable.

### DOD-10 — Repetibilidad

El flujo puede repetirse sin editar manualmente la evidencia generada.

### DOD-11 — CI

La suite completa permanece verde.

### DOD-12 — Documentación

README y documentación canónica permiten localizar el flujo, los contratos y el protocolo de medición.

### DOD-13 — Limpieza

El repositorio termina limpio, sin cambios no registrados ni artefactos temporales.

---

# 18. Gates técnicos

El camino hacia RC1 se considera bloqueado si falla cualquiera de los siguientes gates.

```text
G0  Base congelada
 ↓
G1  Tests verdes
 ↓
G2  Hardware profile válido
 ↓
G3  Candidate/selection válido
 ↓
G4  Runtime plan autorizado
 ↓
G5  Ejecución física real
 ↓
G6  Evidence válida
 ↓
G7  Recomendación reproducible
 ↓
G8  Documentación navegable
 ↓
RC1
```

## Principio de bloqueo

Un resultado de benchmark no debe saltarse G2–G4.

Una recomendación no debe saltarse G6.

Una cifra `measured` no debe existir sin una ejecución física trazable.

---

# 19. Pruebas mínimas

La suite debe cubrir cuatro clases.

## Contratos

Comprueban que las estructuras y estados semánticos no se rompen.

## Unitarias

Comprueban funciones puras: selección, parsing, validación, adaptación, clasificación.

## Integración

Comprueban el recorrido entre componentes.

## E2E / físico

Comprueban el recorrido completo con runtime real cuando el entorno disponible lo permite.

No todo test físico debe ejecutarse en CI. La ejecución física se conserva como evidencia independiente y reproducible.

---

# 20. Política de cambios durante RC1

RC1 necesita disciplina de alcance.

## Se acepta

- correcciones de bugs;
- endurecimiento de validadores;
- mejoras de documentación;
- eliminación de duplicaciones;
- automatización que reduzca intervención manual;
- mejoras de trazabilidad;
- mejoras necesarias para repetir el camino E2E.

## Se difiere

- nuevas arquitecturas no necesarias;
- nuevos runtimes físicos;
- cambios de contrato por comodidad;
- nuevas taxonomías sin consumidor;
- nuevas fuentes sin impacto en el vertical slice;
- rediseño de la UI;
- optimizaciones prematuras.

## Se bloquea especialmente

Cualquier cambio que permita que un dato estimado o reportado aparezca como medido sin evidencia física equivalente.

---

# 21. Estrategia de commits

Durante RC1 se recomienda mantener commits pequeños y semánticos.

Ejemplos:

```text
feat: connect hardware profile to selection pipeline
feat: close canonical llama.cpp execution path
feat: promote validated runtime evidence to recommendation
fix: reject incomplete measured evidence
refactor: remove duplicate runtime execution path
test: add RC1 end-to-end acceptance gate
docs: document RC1 operational flow
```

Evitar commits que mezclen arquitectura, documentación y cambios no relacionados cuando no sea necesario.

---

# 22. Estrategia de ramas

La rama de JALÓN 3 debe tratarse como la base congelada del contrato de medición.

El trabajo de producto RC1 debería desarrollarse en una rama específica de RC1, nacida de esta base una vez registrada la hoja de ruta.

Propuesta:

```text
jalon3-measurement-protocol
              │
              └── rc1-minimal-operational
                         │
                         ├── implementación
                         ├── tests
                         └── documentación
```

Al terminar, RC1 debe integrarse mediante el mecanismo de revisión habitual del repositorio.

---

# 23. Qué debe ejecutarse en Ubuntu y qué no

Una de las decisiones operativas de este proyecto es minimizar el trabajo manual sobre el host físico.

## Puede hacerse sin Ubuntu

- diseño de contratos;
- documentación;
- tests unitarios;
- validadores;
- selección simulada;
- integración de adaptadores;
- revisión de artefactos ya existentes;
- CI;
- limpieza de README y documentación.

## Requiere el host físico

- detección real del hardware;
- ejecución del runtime local;
- benchmark físico;
- medición de throughput/tiempos;
- captura de recursos que solo existen en el host;
- generación de evidencia que dependa de esa ejecución.

Por tanto, la estrategia RC1 es:

> **hacer todo lo posible en GitHub/CI y reservar Ubuntu para aquello que solo puede demostrar el hardware real.**

---

# 24. Artefactos que RC1 debe dejar

Al cerrar RC1 debe ser posible localizar:

```text
docs/RELEASE-CANDIDATE-1.md
        │
        ├── arquitectura mínima
        ├── gates
        ├── Definition of Done
        └── alcance congelado

runtime-selection / plan
        │
        └── ejecución autorizada

artifacts/
        │
        ├── runtime execution
        ├── benchmark evidence
        └── summaries

README.md
        │
        └── entrada clara a RC1
```

Los artefactos físicos históricos no deben sobrescribirse para hacerlos coincidir con nuevas ejecuciones.

---

# 25. Riesgos principales

## R1 — Scope creep

**Riesgo:** intentar terminar todos los runtimes, benchmarks y subsistemas antes de publicar una primera versión.

**Mitigación:** RC1 se define por un único vertical slice operativo.

## R2 — Confundir fit con rendimiento

**Riesgo:** que LLMFit o una estimación de memoria se interprete como benchmark.

**Mitigación:** estados semánticos y evidencia separados.

## R3 — Evidencia histórica reutilizada

**Riesgo:** usar una ejecución antigua como si fuera una ejecución actual.

**Mitigación:** `execution_id`, timestamp y artefactos inmutables.

## R4 — Multiplicación de runners

**Riesgo:** varias rutas de ejecución producen resultados incompatibles.

**Mitigación:** un adaptador/runner canónico por runtime.

## R5 — Hardware incompleto

**Riesgo:** seleccionar usando datos que no representan la máquina real.

**Mitigación:** distinguir campos detectados, desconocidos y estimados.

## R6 — UI antes que producto

**Riesgo:** invertir en presentación antes de cerrar el pipeline.

**Mitigación:** CLI/E2E primero; UI después.

---

# 26. Resultado esperado de RC1

El resultado no será "LEONES terminado".

Será esto:

> **LEONES puede recibir una máquina, seleccionar un candidato razonable, autorizar un runtime, ejecutar una tarea real, medirla, conservar evidencia y devolver una recomendación explicable.**

Ese resultado convierte LEONES de una colección de componentes en un **producto mínimo operativo**.

---

# 27. Evolución después de RC1

Una vez que RC1 esté cerrada, el proyecto podrá ampliar el camino sin perder su núcleo:

```text
                    RC1
                     │
       ┌─────────────┼─────────────┐
       ↓             ↓             ↓
  más runtimes   más modelos    más hardware
       │             │             │
       └─────────────┼─────────────┘
                     ↓
              más mediciones
                     ↓
             mejor recomendador
                     ↓
                MANADA / web
```

La expansión debe reutilizar los contratos ya cerrados en lugar de crear caminos paralelos.

---

# 28. Regla final de congelación

A partir de este documento, la pregunta para cualquier nueva tarea será:

> **¿Esto acerca de forma directa y verificable a LEONES a la Definition of Done de RC1?**

Si la respuesta es **sí**, entra en RC1.

Si la respuesta es **no**, se documenta como trabajo posterior y no se introduce en el camino crítico.

Si la respuesta es **"tal vez"**, queda fuera hasta que exista un consumidor concreto o un gate que lo requiera.

Esta regla pretende impedir que el proyecto vuelva a abrir indefinidamente su arquitectura antes de disponer de una primera versión funcional.

---

## 29. Enlaces canónicos

- [`README.md`](../README.md) — entrada principal del proyecto.
- [`docs/README.md`](README.md) — índice documental canónico.
- [`docs/completed/JALON-3-MEASUREMENT-PROTOCOL.md`](completed/JALON-3-MEASUREMENT-PROTOCOL.md) — contrato de medición física cerrado.
- [`docs/FROZEN_DECISIONS.md`](FROZEN_DECISIONS.md) — decisiones congeladas.
- [`docs/ROADMAP.md`](ROADMAP.md) — evolución general.
- [`docs/sources/LLMFIT.md`](sources/LLMFIT.md) — LLMFit.
- [`docs/integrations/LLMFIT/README.md`](integrations/LLMFIT/README.md) — integración LLMFit.
- [`docs/RESULT_SCHEMA.md`](RESULT_SCHEMA.md) — contrato de resultados.
- [`PIPELINE_E2E.md`](../PIPELINE_E2E.md) — recorrido E2E del repositorio.

---

# 30. Estado

**RC1 — PLAN CONGELADO.**

El siguiente objetivo de implementación es cerrar el **vertical slice mínimo operativo**, manteniendo JALÓN 1, JALÓN 2 y JALÓN 3 como base contractual ya cerrada.
