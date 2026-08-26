# Harnesses — investigación y conocimiento

## Objetivo
Identificar harnesses OSS útiles para LEONES, filtrados por licencia OSI y clasificados por compatibilidad y funcionalidad. Un harness no es un modelo ni un runtime: es la capa que orquesta sesiones, herramientas, memoria, agentes, permisos y evaluación.

## Filtro OSI
El filtro de entrada exige una licencia aprobada por OSI para el núcleo considerado. Proyectos con partes enterprise o componentes de licencia diferente conservan esa excepción explícita.

## Familias
### A — AGENT GENERAL
Harnesses de propósito general: herramientas, memoria, sesiones, planificación y ejecución.
- Hermes Agent — MIT.
- OpenHands — MIT para el núcleo; `enterprise/` tiene licencia separada.
- DeepSeek Harness — MIT; developer preview.

### B — CODING
Agentes/harnesses centrados en repositorios, terminal, edición y pruebas.
- OpenCode.
- OpenHands.
- DeepSeek Harness.

### C — LOCAL / HARDWARE MODESTO
Harnesses que pueden consumir modelos locales o endpoints OpenAI-compatible y son adecuados para ejecución privada/local.
- Hermes Agent.
- OpenCode.
- ResearchHarness.
- Magnitude como referencia de meta-harness local, no como candidato externo independiente: integra su propio harness e inference engine.

### D — EVALUATION
Infraestructura para ejecutar benchmarks reproducibles y comparar modelos.
- lm-evaluation-harness — MIT.
- ResearchHarness — runtime/benchmark experimental.

### E — SECURITY / REGRESSION
Harnesses cuyo objetivo principal es seguridad, regresión y control de agentes.
- OWASP Agent Security Regression Harness.

### F — OBSERVABILITY / CONTROL
Capas de políticas, tracing, budgets, permisos y recuperación.
- HarnessAgent.
- agent-harness.
- ODS APE como referencia de control integrado.

### G — INTEROPERABILITY / META-HARNESS
Unifica distintos harnesses bajo un contrato común.
- HarnessRouter / Unified Harness Protocol (UHP) — Apache-2.0 Community Edition.

## Candidatos prioritarios para LEONES
1. Hermes Agent — local-first, herramientas, memoria, skills y amplio soporte de modelos/endpoints locales.
2. OpenCode — coding agent proveedor-agnóstico y local-compatible.
3. OpenHands — coding/general agent con SDK y ejecución local.
4. DeepSeek Harness — arquitectura plugin-first y adaptadores; developer preview.
5. HarnessRouter/UHP — interoperabilidad y conformidad entre harnesses.
6. lm-evaluation-harness — benchmark/evaluación reproducible; no sustituye a un agente.

## Compatibilidad con Magnitude
Magnitude es un agente local OSS Apache-2.0 con su propio inference engine sobre llama.cpp. Puede usar modelos del catálogo y GGUF compatibles, y puede conectarse a endpoints OpenAI-compatible. Por ello, la compatibilidad con un harness externo debe distinguirse de la instalación: Magnitude no es un gestor universal de instalación de harnesses. `magnitude` puede actuar como entorno/consumidor de modelos y herramientas, pero la instalación del harness sigue su propio mecanismo.

## Compatibilidad con ODS/Osmantic
ODS es un stack local extensible. Su estado actual integra directamente Hermes Agent como agente por defecto y OpenCode como IDE/agente de coding; ambos forman la ruta de instalación directa de ODS. ODS también expone el LLM local por interfaces compatibles y permite extensiones mediante manifests. Otros harnesses requieren integración/extensión específica y no deben etiquetarse como instalables por ODS sin una receta de instalación verificada.

## Regla de compatibilidad
Tres estados independientes:
- `DIRECT_INSTALL`: el sistema de destino tiene instalación documentada y verificada.
- `CONSUMER_COMPATIBLE`: puede consumir el endpoint/runtime del sistema, pero no es instalado por él.
- `INTEGRATION_REQUIRED`: requiere adaptación/extensión.

## Evidencia y estado
La existencia/licencia/instalación se mantiene como evidencia externa. La compatibilidad real en una máquina concreta debe pasar por preflight y prueba de instalación/arranque. No convertir una declaración de README en medición LEONES.

## Relación con Selector múltiple evolucionado V1.1
Este bloque es conocimiento independiente. El selector de harness futuro se denomina **Selector Harness V1.2** y se ejecutará después de determinar caso de uso, hardware, runtime y optimizaciones.
