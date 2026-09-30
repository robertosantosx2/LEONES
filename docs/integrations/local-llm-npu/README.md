# local-llm-npu ↔ ODS ↔ LEONES
**Perfil:** inferencia local sobre Intel NPU mediante OpenVINO GenAI con fallback NPU/GPU/CPU.
**Estado LEONES:** 🟡 P2/P3.

## Resumen
Amplía la visión de ODS más allá de CUDA. Proporciona una API OpenAI-compatible y una ruta de inferencia para Intel NPU, con modelos cuantizados y fallback entre dispositivos.

## Encaje ODS
Debe modelarse como runtime/acelerador alternativo:
`NPU → GPU → CPU`.
Esto encaja directamente con un selector basado en capabilities.

## Hardware
No aporta ventaja al RTX 3050 actual, pero es relevante para futuros equipos Intel con NPU.

## LEONES
Registrar dispositivo, backend OpenVINO, modelo, precisión, memoria y métricas por dispositivo.

## Veredicto
**Clasificación:** P2/P3 — expansión futura de hardware.
**Fuente:** https://github.com/Jaroslav-Loskot/local-llm-npu