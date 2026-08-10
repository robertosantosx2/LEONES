# Web pública de resultados metaLOAS

LOAS debe disponer de una web pública que presente de forma legible los resultados agregados de metaLOAS.

## Objetivo

Convertir los informes Markdown de `results/metaLOAS/` en una vista útil para comparar hardware de consumo y pilas agentivas.

La web no debe exponer datos personales ni identificadores de máquinas.

## Contenido mínimo

- número total de informes;
- distribución H0/H1/H2/H3;
- CPU y RAM;
- GPU/VRAM cuando exista;
- sistemas operativos;
- modelos y cuantizaciones;
- backend/harness;
- tok/s;
- porcentaje que alcanza 10 tok/s;
- referencia de 100 tok/s;
- resultados LOTB B01–B05;
- tiempos por tarea cuando estén disponibles;
- evolución temporal;
- comparativas por perfil de hardware;
- recomendaciones derivadas de la evidencia.

## Principio

La web debe mostrar **resultados observados**, diferenciándolos claramente de estimaciones o recomendaciones.

Debe permitir filtrar por:

- perfil de RAM;
- CPU;
- GPU;
- sistema operativo;
- modelo;
- cuantización;
- backend;
- harness;
- tarea LOTB.

## Arquitectura inicial

```text
results/metaLOAS/*.md
          ↓
   metaloas-stats.py
          ↓
   dataset agregado
          ↓
       web LOAS
          ↓
 comparativas / gráficas
```

La primera implementación debe poder funcionar como sitio estático y publicarse mediante GitHub Pages, evitando una infraestructura de servidor innecesaria.
