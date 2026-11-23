# LEONES — Agent Use Case Observatory

**Estado:** implementación inicial en revisión.  
**Publicación:** [catálogo Markdown](../../../web/agent-use-cases.md) · [índice de observatorios](../../../web/observatory.md).  
**Automatización:** `.github/workflows/daily-prospection.yml` (workflow diario existente).

## Propósito

Mantener un catálogo vivo de **casos concretos de uso de agentes**, repositorios, skills, prompts, servidores MCP, ejemplos y workflows que puedan inspeccionarse y reproducirse. El Observatory amplía la prospección de LEONES; no crea un pipeline paralelo.

## Integración con LEONES

- Reutiliza el catálogo existente de `data/discovery/skills.json` y `data/observatory/prospeccion.json`. También incorpora hallazgos federados de `data/prospection/federated_discoveries.ndjson`.
- Añade descubrimiento diario mediante GitHub Repository Search API.
- El proceso se ejecuta como un paso del workflow `Daily Atlas Prospection`, programado a las 04:17 UTC y ejecutable manualmente.
- Mantiene el histórico normalizado en `data/prospection/agent_use_cases.ndjson`.
- Genera datos internos en `data/observatory/agent-use-cases.json`; el publicador común produce `web/agent-use-cases.md`.
- Publica los artefactos mediante el mecanismo de commit existente de la prospección diaria.

## Consultas iniciales

La primera versión cubre seis familias:

1. Frameworks y agentes (`topic:ai-agents`).
2. Agent Skills.
3. Ejemplos de agentes.
4. Workflows agentic.
5. Herramientas y servidores MCP.
6. Prompts y recetas de agentes.

Cada consulta usa GitHub Search con repositorios no archivados y no forks, y ordena por actualización. Los límites de estrellas reducen ruido, pero no constituyen una evaluación de calidad.

## Evidencia y reproducibilidad

Para cada repositorio encontrado se intenta consultar el README mediante la API de GitHub y se conservan:

- URL del repositorio y README, rama por defecto, descripción, topics y lenguaje.
- Stars, forks, fecha de último push y licencia/SPDX declarada por GitHub.
- Presencia/tamaño del README.
- Señales textuales de instrucciones de instalación/ejecución y de ejemplos/prompts.
- Puntuación heurística transparente y sus evidencias.

La puntuación es una **señal de triaje**, no una prueba de ejecución. Un README que menciona Docker o una instalación no demuestra que funcione. Los candidatos heredados del catálogo anterior se muestran como `unassessed` hasta que el nuevo proceso los enriquezca.

## Estados y límites

- `discovered`: hallazgo automático.
- `pending`: pendiente de revisión humana.
- `verified`: reservado para una comprobación explícita y documentada; la automatización inicial no asigna este estado.
- `rejected`: candidato descartado tras revisión.

**No se aprueba, recomienda, ejecuta, instala ni integra automáticamente ningún repositorio.** La licencia de GitHub es metadato declarado, no auditoría legal ni confirmación de compatibilidad de todas las dependencias. El estado de licencia desconocida permanece visible como no validado.

## Ejecución y validación

Desde la raíz del repositorio:

```bash
GITHUB_TOKEN=... python3 scripts/prospection/agent_use_case_observatory.py
python3 -m json.tool data/observatory/agent-use-cases.json >/dev/null\npython3 scripts/prospection/build_markdown_observatories.py
python3 - <<'PY'
import json
from pathlib import Path
p = json.loads(Path("data/observatory/agent-use-cases.json").read_text())
assert p["publication_is_not_approval"] is True
assert p["automatic_recommendation"] is False
assert isinstance(p["items"], list)
print("items:", len(p["items"]))
PY
```

La publicación resultante se consulta en `web/agent-use-cases.md`; el JSON interno no es un endpoint público del observatorio. La ejecución local necesita acceso a GitHub. GitHub Actions usa el token efímero `github.token`; no requiere un secreto personal. Si una consulta falla, el informe conserva el error y las demás consultas continúan.

## Próximas gates

1. **G1 — Integración remota:** script, feed inicial, interfaz y README enlazados; workflow incorpora el paso diario.
2. **G2 — CI:** ejecutar manualmente el workflow y verificar que se actualizan NDJSON/JSON y que el artefacto de Actions se conserva.
3. **G3 — Calidad del catálogo:** revisar falsos positivos, cobertura de prompts/skills y deduplicación; ajustar consultas con evidencia.
4. **G4 — Reproducibilidad:** seleccionar candidatos y probarlos en entornos aislados, registrando comandos, versiones, resultados, licencias y límites.
5. **G5 — Curación:** promoción manual de los candidatos revisados; nunca inferir aceptación a partir de stars o puntuaciones heurísticas.

La aceptación de la automatización requiere una ejecución real del workflow y revisión del feed generado; la creación de los archivos por sí sola no acredita esa ejecución.
