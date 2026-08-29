# JALÓN 12 — Notas del operador

Este documento acompaña a `docs/jalones/jalon12.md` y está escrito para el mantenimiento diario.

## Qué se ha construido

La primera puerta de usuario es `scripts/run_leones_v1.sh`. Su única responsabilidad es llevar al usuario hasta `scripts/leones_v1.py preflight --pretty`.

El programa Python observa el entorno y devuelve JSON. No ejecuta un benchmark y no inventa una recomendación.

## Qué no debe hacerse aquí

No añadir en esta capa:

- otro cálculo de tokens por segundo;
- otro ranking;
- otra selección de modelos;
- otra fuente de verdad para hardware;
- una copia de la lógica de decisión;
- una simulación presentada como medición.

Si una capacidad ya existe en un contrato anterior, esta puerta debe referenciarla y no duplicarla.

## Mantenimiento sencillo

Si cambia un contrato canónico, comprobar que `CONTRACTS` de `leones_v1.py` sigue apuntando al archivo correcto.

Si cambia la forma del preflight, modificar primero `schemas/leones-v1-preflight.v1.json` y después las pruebas. El JSON emitido debe seguir siendo compatible con ese contrato.

Si cambia la experiencia del usuario, actualizar también `docs/V1-USER-GUIDE.md`.

## Regla -strict-

Una modificación sólo está terminada cuando queda:

1. limpia — sin duplicación ni código muerto;
2. fijada — con contrato y/o prueba;
3. espléndida — explicada en comentarios comprensibles y documentación Markdown;
4. auditada — con un resultado reproducible.

La claridad para un lector poco familiarizado con programación es un requisito de mantenimiento, no un adorno.
