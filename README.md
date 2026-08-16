# LEONES — Local Ecosystem of Open Neural Expert Systems

> **IA agéntica Libre/Open para hardware de consumo.**  
> **Linux primero · evidencia real · conocimiento colectivo.**

[🌐 Web de LEONES y dashboard de la Manada](https://robertosantosx2.github.io/LEONES/) · [⚙️ Aplicación](https://robertosantosx2.github.io/LEONES/app.html) · [🦁 GitHub](https://github.com/robertosantosx2/LEONES)

---

# 📊 Estado global del proyecto

**Corte de estado: 16 de agosto de 2026.** Este apartado es la referencia rápida para saber qué existe realmente, qué ha sido validado y qué sigue pendiente. El detalle técnico permanece en la documentación especializada.

### Convención

| Estado | Significado |
|---|---|
| 🟢 **ACEPTADO / OPERATIVO** | Implementado, documentado y validado con la evidencia disponible. |
| 🟡 **EN DESARROLLO** | Existe implementación o una base funcional, pero falta cobertura, validación, robustez o integración completa. |
| 🔵 **SIGUIENTE** | Siguiente unidad prioritaria de trabajo. |
| ⚪ **PLANIFICADO** | Identificado en roadmap, sin implementación funcional suficiente. |

## 🟢 Hitos aceptados

### H01 — Bot mensual de precios de hardware

**Estado: 🟢 ACEPTADO.**

- Coolmod, PcComponentes, MediaMarkt España y LDLC España como fuentes activas.
- Amazon fuera de la cobertura activa.
- Extracción, normalización y control de calidad.
- Conservación de observaciones rechazadas para auditoría.

Documentación: [`docs/phases/2026-08-hardware-pricing/`](docs/phases/2026-08-hardware-pricing/) · [`docs/hardware-price-sources.md`](docs/hardware-price-sources.md) · [`docs/hardware-price-quality.md`](docs/hardware-price-quality.md).

### H02 — Precios → hardware → Atlas/recomendador

**Estado: 🟢 ACEPTADO.**

La integración de observaciones válidas de precios con perfiles de hardware y recomendación dispone de tests automatizados y paquete de fase.

Documentación: [`docs/atlas-hardware-price-integration.md`](docs/atlas-hardware-price-integration.md).

### H03 — Ranking económico V1

**Estado: 🟢 ACEPTADO.**

- Integrado en GitHub Actions.
- Tests automatizados.
- Generación de recomendaciones técnicas y ranking económico.
- Publicación automática.
- Separación explícita entre JGB, rendimiento, hardware y precio.

Documentación: [`docs/phases/2026-08-economic-ranking-v1/`](docs/phases/2026-08-economic-ranking-v1/) · [`docs/atlas-economic-ranking.md`](docs/atlas-economic-ranking.md).

### H04 — Prospección diaria

**Estado: 🟢 ACEPTADO.**

Descubrimiento diario, filtro OSI, prioridad Copyleft, enriquecimiento, informes e integración con Atlas/web.

Documentación: [`docs/phases/2026-08-daily-prospection/`](docs/phases/2026-08-daily-prospection/) · [`docs/PROSPECTION.md`](docs/PROSPECTION.md).

### H05 — Sistema formal de documentación

**Estado: 🟢 ACEPTADO.**

El proyecto dispone de protocolo de fases, arquitectura, decisiones, validación, trazabilidad e índice documental.

Documentación: [`docs/DOCUMENTATION_PROTOCOL.md`](docs/DOCUMENTATION_PROTOCOL.md) · [`docs/phases/README.md`](docs/phases/README.md).

### H10 — Pipeline Atlas → recomendador diario enriquecido

**Estado: 🟢 ACEPTADO.**

El cierre de H10 está respaldado por el Run #18 de GitHub Actions: prospección → ingesta → evidencia técnica → calidad → hipótesis → matriz → recomendador → enriquecimiento → validación → publicación.

Evidencia de cierre:

- 209 modelos procesados.
- 39/209 con evidencia técnica reportada en esa ejecución.
- T0=187, T1=5, T2=17, T3=0.
- 32.128 filas de matriz hardware.
- 59 ficheros de recomendaciones.
- 859 filas validadas.
- Contrato de salida con `cabe`, `rula`, `jgb_status`, `evidence_state`, `evidence_type` y `uncertainty`.
- Publicación resistente a concurrencia.
- Actions actualizadas a `checkout@v7` y `setup-python@v7`.

Documentación: [`docs/phases/2026-08-atlas-recommendation-pipeline/`](docs/phases/2026-08-atlas-recommendation-pipeline/) · [`VALIDATION.md`](docs/phases/2026-08-atlas-recommendation-pipeline/VALIDATION.md).

> **Importante:** H10 demuestra que el pipeline funciona; no significa que todos los modelos estén benchmarkeados físicamente, que CABE/RULA sean mediciones físicas completas, que JGB esté completo ni que el ranking multiobjetivo final exista.

---

# 🟡 Partes en desarrollo

### H06 — Open LLM Atlas ampliado

**Estado: 🔵 SIGUIENTE.**

Atlas v0.2 ya tiene esquema ampliado y pipeline operativo, pero la **capa de conocimiento del Atlas sigue en expansión**. El siguiente trabajo es mejorar cobertura y calidad de modelos, familias, organizaciones, variantes, benchmarks, runtimes y procedencia, y reforzar los contratos de evidencia.

Documentación: [`atlas/README.md`](atlas/README.md) · [`atlas/schema.json`](atlas/schema.json) · [`atlas/INGEST.md`](atlas/INGEST.md).

### H07 — Índice JGB sistemático

**Estado: 🟡 EN DESARROLLO.**

El criterio JGB ya está documentado con seis clases (0–5) y cinco dimensiones de libertad/control: Access, Model control, Data control, Autonomy y Trust. Se mantiene **independiente de rendimiento, calidad, precio y self-hostability**.

Pendiente: aplicación sistemática y verificación de evidencia sobre el conjunto de modelos.

Documentación: [`web/proyectos/atlas/openness/JGB-INDEX.md`](web/proyectos/atlas/openness/JGB-INDEX.md) · [`JGB-MATRIX.md`](web/proyectos/atlas/openness/JGB-MATRIX.md) · [`JGB-METHOD.md`](web/proyectos/atlas/openness/JGB-METHOD.md).

### H08 — Matriz completa de hardware

**Estado: 🟡 EN DESARROLLO.**

Ya existe una matriz grande y generación automática de perfiles, incluyendo Intel i3/i5/i7/i9, AMD Ryzen 3/5/7/9, 2/4/8/16/32/64/128 GB y perfiles específicos como RTX 4060 8 GB. El pipeline H10 generó 32.128 filas.

Pendiente: convertir esa cobertura generada en una matriz completa, auditada y aceptada como capacidad independiente.

### H09 — CABE / RULA

**Estado: 🟡 EN DESARROLLO.**

Los conceptos y contratos ya existen en Atlas y en el recomendador:

- **CABE:** si una configuración puede caber/ejecutarse con los recursos disponibles.
- **RULA:** si puede funcionar de forma útil bajo la carga relevante.

La lógica evita confundir `fit_score` con CABE y mantiene `unknown` cuando falta evidencia.

Pendiente: cobertura y validación sistemática, especialmente con mediciones reales.

### Benchmarks reales y evaluación agentiva

**Estado: 🟡 EN DESARROLLO.**

Existe contrato de resultados, batería B01–B05, scripts de inferencia/evaluación y estructura para resultados reproducibles. Falta ampliar la ejecución sobre hardware real y convertirla en evidencia suficiente para el Atlas y el recomendador.

Documentación: [`docs/RESULT_SCHEMA.md`](docs/RESULT_SCHEMA.md) · [`docs/EVALUACION_AGENTIC_TESTS.md`](docs/EVALUACION_AGENTIC_TESTS.md) · [`scripts/local/llm-smoke-test/`](scripts/local/llm-smoke-test/).

### Evidencia técnica

**Estado: 🟢 INFRAESTRUCTURA ACEPTADA DENTRO DE H10; 🟡 COBERTURA EN EVOLUCIÓN.**

El pipeline ya clasifica evidencia y conserva estados T0–T3, procedencia, incertidumbre y diferencias entre datos externos y mediciones LEONES. La cobertura no es todavía uniforme para todos los modelos.

### Adaptadores y fuentes empíricas

**Estado: 🟡 EN DESARROLLO.**

El repositorio contiene adaptadores para MSA, LM Arena, Artificial Analysis, Hugging Face y otras fuentes/benchmarks. La arquitectura ya permite que las observaciones sean trazables; la cobertura y robustez de cada adaptador siguen siendo objeto de mejora.

El principio es: **un dato externo es evidencia de descubrimiento/observación, no una medición LEONES por defecto**.

### Ranking económico completo

**Estado: 🟢 V1 ACEPTADA / 🟡 EVOLUCIÓN.**

La V1 está automatizada y validada. Quedan la ampliación a toda la matriz, PC completo, TCO, coste por tarea y optimización multiobjetivo.

### Web y aplicación

**Estado: 🟡 EN DESARROLLO.**

La web funcional está publicada y contiene páginas de inicio, arquitectura, pilares, Atlas, modelos, hardware, inferencia, prospección, evaluación, Manada, proyectos y recomendaciones. La aplicación y el sistema visual están implementados.

En las últimas iteraciones se han añadido la página de recomendaciones de visita, formulario de recomendaciones de usuarios y mejoras de formato/UX.

Pendiente: cerrar la coherencia de navegación, validar todos los flujos de usuario y mantener la web como interfaz sencilla sobre la infraestructura real.

Documentación: [`web/README.md`](web/README.md) · [`docs/UX_OPTIMIZATION.md`](docs/UX_OPTIMIZATION.md) · [`docs/WEB_DESIGN_SYSTEM.md`](docs/WEB_DESIGN_SYSTEM.md).

### Recomendaciones de usuarios

**Estado: 🟡 IMPLEMENTADO, PENDIENTE DE PRIMER CICLO REAL.**

Existe formulario público, plantilla de issue, flujo de validación y mecanismo de confirmación por **OK LEONES**. El workflow de validación está instalado, pero al corte actual todavía registra **0 ejecuciones**, porque aún no hay un ciclo real de entrada → validación → integración que demostrar.

Documentación: [`docs/USER-RECOMMENDATIONS.md`](docs/USER-RECOMMENDATIONS.md) · [`web/recomendar.html`](web/recomendar.html).

### MANADA

**Estado: 🟡 BASE OPERATIVA / EN EVOLUCIÓN.**

Existe generación de informes, contrato de resultados, controles de privacidad, agregación y estadísticas. La aportación es voluntaria y debe pasar revisión humana antes de compartir.

El último run observado de `Manada statistics` (#154, 16-08-2026) terminó en **failure**; por tanto, esta parte no se declara completamente cerrada hasta revisar y volver a validar ese workflow.

Documentación: [`docs/MANADA_AUTO_REPORT.md`](docs/MANADA_AUTO_REPORT.md) · [`docs/MANADA_STATS.md`](docs/MANADA_STATS.md).

---

# 🧭 Estado de los 9 pilares oficiales

La arquitectura canónica de LEONES tiene nueve pilares. No todos están en el mismo nivel de madurez.

| Pilar | Estado actual | Qué está realmente disponible |
|---|---|---|
| **1. Prospector** | 🟢 **Activo/aceptado** | Prospección diaria, fuentes, filtros, enriquecimiento y publicación. |
| **2. Atlas** | 🟡 **En expansión** | Esquema, ingesta, evidencia y pipeline operativo; cobertura del conocimiento aún incompleta. |
| **3. Task Intelligence** | 🟡 **Arquitectura definida** | Contratos y arquitectura conceptual; implementación integral pendiente. |
| **4. Router** | 🟡 **Primera implementación** | Scripts/capa de recomendación existentes; falta convertirlo en router dinámico validado de extremo a extremo. |
| **5. Quant** | 🟡 **Base / desarrollo** | Espacio y documentación para cuantización; falta integración completa con selección dinámica y evidencia. |
| **6. Fine-Tuning** | 🟡 **Base / desarrollo** | Directorio y documentación inicial; no es todavía un sistema completo de adaptación validado. |
| **7. Agents** | 🟡 **Base / desarrollo** | Arquitectura y evaluación agentiva presentes; falta cerrar el ciclo de agentes reproducibles y validación amplia. |
| **8. Runtime** | 🟡 **Base funcional** | Scripts de detección/ejecución y smoke tests; cobertura de backends y mediciones reales en expansión. |
| **9. Benchmark & Evaluation** | 🟡 **Base funcional** | Contratos, B01–B05, inferencia y validación; falta ampliar evidencia real y continua. |

Documentación de arquitectura: [`docs/PILLARS.md`](docs/PILLARS.md) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

# ⚙️ Automatización y CI

El repositorio dispone de workflows para:

- pipeline diario Atlas;
- prospección diaria;
- ingesta NDJSON;
- evidencia empírica;
- recomendaciones;
- precios mensuales;
- ranking económico;
- publicación web;
- integración de logos;
- validación de recomendaciones de usuarios;
- estadísticas de Manada;
- extracción periódica de fuentes;
- validaciones de formato y contratos.

**Estado:** 🟢 infraestructura ampliamente operativa / 🟡 algunos workflows requieren validación continua.

La última ejecución diaria completa del pipeline Atlas observada antes de este corte terminó correctamente y publicó sus resultados. El workflow de Manada tiene un fallo observado que queda explícitamente registrado arriba.

---

# 📦 Datos y contratos

### Discovery

**🟢 Activo.** Existen catálogos de modelos, runtimes, skills, harnesses y agentes, además de datos de prospección enriquecidos.

### Atlas feed

**🟢 Activo dentro del pipeline H10.** Se generan feed, auditorías de identidad/calidad/evidencia, hipótesis y colas de revisión.

### Hardware

**🟡 En expansión.** Hay perfiles, precios, observaciones de mercado, calidad y matriz de compatibilidad. La cobertura completa y su aceptación como producto independiente siguen pendientes.

### Resultados experimentales

**🟡 Base funcional.** El formato canónico es JSON primero y permite estados `reported → reproducible → verified` o `rejected`. La validez sintáctica no equivale a verificación.

Documentación: [`docs/RESULT_SCHEMA.md`](docs/RESULT_SCHEMA.md) · [`schemas/`](schemas/).

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

No se inventan valores para rellenar huecos. Cuando no hay evidencia suficiente se conserva `unknown`. Las estimaciones documentadas se marcan como `estimated` y las observaciones externas no se presentan automáticamente como mediciones propias.

El criterio de evaluación debe evitar contaminar conjuntos de prueba: entrenamiento, validación y test deben mantenerse separados, y las evaluaciones finales no deben convertirse en objetivos de optimización continua.

---

# 🧠 Fuentes de conocimiento en seguimiento

El proyecto mantiene investigación sobre LLM locales, hardware, memoria, ancho de banda, motores de inferencia, evaluación y construcción de sistemas. Entre las fuentes de seguimiento incorporadas se encuentran:

- Serie **LLM de Cero a Héroe — Edición 2026**, compilada en el material de investigación del proyecto.
- **Kilo — The Best Local Coding Models for Any Setup**, como fuente recurrente de seguimiento de modelos locales de coding, hardware, contexto y uso agentic.
- Fuentes empíricas y benchmarks definidos en [`atlas/empirical-evidence-sites.md`](atlas/empirical-evidence-sites.md).

Estas fuentes alimentan investigación y descubrimiento; su información debe pasar por las reglas de evidencia del proyecto antes de convertirse en dato aceptado del Atlas.

---

# 🗺️ Flujo completo del proyecto

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

El principio central sigue siendo:

> **modelo × variante × runtime × hardware × workload × restricciones**

Y la regla de recomendación es: **primero viabilidad técnica; después evidencia de carga; después rendimiento/calidad; después coste y preferencias; siempre con explicación y procedencia.**

---

# 📚 Documentación principal

- [`LEONES_DECISION_LOG.md`](LEONES_DECISION_LOG.md) — decisiones y trazabilidad.
- [`docs/README.md`](docs/README.md) — índice técnico.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — roadmap consolidado.
- [`docs/phases/README.md`](docs/phases/README.md) — hitos Hxx y estados de aceptación.
- [`docs/phases/PHASE_AUDIT_2026-08.md`](docs/phases/PHASE_AUDIT_2026-08.md) — auditoría documental.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitectura general.
- [`docs/PILLARS.md`](docs/PILLARS.md) — nueve pilares oficiales.
- [`PIPELINE_E2E.md`](PIPELINE_E2E.md) — flujo extremo a extremo.
- [`scripts/README.md`](scripts/README.md) — contrato de scripts.
- [`atlas/README.md`](atlas/README.md) — Open LLM Atlas.
- [`docs/RESULT_SCHEMA.md`](docs/RESULT_SCHEMA.md) — formato canónico de resultados.

## Regla de cierre

```text
IMPLEMENTAR → VALIDAR → ACEPTAR → DOCUMENTAR → ENLAZAR → CERRAR
```

Una pieza no se declara terminada solamente porque exista código. Debe existir una evidencia proporcional a lo que se afirma.

---

# 🚧 Próximo orden de trabajo

```text
H10 CERRADA 🟢
      ↓
H06 ATLAS AMPLIADO 🔵
      ↓
H07 JGB SISTEMÁTICO 🟡
      ↓
H08 MATRIZ HARDWARE 🟡
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

### Fases posteriores todavía no disponibles como capacidad completa

- Coste de PC completo: placa base, almacenamiento, PSU, caja y refrigeración.
- TCO y consumo eléctrico.
- Coste por tarea útil y por ejecución agentiva.
- Ranking económico multiobjetivo configurable por usuario.
- Optimización conjunta de libertad, rendimiento, coste, privacidad y eficiencia.
- Evaluación continua y detección de regresiones.
- Snapshots versionados del Atlas y changelog automático del conocimiento.
- Aprendizaje continuo de la Manada incorporado al motor.
- Selección dinámica de modelo/runtime/hardware.
- Auditoría integral de privacidad y seguridad.

---

# ¿Qué es LEONES?

LEONES investiga, mide y construye un ecosistema de IA agéntica Libre/Open que pueda ejecutarse en **hardware real de consumo**, con especial prioridad al software **Copyleft**.

No pretende ser simplemente otro catálogo de modelos. La pregunta central es:

> **¿Qué combinación de hardware, modelo, runtime, herramientas y arquitectura permite convertir un PC de consumo en una máquina agentic realmente útil?**

Y una segunda pregunta es igual de importante:

> **¿Cómo transformamos las mediciones de muchos equipos reales en mejores recomendaciones para todos?**

Por eso LEONES combina **prospección, conocimiento estructurado, experimentación local, benchmarks agentivos, evidencia reproducible y conocimiento colectivo**.

## Licencia

El repositorio se distribuye bajo **GNU Affero General Public License v3.0 (AGPL-3.0)**. Consulta [`LICENSE`](LICENSE).
