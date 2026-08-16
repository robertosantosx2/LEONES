# Source Discovery — descubrimiento automático de fuentes

LEONES necesita descubrir continuamente nuevas fuentes de conocimiento y medición sin modificar el código cada vez que aparece un sitio, repositorio, dataset, benchmark, runtime, skill o proyecto relevante.

## Arquitectura

```text
FUENTES CONOCIDAS
      ↓
DESCUBRIMIENTO
      ↓
CANDIDATOS
      ↓
VALIDACIÓN
      ↓
APROBACIÓN / RECHAZO
      ↓
ADAPTADOR
      ↓
CONOCIMIENTO / MEDICIONES
      ↓
EVIDENCIA + QUALITY GATE
      ↓
ATLAS / MANADA / RECOMENDADOR
```

## Qué descubre

- repositorios de modelos y código;
- proyectos y documentación técnica;
- benchmarks y leaderboards;
- hardware, drivers y runtimes;
- skills, herramientas, agentes y harnesses;
- datasets y publicaciones;
- APIs y servicios;
- RSS/Atom y páginas de novedades.

## Semillas iniciales

El diseño admite adaptadores para GitHub, Hugging Face, arXiv, Semantic Scholar, PyPI, npm, RSS/Atom y webs oficiales/documentación enlazada.

Una fuente descubierta no se considera fiable automáticamente.

## Registro

Cada candidato conserva como mínimo:

```text
source_id, name, url, source_type, discovery_method,
discovered_at, last_checked_at, status, relevance, trust,
license, notes
```

Estados:

```text
candidate → validated → approved → active
                         ↘ rejected
```

## Regla fundamental

Descubrimiento, extracción, verificación y publicación son etapas distintas. Una fuente nueva nunca publica directamente en el Atlas: genera candidatos o datos de staging y atraviesa los gates existentes.

El pipeline existente `daily_atlas_ingest.py` ya aplica esta filosofía: normaliza, deduplica, aplica el gate de licencia y separa candidatos de revisión; no promociona un descubrimiento no verificado directamente al Atlas. fileciteturn243file0L2-L2

## Licencias

En software se mantiene la distinción entre `open weights` y licencia de software compatible con OSI. Una fuente sin licencia suficiente permanece en revisión.

## Aprendizaje continuo

Cada ejecución puede consultar fuentes activas, encontrar enlaces nuevos, normalizar URLs, deduplicar por URL/huella, puntuar relevancia y confianza y añadir nuevos candidatos. Las fuentes rechazadas conservan el motivo para no redescubrirlas continuamente.

## CI

Todo workflow nuevo que escriba en `main` debe cumplir la regla global de no concurrencia de `docs/CI-WORKFLOW-RULES.md`.

## Resultado

Las fuentes actuales se convierten en semillas de una red creciente de fuentes candidatas, pero la activación siempre queda detrás de validación y evidencia.
