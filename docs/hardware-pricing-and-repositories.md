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

## 6. Regla de integridad económica

Una ausencia de precio no se rellena con una estimación silenciosa. Si una fuente no responde, cambia su HTML o no ofrece un producto, el registro permanece sin precio o se conserva la última observación histórica claramente fechada.

El recomendador debe poder distinguir:

- `observed`: precio observado directamente;
- `reference`: valor de referencia previamente documentado;
- `unknown`: no existe evidencia suficiente.

## 7. Bot mensual

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

## 8. Fuentes iniciales

La primera implementación utiliza páginas de catálogo de PcComponentes para:

- Intel;
- AMD Ryzen 3/5/7/9;
- DDR4;
- DDR5;
- tarjetas gráficas, filtrando NVIDIA RTX.

El recolector utiliza datos estructurados `Product`/`offers` cuando están disponibles. Si una página bloquea la consulta o cambia de estructura, el workflow registra el fallo y no inventa precios.

La cobertura de una fuente se debe considerar una muestra de mercado, no una representación universal de todos los vendedores españoles.

## 9. Relación con JGB

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

## 10. Estado

La arquitectura está preparada para pasar de un catálogo de precios mantenido manualmente a una **serie temporal mensual automatizada**. La calidad de cada dato depende de la fuente y debe conservarse junto a su fecha y URL.
