# Noodle — ODS integration observation

**Status:** Experimental observation  
**Date:** 2026-10-01  
**Upstream:** https://github.com/pdparchitect/noodle  
**License:** Apache-2.0

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
- Noodle Browser, providing persistent signed-in browser profiles for agents; current release is also macOS-oriented.
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

Noodle is Apache-2.0. An ODS integration can be studied as an optional external component, while preserving Noodle's licensing and attribution requirements. Dependencies and separately distributed components must be audited independently.

## Conclusion

**Experimental observation: Noodle is a strong candidate for investigation as an agent/workspace orchestration layer around ODS, especially for persistent multi-agent observation workflows. It should not currently be added as a mandatory Ubuntu ODS component because the upstream application is macOS-oriented.**

This document records an observation only; it does not claim a tested ODS/Noodle integration.
