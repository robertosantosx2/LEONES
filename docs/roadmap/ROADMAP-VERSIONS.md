# LEONES — Roadmap de versiones

## Propósito
Convertir LEONES en un compendio abierto, navegable, reproducible y ejecutable del estado del arte de la IA agéntica abierta funcionando en local, manteniendo separadas fuente, evidencia, estimación y medición LEONES.

## Versiones congeladas

### V1 — Operativa
Selector actual basado en `model_selector.py`, feed de modelos y restricciones de hardware.

### V1.1 — Selector múltiple evolucionado
**CONGELADO.** Caso de uso → hardware → runtime → optimización → Dense/MoE → 6 estimadores → 108 candidatos → 9 representantes → `runtime-selection.v1` → benchmark.

### V1.2 — Selector Harness
**CONGELADO.** Selección de harnesses mediante capacidades, OSI, compatibilidad con ODS/Magnitude y preflight, manteniendo separados instalación, smoke test y benchmark.

---

# V1.3 — Compendio de conocimiento agentic local
**Objetivo:** convertir el conocimiento acumulado en un mapa coherente y navegable.

- Auditar y enlazar todos los README y fichas.
- Crear el mapa canónico del stack local.
- Unificar Modelos → Runtime → Optimización → Harness → Tools → Protocolos → Evaluación.
- Mantener las cuatro capas: Fuente / Evidencia / Estimación / Medición.
- Crear matrices de compatibilidad.
- Incorporar MCP como familia propia.
- Incorporar herramientas de agentes como familia propia.
- Incorporar memoria y RAG como familias propias.

**Definition of Done:** desde cualquier ficha se puede navegar hacia arriba y abajo del stack sin callejones documentales.

# V1.4 — Stack Explorer
**Objetivo:** representación visual del stack completo.

- Hardware.
- Runtime.
- Optimización.
- Modelo.
- Harness.
- Tools.
- MCP.
- Memoria/RAG.
- Benchmark.
- Compatibilidades.
- Vista de configuración completa.

**Definition of Done:** una configuración LEONES puede recorrerse visualmente de hardware a medición.

# V1.5 — ¿Puede mi PC hacerlo?
**Objetivo:** calculadora de viabilidad local.

Entrada:
- CPU.
- RAM.
- GPU.
- VRAM.
- almacenamiento.
- sistema operativo.
- caso de uso.

Salida:
- modelos viables;
- runtime recomendado;
- optimizaciones;
- harness;
- memoria requerida;
- estimación de rendimiento;
- mediciones existentes;
- advertencias.

Estados: `VIABLE`, `VIABLE_WITH_OPTIMIZATION`, `NOT_RECOMMENDED`, `UNKNOWN`.

# V1.6 — MCP Registry
**Objetivo:** catálogo de servidores y herramientas MCP locales.

Cada entrada debe incluir:
- licencia;
- fuente;
- instalación;
- capacidades;
- permisos;
- red requerida;
- funcionamiento offline;
- consumo de recursos;
- harnesses compatibles;
- riesgos de seguridad.

# V1.7 — Agent Tools & Memory
**Objetivo:** cubrir la capa funcional del agente.

Familias:
- browser;
- code;
- shell;
- filesystem;
- git;
- database;
- web search;
- vision/OCR;
- computer use;
- Docker/SSH;
- short-term memory;
- long-term memory;
- episodic/semantic/procedural memory;
- vector/graph memory;
- RAG y agentic RAG.

# V1.8 — Local Agent Security
**Objetivo:** seguridad como propiedad medible del stack.

Dimensiones:
- licencia;
- red;
- filesystem;
- shell;
- secretos;
- MCP;
- browser;
- Docker;
- privilegios;
- sandbox;
- prompt injection;
- exfiltración de datos.

Crear `Local Agent Security Score` explicable, nunca un número opaco.

# V1.9 — LEONES Passport
**Objetivo:** identidad reproducible para cada ejecución.

Cada ejecución registra:
- hardware;
- OS;
- modelo/arquitectura;
- parámetros totales/activos;
- cuantización;
- runtime;
- optimizaciones;
- harness;
- herramientas;
- workload;
- benchmark;
- resultados;
- procedencia de cada dato.

Crear identificador único de ejecución.

# V2.0 — LEONES Arena
**Objetivo:** comparar configuraciones agénticas completas, no únicamente modelos.

Pipeline:
`task → harness → model → runtime → tools → grader → evidence → measurement`.

Medir:
- éxito;
- tiempo;
- tokens;
- tok/s;
- RAM/VRAM;
- llamadas a herramientas;
- pasos;
- errores;
- energía cuando sea medible.

Separar claramente resultados estimados de mediciones propias.

# V2.1 — Local Agent Score
**Objetivo:** perfil multidimensional de una configuración.

Dimensiones propuestas:
- capacidad;
- velocidad;
- memoria;
- privacidad;
- autonomía;
- compatibilidad;
- seguridad.

No crear un ranking único que oculte las dimensiones.

# V2.2 — Selector de configuración completa
**Objetivo:** evolucionar el Selector para recomendar el stack completo.

`caso de uso → hardware → runtime → optimización → modelo → harness → tools → benchmark`.

La unidad de selección será una configuración reproducible, no un modelo aislado.

# V2.3 — Evidence Graph
**Objetivo:** grafo de procedencia que conecte:
`fuente → evidencia → estimación → configuración → benchmark → medición → recomendación`.

Toda cifra pública deberá poder rastrearse a su origen y estado epistemológico.

# V2.4 — Knowledge/Discovery Automation
**Objetivo:** mantener actualizado el compendio.

- descubrimiento de nuevos proyectos;
- detección de cambios de licencia;
- cambios de runtime;
- cambios de compatibilidad;
- nuevos benchmarks;
- nuevas técnicas de optimización;
- regresiones.

# V3.0 — Open Local Agent Atlas
**Objetivo final del roadmap:** LEONES como atlas operativo del ecosistema de IA agéntica abierta/local.

Debe permitir responder de forma reproducible:

> ¿Qué puedo ejecutar, en mi hardware, para mi caso de uso, con qué modelo, runtime, optimización, harness y herramientas, y qué evidencia demuestra que funciona?

---

## Principios de desarrollo congelados

1. No mezclar Fuente, Evidencia, Estimación y Medición.
2. No convertir claims externos en mediciones LEONES.
3. Hardware y caso de uso preceden a la selección.
4. Runtime y optimización preceden al modelo.
5. Dense y MoE usan criterios de parámetros diferentes.
6. El harness es una dimensión del stack, no un ranking paralelo de modelos.
7. OSI es un gate documental para candidatos OSS; no sustituye la verificación técnica.
8. Compatibilidad, instalación, smoke test y benchmark son estados distintos.
9. Cada nueva familia de conocimiento debe tener ficha, fuente, relaciones y publicación web.
10. Los contratos existentes de V1, V1.1 y V1.2 no se rompen para desarrollar versiones posteriores.
11. Las versiones se añaden incrementalmente; no se reescribe la historia.
12. Toda recomendación debe poder explicar por qué fue seleccionada.

## Orden de desarrollo
`V1.3 → V1.4 → V1.5 → V1.6 → V1.7 → V1.8 → V1.9 → V2.0 → V2.1 → V2.2 → V2.3 → V2.4 → V3.0`

Este roadmap queda **FIJADO PARA DESARROLLO**. Cualquier cambio posterior debe registrarse como modificación explícita del roadmap, no introducirse implícitamente durante una tarea.