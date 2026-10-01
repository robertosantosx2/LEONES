# Edge0 — vigilancia para LEONES / ODS

**Estado:** vigilancia / investigación futura  
**Fecha:** 2026-10-01  
**Repositorio:** https://github.com/Edge0-AI/Edge0  
**Relación:** posible backend de inferencia para ODS; seguimiento desde LEONES

## Resumen

Edge0 es un framework abierto de inferencia **streaming MoE** que combina *SSD expert offload*, Recover-LoRA y un *prerouter* para predecir los expertos necesarios. El proyecto mantiene el backend separado del núcleo y expone un servidor HTTP compatible con OpenAI.

La idea es especialmente relevante para LEONES porque intenta desacoplar el tamaño total de un modelo MoE de la memoria que debe permanecer activa durante la inferencia.

## Situación actual

La versión actual implementa el backend **MLX para Apple Silicon**. El backend **CUDA está previsto pero todavía no está disponible como backend soportado**, por lo que no debe considerarse instalable actualmente en el ODS Linux/NVIDIA del laboratorio.

El repositorio ya reserva explícitamente `backends/cuda/` y mantiene una fachada común para `core`, `nn`, `io` y `quant`, lo que hace que la futura incorporación de CUDA sea arquitectónicamente relevante para ODS.

## Modelos vigilados

| Tier | Modelo base | Perfil publicado | Disco aproximado | Memoria activa publicada* |
|---|---|---|---:|---:|
| edge0-8b | Ling 3.0 hybrid | 8B-class, 128 expertos, 4-bit | ~4.2 GB | ~1.0 GB |
| edge0-35b | Qwen3.6-35B-A3B | 35B-class, 256 expertos, 4-bit | ~23 GB | ~2.9 GB |

\* Valores publicados para contextos cortos; no equivalen a la VRAM/RAM total necesaria. Hay que reservar margen para sistema, tokenizer y crecimiento del KV cache.

## Encaje con ODS

La integración potencial es sencilla conceptualmente porque Edge0 ofrece:

- `GET /healthz`
- `GET /v1/models`
- `POST /v1/chat/completions`
- streaming de chat
- API compatible con OpenAI

Por tanto, cuando exista un backend CUDA operativo, el flujo candidato sería:

```
ODS
 └── LiteLLM
      └── Edge0
           ├── streaming MoE
           ├── SSD expert offload
           ├── prerouter
           └── LoRA
```

No sería necesario convertir Edge0 en una aplicación de usuario independiente de ODS; la vía natural es tratarlo como **motor/backend de inferencia adicional**.

## Relevancia para el hardware NVIDIA de LEONES

La máquina NVIDIA de referencia de esta línea de investigación dispone de una RTX 3050 Laptop de 4 GB de VRAM.

No se debe inferir que los ~2.9 GB publicados para edge0-35b impliquen que el modelo vaya a funcionar en una GPU de 4 GB. Ese valor es memoria activa bajo el perfil de benchmark y requiere margen adicional.

La condición de prueba para LEONES será:

1. que exista un backend CUDA funcional y mantenido;
2. que Edge0 pueda ejecutarse de forma reproducible sobre Linux/NVIDIA;
3. medir VRAM real, RAM, tráfico SSD, tokens/s, latencia y estabilidad;
4. comprobar compatibilidad con la API OpenAI usada por ODS/LiteLLM;
5. comparar resultados con el backend que ODS utilice como referencia.

## Señales de vigilancia

El proyecto tiene solicitudes abiertas relacionadas con:

- soporte CUDA experimental;
- soporte para plataformas no macOS;
- ejecución de modelos Edge0 en hardware distinto de Apple Silicon.

Estas señales justifican mantenerlo en **Vigilancia**, pero no promover todavía su integración operativa en ODS.

## Hitos que activarían una nueva revisión

- [ ] Backend CUDA oficial o suficientemente estable.
- [ ] Linux/NVIDIA soportado de forma reproducible.
- [ ] Instalación documentada fuera de Apple Silicon.
- [ ] Benchmark CUDA publicado.
- [ ] Verificación con GPU de 4–8 GB.
- [ ] Prueba mediante API OpenAI-compatible detrás de LiteLLM.
- [ ] Evaluación de Edge0-8B.
- [ ] Evaluación de Edge0-35B.
- [ ] Determinar si el coste de I/O SSD compensa la reducción de memoria activa.

## Evidencia principal

- Arquitectura: https://github.com/Edge0-AI/Edge0/blob/main/docs/architecture.md
- Streaming SSD: https://github.com/Edge0-AI/Edge0/blob/main/docs/streaming.md
- Edge0-35B: https://github.com/Edge0-AI/Edge0/blob/main/docs/models/edge0-35b.md
- Edge0-8B: https://github.com/Edge0-AI/Edge0/blob/main/docs/models/edge0-8b.md
- Incidencias CUDA/no-macOS: https://github.com/Edge0-AI/Edge0/issues

## Conclusión de vigilancia

**Mantener Edge0 bajo vigilancia tecnológica para LEONES/ODS.**

La arquitectura tiene un encaje claro con la abstracción de backends de ODS y su API OpenAI-compatible. El bloqueo actual es la ausencia de un backend CUDA soportado y verificable. La próxima revisión debe centrarse en ese punto, no en intentar instalar la versión MLX en el ODS Ubuntu/NVIDIA.
