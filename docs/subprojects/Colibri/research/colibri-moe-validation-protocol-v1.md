# Protocolo LEONES: validación MoE híbrida de Colibrì

**Versión:** 1.0.0  
**Fecha:** 2026-11-10  
**Estado:** especificación; no implica que los experimentos se hayan ejecutado.  
**Hardware de referencia:** MSI Thin 15 B12UC, RTX 3050 Laptop 4 GiB (sm_86), RAM 14 GiB, Ubuntu.

## 1. Objetivo

Definir una campaña repetible para validar por separado: presupuesto de memoria y reserva previa; colocación indivisible de la cadena CUDA Qwen3.6; caché de expertos GPU; split exacto de misses CPU/GPU; y controlador adaptativo posterior.

LEONES conserva el protocolo y los recibos. Colibrì ejecuta la inferencia y emite los datos del motor. No se infieren resultados a partir de la configuración, la existencia de un binario o un test que no se haya ejecutado.

## 2. Contrato de evidencia

| Estado | Uso |
|---|---|
| PLAN_ONLY | Configuración preparada, sin ejecutar |
| RUNNING | Proceso iniciado, sin resultado final |
| RUN_COMPLETED_UNPARSED | Proceso terminó, recibo no validado |
| MEASURED | Recibo válido con métricas, identidad de modelo/build y protocolo |
| FAILED | Ejecución terminó con error |
| TIMEOUT | Alcanzó el límite de tiempo |
| INVALID | Recibo incoherente, incompleto o no conforme |

Solo MEASURED puede alimentar comparativas o conclusiones de rendimiento. Los datos estimados deben etiquetarse ESTIMATED y nunca mezclarse con mediciones.

## 3. Fases y gates

### Gate A — inventario y presupuesto

Registrar GPU UUID/nombre/compute capability/memoria/driver; RAM y swap; kernel y distribución; modelo/revisión/cuantización/tamaño/SHA-256; bytes de trunk, KV/mirror, scratch, reservas y presupuesto restante de expertos; y variables relevantes (CUDA_EXPERT_GB, G_reserve, COLI_PLACE, COLI_CUDA_CHAIN).

Criterio: las sumas deben ser coherentes y el presupuesto no puede superar la memoria admisible. Un cap explícito de expertos nunca debe consumir la reserva de la cadena ni el margen de seguridad.

### Gate B — colocación atómica de cadena

| ID | Escenario | Resultado esperado |
|---|---|---|
| CHAIN-01 | Un dispositivo puede alojar el conjunto completo | Se admite todo el grupo en ese dispositivo |
| CHAIN-02 | Ningún dispositivo puede alojar el conjunto | No se admite ningún tensor; fallback explícito |
| CHAIN-03 | Dos dispositivos solo pueden alojar fragmentos distintos | Rechazo; no se divide el grupo |
| CHAIN-04 | Falta una proyección obligatoria o lm_head | Rechazo completo |
| CHAIN-05 | Falla una subida tras varias correctas | Rollback de todas las asignaciones de la cadena |
| CHAIN-06 | Reserva de scratch/KV cambia el espacio disponible | El planner recalcula y no sobreasigna |
| CHAIN-07 | Cap numérico de expertos excede el remanente | Se limita al remanente, sin tocar reservas |
| CHAIN-08 | Overflow en sumas de tamaños | Rechazo seguro; nunca wraparound |

Criterio: chain_ready=true solo si todas las proyecciones obligatorias y lm_head están disponibles en el mismo dispositivo y las reservas están confirmadas. La colocación parcial no es éxito.

### Gate C — baseline de inferencia

Ejecutar primero una referencia sin split CPU/GPU. Fijar modelo, hash, prompt, sampler, contexto, número de tokens, backend y configuración. Separar warm-up y realizar al menos tres repeticiones medidas.

### Gate D — caché y split exacto

| Variante | Cache GPU | Misses CPU | Share |
|---|---:|---:|---:|
| D0 | no | no | 0% |
| D1 | sí | no | 0% |
| D2 | sí | sí | 10% |
| D3 | sí | sí | 20% |
| D4 | sí | sí | 30% |
| D5 | sí | sí | 50% |

La implementación híbrida debe demostrar que cada experto requerido contribuye exactamente una vez. No activar mecanismos aproximados tipo tail-skip. Si el layout/operación no está soportado por el kernel CPU, el caso debe ir por fallback exacto y quedar registrado.

### Gate E — control adaptativo

Solo después de D0–D5. Comparar modo auto con el mejor share fijo, usando ventanas A/B alternadas. Registrar decisiones del controlador, muestras de ancho de banda, tasa CPU, tiempo de sincronización y cambios de share. El modo auto debe evitar regresiones sostenidas respecto al mejor fijo dentro de una tolerancia predefinida.

## 4. Métricas obligatorias

**Inferencia:** prompt/completion tokens, TTFT, prefill tokens/s, decode tokens/s, duración total, contexto, batch y sampler.

**MoE:** expertos requeridos, hits, misses, misses CPU y misses subidos; bytes H2D, uploads y evictions; tiempo CPU de expertos; tiempo de transferencia y sincronización; espera GPU/CPU; share solicitado y aplicado.

**Recursos:** VRAM pico/mínima libre, RAM pico/disponible, RSS, swap antes/después, page faults, temperatura y clocks si están disponibles.

Si un campo no puede medirse, se omite o se marca null con explicación; nunca se rellena con cero como sustituto.

## 5. Repetibilidad

- Tres repeticiones como mínimo por variante; cinco preferibles para comparativas finales.
- Alternar el orden de variantes para reducir sesgo térmico y de caché.
- No cambiar modelo, prompt, contexto, sampler o versión entre variantes comparadas.
- Separar warm-up de mediciones.
- Guardar errores y ejecuciones incompletas, no descartarlas silenciosamente.
- Guardar stdout/stderr originales y manifiesto junto al recibo.
- Comparar exactitud con logits o referencia token a token cuando cambie el camino de cómputo.

## 6. Estructura de artefactos

Cada experimento usa un directorio único bajo experiments/colibri-moe/<fecha>-<id>/ con manifest.json, engine.stdout.log, engine.stderr.log, metrics.json y checksums.txt. comparison.json solo si existe referencia comparable.

El esquema normativo de manifest.json está en [colibri-moe-benchmark-v1.schema.json](../../../schemas/colibri-moe-benchmark-v1.schema.json).

## 7. Límites del equipo de referencia

La RTX 3050 Laptop dispone de 4 GiB de VRAM y el equipo de 14 GiB de RAM. No asumir que las pruebas de tandem.cpp en sm_89/sm_120 se reproducen en sm_86. No copiar masivamente expertos a pinned RAM ni interpretar swap como memoria DMA utilizable. Ajustar contexto, scratch y caché al presupuesto medido en cada ejecución.

## 8. Regla de publicación

Un informe LEONES debe indicar commit exacto de Colibrì y motor; hash del modelo y configuración; estado de evidencia; comando ejecutado; repeticiones; hardware observado; desviación y límites; y si el test fue host/fake-CUDA o CUDA real.

Hasta ejecutar los tests, el estado de esta campaña es **SPECIFIED / NOT RUN**. No hay todavía resultados de rendimiento híbrido de Colibrì en el MSI.