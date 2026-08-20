# LEONES — Local Ecosystem of Open Neural Expert Systems

> **IA agéntica Libre/Open para hardware de consumo.**  
> **Linux primero · evidencia real · conocimiento colectivo.**

[🌐 Web de LEONES](https://robertosantosx2.github.io/LEONES/) · [⚙️ Aplicación](https://robertosantosx2.github.io/LEONES/app.html) · [🦁 GitHub](https://github.com/robertosantosx2/LEONES)

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

**Metodología.** Cada harness se integra como adaptador: tarea definida → entorno aislado → permisos explícitos → ejecución → trazas → resultado → benchmark. La selección de harness no modifica los hechos del Atlas.

Los harnesses de referencia del proyecto son **Hermes, DeepSeek Harness y Buddy**, junto con la integración de **Magnitude** como asistente de coding y **ODS** como servidor de stacks IA.

## 14. ODS — servidor de stacks IA

**Motivación.** Muchos usuarios necesitan algo más que un modelo: necesitan inferencia, UI, RAG, agentes, voz, imagen, workflows y servicios coordinados.

**Objetivo.** Integrar ODS como perfil instalable de servidor local, sin convertir ODS en una dependencia interna de LEONES.

**Metodología.** Preflight → consentimiento → instalación reproducible → captura de configuración → health check → benchmark LEONES → separación `reported/estimated/measured` → publicación solo con consentimiento.

Documentación: [`docs/integrations/ODS/README.md`](docs/integrations/ODS/README.md) · [`docs/integrations/DATA-CONTRACT.md`](docs/integrations/DATA-CONTRACT.md).

## 15. Magnitude — asistente personal IA

**Motivación.** El coding agent necesita seleccionar modelo/runtime en función del hardware y ejecutar tareas reales sobre un proyecto, no únicamente producir texto.

**Objetivo.** Integrar Magnitude como perfil de asistente personal local, conservando su recomendación separada de la medición independiente de LEONES.

**Metodología.** Preflight Node/npm/hardware → consentimiento → instalación → identificación de modelo/runtime → tarea controlada → benchmark → captura de resultado → limpieza del entorno de prueba.

Las skills se consideran superficie de permisos y se registran con origen, versión, permisos y alcance.

Documentación: [`docs/integrations/Magnitude/README.md`](docs/integrations/Magnitude/README.md).

## 16. Web / App

**Motivación.** El conocimiento solo es útil si una persona puede consultarlo y utilizarlo para tomar una decisión.

**Objetivo.** Convertir los datos y recomendaciones en una interfaz accesible, comprensible y navegable.

**Metodología.** Datos canónicos → vistas explicativas → recomendación trazable → enlaces a evidencia → formularios/feedback → validación → mejora continua. La interfaz nunca debe ocultar el nivel de certeza de un dato.

Documentación: [`web/README.md`](web/README.md) · [`docs/UX_OPTIMIZATION.md`](docs/UX_OPTIMIZATION.md).

## 17. Recomendaciones de usuarios

**Motivación.** La comunidad puede descubrir hardware, software, modelos y fuentes que un crawler no encuentra.

**Objetivo.** Crear un canal de entrada humano que transforme recomendaciones en candidatos evaluables sin convertirlas automáticamente en verdad.

**Metodología.** Usuario → propuesta → validación `OK LEONES` → revisión → enriquecimiento → evidencia → integración si supera el quality gate.

## 18. MANADA / conocimiento colectivo

**Motivación.** La experiencia distribuida de usuarios sobre hardware y tareas reales complementa los datos automáticos.

**Objetivo.** Construir una capa colectiva de conocimiento práctico, manteniendo trazabilidad y evitando que una opinión se convierta automáticamente en evidencia técnica.

**Metodología.** Observación de usuario → anonimización/minimización → validación → agregación → contraste con benchmark → publicación con nivel de confianza.

## 19. Fuentes de conocimiento

**Motivación.** La calidad del sistema depende de la calidad y diversidad de sus fuentes.

**Objetivo.** Mantener un inventario de fuentes primarias, empíricas, comunitarias y metodológicas y asignarles un papel explícito.

**Metodología.** Descubrir → clasificar → evaluar autoridad → extraer evidencia → conservar URL/fecha/procedencia → contrastar → incorporar al conocimiento solo cuando corresponda.

Entre las fuentes empíricas se incluyen LMSYS Chatbot Arena, Open LLM Leaderboard, LLM Stats y otras fuentes de medición real; entre las fuentes de infraestructura se incluyen ODS, Magnitude y LLMFit.

---

# 🔬 Principio metodológico común

Todos los subproyectos siguen el mismo ciclo:

```text
HIPÓTESIS
   ↓
FUENTE
   ↓
EXTRACCIÓN
   ↓
NORMALIZACIÓN
   ↓
EVIDENCIA
   ↓
QUALITY GATE
   ↓
MEDICIÓN / VALIDACIÓN
   ↓
PUBLICACIÓN
   ↓
RETROALIMENTACIÓN
```

Una recomendación no puede mejorar la evidencia retrospectivamente: primero se conserva la procedencia y después se calcula la recomendación.

# 🧱 Regla de arquitectura

LEONES separa deliberadamente:

```text
IDENTIDAD       → Atlas
APERTURA        → JGB
HARDWARE        → Hardware Matrix
FIT INICIAL     → LLMFit
PRECIO          → Hardware Pricing
ECONOMÍA        → TCO
RENDIMIENTO     → Benchmarks
AGENTICIDAD     → Agentic Evaluation
EJECUCIÓN       → Runtime / Harnesses
DESPLIEGUE      → ODS / Magnitude
DECISIÓN        → Recommender / Router
EXPERIENCIA     → Web / App / MANADA
```

Esta separación permite sustituir una fuente o herramienta sin destruir el conocimiento acumulado de LEONES.

# 🧪 Regla de evidencia

Nunca se debe escribir:

```text
LLMFit dice que cabe → LEONES ha demostrado que funciona
```

La cadena correcta es:

```text
LLMFit estima que puede caber
            ↓
LEONES contrasta requisitos y configuración
            ↓
LEONES ejecuta benchmark
            ↓
LEONES mide
            ↓
Atlas conserva ambas evidencias
```

# 📚 Documentación

- [`docs/phases/README.md`](docs/phases/README.md) — fases e hitos.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitectura.
- [`docs/DOCUMENTATION_PROTOCOL.md`](docs/DOCUMENTATION_PROTOCOL.md) — protocolo documental.
- [`docs/integrations/README.md`](docs/integrations/README.md) — integraciones.
- [`docs/integrations/DATA-CONTRACT.md`](docs/integrations/DATA-CONTRACT.md) — contrato de datos.
- [`docs/integrations/E2E.md`](docs/integrations/E2E.md) — validación E2E.
- [`docs/completed/`](docs/completed/) — documentación de hitos cerrados.

# 🟢 Estado del proyecto

El estado operativo de cada hito se mantiene en [`docs/phases/README.md`](docs/phases/README.md). El README principal describe el **qué, por qué y cómo**; los documentos de fase contienen el detalle de implementación, decisiones y validación.
