# Control de calidad de precios de hardware

## Objetivo

La capa de precios del recomendador separa tres conceptos: observación, calidad y utilización. El histórico mensual conserva las observaciones recibidas; el control de calidad decide cuáles pueden alimentar los resúmenes que consume el recomendador.

## Reglas

- No se inventan precios ausentes.
- No se convierten equipos completos en CPU, RAM o GPU individuales.
- Portátiles, notebooks, PCs completos, barebones y all-in-one quedan fuera de los resúmenes de componentes.
- Una CPU debe contener una familia Core i3/i5/i7/i9 o Ryzen 3/5/7/9.
- Una GPU debe contener una familia RTX válida y pertenecer a NVIDIA.
- Una RAM debe contener DDR4 o DDR5.
- El precio debe estar dentro del rango operativo de 5 a 10.000 €.
- Las observaciones rechazadas no se borran: permanecen en `hardware_price_observations.csv` para auditoría.

## Salidas

- `hardware_price_observations.csv`: histórico bruto/normalizado de observaciones.
- `hardware_price_quality.csv`: cada observación con `quality_score`, `quality_status` y `quality_reason`.
- `hardware_prices.csv`: únicamente observaciones aceptadas para el estado vigente.
- `hardware_price_market_summary.csv`: resumen por producto con mínimo, mediana, máximo y número de fuentes.

## Principio para el recomendador

El recomendador debe consumir exclusivamente las observaciones aceptadas. Un dato rechazado no se transforma en una estimación: se mantiene como hueco de evidencia.

## Evolución prevista

La siguiente fase añadirá detección de precios truncados y consistencia entre título, especificaciones, precio y categoría por fuente. También se podrá incorporar un `quality_score` específico por fuente y un control de anomalías temporales.
