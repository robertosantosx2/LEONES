# Bot de precios de hardware de LEONES

## Objetivo

El bot mantiene una capa de precios independiente del Atlas de LLMs. Su misión es proporcionar al recomendador una fotografía mensual y un histórico verificable del coste de **CPU + RAM + GPU NVIDIA** en euros, principalmente para el mercado español.

El precio es una dimensión económica del recomendador; **no sustituye al Índice JGB, ni a los benchmarks, ni a la compatibilidad del modelo**.

## Fuentes oficiales fijadas

1. **PcComponentes** — prioridad 1, fuente principal española.
2. **Amazon España** — prioridad 2, fuente secundaria; se conserva vendedor/marketplace como información de procedencia.
3. **Coolmod** — prioridad 3, especialista español.
4. **MediaMarkt España** — prioridad 4, secundaria; hay que distinguir venta directa, marketplace y reacondicionado.
5. **LDLC España** — prioridad 5, especialista europeo con presencia española.

Caseking está deliberadamente excluida.

La definición de fuentes vive en `data/hardware/price_sources.csv` y las páginas objetivo en `data/hardware/price_source_targets.json`.

## Arquitectura

```text
                    BOT MENSUAL
                         |
        +----------------+----------------+
        |                |                |
     CPU               RAM              GPU
        |                |                |
  Intel / AMD       DDR4 / DDR5       NVIDIA RTX
        |                |                |
        +----------------+----------------+
                         |
                adaptadores de fuente
                         |
          +--------------+--------------+
          |              |              |
       directo         Jina          discovery
          |              |              |
          +--------------+--------------+
                         |
                   normalización
                         |
                    validación
                         |
          +--------------+--------------+
          |              |              |
      histórico       resumen       mercado
          |              |              |
          +--------------+--------------+
                         |
                    RECOMENDADOR
```

## Estrategias de adquisición

### category

Consulta páginas de categorías conocidas. Se usa en PcComponentes, MediaMarkt y LDLC.

### search

Consulta páginas de búsqueda de producto. Se usa en Amazon España.

### discover

Parte de la portada oficial y descubre enlaces internos relacionados con procesadores, memoria y gráficas. Se usa en Coolmod para no depender de una URL interna que pueda cambiar.

## Fallback

Cada URL se intenta primero mediante HTTP directo. Si la fuente responde con bloqueo, error de red o timeout, se utiliza Jina Reader como fallback.

Un fallo de una fuente **no detiene las demás**.

El bot solo falla por ausencia de datos cuando:

- no existe ninguna observación válida en el histórico, o
- todas las fuentes configuradas fallan.

## Extracción

El normalizador reconoce:

- Intel Core i3/i5/i7/i9.
- AMD Ryzen 3/5/7/9.
- DDR4 y DDR5 con capacidad en GB.
- NVIDIA GeForce RTX y VRAM cuando está publicada.
- precios `123,45 €`, `123.45 €` y formatos tipográficos como `123 ^{45} €`.

Las observaciones con nombres corruptos, enlaces incrustados, encabezados Markdown o precios fuera del rango razonable son descartadas.

## Datos generados

### `hardware_price_observations.csv`

Es el **histórico inmutable lógico** de observaciones. Cada fila conserva fecha, componente, modelo, precio, fuente y URL.

### `hardware_prices.csv`

Es el resumen vigente por producto/modelo y sirve como entrada sencilla para el recomendador.

### `hardware_price_market_summary.csv`

Agrupa las observaciones por producto y calcula:

- número de fuentes;
- fuentes disponibles;
- precio mínimo;
- mediana;
- precio máximo;
- fecha de observación más reciente.

La mediana es especialmente útil para evitar que una oferta aislada o un marketplace distorsione el coste representativo.

## Reglas económicas

1. Nunca inventar un precio.
2. Precio desconocido permanece desconocido.
3. Una oferta puntual no sustituye al histórico.
4. El precio más bajo no gana automáticamente.
5. Se conservan todas las fuentes disponibles.
6. Amazon debe distinguir vendedor/marketplace cuando la página lo permita.
7. MediaMarkt debe distinguir venta directa, marketplace y reacondicionado.
8. El precio se almacena en EUR y con fecha de observación.
9. La comparación entre fuentes se hace sobre productos equivalentes, no por familia genérica cuando exista modelo concreto.
10. El coste no altera el Índice JGB.

## Calidad

Antes de cada recogida se ejecutan pruebas offline en `scripts/test_hardware_price_bot.py`.

Después se ejecuta `scripts/update_hardware_prices.py`, que informa de cobertura CPU/RAM y del catálogo NVIDIA.

El workflow utiliza `checkout@v6` y `setup-python@v7`, evitando la advertencia de Node 20 de las versiones anteriores.

## Programación

El workflow `.github/workflows/monthly-hardware-prices.yml` se ejecuta el día 1 de cada mes a las 04:23 UTC y también admite ejecución manual.

La publicación usa `fetch + rebase + push` con hasta tres intentos para evitar perder datos si otro workflow actualiza `main` simultáneamente.

## Evolución prevista

### Fase 1 — infraestructura

- [x] separar precios del Atlas;
- [x] histórico mensual;
- [x] CPU/RAM/GPU;
- [x] cinco fuentes;
- [x] fallback Jina;
- [x] validación;
- [x] publicación automática.

### Fase 2 — cobertura

- [x] PcComponentes;
- [x] Amazon España;
- [x] Coolmod;
- [x] MediaMarkt España;
- [x] LDLC España;
- [ ] aumentar cobertura efectiva por fuente;
- [ ] resolver variantes de producto y marketplace.

### Fase 3 — inteligencia de precios

- [ ] detectar bajadas/subidas mensuales;
- [ ] detectar mínimos históricos;
- [ ] detectar anomalías;
- [ ] calcular precio representativo por categoría;
- [ ] calcular coste de configuración CPU + RAM + GPU;
- [ ] integrar €/token/s y €/GB de VRAM en el recomendador.

## Principio rector

El bot no tiene como objetivo producir el precio más bonito, sino **el precio más trazable y útil para tomar decisiones sobre hardware de IA local**.
