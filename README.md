# LEONES — Local Ecosystem of Open Neural Expert Systems

> **IA agéntica Libre/Open para hardware de consumo.**  
> **Linux primero · evidencia real · conocimiento colectivo.**

[🌐 Web de LEONES](https://robertosantosx2.github.io/LEONES/) · [⚙️ Aplicación](https://robertosantosx2.github.io/LEONES/app.html) · [🦁 GitHub](https://github.com/robertosantosx2/LEONES) · [🤝 Contribuir](CONTRIBUTING.md)

---

## 🟢 Estado V1 — A01 con runtime real

**La cadena A01 está integrada y validada de extremo a extremo.** El selector puede producir un plan `runtime-selection.v1`, autorizar un runtime, ejecutar una tarea agentiva real, validar la trayectoria y conservar la medición devuelta por el runtime.

```text
selector
  → runtime-selection.v1
  → plan autorizado
  → Ollama
  → modelo real
  → A01
  → lookup_model → write_report
  → grader
  → runtime-benchmark.v1
  → evidencia medida
```

La ejecución real de referencia utilizó Ollama `0.33.1` y `qwen2.5:0.5b-instruct-q4_K_M` y obtuvo **47.9803 tok/s**, `2.345202 s` de tiempo de pared y **A01 score 1.0**. Es una medición de esa ejecución concreta; no es una cifra universal del modelo.

Los gates asociados a la integración quedaron verdes: **Agentic A01 contract**, **LEONES Contract Tests** y **LEONES V1 Complete Gate**.

### Documentación de referencia

- [`docs/V1-A01-REAL-RUNTIME.md`](docs/V1-A01-REAL-RUNTIME.md) — metodología, recorrido, evidencia y límites de la ejecución real.
- [`docs/V1-CLEAN-ROOM.md`](docs/V1-CLEAN-ROOM.md) — política de limpieza, versionado y conservación de evidencia.
- [`docs/RELEASE-CANDIDATE-1.md`](docs/RELEASE-CANDIDATE-1.md) — plan maestro de Release Candidate 1.
- [`docs/RELEASE-CANDIDATE-1-HERMES.md`](docs/RELEASE-CANDIDATE-1-HERMES.md) — integración de Hermes como harness agéntico de RC1.
- [`docs/RELEASE-CANDIDATE-1-ENDGAME.md`](docs/RELEASE-CANDIDATE-1-ENDGAME.md) — plan de ejecución de RC1 hasta instalación de ODS/Magnitude, benchmarks físicos y publicación en MANADA.
- [`docs/INFERENCE-INTERFACES-ODS-MAGNITUDE.md`](docs/INFERENCE-INTERFACES-ODS-MAGNITUDE.md) — contrato RC1 para separar `llama-cli`, `llama-server`, ODS/Hermes y Magnitude.
- [`docs/RC1-AGENTIC-TASK-CONTRACT.md`](docs/RC1-AGENTIC-TASK-CONTRACT.md) — contrato mínimo de la tarea agentiva comparable, métricas, evidencia y gate de Ubuntu.
- [`PIPELINE_E2E.md`](PIPELINE_E2E.md) — pipeline integral.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contrato de contribución.

---

# 📖 Qué es LEONES

LEONES es un ecosistema abierto para responder una pregunta concreta: **qué modelo, runtime, hardware y configuración permiten ejecutar una tarea real de IA de forma razonable, reproducible, abierta y económicamente sostenible**.

El proyecto no pretende construir otro catálogo de modelos ni otro chatbot. Construye una **cadena de conocimiento y decisión** que conecta descubrimiento, evidencia, hardware, rendimiento, coste, ejecución agéntica y medición física.

La regla fundacional es sencilla:

> **No convertir una afirmación en un hecho por repetición. Descubrir, documentar, verificar, medir y conservar la procedencia.**

Por eso LEONES distingue siempre entre:

- `estimated`: cálculo o estimación;
- `reported`: dato declarado por una fuente externa;
- `observed`: configuración observada en un entorno;
- `measured`: medición ejecutada por LEONES;
- `verified`: dato que ha superado el quality gate definido por el proyecto;
- `unknown`: información que todavía no está demostrada.

---

# 🧭 Orientación RC1: medir productos reales, no reconstruirlos

LEONES reutiliza tanto como sea posible el trabajo de los proyectos especializados.

```text
                     LEONES
                       │
              investigación / Atlas
                       │
                    LLMFit
                       │
              selección y decisión
                       │
             ┌─────────┴─────────┐
             │                   │
          ODS/SOHO          Magnitude/personal
             │                   │
           Hermes        agente + motor propio
             │                   │
      llama-server        llama.cpp integrado
             │                   │
             └─────────┬─────────┘
                       │
                 tarea real
                       │
                 benchmark LEONES
                       │
                 medición física
                       │
                    evidencia
                       │
                    MANADA
```

La responsabilidad de LEONES es **decidir qué probar y medir qué ocurre realmente**. ODS/Hermes y Magnitude aportan el agente y el mecanismo de inferencia que realmente utilizan. LEONES no debe crear un agente ni un servidor paralelo salvo que una necesidad futura esté demostrada y documentada.

Para RC1 se fija una distinción especialmente importante:

- **`llama-cli`**: ejecución directa útil para benchmarks de inferencia de bajo nivel y para el protocolo físico de JALÓN 3.
- **`llama-server`**: servidor HTTP OpenAI-compatible de llama.cpp; es la frontera de inferencia que ODS/Hermes utiliza por defecto.
- **ODS/Hermes**: harness agéntico SOHO que consume un proveedor OpenAI-compatible.
- **Magnitude**: agente personal que incorpora su propio motor de inferencia construido sobre llama.cpp y que además puede interoperar con endpoints OpenAI-compatible.

La documentación normativa de esta separación está en [`docs/INFERENCE-INTERFACES-ODS-MAGNITUDE.md`](docs/INFERENCE-INTERFACES-ODS-MAGNITUDE.md).

---

# 🤝 Contribuir

LEONES es un proyecto abierto y las contribuciones son bienvenidas. Antes de abrir un issue, pull request o aportar una nueva fuente de conocimiento, consulta **[CONTRIBUTING.md](CONTRIBUTING.md)**.

Las contribuciones deben respetar especialmente la procedencia de los datos, la separación entre fuente, evidencia, estimación y medición, y los contratos de CI y pruebas del proyecto.

---

# 🧭 Subproyectos: motivación, objetivo y metodología

Los subproyectos de LEONES se organizan en **capas complementarias**. Cada uno resuelve un problema concreto y entrega datos o capacidades al siguiente. No son aplicaciones aisladas: forman una cadena de evidencia.

```text
                         LEONES
                           │
        ┌──────────────────┼──────────────────┐
        ↓                  ↓                  ↓
   PROSPECTOR           ATLAS             HARDWARE
        │                  │                  │
        └──────────────┬───┴──────────────┬───┘
                       ↓                  ↓
                 EVIDENCIA          PRECIO / TCO
                       │                  │
                       └────────┬─────────┘
                                ↓
                     LLMFIT / MODEL FIT
                                │
                                ↓
                         RECOMENDADOR
                                │
                ┌───────────────┼───────────────┐
                ↓               ↓               ↓
             ROUTER           QUANT          RUNTIME
                │               │               │
                └───────────────┼───────────────┘
                                ↓
                             AGENTS
                                │
                         TAREA REAL / TOOLS
                                ↓
                    BENCHMARK & EVALUATION
                                │
                                ↓
                         MEDICIÓN FÍSICA
                                │
                                ↓
                       CONOCIMIENTO COLECTIVO
```

## 1. Prospector / Prospección diaria

**Motivación.** El ecosistema de IA abierta cambia demasiado deprisa para mantener un catálogo manual. Modelos, repositorios, benchmarks, datasets y herramientas aparecen continuamente.

**Objetivo.** Descubrir candidatos nuevos de forma automatizada, priorizando software y modelos compatibles con los principios de apertura de LEONES.

**Metodología.** Descubrimiento → filtro OSI/licencias → prioridad Copyleft → extracción de identidad → enriquecimiento → deduplicación → generación de feed → incorporación al circuito de evidencia. La prospección **no convierte un candidato en un registro canónico**: eso corresponde a Atlas y su quality gate.

Documentación: [`docs/phases/2026-08-daily-prospection/`](docs/phases/2026-08-daily-prospection/) · [`docs/SOURCE-DISCOVERY.md`](docs/SOURCE-DISCOVERY.md).

## 2. Open LLM Atlas

Atlas conserva la parte de **investigación, conocimiento y procedencia** de LEONES. No se elimina por la orientación RC1: al contrario, proporciona la base que alimenta selección, comparación, evidencia y publicación.

Atlas debe distinguir siempre entre datos externos, observaciones, estimaciones y mediciones físicas promovidas por los quality gates.

---

## Principio operativo RC1

> **Poco código, cada pieza con una responsabilidad, comentarios que expliquen decisiones y README que explique cómo utilizarla.**

LEONES integra antes de duplicar, mide antes de afirmar y documenta antes de congelar.
