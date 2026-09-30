# llama-cpp-studio ↔ ODS ↔ LEONES
**Perfil:** control plane local para gestionar y servir múltiples engines con endpoint OpenAI-compatible.
**Estado LEONES:** 🟢 P1 arquitectónico.

## Resumen
llama-cpp-studio separa UI/control plane de runtimes. Gestiona llama.cpp, forks de llama.cpp, vLLM, SGLang, LMDeploy y otros mediante un endpoint unificado. Este patrón es muy próximo a lo que ODS necesita para convertir el catálogo de runtimes en una capacidad seleccionable.

## Encaje ODS
No hace falta instalarlo en ODS. Conviene estudiar:
- lifecycle de procesos;
- configuración declarativa;
- selección de engine;
- endpoint unificado;
- gestión de modelos.

## Integración LEONES
Añadir estas ideas al Runtime Registry: `runtime_id`, versión, capabilities, model constraints, launch command, health endpoint, API endpoint y shutdown semantics.

## Riesgos
El control plane puede solaparse con componentes de ODS. La utilidad es conceptual.

## Veredicto
**Clasificación:** P1 — referencia para la capa Runtime Selector/Control Plane.
**Fuente:** https://github.com/lapy/llama-cpp-studio