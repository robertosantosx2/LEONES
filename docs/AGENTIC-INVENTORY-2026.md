# Inventario serio de agentes, harnesses y frameworks agentivos — LEONES

**Fecha de revisión:** 2026-08-16  
**Estado:** 🟡 inventario inicial consolidado; seguimiento continuo requerido.

## 1. Criterio

LEONES no debe mezclar tres cosas:

1. **Agente/producto:** sistema que ejecuta un bucle de decisión y herramientas.
2. **Harness/engine:** runtime que proporciona herramientas, sandbox, contexto, memoria, permisos y ciclo de ejecución.
3. **Framework/orquestador:** biblioteca para construir y coordinar agentes.

Además se mantiene una cuarta categoría: **benchmarks/evaluación**, porque un agente sin medición comparable no puede entrar en el recomendador como evidencia agentiva.

## 2. Prioridad para LEONES

### P0 — conocer y seguir de forma recurrente

| Sistema | Tipo | Por qué importa |
|---|---|---|
| OpenHands | agente + SDK/harness | Agente de desarrollo abierto, ejecución local/sandbox y SDK componible. Especialmente relevante para modelos locales. |
| mini-SWE-agent / SWE-agent | agente/harness de software engineering | Excelente referencia de agente simple y evaluable; el proyecto recomienda actualmente mini-SWE-agent sobre SWE-agent. |
| Goose | agente general open source | Local, CLI/desktop/API, multi-provider, MCP y tareas más allá de coding. Muy relevante para Debian/local. |
| Codex CLI | coding agent | Referencia de agente terminal con herramientas, sandbox, subagentes y workflow de desarrollo. |
| Claude Code | coding agent | Referencia de harness comercial de coding y de patrones de herramientas/subagentes/skills. |
| Gemini CLI | coding agent | Referencia de Google y tercer vértice del grupo de coding agents terminales. |
| LangGraph | framework/orquestador | Control explícito de estado, grafos y workflows complejos; referencia para agentes durables. |
| OpenAI Agents SDK | framework | Handoffs, tools, guardrails y tracing; referencia de arquitectura multiagente. |
| PydanticAI | framework | Tipado, validación y construcción de agentes Python con fuerte control de contratos. |
| CrewAI | framework | Patrón multiagente por roles; importante como referencia de coordinación. |
| smolagents | framework | Muy relevante para LEONES por simplicidad, code agents y compatibilidad con modelos locales. |

### P1 — seguimiento importante

| Sistema | Tipo | Uso en LEONES |
|---|---|---|
| Aider | coding agent | Referencia ligera de coding local/terminal. |
| OpenCode | coding agent | Alternativa abierta/portable de terminal. |
| Qwen Code | coding agent | Especial interés por stack abierto/modelos locales. |
| Cline | coding/IDE agent | Referencia de agente con herramientas dentro del IDE. |
| Roo Code | coding/IDE agent | Variante importante del ecosistema VS Code/open coding agents. |
| Continue | coding/IDE framework | Integración de modelos locales y herramientas en IDE. |
| Goose/ACP ecosystem | protocolo/agents | Interoperabilidad entre agentes y harnesses. |
| Letta | agent framework/runtime | Memoria persistente como parte central del agente. |
| LlamaIndex | agent/RAG framework | Agentes orientados a datos, documentos y RAG. |
| Haystack | pipeline/agent framework | Pipelines RAG y agentes documentales. |
| Semantic Kernel / Microsoft Agent Framework | framework | Referencia Microsoft para orquestación y agentes enterprise. |
| Strands Agents | framework | Alternativa importante de orquestación/tool use. |
| Agno | framework | Framework ligero de agentes y equipos. |

### P2 — mantener catalogados, no priorizar integración

- AutoGen / AG2: importante históricamente y para comparación multiagente; comprobar siempre estado de mantenimiento y sucesor antes de recomendarlo.
- Atomic Agents: referencia ligera/open-source.
- AgentSwarm y proyectos de swarm/multiagente: observar como categoría, no como dependencia de LEONES.
- Cursor Agent, Windsurf y T3 Code: relevantes como productos de coding agent, especialmente para comparación de capacidades, aunque no sean el foco local-first.
- Zed Agent: referencia de agente integrado en editor.
- Antigravity CLI: seguir su evolución como sucesor/cambio del ecosistema Gemini CLI en determinados escenarios.

## 3. Familias que LEONES debe distinguir

### A. Coding agents

Claude Code, Codex CLI, Gemini CLI, OpenHands, mini-SWE-agent, SWE-agent, Aider, OpenCode, Goose, Qwen Code, Cline, Roo Code, Continue, Cursor Agent, Zed Agent.

### B. Agentes generales/local-first

Goose, OpenHands, smolagents, Letta, Agno.

### C. Orquestación multiagente

LangGraph, OpenAI Agents SDK, PydanticAI, CrewAI, Semantic Kernel/Microsoft Agent Framework, Strands, AutoGen/AG2.

### D. Datos/RAG

LlamaIndex, Haystack, LangGraph y los agentes construidos sobre estas capas.

### E. Evaluación / software-engineering benchmarks

SWE-bench, SWE-ReX, mini-SWE-agent y harnesses de ejecución reproducible deben tratarse como infraestructura de medición, no como agentes equivalentes.

## 4. Qué debe medir LEONES

Para comparar agentes no basta con preguntar si "pueden usar herramientas". El inventario debe registrar al menos:

- modelo(s) admitidos;
- modelo local / cloud;
- tool calling;
- ejecución de código;
- shell;
- filesystem;
- browser/web;
- MCP;
- ACP u otros protocolos;
- subagentes;
- memoria persistente;
- gestión de contexto;
- sandbox/isolation;
- permisos y human-in-the-loop;
- recuperación ante errores;
- checkpointing/durabilidad;
- observabilidad/tracing;
- coste;
- reproducibilidad;
- licencia del software;
- portabilidad Linux/Debian;
- dependencia de proveedor;
- rendimiento con modelos pequeños/locales.

## 5. Regla especial para LEONES

La palabra **"agentic" no se concede por marketing**. Para considerar una capacidad como evidencia agentiva verificable debe distinguirse:

```text
LLM responde
   ≠
LLM decide usar una herramienta
   ≠
harness ejecuta la herramienta
   ≠
agente observa el resultado
   ≠
agente recupera un error
   ≠
agente completa una tarea multi-step
```

Esto amplía el smoke test B01–B05 de LEONES sin sustituirlo.

## 6. Estado actual de LEONES

El proyecto ya tenía identificados **Buddy, Hermes y LangGraph** como referencias para evaluación agentiva. Este inventario los conserva, pero amplía el mapa para evitar que la investigación quede limitada a esos tres nombres.

El smoke test propio B01–B05 continúa siendo una prueba de cribado, no una certificación agentiva completa.

## 7. Fuentes y verificación

La revisión web de 2026-08-16 confirma, entre otras fuentes, que OpenHands dispone de SDK y CLI para agentes de desarrollo; SWE-agent recomienda actualmente mini-SWE-agent como sucesor simplificado; Goose es un agente open source local con CLI/desktop/API, múltiples proveedores y extensiones MCP; y smolagents soporta CodeAgent, ToolCallingAgent y múltiples proveedores/modelos. 

Fuentes principales:

- OpenHands: https://github.com/All-Hands-AI/OpenHands
- OpenHands SDK: https://github.com/OpenHands/software-agent-sdk
- SWE-agent: https://github.com/SWE-agent/SWE-agent
- mini-SWE-agent: https://github.com/SWE-agent/mini-swe-agent
- Goose: https://github.com/aaif-goose/goose
- smolagents: https://huggingface.co/blog/smolagents
- Comparativa de agentes terminales: https://corcolabs.com/blog/cli-coding-agents-in-2026-what-actually-works
- Comparativa de primitivas Codex/Claude/Gemini: https://codex.danielvaughan.com/2026/03/26/agentic-primitives-compared-codex-claude-gemini/

## 8. Siguiente trabajo

No se integra todavía ningún agente por aparecer en esta lista. Primero se mantiene el inventario, después se recopila evidencia primaria, luego se ejecutan pruebas comparables y finalmente se decide qué entra en el recomendador.

**Regla global:** todo workflow futuro que escriba artefactos canónicos respeta la no concurrencia de LEONES (`leones-main-writers`, `cancel-in-progress: false`).
