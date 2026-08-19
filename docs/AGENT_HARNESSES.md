# Harnesses de referencia de LEONES

LEONES adopta tres harnesses de referencia para evaluación agentiva:

| Harness | Rol | Integración principal |
|---|---|---|
| **DeepSeek Harness (DSH)** | runtime agéntico componible por plugins/eventos | ODS + benchmark LEONES |
| **Buddy** | asistente personal con memoria Git/Markdown y herramientas file-first | ODS + Magnitude + benchmark LEONES |
| **Hermes** | agente/harness integrado en el ecosistema ODS | ODS + benchmark LEONES |

## Objetivo

Los tres deben poder ejecutar una batería común de tareas y exportar trazas al contrato LEONES. No se busca hacerlos funcionalmente idénticos: las diferencias de capacidades forman parte de la medición.

## Matriz experimental mínima

```text
misma tarea
+ mismo modelo
+ mismo hardware
+ mismo presupuesto
+ políticas declaradas
        ↓
DSH | Buddy | Hermes
        ↓
resultado + trayectoria + coste/tiempo + seguridad + artefactos
```

## Fuentes upstream

- DSH: https://github.com/deepseek-ai/deepseek-harness
- Buddy: https://github.com/juanje/buddy
- Hermes/ODS: https://github.com/Osmantic/ODS

## Buddy

Documentación del subproyecto: [`docs/subprojects/buddy/`](subprojects/buddy/).
