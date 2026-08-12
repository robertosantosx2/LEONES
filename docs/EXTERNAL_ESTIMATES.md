# External Estimates — NO VALIDADAS

Esta sección recopila información orientativa publicada por terceros sobre modelos locales, hardware, memoria, rendimiento, cuantización y otros aspectos de ejecución.

## Regla de transparencia

**`external-unvalidated` no es evidencia validada por LEONES.**

Los datos pueden ser útiles para investigación y planificación, pero no pasan automáticamente a Leones Atlas ni autorizan al Router a afirmar que un modelo es ejecutable.

Cada registro debe conservar:

- fecha de observación;
- modelo;
- hardware;
- cuantización;
- métrica;
- estimación reportada;
- URL y título de la fuente;
- tipo de fuente;
- tipo de evidencia;
- notas y contexto.

## Estados

- `external-unvalidated`: encontrado fuera de LEONES y no validado.
- `reviewed`: revisado por una persona, pero todavía no constituye medición propia.
- `validated`: solo cuando existe evidencia suficiente según las reglas de validación de LEONES.
- `rejected`: descartado por falta de calidad, contradicción o imposibilidad de verificarlo.

`reviewed` tampoco significa `validated`.

## Tipos de evidencia

`measured`, `reported`, `estimated`, `calculated`, `anecdotal`.

## Alimentación semanal

El registro de fuentes está en `config/external_sources.txt`. El script `scripts/discover_external_estimates.py` comprueba semanalmente las fuentes y conserva metadatos básicos de descubrimiento.

El workflow de GitHub Actions se ejecuta cada lunes y también puede lanzarse manualmente.

**La automatización nunca valida afirmaciones ni escribe en Leones Atlas.**
