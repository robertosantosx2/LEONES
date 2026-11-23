# Xiaomi Mi 9T Pro — matriz de runtimes y orden de evaluación

**Estado:** evaluación documental inicial; no hay resultados físicos LEONES.  
**Dispositivo esperado:** Snapdragon 855 / Adreno 640 / Hexagon 690, pendiente de confirmar en el teléfono.  
**Ruta prioritaria:** Android sin root.

## Criterios

La matriz separa facilidad de puesta en marcha de rendimiento potencial. El rendimiento real depende del build, kernels, driver, memoria, temperatura y modelo. No se publican estimaciones numéricas como si fueran resultados.

## Matriz inicial

| Runtime / ruta | Backend inicial | Dificultad | Probabilidad inicial de ejecución | Potencial a investigar | Estado |
|---|---|---:|---|---|---|
| llama.cpp Android/Termux ARM64 | CPU NEON/dotprod si existe | Baja | Alta | Baseline y posible rendimiento fuerte en modelos pequeños | PLANNED |
| ExecuTorch | XNNPACK CPU | Media-alta | Media | Competencia CPU optimizada | PLANNED |
| LiteRT | CPU / delegate disponible | Media-alta | Media | Modelos compactos y tareas especializadas | PLANNED |
| llama.cpp Vulkan | Adreno 640 | Alta | Incierta | Posible aceleración; validar kernels y driver | PLANNED |
| MLC LLM Android | Vulkan/CPU según build | Alta | Incierta | Ruta GPU compilada | PLANNED |
| Qualcomm QNN | HTP/DSP si SM8150 y SDK son compatibles | Muy alta | Desconocida | Investigación de acelerador | DISCOVERY |
| Servicio local | Backend previamente validado | Alta | Condicionada | Nodo REDIL | BLOCKED_BY_RUNTIME |

## Orden por facilidad (ejecución)

1. Inventario ADB/Termux sin root.
2. llama.cpp CPU con GGUF de 360M–0.6B.
3. Afinado CPU y memoria.
4. Escalado a 1B–1.7B.
5. ExecuTorch/XNNPACK y LiteRT.
6. Vulkan en Adreno 640.
7. MLC LLM.
8. QNN/Hexagon.
9. Servicio local y REDIL.

El plan completo contiene gates, criterios y comandos: [XIAOMI-MI-9T-PRO-TEST-PLAN.md](XIAOMI-MI-9T-PRO-TEST-PLAN.md).

## Orden de rendimiento: hipótesis, no ranking medido

No existe base para afirmar hoy que Vulkan, XNNPACK o Hexagon superarán a llama.cpp CPU en este Snapdragon. Para maximizar rendimiento útil, ejecutar primero los modelos pequeños y establecer CPU como baseline; después medir XNNPACK y Vulkan bajo condiciones idénticas. Hexagon solo entra en la comparativa si se demuestra compatibilidad y ejecución real.

El ranking final se publicará por caso de uso y tamaño de modelo:
- decode tokens/s sostenido;
- TTFT/prefill;
- memoria máxima;
- energía por token, solo si medida físicamente;
- temperatura/throttling;
- calidad de tarea.

## Selección inicial de modelos

| Orden | Familia/modelo candidato | Tamaño aproximado de parámetros | Uso |
|---|---|---:|---|
| 1 | SmolLM2-360M-Instruct | 360M | Smoke y baseline |
| 2 | Qwen2.5-0.5B-Instruct | 0.5B | Baseline principal |
| 3 | Qwen3-0.6B | 0.6B | Comparación compacta |
| 4 | Qwen2.5-1.5B-Instruct | 1.5B | Escalado |
| 5 | Qwen3-1.7B / SmolLM2-1.7B | 1.7B | Escalado |
| 6 | Llama 3.2-3B | 3B | Exploratorio, solo con margen de memoria |

Cada modelo necesita artefacto GGUF realmente disponible, licencia revisada, soporte de arquitectura/tokenizer en la versión de llama.cpp y hash fijado. Los nombres de la tabla son candidatos, no descargas aprobadas.

## Referencias primarias de proyectos

- llama.cpp: https://github.com/ggml-org/llama.cpp
- ExecuTorch: https://github.com/pytorch/executorch
- LiteRT: https://github.com/google-ai-edge/LiteRT
- MLC LLM: https://github.com/mlc-ai/mlc-llm
- Qualcomm AI Engine Direct SDK: https://www.qualcomm.com/developer/software/qualcomm-ai-engine-direct-sdk

Las referencias documentan proyectos, no soporte garantizado del Mi 9T Pro. La compatibilidad se comprobará contra la versión concreta y el SoC/Android detectados.
