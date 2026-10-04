# LEONES — Prehistoria de ChatGPT (snapshot 2026-10-04)

> **Estado:** reconstrucción provisional, no exportación oficial de la cuenta de ChatGPT.
>
> **Fecha del snapshot:** 2026-10-04.
>
> Este documento conserva la cronología que puede reconstruirse desde el contexto y las conversaciones disponibles en ChatGPT. No debe confundirse con una exportación oficial de datos de OpenAI.

## 1. Por qué este documento existe

La historia técnica de LEONES empezó antes del primer commit actualmente visible en su repositorio GitHub. El repositorio puede establecer fechas de código, pero las conversaciones de ChatGPT permiten recuperar parte de la **prehistoria conceptual**: ideas, diseños, decisiones y proyectos que precedieron o dieron origen a LEONES.

La reconstrucción definitiva requerirá la exportación oficial de datos de ChatGPT (`conversations.json` o los JSON numerados de una exportación grande).

## 2. Primeros hitos localizados

| Fecha | Línea / proyecto | Papel en la evolución |
|---|---|---|
| **2026-07-11** | **Open LLM Atlas / Atlas-Open-LLM** | Primer hito de esta reconstrucción. Atlas nace como inventario y conocimiento estructurado sobre modelos, familias, organizaciones, licencias, hardware y benchmarks. |
| **2026-07-11 → julio** | **Atlas / recommendation engine** | La idea evoluciona de catálogo a recomendación: modelo × cuantización × formato × runtime × hardware × contexto × carga. |
| **2026-08-10** | **LEONES — repositorio** | Fecha de creación del repositorio GitHub `robertosantosx2/LEONES`: 2026-08-10T06:10:29Z. |
| **2026-08-15** | **LEONES — primer commit actualmente recuperado** | Commit `088cb4ce71d571b25e4e75b7644b7b528c52778a`, `docs(atlas): integrate 2026 LLM systems methodology`, 2026-08-15T20:03:51+02:00. |
| **2026-08-15** | **Atlas → LEONES** | Atlas pasa a integrarse conceptualmente como subproyecto especializado de LEONES. |
| **agosto 2026** | **LEONES / prospección / recomendación** | LEONES amplía Atlas hacia descubrimiento, perfilado, candidatos, selección, consentimiento, instalación y evidencia. |
| **septiembre 2026** | **LEONES / ejecución** | El foco se desplaza desde recomendar modelos hacia ejecutar la combinación adecuada de modelo, runtime, hardware y proveedor. |
| **septiembre–octubre 2026** | **ODS + LEONES** | ODS se investiga como plataforma de ejecución local/híbrida; aparecen TensorFold, Edge0, Strata, Magnitude, Noodle, FreeLLM y otros candidatos alrededor de esta capa. |

## 3. Evolución conceptual

```text
OPEN LLM ATLAS
      │
      │ inventario / conocimiento
      ▼
MODELO ≠ RECOMENDACIÓN
      │
      │ modelo × cuantización × runtime × hardware
      ▼
RECOMMENDATION ENGINE
      │
      ▼
    LEONES
      │
      ├── conocimiento
      ├── prospección
      ├── perfilado
      ├── candidatos
      ├── elección
      ├── consentimiento
      ├── instalación
      ├── verificación física
      ├── benchmark
      └── evidencia
              │
              ▼
       EJECUCIÓN REAL
              │
       ┌──────┴──────┐
       ▼             ▼
      ODS       otros runtimes
       │
       ├── local
       ├── híbrido
       ├── selección dinámica
       ├── privacidad
       └── coste
```

## 4. Qué está verificado y qué no

### Verificado mediante GitHub

- Repositorio: `robertosantosx2/LEONES`.
- Creación del repositorio: **2026-08-10T06:10:29Z**.
- Primer commit actualmente recuperado de la historia accesible: **2026-08-15T20:03:51+02:00**.
- SHA: `088cb4ce71d571b25e4e75b7644b7b528c52778a`.
- Mensaje: `docs(atlas): integrate 2026 LLM systems methodology`.

### Recuperado de la historia disponible de ChatGPT

- Primer hito localizado de **Open LLM Atlas / Atlas-Open-LLM**: **2026-07-11**.
- Atlas precede cronológicamente al repositorio de LEONES.
- La evolución posterior muestra una transición de catálogo/inventario de modelos a sistema de recomendación y finalmente a plataforma de selección y ejecución.

### Aún no verificable desde el acceso actual

- Fecha exacta de creación de cada **Project** de ChatGPT.
- Lista completa de todos los Projects históricos.
- Primera conversación absoluta de cada Project.
- Primer archivo generado en cada Project.
- Correspondencia exhaustiva entre Projects de ChatGPT y repositorios GitHub.

## 5. Exportación oficial pendiente

ChatGPT permite solicitar una exportación desde **Configuración → Controles de datos → Exportar datos**. La exportación se entrega posteriormente como ZIP y puede contener `conversations.json` o archivos JSON numerados en exportaciones grandes.

Cuando ese archivo esté disponible, esta reconstrucción debe actualizarse para:

1. Enumerar todos los Projects/conversaciones recuperables.
2. Ordenarlos por primera actividad.
3. Identificar la primera idea y el primer artefacto de cada línea.
4. Cruzar cada línea con repositorios GitHub.
5. Distinguir creación del Project, primera conversación, primer archivo, creación del repositorio, primer commit y primera integración en LEONES.
6. Marcar explícitamente incertidumbres y reconstrucciones inferidas.

## 6. Regla histórica de LEONES

No mezclar **evidencia** con **reconstrucción**.

Las fechas procedentes de GitHub deben conservarse como evidencia de GitHub. Las fechas procedentes de memoria/contexto de ChatGPT deben etiquetarse como actividad localizada. Las fechas obtenidas de una futura exportación oficial deberán etiquetarse como evidencia de exportación.

---

**Snapshot generado el 2026-10-04.**