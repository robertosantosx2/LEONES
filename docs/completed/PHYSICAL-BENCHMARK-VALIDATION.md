# Validación física de benchmarks — protocolo LEONES

## Estado

**🟢 PROTOCOLO CERRADO / COBERTURA FÍSICA PENDIENTE**

Este documento define y cierra el procedimiento. **No certifica que LEONES ya tenga una cobertura amplia de mediciones sobre hardware físico.** Las pruebas simuladas o de integración comprueban el software, no el rendimiento del equipo. fileciteturn130file0L2-L2

## Qué queda cerrado

El circuito de medición física queda definido de extremo a extremo:

```text
hardware + modelo + condiciones
            ↓
      ejecución real
            ↓
     registro original
            ↓
        validación
            ↓
       CABE / RULA
            ↓
    evidencia publicada
            ↓
    Atlas / matriz / router
```

## Qué queda pendiente

**Solo la obtención progresiva de ejecuciones reales.** No queda pendiente diseñar otro mecanismo para medir.

Cada futura medición debe identificar hardware, modelo, runtime y condiciones; obtener `tokens_per_second` de la ejecución real; conservar las ejecuciones individuales; validar el registro y solo entonces publicarlo. fileciteturn131file0L2-L2

## Reglas esenciales

- `estimated` nunca se convierte en `measured`.
- Un benchmark de terceros es evidencia externa, no medición propia.
- CABE/RULA se deriva del valor medido; nunca sustituye al dato primario.
- Se conservan las ejecuciones individuales y no solo un promedio.
- No se comparan configuraciones distintas como si fueran equivalentes.
- No se sobrescriben mediciones históricas.
- La identidad del hardware y modelo debe ser suficiente para reproducir el experimento.

### Contrato CABE/RULA

```text
<1        → NO_CABE
1–<10     → CABE
10–100    → RULA
>100      → RULA+
```

## Calidad mínima

Una medición apta para evidencia debe proceder de una ejecución real, identificar inequívocamente modelo/hardware/runtime, conservar las condiciones, obtener el tok/s mediante el runner, superar el validador y poder trazarse hasta la ejecución original. fileciteturn131file0L2-L2

## Campaña física futura

La campaña se ejecutará progresivamente sobre perfiles representativos, priorizando equipos y modelos que permitan cubrir especialmente los rangos **CABE (1–10 tok/s)** y **RULA (10–100 tok/s)**. Los perfiles descritos en este protocolo son objetivos de campaña, **no resultados**. fileciteturn131file0L2-L2

## Limpia y da esplendor

Este documento no contiene resultados ficticios, cifras de prueba presentadas como reales ni afirmaciones de cobertura que el proyecto todavía no puede demostrar. La documentación distingue expresamente mecanismo terminado de evidencia física pendiente.

No se añaden nuevos adaptadores, workflows ni artefactos de medición como parte de este cierre documental.

## No concurrencia

Todo workflow futuro que escriba resultados físicos debe respetar la regla global: un único grupo escritor `leones-main-writers` y `cancel-in-progress: false`.

## Criterio de cierre definitivo

La **infraestructura/protocolo queda cerrado 🟢**. La **cobertura empírica física permanece 🟡** hasta disponer de ejecuciones reales suficientes y reproducibles.
