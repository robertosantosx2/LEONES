# LEONES — Local Ecosystem of Open Neural Expert Systems

> **IA agéntica Libre/Open para hardware de consumo.**  
> **Linux primero · evidencia real · conocimiento colectivo.**

[🌐 Web de LEONES](https://robertosantosx2.github.io/LEONES/) · [⚙️ Aplicación](https://robertosantosx2.github.io/LEONES/app.html) · [🦁 GitHub](https://github.com/robertosantosx2/LEONES) · [🤝 Contribuir](CONTRIBUTING.md)

---

## 🟢 Estado V1

**La cadena A01 está integrada y validada.** LEONES ya puede recorrer el camino completo desde una selección de modelo hasta un runtime real, ejecutar una tarea agentiva, validar su trayectoria y conservar la medición devuelta por el runtime.

```text
selector
  → runtime-selection.v1
  → execution plan autorizado
  → Ollama
  → modelo real
  → A01
  → tools
  → grader
  → runtime-benchmark.v1
  → evidencia medida
```

La prueba real realizada con Ollama `0.33.1` y `qwen2.5:0.5b-instruct-q4_K_M` produjo **47.9803 tok/s**, `2.345202 s` de tiempo de pared y `A01 score = 1.0`. Esta cifra es una medición de esa ejecución, no una afirmación universal sobre el modelo o el hardware.

Los tres gates asociados a la corrección de la integración quedaron verdes: **Agentic A01 contract**, **LEONES Contract Tests** y **LEONES V1 Complete Gate**.

### Documentación de referencia

- [V1 — A01 con runtime real](docs/V1-A01-REAL-RUNTIME.md): recorrido técnico, evidencia, metodología y límites.
- [V1 — Limpieza, fijación y conservación de evidencia](docs/V1-CLEAN-ROOM.md): política para separar código, estado local, fixtures y evidencia.
- [PIPELINE_E2E.md](PIPELINE_E2E.md): descripción integral del pipeline.
- [CONTRIBUTING.md](CONTRIBUTING.md): contrato para contribuir sin romper procedencia, contratos o CI.

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

**Motivación.** El ecosistema de IA abierta cambia demasiado deprisa para mantener un catálogo manual. Modelos, repositorios, benchmarks, runtimes, datasets y herramientas aparecen continuamente.

**Objetivo.** Descubrir candidatos nuevos de forma automatizada, priorizando software y modelos compatibles con los principios de apertura de LEONES.

**Metodología.** Descubrimiento → filtro OSI/licencias → prioridad Copyleft → extracción de identidad → enriquecimiento → deduplicación → generación de feed → incorporación al circuito de evidencia. La prospección **no convierte un candidato en un registro canónico**: eso corresponde a Atlas y su quality gate.

Documentación: [`docs/phases/2026-08-daily-prospection/`](docs/phases/2026-08-daily-prospection/) · [`docs/SOURCE-DISCOVERY.md`](docs/SOURCE-DISCOVERY.md).

## 2. Open LLM Atlas

**Motivación.** La información sobre modelos está fragmentada, cambia con frecuencia y mezcla nombres, familias, checkpoints, variantes, organizaciones y afirmaciones de apertura.

**Objetivo.** Construir la base canónica de identidad y evidencia de modelos y familias de modelos que LEONES puede utilizar sin perder procedencia.

**Metodología.** Feed → identidad → evidencia → quality gate → `verified-only` → catálogo canónico. Los registros sin evidencia suficiente permanecen `unknown`/`unverified`; no se rellenan por inferencia.

Atlas es la **fuente de identidad y evidencia**, no un ranking arbitrario.

Documentación: [`atlas/README.md`](atlas/README.md) · [`docs/phases/2026-08-atlas-expanded/`](docs/phases/2026-08-atlas-expanded/).

## 3. Índice JGB / apertura

**Motivación.** "Open source", "open weights", "open model" y "open research" no significan necesariamente lo mismo. Un único porcentaje de apertura ocultaría diferencias importantes.

**Objetivo.** Medir y documentar sistemáticamente la apertura de cada modelo con criterios explícitos, manteniendo separados los grados de libertad y su evidencia.

**Metodología.** Definir criterios → localizar evidencia primaria → clasificar cada dimensión → conservar procedencia → publicar únicamente lo que esté suficientemente respaldado. JGB no se mezcla con rendimiento, precio o velocidad.

Documentación: [`web/proyectos/atlas/openness/JGB-INDEX.md`](web/proyectos/atlas/openness/JGB-INDEX.md) · [`docs/phases/2026-08-jgb-systematic/`](docs/phases/2026-08-jgb-systematic/).

## 4. Matriz de hardware

**Motivación.** Un modelo puede ser excelente en un benchmark y, sin embargo, ser inútil para una máquina concreta por RAM, VRAM, ancho de banda, CPU, almacenamiento o aceleración disponible.

**Objetivo.** Relacionar modelos y configuraciones con perfiles reales de hardware, inicialmente CPU × RAM × GPU y posteriormente con mediciones más completas.

**Metodología.** Detectar hardware → normalizar perfil → estimar requisitos → generar matriz de compatibilidad → contrastar con mediciones → conservar diferencia entre compatibilidad, estimación y rendimiento físico.

La matriz **no es un benchmark físico** por sí misma.

Documentación: [`docs/phases/2026-08-hardware-matrix/`](docs/phases/2026-08-hardware-matrix/) · [`docs/completed/H08-HARDWARE-MATRIX.md`](docs/completed/H08-HARDWARE-MATRIX.md).

## 5. Hardware Pricing / precios

**Motivación.** El mejor hardware técnico no es necesariamente la mejor compra. La decisión necesita precio temporal y no solo especificaciones.

**Objetivo.** Construir un histórico reproducible de precios y utilizar observaciones válidas para enriquecer la recomendación hardware/modelo.

**Metodología.** Extracción periódica → normalización → control de calidad → deduplicación → histórico → integración con perfiles hardware → publicación de observaciones.

Documentación: [`docs/phases/2026-08-hardware-pricing/`](docs/phases/2026-08-hardware-pricing/) · [`docs/atlas-hardware-price-integration.md`](docs/atlas-hardware-price-integration.md).

## 6. Ranking económico / TCO

**Motivación.** Comparar precio de compra sin rendimiento, consumo, capacidad o vida útil produce decisiones engañosas.

**Objetivo.** Introducir una capa económica separada de la calidad del modelo y del rendimiento bruto.

**Metodología.** Precio observado + perfil hardware + capacidad/rendimiento disponible → métricas económicas → ranking, manteniendo JGB, rendimiento, hardware y precio como dimensiones independientes.

Documentación: [`docs/phases/2026-08-economic-ranking-v1/`](docs/phases/2026-08-economic-ranking-v1/).

## 7. LLMFit — primera estimación de encaje modelo ↔ máquina

**Motivación.** Antes de ejecutar un benchmark físico o descargar varios gigabytes de pesos, LEONES necesita una **primera estimación rápida y barata** de qué modelos son candidatos razonables para el hardware disponible. Esto evita gastar tiempo y almacenamiento en modelos que claramente no encajan y mejora la primera recomendación al usuario.

**Objetivo.** Incorporar [llmfit](https://www.llmfit.org/) como **capa de estimación inicial de model fit**, aprovechando su análisis de hardware y su capacidad de valorar qué modelos pueden ejecutarse en una máquina concreta. El proyecto de referencia es [`AlexsJones/llmfit`](https://github.com/AlexsJones/llmfit).

LLMFit **no sustituye Atlas, el recomendador ni los benchmarks de LEONES**. Es una señal previa de encaje. Su resultado debe conservarse como `estimated`/`reported` según el origen del dato y nunca promocionarse automáticamente a `measured`.

**Metodología.**

```text
HARDWARE DEL USUARIO
        ↓
   LLMFit / FIT
        ↓
 candidatos iniciales
        ↓
Atlas + apertura + evidencia
        ↓
 requisitos / cuantización / runtime
        ↓
 benchmark LEONES
        ↓
  MEDICIÓN REAL
        ↓
 recomendación final
```

El flujo previsto es:

1. detectar CPU, RAM, GPU/VRAM y otras capacidades relevantes;
2. ejecutar LLMFit como filtro/estimador inicial;
3. conservar sus supuestos y fuente;
4. cruzar candidatos con Atlas y evidencia técnica;
5. incorporar cuantización, contexto y runtime reales;
6. descartar candidatos incompatibles antes de descargar cuando la evidencia lo justifique;
7. ejecutar benchmark LEONES sobre los candidatos restantes;
8. sustituir la hipótesis por medición cuando exista evidencia física;
9. retroalimentar la matriz y el recomendador sin sobrescribir el histórico de estimaciones.

**Regla de arquitectura:** LLMFit es **front-end de estimación**, no fuente de verdad. LEONES mantiene la procedencia y conserva la diferencia entre `fit estimado` y `rendimiento medido`.

Documentación prevista: [`docs/integrations/LLMFIT/`](docs/integrations/LLMFIT/) · [`docs/phases/2026-08-atlas-recommendation-pipeline/`](docs/phases/2026-08-atlas-recommendation-pipeline/).

## 8. CABE / RULA

**Motivación.** Saber si un modelo "cabe" en una máquina no es suficiente; también importa si la velocidad resultante hace viable una tarea.

**Objetivo.** Traducir rendimiento medido en categorías operativas sin destruir el dato continuo.

**Metodología.** Conservar `tokens_per_second` como métrica primaria y derivar clasificación:

```text
<1 tok/s      → No CABE
1–<10 tok/s   → CABE
10–100 tok/s  → RULA
>100 tok/s    → RULA+
```

La clasificación nunca sustituye a la medición.

Documentación: [`docs/phases/2026-08-cabe-rula/`](docs/phases/2026-08-cabe-rula/) · [`docs/completed/H09-CABE-RULA.md`](docs/completed/H09-CABE-RULA.md).

## 9. Atlas → recomendador

**Motivación.** Un catálogo no responde a la pregunta del usuario: "¿qué modelo debería utilizar yo para esta tarea y este hardware?".

**Objetivo.** Convertir evidencia de modelos + hardware + rendimiento + apertura + precio en recomendaciones trazables.

**Metodología.** Prospección → ingesta → evidencia → calidad → hipótesis → matriz hardware → **LLMFit como estimación inicial cuando esté disponible** → recomendación → enriquecimiento → validación → publicación. CABE/RULA, JGB y los datos económicos permanecen como dimensiones independientes.

Documentación: [`docs/phases/2026-08-atlas-recommendation-pipeline/`](docs/phases/2026-08-atlas-recommendation-pipeline/) · [`docs/completed/H10-ATLAS-RECOMMENDER-PIPELINE.md`](docs/completed/H10-ATLAS-RECOMMENDER-PIPELINE.md).

## 10. Benchmarks reales

**Motivación.** Los benchmarks publicados por terceros son imprescindibles, pero no sustituyen la medición en el hardware y runtime que realmente utiliza el usuario.

**Objetivo.** Crear una batería reproducible que mida modelos, runtimes y tareas en condiciones controladas.

**Metodología.** Fijar hardware + modelo + cuantización + runtime + contexto → ejecutar tarea controlada → recoger tiempo, tokens y resultado → validar → almacenar evidencia con procedencia. La medición LEONES nunca se confunde con una cifra declarada por el fabricante.

Documentación: [`docs/RESULT_SCHEMA.md`](docs/RESULT_SCHEMA.md) · [`docs/completed/BENCHMARK-MEASURED-EVIDENCE.md`](docs/completed/BENCHMARK-MEASURED-EVIDENCE.md) · [`docs/completed/PHYSICAL-BENCHMARK-VALIDATION.md`](docs/completed/PHYSICAL-BENCHMARK-VALIDATION.md).

## 11. Evaluación agentiva

**Motivación.** Un agente no se puede evaluar solo por tokens/segundo ni por una respuesta final. Importan herramientas, trayectoria, recuperación ante errores, coste, tiempo, seguridad y artefactos producidos.

**Objetivo.** Evaluar agentes mediante tareas reales y reproducibles, no únicamente mediante preguntas sintéticas.

**Metodología.** Tarea → entorno controlado → herramientas → trazas → outcome → trajectory → grading → coste/tiempo → seguridad → artefactos → informe. Las métricas se conservan separadas para evitar que una única puntuación oculte fallos.

Documentación: [`docs/EVALUACION_AGENTIC_TESTS.md`](docs/EVALUACION_AGENTIC_TESTS.md) · [`docs/sources/ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md`](docs/sources/ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md).

## 12. Runtime / Router / Quant

**Motivación.** El modelo no ejecuta solo: el resultado depende del motor, cuantización, placement, contexto, batching, aceleración y estrategia de routing.

**Objetivo.** Separar modelo, runtime y configuración para poder comparar combinaciones reproducibles y seleccionar dinámicamente la mejor opción para una tarea.

**Metodología.** Registrar cada ejecución como una combinación explícita `modelo + cuantización + runtime + hardware + configuración`; medir; comparar; alimentar Router sin ocultar las condiciones de la medición.

Documentación general: [`docs/PILLARS.md`](docs/PILLARS.md) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## 13. Agentes y harnesses

**Motivación.** LEONES necesita una capa de ejecución agéntica capaz de probar tareas reales de manera reproducible y comparable.

**Objetivo.** Utilizar harnesses especializados como referencia de ejecución/evaluación y mantener separada la infraestructura de agente de la base de evidencia de LEONES.

**Metodología.** Cada harness se integra como adaptador: tarea definida → entorno aislado → permisos explícitos → ejecución → trazabilidad → grading → evidencia. Un harness externo es una fuente técnica o un componente de integración, no una autoridad automática sobre el catálogo LEONES.

Documentación: [`docs/subprojects/`](docs/subprojects/).
