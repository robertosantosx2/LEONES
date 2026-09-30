# BigMoeLLM ↔ ODS ↔ LEONES
**Perfil:** runtime experimental para MoE que supera VRAM mediante mmap, pinning de host y streaming directo desde NVMe.
**Estado LEONES:** 🟡 candidato experimental P1 · ⏳ reproducción pendiente.

## 1. Resumen
BigMoeLLM está diseñado alrededor de GPUs de consumo con memoria insuficiente para el conjunto completo de expertos. Combina pesos host memory-mapped, pinning de regiones calientes y lectura directa de expertos desde almacenamiento.

## 2. Encaje ODS
Su interés principal es explorar una ruta intermedia entre llama.cpp convencional y runtimes de paging especializados. Podría convertirse en backend opcional detrás de un endpoint OpenAI-compatible si la interfaz de serving resulta estable.

## 3. Hardware
El proyecto está orientado a GPUs de consumo. Las cifras publicadas para modelos Qwen MoE grandes deben tratarse como evidencia externa. En una RTX 3050 de 4 GB, el objetivo debe ser un modelo pequeño y una prueba de concepto, no extrapolar resultados de GPUs con más VRAM.

## 4. Storage
El acceso NVMe puede dominar el rendimiento. ODS debe medir IOPS, throughput secuencial/aleatorio, latencia y cache residency.

## 5. Riesgos
Proyecto experimental, compatibilidad de modelos potencialmente limitada y posible dependencia de detalles CUDA. La integración directa en la distribución base de ODS sería prematura.

## 6. Plan
Probar fuera de ODS → verificar modelo/API → medir → contenerizar → manifest de capacidades → añadir sólo como backend experimental.

## 7. Veredicto
| Área | Evaluación |
|---|---|
| MoE > VRAM | 🟢 |
| GPU consumo | 🟢 |
| NVMe | 🟢 |
| Madurez | 🟡 |
| API | 🟡 verificar |
| RTX 3050 | 🟡/🔴 según modelo |
| Integración | 🟡 |

**Clasificación:** P1 experimental.
**Fuente:** https://github.com/OllyJohnston/BigMoeLLM