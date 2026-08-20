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

## 7. CABE / RULA

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

## 8. Atlas → recomendador

**Motivación.** Un catálogo no responde a la pregunta del usuario: "¿qué modelo debería utilizar yo para esta tarea y este hardware?".

**Objetivo.** Convertir evidencia de modelos + hardware + rendimiento + apertura + precio en recomendaciones trazables.

**Metodología.** Prospección → ingesta → evidencia → calidad → hipótesis → matriz hardware → recomendación → enriquecimiento → validación → publicación. CABE/RULA, JGB y los datos económicos permanecen como dimensiones independientes.

Documentación: [`docs/phases/2026-08-atlas-recommendation-pipeline/`](docs/phases/2026-08-atlas-recommendation-pipeline/) · [`docs/completed/H10-ATLAS-RECOMMENDER-PIPELINE.md`](docs/completed/H10-ATLAS-RECOMMENDER-PIPELINE.md).

## 9. Benchmarks reales

**Motivación.** Los benchmarks publicados por terceros son imprescindibles, pero no sustituyen la medición en el hardware y runtime que realmente utiliza el usuario.

**Objetivo.** Crear una batería reproducible que mida modelos, runtimes y tareas en condiciones controladas.

**Metodología.** Fijar hardware + modelo + cuantización + runtime + contexto → ejecutar tarea controlada → recoger tiempo, tokens y resultado → validar → almacenar evidencia con procedencia. La medición LEONES nunca se confunde con una cifra declarada por el fabricante.

Documentación: [`docs/RESULT_SCHEMA.md`](docs/RESULT_SCHEMA.md) · [`docs/completed/BENCHMARK-MEASURED-EVIDENCE.md`](docs/completed/BENCHMARK-MEASURED-EVIDENCE.md) · [`docs/completed/PHYSICAL-BENCHMARK-VALIDATION.md`](docs/completed/PHYSICAL-BENCHMARK-VALIDATION.md).

## 10. Evaluación agentiva

**Motivación.** Un agente no se puede evaluar solo por tokens/segundo ni por una respuesta final. Importan herramientas, trayectoria, recuperación ante errores, coste, tiempo, seguridad y artefactos producidos.

**Objetivo.** Evaluar agentes mediante tareas reales y reproducibles, no únicamente mediante preguntas sintéticas.

**Metodología.** Tarea → entorno controlado → herramientas → trazas → outcome → trajectory → grading → coste/tiempo → seguridad → artefactos → informe. Las métricas se conservan separadas para evitar que una única puntuación oculte fallos.

Documentación: [`docs/EVALUACION_AGENTIC_TESTS.md`](docs/EVALUACION_AGENTIC_TESTS.md) · [`docs/sources/ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md`](docs/sources/ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md).

## 11. Runtime / Router / Quant

**Motivación.** El modelo no ejecuta solo: el resultado depende del motor, cuantización, placement, contexto, batching, aceleración y estrategia de routing.

**Objetivo.** Separar modelo, runtime y configuración para poder comparar combinaciones reproducibles y seleccionar dinámicamente la mejor opción para una tarea.

**Metodología.** Registrar cada ejecución como una combinación explícita `modelo + cuantización + runtime + hardware + configuración`; medir; comparar; alimentar Router sin ocultar las condiciones de la medición.

Estos subproyectos evolucionan sobre los contratos establecidos por Atlas, la matriz hardware y Benchmark.

Documentación general: [`docs/PILLARS.md`](docs/PILLARS.md) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## 12. Agentes y harnesses

**Motivación.** LEONES necesita una capa de ejecución agéntica capaz de probar tareas reales de manera reproducible y comparable.

**Objetivo.** Utilizar harnesses especializados como referencia de ejecución/evaluación y mantener separada la infraestructura de agente de la base de evidencia de LEONES.

**Metodología.** Cada harness se integra como adaptador: tarea definida → entorno aislado → permisos explícitos → ejecución → trazas → resultado → benchmark. La selección de harness no modifica los hechos del Atlas.

Los harnesses de referencia del proyecto son **Hermes, DeepSeek Harness y Buddy**, junto con la integración de **Magnitude** como asistente de coding y **ODS** como servidor de stacks IA.

## 13. ODS — servidor de stacks IA

**Motivación.** Muchos usuarios necesitan algo más que un modelo: necesitan inferencia, UI, RAG, agentes, voz, imagen, workflows y servicios coordinados.

**Objetivo.** Integrar ODS como perfil instalable de servidor local, sin convertir ODS en una dependencia interna de LEONES.

**Metodología.** Preflight → consentimiento → instalación reproducible → captura de configuración → health check → benchmark LEONES → separación `reported/estimated/measured` → publicación solo con consentimiento.

Documentación: [`docs/integrations/ODS/README.md`](docs/integrations/ODS/README.md) · [`docs/integrations/DATA-CONTRACT.md`](docs/integrations/DATA-CONTRACT.md).

## 14. Magnitude — asistente personal IA

**Motivación.** El coding agent necesita seleccionar modelo/runtime en función del hardware y ejecutar tareas reales sobre un proyecto, no únicamente producir texto.

**Objetivo.** Integrar Magnitude como perfil de asistente personal local, conservando su recomendación separada de la medición independiente de LEONES.

**Metodología.** Preflight Node/npm/hardware → consentimiento → instalación → identificación de modelo/runtime → tarea controlada → benchmark → captura de resultado → limpieza del entorno de prueba.

Las skills se consideran superficie de permisos y se registran con origen, versión, permisos y alcance.

Documentación: [`docs/integrations/Magnitude/README.md`](docs/integrations/Magnitude/README.md).

## 15. Web / App

**Motivación.** El conocimiento solo es útil si una persona puede consultarlo y utilizarlo para tomar una decisión.

**Objetivo.** Convertir los datos y recomendaciones en una interfaz accesible, comprensible y navegable.

**Metodología.** Datos canónicos → vistas explicativas → recomendación trazable → enlaces a evidencia → formularios/feedback → validación → mejora continua. La interfaz nunca debe ocultar el nivel de certeza de un dato.

Documentación: [`web/README.md`](web/README.md) · [`docs/UX_OPTIMIZATION.md`](docs/UX_OPTIMIZATION.md).

## 16. Recomendaciones de usuarios

**Motivación.** La comunidad puede descubrir hardware, software, modelos y fuentes que un crawler no encuentra.

**Objetivo.** Crear un canal de entrada humano que transforme recomendaciones en candidatos evaluables sin convertirlas automáticamente en verdad.

**Metodología.** Usuario → propuesta → validación `OK LEONES` → revisión → enriquecimiento → evidencia → integración si supera el quality gate.

## 17. MANADA / conocimiento colectivo

**Motivación.** La experiencia distribuida de usuarios sobre hardware y tareas reales complementa los datos automáticos.

**Objetivo.** Agregar observaciones voluntarias y anónimas/seudonimizadas de forma que puedan mejorar las recomendaciones sin comprometer privacidad.

**Metodología.** Aportación voluntaria → minimización de datos → revisión → agregación → estadísticas → evidencia colectiva. Nunca se incorpora automáticamente una observación individual como hecho universal.

## 18. ADIVINO / descubrimiento futuro

**Motivación.** El ecosistema cambia y LEONES debe poder descubrir nuevas fuentes, benchmarks, repositorios, runtimes, datasets y skills.

**Objetivo.** Automatizar el descubrimiento de nuevas fuentes sin automatizar ciegamente su incorporación al conocimiento canónico.

**Metodología.** Descubrir → clasificar → registrar procedencia → proponer → revisión humana → quality gate → integrar.

ADIVINO permanece separado del catálogo canónico hasta superar los controles definidos.

Documentación: [`docs/SOURCE-DISCOVERY.md`](docs/SOURCE-DISCOVERY.md).

## 19. Fuentes empíricas externas

**Motivación.** LEONES necesita contrastar sus mediciones y recomendaciones con el ecosistema externo.

**Objetivo.** Mantener un mapa de fuentes de evidencia independientes —benchmarks, arenas, fabricantes, Hugging Face, Artificial Analysis, Mozilla y otras— sin mezclarlas con las mediciones propias.

**Metodología.** Registrar fuente → identificar qué mide realmente → capturar fecha/procedencia → normalizar → etiquetar como evidencia externa → contrastar con LEONES → conservar diferencias.

Documentación: [`docs/sources/`](docs/sources/) y [`docs/sources/MOZILLA_OPEN_SOURCE_AI_ECOSYSTEM.md`](docs/sources/MOZILLA_OPEN_SOURCE_AI_ECOSYSTEM.md).

---

# 📊 Estado global del proyecto

**Corte: 20 de agosto de 2026.** Este README es la fotografía operativa del proyecto. El detalle técnico y la evidencia de cada fase viven en `docs/`.

| Estado | Significado |
|---|---|
| 🟢 **ACEPTADO / OPERATIVO** | Implementado, documentado y validado. |
| 🟡 **EN DESARROLLO** | Existe base funcional, pero falta cobertura, validación o integración. |
| 🔵 **SIGUIENTE** | Próxima prioridad. |
| ⚪ **PLANIFICADO** | Aún no es una capacidad funcional completa. |

## 🟢 Hitos aceptados

### H01 — Bot mensual de precios de hardware

**🟢 ACEPTADO.** Fuentes activas, extracción, normalización, control de calidad e histórico de observaciones.

Documentación: [`docs/phases/2026-08-hardware-pricing/`](docs/phases/2026-08-hardware-pricing/).

### H02 — Precios → hardware → Atlas/recomendador

**🟢 ACEPTADO.** Integración de observaciones válidas de precios con hardware y recomendación, con tests.

Documentación: [`docs/atlas-hardware-price-integration.md`](docs/atlas-hardware-price-integration.md).

### H03 — Ranking económico V1

**🟢 ACEPTADO.** Automatizado en GitHub Actions, con tests y separación explícita entre JGB, rendimiento, hardware y precio.

Documentación: [`docs/phases/2026-08-economic-ranking-v1/`](docs/phases/2026-08-economic-ranking-v1/).

### H04 — Prospección diaria

**🟢 ACEPTADO.** Descubrimiento diario, filtro OSI, prioridad Copyleft, enriquecimiento e integración con Atlas/web.

Documentación: [`docs/phases/2026-08-daily-prospection/`](docs/phases/2026-08-daily-prospection/).

### H05 — Sistema formal de documentación

**🟢 ACEPTADO.** Fases, arquitectura, decisiones, validación, trazabilidad e índices documentales.

Documentación: [`docs/DOCUMENTATION_PROTOCOL.md`](docs/DOCUMENTATION_PROTOCOL.md) · [`docs/phases/README.md`](docs/phases/README.md).

### H06 — Open LLM Atlas ampliado

**🟢 ACEPTADO / OPERATIVO.**

H06 establece la frontera canónica entre el feed de prospección y el Atlas:

```text
FEED OPERATIVO → IDENTIDAD → EVIDENCIA → QUALITY GATE → VERIFIED-ONLY → ATLAS CANÓNICO
```

Validación final: 193 filas auditadas, 193 identidades únicas, 0 duplicados detectados, 193 flags `unverified`, 0 filas `verified`, 0 registros promovidos y 0 registros en el catálogo canónico. Esto es correcto: no se introducen modelos sin evidencia suficiente.

Documentación: [`docs/phases/2026-08-atlas-expanded/`](docs/phases/2026-08-atlas-expanded/) · [`atlas/README.md`](atlas/README.md) · [`data/prospection/h06_audit_report.json`](data/prospection/h06_audit_report.json).

### H10 — Pipeline Atlas → recomendador diario enriquecido

**🟢 ACEPTADO.** El pipeline completo está operativo: prospección → ingesta → evidencia → calidad → hipótesis → matriz → recomendador → enriquecimiento → validación → publicación.

La integración de CABE/RULA mantiene `tokens_per_second` como dato continuo y añade `performance_class` sin introducir esa clasificación en `fit_score`.

Documentación: [`docs/phases/2026-08-atlas-recommendation-pipeline/`](docs/phases/2026-08-atlas-recommendation-pipeline/).

### Integraciones ODS + Magnitude

**🟢 INTEGRADAS.** ODS y Magnitude están documentados como perfiles externos instalables y medibles, con preflight, consentimiento, contrato de evidencia, validación E2E y tests. No se convierten en dependencias estructurales de LEONES.

Documentación: [`docs/integrations/`](docs/integrations/) · [`docs/integrations/E2E.md`](docs/integrations/E2E.md).

---

# 🧹 Estándar de «limpia, fija y da esplendor»

Cuando una fase pasa a terminada, se aplica este cierre antes de considerarla terminada:

1. eliminar trazas, pruebas y borradores que no formen parte del producto;
2. retirar código muerto y artefactos temporales;
3. revisar nombres y contratos públicos;
4. documentar los scripts con comentarios pedagógicos, pensados para lectores con conocimientos básicos de programación;
5. mantener documentación externa pormenorizada;
6. enlazar esa documentación desde los README correspondientes;
7. conservar evidencia de validación y criterios de cierre;
8. comprobar que CI es reproducible;
9. comprobar que ningún workflow escritor puede concurrir con otro;
10. actualizar el estado del proyecto.

Este estándar se aplica también retrospectivamente a las fases ya aceptadas.

---

# 🟡 Partes en desarrollo

### H07 — Índice JGB sistemático

**🟡 EN DESARROLLO.** El criterio JGB ya está documentado y se mantiene independiente de rendimiento, calidad, precio y self-hostability. Falta aplicarlo sistemáticamente y verificar su evidencia.

Documentación: [`web/proyectos/atlas/openness/JGB-INDEX.md`](web/proyectos/atlas/openness/JGB-INDEX.md).

### H08 — Matriz completa de hardware

**🟡 EN DESARROLLO.** Existe una matriz grande y generación automática de perfiles, incluyendo CPU, RAM y GPU. Falta convertir toda esa cobertura en capacidad independiente auditada y aceptada.

### H09 — CABE / RULA

**🟡 EN DESARROLLO.** Contratos, normalización, clasificación, pruebas e integración con el recomendador están implementados. Falta ampliar la cobertura con mediciones reales y cerrar la validación sistemática.

Regla oficial: `<1 = No CABE`, `1–<10 = CABE`, `10–100 = RULA`, `>100 = RULA+` tok/s. El valor `tokens_per_second` siempre se conserva y la clasificación no sustituye al dato.

### Benchmarks reales y evaluación agentiva

**🟡 EN DESARROLLO.** Contrato de resultados, B01–B05, inferencia y evaluación ya existen; la metodología agentiva se ha ampliado hacia tareas reales, herramientas, trazas, outcome/trajectory, grading multidimensional y métricas de coste/tiempo/seguridad. Falta ejecutar la campaña amplia sobre hardware y entornos reales.

Documentación: [`docs/RESULT_SCHEMA.md`](docs/RESULT_SCHEMA.md) · [`docs/EVALUACION_AGENTIC_TESTS.md`](docs/EVALUACION_AGENTIC_TESTS.md) · [`docs/sources/ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md`](docs/sources/ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md).

### Adaptadores y fuentes empíricas

**🟡 EN DESARROLLO.** La arquitectura permite trazabilidad de observaciones externas; la cobertura y robustez de adaptadores continúan evolucionando.

### 🔮 ADIVINO — descubrimiento futuro

**🟡 APARCADO.** Arquitectura documentada para descubrir nuevas webs, repositorios, datasets, benchmarks, runtimes, software y skills. Su activación de correo y validación humana `OK LEONES` quedan pendientes por decisión explícita del proyecto.

Documentación: [`docs/SOURCE-DISCOVERY.md`](docs/SOURCE-DISCOVERY.md).

### Web / aplicación

**🟡 EN DESARROLLO.** La web funcional y la aplicación están publicadas. Quedan coherencia completa de navegación, validación de todos los flujos y evolución de UX.

Documentación: [`web/README.md`](web/README.md) · [`docs/UX_OPTIMIZATION.md`](docs/UX_OPTIMIZATION.md).

### Recomendaciones de usuarios

**🟡 IMPLEMENTADO / PENDIENTE DE PRIMER CICLO REAL.** Existe formulario, plantilla, workflow y validación mediante OK LEONES; falta demostrar el ciclo completo con una entrada real.

### MANADA

**🟡 BASE OPERATIVA / EN EVOLUCIÓN.** Existe generación de informes, privacidad, agregación y estadísticas. La aportación es voluntaria y pasa revisión humana. El estado se seguirá validando mediante CI.

### Fuente estratégica — Mozilla State of Open Source AI

**🟢 INTEGRADA COMO FUENTE DE CONOCIMIENTO.** El ecosistema identificado por Mozilla se conserva en un documento independiente, con procedencia, análisis LEONES, entidades de seguimiento y reglas de separación entre evidencia externa y medición propia.

Documentación: [`docs/sources/MOZILLA_OPEN_SOURCE_AI_ECOSYSTEM.md`](docs/sources/MOZILLA_OPEN_SOURCE_AI_ECOSYSTEM.md).

---

# 🧭 Los 9 pilares oficiales

| Pilar | Estado | Situación |
|---|---|---|
| **1. Prospector** | 🟢 | Prospección diaria operativa. |
| **2. Atlas** | 🟢 H06 | Frontera canónica de identidad/evidencia operativa; cobertura depende de evidencia. |
| **3. Task Intelligence** | 🟡 | Arquitectura definida; implementación integral pendiente. |
| **4. Router** | 🟡 | Primera implementación; falta selección dinámica E2E validada. |
| **5. Quant** | 🟡 | Base documental; falta integración completa. |
| **6. Fine-Tuning** | 🟡 | Base documental; falta sistema completo validado. |
| **7. Agents** | 🟡 | Arquitectura y evaluación presentes; falta cerrar ciclo reproducible amplio. |
| **8. Runtime** | 🟡 | Base funcional; backends y mediciones en expansión. |
| **9. Benchmark & Evaluation** | 🟡 | Contratos y batería existentes; la metodología agentiva se ha ampliado con tareas reales, trazas, graders y métricas multidimensionales; falta evidencia de ejecución continua. |

Documentación: [`docs/PILLARS.md`](docs/PILLARS.md) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

# ⚙️ Automatización y CI

El repositorio dispone de workflows para prospección, Atlas, evidencia, recomendaciones, precios, ranking económico, web, recomendaciones de usuarios y MANADA.

**Regla obligatoria de no concurrencia:** todo workflow futuro que escriba en `main` debe usar el grupo global `leones-main-writers` con `cancel-in-progress: false`. Ningún nuevo workflow escritor puede saltarse esta regla.

Regla de cierre:

```text
IMPLEMENTAR → VALIDAR → ACEPTAR → DOCUMENTAR → ENLAZAR → CERRAR
```

Una pieza no se declara terminada solo porque exista código.

---

# 🔬 Principios de evidencia

LEONES separa deliberadamente:

```text
DESCUBRIMIENTO → EVIDENCIA EXTERNA → NORMALIZACIÓN → VERIFICACIÓN / MEDICIÓN → ATLAS → RECOMENDACIÓN
```

No se inventan valores. La ausencia permanece `unknown`. Las estimaciones se marcan como `estimated`. Una fuente externa no se presenta automáticamente como medición LEONES.

Además:

- la clasificación de apertura no se sustituye por un score;
- JGB, CABE y RULA permanecen separados;
- el tamaño de pesos no equivale a memoria total de ejecución;
- el contexto declarado no equivale a rendimiento medido;
- entrenamiento, validación y test deben mantenerse separados;
- en evaluación agentiva se separan **outcome**, **trajectory**, **coste/tiempo**, **seguridad** y **artefactos**.

---

# 🗺️ Flujo general

```text
PROSPECCIÓN → IDENTIDAD → EVIDENCIA → ATLAS
                              ↓
                 JGB / HARDWARE / RENDIMIENTO / PRECIO
                              ↓
                         CABE / RULA
                              ↓
                        RECOMENDADOR
                              ↓
                         RUNTIME / AGENT
                              ↓
                 TAREA → HERRAMIENTAS → TRAZA
                              ↓
                  OUTCOME / COSTE / SEGURIDAD
                              ↓
                           MEDICIÓN
                              ↓
                         PUBLICACIÓN
```
