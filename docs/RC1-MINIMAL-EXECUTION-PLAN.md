# LEONES — RC1: plan mínimo de ejecución

> **Estado: PLAN ACTIVO**
>
> Punto de partida: JALÓN 3 cerrado.
>
> Objetivo: obtener una versión mínima de LEONES que funcione de extremo a extremo sobre hardware real y publique conocimiento reproducible en MANADA.

## Principio rector

> **No construir lo que ya existe. Integrar lo que funciona. Medir lo que afirmamos. Documentar todo lo que condiciona una decisión.**

## Resultado final

```text
hardware
  ↓
Magnitude / perfilador
  ↓
LEONES
  ↓
LLMFit + Atlas
  ↓
modelo candidato
  ↓
runtime autorizado
  ↓
llama.cpp u ODS
  ↓
Hermes
  ↓
A01
  ↓
benchmark físico
  ↓
evidence
  ↓
validation
  ↓
recommendation
  ↓
MANADA
```

## Fase 0 — congelación

**Ya cerrada:** JALÓN 3.

No se reabre salvo bug que rompa el contrato.

Gate: árbol limpio, tests verdes, contrato de medición vigente.

## Fase 1 — núcleo mínimo

Construir sólo los objetos que unen las piezas:

- `hardware-profile.v1`;
- `model-candidate.v1`;
- `runtime-plan.v1`;
- `agent-plan.v1`;
- `execution-reference.v1`;
- `evidence-reference.v1`;
- `recommendation.v1`.

El núcleo no ejecuta todavía. Transporta decisiones y procedencia.

**GitHub/CI. No Ubuntu.**

## Fase 2 — adapters externos

### Magnitude

Adapter de lectura/normalización de perfil hardware. Debe distinguir medición, estimación y dato observado.

### LLMFit

Adapter de consulta/normalización de fit. No se copia el motor.

### ODS

Adapter de stack. Describe identidad, versión, instalación, healthcheck, runtime/modelo detectados y entrada al benchmark.

### Hermes

Adapter/harness de A01. Debe conservar trayectoria, tool calls, errores, recovery, resultado y correlación con runtime evidence.

**GitHub/CI. No Ubuntu.**

## Fase 3 — camino sintético completo

Un fixture representa:

```text
hardware → fit → selection → runtime → Hermes → evidence → recommendation
```

Debe ser reproducible en CI sin software externo instalado.

Gate: una sola prueba E2E del contrato completo.

**GitHub/CI. No Ubuntu.**

## Fase 4 — preparación de instalación real

Crear un `physical-run-manifest` que fije antes de tocar la máquina:

- hardware esperado;
- modelo;
- revisión;
- quantización;
- runtime;
- stack;
- Hermes;
- contexto;
- prompt/tarea;
- warm-up;
- N;
- métricas;
- comandos;
- artefactos esperados;
- criterios PASS/FAIL.

**GitHub/CI. No Ubuntu.**

## Fase 5 — Ubuntu: primera intervención imprescindible

Sólo cuando Fases 1–4 estén verdes.

Orden:

1. perfilar hardware real;
2. comprobar herramienta Magnitude si procede;
3. ejecutar selección;
4. instalar/validar ODS si aporta valor;
5. mantener llama.cpp como ruta de fallback/control;
6. instalar/validar Hermes;
7. ejecutar A01;
8. ejecutar benchmark físico;
9. conservar evidencia.

Ubuntu no se utiliza para diseñar contratos.

## Fase 6 — benchmark controlado

Primero benchmark directo de runtime. Después benchmark agentivo Hermes.

No mezclar:

- throughput;
- TTFT;
- memoria;
- potencia;
- score agentivo.

Cada métrica mantiene su propia semántica.

## Fase 7 — comparación

Si ODS y la ruta directa pasan:

```text
misma máquina
misma familia de modelo
misma cuantización
mismo contexto
misma tarea
misma política de warm-up/N
```

Sólo entonces comparar.

Magnitude se usa para caracterizar el hardware; no para sustituir una medición de inferencia.

## Fase 8 — recomendador mínimo

El recomendador debe responder:

1. qué recomienda;
2. por qué;
3. qué parte es estimación;
4. qué parte está medida;
5. qué parte está verificada;
6. bajo qué condiciones;
7. qué alternativas quedaron descartadas y por qué.

No necesita una UI sofisticada para RC1.

## Fase 9 — MANADA

Publicar un registro estructurado con:

- hardware;
- modelo;
- runtime;
- stack;
- harness;
- configuración;
- benchmark;
- evidencia;
- confidence/status;
- timestamp;
- execution_id;
- enlaces a artefactos públicos.

MANADA presenta el conocimiento; no recalcula ni inventa evidencia.

## Fase 10 — release gate

RC1 pasa cuando existe al menos una demostración completa:

```text
REAL HARDWARE = PASS
SELECTION = PASS
RUNTIME = PASS
HERMES/A01 = PASS
MEASUREMENT = PASS
EVIDENCE = PASS
RECOMMENDATION = PASS
MANADA = PASS
```

## Qué se aparca

Hasta después de RC1:

- segunda oleada completa de runtimes;
- soporte multi-GPU amplio;
- automatización multiplataforma extensa;
- dashboards complejos;
- catálogo exhaustivo;
- nuevos benchmarks sin necesidad para el camino canónico.

## Regla de Ubuntu

**Hasta Fase 4: cero Ubuntu.**

La primera petición al usuario será explícita y concreta: instalación, comando exacto, salida esperada y artefactos que deben conservarse.
