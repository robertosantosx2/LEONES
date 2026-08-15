# Ranking económico del recomendador LEONES / Atlas

## 1. Objetivo

El ranking económico responde a una pregunta distinta de «¿qué modelo tiene la puntuación técnica más alta?». Busca identificar qué candidato ofrece la mejor combinación de:

1. **Índice JGB**: nivel de apertura/libertad asignado por el Atlas.
2. **Rendimiento**: evidencia observada, principalmente `tokens_per_second` cuando está disponible.
3. **Adecuación al hardware**: memoria, contexto y `fit_score` ya calculado por el recomendador.
4. **Precio real del hardware**: precios observados por el bot mensual, después de control de calidad.

El precio no sustituye al JGB ni al rendimiento. Es una dimensión económica independiente.

## 2. Esquema de decisión

```text
                    ATLAS
                      │
        ┌─────────────┼─────────────┐
        │             │             │
       JGB       RENDIMIENTO    HARDWARE
        │             │             │
        │        tokens/s       memoria/contexto
        │             │             │
        └─────────────┼─────────────┘
                      ▼
                 FIT TÉCNICO
                      │
                      ▼
             PRECIO DE MERCADO
                      │
            bot mensual de precios
                      │
          control de calidad de datos
                      │
                      ▼
              COSTE HARDWARE OBSERVADO
                      │
                      ▼
             RANKING ECONÓMICO
```

## 3. Regla fundamental: primero viabilidad

El ranking económico **no puede rescatar un modelo que no sea viable** en el hardware solicitado.

La secuencia es:

```text
¿Cabe el modelo?
   ├─ NO → excluir
   └─ SÍ
       ↓
¿Hay evidencia suficiente?
   ├─ NO → confianza baja / excluir según política
   └─ SÍ
       ↓
JGB + rendimiento + ajuste hardware
       ↓
precio observado
       ↓
valor económico
```

Esto evita que un modelo barato aparezca por delante de uno viable y de mayor utilidad simplemente porque el coste es menor.

## 4. Componentes del score

La primera versión utiliza una ponderación explícita y auditable:

- **35 % rendimiento**
- **25 % JGB**
- **40 % adecuación al hardware**

El resultado técnico se divide posteriormente por el coste observado por cada 100 € de hardware:

```text
calidad_técnica =
    0,35 × rendimiento_normalizado
  + 0,25 × JGB_normalizado
  + 0,40 × hardware_fit

ranking_económico = calidad_técnica / (coste_hardware / 100)
```

Los pesos son una **versión 1 del motor**, no una verdad universal. Deben permanecer parametrizables y evaluarse con resultados reales del recomendador.

## 5. Índice JGB

El JGB se conserva como una dimensión independiente. No se sustituye por precio, benchmark ni rendimiento.

La documentación de base utilizada para fijar el criterio JGB distingue modelos con pesos disponibles, open-weight, open-source y reproducibles, y utiliza dimensiones como acceso, control del modelo, control de datos, autonomía y confianza. La referencia de trabajo es la presentación de Jesús M. González-Barahona, «IA generativa abierta» (2026), incorporada al proyecto Atlas.

Por tanto, el ranking económico puede favorecer un modelo con mejor JGB cuando su rendimiento y adecuación siguen siendo suficientes, pero no debe convertir «más abierto» en «más rápido» ni en «más barato».

## 6. Precio real

Los precios proceden exclusivamente de `data/hardware/hardware_prices.csv`, alimentado por el bot mensual y su control de calidad.

En la versión actual, cuando se construye el coste de un perfil CPU+RAM, se utiliza la **mediana de precios observados** para la familia de CPU y la capacidad exacta de RAM solicitada.

Esto es deliberadamente conservador:

- no se usa un precio inventado;
- no se usa una predicción;
- no se utiliza un precio de marketplace descartado;
- no se mezclan productos sin correspondencia de categoría;
- no se presenta como precio de un PC completo.

El coste actual se denomina **coste de componentes observado**. No incluye placa base, almacenamiento, PSU, caja, refrigeración ni GPU si no existe un mapeo explícito.

## 7. Cobertura del precio

Cada resultado lleva `price_coverage`:

- `complete`: todos los componentes que exige el perfil económico actual tienen precio observado.
- `partial`: existe algún precio pero falta otro.
- `unknown`: no existe precio suficiente.

Si la cobertura no es completa, **no se calcula un `economic_score` ficticio**.

## 8. Por qué no usamos directamente el precio del modelo

Un LLM no tiene un precio de hardware propio.

El hardware tiene un precio.

Por eso la arquitectura correcta es:

```text
LLM
 │
 ├── JGB
 ├── rendimiento
 └── requisitos de memoria
          │
          ▼
     PERFIL HARDWARE
          │
          ├── CPU
          ├── RAM
          └── GPU
                │
                ▼
        PRECIOS OBSERVADOS
                │
                ▼
       COSTE DEL HARDWARE
```

Esta separación evita asociar accidentalmente el precio de una RTX o de un procesador al nombre del modelo LLM.

## 9. Relación con la filosofía de ejecución local

La serie de LLM locales utilizada como referencia en el proyecto establece que la capacidad de memoria decide qué modelos caben y que el ancho de banda influye decisivamente en la velocidad de decodificación; también recomienda dejar margen de memoria y medir rendimiento con cargas reales.

El recomendador conserva esas ideas: primero capacidad/viabilidad, después rendimiento observado y finalmente coste.

## 10. Salida

`data/prospection/atlas_economic_ranking.csv`

Incluye, entre otros:

- `economic_rank`
- `model_id`
- `model_name`
- `hardware_id`
- `fit_score`
- `jgb_level`
- `jgb_score`
- `tokens_per_second`
- `performance_score`
- `hardware_score`
- `hardware_cost_eur`
- `price_coverage`
- `cpu_price_eur`
- `ram_price_eur`
- `economic_score`
- `price_basis`

## 11. Automatización

El workflow `Generate Atlas Recommendations` ejecuta:

```text
1. test_atlas_price_integration.py
2. test_atlas_economic_rank.py
3. generar recomendaciones técnicas
4. generar ranking económico
5. publicar ambos CSV
```

La actualización automática no debe ocultar datos faltantes: un ranking sin precio completo debe decirlo explícitamente.

## 12. Evolución prevista

### V1 — actual
CPU + RAM observadas, JGB, rendimiento y ajuste hardware.

### V1.1
Incorporar GPU real y VRAM al coste del perfil.

### V1.2
Construir perfiles completos CPU + placa + RAM + GPU + almacenamiento + PSU + caja.

### V2
Añadir precio de compra inicial frente a coste por rendimiento sostenido.

### V3
Incorporar consumo eléctrico y coste total de propiedad (TCO).

### V4
Optimización multiobjetivo configurable por usuario:

```text
máximo JGB
máximo rendimiento
mínimo coste
máxima eficiencia
máxima privacidad
máxima libertad
```

## 13. Principio de diseño final

**El recomendador no decide cuál es «el mejor modelo» en abstracto. Decide cuál es el candidato más adecuado para una combinación concreta de carga, hardware, apertura y coste observado.**
