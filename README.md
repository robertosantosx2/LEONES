# LEONES — Local Ecosystem of Open Neural Expert Systems

> **IA agéntica libre/open para hardware de consumo.**  
> **Linux primero · evidencia real · conocimiento colectivo.**

[🌐 Web](https://robertosantosx2.github.io/LEONES/) · [⚙️ Aplicación](https://robertosantosx2.github.io/LEONES/app.html) · [🦁 GitHub](https://github.com/robertosantosx2/LEONES) · [🤝 Contribuir](CONTRIBUTING.md)

---

## Qué es LEONES

LEONES construye una cadena reproducible para responder una pregunta práctica:

> **¿Qué modelo, runtime, hardware y configuración permiten realizar una tarea real de IA de forma razonable, reproducible, abierta y económicamente sostenible?**

No es otro catálogo de modelos ni otro chatbot. Es un sistema de **descubrimiento, selección, ejecución, medición, evidencia y decisión**.

Su principio fundamental es simple:

> **Una afirmación no se convierte en un hecho por repetición: se descubre, documenta, contrasta, mide cuando corresponde y conserva con su procedencia.**

---

## Estado y cadena operativa

La arquitectura distingue explícitamente entre **estimación, observación, reporte externo, medición física y verificación**.

```text
DESCUBRIMIENTO
      ↓
ATLAS + EVIDENCIA + APERTURA
      ↓
HARDWARE + PRECIO / TCO
      ↓
LLMFIT / MODEL FIT
      ↓
SELECCIÓN DE MODELO + RUNTIME
      ↓
ROUTER
      ↓
AGENT / TAREA REAL
      ↓
BENCHMARK
      ↓
RUNNER CANÓNICO
      ↓
MEDICIÓN FÍSICA
      ↓
EVIDENCIA REPRODUCIBLE
      ↓
RECOMENDACIÓN
      ↓
CONOCIMIENTO COLECTIVO
```

### Regla de frontera

**GitHub/CI prepara y valida; el host Linux ejecuta y mide.**

CI puede validar contratos, esquemas, código, fixtures, tests y gates. No puede sustituir una medición realizada sobre el hardware y runtime reales.

El **runner existente es la vía canónica de ejecución medida**. LEONES no crea un segundo runner paralelo para JALÓN 3 ni convierte el protocolo de medición en otra arquitectura de ejecución.

```text
GitHub / CI
  ├─ contratos
  ├─ esquemas
  ├─ validadores
  ├─ tests
  └─ preparación del runner
          │
          ▼
HOST LINUX
  ├─ runtime real
  ├─ modelo real
  ├─ hardware real
  ├─ benchmark real
  └─ evidencia
```

---

# Hitos cerrados y en curso

## V1 — A01 con runtime real

La cadena A01 dispone de una integración real de extremo a extremo: selección → autorización de runtime → ejecución de tarea → validación → benchmark → evidencia.

La ejecución de referencia registrada utilizó Ollama `0.33.1` con `qwen2.5:0.5b-instruct-q4_K_M` y obtuvo **47.9803 tok/s**, `2.345202 s` de tiempo de pared y **A01 score 1.0**.

Estos valores pertenecen a esa ejecución concreta y **no son una cifra universal del modelo**.

## JALÓN 2 — evidencia física

JALÓN 2 estableció el puente entre ejecución física y conservación de evidencia con `llama.cpp`.

Referencia histórica registrada:

```text
llama.cpp
Qwen3 0.6B · Q4_K_M
CPU · 4 threads
5 ejecuciones
43.6 tok/s de media
```

La evidencia física de JALÓN 2 es histórica e inmutable: los resultados posteriores no deben reescribirla para hacerlos coincidir.

## JALÓN 3 — protocolo de medición real

JALÓN 3 convierte la medición real en un **contrato operativo reproducible**.

El contrato se prepara y valida en GitHub. El runner existente es la vía de ejecución. El host Linux se utiliza únicamente cuando hace falta producir evidencia que requiere runtime y hardware físicos.

**Criterio de cierre:** JALÓN 3 no queda empíricamente cerrado hasta que una ejecución física autorizada produzca evidencia válida conforme al protocolo congelado.

---

# Componentes principales

## 1. Prospector

Descubre modelos, repositorios, benchmarks, runtimes, datasets y herramientas. Filtra candidatos según los criterios del proyecto y alimenta el Atlas.

**No convierte candidatos en conocimiento canónico.**

Docs: [`docs/phases/2026-08-daily-prospection/`](docs/phases/2026-08-daily-prospection/) · [`docs/SOURCE-DISCOVERY.md`](docs/SOURCE-DISCOVERY.md)

## 2. Open LLM Atlas

Mantiene la identidad canónica de modelos y familias y conserva la evidencia que respalda sus atributos.

**Atlas es fuente de identidad y evidencia, no un ranking arbitrario.**

Docs: [`atlas/README.md`](atlas/README.md) · [`docs/phases/2026-08-atlas-expanded/`](docs/phases/2026-08-atlas-expanded/)

## 3. JGB / apertura

Clasifica la apertura mediante dimensiones explícitas y evidencia primaria. Apertura, velocidad, precio y calidad de tarea son dimensiones distintas.

Docs: [`web/proyectos/atlas/openness/JGB-INDEX.md`](web/proyectos/atlas/openness/JGB-INDEX.md)

## 4. Hardware

Relaciona modelos con CPU, RAM, GPU/VRAM, almacenamiento y otras capacidades relevantes.

La compatibilidad estimada **no equivale a rendimiento medido**.

Docs: [`docs/phases/2026-08-hardware-matrix/`](docs/phases/2026-08-hardware-matrix/) · [`docs/completed/H08-HARDWARE-MATRIX.md`](docs/completed/H08-HARDWARE-MATRIX.md)

## 5. Precio / TCO

Conserva observaciones de precio y las combina con capacidad y rendimiento para estudiar el coste de una solución completa.

Docs: [`docs/phases/2026-08-hardware-pricing/`](docs/phases/2026-08-hardware-pricing/) · [`docs/phases/2026-08-economic-ranking-v1/`](docs/phases/2026-08-economic-ranking-v1/)

## 6. LLMFit

LLMFit aporta una **primera estimación de encaje modelo ↔ máquina** y permite reducir candidatos antes de ejecutar o descargar modelos cuando la evidencia disponible lo permite.

```text
hardware
   ↓
LLMFit / fit estimado
   ↓
candidatos
   ↓
Atlas + evidencia + cuantización + runtime
   ↓
benchmark LEONES
   ↓
medición física
```

LLMFit **no es fuente de verdad** y nunca convierte una estimación en `measured`.

Docs: [`docs/integrations/LLMFIT/`](docs/integrations/LLMFIT/) · [`docs/phases/2026-08-atlas-recommendation-pipeline/`](docs/phases/2026-08-atlas-recommendation-pipeline/)

## 7. CABE / RULA

Conserva `tokens_per_second` como dato primario y deriva una clasificación operativa:

```text
<1 tok/s       → No CABE
1–<10 tok/s    → CABE
10–100 tok/s   → RULA
>100 tok/s     → RULA+
```

La clasificación nunca sustituye a la medición.

Docs: [`docs/phases/2026-08-cabe-rula/`](docs/phases/2026-08-cabe-rula/) · [`docs/completed/H09-CABE-RULA.md`](docs/completed/H09-CABE-RULA.md)

## 8. Selección, Router y recomendación

LEONES separa la decisión declarativa de la ejecución.

Una ejecución queda determinada por la combinación explícita de:

`modelo + cuantización + runtime + hardware + configuración`

El selector y el Router trabajan con las restricciones y evidencias disponibles. El rendimiento no se atribuye al modelo ignorando runtime, cuantización o hardware.

LLMFit puede filtrar candidatos; la medición física prevalece sobre la estimación cuando ambas existen.

Docs: [`docs/PILLARS.md`](docs/PILLARS.md) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## 9. Agentes y evaluación

LEONES evalúa tareas agentivas mediante tareas reproducibles, herramientas, trayectoria, resultado, grading, tiempo, coste, seguridad y artefactos.

Los benchmarks orientados a tareas complementan los benchmarks externos: el objetivo final es conocer **qué tareas se completan en qué condiciones**, no reducir todo el sistema a una única cifra.

Docs: [`docs/EVALUACION_AGENTIC_TESTS.md`](docs/EVALUACION_AGENTIC_TESTS.md) · [`docs/sources/ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md`](docs/sources/ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md)

## 10. Runner y medición física

El runner existente ocupa una posición única en la arquitectura:

```text
selección autorizada
        ↓
runner
        ↓
runtime
        ↓
modelo + hardware
        ↓
benchmark
        ↓
medición
        ↓
evidence
```

El runner **no decide qué resultado es verdadero** ni inventa mediciones. Ejecuta la configuración autorizada y conserva los datos necesarios para que el benchmark y los validadores puedan determinar si la ejecución es válida.

No se promocionan fixtures a evidencia física. Una ejecución fallida puede conservarse como incidente cuando corresponda, pero nunca se presenta como benchmark válido.

Docs: [`docs/completed/`](docs/completed/) · [`docs/RESULT_SCHEMA.md`](docs/RESULT_SCHEMA.md)

## 11. ODS, Magnitude, FreeToken, AirLLM, Ollama y llama.cpp

LEONES puede utilizar herramientas externas para descubrimiento, profiling, estimación, ejecución o comparación.

La separación es esencial:

- **evidencia externa** sigue siendo evidencia externa;
- **estimación** sigue siendo estimación;
- **medición LEONES** requiere una ejecución LEONES reproducible;
- una herramienta externa no se convierte automáticamente en parte de la verdad canónica del proyecto.

Cuando una herramienta se integra, se documentan su función, procedencia, supuestos y límites. Se reutiliza su arquitectura cuando es adecuada; **no se crea innecesariamente un sistema paralelo**.

Docs: [`docs/subprojects/ods/`](docs/subprojects/ods/) · [`docs/subprojects/magnitude/`](docs/subprojects/magnitude/)

---

# Contratos y evidencia

LEONES utiliza contratos versionados para evitar que selección, ejecución y medición se mezclen.

En particular, `runtime-selection.v1.1` es deliberadamente declarativo: identifica runtime, adaptador, modelo, compatibilidad, restricciones y razón de selección, pero no contiene comandos de ejecución ni rendimiento medido.

```text
runtime-selection
      ↓
plan validado
      ↓
adapter / runner
      ↓
runtime-execution
      ↓
benchmark
      ↓
evidence
```

La frontera evita que un plan de selección se convierta accidentalmente en una orden de ejecución o en una afirmación de rendimiento.

---

# Modelo de estados de evidencia

```text
FUENTE
  ↓
EVIDENCIA
  ↓
REPORTE / OBSERVACIÓN / ESTIMACIÓN
  ↓
MEDICIÓN LEONES
  ↓
VERIFICACIÓN
  ↓
CONOCIMIENTO PUBLICABLE
```

| Estado | Significado |
|---|---|
| `estimated` | cálculo o estimación |
| `reported` | dato declarado por una fuente externa |
| `observed` | configuración observada en un entorno |
| `measured` | medición ejecutada por LEONES |
| `verified` | dato que superó el quality gate correspondiente |
| `unknown` | todavía no demostrado |

**Nunca se eleva un estado por inferencia, conveniencia o repetición.**

---

# Calidad y reproducibilidad

La CI forma parte del contrato del proyecto.

Todo cambio que afecte a código, contratos, esquemas, selección de runtimes, ejecución, benchmarks o datos debe conservar sus consumidores y superar las pruebas y validaciones correspondientes.

Principios:

- contratos explícitos y versionados;
- cambios mínimos antes que reescrituras innecesarias;
- separación estricta entre fixtures y evidencia;
- procedencia conservada;
- mediciones repetibles;
- ningún dato físico inventado;
- documentación alineada con el código real;
- una única vía canónica de ejecución medida: el runner existente.

Para contribuir: [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

# Documentación clave

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitectura general.
- [`docs/PILLARS.md`](docs/PILLARS.md) — pilares del sistema.
- [`PIPELINE_E2E.md`](PIPELINE_E2E.md) — recorrido integral.
- [`docs/RESULT_SCHEMA.md`](docs/RESULT_SCHEMA.md) — resultados y evidencia.
- [`docs/V1-A01-REAL-RUNTIME.md`](docs/V1-A01-REAL-RUNTIME.md) — A01 con runtime real.
- [`docs/V1-CLEAN-ROOM.md`](docs/V1-CLEAN-ROOM.md) — limpieza, versionado y evidencia.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribución.

---

# Licencia

Consulta [`LICENSE`](LICENSE) y la documentación específica de cada subproyecto o dependencia externa. Las licencias de terceros no deben interpretarse como licencia de LEONES.
