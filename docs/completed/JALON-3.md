# JALÓN 3 — Protocolo de medición real

**Estado: 🟢 CERRADO (diseño y contrato)**  
**Fecha de cierre: 2026-08-27**

## Objetivo

Fijar antes de la ejecución física el protocolo que convierte una ejecución de runtime en evidencia comparable, reproducible y conservable.

## Contrato mínimo de una medición

Toda medición LEONES debe conservar, cuando esté disponible:

- modelo y revisión/checkpoint;
- cuantización;
- contexto y configuración de inferencia;
- prompt/tarea y protocolo de generación;
- warm-up;
- número de iteraciones;
- TTFT, cuando el runtime lo permita;
- throughput de generación (`tokens/s`), con su definición explícita;
- tokens de entrada/salida cuando estén disponibles;
- tiempo de pared y/o duración de ejecución;
- memoria RAM y VRAM, cuando puedan observarse;
- consumo energético, si existe una fuente de medición válida;
- versión exacta del runtime;
- hardware y sistema operativo;
- comando realmente ejecutado;
- stdout/stderr relevantes;
- timestamp;
- `execution_id` único;
- hash del artefacto o de la evidencia conservada.

## Reglas de medición

1. **No mezclar estimación, dato reportado y medición física.**
2. El hardware, modelo, cuantización y runtime deben quedar identificados.
3. El warm-up debe quedar registrado y separado de las iteraciones medidas.
4. Las iteraciones y el protocolo deben ser constantes dentro de una comparación.
5. Un dato ausente se conserva como `unknown`; no se inventa ni se deduce sin declarar el método.
6. El throughput debe indicar qué tokens y qué intervalo representa.
7. La evidencia debe permitir reconstruir qué se ejecutó, cuándo, dónde y con qué configuración.
8. Una medición de una máquina concreta no se presenta como rendimiento universal del modelo.

## Flujo canónico

```text
modelo + revisión + cuantización
              ↓
        hardware/OS
              ↓
       runtime/version
              ↓
     protocolo controlado
              ↓
          warm-up
              ↓
       N iteraciones
              ↓
      métricas observadas
              ↓
       evidence record
              ↓
       quality/validation
              ↓
        conservación
```

## Relación con JALÓN 2

El protocolo queda **cerrado antes de Debian**. JALÓN 2 es el encargado de ejecutar este contrato en runtime físico y producir la primera evidencia real bajo estas condiciones.

Por tanto, cerrar JALÓN 3 **no significa que todas las métricas ya estén medidas**; significa que no será necesario rediseñar el protocolo al llegar a Debian.

## Decisión

**JALÓN 3 queda cerrado en su dimensión de diseño, contrato y protocolo.** La ejecución física permanece en JALÓN 2.
