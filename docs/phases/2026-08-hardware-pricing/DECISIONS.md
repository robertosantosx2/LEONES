# Decisiones — Bot mensual de precios

## D1 — Capa independiente del Atlas

El precio se mantiene separado del conocimiento del modelo. El hardware tiene precio; el LLM tiene requisitos y evidencia.

## D2 — Cuatro fuentes activas

La configuración actual mantiene Coolmod, PcComponentes, MediaMarkt España y LDLC España. Amazon queda fuera de la cobertura activa.

## D3 — No inventar precios

Ausencia de precio = desconocido. Nunca se completa silenciosamente mediante estimación.

## D4 — Histórico separado del resumen

Las observaciones históricas y la vista vigente tienen responsabilidades distintas para conservar trazabilidad.

## D5 — Control de calidad previo a recomendación

Los datos deben pasar controles antes de alimentar el recomendador.

## D6 — Fallo aislado de fuente

Un fallo de una tienda no debe impedir la recogida del resto.

## D7 — Coste observado no equivale a PC completo

Mientras no exista cobertura de todos los componentes, el coste se denomina coste de componentes observado y no debe presentarse como precio de un equipo completo.
