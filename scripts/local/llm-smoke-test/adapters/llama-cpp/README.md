# Adaptador llama.cpp

**Estado: especificación inicial; implementación pendiente.**

Este directorio define el contrato del adaptador para conectar `llm-smoke-test` con una instalación local de llama.cpp.

## Objetivo

Ejecutar una prueba local mediante el runtime llama.cpp y devolver las métricas al esquema común `RESULT_SCHEMA.md`.

## Requisitos previstos

- llama.cpp instalado por el usuario;
- un modelo compatible con el formato soportado por la versión instalada;
- parámetros explícitos de modelo, contexto y generación;
- sistema local compatible.

El adaptador no instalará llama.cpp ni descargará modelos silenciosamente.

## Aislamiento

El adaptador:

- no importa código de LEONES;
- no accede a Atlas;
- no accede a `agents/`;
- no requiere GitHub Actions;
- no necesita credenciales de LEONES;
- no envía resultados a servicios externos por defecto.

## Métricas

Debe intentar producir, cuando el runtime permita medirlas:

- carga/arranque separado de generación;
- TTFT;
- tiempo de generación;
- tokens de entrada;
- tokens generados;
- tokens/segundo;
- contexto utilizado;
- memoria/VRAM cuando exista una medición fiable.

Las métricas no disponibles deben ser `null`, nunca `0`.

## Implementación

Antes de convertir esta especificación en código ejecutable hay que validar la interfaz concreta de la versión de llama.cpp que vayamos a soportar y fijar los comandos/formatos de salida. La especificación no asume una CLI concreta para evitar acoplarla prematuramente a una versión.
