# LocalAI ↔ ODS ↔ LEONES
**Perfil:** motor/orquestador local multi-backend con API OpenAI-compatible.
**Estado LEONES:** 🟢 P1 arquitectónico · ⏳ integración ODS directa no necesaria inicialmente.

## Resumen
LocalAI es relevante menos por una técnica concreta de MoE y más por su arquitectura: reúne múltiples runtimes bajo una API común, soporta aceleradores diversos y puede instalar backends de forma separada. Incluye llama.cpp, vLLM, SGLang, Transformers y otros.

## Encaje ODS
ODS ya tiene una capa de servicios y LiteLLM; por ello no sería razonable introducir LocalAI simplemente como otro frontend. Su valor está en estudiar su modelo de **backend registry + capability detection + instalación de engines**.

## Arquitectura propuesta
`ODS model profile → runtime registry → capability match → backend → OpenAI endpoint`.

## Aprovechable
- catálogo de backends;
- instalación aislada;
- selección por hardware;
- API homogénea;
- separación de modelos y engines.

## Riesgo
Duplicar funciones existentes de ODS. Debe tratarse como referencia arquitectónica, no como dependencia obligatoria.

## LEONES
Comparar el manifiesto de capacidades de LocalAI con el que ya necesita ODS y reutilizar ideas sin mezclar métricas de ambos sistemas.

## Veredicto
| Área | Evaluación |
|---|---|
| Multi-backend | 🟢 Muy alta |
| OpenAI API | 🟢 |
| MoE específico | 🟡 Indirecto |
| Reutilización arquitectónica | 🟢 |
| Integración como servicio | 🟡/🔴 |
**Clasificación:** P1 como referencia de arquitectura; no como sustituto de ODS.
**Fuente:** https://github.com/mudler/LocalAI