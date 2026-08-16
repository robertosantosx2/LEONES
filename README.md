# LEONES — Local Ecosystem of Open Neural Expert Systems

> **IA agéntica Libre/Open para hardware de consumo.**  
> **Linux primero · evidencia real · conocimiento colectivo.**

[🌐 Web de LEONES](https://robertosantosx2.github.io/LEONES/) · [⚙️ Aplicación](https://robertosantosx2.github.io/LEONES/app.html) · [🦁 GitHub](https://github.com/robertosantosx2/LEONES)

---

# 📊 Estado global del proyecto

**Corte: 16 de agosto de 2026.** Este README es la fotografía operativa del proyecto. El detalle técnico y la evidencia de cada fase viven en `docs/`.

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
FEED OPERATIVO
      ↓
IDENTIDAD
      ↓
EVIDENCIA
      ↓
QUALITY GATE
      ↓
VERIFIED-ONLY
      ↓
ATLAS CANÓNICO
```

Validación final:

- 193 filas auditadas.
- 193 identidades.
- 193 identidades únicas según el auditor actual.
- 0 grupos duplicados detectados.
- 193 flags, todos `unverified`.
- 0 filas `verified`.
- 0 registros promovidos.
- 0 registros en `atlas/catalog.json`.

**Esto es correcto:** no se introducen modelos en el Atlas oficial sin evidencia suficiente.

Documentación: [`docs/phases/2026-08-atlas-expanded/`](docs/phases/2026-08-atlas-expanded/) · [`atlas/README.md`](atlas/README.md) · [`data/prospection/h06_audit_report.json`](data/prospection/h06_audit_report.json).

### H10 — Pipeline Atlas → recomendador diario enriquecido

**🟢 ACEPTADO.** El Run #18 cerró el pipeline completo: prospección → ingesta → evidencia → calidad → hipótesis → matriz → recomendador → enriquecimiento → validación → publicación.

Evidencia de cierre: 209 modelos procesados, 39/209 con evidencia técnica reportada en aquella ejecución, 32.128 filas de matriz hardware, 59 ficheros de recomendaciones y 859 filas validadas.

Documentación: [`docs/phases/2026-08-atlas-recommendation-pipeline/`](docs/phases/2026-08-atlas-recommendation-pipeline/).

> H10 demuestra que el pipeline funciona; no significa que todos los modelos estén benchmarkeados físicamente ni que JGB/CABE/RULA estén completos.

---

# 🟡 Partes en desarrollo

### H07 — Índice JGB sistemático

**🟡 EN DESARROLLO.** El criterio JGB ya está documentado y se mantiene independiente de rendimiento, calidad, precio y self-hostability. Falta aplicarlo sistemáticamente y verificar su evidencia.

Documentación: [`web/proyectos/atlas/openness/JGB-INDEX.md`](web/proyectos/atlas/openness/JGB-INDEX.md).

### H08 — Matriz completa de hardware

**🟡 EN DESARROLLO.** Existe una matriz grande y generación automática de perfiles, incluyendo CPU, RAM y GPU. Falta convertir toda esa cobertura en capacidad independiente auditada y aceptada.

### H09 — CABE / RULA

**🟡 EN DESARROLLO.** Contratos y lógica ya existen. Falta cobertura y validación sistemática, especialmente mediante mediciones reales.

### Benchmarks reales y evaluación agentiva

**🟡 EN DESARROLLO.** Contrato de resultados, B01–B05, inferencia y evaluación ya existen; falta ampliar la ejecución sobre hardware real.

Documentación: [`docs/RESULT_SCHEMA.md`](docs/RESULT_SCHEMA.md) · [`docs/EVALUACION_AGENTIC_TESTS.md`](docs/EVALUACION_AGENTIC_TESTS.md).

### Adaptadores y fuentes empíricas

**🟡 EN DESARROLLO.** La arquitectura permite trazabilidad de observaciones externas; la cobertura y robustez de adaptadores continúan evolucionando.

### Web / aplicación

**🟡 EN DESARROLLO.** La web funcional y la aplicación están publicadas. Quedan coherencia completa de navegación, validación de todos los flujos y evolución de UX.

Documentación: [`web/README.md`](web/README.md) · [`docs/UX_OPTIMIZATION.md`](docs/UX_OPTIMIZATION.md).

### Recomendaciones de usuarios

**🟡 IMPLEMENTADO / PENDIENTE DE PRIMER CICLO REAL.** Existe formulario, plantilla, workflow y validación mediante OK LEONES; falta demostrar el ciclo completo con una entrada real.

### MANADA

**🟡 BASE OPERATIVA / EN EVOLUCIÓN.** Existe generación de informes, privacidad, agregación y estadísticas. La aportación es voluntaria y pasa revisión humana. El estado se seguirá validando mediante CI.

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
| **9. Benchmark & Evaluation** | 🟡 | Contratos y batería existentes; falta ampliar evidencia real continua. |

Documentación: [`docs/PILLARS.md`](docs/PILLARS.md) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

# ⚙️ Automatización y CI

El repositorio dispone de workflows para prospección, Atlas, evidencia, recomendaciones, precios, ranking económico, web, recomendaciones de usuarios y MANADA.

Regla de cierre:

```text
IMPLEMENTAR → VALIDAR → ACEPTAR → DOCUMENTAR → ENLAZAR → CERRAR
```

Una pieza no se declara terminada solo porque exista código.

---

# 🔬 Principios de evidencia

LEONES separa deliberadamente:

```text
DESCUBRIMIENTO
     ↓
EVIDENCIA EXTERNA
     ↓
NORMALIZACIÓN
     ↓
VERIFICACIÓN / MEDICIÓN
     ↓
ATLAS
     ↓
RECOMENDACIÓN
```

No se inventan valores. La ausencia permanece `unknown`. Las estimaciones se marcan como `estimated`. Una fuente externa no se presenta automáticamente como medición LEONES.

Además:

- la clasificación de apertura no se sustituye por un score;
- JGB, CABE y RULA permanecen separados;
- el tamaño de pesos no equivale a memoria total de ejecución;
- el contexto declarado no equivale a rendimiento medido;
- entrenamiento, validación y test deben mantenerse separados.

---

# 🗺️ Flujo general

```text
PROSPECCIÓN
    ↓
IDENTIDAD
    ↓
EVIDENCIA
    ↓
ATLAS
    ↓
JGB ───────────────┐
HARDWARE ──────────┤
RENDIMIENTO ───────┤
PRECIO ────────────┤
                    ↓
                  CABE
                    ↓
                 RULA
                    ↓
              RECOMENDADOR
                    ↓
             RUNTIME / AGENT
                    ↓
               MEDICIÓN
                    ↓
                 MANADA
                    ↺
```

Principio central:

> **modelo × variante × runtime × hardware × workload × restricciones**

---

# 🚧 Próximo orden de trabajo

```text
H01–H06 🟢
     ↓
H07 JGB 🟡
     ↓
H08 HARDWARE 🟡
     ↓
H09 CABE / RULA 🟡
     ↓
BENCHMARKS REALES 🟡
     ↓
AGENTIC / B01–B05 🟡
     ↓
ROUTER / SELECCIÓN DINÁMICA 🟡
     ↓
WEB / APP 🟡
     ↓
MANADA 🟡
     ↓
TCO ⚪
     ↓
OPTIMIZACIÓN MULTIOBJETIVO ⚪
```

## Fases posteriores

- Coste completo del PC.
- TCO y consumo eléctrico.
- Coste por tarea útil y ejecución agentiva.
- Ranking económico multiobjetivo configurable.
- Optimización conjunta de libertad, rendimiento, coste, privacidad y eficiencia.
- Evaluación continua y regresiones.
- Snapshots versionados del Atlas.
- Aprendizaje continuo de MANADA.
- Selección dinámica modelo/runtime/hardware.
- Auditoría integral de privacidad y seguridad.

---

# 📚 Documentación principal

- [`docs/README.md`](docs/README.md)
- [`docs/ROADMAP.md`](docs/ROADMAP.md)
- [`docs/phases/README.md`](docs/phases/README.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/PILLARS.md`](docs/PILLARS.md)
- [`PIPELINE_E2E.md`](PIPELINE_E2E.md)
- [`atlas/README.md`](atlas/README.md)
- [`docs/RESULT_SCHEMA.md`](docs/RESULT_SCHEMA.md)

## ¿Qué es LEONES?

LEONES investiga y construye un ecosistema de IA agéntica Libre/Open capaz de ejecutarse sobre **hardware real de consumo**, con especial prioridad al software Copyleft.

La pregunta central es:

> **¿Qué combinación de hardware, modelo, runtime, herramientas y arquitectura convierte un PC de consumo en una máquina agentic realmente útil?**

Y la segunda:

> **¿Cómo convertimos las mediciones de muchos equipos reales en mejores recomendaciones para todos?**

## Licencia

GNU Affero General Public License v3.0 (AGPL-3.0). Consulta [`LICENSE`](LICENSE).
