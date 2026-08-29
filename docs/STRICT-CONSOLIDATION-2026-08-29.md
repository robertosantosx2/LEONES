# LEONES — Consolidación `-strict-` de JALONES 1–11

**Fecha:** 2026-08-29  
**Rama de trabajo:** `rc1-minimal-script-cleanup`  
**Ámbito:** trabajo realizado desde el 27 de agosto de 2026 hasta la consolidación actual.

## 1. Qué significa «limpiar, fijar y dar esplendor» en LEONES

En este proyecto, la expresión no significa borrar código por gusto ni reescribir lo que ya funciona. Significa aplicar una revisión estricta antes de considerar una pieza terminada:

1. **Limpiar:** eliminar ambigüedades, duplicidades, nombres engañosos, comprobaciones frágiles y documentación contradictoria.
2. **Fijar:** convertir las decisiones correctas en contratos, schemas, tests y gates reproducibles.
3. **Dar esplendor:** explicar el porqué y el cómo, tanto para quien mantiene el código como para quien sólo necesita utilizarlo.

La limpieza no debe cambiar silenciosamente el significado de una evidencia ya obtenida.

## 2. Regla `-strict-`

Cuando una petición de trabajo diga **«limpia, fija y da esplendor»**, esta revisión es obligatoria antes de añadir la siguiente capa funcional.

El orden estricto es:

`inventario → autoridad → fronteras → documentación → tests → auditoría → evidencia → cierre → siguiente bloque`

Si una comprobación necesita ejecución física, se prepara en GitHub y se deja Ubuntu únicamente para la ejecución que no pueda sustituirse por una prueba declarativa.

## 3. Arquitectura consolidada

La cadena construida durante estos jalones debe entenderse como **una sola tubería**, no como once sistemas independientes:

```text
selección
   ↓
runtime autorizado
   ↓
ejecución
   ↓
medición
   ↓
evidencia
   ↓
decisión ODS/Magnitude → LEONES
   ↓
recomendación
   ↓
publicación
   ↓
salida fiel
   ↓
traza E2E
```

Las capas superiores transportan referencias de las capas inferiores. No vuelven a medir, puntuar ni decidir.

## 4. Qué quedó establecido

### JALÓN 1
Base de CI y contrato inicial. Su función es proporcionar la base verificable sobre la que se construyen los siguientes bloques.

### JALÓN 2
Puente de ejecución física y evidencia real. La referencia conservada usa `llama.cpp`, un modelo Qwen3 0.6B cuantizado y cinco ejecuciones reales. La cifra obtenida pertenece a esa ejecución concreta y no debe convertirse en una constante universal.

### JALÓN 3
Contrato operativo de medición real. Fija la separación entre ejecución, medición y evidencia y conserva identidad, timestamps, protocolo, runtime, hardware y hash del artefacto.

### JALÓN 4
Taxonomía de runtime y contratos de adapters. Define cómo se representa un runtime autorizado sin inventar una segunda capa de ejecución.

### JALÓN 5
Contrato de decisión ODS/Magnitude → LEONES y puente de decisión. Las señales externas permanecen diferenciadas de la evidencia física medida.

### JALÓN 6
Gate de recomendación/evidencia. Una recomendación sólo puede utilizar las referencias y condiciones definidas por el contrato; no crea un nuevo motor de scoring.

### JALÓN 7
Cadena de validación → promoción → publicación. La evidencia no pasa directamente a publicación sin las fronteras contractuales intermedias.

### JALÓN 8
Sobre de trazabilidad E2E. Conecta las etapas existentes mediante referencias y no duplica selección, benchmark, scoring ni evidencia.

### JALÓN 9
Recomendación canónica. Sintetiza decisión y evidencia existentes. Los estados son `recommend`, `watch`, `reject` y `verify_first`.

### JALÓN 10
Salida de recomendación. Transporta fielmente una recomendación hacia el consumidor y no reinterpreta decisión, evidencia ni scoring.

### JALÓN 11
Operación E2E. Encadena todos los contratos anteriores en una única operación identificable, manteniendo separada la ejecución física real de la validación declarativa.

## 5. Fronteras que no se deben romper

### Externo ≠ medido
LLMFit, ODS/Magnitude y otras fuentes externas pueden aportar señales, estimaciones o datos declarados. Su presencia no los convierte en medición local.

### Compatibilidad ≠ rendimiento
Que un modelo pueda caber o arrancar en una máquina no demuestra cuántos tokens por segundo producirá.

### Benchmark ≠ tarea completada
Un benchmark de rendimiento no sustituye una evaluación de una tarea real. La medición física y la evaluación agentiva conservan sus respectivos contratos.

### Recomendación ≠ scoring nuevo
La recomendación consume una decisión ya autorizada y evidencia correspondiente. No debe aparecer un `score` paralelo para volver a ordenar los resultados.

### Trazabilidad ≠ nueva base de datos de verdad
La traza E2E enlaza artefactos existentes. No debe convertirse en un almacén alternativo que contradiga esos artefactos.

## 6. Guía para leer el código

Un lector con pocos conocimientos de programación debería poder contestar tres preguntas al abrir cualquier script de esta cadena:

1. **¿Qué recibe?** — normalmente referencias o un JSON que pertenece a un contrato anterior.
2. **¿Qué comprueba o transforma?** — validación, transporte o encadenamiento.
3. **¿Qué NO hace?** — no inventa mediciones, no recalcula scoring y no sustituye una fuente de verdad anterior.

Por eso los scripts de recomendación, salida y E2E deben mantener comentarios sencillos y explícitos. Por ejemplo, el validador de JALÓN 9 es un guardián del contrato, no una calculadora, y el productor de JALÓN 10 es un transportador fiel de la recomendación. fileciteturn365file0L2-L2 fileciteturn358file0L2-L2

## 7. Cómo utilizar la cadena

### Validación declarativa

Ejecutar el runner del jalón correspondiente. El runner debe comprobar contrato, tests, invariantes y `git diff --check` cuando corresponda.

### Ejecución física

Sólo cuando el contrato indique que hace falta evidencia real:

```text
preflight → ejecutar runtime → medir → conservar stdout/stderr
→ calcular/verificar hash → validar evidencia → publicar referencia
```

Nunca se debe rellenar una evidencia física con valores inventados para que un gate pase.

### Operación E2E

Una operación de JALÓN 11 contiene referencias como `selection_ref`, `runtime_ref`, `execution_ref`, `measurement_ref`, `evidence_refs`, `decision_ref`, `recommendation_ref`, `publication_ref`, `output_ref` y `trace_ref`, además de su estado. fileciteturn357file0L2-L2

## 8. Criterio de calidad para futuras ampliaciones

Una ampliación es aceptable sólo si:

- reutiliza contratos existentes cuando la semántica ya está resuelta;
- crea un contrato nuevo sólo cuando existe una frontera nueva real;
- documenta entradas, salidas y errores;
- tiene tests negativos además de tests felices;
- tiene un runner reproducible si constituye un jalón;
- no duplica scoring, benchmark o evidencia;
- conserva procedencia;
- distingue `estimated`, `reported`, `observed`, `measured`, `verified` y `unknown`;
- puede explicar a una persona no experta qué hace cada script.

## 9. Estado de esta consolidación

Los jalones 3–11 alcanzaron cierres declarativos mediante sus respectivos gates en la rama de trabajo. El hecho de que un jalón tenga cierre declarativo **no implica que toda la cadena haya sido ejecutada físicamente de extremo a extremo**.

La evidencia física debe seguir siendo la que realmente se ejecutó y conservó. La siguiente ejecución real debe ampliar esa evidencia, no reescribir la historia.

**Frase de recuperación:**

> `-strict-` = antes de seguir construyendo, limpiar la arquitectura, fijar sus contratos, explicar su uso y demostrar que no existe una segunda fuente de verdad.
