# Evidence policy

LEONES separa explícitamente **información encontrada** de **evidencia aceptada por Atlas**.

## Estados

```text
external-unvalidated
        ↓
      review
   ↙         ↘
rejected   atlas-evidence
```

`external-unvalidated` puede publicarse en la sección de estimaciones externas. No puede utilizarse por sí sola para afirmar que un modelo cabe, alcanza una velocidad o funciona con una determinada configuración.

## Promoción a Atlas

La transición requiere revisión explícita. El código exige identificar al revisor, pero **no automatiza la verdad de la afirmación**. La revisión debe comprobar la fuente, el contexto, la configuración y, cuando sea posible, una segunda evidencia independiente o una medición propia.

## Tipos de evidencia

- `measured`: medición realizada por LEONES o por una fuente identificada con metodología reproducible;
- `reported`: resultado declarado por un tercero;
- `estimated`: cálculo o estimación;
- `calculated`: valor derivado de datos conocidos;
- `anecdotal`: experiencia individual.

El tipo de evidencia permanece visible incluso después de ser aceptado en Atlas.

## Regla de transparencia

**Validado en Atlas no significa necesariamente medido por LEONES.** Significa que la afirmación ha pasado el proceso de revisión definido para Atlas y que su procedencia y naturaleza están documentadas.
