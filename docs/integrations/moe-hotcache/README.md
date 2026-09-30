# moe-hotcache ↔ ODS ↔ LEONES
**Perfil:** fork de llama.cpp con caché dinámica de expertos calientes y acceso desde RAM host a GPU.
**Estado LEONES:** 🟢 candidato P2 · ⏳ reproducción pendiente.

## 1. Resumen
moe-hotcache coloca expertos en RAM pinned y mantiene una pequeña caché VRAM de expertos usados con mayor frecuencia. La selección se adapta durante la ejecución a partir del routing observado.

## 2. Arquitectura
`routing IDs → counters → background refresh → VRAM hot slots`; los misses leen pesos host mediante UVA/DMA. Es especialmente interesante porque parte de llama.cpp y, conceptualmente, podría acercarse más a ODS que un runtime independiente.

## 3. Evidencia
El repositorio documenta experimentos sobre AMD ROCm y advierte explícitamente de resultados retractados por errores de calidad. Esto es una señal positiva de trazabilidad experimental, pero obliga a LEONES a verificar output además de throughput.

## 4. ODS
Puede estudiarse como parche upstream/experimental del backend llama-server. No debe incorporarse como reemplazo sin resolver portabilidad y estabilidad.

## 5. Hardware
La implementación publicada se valida en AMD/ROCm. NVIDIA/CUDA requiere prueba. En 4 GB VRAM la caché será pequeña y el beneficio dependerá fuertemente de RAM y PCIe.

## 6. Veredicto
| Área | Evaluación |
|---|---|
| Integración con llama.cpp | 🟢 Muy interesante |
| Cache dinámica | 🟢 |
| AMD | 🟢 |
| NVIDIA | 🟡 |
| Calidad/verificación | 🟡 Obligatoria |
| ODS | 🟡 |

**Clasificación:** P2 — fuente técnica de alto interés para llama-server.
**Fuente:** https://github.com/ap03906101/moe-hotcache