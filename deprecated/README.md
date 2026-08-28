# Deprecated — LEONES

Esta zona contiene componentes históricos que ya no forman parte del núcleo operativo de RC1.

## Regla

No se mueve aquí un archivo simplemente porque sea antiguo. Antes hay que comprobar que no tenga consumidores activos o migrarlos explícitamente.

El procedimiento es:

```text
inventariar
  ↓
buscar consumidores
  ↓
clasificar
  ↓
migrar o retirar
  ↓
tests
  ↓
documentar
  ↓
mover a deprecated
```

La documentación de referencia es [`../docs/RC1-SCRIPT-MIGRATION.md`](../docs/RC1-SCRIPT-MIGRATION.md).

## Archivo histórico

La rama `deprecated/pre-rc1-archive` conserva un punto de referencia del estado de RC1 antes de futuras migraciones destructivas. No sustituye al movimiento individual de componentes: sirve como salvaguarda histórica y facilita comparar antes/después.

## Importante

`deprecated/` no es un vertedero. Cada componente que llegue aquí debe conservar una nota mínima sobre:

- procedencia;
- motivo de deprecación;
- sustituto, si existe;
- consumidores conocidos en el momento del movimiento;
- condición de recuperación, si procede.
