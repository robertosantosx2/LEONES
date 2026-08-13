# Estadísticas de la Manada

` scripts/leones-manada-stats.py` analiza los informes Markdown publicados voluntariamente en `results/manada/` y genera estadísticas y gráficas.

## Uso

```bash
python3 scripts/leones-manada-stats.py
```

Para otra ubicación:

```bash
python3 scripts/leones-manada-stats.py --input results/manada --output results/manada/stats
```

## Qué permite observar

- perfiles de hardware;
- sistemas operativos;
- RAM y CPU;
- tok/s de inferencia;
- resultados de Evaluación B01–B05;
- señales agregadas útiles para el Router.

Los datos deben proceder de informes realmente disponibles. No se inventan cifras.
