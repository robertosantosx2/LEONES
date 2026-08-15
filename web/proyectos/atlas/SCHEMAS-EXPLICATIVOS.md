# Esquemas explicativos del Atlas

## 1. Atlas → recomendador

```text
                     OPEN LLM ATLAS
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
      MODELOS           APERTURA          EVIDENCIA
        │             JGB + Barahona          │
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ▼
                    DEPLOYMENT LAYER
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
        HARDWARE         RUNTIME         WORKLOAD
           │               │               │
           └───────────────┼───────────────┘
                           ▼
                    OBSERVACIONES
                           │
                    MSA / benchmarks
                           ▼
                 RECOMMENDATION ENGINE
                           │
                           ▼
                 RECOMENDACIÓN EXPLICABLE
```

## 2. JGB

```text
                         JGB
                          │
       ┌──────────────────┼──────────────────┐
       ▼                  ▼                  ▼
     Access         Model control       Data control
       │                  │                  │
       └──────────────────┼──────────────────┘
                          ▼
                    Autonomy
                          │
                          ▼
                       Trust
                          │
                          ▼
              CLASE JGB 0 ──── 5
```

Las dimensiones no deben ocultarse dentro del nivel. El nivel es una síntesis; las dimensiones y su evidencia son los datos auditables.

## 3. JGB frente a ejecución local

```text
          ¿PUEDO USARLO?
                 │
                 ▼
             JGB Access
                 │
                 ▼
       ¿PUEDO CONTROLARLO?
                 │
                 ▼
         Model control
                 │
                 ▼
      ¿PUEDO CONTROLAR DATOS?
                 │
                 ▼
          Data control
                 │
                 ▼
      ¿DEPENDO DEL PROVEEDOR?
                 │
                 ▼
            Autonomy
                 │
                 ▼
       ¿PUEDO VERIFICARLO?
                 │
                 ▼
              Trust

                 ║
                 ║  distinto de
                 ▼
        SELF-HOSTABILITY
                 │
        hardware + runtime
        + pesos + contexto
                 │
                 ▼
          ¿PUEDE EJECUTARSE?
```

## 4. De modelo a recomendación

```text
MODELO
  │
  ├── arquitectura
  ├── parámetros
  ├── capacidades
  ├── benchmarks
  └── apertura
       │
       ├── JGB
       └── Barahona
  │
  ▼
VARIANTE
  │
  ├── quantización
  └── formato
  │
  ▼
RUNTIME
  │
  ▼
HARDWARE
  │
  ▼
WORKLOAD
  │
  ▼
OBSERVACIONES
  │
  ├── velocidad
  ├── latencia
  ├── memoria
  └── fiabilidad
  │
  ▼
RECOMENDACIÓN
```

## 5. Bucle de aprendizaje operativo

```text
PROSPECCIÓN DIARIA
       │
       ▼
   NUEVO MODELO
       │
       ▼
      ATLAS
       │
       ├───────────────┐
       ▼               ▼
  ¿CAMBIA JGB?    ¿HAY MÉTRICAS?
       │               │
       ▼               ▼
  VERIFICACIÓN     OBSERVACIÓN
       │               │
       └───────┬───────┘
               ▼
       RECOMMENDATION
               │
               ▼
          LEONES USER
               │
               ▼
       nueva medición local
               │
               └──────────────► ATLAS
```

## 6. Regla de oro

```text
NO:
modelo → score universal → recomendación

SÍ:
modelo
  + evidencia
  + apertura
  + hardware
  + runtime
  + workload
  + observaciones
  + preferencias
       ↓
recomendación explicable
```
