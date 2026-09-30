# oBeaver ↔ ODS ↔ LEONES
**Perfil:** toolkit de inferencia LLM local-first, OpenAI-compatible y consciente de plataforma.
**Estado LEONES:** 🟡 P2.

## Resumen
oBeaver es interesante por su enfoque platform-aware y por ofrecer una superficie local de inferencia homogénea. Su valor para ODS está en estudiar cómo abstrae engine, plataforma y API.

## Encaje
Debe evaluarse como referencia para capability manifests y fallback entre engines. No existe motivo para duplicar su toolkit dentro de ODS sin una ventaja concreta.

## LEONES
Registrar qué hardware/runtime combinations detecta, qué engines selecciona y cómo expresa incompatibilidades.

## Veredicto
| Arquitectura | 🟢 |
| Serving | 🟢 |
| MoE paging | 🟡 |
| Integración directa | 🟡/🔴 |
**Clasificación:** P2 — radar arquitectónico.
**Fuente:** https://github.com/microsoft/obeaver