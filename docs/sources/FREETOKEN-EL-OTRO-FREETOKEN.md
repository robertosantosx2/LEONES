# El otro FreeToken — FreeToken de FlashML

## Identidad

**Nombre de referencia en LEONES:** El otro FreeToken

**Proyecto:** FreeToken, de FlashML-org.

**Repositorio:** https://github.com/FlashML-org/FreeToken

**Paper:** https://arxiv.org/abs/2608.16157

**Proyecto:** https://flashml.ai

**Licencia del repositorio:** Apache-2.0.

## Qué es

FreeToken es un runtime de serving **edge-native especializado en Mixture-of-Experts (MoE)**. Su propuesta no consiste simplemente en cargar un modelo grande en una GPU pequeña, sino en tratar el equipo local como una plataforma elástica formada por GPU, CPU, memoria de host e interconexión.

La idea central es adaptar continuamente dónde residen los expertos y dónde se ejecuta el trabajo según las características reales del hardware. El proyecto declara soporte para modelos MoE de gran tamaño y hardware NVIDIA RTX 30/40/50, además de escenarios que combinan VRAM y memoria del sistema.

## Por qué interesa a LEONES

FreeToken encaja directamente con la hipótesis que LEONES está desarrollando: **la selección correcta no puede terminar en el modelo; debe seleccionar una combinación modelo × cuantización × runtime × hardware × workload**.

En un MoE grande, la capacidad total de memoria necesaria puede superar ampliamente la VRAM disponible aunque solo una parte de los expertos esté activa por token. FreeToken intenta explotar precisamente esa diferencia mediante residencia selectiva de expertos, ejecución CPU/GPU y caché.

Por ello debe tratarse como un runtime candidato de primera clase para la familia de escenarios `edge-moe-bandwidth-adaptive`.

## Arquitectura y mecanismos relevantes

### Ejecución CPU–GPU adaptativa

FreeToken describe una política `q*` que adapta la co-ejecución CPU/GPU al ancho de banda disponible. Esto es especialmente importante para LEONES porque el selector ya debe considerar el ancho de banda efectivo y no únicamente la capacidad nominal de VRAM.

### Caché global de expertos

El runtime mantiene una caché LRU de expertos para conservar en memoria rápida los componentes que se reutilizan con mayor frecuencia.

### Prefill con double buffering

El streaming de capas durante el prefill utiliza double buffering para solapar transferencia y cómputo cuando el hardware lo permite.

### Formato FTW

FreeToken incorpora un formato de pesos rápido, FTW, destinado a acelerar la carga y el acceso a los pesos en su propia arquitectura de ejecución.

### Estado y caché semánticos

Una característica particularmente relevante para agentes es el uso de checkpoints/anchors semánticos para reutilizar estado recurrente y cachés KV. La intención es evitar recomputaciones completas cuando un agente modifica el contexto mediante tool calls, bloques de pensamiento u otras operaciones.

### Gestión elástica de memoria

El runtime puede redistribuir dinámicamente VRAM entre caché de expertos y KV cache sin reiniciar el motor ni volver a cargar los pesos. Para LEONES esto convierte la memoria disponible en una variable dinámica del workload y no en un simple umbral estático.

## Evidencia externa disponible

El paper de FreeToken, publicado en agosto de 2026, afirma resultados en hardware que van desde una GPU de portátil de 8 GB hasta una GPU de workstation de 96 GB. Entre los resultados destacados se encuentran **39,3 tok/s para Qwen3.6-35B-A3B en una RTX 4060 Laptop de 8 GB** y **14,9 tok/s para GLM-5.2 753B en una RTX PRO 6000 de 96 GB**, frente a 7,3 tok/s de llama.cpp en la configuración comparada del estudio.

Estas cifras son **evidencia externa del proyecto**, no benchmarks LEONES. No deben trasladarse a otra máquina sin conservar modelo, versión, cuantización, workload, contexto, concurrencia y configuración del runtime.

## Integración conceptual con LEONES

La cadena objetivo es:

```text
hardware discovery
      ↓
LLMFit / candidates
      ↓
runtime-selection.v1
      ↓
FreeToken cuando el perfil MoE lo justifica
      ↓
A01 executor / benchmark runtime
      ↓
grader
      ↓
evidence
      ↓
Router
```

El selector debe considerar, como mínimo:

- VRAM disponible y memoria RAM disponible.
- Ancho de banda efectivo de memoria.
- Ancho de banda host→GPU/PCIe medido.
- Coste de transferencia CPU↔GPU.
- Tamaño total del MoE frente a capacidad de VRAM.
- Número y tamaño de expertos activos.
- Localidad/reutilización de expertos.
- Capacidad y presión de la KV cache.
- Longitud de contexto.
- Patrón de workload: chat, coding, tool calling, multi-turn, agente.
- Latencia objetivo y throughput.
- Compatibilidad real del modelo y cuantización con el runtime.

## Qué debe medir LEONES

Para convertir FreeToken en evidencia canónica se deben registrar, como mínimo:

1. Identidad exacta del modelo y commit/revisión.
2. Formato y cuantización de pesos.
3. GPU, VRAM, CPU y RAM.
4. Driver/CUDA y versión del runtime.
5. Configuración de caché de expertos.
6. Memoria usada por pesos, expertos y KV.
7. Ancho de banda host↔GPU y ancho de banda de memoria relevante.
8. TTFT.
9. TPOT / tokens por segundo de decode.
10. Throughput bajo concurrencia definida.
11. Longitud de entrada y salida.
12. Resultado del workload y del grader.
13. Evidencia reproducible y artefactos del benchmark.

## Limitaciones y estado

El repositorio evoluciona rápidamente. A fecha de esta ficha existen solicitudes abiertas relacionadas con GPU dual, soporte de hardware antiguo, Docker y Apple Silicon. Por tanto, **no debe asumirse portabilidad universal**.

La documentación oficial publicada actualmente indica Linux x86_64, GPU NVIDIA y driver r580+ / CUDA 13 para la instalación acelerada, con `uv`/pip y compilación JIT de kernels en el primer uso.

## Relación con otros runtimes

FreeToken no sustituye a llama.cpp, vLLM, SGLang, AirLLM u otros runtimes. Su interés está en el nicho donde el modelo MoE es demasiado grande para la VRAM disponible y el sistema puede beneficiarse de memoria heterogénea y reutilización de expertos.

LEONES debe comparar **la misma carga de trabajo**, no slogans de rendimiento. El benchmark canónico debe determinar cuándo FreeToken gana y cuándo el coste de transferencia, caché o compatibilidad hace preferible otro runtime.

## Conclusión LEONES

**Clasificación:** `runtime-candidate`

**Subclase:** `edge-moe-bandwidth-adaptive`

**Prioridad:** alta para MoE grandes y agentes locales.

**Evidencia:** externa, fuerte pero condicionada; pendiente de reproducción LEONES.

**Uso en selector:** sí, mediante `runtime-selection.v1`.

**Uso como benchmark propio:** solo después de pasar por executor + grader + evidence.

**Principio:** FreeToken demuestra que la pregunta correcta no es «¿cabe el modelo en la GPU?», sino «¿cómo se distribuyen modelo, expertos, KV y cómputo entre los recursos reales de esta máquina para este workload?».
