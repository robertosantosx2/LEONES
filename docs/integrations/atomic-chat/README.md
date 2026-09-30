# Atomic-Chat ↔ ODS ↔ LEONES
**Perfil:** aplicación local que unifica varios engines de inferencia bajo API OpenAI-compatible.
**Estado LEONES:** 🟡 P2.

## Resumen
Atomic-Chat combina llama.cpp upstream, una variante TurboQuant y MLX-VLM, y añade speculative decoding. Es útil como ejemplo de cómo encapsular varios engines sin obligar a las aplicaciones consumidoras a conocerlos.

## ODS
Interesa como referencia de Runtime Registry y de separación entre engine y API. No parece necesario añadir la aplicación completa a ODS.

## LEONES
Registrar engine, capacidades multimodales, speculative decoding y requisitos de hardware.

## Veredicto
**Clasificación:** P2 — referencia de multi-engine.
**Fuente:** https://github.com/atomicbot-ai/atomic-chat