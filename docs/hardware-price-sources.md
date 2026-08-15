# Fuentes de precios de hardware

## Fuentes activas

El bot utiliza cuatro fuentes de precios:

1. **Coolmod** — fuente prioritaria en España.
2. **PcComponentes** — fuente secundaria de apoyo.
3. **MediaMarkt España** — fuente secundaria de apoyo.
4. **LDLC España** — fuente europea de apoyo.

## Amazon: descartada

Amazon queda **fuera del sistema de precios de LEONES**. No se consulta, no participa en la cobertura, no se contabiliza como fuente activa y sus observaciones históricas no deben alimentar nuevos resúmenes del recomendador.

La decisión es deliberada: el modelo de marketplace y la variabilidad del vendedor hacen que no sea una fuente adecuada para esta fase del motor de precios. Si en el futuro se reconsiderase, tendría que reincorporarse explícitamente como un adaptador independiente y con reglas propias de vendedor, condición y precio.

## Regla de diseño

Una fuente solo se considera activa cuando existe un adaptador operativo que la consulta y produce observaciones normalizadas. La lista de fuentes activas debe coincidir con las fuentes realmente ejecutadas por el workflow.

El recomendador consume únicamente observaciones aceptadas por el control de calidad.
