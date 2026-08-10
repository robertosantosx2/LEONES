# Estadísticas metaLOAS

`scripts/metaloas-stats.py` analiza los Markdown almacenados en `results/metaLOAS/` y genera un resumen estadístico y gráficas PNG.

## Uso

```bash
python3 scripts/metaloas-stats.py
```

Para otra ubicación:

```bash
python3 scripts/metaloas-stats.py --input results/metaLOAS --output results/metaLOAS/stats
```

Requiere matplotlib:

```bash
python3 -m pip install matplotlib
```

## Resultados

Se generan:

- `README.md` — resumen estadístico.
- `profiles.png` — distribución H0/H1/H2/H3.
- `os.png` — sistemas operativos reportados.
- `ram.png` — memoria RAM.
- `cpu.png` — CPUs.
- `lotb-pass.png` — PASS detectados en B01–B05.

El script analiza exclusivamente los informes publicados en el directorio de resultados y no necesita datos personales para funcionar.

## Evolución prevista

La primera versión es deliberadamente sencilla. En próximas versiones puede incorporar:

- tok/s de inferencia;
- latencia;
- tiempo por tarea;
- éxito de B01–B05;
- modelo y cuantización;
- backend;
- GPU/VRAM;
- comparación por perfil de hardware;
- evolución temporal;
- recomendaciones de mejora de pila.
