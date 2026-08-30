# LEONES — Local Ecosystem of Open Neural Expert Systems

> **IA agéntica libre/open para hardware de consumo.**  
> **Linux primero · evidencia real · conocimiento colectivo.**

[🌐 Web](https://robertosantosx2.github.io/LEONES/) · [⚙️ Aplicación](https://robertosantosx2.github.io/LEONES/app.html) · [🦁 GitHub](https://github.com/robertosantosx2/LEONES) · [🤝 Contribuir](CONTRIBUTING.md)

---

## 🟢 Estado del proyecto

LEONES está construyendo una cadena reproducible para pasar de **descubrir un modelo** a **saber si sirve para una tarea concreta en un hardware concreto**.

La arquitectura distingue explícitamente entre estimación, observación, reporte externo, medición física y verificación.

### Cadena operativa

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
RUNNER
     ↓
MEDICIÓN FÍSICA
     ↓
EVIDENCIA REPRODUCIBLE
     ↓
RECOMENDACIÓN
     ↓
CONOCIMIENTO COLECTIVO
```

### V1 — A01 con runtime real

La cadena A01 dispone de una integración real de extremo a extremo: selección → autorización de runtime → ejecución de tarea → validación → benchmark → evidencia.

La ejecución de referencia registrada en el proyecto utilizó Ollama `0.33.1` con `qwen2.5:0.5b-instruct-q4_K_M` y obtuvo **47.9803 tok/s**, `2.345202 s` de tiempo de pared y **A01 score 1.0**. Estos valores describen esa ejecución concreta; **no son una cifra universal del modelo**.

### JALÓN 2 — evidencia física

JALÓN 2 estableció el puente de ejecución física y conservación de evidencia con `llama.cpp`. Su referencia registrada es **Qwen3 0.6B · Q4_K_M · CPU · 4 threads · 5 ejecuciones · 43.6 tok/s de media**.

La evidencia física y sus artefactos son históricos: no deben reescribirse para hacer coincidir resultados posteriores.

### JALÓN 3 — contrato de medición

JALÓN 3 convierte la medición real en un **contrato operativo reproducible**. El diseño, los esquemas, validadores, runner y gates de CI se preparan en GitHub; el host Linux se reserva para la ejecución física que ningún CI puede sustituir.

**Regla:** JALÓN 3 no se considera empíricamente cerrado hasta que una ejecución física autorizada produzca evidencia válida bajo el protocolo congelado.

---

# 📖 Qué es LEONES

LEONES responde a una pregunta práctica:

> **¿Qué modelo, runtime, hardware y configuración permiten realizar una tarea real de IA de forma razonable, reproducible, abierta y económicamente sostenible?**

No es otro catálogo de modelos ni otro chatbot. Es una **cadena de conocimiento y decisión** que conecta modelos, apertura, hardware, rendimiento, coste, runtimes, agentes y medición física.

Principio fundacional:

> **No convertir una afirmación en un hecho por repetición: descubrir, documentar, verificar, medir y conservar la procedencia.**

---

# 🧭 Componentes principales

## 1. Prospector

Descubre modelos, repositorios, benchmarks, runtimes, datasets y herramientas. Filtra por criterios de apertura y genera candidatos para Atlas.

**No convierte candidatos en conocimiento canónico.**

Docs: [`docs/phases/2026-08-daily-prospection/`](docs/phases/2026-08-daily-prospection/) · [`docs/SOURCE-DISCOVERY.md`](docs/SOURCE-DISCOVERY.md)

## 2. Open LLM Atlas

Mantiene la identidad canónica de modelos y familias y conserva la evidencia que respalda sus atributos.

**Atlas es fuente de identidad y evidencia, no un ranking arbitrario.**

Docs: [`atlas/README.md`](atlas/README.md) · [`docs/phases/2026-08-atlas-expanded/`](docs/phases/2026-08-atlas-expanded/)

## 3. JGB / apertura

Clasifica la apertura de los modelos mediante dimensiones explícitas y evidencia primaria. No mezcla apertura con velocidad, precio o calidad de tarea.

Docs: [`web/proyectos/atlas/openness/JGB-INDEX.md`](web/proyectos/atlas/openness/JGB-INDEX.md)

## 4. Hardware

Relaciona modelos con CPU, RAM, GPU/VRAM, almacenamiento y otras capacidades relevantes. La compatibilidad estimada **no equivale a rendimiento medido**.

Docs: [`docs/phases/2026-08-hardware-matrix/`](docs/phases/2026-08-hardware-matrix/) · [`docs/completed/H08-HARDWARE-MATRIX.md`](docs/completed/H08-HARDWARE-MATRIX.md)

## 5. Precio / TCO

Conserva observaciones de precio y las utiliza junto con capacidad y rendimiento para estudiar el coste de una solución completa.

Docs: [`docs/phases/2026-08-hardware-pricing/`](docs/phases/2026-08-hardware-pricing/) · [`docs/phases/2026-08-economic-ranking-v1/`](docs/phases/2026-08-economic-ranking-v1/)

## 6. LLMFit

LLMFit aporta una **primera estimación de encaje modelo ↔ máquina**. Sirve para reducir candidatos antes de ejecutar o descargar modelos cuando la evidencia lo permita.

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

La clasificación **nunca sustituye a la medición**.

Docs: [`docs/phases/2026-08-cabe-rula/`](docs/phases/2026-08-cabe-rula/) · [`docs/completed/H09-CABE-RULA.md`](docs/completed/H09-CABE-RULA.md)

## 8. Recomendador

Combina evidencia de modelos, apertura, hardware, precio y rendimiento para producir recomendaciones trazables. LLMFit puede actuar como filtro inicial; la medición física prevalece sobre la estimación cuando ambas existen.

Docs: [`docs/phases/2026-08-atlas-recommendation-pipeline/`](docs/phases/2026-08-atlas-recommendation-pipeline/) · [`docs/completed/H10-ATLAS-RECOMMENDER-PIPELINE.md`](docs/completed/H10-ATLAS-RECOMMENDER-PIPELINE.md)

## 9. Runtime / Router / Quant

Una ejecución se identifica por la combinación explícita:

`modelo + cuantización + runtime + hardware + configuración`

El Router decide dentro de las restricciones y evidencia disponibles. El rendimiento no se atribuye al modelo ignorando runtime, cuantización o hardware.

Docs: [`docs/PILLARS.md`](docs/PILLARS.md) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## 10. Agentes y evaluación

LEONES evalúa tareas agentivas mediante tareas reproducibles, herramientas, trayectoria, resultado, grading, tiempo, coste, seguridad y artefactos.

Docs: [`docs/EVALUACION_AGENTIC_TESTS.md`](docs/EVALUACION_AGENTIC_TESTS.md) · [`docs/sources/ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md`](docs/sources/ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md)

## 11. Runner y medición física

El **runner es la vía canónica de ejecución medida**. Su función es convertir una configuración autorizada en una ejecución reproducible y conservar la evidencia necesaria.

La frontera es deliberada:

```text
GitHub / CI
  → contratos
  → esquemas
  → validadores
  → tests
  → runner preparado
          │
          ▼
HOST LINUX
  → runtime real
  → modelo real
  → hardware real
  → medición real
  → evidencia
```

No se inventan mediciones en CI. No se promocionan fixtures a evidencia física. Una ejecución fallida se conserva como incidente cuando corresponde, pero no se presenta como benchmark válido.

Docs: [`docs/completed/`](docs/completed/) · [`docs/RESULT_SCHEMA.md`](docs/RESULT_SCHEMA.md)

## 12. ODS, Magnitude, FreeToken y otros proyectos externos

LEONES puede estudiar e integrar herramientas externas como **ODS, Magnitude, FreeToken, AirLLM, Ollama o llama.cpp**.

La regla es siempre la misma: **una fuente externa aporta conocimiento o evidencia externa; una medición LEONES sigue siendo una medición LEONES**.

Cuando un componente externo se integra, se documentan su función, procedencia, supuestos y límites. No se duplica innecesariamente su arquitectura dentro de LEONES.

Docs: [`docs/subprojects/ods/`](docs/subprojects/ods/) · [`docs/subprojects/magnitude/`](docs/subprojects/magnitude/)

---

# 🔬 Modelo de evidencia

LEONES utiliza una cadena explícita de procedencia:

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

Estados utilizados en el proyecto:

| Estado | Significado |
|---|---|
| `estimated` | cálculo o estimación |
| `reported` | dato declarado por una fuente externa |
| `observed` | configuración observada en un entorno |
| `measured` | medición ejecutada por LEONES |
| `verified` | dato que superó el quality gate correspondiente |
| `unknown` | todavía no demostrado |

**Nunca se debe elevar un estado por inferencia o conveniencia.**

---

# 🧪 Calidad y reproducibilidad

La CI forma parte del contrato del proyecto.

Un cambio que afecte a código, contratos, esquemas, selección de runtimes, ejecución, benchmarks o datos debe mantener sus consumidores y pasar las pruebas y validaciones correspondientes.

Principios:

- contratos explícitos y versionados;
- pruebas deterministas cuando sea posible;
- evidencia separada de fixtures;
- procedencia conservada;
- mediciones repetibles;
- ningún dato físico inventado;
- cambios mínimos antes que reescrituras innecesarias;
- documentación alineada con el código real.

Para contribuir: [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

# 📚 Documentación clave

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitectura general.
- [`docs/PILLARS.md`](docs/PILLARS.md) — pilares del sistema.
- [`PIPELINE_E2E.md`](PIPELINE_E2E.md) — recorrido integral.
- [`docs/RESULT_SCHEMA.md`](docs/RESULT_SCHEMA.md) — resultados y evidencia.
- [`docs/V1-A01-REAL-RUNTIME.md`](docs/V1-A01-REAL-RUNTIME.md) — A01 con runtime real.
- [`docs/V1-CLEAN-ROOM.md`](docs/V1-CLEAN-ROOM.md) — limpieza, versionado y evidencia.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribución.

---

# 📜 Licencia

Consulta los ficheros de licencia del repositorio y la documentación específica de cada subproyecto o dependencia externa. Las licencias de terceros no deben interpretarse como licencia de LEONES.
