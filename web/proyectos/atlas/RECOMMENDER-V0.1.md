# Recommendation Engine v0.1

El motor determinista convierte el conocimiento del Atlas en una recomendación contextual.

## Entrada

```text
hardware
+ workload
+ contexto requerido
+ restricciones obligatorias
+ preferencias
```

## Fase 1 — viabilidad

Se descartan configuraciones que incumplan requisitos duros:

- memoria disponible;
- contexto mínimo;
- compatibilidad hardware/runtime;
- workload/modalidad;
- JGB mínimo, si el usuario lo exige;
- rendimiento mínimo, si el usuario lo exige.

## Fase 2 — ajuste

Las configuraciones viables se comparan mediante:

- calidad;
- velocidad observada;
- margen de memoria;
- compatibilidad;
- apertura JGB, únicamente si es una preferencia explícita.

## Pesos iniciales

| Factor | Peso |
|---|---:|
| Calidad | 0.35 |
| Velocidad | 0.25 |
| Memoria | 0.15 |
| Compatibilidad | 0.15 |
| Apertura | 0.10 |

Estos pesos son **defaults del v0.1**, no una verdad universal. El usuario puede modificar las prioridades.

## Regla JGB

JGB nunca aumenta artificialmente la calidad de un modelo. Su función es representar apertura/libertad.

Puede actuar de dos maneras:

### Restricción

```text
required_jgb_level = 3
```

Entonces una configuración JGB 2 o desconocida no cumple el requisito.

### Preferencia

```text
prefer_jgb = true
```

Entonces se incorpora como una preferencia secundaria.

### Sin preferencia

JGB se muestra como información y evidencia, pero no altera el ranking.

## Resultado

Cada resultado contiene:

```text
rank
model_id
deployment_id
viable
fit_score
explanation
confidence
```

La explicación debe permitir entender por qué se recomienda y qué incertidumbres quedan.

## Conservadurismo

Datos desconocidos no se rellenan con estimaciones silenciosas.

Especialmente:

- JGB desconocido ≠ JGB 0;
- JGB desconocido ≠ Open Weight;
- rendimiento desconocido ≠ rendimiento cero en la base de conocimiento;
- ausencia de benchmark ≠ mala calidad.

## Evolución

El v0.1 es deliberadamente determinista. Primero se busca una base auditable y reproducible. La incorporación posterior de aprendizaje automático solo tendrá sentido cuando existan suficientes observaciones locales y externas de calidad y rendimiento.
