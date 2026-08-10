# metaLOAS — Resultados de la comunidad

Este directorio almacena los informes Markdown generados por las máquinas que participan en metaLOAS.

## Cómo aportar

Desde una copia local de LOAS:

```bash
python3 scripts/metaloas-report.py --model ~/models/loas/Qwen3-8B-Q4_K_M.gguf --publish
```

El script crea un fichero con marca temporal dentro de `results/metaLOAS/` y lo publica en el repositorio usando la sesión autenticada de GitHub CLI (`gh`).

Primero:

```bash
gh auth login
```

## Privacidad

El informe está diseñado para no recoger deliberadamente:

- nombre de usuario;
- hostname;
- MAC/IP;
- número de serie;
- UUID;
- ubicación;
- rutas personales;
- credenciales o tokens.

**Revisar siempre el Markdown antes de publicarlo.**

## Estructura

Cada máquina/ejecución genera un Markdown independiente:

```text
results/metaLOAS/
├── README.md
├── 20260810-231500-H1.md
├── 20260811-091200-H2.md
└── ...
```

Los resultados LOTB B01–B05 pueden completarse en el propio informe antes de publicarlo.
