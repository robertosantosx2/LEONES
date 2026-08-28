# LEONES — Arquitectura de referencia

**Estado:** guía de referencia operativa
**Ámbito:** RC1 y evolución posterior

## Flujo canónico

```text
LEONES
   │
   ├── investigación / Atlas / conocimiento
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

## Principios de interpretación

1. **LEONES conserva la autoridad de decisión.** LLMFit aporta la información de adecuación de modelo/hardware; no sustituye la decisión de LEONES.
2. **ODS y Magnitude son vías de ejecución/medición complementarias.** LEONES no debe inventar un tercer sistema paralelo cuando pueda consumir sus capacidades mediante interfaces compatibles.
3. **La interfaz de ejecución debe converger en un contrato compatible con `llama-server`** para separar selección y ejecución del modelo local.
4. **La medición pertenece a LEONES.** La ejecución local debe producir datos observables y reproducibles que LEONES pueda convertir en evidencia.
5. **La evidencia precede al benchmark de tareas.** No se deben presentar estimaciones, rankings externos o resultados declarativos como sustitutos de una medición local reproducible.
6. **El objetivo final es medir tareas realizadas**, no únicamente tokens/segundo: la evidencia de runtime alimenta benchmarks de tareas y estos alimentan MANADA.
7. **Atlas/investigación y selección alimentan el flujo, pero no deben contaminar el núcleo de ejecución.** Las piezas históricas o sustituidas se deprecian conservando procedencia.

## Frontera arquitectónica

### Dentro del núcleo

- investigación, Atlas y conocimiento que alimentan la selección;
- selección y decisión de LEONES;
- integración con LLMFit como fuente de adecuación;
- integración con ODS/SOHO y Magnitude como capacidades externas de ejecución/asistencia;
- interfaz compatible de ejecución;
- `llama-server` y el modelo local;
- medición reproducible y contratos de evidencia;
- benchmark de tareas;
- salida hacia MANADA.

### Fuera del núcleo

- runners históricos `leones-*`;
- duplicados de selección, runtime o benchmark;
- scripts que mantengan una ruta paralela al contrato canónico sin justificación;
- estimaciones presentadas como mediciones reales.

## Regla de evolución

Cada nueva pieza debe responder a una de estas preguntas:

- ¿aporta conocimiento para seleccionar?
- ¿mejora la decisión de LEONES?
- ¿proporciona ejecución compatible?
- ¿permite medir de forma reproducible?
- ¿convierte la medición en benchmark de tareas?
- ¿alimenta MANADA?

Si no cumple ninguna, no entra en el núcleo por defecto: se conserva como periférica o se depreca tras auditar dependencias.
