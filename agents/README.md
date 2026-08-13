# 🦁 LEONES · Agents

Agents en LEONES son una capa de ejecución sobre Runtime + herramientas + Task Intelligence.

## Contrato v0.1

Entrada: tarea normalizada por `scripts/leones-task.py` y una capacidad de herramientas disponible localmente.

Salida mínima:
- `status`: completed | failed | blocked | manual_review
- `steps`: pasos ejecutados
- `artifacts`: artefactos producidos, sin rutas privadas
- `evidence`: referencia al resultado de Evaluación o revisión manual

Un agente no puede declarar una capacidad por sí mismo: debe quedar respaldada por una ejecución reproducible.

## Próximo backend
El primer agente operativo debe reutilizar Evaluación y herramientas locales antes de añadir planificación compleja.
