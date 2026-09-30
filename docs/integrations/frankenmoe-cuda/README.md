# FrankenMoE-CUDA ↔ ODS ↔ LEONES
**Perfil:** runtime CUDA experimental con pipeline NVMe → RAM LRU → pinned staging → VRAM hot store para MoE.
**Estado LEONES:** 🟡 P1 experimental · ⏳ benchmark propio pendiente.

## 1. Resumen
FrankenMoE-CUDA implementa una arquitectura de tiers explícita para ejecutar modelos MoE que superan conjuntamente VRAM y RAM. Parte de GGUF y utiliza una caché acotada de expertos.

## 2. Arquitectura
`NVMe GGUF → bounded RAM LRU → pinned staging → bounded VRAM hot store → CUDA kernels`.
Este pipeline es muy cercano al Runtime Registry que ODS necesita estudiar.

## 3. Encaje
No debería reemplazar llama-server. Es un laboratorio de técnicas de expert paging y puede servir para validar qué capacidades debe declarar el runtime selector.

## 4. Riesgos
La dependencia de una rama/PoC de llama.cpp y el carácter experimental elevan el coste de mantenimiento. La API de servidor y compatibilidad de modelos deben comprobarse antes de crear un servicio ODS permanente.

## 5. Benchmark LEONES
Comparar contra llama.cpp sobre el mismo GGUF: carga, RAM/VRAM, bytes NVMe, TTFT, prefill, decode, calidad y estabilidad.

## 6. Veredicto
| Área | Evaluación |
|---|---|
| Arquitectura MoE paging | 🟢 Muy relevante |
| CUDA | 🟢 |
| NVMe | 🟢 |
| Madurez | 🔴 Experimental |
| Sustituto llama-server | 🔴 |
| Valor de investigación | 🟢 |

**Clasificación:** P1 para investigación, no producción.
**Fuente:** https://github.com/Endorpheen/FrankenMoE-CUDA