# Buddy — subproyecto de LEONES

**Upstream:** https://github.com/juanje/buddy  
**Tipo:** harness / asistente personal local con memoria persistente  
**Estado LEONES:** referencia de harness; integración diseñada para ODS y Magnitude.

## Mapa documental

- [`../../AGENT_HARNESSES.md`](../../AGENT_HARNESSES.md) — posición de Buddy junto a DSH y Hermes.
- [`../../EVALUACION_AGENTIC_TESTS.md`](../../EVALUACION_AGENTIC_TESTS.md) — metodología común de evaluación.
- [`../../../benchmarks/agentic/README.md`](../../../benchmarks/agentic/README.md) — batería agentiva.
- [`../../../schemas/result.schema.json`](../../../schemas/result.schema.json) — contrato de resultados.
- [`HARNESS-CONTRACT.md`](HARNESS-CONTRACT.md) — contrato específico de Buddy.
- [`ODS-INTEGRATION.md`](ODS-INTEGRATION.md) — adaptación para ODS.
- [`MAGNITUDE-INTEGRATION.md`](MAGNITUDE-INTEGRATION.md) — adaptación para Magnitude.
- [`LICENSING-INTEGRATION.md`](LICENSING-INTEGRATION.md) — licencia y frontera de integración.
- [`../../sources/BUDDY_HARNESS.md`](../../sources/BUDDY_HARNESS.md) — ficha de conocimiento.

## Objetivo

Incorporar Buddy al laboratorio de harnesses de LEONES junto con **DeepSeek Harness (DSH)** y **Hermes**, de forma que una misma tarea, modelo, hardware y política puedan ejecutarse bajo distintos harnesses y compararse mediante el contrato común de evaluación agentiva.

Buddy se incorpora como dependencia upstream versionada, no como un fork silencioso. La implementación de Buddy debe permanecer atribuida a su repositorio original y cualquier adaptación específica de LEONES debe vivir en esta capa de integración.

## Qué aporta Buddy

Según su documentación upstream, Buddy es una aplicación nativa de escritorio construida con Tauri v2, Svelte 5 y un worker Node.js/TypeScript que usa Pi SDK como runtime de agente. Su memoria es un repositorio Git de archivos Markdown locales, con `AGENTS.md`, `agent_brain/`, `user/` y `logs/`. El diseño busca continuidad entre sesiones, memoria transparente y dependencia del proveedor desacoplada de esa memoria.

La arquitectura también aplica una capa de permisos por zonas y limita deliberadamente las herramientas del agente a operaciones de archivos, sin Bash/shell para el agente. La reflexión de fondo se ejecuta sin herramientas y el I/O de ficheros queda en código determinista.

## Posición en LEONES

```text
LEONES Agent Harnesses
├── DSH        → harness plugin/event driven
├── Buddy      → personal-memory / file-first harness
└── Hermes     → ODS-native agent harness
```

Los tres son **harnesses de referencia**. El benchmark debe poder sustituirlos sin cambiar la tarea ni el modelo evaluado.

## Regla de integración

No se copia el núcleo de Buddy dentro de ODS o Magnitude. Se integra mediante adaptadores y perfiles:

```text
Buddy upstream
      │
      ├── standalone
      ├── ODS adapter
      └── Magnitude adapter
               │
               ▼
       LEONES Agent Trace
```

## Calidad y validación

El upstream declara como gate `tsc --noEmit`, `vite build` y `npm test`, con tests unitarios y BDD. La integración LEONES añade pruebas de contrato para:

- arranque/parada;
- selección de proveedor/modelo;
- trazado de turn/step/tool;
- persistencia de memoria;
- aislamiento del workspace;
- permisos;
- equivalencia de tarea entre harnesses;
- captura de outcome, trajectory, coste/tiempo y seguridad.

El resultado de Buddy no se promociona automáticamente a medición: la tarea, la traza y el grader deben pasar por el contrato común de LEONES.

## Integraciones relacionadas

- [Diseño ODS](./ODS-INTEGRATION.md)
- [Diseño Magnitude](./MAGNITUDE-INTEGRATION.md)
- [Contrato común de harnesses](./HARNESS-CONTRACT.md)
- [Licensing](./LICENSING-INTEGRATION.md)
- [Ficha de conocimiento](../../sources/BUDDY_HARNESS.md)
