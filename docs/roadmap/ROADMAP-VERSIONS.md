# LEONES — Roadmap de versiones

## Propósito
Convertir LEONES en un compendio abierto, navegable, reproducible y ejecutable del estado del arte de la IA agéntica abierta funcionando en local, manteniendo separadas **Fuente, Evidencia, Estimación y Medición LEONES**.

## Estado del roadmap
**FIJADO PARA DESARROLLO.** Este documento es la referencia canónica de evolución. Las versiones anteriores se preservan; las nuevas se añaden incrementalmente.

---

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

**Trabajo:**
- auditar y enlazar todos los README, fichas y fuentes;
- crear el mapa canónico del stack local;
- unificar Modelo → Runtime → Optimización → Harness → Tools → Protocolos → Evaluación;
- mantener las cuatro capas epistemológicas;
- crear matrices de compatibilidad;
- incorporar MCP, herramientas de agentes, memoria y RAG como familias propias.

**Definition of Done:** cualquier ficha puede recorrerse hacia arriba y abajo del stack mediante enlaces canónicos, sin duplicidades ni callejones documentales.

# V1.4 — Stack Explorer
**Objetivo:** representar visualmente el stack completo.

Hardware → Runtime → Optimización → Modelo → Harness → Tools → MCP → Memoria/RAG → Benchmark → Compatibilidades → Medición.

**Definition of Done:** una configuración LEONES puede recorrerse visualmente desde hardware hasta evidencia/medición.

# V1.5 — ¿Puede mi PC hacerlo?
**Objetivo:** calculadora de viabilidad local.

**Entrada:** CPU, RAM, GPU, VRAM, almacenamiento, OS y caso de uso.

**Salida:** modelos viables, runtime recomendado, optimizaciones, harness, memoria, rendimiento estimado, mediciones existentes y advertencias.

Estados: `VIABLE`, `VIABLE_WITH_OPTIMIZATION`, `NOT_RECOMMENDED`, `UNKNOWN`.

# V1.6 — MCP Registry
**Objetivo:** catálogo de servidores y herramientas MCP locales.

Cada entrada: licencia, fuente, instalación, capacidades, permisos, red requerida, offline, recursos, harnesses compatibles y riesgos.

# V1.7 — Agent Tools & Memory
**Objetivo:** cubrir la capa funcional del agente.

Familias: browser, code, shell, filesystem, git, database, web search, vision/OCR, computer use, Docker/SSH, memoria de corto y largo plazo, episódica/semántica/procedimental, memoria vectorial/grafo, RAG y agentic RAG.

# V1.8 — Local Agent Security
**Objetivo:** hacer de la seguridad una propiedad medible del stack.

Dimensiones: licencia, red, filesystem, shell, secretos, MCP, browser, Docker, privilegios, sandbox, prompt injection y exfiltración.

Crear `Local Agent Security Score` **explicable y multidimensional**, nunca un número opaco.

# V1.9 — LEONES Passport
**Objetivo:** identidad reproducible para cada ejecución.

Registrar hardware, OS, modelo/arquitectura, parámetros totales/activos, cuantización, runtime, optimizaciones, harness, herramientas, workload, benchmark, resultados y procedencia.

Crear identificador único de ejecución.

# V2.0 — LEONES Arena
**Objetivo:** comparar configuraciones agénticas completas.

Pipeline: `task → harness → model → runtime → tools → grader → evidence → measurement`.

Medir éxito, tiempo, tokens, tok/s, RAM/VRAM, llamadas a herramientas, pasos, errores y energía cuando sea medible.

# V2.1 — Local Agent Score
**Objetivo:** perfil multidimensional de una configuración.

Dimensiones: capacidad, velocidad, memoria, privacidad, autonomía, compatibilidad y seguridad.

No ocultar las dimensiones detrás de un ranking único.

# V2.2 — Selector de configuración completa
**Objetivo:** recomendar el stack completo.

`caso de uso → hardware → runtime → optimización → modelo → harness → tools → benchmark`.

La unidad de selección será una configuración reproducible, no un modelo aislado.

# V2.3 — Evidence Graph
**Objetivo:** grafo de procedencia que conecte:

`fuente → evidencia → estimación → configuración → benchmark → medición → recomendación`.

Toda cifra pública deberá poder rastrearse a su origen y estado epistemológico.

# V2.4 — Knowledge / Discovery Automation
**Objetivo:** mantener actualizado el compendio.

Descubrimiento de proyectos, cambios de licencia, runtime y compatibilidad, nuevos benchmarks, técnicas de optimización y regresiones.

# V3.0 — Open Local Agent Atlas
**Objetivo final:** LEONES como atlas operativo del ecosistema de IA agéntica abierta/local.

Debe responder de forma reproducible:

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
13. Las dependencias entre versiones deben declararse explícitamente; una versión posterior no puede asumir una capacidad que no esté entregada por una versión anterior.
14. Toda nueva funcionalidad debe tener contrato, pruebas y documentación antes de considerarse parte de una versión.
15. Los estados no verificados deben permanecer explícitamente como `UNKNOWN` o equivalentes; nunca se rellenan por inferencia.

## Orden de desarrollo
`V1.3 → V1.4 → V1.5 → V1.6 → V1.7 → V1.8 → V1.9 → V2.0 → V2.1 → V2.2 → V2.3 → V2.4 → V3.0`

## Control de cambios
Este roadmap queda **FIJADO PARA DESARROLLO**. Cualquier cambio de alcance, orden o Definition of Done debe registrarse como modificación explícita del roadmap, con justificación y nueva versión del documento. No se introducirán cambios de roadmap de forma implícita durante tareas de implementación.