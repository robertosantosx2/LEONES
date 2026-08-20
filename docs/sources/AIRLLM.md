# AirLLM — fuente de conocimiento para LEONES

- **Proyecto:** AirLLM
- **Repositorio primario:** https://github.com/lyogavin/airllm
- **Tipo:** runtime/biblioteca de inferencia orientada a reducir el uso de memoria durante la inferencia de LLM grandes.
- **Estado LEONES:** 🟢 fuente activa · 🟡 candidato de integración funcional · ⏳ pendiente de benchmark propio.
- **Fecha de revisión documental:** 2026-08-20

> **Regla de evidencia:** las cifras, compatibilidades y afirmaciones de rendimiento procedentes de AirLLM son evidencia externa hasta que LEONES las reproduzca. AirLLM no convierte por sí mismo un resultado en `measured`.

## 1. Qué aporta

AirLLM aborda escenarios en los que el modelo completo no resulta cómodo de mantener en la memoria aceleradora. Su estrategia de carga por capas permite mantener en memoria de ejecución la parte necesaria para el cálculo y mover el resto según el flujo de inferencia.

El valor para LEONES es ampliar el conjunto de modelos **ejecutables**, especialmente cuando la memoria es el cuello de botella. Ejecutable no significa automáticamente rápido, interactivo ni recomendable.

## 2. Mecanismos relevantes

### Carga por capas

La estrategia layer-wise reduce la necesidad de mantener simultáneamente todo el modelo en la memoria aceleradora. El coste se desplaza parcialmente hacia transferencias entre almacenamiento/CPU y el dispositivo de cálculo.

### Prefetching

El prefetching intenta solapar transferencia y cálculo. Para LEONES esto hace que el rendimiento dependa también de la latencia, ancho de banda y comportamiento sostenido del almacenamiento.

### Compresión / cuantización

El proyecto documenta opciones de reducción de precisión. La combinación exacta debe registrarse junto con el modelo y la versión del runtime; cualquier mejora de velocidad o memoria anunciada externamente requiere reproducción en el hardware objetivo.

### CPU

AirLLM contempla escenarios de inferencia CPU. LEONES debe distinguir siempre entre **compatibilidad de ejecución** y **rendimiento útil**.

## 3. Modelos y compatibilidad

La documentación del proyecto contempla numerosas familias de modelos. La compatibilidad efectiva debe comprobarse para la versión concreta de AirLLM, `torch`, `transformers`, arquitectura, formato de pesos, atención, precisión y hardware.

Los modelos MoE merecen una medición específica: el ahorro potencial de memoria puede venir acompañado de costes de transferencia, routing y sincronización.

## 4. Encaje arquitectónico en LEONES

AirLLM es un **runtime**, no una propiedad del modelo y no sustituye al preselector hardware-aware ni al benchmark canónico.

```text
Perfil hardware
      ↓
LLMFit — preselección hardware-aware
      ↓
Router LEONES — tarea + restricciones + evidencia
      ↓
Runtime Selector
      ├── runtimes convencionales
      └── AirLLM — cuando la memoria sea el cuello de botella
      ↓
Benchmark LEONES
      ↓
Atlas / recomendador
```

### Contrato conceptual del recomendador

Mantener separados, como mínimo:

- `model_id`
- `runtime_id = airllm`
- `hardware_profile`
- `precision`
- `compression`
- `context_length`
- `storage_profile`
- `measured_prefill_tps`
- `measured_decode_tps`
- `time_to_first_token`
- `peak_ram`
- `peak_vram`
- `disk_read_bytes`
- `disk_read_latency`
- `result_quality`

Así se evita atribuir al modelo el comportamiento específico del runtime.

## 5. Benchmark mínimo LEONES

Antes de promocionar AirLLM a una recomendación basada en evidencia medida, registrar:

1. instalación reproducible en Debian;
2. versiones exactas de AirLLM, PyTorch y Transformers;
3. modelo, commit/revisión y formato de pesos;
4. precisión/compresión;
5. espacio de almacenamiento;
6. tiempo de carga inicial;
7. TTFT;
8. tok/s de prefill y decode;
9. RAM pico;
10. VRAM pico, si existe GPU;
11. lectura y latencia del almacenamiento;
12. comportamiento con contextos crecientes;
13. estabilidad en sesiones largas;
14. calidad frente al mismo modelo en otro runtime comparable.

Para perfiles de bajo consumo, almacenamiento e I/O son variables de primer orden. Una configuración puede ser técnicamente ejecutable y quedar fuera del objetivo práctico de LEONES por latencia.

## 6. Reproducibilidad

LEONES debe registrar la combinación completa:

`airllm + torch + transformers + modelo + revisión + precisión + hardware + SO`

No basta con almacenar la versión de AirLLM: el ecosistema de inferencia cambia rápidamente y puede alterar compatibilidad y rendimiento.

## 7. Clasificación de evidencia

| Estado | Significado |
|---|---|
| `external` | Afirmación procedente de la documentación de AirLLM. |
| `verified-primary` | La identidad/procedencia del proyecto ha sido comprobada por LEONES. |
| `measured` | Resultado reproducido mediante benchmark LEONES en un perfil hardware concreto. |

La ficha actual queda en **fuente activa + candidato funcional**; no aporta todavía mediciones `measured`.

## 8. Valor estratégico

AirLLM permite separar tres preguntas que el recomendador de LEONES no debe confundir:

- **¿Cabe?** — capacidad y memoria.
- **¿Funciona?** — compatibilidad y estabilidad.
- **¿Sirve?** — rendimiento y calidad medidos para la tarea.

LLMFit ayuda con la primera preselección. AirLLM puede ampliar las opciones de ejecución. LEONES decide mediante evidencia y medición propia cuáles merecen una recomendación.

## 9. Fuente primaria y trazabilidad

Repositorio oficial: https://github.com/lyogavin/airllm

Esta ficha fue revisada el **2026-08-20**. Las afirmaciones externas se mantienen separadas de las mediciones LEONES y deben revisarse cuando cambien el repositorio, las arquitecturas soportadas o el stack de inferencia.
