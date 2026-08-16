# H01 + H02 — Precios de hardware e integración

## 1. Para qué existe esta pieza

LEONES necesita saber cuánto cuesta realmente el hardware que después aparece en sus recomendaciones. Esta capa observa precios; no los adivina.

H01 cubre la observación mensual. H02 conecta esas observaciones con los perfiles de hardware y el recomendador.

La separación es importante: **precio, rendimiento, JGB y viabilidad técnica son dimensiones diferentes**.

## 2. Flujo sencillo

```text
TIENDAS
  ↓
LECTURA DE PÁGINAS
  ↓
IDENTIFICACIÓN DEL PRODUCTO
  ↓
IDENTIFICACIÓN CPU/RAM/GPU
  ↓
PRECIO OBSERVADO
  ↓
VALIDACIÓN
  ├── válido → histórico
  └── inválido → no entra en el dato utilizable
  ↓
RESUMEN / MERCADO
  ↓
RECOMENDADOR
```

## 3. Fuentes aceptadas

Actualmente la fase declara cuatro fuentes activas: Coolmod, PcComponentes, MediaMarkt España y LDLC España. Amazon permanece fuera de la cobertura activa.

## 4. Script principal: `scripts/collect_hardware_prices.py`

Este script hace cuatro trabajos grandes:

### A. Descargar

`fetch()` intenta primero la página directamente. Si la adquisición falla, usa el mecanismo de fallback configurado. El objetivo es que un problema de una tienda no destruya las observaciones de las demás.

### B. Encontrar productos y precios

Primero intenta datos estructurados JSON-LD, porque una tienda puede publicar ahí nombre y precio de un producto. Después usa una extracción textual como segunda vía.

### C. Clasificar

`classify()` intenta decidir si el texto corresponde a CPU, RAM o GPU y extrae familia, capacidad o VRAM. Las GPU que entran en esta capa son NVIDIA, de acuerdo con el alcance aceptado.

### D. Guardar

Las observaciones se guardan en `hardware_price_observations.csv`. Después `build_outputs()` crea dos vistas de trabajo: `hardware_prices.csv` y `hardware_price_market_summary.csv`.

## 5. Por qué existen varios CSV

- **Observations:** conserva el histórico de observaciones individuales.
- **Prices:** ofrece una vista resumida de la observación vigente.
- **Market summary:** agrupa observaciones para conocer número de fuentes y rango de precios.
- **Quality:** conserva los controles de calidad.

Nunca debe usarse un resumen para destruir el histórico.

## 6. Precisión económica

La implementación redondea las observaciones a una precisión de 10 €. Esto es deliberado: LEONES no pretende aparentar una precisión comercial que la propia extracción web no puede garantizar.

Un precio desconocido sigue siendo desconocido. **No se interpola ni se inventa.**

## 7. Workflow

`.github/workflows/monthly-hardware-prices.yml` ejecuta, por orden:

1. pruebas offline;
2. recolección multi-fuente;
3. control de calidad;
4. revisión de cobertura/coherencia;
5. publicación con protección frente a commits concurrentes.

El workflow está programado para el día 1 de cada mes y también permite ejecución manual.

## 8. H02 — integración

El precio llega al recomendador mediante `data/hardware/hardware_prices.csv`. El recomendador busca evidencia de CPU, RAM y GPU compatible con el perfil solicitado y conserva la cobertura (`1/3`, `2/3`, `3/3`, etc.).

Una cobertura parcial **no debe convertirse en un precio de PC completo**.

## 9. Qué significa «aceptado»

La fase está aceptada porque están implementados y validados extracción, normalización, calidad, histórico, resumen, automatización, publicación e integración posterior.

Eso no significa que la cobertura comercial sea perfecta. La evolución prevista incluye más tiendas, variantes, marketplaces, anomalías, promociones y TCO.

## 10. Mantenimiento para principiantes

Si tienes que modificar el recolector:

1. no cambies primero el CSV de salida;
2. localiza dónde se obtiene el dato;
3. comprueba cómo se clasifica;
4. comprueba `valid_row()`;
5. ejecuta las pruebas offline;
6. verifica que una tienda que falla no elimina las demás;
7. comprueba que el histórico sigue creciendo sin duplicar la misma observación;
8. revisa el workflow antes de dar la fase por cerrada.

## Enlaces

- Fase: [`docs/phases/2026-08-hardware-pricing/`](../phases/2026-08-hardware-pricing/)
- Script: [`scripts/collect_hardware_prices.py`](../../scripts/collect_hardware_prices.py)
- Workflow: [`.github/workflows/monthly-hardware-prices.yml`](../../.github/workflows/monthly-hardware-prices.yml)
- Integración: [`docs/atlas-hardware-price-integration.md`](../atlas-hardware-price-integration.md)
