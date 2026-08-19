# LEONES — Local Ecosystem of Open Neural Expert Systems

> **IA agéntica Libre/Open para hardware de consumo.**  
> **Linux primero · evidencia real · conocimiento colectivo.**

[🌐 Web de LEONES](https://robertosantosx2.github.io/LEONES/) · [⚙️ Aplicación](https://robertosantosx2.github.io/LEONES/app.html) · [🦁 GitHub](https://github.com/robertosantosx2/LEONES)

---

# 📊 Estado global del proyecto

**Corte: 19 de agosto de 2026.** Este README es la fotografía operativa del proyecto. El detalle técnico y la evidencia de cada fase viven en `docs/`.

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

**🟡 EN DESARROLLO.** Contrato de resultados, B01–B05, inferencia y evaluación ya existen; la nueva fuente de Artificial Analysis / Optima amplía el diseño hacia tareas reales, herramientas, trazas, outcome/trajectory, grading multidimensional y métricas de coste/tiempo/seguridad. Falta ejecutar la campaña amplia sobre hardware y entornos reales.

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
