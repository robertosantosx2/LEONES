# Artificial Analysis Optima y diseño de benchmarks de tareas agénticas

**Fuente principal:** https://www.youtube.com/watch?v=H-TTBsquXjw  
**Vídeo:** *Build your own AI evals with Optima (end-to-end walkthrough)*  
**Fuente complementaria:** Artificial Analysis, metodología de Intelligence Benchmarking y evaluaciones agénticas.  
**Fecha de incorporación:** 2026-08-19

> **Nota de trazabilidad:** el vídeo de YouTube no ha podido ser recuperado directamente en esta ejecución. La identificación del vídeo y su tema se han verificado externamente; el análisis de abajo distingue las capacidades documentadas de Optima de las decisiones de diseño que LEONES propone derivar de ellas.

## 1. Por qué esta fuente es importante para LEONES

El valor principal no es adoptar Optima como dependencia, sino adoptar su **modelo de evaluación**: construir evaluaciones específicas del trabajo real a partir de datos propios, trazas de agentes o una descripción del caso de uso, y comparar modelos no solo por calidad sino también por coste y tiempo por tarea.

Artificial Analysis ya emplea esta filosofía en evaluaciones como GDPval-AA v2: tareas reales, entorno agéntico, herramientas, producción de artefactos y evaluación por comparación ciega. Su metodología actual da un peso importante a la categoría Agents y usa límites de turnos elevados para trabajos de horizonte largo.

## 2. Ideas que debemos incorporar al sistema de benchmarks de LEONES

### 2.1. Tres vías para construir tareas

LEONES debe admitir tres entradas de benchmark:

1. **Dataset de tareas:** casos preparados por el equipo, con instrucciones, contexto, herramientas, restricciones y criterios de éxito.
2. **Trazas reales de agentes:** convertir ejecuciones reales en casos de evaluación reproducibles, conservando acciones, observaciones, errores, resultados y artefactos.
3. **Descripción de un caso de uso:** transformar una descripción de trabajo real en una propuesta de tareas, que después debe ser validada y congelada antes de convertirse en test.

Esto permite que el benchmark evolucione desde ejemplos sintéticos hacia trabajo real sin perder trazabilidad.

### 2.2. Evaluar sistemas, no únicamente modelos

Una tarea agéntica debe registrar al menos:

- modelo y versión;
- scaffold/orquestador;
- herramientas disponibles;
- permisos;
- entorno/sandbox;
- prompt y plantilla;
- límite de pasos/turnos;
- presupuesto de tokens/coste;
- tiempo máximo;
- resultado final;
- artefactos generados;
- traza completa de herramientas;
- errores y recuperaciones.

**Principio LEONES:** el resultado de un benchmark agéntico pertenece a la combinación `modelo + scaffold + herramientas + entorno + protocolo`, no al modelo aislado.

### 2.3. Separar outcome y trayectoria

El benchmark debe medir dos planos:

**Outcome**
- ¿La tarea quedó resuelta?
- ¿El artefacto cumple los requisitos?
- ¿El estado final del entorno es correcto?
- ¿Pasaron los validadores deterministas?

**Trajectory**
- ¿Usó las herramientas correctas?
- ¿Respetó permisos?
- ¿Evitó llamadas innecesarias?
- ¿Recuperó correctamente los errores?
- ¿Se quedó atrapado en bucles?
- ¿Cuántos pasos, tokens y llamadas necesitó?
- ¿Tomó acciones destructivas o innecesariamente arriesgadas?

Una tarea puede tener outcome correcto y trayectoria inaceptable. LEONES debe conservar ambos resultados.

## 3. Sistema de grading recomendado

LEONES debe soportar varios graders y no depender de una única puntuación.

### 3.1. Graders deterministas

Para aquello que puede verificarse sin un juez LLM:

- tests;
- diffs;
- existencia y contenido de ficheros;
- JSON Schema;
- consultas SQL esperadas;
- estado final de una base de datos;
- compilación;
- tests de software;
- permisos y llamadas de herramientas;
- límites de pasos/coste/tiempo.

Son los graders de mayor reproducibilidad.

### 3.2. Rubric grading

Para calidad de documentos, análisis, presentaciones y otras salidas abiertas:

- definir criterios explícitos;
- puntuar cada criterio independientemente;
- guardar la justificación del grader;
- calibrar el grader con ejemplos humanos;
- medir acuerdo entre graders cuando sea posible.

### 3.3. Pairwise grading

Para comparar entregables abiertos, LEONES debe poder enfrentar `A vs B` con evaluación ciega y producir rankings tipo Elo.

Esto es especialmente útil cuando no existe una respuesta única y permite comparar calidad relativa de artefactos completos.

## 4. Métricas mínimas de una tarea agéntica

Cada ejecución debe producir, como mínimo:

| Dimensión | Métrica |
|---|---|
| Calidad | score de outcome/rúbrica |
| Éxito | resolved/pass/fail |
| Trayectoria | pasos y llamadas de herramientas |
| Eficiencia | tokens, tiempo, coste |
| Robustez | recuperación tras errores |
| Seguridad | violaciones de permisos/políticas |
| Artefacto | validez y calidad del resultado |
| Fiabilidad | varianza entre repeticiones |
| Reproducibilidad | versión exacta del entorno |
|

No debemos colapsarlo todo inmediatamente en una única cifra.

## 5. Métrica compuesta propuesta para LEONES

Mantener como métricas primarias:

`quality`, `success_rate`, `cost_per_success`, `time_to_success`, `tool_efficiency`, `safety`, `recovery_rate`.

Como vista secundaria, construir una frontera de Pareto entre:

- calidad;
- coste;
- tiempo;
- seguridad.

Así evitamos declarar ganador a un agente que obtiene un pequeño incremento de calidad multiplicando por diez el coste o el tiempo.

## 6. Qué tareas debemos crear para el benchmark agéntico de LEONES

### Nivel A — Tool use

- elegir la herramienta correcta;
- generar argumentos válidos;
- respetar schemas;
- detectar cuándo no debe usar una herramienta;
- evitar llamadas redundantes.

### Nivel B — Multi-step

- encadenar varias herramientas;
- conservar estado;
- comprobar resultados intermedios;
- recuperarse de errores;
- terminar cuando se alcanza el objetivo.

### Nivel C — Artefactos

- generar documentos;
- modificar código;
- producir hojas de cálculo;
- crear presentaciones;
- entregar ficheros verificables.

### Nivel D — Long-horizon

- tareas de 20–250 pasos;
- objetivos con información incompleta;
- cambios de estrategia;
- errores deliberadamente introducidos;
- recuperación y replanteamiento.

### Nivel E — Operación real

- GitHub;
- shell;
- navegador;
- APIs;
- bases de datos;
- sistemas de ficheros;
- despliegues controlados.

### Nivel F — Seguridad y gobernanza

- permisos mínimos;
- operaciones destructivas;
- secretos;
- prompt injection;
- herramientas comprometidas;
- datos contradictorios;
- necesidad de aprobación humana.

## 7. Banco de tareas LEONES: estructura canónica

Cada tarea debería tener un registro equivalente a:

```yaml
id: AGENT-XXXX
version: 1
category: tool_use|workflow|artifact|long_horizon|security
instruction: ...
context: ...
allowed_tools: [...] 
permissions: ...
initial_state: ...
success_criteria: [...] 
deterministic_graders: [...] 
rubric: [...] 
max_turns: 50
max_cost: ...
max_duration_seconds: ...
expected_artifacts: [...] 
contamination_status: clean|unknown|retired
split: development|validation|audit
```

La especificación real puede evolucionar, pero debe separar claramente **definición de tarea**, **entorno**, **grader** y **ejecución**.

## 8. Trazas como fuente de nuevos benchmarks

Una de las ideas más aprovechables es convertir las trazas de producción en material de evaluación.

Pipeline propuesto:

`traza real → anonimización → detección de datos sensibles → normalización → etiquetado → generación de variantes → revisión humana → split → benchmark congelado`

No debemos convertir automáticamente toda traza en test. Primero hay que detectar duplicados, fugas de respuesta, datos sensibles, tareas triviales y dependencia excesiva de un proveedor concreto.

## 9. Contaminación y ciclo de vida

La serie de conocimiento de Ahmad ya establece que un benchmark deja de ser limpio cuando se optimiza repetidamente contra él. LEONES debe aplicar esa regla especialmente a los benchmarks agénticos.

Medidas obligatorias:

- separar desarrollo, validación y auditoría;
- congelar el protocolo antes de la prueba final;
- registrar versiones del benchmark;
- mantener tareas privadas/frescas;
- detectar reutilización de tareas y artefactos públicos;
- retirar tareas saturadas;
- no usar la puntuación del test de auditoría para optimizar prompts o scaffolds.

## 10. Qué NO debemos copiar sin más de Optima

Optima es una plataforma comercial/externa. LEONES debe aprender de su metodología sin convertirse en un simple cliente de ella.

LEONES necesita conservar:

- benchmark reproducible;
- definición abierta del protocolo;
- trazas exportables;
- graders intercambiables;
- ejecución local cuando sea posible;
- soporte de modelos abiertos y cerrados;
- comparación de hardware/runtimes;
- historial de versiones;
- posibilidad de auditoría independiente.

## 11. Integración con Open LLM Atlas

El resultado de una evaluación agéntica debe alimentar Atlas como evidencia empírica, pero con separación entre:

- **modelo**;
- **configuración**;
- **runtime**;
- **hardware**;
- **benchmark**;
- **tarea**;
- **ejecución**;
- **métrica**;
- **artefacto/evidencia**.

Esto evita el error clásico de almacenar simplemente `modelo → score`.

Para cada resultado debemos poder responder:

> ¿Qué modelo, en qué versión, con qué cuantización, en qué hardware, con qué runtime, con qué scaffold, usando qué herramientas y protocolo, resolvió qué tarea, con qué coste, en cuánto tiempo y con qué trayectoria?

## 12. Integración con los benchmarks actuales de LEONES

Optima no sustituye benchmarks públicos como SWE-bench, TerminalBench, τ-bench o GDPval. Debe complementar esa capa con una **familia propia de tareas reales de LEONES**.

La arquitectura recomendada queda:

`Benchmarks públicos → comparabilidad externa`

`Benchmarks propios LEONES → relevancia para nuestro ecosistema`

`Trazas reales → descubrimiento de nuevas tareas`

`Micro-evals → diagnóstico rápido`

`Auditoría privada → medición final`

## 13. Decisión para LEONES

**Adoptar como principio de diseño:** benchmarks agénticos construidos alrededor de tareas reales, trazas y artefactos, con grading múltiple y métricas simultáneas de calidad, coste, tiempo, seguridad y eficiencia.

**No adoptar:** dependencia obligatoria de Optima, puntuación única, evaluación únicamente conversacional o comparación de modelos sin fijar scaffold, herramientas y entorno.

## 14. Próximo desarrollo recomendado

1. Crear el esquema `agentic_task`.
2. Crear el esquema `agentic_run`.
3. Crear almacenamiento de trazas.
4. Implementar graders deterministas.
5. Implementar rubric grader.
6. Implementar pairwise/Elo.
7. Añadir métricas de coste/tiempo.
8. Crear 20 tareas iniciales reales.
9. Dividirlas en desarrollo/validación/auditoría.
10. Ejecutar varios modelos y runtimes.
11. Publicar leaderboard reproducible.
12. Añadir extracción de tareas desde trazas reales.
13. Integrar resultados con Open LLM Atlas.
14. Mantener un conjunto privado/fresco de auditoría.

## 15. Fuentes

- Vídeo: https://www.youtube.com/watch?v=H-TTBsquXjw
- Artificial Analysis — Intelligence Benchmarking: https://artificialanalysis.ai/methodology/intelligence-benchmarking
- Artificial Analysis — GDPval-AA v2: https://artificialanalysis.ai/evaluations/gdpval-aa
- Artificial Analysis — MicroEvals: https://artificialanalysis.ai/microevals
- Artificial Analysis — Intelligence/agentic evaluations: https://artificialanalysis.ai/
