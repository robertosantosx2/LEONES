# Componentes terminados — documentación para mantenimiento

Este directorio reúne la documentación pedagógica de las partes de LEONES que ya tienen estado **🟢 ACEPTADA**.

La intención no es sustituir la documentación normativa de cada fase, sino hacer algo distinto: explicar **cómo funciona realmente el código**, cómo se relacionan los scripts y qué debe entender una persona que tenga conocimientos básicos de programación antes de modificarlo.

## Qué significa «terminado» aquí

Solo se incluyen los hitos que el proyecto declara aceptados en `docs/phases/README.md`:

- H01 — precios mensuales de hardware.
- H02 — integración de precios con hardware, Atlas y recomendador.
- H03 — ranking económico V1.
- H04 — prospección diaria automatizada.
- H05 — protocolo y sistema documental.
- H10 — pipeline diario Atlas → recomendador.

H06, H07, H08 y H09 **no se documentan aquí como terminados**, porque siguen en evolución.

## Cómo leer esta documentación

Para cada componente se explican cinco cosas:

1. **Para qué existe.** La pregunta que resuelve.
2. **Qué datos recibe.** Archivos, columnas y parámetros principales.
3. **Qué hace paso a paso.** En lenguaje deliberadamente sencillo.
4. **Qué produce.** Archivos y efectos sobre la web o Atlas.
5. **Qué no debe hacer.** Invariantes que protegen la calidad del proyecto.

Después se incluye el mapa de scripts y workflows para que sea posible pasar de la explicación al código.

## Documentación

| Hito | Documento | Función |
|---|---|---|
| H01/H02 | [Precios y su integración](H01-H02-HARDWARE-PRICES.md) | Explica la observación de precios, calidad, histórico y conexión con el recomendador. |
| H03 | [Ranking económico V1](H03-ECONOMIC-RANKING.md) | Explica la fórmula, sus entradas, límites y generación del ranking. |
| H04 | [Prospección diaria](H04-DAILY-PROSPECTION.md) | Explica descubrimiento, licencias, enriquecimiento y publicación. |
| H05 | [Sistema documental](H05-DOCUMENTATION-SYSTEM.md) | Explica cómo se cierra y mantiene una fase. |
| H10 | [Pipeline Atlas → recomendador](H10-ATLAS-RECOMMENDER-PIPELINE.md) | Explica el recorrido diario completo y sus contratos. |

## Regla para futuros cambios

Si se modifica un script de un componente terminado, primero hay que decidir si sigue siendo compatible con su contrato de aceptación. Si la modificación cambia comportamiento, evidencia, entradas, salidas o invariantes, la fase debe volver a validarse y su estado debe dejar de considerarse automáticamente cerrado hasta superar esa validación.

## Regla de limpieza

Los ejemplos ficticios, fixtures y datos sintéticos que tengan valor para pruebas **no son basura** y no deben eliminarse por el mero hecho de ser ficticios. Deben estar claramente identificados. En cambio, trazas de depuración, archivos temporales y borradores que no formen parte de la reproducibilidad no pertenecen a una fase terminada.
