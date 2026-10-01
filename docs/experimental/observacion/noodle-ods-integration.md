# Noodle — ODS integration observation / Observación de integración ODS

**Status / Estado:** Experimental observation / Observación experimental  
**Date / Fecha:** 2026-10-01  
**Upstream:** https://github.com/pdparchitect/noodle  
**License / Licencia:** Apache-2.0

---

# English

## Purpose

Evaluate Noodle as an optional **agent workspace / multi-agent layer** for ODS, rather than as an inference engine.

## Functional findings

Noodle provides:

- Persistent agents with their own workspace, backstory and conversation history.
- Groups/teams of agents working toward a shared goal.
- A harness abstraction supporting Codex, Claude Code, FX, Grok Build, Muse Code, OpenCode v2, Antigravity and experimental Apple Intelligence.
- Per-agent model/reasoning selection where the harness supports it.
- MCP and other tool integrations.
- Per-agent access controls, restricted workspaces and explicitly shared folders.
- Persistent computers and browsers that can be assigned to agents.
- Heartbeats for periodic follow-up on existing work.
- Native chat, attachments, voice/screen features and OS integration on macOS.
- Local/on-device model support, currently oriented primarily around Apple/MLX environments.
- Noodle Computer, providing Linux virtual computers for agents, although the current Computer application requires an Apple-silicon Mac running macOS 26+.
- Noodle Browser, providing persistent signed-in browser profiles for agents; the current release is also macOS-oriented.
- Noodle Hub for sharing harnesses and running bots for other users from an always-on Mac.

## ODS relationship

Noodle should **not** be treated as a replacement for ODS inference backends such as llama-server or LiteLLM.

A possible architecture is:

    ODS
     |
     +-- inference backends
     |    +-- llama-server
     |    +-- LiteLLM / remote providers
     |
     +-- services
     |    +-- Qdrant
     |    +-- SearXNG
     |    +-- n8n
     |    +-- Whisper / TTS
     |
     +-- agent layer
          +-- Noodle (experimental)
               +-- agents
               +-- teams
               +-- harnesses
               +-- MCP tools
               +-- workspaces

The strongest integration concept is therefore **agent orchestration above the ODS model/service layer**.

## LEONES observation / surveillance relevance

Noodle is relevant to the LEONES **observación** area because persistent agents, assigned tools, browsers/computers and heartbeats can support continuous observation workflows.

However, observation must remain distinct from autonomous action:

    observation
        -> collection
        -> analysis
        -> human decision
        -> authorized action

Noodle's heartbeat mechanism is useful for checking existing work, but it is not a general-purpose scheduler and does not by itself authorize new work.

## Linux / Ubuntu limitation

For the current ODS target on Ubuntu/Linux, the main Noodle application and companion applications are currently documented as macOS applications. Noodle Computer can run Linux guest environments but its current application requires Apple silicon + macOS 26+.

Therefore this is currently an **architectural integration study**, not a recommendation to add Noodle directly to the Ubuntu ODS installer.

The investigation should be revisited if Noodle exposes a Linux-native runtime or a separable headless agent/orchestration component.

## Integration candidates

| Noodle capability | ODS relevance |
| --- | --- |
| Multi-agent orchestration | High |
| Persistent agents | High |
| Harness abstraction | High |
| MCP tools | High |
| Agent workspaces | High |
| Heartbeats / observation | High for experimental observation |
| Teams | High |
| Browser automation | Interesting, but current platform limitation |
| Linux Computer | Interesting, but current host-app limitation |
| Local models | Partial overlap; different runtime assumptions |
| Hub / remote sharing | Secondary |

## License note

Noodle is Apache-2.0. An ODS integration can be studied as an optional external component while preserving Noodle's licensing and attribution requirements. Dependencies and separately distributed components must be audited independently.

## Conclusion

**Experimental observation: Noodle is a candidate for investigation as an agent/workspace orchestration layer around ODS, especially for persistent multi-agent observation workflows. It should not currently be added as a mandatory Ubuntu ODS component because the upstream application is macOS-oriented.**

This document records an observation only; it does not claim a tested ODS/Noodle integration.

---

# Español

## Objetivo

Evaluar Noodle como **capa opcional de workspace de agentes / multiagente** para ODS, y no como motor de inferencia.

## Hallazgos funcionales

Noodle proporciona:

- Agentes persistentes con su propio workspace, contexto e historial de conversación.
- Grupos/equipos de agentes que trabajan hacia un objetivo común.
- Una abstracción de harness compatible con Codex, Claude Code, FX, Grok Build, Muse Code, OpenCode v2, Antigravity y Apple Intelligence experimental.
- Selección de modelo/razonamiento por agente cuando el harness lo permite.
- Integraciones mediante MCP y otras herramientas.
- Controles de acceso por agente, workspaces restringidos y carpetas compartidas explícitamente.
- Ordenadores y navegadores persistentes que pueden asignarse a los agentes.
- Heartbeats para comprobaciones periódicas sobre trabajos existentes.
- Chat nativo, adjuntos, funciones de voz/pantalla e integración con el sistema operativo en macOS.
- Soporte de modelos locales/en dispositivo, actualmente orientado principalmente a entornos Apple/MLX.
- Noodle Computer, que proporciona ordenadores virtuales Linux para los agentes, aunque la aplicación actual requiere un Mac con Apple Silicon y macOS 26+.
- Noodle Browser, con perfiles de navegador persistentes y sesiones autenticadas; la versión actual también está orientada a macOS.
- Noodle Hub para compartir harnesses y ejecutar bots para otros usuarios desde un Mac siempre encendido.

## Relación con ODS

Noodle **no debería considerarse un sustituto** de los backends de inferencia de ODS, como llama-server o LiteLLM.

Una arquitectura posible sería:

    ODS
     |
     +-- backends de inferencia
     |    +-- llama-server
     |    +-- LiteLLM / proveedores remotos
     |
     +-- servicios
     |    +-- Qdrant
     |    +-- SearXNG
     |    +-- n8n
     |    +-- Whisper / TTS
     |
     +-- capa de agentes
          +-- Noodle (experimental)
               +-- agentes
               +-- equipos
               +-- harnesses
               +-- herramientas MCP
               +-- workspaces

Por tanto, el concepto de integración más claro es **orquestar agentes por encima de la capa de modelos y servicios de ODS**.

## Relevancia para observación / vigilancia en LEONES

Noodle es relevante para el área de **observación** de LEONES porque los agentes persistentes, las herramientas asignadas, los navegadores/ordenadores y los heartbeats pueden utilizarse para flujos de observación continuada.

No obstante, la observación debe mantenerse separada de la acción autónoma:

    observación
        -> recopilación
        -> análisis
        -> decisión humana
        -> acción autorizada

El mecanismo de heartbeat de Noodle resulta útil para comprobar trabajos existentes, pero no es un scheduler general y por sí mismo no autoriza trabajos nuevos.

## Limitación Linux / Ubuntu

Para el objetivo actual de ODS sobre Ubuntu/Linux, la aplicación principal de Noodle y sus aplicaciones complementarias están documentadas actualmente como aplicaciones para macOS. Noodle Computer puede ejecutar entornos Linux invitados, pero su aplicación actual requiere Apple Silicon + macOS 26+.

Por tanto, actualmente esto debe considerarse un **estudio de integración arquitectónica**, no una recomendación para añadir Noodle directamente al instalador de ODS para Ubuntu.

La investigación debería retomarse si Noodle proporciona un runtime nativo para Linux o un componente independiente headless de agentes/orquestación.

## Candidatos de integración

| Capacidad de Noodle | Relevancia para ODS |
| --- | --- |
| Orquestación multiagente | Alta |
| Agentes persistentes | Alta |
| Abstracción de harness | Alta |
| Herramientas MCP | Alta |
| Workspaces de agentes | Alta |
| Heartbeats / observación | Alta para observación experimental |
| Equipos | Alta |
| Automatización de navegador | Interesante, pero con limitación de plataforma |
| Linux Computer | Interesante, pero con limitación de la aplicación anfitriona |
| Modelos locales | Solapamiento parcial; distintos supuestos de runtime |
| Hub / compartición remota | Secundaria |

## Nota sobre la licencia

Noodle utiliza Apache-2.0. Una integración de ODS puede estudiarse como componente externo opcional respetando las obligaciones de licencia y atribución de Noodle. Las dependencias y los componentes distribuidos por separado deben auditarse individualmente.

## Conclusión

**Observación experimental: Noodle es un candidato para investigar como capa de orquestación de agentes/workspaces alrededor de ODS, especialmente para flujos persistentes de observación multiagente. Actualmente no debería añadirse como componente obligatorio del ODS para Ubuntu porque la aplicación upstream está orientada a macOS.**

Este documento registra una observación; no afirma que exista una integración ODS/Noodle probada.
