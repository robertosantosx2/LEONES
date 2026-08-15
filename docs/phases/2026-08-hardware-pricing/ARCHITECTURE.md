# Arquitectura — Bot mensual de precios

```text
                  WORKFLOW MENSUAL
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
    Coolmod         PcComponentes     MediaMarkt
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
                      LDLC
                         │
                         ▼
                    ADAPTADORES
                         │
                 HTTP directo / fallback
                         │
                         ▼
                   NORMALIZACIÓN
                         │
                         ▼
                    VALIDACIÓN
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
     OBSERVACIÓN VÁLIDA            RECHAZADA
          │                             │
          ▼                             ▼
      HISTÓRICO                    CALIDAD/AUDITORÍA
          │
          ├──────────────┐
          ▼              ▼
       RESUMEN       MARKET SUMMARY
          │              │
          └───────┬──────┘
                  ▼
             RECOMENDADOR
```

## Separación de datos

El histórico conserva observaciones individuales. El resumen ofrece una vista de trabajo. La capa de calidad conserva el motivo de rechazo/aceptación.

## Unidades

Los precios se expresan en EUR y llevan fecha de observación. Los productos se comparan por correspondencia concreta cuando es posible.

## Robustez

El fallo de una fuente no debe detener las demás. El proceso solo debe fallar por ausencia global de datos o fallo general de las fuentes configuradas.
