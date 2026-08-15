# Bot de precios de hardware de LEONES

> **Fase formal:** [`docs/phases/2026-08-hardware-pricing/`](phases/2026-08-hardware-pricing/)
>
> **Estado:** 🟢 ACEPTADA como infraestructura operativa; cobertura e inteligencia de precios continúan evolucionando.

## Objetivo

El bot mantiene una capa de precios independiente del Atlas de LLMs. Su misión es proporcionar al recomendador una fotografía mensual y un histórico verificable del coste de **CPU + RAM + GPU NVIDIA** en euros, principalmente para el mercado español.

El precio es una dimensión económica del recomendador; **no sustituye al Índice JGB, ni a los benchmarks, ni a la compatibilidad del modelo**.

## Fuentes activas actuales

La configuración efectiva y vigente es:

1. **Coolmod** — prioridad 1.
2. **PcComponentes** — prioridad 2.
3. **MediaMarkt España** — prioridad 3.
4. **LDLC España** — prioridad 4.

**Amazon España no está actualmente en la cobertura activa.** Cualquier reactivación requiere una decisión explícita y una actualización de `data/hardware/price_sources.csv`.

La definición efectiva vive en `data/hardware/price_sources.csv` y las páginas objetivo en `data/hardware/price_source_targets.json`.

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
       directo         fallback      discovery
          |              |              |
          +--------------+--------------+
                         |
                   normalización
                         |
                    validación
                         |
          +--------------+--------------+
          |              |              |
      histórico       resumen       calidad
          |              |              |
          +--------------+--------------+
                         |
                    RECOMENDADOR
```

## Estrategias de adquisición

### category

Consulta páginas de categorías conocidas.

### search

Consulta páginas de búsqueda de producto cuando estén configuradas.

### discover

Parte de una página oficial y descubre enlaces internos relacionados con procesadores, memoria y gráficas cuando una URL interna pueda cambiar.

## Fallback

Cada URL se intenta primero mediante HTTP directo. Si la fuente responde con bloqueo, error de red o timeout, puede utilizarse el mecanismo de fallback configurado.

Un fallo de una fuente **no debe detener las demás**.

## Extracción

El normalizador reconoce familias de CPU Intel/AMD, DDR4/DDR5 con capacidad y NVIDIA GeForce RTX con VRAM cuando está publicada, además de diferentes formatos habituales de precio.

Las observaciones corruptas o fuera de las reglas de calidad se descartan del conjunto utilizable y conservan su trazabilidad en la capa de calidad cuando corresponde.

## Datos generados

### `hardware_price_observations.csv`

Histórico de observaciones. Cada fila conserva fecha, componente, modelo, precio, fuente y URL.

### `hardware_prices.csv`

Resumen vigente por producto/modelo y entrada sencilla para el recomendador.

### `hardware_price_market_summary.csv`

Agrupa observaciones por producto y calcula número de fuentes, fuentes disponibles, precio mínimo, mediana, máximo y fecha más reciente.

La mediana ayuda a evitar que una observación aislada distorsione el coste representativo.

## Reglas económicas

1. Nunca inventar un precio.
2. Precio desconocido permanece desconocido.
3. Una oferta puntual no sustituye al histórico.
4. El precio más bajo no gana automáticamente.
5. Se conservan las fuentes disponibles.
6. El precio se almacena en EUR y con fecha de observación.
7. La comparación entre fuentes se hace sobre productos equivalentes.
8. El coste no altera el Índice JGB.
9. El coste de componentes observado no debe presentarse como precio de un PC completo.

## Calidad

Antes de la recogida se ejecutan pruebas offline en `scripts/test_hardware_price_bot.py`.

Después se ejecuta `scripts/update_hardware_prices.py`, que informa de cobertura y catálogo.

El workflow debe publicar únicamente datos que hayan pasado el control correspondiente.

## Programación

El workflow `.github/workflows/monthly-hardware-prices.yml` se ejecuta mensualmente y admite ejecución manual.

La publicación utiliza una estrategia de sincronización para reducir conflictos si otro workflow actualiza `main` simultáneamente.

## Evolución prevista

### Fase 1 — infraestructura — ACEPTADA

- [x] separar precios del Atlas;
- [x] histórico mensual;
- [x] CPU/RAM/GPU;
- [x] cuatro fuentes activas;
- [x] fallback;
- [x] validación;
- [x] publicación automática.

### Fase 2 — cobertura — EN DESARROLLO

- [x] Coolmod;
- [x] PcComponentes;
- [x] MediaMarkt España;
- [x] LDLC España;
- [ ] aumentar cobertura efectiva por fuente;
- [ ] resolver variantes de producto.

### Fase 3 — inteligencia de precios — PENDIENTE

- [ ] detectar bajadas/subidas mensuales;
- [ ] detectar mínimos históricos;
- [ ] detectar anomalías;
- [ ] calcular precio representativo por categoría;
- [ ] calcular coste de configuración CPU + RAM + GPU completo;
- [ ] integrar €/token/s y €/GB de VRAM cuando exista evidencia suficiente.

## Principio rector

El bot no tiene como objetivo producir el precio más bonito, sino **el precio más trazable y útil para tomar decisiones sobre hardware de IA local**.

## Cierre de fase

La infraestructura del bot está aceptada. Las mejoras de cobertura, inteligencia y TCO son fases posteriores y no deben retroactivamente convertir esta fase en «incompleta».
