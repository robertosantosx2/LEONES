# LEONES — Capa de evidencia técnica

**Estado:** especificación operativa v1  
**Fecha:** 2026-08-16  
**Relacionado:** H10 — Implementar capa de evidencia técnica antes de generar recomendaciones

## Propósito

La capa de evidencia evita que un descubrimiento de Prospector se convierta directamente en una recomendación. Separa **lo que hemos encontrado** de **lo que podemos afirmar**.

```text
DESCUBRIMIENTO → IDENTIDAD → EVIDENCIA TÉCNICA → VERIFICACIÓN → PERFIL → CABE → MATRIZ → RECOMENDACIÓN
```

## Regla fundamental

**La ausencia de evidencia no es evidencia de ausencia.** Cuando un dato no se conoce se conserva como `unknown`; no se rellena para hacer completa una matriz o un score.

## Niveles de evidencia

| Nivel | Significado | Uso |
|---|---|---|
| `measured` | Medido por LEONES mediante procedimiento reproducible | máxima confianza para métricas propias |
| `verified` | Confirmado en fuente primaria o prueba reproducible | apto para perfil con procedencia |
| `reported` | Declarado por proyecto/proveedor | señal externa, no medición LEONES |
| `calculated` | Derivado matemáticamente | conservar fórmula y entradas |
| `estimated` | Estimación documentada | nunca presentarla como medición |
| `anecdotal` | Experiencia individual sin control suficiente | contexto, no base única |
| `unknown` | Sin evidencia suficiente | conservar explícitamente |

## Evidencia mínima

### Modelo

- nombre, familia y organización;
- URL primaria;
- licencia/condición de uso conocida;
- disponibilidad de pesos, si procede;
- arquitectura y tamaño cuando estén documentados;
- contexto cuando exista fuente fiable;
- cuantizaciones y runtimes documentados;
- benchmarks con fuente, versión y tipo de evidencia;
- fecha de comprobación.

### Runtime / herramienta

- proyecto y repositorio oficial;
- versión comprobada;
- plataforma y requisitos;
- hardware soportado si está documentado;
- modelos/formatos soportados;
- evidencia de funcionamiento;
- limitaciones conocidas.

### Benchmark

- nombre, tarea y métrica;
- protocolo;
- fuente y fecha/versión;
- resultado;
- tipo de evidencia;
- comparabilidad con otros resultados.

## Procedencia

Cada afirmación importante debe rastrearse a una fuente o a una ejecución de LEONES.

```yaml
claim: "..."
value: "..."
evidence_level: measured|verified|reported|calculated|estimated|anecdotal|unknown
source_url: "..."
source_type: primary|secondary|execution
observed_at: "YYYY-MM-DD"
checked_by: "leones|external"
method: "..."
notes: "..."
```

## Reglas de recomendación

Una recomendación no puede depender únicamente de `fit_score`, popularidad, ranking externo, afirmaciones del proveedor o una única experiencia anecdótica. Debe explicar **por qué encaja**, **qué evidencia la respalda**, **qué desconocemos** y **qué hay que probar después**.

## CABE y JGB

CABE y JGB son dimensiones independientes de la evidencia técnica.

- No derivar **CABE** de `fit_score`.
- No derivar **JGB** de rendimiento o hardware.
- No convertir una puntuación externa en propiedad intrínseca del modelo.
- Si faltan datos, el resultado es `unknown`.

## Puerta de calidad

Antes de entrar en una matriz de recomendación:

- [ ] identidad inequívoca o pendiente explícita;
- [ ] fuente primaria localizada cuando sea posible;
- [ ] afirmaciones separadas de mediciones;
- [ ] procedencia y fecha conservadas;
- [ ] desconocidos no rellenados artificialmente;
- [ ] benchmarks identificados y contextualizados;
- [ ] compatibilidad de hardware no inventada;
- [ ] licencia/openness no inferida solo por marketing;
- [ ] limitaciones registradas;
- [ ] evidencia suficiente para justificar la siguiente acción.

## Resultado

El resultado debe ser un **perfil de evidencia**, no un simple score:

```text
entity
claims[]
evidence[]
unknowns[]
verification_status
sources[]
observed_at
next_action
```

`next_action` puede ser `verify`, `measure`, `profile`, `watch` o `reject`.

## Criterio de cierre de H10

H10 queda técnicamente resuelto cuando el pipeline puede explicar tanto las recomendaciones como los descartes y ninguna recomendación depende de datos inventados o de un score que sustituya a la evidencia.

La matriz puede estar vacía y el pipeline seguir siendo correcto: **la calidad de la evidencia precede a la cantidad de candidatos**.
