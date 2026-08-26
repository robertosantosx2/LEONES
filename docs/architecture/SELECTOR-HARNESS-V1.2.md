# Selector Harness V1.2

## Estado
**PREPARADO Y CONGELADO COMO DISEÑO PARA V1.2**

No implica que ningún harness haya sido instalado en la máquina del usuario.

## Objetivo
Seleccionar hasta seis candidatos OSS de harness según caso de uso, capacidades, hardware/OS, runtime, optimizaciones y compatibilidad de despliegue. La decisión final de instalación exige preflight y prueba de arranque.

## Gate OSI
Solo el núcleo de un candidato con licencia aprobada por OSI entra en el conjunto OSS. Las excepciones de licencia de componentes se conservan explícitamente.

## Seis candidatos de referencia
| # | Harness | Familia | OSI | ODS | Magnitude | Papel |
|---|---|---|---|---|---|---|
| 1 | Hermes Agent | agente general/local | Sí | DIRECT_INSTALL* | CONSUMER_COMPATIBLE* | agente local principal |
| 2 | OpenCode | coding/local | Sí | DIRECT_INSTALL* | CONSUMER_COMPATIBLE* | coding principal |
| 3 | OpenHands | coding/general | Sí, núcleo MIT | INTEGRATION_REQUIRED | CONSUMER_COMPATIBLE | agente/coding alternativo |
| 4 | DeepSeek Harness | agente/plugin | Sí, MIT | INTEGRATION_REQUIRED | CONSUMER_COMPATIBLE | investigación / preview |
| 5 | HarnessRouter / UHP | interoperabilidad | Sí, Apache-2.0 CE | INTEGRATION_REQUIRED | CONSUMER_COMPATIBLE | meta-harness/gateway |
| 6 | lm-evaluation-harness | evaluación | Sí, MIT | INTEGRATION_REQUIRED | CONSUMER_COMPATIBLE | evaluación; no agente |

`*` DIRECT_INSTALL en ODS significa integración/receta de ODS; no significa que ODS sea un instalador universal de harnesses. La instalación concreta debe verificarse sobre la versión/plataforma objetivo.

## Compatibilidad no es instalación
- `DIRECT_INSTALL`: receta reproducible para instalar/activar en el sistema objetivo.
- `CONSUMER_COMPATIBLE`: puede consumir el endpoint/runtime/API, pero no existe una ruta de instalación por ese sistema.
- `INTEGRATION_REQUIRED`: falta una receta, extensión, adaptador o empaquetado verificado.

Magnitude incluye su propio harness/inference engine y puede consumir modelos/endpoints compatibles; no debe tratarse como gestor universal de harnesses externos.

ODS es un stack de despliegue local y actualmente incluye Hermes Agent y OpenCode en su stack; otros candidatos requieren integración específica.

## Orden de decisión
```text
caso de uso
  ↓
hardware / OS
  ↓
runtime de inferencia
  ↓
optimización
  ↓
capacidades necesarias del harness
  ↓
OSI gate
  ↓
compatibilidad ODS / Magnitude
  ↓
preflight de instalación
  ↓
selección
  ↓
instalación / activación
  ↓
arranque + smoke test
```

## Capacidades
- coding/repository
- shell/tools
- browser/computer use
- memoria/skills
- multi-agent
- MCP/tools
- local model support
- OpenAI-compatible endpoint
- offline/private operation
- observability
- policy/security
- benchmark/evaluation
- installation footprint
- platform compatibility

## Regla de selección
El selector no debe afirmar que los seis candidatos son igualmente instalables. Devuelve candidatos ordenados y su estado de compatibilidad; la instalación se realiza solo cuando el preflight confirme plataforma, dependencias, puertos, runtime y recursos.

## Hardware modesto
Priorizar local-first, footprint razonable, endpoints locales y compatibilidad con llama.cpp/GGUF cuando corresponda. Evitar instalar varios agentes que compitan por puertos, procesos o modelos sin una razón funcional.

## Relación con versiones
V1 permanece operativo. `Selector múltiple evolucionado V1.1` permanece congelado. `Selector Harness V1.2` añade la dimensión harness sin modificar V1.1.
