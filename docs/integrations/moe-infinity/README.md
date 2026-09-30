# MoE-Infinity ↔ ODS ↔ LEONES
**Perfil:** runtime CUDA para inferencia MoE con offload de expertos a RAM/NVMe, caché activacional, prefetch y servidor OpenAI-compatible.
**Estado LEONES:** 🟢 fuente activa · 🟢 candidato prioritario ODS · ⏳ benchmark LEONES pendiente.

## 1. Resumen ejecutivo
MoE-Infinity ataca exactamente el cuello de botella que motiva esta prospección: modelos MoE cuyos expertos no caben simultáneamente en VRAM. Mantiene pesos activos en GPU y descarga expertos a memoria host y SSD, con caché consciente de activaciones y prefetch. Además incorpora serving continuo, paged KV cache, streaming SSE, health monitoring y multi-GPU en un único servidor.
Para ODS encaja mejor como **backend especializado MoE**, no como sustituto de llama-server.

## 2. Arquitectura
El flujo conceptual es:
`router → expert IDs → cache GPU → RAM/SSD → transferencia → kernels CUDA`.
La implementación separa runtime de serving, por lo que ODS puede consumirlo mediante HTTP en lugar de integrar directamente Python/PyTorch en el dashboard.

## 3. Capacidades relevantes
- Offload de expertos a host memory y SSD.
- Activation-aware caching y prefetch.
- Continuous batching y paged KV.
- Streaming OpenAI-compatible.
- Multi-GPU single-server.
- Hot reload, watchdog y crash recovery.
- Soporte de varias familias: DeepSeek, Mixtral, Qwen3/Qwen3.5-MoE, GLM y otras.

## 4. Encaje con ODS
Propuesta:
`extensions/services/moe-infinity/` con imagen propia, almacenamiento de modelos y endpoint interno. LiteLLM puede tratarlo como proveedor OpenAI-compatible. El selector de runtime de ODS debería activarlo sólo cuando el perfil del modelo indique MoE + offload requerido + CUDA compatible.

## 5. Hardware
Requiere CUDA y una pila PyTorch/CUDA coherente. La documentación actual apunta especialmente a GPUs modernas; por tanto la RTX 3050 4 GB del equipo ODS debe considerarse **objetivo experimental**, no compatibilidad asumida. La memoria y el NVMe pasan a ser recursos de primer orden.

## 6. Storage
El modelo puede superar ampliamente VRAM y parte de RAM. LEONES debe medir throughput sostenido, latencia, espacio disponible y comportamiento dentro del contenedor. Un benchmark que sólo registre tok/s no basta: hay que registrar bytes transferidos y cache hit rate.

## 7. Integración LEONES
Registrar runtime, commit/tag, modelo, formato, CUDA/PyTorch, VRAM/RAM, NVMe, cache size, contexto, TTFT, prefill, decode, I/O y estabilidad. Las cifras del README son **reported**, no measured por LEONES.

## 8. Riesgos
- Dependencia fuerte de CUDA.
- Build complejo.
- Compatibilidad modelo por modelo.
- Coste de transferencias si la caché no captura suficiente localidad.
- La ruta SSD puede dominar latencia en hardware modesto.

## 9. Plan
1. Prueba aislada del runtime y API.
2. Validar un MoE pequeño.
3. Medir con límites de RAM/VRAM realistas.
4. Empaquetar extensión ODS.
5. Añadir capability manifest.
6. Integrar selector y benchmark LEONES.

## 10. Veredicto
| Área | Evaluación |
|---|---|
| Backend ODS opcional | 🟢 Alto encaje |
| MoE grande | 🟢 Muy alto |
| OpenAI API | 🟢 |
| CUDA | 🟢 |
| RTX 3050 4GB | 🟡 Experimental |
| NVMe offload | 🟢 |
| Complejidad integración | 🟡 Alta |
| Benchmark LEONES | ⏳ |

**Clasificación:** P1 — runtime candidato prioritario.
**Fuente:** https://github.com/EfficientMoE/MoE-Infinity