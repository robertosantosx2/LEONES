# Open LLM Atlas + LEONES — Arquitectura consolidada

## Estado

**v0.1 — criterio y arquitectura fijados.**

Open LLM Atlas se integra en LEONES como subproyecto. El Atlas es la capa de conocimiento estructurado; el recomendador es la capa de decisión; la prospección diaria alimenta ambos.

## 1. Principio general

El sistema no debe responder «cuál es el mejor LLM» de forma universal. Debe determinar **qué configuración es más adecuada para una carga de trabajo concreta en un hardware y entorno determinados**.

Unidad de recomendación:

```text
modelo × variante × cuantización × runtime × hardware × workload × restricciones
```

## 2. Capas

```text
                     LEONES
                       │
                PROSPECCIÓN DIARIA
                       │
                       ▼
                 OPEN LLM ATLAS
                       │
       ┌───────────────┼────────────────┐
       │               │                │
    MODELOS        EVIDENCIAS       OBSERVACIONES
       │               │                │
       │          JGB / apertura    MSA / benchmarks
       │               │                │
       └───────────────┼────────────────┘
                       ▼
              DEPLOYMENT KNOWLEDGE
                       │
       modelo × quant × runtime × hardware
                       │
                       ▼
              RECOMMENDATION ENGINE
                       │
           ┌───────────┼───────────┐
           ▼           ▼           ▼
       viabilidad   calidad     rendimiento
           │           │           │
           └───────────┼───────────┘
                       ▼
              RECOMENDACIÓN EXPLICABLE
                       │
                       ▼
                    LEONES
```

## 3. JGB: criterio oficial de apertura/libertad

El Índice JGB se deriva de Jesús M. Gonzalez-Barahona, *Generative AI in your own infrastructure* (Fuenlabrada, 6 de julio de 2026).

El marco distingue seis clases:

| Nivel | Clase |
|---:|---|
| 0 | Behind-app model |
| 1 | Directly accessible model |
| 2 | Available weights model |
| 3 | Open weight model |
| 4 | Open source model |
| 5 | Reproducible (libre) model |

Las cinco dimensiones se almacenan por separado:

- Access
- Model control
- Data control
- Autonomy
- Trust

**JGB no mide calidad, inteligencia, velocidad ni utilidad.**

### Regla de clasificación

No se puede asignar un nivel JGB superior simplemente porque:

- los pesos estén disponibles;
- el modelo sea ejecutable localmente;
- tenga una licencia aparentemente abierta;
- sea popular o de alta calidad.

La clasificación debe apoyarse en evidencia y guardar `confidence`.

### Evidencia insuficiente

Si no existe evidencia suficiente para justificar una dimensión o categoría:

```text
jgb_level       = unknown
jgb_class       = unknown
confidence      = low
verification    = needs_verification
```

No se completa por inferencia.

## 4. JGB y self-hostability son conceptos diferentes

```text
JGB / libertad
      ≠
self-hostability
      ≠
performance
      ≠
quality
```

Un modelo puede ser técnicamente self-hostable sin alcanzar JGB 4 o 5. Del mismo modo, una clasificación de apertura no garantiza que el modelo sea adecuado para un hardware concreto.

## 5. Rendimiento: principio MSA

Las mediciones de Model Speed Arena se incorporan como **observaciones empíricas**.

No se almacenará:

```text
modelo → 80 tok/s
```

sino:

```text
modelo + hardware + runtime + cuantización + contexto + workload
        → observación de rendimiento
```

Las observaciones deben conservar:

- fuente;
- URL;
- fecha;
- hardware;
- runtime;
- cuantización/formato;
- contexto/carga;
- tokens/s y métricas disponibles;
- metodología;
- confianza.

Una observación externa nunca sustituye los metadatos intrínsecos del modelo.

## 6. Viabilidad antes de recomendación

El motor debe aplicar primero filtros duros:

1. ¿Cabe en memoria?
2. ¿Es compatible con el runtime?
3. ¿Soporta la modalidad/carga solicitada?
4. ¿Dispone del contexto requerido?
5. ¿Puede ejecutarse en el hardware elegido?

Solo después se comparan calidad, rendimiento y preferencias.

## 7. No existe un score universal

Las dimensiones deben permanecer separadas:

```text
quality
speed
memory
compatibility
privacy
openness/JGB
reliability
cost
```

El usuario puede priorizarlas según su caso de uso.

La apertura JGB no debe convertirse automáticamente en un componente obligatorio del score de calidad.

## 8. Flujo de prospección

```text
prospección diaria
      ↓
nuevo/actualizado modelo
      ↓
actualización Atlas
      ↓
¿cambios de apertura?
      ↓
JGB verification queue
      ↓
evidencia primaria
      ↓
clasificación JGB + confianza
      ↓
¿hay nueva observación de rendimiento?
      ↓
performance_observations
      ↓
Recommendation Engine
```

## 9. Cola de verificación JGB

Los registros heredados que solo dicen `Open weights` no se convierten automáticamente en JGB 3.

Estado inicial conservador:

```text
jgb_class = unknown
verification_status = needs_verification
confidence = low
```

La cola se prioriza por:

1. `local_priority=high`;
2. relevancia para el recomendador;
3. impacto de cambios recientes;
4. disponibilidad de evidencia primaria.

## 10. Evidencia y auditoría

Cada clasificación JGB debe poder responder:

- ¿qué fuente la justifica?
- ¿qué parte de la fuente respalda cada dimensión?
- ¿cuándo se verificó?
- ¿qué confianza tiene?
- ¿qué podría hacer que dejase de ser válida?

Los cambios de licencia, pesos, código de entrenamiento, datasets o condiciones de uso deben poder disparar una revisión.

## 11. Relación con Barahona

La clasificación JGB **no sustituye** la clasificación de apertura de Jesús Rodríguez Barahona existente en el Atlas.

Ambas taxonomías se mantienen independientes para permitir comparación y análisis.

```text
                  OPENNESS
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
     BARAHONA                  JGB
     taxonomía             dimensiones de
     existente             libertad/control
```

No se debe convertir ninguna de las dos taxonomías en un sustituto de benchmarks de calidad.

## 12. Modelo de datos mínimo

```text
models
  │
  ├── jgb_classifications
  │       └── jgb_evidence
  │
  ├── model_deployments
  │       ├── hardware_profiles
  │       ├── runtime_profiles
  │       └── workload_profiles
  │
  └── performance_observations
          └── sources
```

## 13. Criterio operativo fijado

A partir de esta versión, cualquier nuevo dato incorporado al Atlas deberá respetar estas reglas:

**A.** No confundir pesos disponibles con Open Weight.

**B.** No confundir apertura con rendimiento.

**C.** No confundir apertura con self-hostability.

**D.** No convertir una observación de rendimiento en propiedad intrínseca del modelo.

**E.** No clasificar JGB sin evidencia suficiente.

**F.** Mantener fuente, fecha y confianza.

**G.** Mantener JGB y Barahona como taxonomías independientes.

**H.** Hacer que la recomendación sea explicable y dependiente del contexto de uso.

## 14. Próxima evolución

### v0.1
Criterio fijado, esquema y documentación.

### v0.2
Clasificación JGB verificada de los modelos de alta prioridad.

### v0.3
Ingesta automática de observaciones MSA/benchmarks.

### v0.4
Motor determinista de recomendación.

### v0.5
Integración completa con la prospección diaria de LEONES.

### v1.0
Recomendador operativo con explicación de evidencia, compatibilidad y rendimiento.
