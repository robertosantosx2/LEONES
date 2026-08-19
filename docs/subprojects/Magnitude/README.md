# Subproyecto Magnitude

## Objetivo

Integrar Magnitude como **runtime/agente local de referencia** para tareas de coding y evaluación agentiva.

Magnitude se presenta como agente de coding open source con motor de inferencia local propio sobre llama.cpp; perfila el hardware, recomienda modelos, calcula requisitos de memoria y ajusta aceleración, placement y batching. citeturn0search1turn0search3

## Papel dentro de LEONES

```text
Atlas → recomendación de modelo/hardware
                 ↓
          Magnitude adapter
                 ↓
       runtime + coding agent
                 ↓
       Agentic Benchmark V1
                 ↓
       result.schema.json
```

Magnitude es especialmente interesante para LEONES porque su dominio coincide directamente con A07 (coding) y con la medición de herramientas, latencia y sesiones largas.

## Qué debe capturar LEONES

- versión del CLI;
- versión/revisión del motor;
- modelo y cuantización;
- configuración de contexto;
- hardware detectado;
- aceleración/placement;
- batching;
- prefill/cache cuando sea observable;
- llamadas a herramientas;
- duración;
- tokens cuando estén disponibles;
- errores y recuperaciones.

No se deben convertir las capacidades declaradas por Magnitude en resultados benchmark.

## Instalación de referencia

El proyecto documenta:

```text
npm install -g @magnitudedev/cli
cd <proyecto>
magnitude
```

y soporta macOS/Linux, con Windows mediante WSL. citeturn0search1turn0search3

Para LEONES, la instalación de benchmark debe fijar versión y conservar el manifiesto del entorno.

## Integración con Agentic Benchmark

Primera prioridad:

- A07 — coding;
- A02 — tareas multietapa;
- A03 — artefactos;
- A04 — recuperación;
- A05 — long horizon.

La traza de Magnitude debe adaptarse al evento canónico LEONES, sin crear un segundo formato.

## Comparación con ODS

| Función | ODS | Magnitude |
|---|---|---|
| Instalador/stack | principal | secundaria |
| Runtime local | sí | sí |
| Agentes | sí | sí |
| Coding agent | parcial/servicios | central |
| Hardware profiling | sí | central |
| Model setup | sí | central |
| Benchmark agentivo | integración | objetivo directo |
| Papel LEONES | despliegue | ejecución/medición |

## Estado

🟡 Diseño de integración. La siguiente fase es construir el adapter y ejecutar A07/A02/A03 en un entorno controlado.
