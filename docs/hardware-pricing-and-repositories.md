# LEONES — Base de repositorios, hardware y precios

## 1. Objetivo

El Atlas y el recomendador de LEONES deben distinguir tres capas:

1. **Modelo/proyecto**: qué sistema de IA es.
2. **Repositorio/evidencia**: dónde está publicado y qué evidencia permite verificarlo.
3. **Hardware y coste**: qué máquina puede ejecutarlo y cuánto cuesta construirla.

No se permite usar una página genérica de una forja como si fuera el repositorio concreto de un modelo.

## 2. Repositorio canónico

El ingestor (`scripts/atlas_ingest_ndjson.py`) acepta rutas de repositorio con formato `owner/repository` y, cuando conoce la forja, construye la URL canónica correspondiente. Ejemplos conceptuales:

- GitHub → `https://github.com/owner/repository`
- GitLab → `https://gitlab.com/owner/repository`
- Codeberg → `https://codeberg.org/owner/repository`
- Gitea → `https://gitea.com/owner/repository`
- Hugging Face → `https://huggingface.co/owner/repository`

La URL de la forja (`https://github.com`, etc.) por sí sola **no es evidencia suficiente**.

Los registros siguen marcados como `discovered` hasta que exista evidencia verificable. La URL canónica no convierte por sí sola un descubrimiento en un modelo verificado.

## 3. Limpieza de prospección

Se eliminaron archivos `.rej` heredados de intentos de parche rechazados. No forman parte del dataset de evidencia y no deben volver a generarse como salida normal del pipeline.

## 4. Matriz de hardware

La matriz del recomendador contempla las categorías:

- Intel Core i3/i5/i7/i9.
- AMD Ryzen 3/5/7/9.
- RAM de 2, 4, 8, 16, 32, 64 y 128 GB.
- DDR4 y DDR5 cuando la capacidad tiene sentido para el mercado.
- GPU NVIDIA RTX con VRAM separada de la RAM del sistema.

Las categorías Intel/AMD son equivalencias de **segmento**, no afirmaciones de igualdad de rendimiento entre modelos.

## 5. Precios: separación de datos

Los precios no forman parte de la identidad del modelo. Se mantienen en una base independiente:

`data/hardware/hardware_price_observations.csv`

Esta es la **historia de observaciones**. Cada fila conserva:

- fecha;
- componente;
- fabricante;
- modelo;
- capacidad/VRAM;
- precio en EUR;
- mercado;
- fuente;
- URL de origen;
- notas.

`data/hardware/hardware_prices.csv` es el **resumen vigente** derivado de las observaciones más recientes.

## 6. Red de fuentes de precios

La fuente de precios deja de ser un único comercio. El registro maestro está en:

`data/hardware/price_sources.csv`

La política establecida para el recomendador es la siguiente.

### 6.1 PcComponentes — prioridad 1 / fuente principal en España

Es el referente principal del mercado español para esta base. Se utilizará como primera fuente para CPU, RAM y GPU cuando exista producto comparable.

Web oficial: https://www.pccomponentes.com/

### 6.2 Amazon España — prioridad 2 / fuente secundaria

Se incorpora como segunda fuente por su volumen y disponibilidad de componentes.

**Regla especial:** Amazon es un marketplace. El precio debe conservar siempre información del vendedor cuando esté disponible. No se deben mezclar automáticamente precio de vendedor externo, precio de Amazon, reacondicionado y ofertas temporales como si fueran la misma observación.

Web oficial: https://www.amazon.es/

### 6.3 Coolmod — prioridad 3 / fuente especialista

Se incorpora como fuente especializada de hardware, especialmente útil para componentes de PC, gaming, modding, refrigeración y configuraciones de alto rendimiento.

Web oficial: https://www.coolmod.com/

### 6.4 MediaMarkt España — prioridad 4 / fuente secundaria

Se incorpora para ampliar la cobertura del mercado español. Su catálogo incluye una categoría específica de componentes, con procesadores, RAM y tarjetas gráficas.

**Regla especial:** distinguir venta directa de MediaMarkt, marketplace y reacondicionado. No deben agregarse en la misma distribución de precios sin etiquetar su naturaleza.

Web oficial: https://www.mediamarkt.es/

### 6.5 LDLC España — prioridad 5 / especialista europeo

Se incorpora como fuente europea especializada. La versión española dispone de categorías de tarjeta gráfica, memoria, procesador y otros componentes, además de configurador de PC.

Web oficial: https://www.ldlc.com/es-es/

### 6.6 Caseking — prioridad 5 / especialista europeo

Se incorpora junto a LDLC como referencia europea especializada, especialmente para componentes de gama alta o difíciles de encontrar. El mercado europeo se conservará separado del mercado español cuando no exista una oferta española equivalente.

Web oficial: https://www.caseking.de/

## 7. Jerarquía de confianza

Las prioridades anteriores **no significan que el precio más bajo gane automáticamente**.

El motor debe conservar todas las observaciones válidas y posteriormente calcular estadísticas comparables.

Una observación debe conservar:

```text
fuente
vendedor
fecha
modelo
SKU/EAN si está disponible
precio
moneda
IVA incluido/excluido
stock/disponibilidad
nuevo/reacondicionado
URL
```

Cuando sea posible, la identificación del producto debe apoyarse en SKU, EAN/GTIN o una combinación normalizada de fabricante + modelo.

## 8. Comparabilidad de precios

Antes de comparar precios entre fuentes, el bot debe normalizar:

1. **Moneda** → EUR.
2. **IVA** → preferentemente precio final con IVA para España.
3. **Estado** → nuevo separado de reacondicionado/segunda mano.
4. **Vendedor** → venta directa separada de marketplace.
5. **Disponibilidad** → en stock, bajo pedido y agotado separados.
6. **Producto** → mismo modelo o equivalencia explícitamente identificada.
7. **Oferta** → precio promocional conservado como observación, pero no tratado automáticamente como precio estructural.

Esto evita que el recomendador elija artificialmente una configuración por mezclar condiciones comerciales diferentes.

## 9. Estrategia de recopilación

El bot mensual seguirá este esquema:

```text
                  RED DE FUENTES
                        │
       ┌────────────────┼────────────────┐
       ▼                ▼                ▼
   España            España            Europa
       │                │                │
 PcComponentes      Amazon          LDLC / Caseking
       │             Coolmod              │
       │           MediaMarkt             │
       └────────────────┼────────────────┘
                        ▼
                NORMALIZACIÓN
                        ▼
                  IDENTIFICACIÓN
                        ▼
                    VALIDACIÓN
                        ▼
              OBSERVACIONES MENSUALES
                        ▼
                  SERIE HISTÓRICA
                        ▼
                PRECIO REPRESENTATIVO
                        ▼
                   RECOMENDADOR
```

La primera implementación automatizada dispone de PcComponentes. Las demás fuentes quedan **establecidas en el registro maestro como fuentes planificadas**, y se incorporarán mediante adaptadores independientes, evitando convertir una única tienda en punto único de fallo.

## 10. Regla de integridad económica

Una ausencia de precio no se rellena con una estimación silenciosa. Si una fuente no responde, cambia su HTML o no ofrece un producto, el registro permanece sin precio o se conserva la última observación histórica claramente fechada.

El recomendador debe poder distinguir:

- `observed`: precio observado directamente;
- `reference`: valor de referencia previamente documentado;
- `unknown`: no existe evidencia suficiente.

## 11. Bot mensual

Workflow:

`.github/workflows/monthly-hardware-prices.yml`

Nombre visible:

**Precios hardware — actualización mensual**

Horario:

**día 1 de cada mes, 04:23 UTC**.

También admite ejecución manual.

El pipeline mensual realiza:

```text
Fuentes de mercado
      ↓
collect_hardware_prices.py
      ↓
hardware_price_observations.csv
      ↓
update_hardware_prices.py
      ↓
hardware_prices.csv
      ↓
Git commit si existen cambios
```

El workflow está preparado para tolerar actualizaciones concurrentes de `main`, haciendo `fetch + rebase + reintento` antes de publicar.

## 12. Relación con JGB

El precio **no sustituye al Índice JGB**.

El recomendador conserva dimensiones independientes:

```text
JGB / apertura
calidad
rendimiento
memoria
contexto
runtime
hardware
precio
```

El precio podrá utilizarse después para métricas como:

- coste total de configuración;
- €/GB de VRAM;
- €/token/s;
- coste por capacidad de modelo;
- relación coste/rendimiento.

Estas métricas económicas no deben modificar retrospectivamente la clasificación JGB.

## 13. Estado

La arquitectura queda preparada para evolucionar desde una primera fuente automatizada hacia una **red mensual multi-fuente**. La calidad de cada dato depende de la fuente y debe conservarse junto a su fecha, vendedor, condiciones comerciales y URL.
