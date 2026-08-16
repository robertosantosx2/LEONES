# H07 — JGB: evaluación de apertura basada en evidencia

## Estado

**🟢 Terminado y limpio.**

## Objetivo

Aplicar el criterio JGB de forma reproducible y trazable sin confundir apertura con rendimiento, precio, capacidad de ejecución o puntuación de recomendación.

## Dimensiones

La evaluación conserva cinco dimensiones independientes:

1. `access`
2. `model_control`
3. `data_control`
4. `autonomy`
5. `trust`

El evaluador exige evidencia para las cinco antes de derivar una clase global. Si falta una, el resultado es `unknown` y se enumera qué dimensiones quedan pendientes.

## Implementación

- `scripts/evaluate_jgb.py` — aplica el contrato JGB a evidencias explícitas.
- `scripts/atlas_jgb_enrich.py` — añade el resultado al feed Atlas sin alterar las demás métricas.
- `tests/test_evaluate_jgb.py` — verifica evaluación completa y comportamiento seguro ante evidencia incompleta.

## Flujo

```text
EVIDENCIAS
    ↓
evaluate_jgb
    ↓
dimensiones + estado + pendientes
    ↓
atlas_jgb_enrich
    ↓
feed Atlas enriquecido
```

## Regla de seguridad epistemológica

`unknown` significa **no hay evidencia suficiente**, no "falso" ni "abierto". El sistema no rellena huecos mediante inferencias silenciosas.

## Separación de conceptos

JGB no sustituye ni alimenta directamente:

- `fit_score`;
- CABE/RULA;
- rendimiento en tok/s;
- precio;
- self-hostability.

Cada propiedad mantiene su propio contrato y evidencia.

## Limpieza

La implementación está documentada para lectores con conocimientos básicos de programación, no contiene trazas de depuración ni marcadores de trabajo pendientes y escribe el resultado enriquecido en un artefacto separado del fichero de entrada.

## Criterio de cierre

H07 se considera cerrado porque el criterio está documentado, el evaluador es determinista respecto a las evidencias suministradas, la ausencia se conserva como `unknown`, existe prueba automatizada y el resultado puede incorporarse al feed de Atlas sin mezclar métricas.
