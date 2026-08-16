# H03 — Ranking económico V1

## 1. Qué problema resuelve

Una recomendación puede ser técnicamente buena pero económicamente poco atractiva. H03 añade una medida de valor económico a partir de datos que ya existen en LEONES.

La V1 combina cuatro ideas: rendimiento, JGB, adecuación al hardware y coste observado.

## 2. Flujo

```text
RECOMENDACIONES ATLAS
        ↓
FILTRAR DATOS UTILIZABLES
        ↓
NORMALIZAR RENDIMIENTO
        ↓
NORMALIZAR JGB
        ↓
USAR HARDWARE FIT
        ↓
OBTENER COSTE OBSERVADO
        ↓
CALCULAR CALIDAD TÉCNICA
        ↓
DIVIDIR POR COSTE
        ↓
RANKING
```

## 3. Script principal

`scripts/atlas_economic_rank.py` recibe un CSV de recomendaciones y el CSV de precios.

Las funciones tienen responsabilidades sencillas:

- `num()` convierte valores numéricos sin romper el proceso ante campos vacíos.
- `cpu_family()` identifica la familia de CPU del perfil.
- `median()` calcula la mediana de precios disponibles.
- `load()` carga un CSV y devuelve filas.
- `component_price()` busca precios observados compatibles.
- `hardware_cost()` comprueba si CPU y RAM tienen precio suficiente para construir el coste V1.
- `economic_rank()` calcula y ordena los candidatos.
- `main()` conecta argumentos, datos y archivo de salida.

## 4. Fórmula V1

```text
calidad_técnica =
    0,35 × rendimiento_normalizado
  + 0,25 × JGB_normalizado
  + 0,40 × hardware_fit

ranking_económico =
    calidad_técnica / (coste_hardware / 100)
```

Los pesos son parametrizables y experimentales. No deben interpretarse como una verdad científica universal.

## 5. Reglas que protegen el resultado

1. La viabilidad técnica precede al precio.
2. JGB no se sustituye por rendimiento.
3. El precio debe proceder de una observación.
4. Si falta precio suficiente, el score económico queda vacío.
5. V1 no afirma que CPU + RAM sea el coste de un PC completo.
6. La salida conserva la base del precio.

## 6. Por qué se usa la mediana

Si existen varias observaciones del mismo componente, la mediana evita que un precio excepcionalmente alto o bajo domine inmediatamente el cálculo. Sigue siendo una representación de las observaciones disponibles, no una tasación.

## 7. Qué NO hace V1

No incorpora todavía de forma completa placa base, almacenamiento, PSU, caja, refrigeración, electricidad, TCO ni coste por tarea. Esas capacidades pertenecen a fases posteriores.

## 8. Mantenimiento para principiantes

Antes de tocar la fórmula, comprueba qué significa cada columna del CSV de entrada. No cambies un nombre de columna solo porque parezca más claro: puede ser parte del contrato con otro script.

Si modificas los pesos, debes actualizar la documentación de la fase y volver a ejecutar los tests de integración.

## Enlaces

- Fase: [`docs/phases/2026-08-economic-ranking-v1/`](../phases/2026-08-economic-ranking-v1/)
- Script: [`scripts/atlas_economic_rank.py`](../../scripts/atlas_economic_rank.py)
- Metodología: [`docs/atlas-economic-ranking.md`](../atlas-economic-ranking.md)
- Precios: [`docs/completed/H01-H02-HARDWARE-PRICES.md`](H01-H02-HARDWARE-PRICES.md)
