# vLLM MoE CPU Offload RFC ↔ ODS ↔ LEONES
**Perfil:** RFC de vLLM para offload dinámico de expertos a CPU con subconjunto caliente en GPU.
**Estado LEONES:** 🟡 P2 — evidencia de diseño, no implementación objetivo.

## Resumen
El RFC plantea mantener los expertos en CPU y copiar dinámicamente los activos a GPU, con caché de hot experts. Aunque el issue fue cerrado como no planificado, es una fuente útil para entender las decisiones de diseño de un runtime generalista.

## ODS
Sirve para comparar dos estrategias: runtime dedicado (MoE-Infinity/ramvamp) frente a capability añadida a vLLM. El selector debería poder representar ambas sin asumir una implementación concreta.

## LEONES
Registrar el patrón como `moe_cpu_offload`, `hot_expert_gpu_cache` y `prefetch`, y comprobar en implementaciones activas si alguna de estas capacidades ha reaparecido.

## Veredicto
**Clasificación:** P2 — referencia de arquitectura y seguimiento upstream.
**Fuente:** https://github.com/vllm-project/vllm/issues/33869