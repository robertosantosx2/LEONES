# LEONES — Local Ecosystem of Open Neural Expert Systems

> **IA agéntica Libre/Open para hardware de consumo.**
>
> **Linux primero · evidencia real · conocimiento colectivo.**

[🌐 **Web de LEONES y dashboard de la Manada**](https://robertosantosx2.github.io/LEONES/)

[⚙️ **Aplicación LEONES**](https://robertosantosx2.github.io/LEONES/app.html)

[🦁 **Repositorio GitHub**](https://github.com/robertosantosx2/LEONES)

---

# 📊 Estado global del proyecto

> **Actualizado tras la validación del bot de precios, la integración Atlas → recomendador y el ranking económico V1.**

La siguiente clasificación distingue tres estados y evita llamar «terminado» a algo que solo tiene código pero no documentación o validación.

| Estado | Significado |
|---|---|
| 🟢 **TERMINADO** | Implementado, documentado y validado cuando corresponde. No significa que nunca vaya a evolucionar. |
| 🟡 **EN DESARROLLO** | Existe implementación o una base funcional, pero todavía faltan cobertura, robustez, validación, integración o evolución prevista. |
| ⚪ **SIN EMPEZAR** | Está identificado en el roadmap, pero todavía no existe una implementación funcional suficiente. |

## 🟢 TERMINADO / OPERATIVO

- 🟢 **Bot mensual de precios de hardware**.
- 🟢 Fuentes activas: **Coolmod, PcComponentes, MediaMarkt España y LDLC España**.
- 🟢 **Amazon descartada** como fuente activa.
- 🟢 Normalización y control de calidad de observaciones de precios.
- 🟢 Conservación de observaciones rechazadas para auditoría.
- 🟢 Integración **precios → perfiles hardware → Atlas/recomendador**.
- 🟢 Test automatizado de integración de precios.
- 🟢 **Ranking económico V1** integrado en GitHub Actions.
- 🟢 Test automatizado del ranking económico.
- 🟢 Generación automática de recomendaciones técnicas.
- 🟢 Generación automática del ranking económico.
- 🟢 Publicación automática de las salidas del recomendador.
- 🟢 Separación conceptual **JGB / rendimiento / hardware / precio**.
- 🟢 Documentación del diseño de precios, calidad, integración y ranking económico.
- 🟢 README y documentación principal enlazados con las piezas del subproyecto Atlas.

**Documentación:** [precios](docs/hardware-price-sources.md) · [calidad](docs/hardware-price-quality.md) · [integración](docs/atlas-hardware-price-integration.md) · [ranking económico](docs/atlas-economic-ranking.md).

## 🟡 EN DESARROLLO

- 🟡 **Open LLM Atlas**: ampliación y depuración continua de modelos, familias, organizaciones, benchmarks y procedencia.
- 🟡 **Índice JGB**: consolidación de cobertura, evidencia y aplicación sistemática al conjunto de modelos.
- 🟡 **Matriz completa de hardware**: 2/4/8/16/32/64/128 GB.
- 🟡 Emparejamiento sistemático **Intel i3/i5/i7/i9 ↔ AMD Ryzen 3/5/7/9**.
- 🟡 Cobertura completa de GPU NVIDIA y VRAM para las distintas configuraciones.
- 🟡 **CABE/RULA** como capa sistemática de viabilidad hardware-modelo.
- 🟡 Escalado del ranking económico a toda la matriz de hardware.
- 🟡 Prospección diaria y alimentación automática de las distintas secciones del ecosistema.
- 🟡 Mejora continua de adaptadores y cobertura del bot de precios.
- 🟡 Benchmarks reproducibles en hardware real.
- 🟡 Evaluación agentiva y batería **LB B01–B05**.
- 🟡 Integración progresiva de runtimes, eficiencia, offloading y ejecución local.
- 🟡 Web/app como interfaz coherente de todo el ecosistema.
- 🟡 **Manada**: agregación, confianza y aprendizaje colectivo.

**Documentación:** [Atlas](atlas/README.md) · [prospección](docs/PROSPECTION.md) · [resultados](docs/RESULT_SCHEMA.md) · [arquitectura](docs/ARCHITECTURE.md).

## ⚪ SIN EMPEZAR / FASES POSTERIORES

- ⚪ Coste de **PC completo**: placa base + almacenamiento + PSU + caja + refrigeración, además de CPU/RAM/GPU.
- ⚪ **TCO** incluyendo consumo eléctrico y coste de uso sostenido.
- ⚪ Coste por tarea útil / coste por ejecución agentiva.
- ⚪ Ranking económico multiobjetivo configurable por usuario.
- ⚪ Optimización conjunta de **libertad + rendimiento + coste + privacidad + eficiencia**.
- ⚪ Sistema completo de evaluación continua y detección de regresiones.
- ⚪ Snapshots versionados del Atlas y changelog automático del conocimiento.
- ⚪ Aprendizaje continuo de la Manada incorporado al motor de recomendación.
- ⚪ Optimización avanzada de rutas de ejecución y selección dinámica de runtime/modelo/hardware.
- ⚪ Auditoría integral de privacidad y seguridad del ecosistema.

> Estos elementos están identificados en el roadmap, pero **no deben interpretarse como funcionalidades ya disponibles**.

### Orden de trabajo recomendado

```text
ATLAS + JGB
    ↓
MATRIZ HARDWARE
    ↓
CABE / RULA
    ↓
BENCHMARKS REALES
    ↓
RANKING ECONÓMICO COMPLETO
    ↓
AGENTIC / LB
    ↓
ROUTER
    ↓
WEB / APP
    ↓
MANADA
    ↓
TCO
    ↓
OPTIMIZACIÓN MULTIOBJETIVO
```

**Roadmap consolidado:** [`docs/ROADMAP.md`](docs/ROADMAP.md).

---

## ¿Qué es LEONES?

LEONES investiga, mide y construye un ecosistema de IA agéntica Libre/Open que pueda ejecutarse en **hardware real de consumo**, con especial prioridad al software **Copyleft**.

No pretende ser simplemente otro catálogo de modelos. El proyecto intenta responder una pregunta práctica:

> **¿Qué combinación de hardware, modelo, runtime, herramientas y arquitectura permite convertir un PC de consumo en una máquina agentic realmente útil?**

Y una segunda pregunta es igual de importante:

> **¿Cómo podemos transformar las mediciones de muchos equipos reales en mejores recomendaciones para todos?**

Por eso LEONES combina **prospección, conocimiento estructurado, experimentación local, benchmarks agentivos, evidencia reproducible y conocimiento colectivo**.

---

# 🗺️ Mapa del proyecto y documentación

LEONES está compuesto por varias capas que deben evolucionar juntas. El README es la puerta de entrada y la documentación especializada explica cada pieza.

```text
                         LEONES
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
 PROSPECCIÓN             ATLAS              EJECUCIÓN
       │                   │                   │
       │              ┌────┼────┐              │
       │              │    │    │              │
       │             JGB rendimiento hardware  │
       │              │    │    │              │
       └──────────────┴────┼────┴──────────────┘
                           ▼
                     RECOMENDADOR
                           │
                    ┌──────┴──────┐
                    ▼             ▼
                 TÉCNICO      ECONÓMICO
                    │             │
                    └──────┬──────┘
                           ▼
                     EJECUCIÓN LOCAL
                           │
                       MEDICIÓN
                           │
                         MANADA
                           │
                           ↺
```

### Documentación fundamental

- [`LEONES_DECISION_LOG.md`](LEONES_DECISION_LOG.md) — historia, decisiones congeladas y fundamentos.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — recopilación consolidada de todo lo que queda por hacer y orden recomendado.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitectura general.
- [`docs/PILLARS.md`](docs/PILLARS.md) — pilares del proyecto.
- [`docs/PLATFORMS.md`](docs/PLATFORMS.md) — plataformas Linux de referencia.
- [`PIPELINE_E2E.md`](PIPELINE_E2E.md) — pipeline extremo a extremo.
- [`scripts/README.md`](scripts/README.md) — filosofía y contrato de los scripts.

---

# 📚 Subproyecto Open LLM Atlas → recomendador

El **Open LLM Atlas** es la memoria estructurada de LEONES. Su función no es ser simplemente una lista de modelos, sino mantener conocimiento trazable sobre **modelos, familias, organizaciones, benchmarks, hardware, procedencia y criterios de apertura** para que otras capas puedan utilizarlo.

El subproyecto Atlas conecta esa memoria con el motor de recomendación:

```text
FUENTES / PROSPECCIÓN
        │
        ▼
   INGESTA ATLAS
        │
        ▼
   OPEN LLM ATLAS
        │
   ┌────┼───────────────┐
   ▼    ▼               ▼
  JGB rendimiento    hardware
   │    │               │
   └────┼───────────────┘
        ▼
      CABE
        │
        ▼
  ¿es viable?
    │       │
   NO      SÍ
    │       │
 excluir   ▼
       PRECIOS REALES
           │
       control calidad
           │
           ▼
     COSTE HARDWARE
           │
           ▼
    RANKING ECONÓMICO
           │
           ▼
      RECOMENDADOR
```

### Qué aporta el Atlas

- Una **fuente estructurada de conocimiento** en lugar de información dispersa.
- Procedencia para saber de dónde procede cada dato.
- Separación entre datos observados, reproducibles y verificados.
- Clasificación de apertura mediante el **Índice JGB**.
- Relación entre modelo, rendimiento y requisitos de hardware.
- Base para generar recomendaciones reproducibles y actualizables.

### El Índice JGB

El **Índice JGB** es una dimensión independiente. Representa el criterio de apertura/libertad adoptado para los modelos y **no se sustituye por rendimiento, precio ni ranking económico**.

```text
JGB          → apertura / libertad
Rendimiento  → capacidad observada
Hardware     → viabilidad
Precio       → coste observado

                    ↓
             combinación auditable
                    ↓
              recomendación
```

### El bot de precios

El coste que utiliza el recomendador procede de un bot mensual de precios de hardware.

Fuentes activas:

1. **Coolmod** — prioritaria.
2. **PcComponentes** — secundaria.
3. **MediaMarkt España** — secundaria.
4. **LDLC España** — apoyo europeo.

**Amazon está descartada** y no forma parte de la cobertura activa.

El bot extrae, normaliza y somete los productos a control de calidad. Las observaciones rechazadas se conservan para auditoría, pero no alimentan el recomendador.

### Ranking económico

La V1 combina:

```text
calidad_técnica =
    0,35 × rendimiento_normalizado
  + 0,25 × JGB_normalizado
  + 0,40 × hardware_fit

ranking_económico =
    calidad_técnica / (coste_hardware / 100)
```

La fórmula es parametrizable y experimental. Primero se determina si el modelo **CABE** en el hardware; después se estudia su economía. Un precio bajo nunca rescata una configuración técnicamente inviable.

### Validación

La integración precios → Atlas → recomendador está validada mediante GitHub Actions. La ejecución validada pasó los tests de integración de precios y ranking económico, generó las recomendaciones, generó el ranking económico y publicó las salidas.

### Índice completo de documentación del subproyecto

- [`atlas/README.md`](atlas/README.md) — entrada específica al Atlas.
- [`atlas/INGEST.md`](atlas/INGEST.md) — ingesta.
- [`atlas/schema.json`](atlas/schema.json) — esquema de datos.
- [`docs/PROSPECTION.md`](docs/PROSPECTION.md) — prospección.
- [`docs/RESULT_SCHEMA.md`](docs/RESULT_SCHEMA.md) — contrato de resultados.
- [`docs/hardware-price-sources.md`](docs/hardware-price-sources.md) — fuentes de precios y decisiones.
- [`docs/hardware-price-quality.md`](docs/hardware-price-quality.md) — control de calidad.
- [`docs/atlas-hardware-price-integration.md`](docs/atlas-hardware-price-integration.md) — integración precios ↔ Atlas.
- [`docs/atlas-economic-ranking.md`](docs/atlas-economic-ranking.md) — ranking económico y evolución.
- [`data/prospection/atlas_recommendations.csv`](data/prospection/atlas_recommendations.csv) — recomendaciones técnicas.
- [`data/prospection/atlas_economic_ranking.csv`](data/prospection/atlas_economic_ranking.csv) — ranking económico.

---

# La arquitectura Atlas → recomendador

El Atlas es la memoria estructurada del ecosistema. El recomendador utiliza esa memoria para contestar una pregunta práctica: **qué candidato tiene sentido para una necesidad y un hardware concretos**.

```text
                    OPEN LLM ATLAS
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
      ÍNDICE JGB      RENDIMIENTO       HARDWARE
          │            tokens/s       CPU / RAM / GPU
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                    FIT / CABE TÉCNICO
                           │
                     ¿es viable?
                      │         │
                     NO        SÍ
                      │         │
                   excluir     ▼
                         PRECIO REAL OBSERVADO
                                │
                         bot mensual de precios
                                │
                         control de calidad
                                │
                                ▼
                     COSTE HARDWARE OBSERVADO
                                │
                                ▼
                        RANKING ECONÓMICO
```

La separación de responsabilidades es deliberada: el Atlas conserva conocimiento; el bot de precios observa el mercado; el recomendador combina las dimensiones sin convertir una de ellas en sustituto de las demás.

---

# Índice JGB: una dimensión independiente

El **Índice JGB** se conserva como una dimensión propia del Atlas. Representa el criterio de apertura/libertad adoptado para evaluar el carácter abierto de los modelos y no debe convertirse en una simple traducción de rendimiento o precio.

La documentación del ranking económico mantiene expresamente esta separación: el JGB puede influir en la calidad técnica del candidato, pero **JGB no significa velocidad, JGB no significa precio y JGB no sustituye a la evidencia de ejecución**.

La documentación detallada del criterio y su utilización en el motor se encuentra en [`docs/atlas-economic-ranking.md`](docs/atlas-economic-ranking.md), sección **Índice JGB**.

---

# Bot de precios de hardware

El precio utilizado por el recomendador no se introduce manualmente en cada modelo. Se alimenta mediante un bot mensual que recoge precios de componentes y genera observaciones normalizadas.

```text
FUENTES → extracción → normalización → CONTROL DE CALIDAD
                                      │             │
                                  aceptar       rechazar
                                      │             │
                                      ▼             ▼
                            hardware_prices.csv  auditoría
                                      │
                                      ▼
                                 recomendador
```

El bot no debe rellenar huecos con precios inventados. Una ausencia de precio sigue siendo una ausencia de precio.

Véanse [`docs/hardware-price-sources.md`](docs/hardware-price-sources.md) y [`docs/hardware-price-quality.md`](docs/hardware-price-quality.md).

---

# Integración Atlas ↔ hardware ↔ precios

Una decisión de diseño fundamental es que **el precio pertenece al perfil de hardware, no al modelo LLM**.

```text
LLM
 │
 ├── JGB
 ├── rendimiento
 └── requisitos de memoria
          │
          ▼
     PERFIL HARDWARE
          │
      ┌───┼───┐
      ▼   ▼   ▼
     CPU RAM GPU
      │   │   │
      └───┼───┘
          ▼
  PRECIOS OBSERVADOS
          │
          ▼
 COSTE HARDWARE OBSERVADO
```

Si falta un precio, no se estima automáticamente. La cobertura puede ser `partial` o `unknown`, y el ranking no debe presentar un `economic_score` ficticio.

Véase [`docs/atlas-hardware-price-integration.md`](docs/atlas-hardware-price-integration.md).

---

# Ranking económico

La V1 utiliza una ponderación explícita y auditable:

```text
calidad_técnica =
    0,35 × rendimiento_normalizado
  + 0,25 × JGB_normalizado
  + 0,40 × hardware_fit

ranking_económico =
    calidad_técnica / (coste_hardware / 100)
```

Los pesos son una **V1 experimental y parametrizable**. No son una verdad universal ni deben confundirse con el propio Índice JGB.

## Primero viabilidad, después economía

```text
¿CABE / es viable?
   ├── NO → excluir
   └── SÍ
        ↓
 evidencia suficiente
        ↓
 JGB + rendimiento + hardware
        ↓
 precio observado
        ↓
 ranking económico
```

La documentación completa está en [`docs/atlas-economic-ranking.md`](docs/atlas-economic-ranking.md).

---

## La filosofía LEONES

### 1. Empieza por la necesidad, no por el script

LEONES no pretende que el usuario ejecute una colección de herramientas porque existen. La aplicación pregunta primero qué quiere conseguir y conduce al **siguiente paso mínimo** que responde a esa necesidad.

> **No ejecutes un script porque existe: ejecútalo porque responde a tu siguiente pregunta.**

El flujo general es:

```text
NECESIDAD
   ↓
HARDWARE
   ↓
MODELO
   ↓
RUNTIME
   ↓
INFERENCIA
   ↓
EVALUACIÓN / AGENTIC
   ↓
INFORME
   ↓
PRIVACIDAD
   ↓
PUBLICACIÓN
   ↓
ESTADÍSTICAS
   ↓
MEJORES RECOMENDACIONES
```

### 2. Herramientas pequeñas y responsabilidades claras

Los scripts son la interfaz local mínima entre una persona y LEONES. Cada herramienta debe responder a **una pregunta concreta** y hacer las menores cosas posibles.

La separación canónica es:

| Herramienta | Pregunta | Responsabilidad |
|---|---|---|
| `leones-hardware.py` | ¿Qué máquina tengo? | Descubrir y explicar el hardware relevante. |
| `leones-model.py` | ¿Qué modelo tengo? | Identificar el modelo y sus metadatos básicos. |
| `leones-runtime.py` | ¿Qué runtime local tengo? | Detectar endpoints/runtimes disponibles. |
| `leones-infer.py` | ¿Cómo rinde una inferencia pequeña? | Medir inferencia básica reproducible. |
| `leones-evaluation.py` | ¿Puede completar tareas agentivas? | Medir tareas agentivas con criterios explícitos. |
| `leones-report.py` | ¿Qué evidencia tengo? | Convertir resultados en un informe legible. |
| `leones-privacy.py` | ¿Qué puede salir de mi máquina? | Revisar posibles datos sensibles. |
| `leones-publish.py` | ¿Quiero compartirlo? | Publicar únicamente mediante acción explícita. |
| `leones-stats.py` | ¿Qué aprende el conjunto? | Agregar resultados sin convertirlos artificialmente en evidencia verificada. |
| `leones-manada-report.py` | ¿Quiero aportar un informe? | Preparar un informe técnico para la Manada. |
| `leones-manada-stats.py` | ¿Qué aprende la Manada? | Agregar los informes compartidos voluntariamente. |

El orquestador puede coordinar el recorrido, pero **no debe absorber la responsabilidad de todos los componentes**.

Los scripts antiguos o especializados se conservan durante la migración hasta que exista una decisión explícita de sustitución, evitando duplicar funciones sin motivo.

### 3. Cada herramienta debe hablar con el usuario

La ejecución no debe ser una caja negra. Cada script debe explicar qué hace, qué ha detectado, qué no puede saber y qué debería hacer el usuario a continuación.

---

# Estado del proyecto

Para el estado actualizado por áreas, consulta la [matriz de estado al principio de este README](#-estado-global-del-proyecto) y el [roadmap consolidado](docs/ROADMAP.md).

El estado debe distinguir siempre entre:

- **terminado y validado**;
- **en desarrollo**;
- **sin empezar**.

No se debe considerar terminada una pieza simplemente porque existe un script: debe existir documentación suficiente, pruebas cuando sean aplicables y una validación real de su salida.
