# Arquitectura — Ranking económico V1

```text
                 ATLAS
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
       JGB     rendimiento  hardware
        │          │          │
        └──────────┼──────────┘
                   ▼
               FIT SCORE
                   │
              CABE/viabilidad
                   │
                   ▼
            PRECIO OBSERVADO
                   │
                   ▼
             COSTE HARDWARE
                   │
                   ▼
          RANKING ECONÓMICO
```

## Contratos

El Atlas proporciona conocimiento y evidencia. El bot de precios proporciona observaciones económicas. El ranking combina ambas capas sin convertir una en sustituta de la otra.

## Cobertura

La V1 trabaja con el coste de componentes disponible y debe expresar explícitamente `price_coverage`.

```text
complete → puede calcularse
partial  → información incompleta
unknown  → no existe base suficiente
```

## No destructividad conceptual

El ranking es una salida derivada. No modifica la definición del JGB ni convierte el score económico en una nueva clasificación de apertura.
