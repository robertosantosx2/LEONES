# Harnesses — investigación y conocimiento

## Propósito
Los harnesses son la capa de orquestación que ejecuta agentes, herramientas, sesiones, memoria, permisos y/o evaluación. **No son modelos ni runtimes de inferencia.**

Esta ficha es conocimiento independiente del selector. La web debe conservar la separación `Fuente / Evidencia / Estimación / Medición LEONES`.

## Gate OSI
Un candidato OSS instalable debe tener un núcleo con licencia aprobada por OSI. Las licencias de componentes, subdirectorios o ediciones enterprise se registran como excepciones. El gate OSI no demuestra por sí mismo que un proyecto sea instalable en el equipo del usuario.

## Familias canónicas

### A — AGENTE GENERAL
Orquestación de agentes, herramientas, memoria, sesiones y ejecución.
- Hermes Agent — MIT.
- OpenHands — núcleo MIT; componentes enterprise se tratan por separado.
- DeepSeek Harness — MIT; estado experimental/developer preview.

### B — CODING
Trabajo sobre repositorios, terminal, edición, tests y ciclos de reparación.
- OpenCode.
- OpenHands.
- DeepSeek Harness.

### C — LOCAL / HARDWARE MODESTO
Operación local/privada y consumo de modelos o endpoints locales.
- Hermes Agent.
- OpenCode.
- ResearchHarness — experimental; requiere validación propia antes de considerarlo candidato de instalación.

### D — EVALUACIÓN
Ejecución reproducible de benchmarks y evaluación de modelos/agentes.
- lm-evaluation-harness — MIT.
- ResearchHarness — experimental.

### E — SEGURIDAD / REGRESIÓN
Pruebas de seguridad, políticas y regresión de sistemas agentivos.
- OWASP Agent Security Regression Harness.

### F — OBSERVABILIDAD / CONTROL
Budgets, permisos, tracing, checkpoints y recuperación.
- HarnessAgent.
- agent-harness.
- ODS APE — referencia integrada de control, no un harness agente independiente.

### G — INTEROPERABILIDAD / META-HARNESS
Contratos y gateways que permiten trabajar con distintos harnesses.
- HarnessRouter / Unified Harness Protocol (UHP) — Community Edition Apache-2.0.

## Candidatos V1.2
Los seis candidatos congelados para el selector son:
1. Hermes Agent — agente general/local.
2. OpenCode — coding/local.
3. OpenHands — coding/general.
4. DeepSeek Harness — plugin/general, experimental.
5. HarnessRouter/UHP — interoperabilidad/meta-harness.
6. lm-evaluation-harness — evaluación.

**La lista no significa que los seis sean instalables directamente.** V1.2 debe seleccionar según caso de uso y preflight de la máquina.

## Compatibilidad: tres estados
- `DIRECT_INSTALL`: existe una receta reproducible y documentada para instalar el proyecto en la plataforma objetivo.
- `CONSUMER_COMPATIBLE`: puede consumir el runtime/API disponible, pero el sistema objetivo no lo instala por esa vía.
- `INTEGRATION_REQUIRED`: necesita extensión, adaptador, empaquetado o trabajo específico antes de instalar/activar.

Estos estados son independientes de la licencia.

## Magnitude
Magnitude debe tratarse como **entorno/harness local con inference engine propio**, además de perfilador y consumidor de modelos. Que pueda consumir un endpoint compatible no significa que pueda instalar o gestionar cualquier harness externo.

Por ello, en V1.2 `Magnitude=CONSUMER_COMPATIBLE` significa solamente compatibilidad como consumidor/endpoint hasta que exista un preflight de instalación específico. No equivale a `DIRECT_INSTALL`.

## ODS / Osmantic
ODS es un stack de despliegue local, no un instalador universal de harnesses. Su documentación actual integra Hermes Agent como agente local por defecto y OpenCode como asistente de coding dentro del stack. Otros harnesses requieren una receta/extensión propia y deben permanecer en `INTEGRATION_REQUIRED` hasta verificarla.

El repositorio ODS declara Apache-2.0, soporta Linux/Windows/macOS dentro de su matriz y ofrece selección automática de modelos/runtime. Esto es evidencia de compatibilidad del **stack ODS**, no evidencia automática de compatibilidad de cada harness candidato.

## Regla de instalación
Nunca convertir:
`OSI` → `instalable`
ni:
`CONSUMER_COMPATIBLE` → `DIRECT_INSTALL`.

La ruta correcta es:
```text
caso de uso
  ↓
hardware / OS
  ↓
runtime
  ↓
optimización
  ↓
capacidades del harness
  ↓
OSI gate
  ↓
compatibilidad ODS / Magnitude
  ↓
preflight
  ↓
instalación / activación
  ↓
arranque + prueba
```

## Evidencia vs medición
La existencia del proyecto, licencia, documentación de instalación y compatibilidad declarada son evidencia externa. Solo una instalación/arranque ejecutados en la máquina objetivo producen evidencia operacional de LEONES. Los benchmarks posteriores producen `measured_*`; no deben rellenarse con claims de terceros.

## Relación con versiones
- **V1:** selector operativo actual sin sustituir.
- **V1.1:** `Selector múltiple evolucionado`, congelado.
- **V1.2:** `Selector Harness`, preparado pero no tratado como instalación realizada.
