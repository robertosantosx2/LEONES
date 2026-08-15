# Esquema explicativo del Índice JGB

El Índice JGB no es una nota de calidad. Es un **mapa de apertura, libertad, control, autonomía y confianza**.

```text
                         ÍNDICE JGB
                              │
       ┌──────────────────────┼──────────────────────┐
       │                      │                      │
   6 CLASES              5 DIMENSIONES         4 LIBERTADES
       │                      │                      │
       │                  Access                 Use
       │                  Model control         Study
       │                  Data control          Modification
       │                  Autonomy              Sharing
       │                  Trust
       │
       ├─ 0 Behind-app
       ├─ 1 Directly accessible
       ├─ 2 Available weights
       ├─ 3 Open weight
       ├─ 4 Open source
       └─ 5 Reproducible (libre)
                              │
                              ▼
                        EVIDENCIA ATLAS
                    fuente + fecha + confianza
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
                 JGB OPENNESS      SELF-HOSTABLE
                    │                   │
                    │             ¿puede ejecutarse
                    │              en infraestructura
                    │                  propia?
                    │                   │
                    └─────────┬─────────┘
                              ▼
                       RECOMENDADOR
```

## Matriz de las seis clases

| Nivel | Clase | Acceso | Control modelo | Control datos | Autonomía | Confianza |
|---:|---|---|---|---|---|---|
| 0 | Behind-app | definido por aplicación | ninguno | ninguno | ninguna | ninguna |
| 1 | Directly accessible | restricciones de API | restricciones de API | ninguno | ninguna | ninguna |
| 2 | Available weights | con condiciones | con condiciones | completo | con condiciones | ninguna |
| 3 | Open weight | uso como se quiera | control profundo | completo | restringido el estudio | ninguna |
| 4 | Open source | uso como se quiera | control profundo | completo | estudio detallado restringido | parcial |
| 5 | Reproducible (libre) | uso como se quiera | control profundo | completo | completa | completa |

## Qué significa visualmente

**JGB 0–1:** el usuario depende esencialmente de una aplicación o API.

**JGB 2:** los pesos permiten despliegue y control técnico, pero existen condiciones que pueden limitar uso, modificación o redistribución.

**JGB 3:** se eliminan las condiciones de uso y modificación indicadas por el marco, pero permanece restringida la libertad de estudio del modelo.

**JGB 4:** se añade tooling abierto y una descripción detallada del entrenamiento; la apertura del dataset de entrenamiento no es requisito.

**JGB 5:** se alcanza el nivel reproducible/libre: toda la información necesaria sobre el modelo y disponibilidad del dataset de entrenamiento.

## Regla de lectura

```text
          MÁS APERTURA
               ▲
               │
 JGB 5 ────────┤ reproducible
 JGB 4 ────────┤ open source
 JGB 3 ────────┤ open weight
 JGB 2 ────────┤ available weights
 JGB 1 ────────┤ directly accessible
 JGB 0 ────────┤ behind-app
               │
               └──────────────►

El número ordena clases; NO es una puntuación de calidad.
```

## Separación crítica para LEONES

```text
                  MODELO
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
    JGB OPENNESS             LOCAL EXECUTION
        │                         │
   libertad/control          hardware
   autonomía                  runtime
   confianza                  memoria
   estudio                    cuantización
                              rendimiento
        │                         │
        └────────────┬────────────┘
                     ▼
                RECOMENDACIÓN
```

Un modelo JGB 5 no tiene por qué ser el mejor modelo para un hardware concreto. Un modelo JGB 3 puede ser perfectamente recomendable para una carga local. La apertura y la adecuación técnica son dimensiones distintas.

## Evidencia y confianza

La clasificación debe ser auditable:

```text
JGB class
   + dimensiones
   + evidencia documental
   + fuente
   + fecha de comprobación
   + nivel de confianza
```

Cuando la fuente no permita decidir, el Atlas debe conservar `unknown` y promover la comprobación mediante prospección, en lugar de inventar una clasificación.
