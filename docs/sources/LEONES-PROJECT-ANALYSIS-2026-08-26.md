# Análisis del proyecto LEONES — 26 de agosto de 2026

## Identidad
- Proyecto: LEONES — Local Ecosystem of Open Neural Expert Systems
- Repositorio: https://github.com/robertosantosx2/LEONES/
- Web: https://robertosantosx2.github.io/LEONES/
- Licencia: AGPL-3.0
- Estado: Alfa

## Tesis
LEONES no debe presentarse como otro catálogo de modelos ni como otro chatbot. Su propósito es construir una cadena de conocimiento y decisión que responda de forma rigurosa y reproducible a:

> ¿Qué modelo + runtime + hardware + configuración permiten ejecutar una tarea real de IA de forma razonable, abierta y económicamente sostenible en hardware de consumo?

La cadena conecta prospección, Atlas, hardware/precios, encaje modelo-máquina, runtimes, optimización, agentes, harnesses, benchmarks físicos y conocimiento colectivo.

## Fortalezas
1. Procedencia de datos como principio de diseño.
2. Separación entre `estimated`, `reported`, `observed`, `measured`, `verified` y `unknown`.
3. Arquitectura modular: prospección → Atlas → hardware/precios → ajuste modelo-máquina → runtime → agentes → benchmark → conocimiento colectivo.
4. Atención explícita a hardware de consumo y configuraciones modestas.
5. Integración con proyectos externos como LLMFit y ODS sin convertir sus claims en mediciones LEONES.
6. Licencia AGPL-3.0 coherente con el enfoque copyleft.
7. Web y documentación con una base metodológica sólida.

## Riesgos / debilidades
1. Estado alfa y baja tracción visible.
2. Complejidad elevada para usuarios que solo quieren una recomendación inmediata.
3. Curva de entrada alta.
4. Volumen todavía limitado de mediciones físicas públicas.
5. La web puede parecer documentación de investigación antes que producto.
6. Riesgo de fragmentación por múltiples subproyectos.
7. Comunidad y comunicación todavía muy dependientes del mantenedor.

## Dirección de producto web
La web debe reducir la distancia entre la profundidad metodológica y el valor inmediato. Debe ofrecer una entrada rápida sin sacrificar el compendio de conocimiento.

### Principios UX
- Valor visible en menos de cinco minutos.
- Un pitch corto antes de la arquitectura profunda.
- Ejemplos reales y mediciones visibles.
- Navegación por capas y relaciones, no por listas aisladas.
- Toda cifra conserva su procedencia y estado epistemológico.
- Las capacidades diseñadas pero no verificadas se muestran como `UNKNOWN`.

## Roadmap web

### Web V1.3 — Compendio navegable
- Auditoría y enlace de todos los README, fichas y fuentes.
- Índice canónico de conocimiento.
- Navegación Modelo → Runtime → Optimización → Harness → Tools → MCP → Memoria/RAG → Benchmark.
- Matrices de compatibilidad.
- Fichas con Fuente/Evidencia/Estimación/Medición.
- Página "Start here" y pitch corto.

### Web V1.4 — Stack Explorer
- Mapa visual interactivo del stack.
- Hardware → Runtime → Optimización → Modelo → Harness → Tools → MCP → Memoria/RAG → Benchmark.
- Vista de configuración completa.
- Enlaces bidireccionales entre fichas.

### Web V1.5 — ¿Puede mi PC hacerlo?
- Formulario de CPU/RAM/GPU/VRAM/almacenamiento/OS/caso de uso.
- Resultado accionable: modelos, runtime, optimización, harness y advertencias.
- Estados `VIABLE`, `VIABLE_WITH_OPTIMIZATION`, `NOT_RECOMMENDED`, `UNKNOWN`.
- Diferenciación visual entre estimación y medición.

### Web V1.6 — MCP Registry
- Catálogo de servidores/herramientas MCP.
- Licencia, instalación, capacidades, permisos, red/offline, recursos, compatibilidad y riesgos.
- Filtros por harness, runtime y nivel de acceso.

### Web V1.7 — Agent Tools & Memory
- Catálogo de herramientas: browser, code, shell, filesystem, git, database, web search, vision/OCR, computer use, Docker/SSH.
- Catálogo de memoria: corto/largo plazo, episódica, semántica, procedimental, vectorial, grafo.
- RAG y agentic RAG.

### Web V1.8 — Local Agent Security
- Ficha de seguridad de cada configuración.
- Licencia, red, filesystem, shell, secretos, MCP, browser, Docker, privilegios, sandbox, prompt injection y exfiltración.
- `Local Agent Security Score` multidimensional y explicable.

### Web V1.9 — LEONES Passport
- Página pública de cada ejecución reproducible.
- Hardware, OS, modelo, parámetros, cuantización, runtime, optimización, harness, tools, workload, benchmark, resultados y procedencia.
- Identificador único y enlace permanente.

### Web V2.0 — LEONES Arena
- Comparación de configuraciones agénticas completas.
- Tareas reproducibles.
- Éxito, tiempo, tokens, tok/s, RAM/VRAM, llamadas a herramientas, pasos, errores y energía cuando exista medición.
- No comparar solamente modelos.

### Web V2.1 — Local Agent Score
- Perfil visual multidimensional: capacidad, velocidad, memoria, privacidad, autonomía, compatibilidad y seguridad.
- Evitar un ranking único opaco.

### Web V2.2 — Selector de configuración completa
- Recomendación de stack completo: caso de uso → hardware → runtime → optimización → modelo → harness → tools → benchmark.
- Explicación de por qué se recomienda cada configuración.

### Web V2.3 — Evidence Graph
- Grafo visual: fuente → evidencia → estimación → configuración → benchmark → medición → recomendación.
- Cada cifra pública navegable hasta su procedencia.

### Web V2.4 — Knowledge / Discovery Automation
- Descubrimiento de proyectos.
- Detección de cambios de licencia, runtime y compatibilidad.
- Nuevos benchmarks y optimizaciones.
- Regresiones y alertas.

### Web V3.0 — Open Local Agent Atlas
La web se convierte en un atlas operativo del ecosistema de IA agéntica abierta/local, capaz de contestar de forma reproducible qué puede ejecutar una persona en su hardware, con qué stack y con qué evidencia.

## Elementos de atractivo prioritarios
1. **Recomendador rápido:** hardware + tarea → 2/3 configuraciones con confianza y procedencia.
2. **LEONES Arena:** comparación de agentes completos.
3. **LEONES Stack Explorer:** recorrido visual por todo el stack.
4. **MCP Registry:** catálogo práctico de herramientas locales.
5. **LEONES Passport:** historial reproducible de ejecuciones.
6. **Local Agent Score:** perfil multidimensional y explicable.
7. **Can LEONES Run It?:** entrada directa para comprobar viabilidad.
8. **Manada:** facilitar aportaciones de mediciones reales y mostrar leaderboards por hardware.

## Mensaje de posicionamiento
**LEONES = evidencia real + hardware de consumo + IA agéntica abierta/local.**

La web debe comunicar que el valor diferencial no es conocer muchos proyectos, sino poder enlazar conocimiento con ejecución y medición sin ocultar la incertidumbre.

## Regla editorial
La profundidad del compendio se conserva, pero la interfaz debe tener dos niveles: **entrada rápida para quien busca una respuesta** y **profundidad documental para quien quiere verificarla**.
