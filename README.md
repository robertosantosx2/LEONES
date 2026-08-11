# LEONES — Local Ecosystem of Open Neural Expert Systems

> **IA agéntica Libre/Open para hardware de consumo.**

[🌐 **Web de LEONES y dashboard metaLEONES**](https://robertosantosx2.github.io/LEONES/)

LEONES investiga y construye un ecosistema agentic que pueda ejecutarse en hardware real de consumo, con especial prioridad a software Libre/Open y, dentro de él, Copyleft.

## Objetivo

No buscamos simplemente el agente más potente en un servidor. La pregunta central es:

> **¿Qué ecosistema de software Libre/Open, especialmente Copyleft, permite convertir hardware de consumo en una máquina agentic realmente útil?**

Perfiles objetivo: **8, 16, 32 y 64 GB de RAM**, con CPU Intel i5/i7 o equivalentes, con o sin GPU.

## Principios fijados

- **Libre** se usa deliberadamente frente a «free»: interesa la libertad del software, no su precio.
- Se descarta lo que no sea Open y se prioriza especialmente **Copyleft**.
- **Buddy (GPL-3.0)** es una pieza central de la pila candidata.
- La primera pila de referencia incluye Buddy, Hermes, LangGraph, llama.cpp y GGUF.
- **10 tok/s** es el umbral mínimo de usabilidad LEONES.
- **100 tok/s** es el techo de comparación, no un requisito universal.
- Medimos **tareas agentic**, no solo tokens por segundo.
- Los resultados oficiales deben ser mediciones propias y reproducibles.
- **metaLEONES** permite aportar resultados de hardware real mediante Markdown sin datos personales.

## LOTB

LOTB separa dos niveles:

1. **Inferencia:** modelo + backend + hardware.
2. **Agentic:** agente + herramientas + tareas.

Tareas iniciales:

- B01 — memoria/localidad
- B02 — operación sobre archivos
- B03 — tarea multietapa
- B04 — recuperación ante fallo
- B05 — coding local

Baseline inicial: **Qwen3-8B Q4_K_M GGUF**.

## metaLEONES

La comunidad puede aportar resultados técnicos al repositorio. No se publican nombres, emails, usuarios, hostnames identificables, números de serie, UUID, MAC/IP, ubicación exacta, rutas personales, credenciales ni otros datos personales.

Los resultados se clasifican como `reported`, `reproducible`, `verified` o `rejected`.

## Documento fundamental

**[Historia, decisiones y fundamentos del proyecto](LEONES_DECISION_LOG.md)** contiene el contexto completo que llevó a estas decisiones y debe ser la primera lectura para entender LEONES.

## Estado

Proyecto experimental en desarrollo. La arquitectura inicial está congelada como referencia, pero la optimización del ecosistema LEONES y de sus métricas sigue abierta a la evidencia.
