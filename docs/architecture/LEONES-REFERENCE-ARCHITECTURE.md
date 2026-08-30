# LEONES — Arquitectura de referencia

**Estado:** guía de referencia operativa
**Ámbito:** RC1 y evolución posterior

## Flujo canónico

```text
LEONES
   │
   ├── investigación / Atlas / conocimiento
   │       │
   │       ├── descubrimiento
   │       ├── prospección
   │       └── construcción / ingestión de Atlas
   │
   └── selección
          │
          ▼
     LLMFit
          │
          ▼
     LEONES decide
          │
          ├───────────────┐
          ▼               ▼
        ODS            Magnitude
       SOHO          asistente personal
          │               │
          └───────┬───────┘
                  ▼
          interfaz compatible
                  │
                  ▼
             llama-server
                  │
                  ▼
             modelo local
                  │
                  ▼
             LEONES mide
                  │
                  ▼
          evidencia reproducible
                  │
                  ▼
        benchmark de tareas
                  │
                  ▼
              MANADA
```

## Contrato de decisión

El flujo anterior queda formalizado por **[LEONES Decision Contract v1](LEONES-DECISION-CONTRACT-v1.md)**. Ese contrato define las responsabilidades y fronteras entre Atlas, LLMFit, la decisión de LEONES, ODS/SOHO, Magnitude, `llama-server`, medición y benchmark de tareas.

### Regla central

> **LLMFit informa; LEONES decide. ODS/Magnitude aportan capacidades; LEONES integra. `llama-server` ejecuta; LEONES mide. La medición produce evidencia; la evidencia alimenta benchmarks de tareas y MANADA.**

## Principios de interpretación

1. **LEONES conserva la autoridad de decisión.** LLMFit aporta la información de adecuación de modelo/hardware; no sustituye la decisión de LEONES.
2. **Investigación, prospección y Atlas son un subsistema protegido.** Su función es descubrir, normalizar, enriquecer y conservar conocimiento que alimenta la selección. No deben confundirse con runners históricos ni eliminarse durante la limpieza del núcleo de ejecución.
3. **Las herramientas que descubren fuentes, modelos, hardware, runtimes, agentes, skills, benchmarks u otras capacidades permanecen a salvo mientras formen parte del flujo de conocimiento.**
4. **Las herramientas que construyen, ingieren, normalizan o preparan Atlas permanecen a salvo mientras tengan una función vigente en ese flujo.**
5. **ODS y Magnitude son vías de ejecución/medición complementarias.** LEONES no debe inventar un tercer sistema paralelo cuando pueda consumir sus capacidades mediante interfaces compatibles.
6. **La interfaz de ejecución debe converger en un contrato compatible con `llama-server`** para separar selección y ejecución del modelo local.
7. **La medición pertenece a LEONES.** La ejecución local debe producir datos observables y reproducibles que LEONES pueda convertir en evidencia.
8. **La evidencia precede al benchmark de tareas.** No se deben presentar estimaciones, rankings externos o resultados declarativos como sustitutos de una medición local reproducible.
9. **El objetivo final es medir tareas realizadas**, no únicamente tokens/segundo: la evidencia de runtime alimenta benchmarks de tareas y estos alimentan MANADA.
10. **Atlas/investigación y selección alimentan el flujo, pero no deben contaminar el núcleo de ejecución.** Las piezas históricas o sustituidas se deprecian conservando procedencia.

## Frontera arquitectónica

### Núcleo protegido de conocimiento

- investigación y prospección;
- descubrimiento de modelos, hardware, runtimes, benchmarks, agentes, skills y capacidades;
- adaptadores de fuentes de descubrimiento;
- normalización y deduplicación de descubrimientos;
- construcción, ingestión y preparación de Atlas;
- contratos de conocimiento que alimentan la selección.

**Regla:** estas piezas **NO se mueven a `deprecated/` por una limpieza genérica**. Antes de deprecar cualquiera hay que demostrar que su función de descubrimiento/Atlas está sustituida y conservar la procedencia.

### Núcleo de decisión y ejecución

- selección y decisión de LEONES;
- integración con LLMFit como fuente de adecuación;
- integración con ODS/SOHO y Magnitude como capacidades externas de ejecución/asistencia;
- interfaz compatible de ejecución;
- `llama-server` y el modelo local;
- medición reproducible y contratos de evidencia;
- benchmark de tareas;
- salida hacia MANADA.

### Fuera del núcleo / candidatos a deprecación

- runners históricos `leones-*`;
- duplicados de selección, runtime o benchmark;
- scripts que mantengan una ruta paralela al contrato canónico sin justificación;
- herramientas de ejecución antiguas sustituidas por la ruta runtime actual;
- estimaciones presentadas como mediciones reales.

## Regla de evolución y limpieza

Cada nueva pieza debe responder a una de estas preguntas:

- ¿aporta conocimiento para seleccionar?
- ¿descubre o mantiene conocimiento para Atlas?
- ¿mejora la decisión de LEONES?
- ¿proporciona ejecución compatible?
- ¿permite medir de forma reproducible?
- ¿convierte la medición en benchmark de tareas?
- ¿alimenta MANADA?

Si una pieza pertenece a descubrimiento o Atlas, se considera **protegida por defecto** y se audita antes de tocarla.

Si no cumple ninguna función y existe una sustitución real, puede pasar a `deprecated/` conservando procedencia. No se elimina ni se depreca por intuición.

## Próximo umbral operativo

Todo lo anterior puede cerrarse y auditarse en GitHub. El siguiente paso que exige Ubuntu es la validación de la cadena real:

```text
selección
  → runtime gate
  → interfaz llama-server
  → modelo local
  → ejecución física
  → medición
  → evidencia
```

No se considera validada una capacidad de rendimiento hasta ejecutarla en hardware real y conservar evidencia reproducible.
