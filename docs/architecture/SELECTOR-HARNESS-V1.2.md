# Selector Harness V1.2

## Estado
**PREPARADO PARA V1.2**

## Objetivo
Seleccionar los mejores harnesses OSS para instalar/activar en el ordenador del usuario, teniendo en cuenta caso de uso, hardware, runtime, optimizaciones, plataforma y compatibilidad real.

## Filtro OSI
Solo candidatos con núcleo bajo licencia OSI aprobada entran en la lista instalable OSS. Componentes con licencias diferentes se registran como excepciones y no se confunden con el núcleo.

## Los 6 candidatos V1.2
| Prioridad | Harness | Familia principal | Licencia | ODS/Osmantic | Magnitude | Estado |
|---|---|---|---|---|---|---|
| 1 | Hermes Agent | general/local | MIT | DIRECT_INSTALL | CONSUMER_COMPATIBLE | candidato principal |
| 2 | OpenCode | coding/local | OSS/OSI | DIRECT_INSTALL | CONSUMER_COMPATIBLE | candidato principal |
| 3 | OpenHands | coding/general | MIT núcleo | INTEGRATION_REQUIRED | CONSUMER_COMPATIBLE vía endpoint | candidato |
| 4 | DeepSeek Harness | plugin/general | MIT | INTEGRATION_REQUIRED | CONSUMER_COMPATIBLE vía endpoint/adaptador | developer preview |
| 5 | HarnessRouter / UHP | interoperability | Apache-2.0 CE | INTEGRATION_REQUIRED | CONSUMER_COMPATIBLE como gateway | meta-harness |
| 6 | lm-evaluation-harness | evaluation | MIT | INTEGRATION_REQUIRED | CONSUMER_COMPATIBLE | evaluación, no agente |

## Importante: Magnitude y ODS no son equivalentes
Magnitude incluye su propio harness e inference engine y perfila hardware/modelos. Puede consumir endpoints OpenAI-compatible, pero no debe declararse instalador universal de otros harnesses.

ODS es un stack de despliegue que actualmente integra Hermes como agente por defecto y OpenCode como IDE/agente. Otros candidatos necesitan una extensión o receta propia antes de poder declararse `DIRECT_INSTALL`.

## Estados de compatibilidad
- `DIRECT_INSTALL`: receta de instalación comprobada en el sistema.
- `CONSUMER_COMPATIBLE`: el harness puede consumir el runtime/API del sistema, pero no es instalado por él.
- `INTEGRATION_REQUIRED`: requiere adaptación, extensión o empaquetado.

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
capacidad de harness necesaria
  ↓
OSI gate
  ↓
compatibilidad ODS / Magnitude
  ↓
preflight de instalación
  ↓
6 candidatos
  ↓
selección final
```

## Capacidades a puntuar
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

## Regla de instalación
Un candidato solo puede aparecer como **instalable** si existe una ruta de instalación reproducible para la plataforma del usuario. `CONSUMER_COMPATIBLE` no equivale a instalable.

## Hardware modesto
Priorizar local-first, bajo footprint, endpoints locales y compatibilidad con llama.cpp/GGUF cuando el hardware lo requiera. Evitar instalar varios harnesses que compitan por los mismos procesos/puertos sin necesidad.

## Relación con V1.1
V1.1 sigue congelado. V1.2 añade la dimensión harness después del camino de selección de modelo/runtime/optimización.
