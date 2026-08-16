# H09 — CABE / RULA

**Estado: 🟡 CONTRATO OPERATIVO; implementación y validación pendientes.**

## Definición oficial de LEONES

CABE y RULA son **clasificaciones de rendimiento de inferencia**, basadas en la velocidad observada en tokens por segundo (`tok/s`).

| Clase | Umbral | Significado |
|---|---:|---|
| No CABE | `< 1 tok/s` | Rendimiento inferior al mínimo operativo definido por LEONES. |
| CABE | `≥ 1 y < 10 tok/s` | Ejecución dentro del intervalo CABE. |
| RULA | `≥ 10 y ≤ 100 tok/s` | Ejecución dentro del intervalo RULA. |
| RULA+ | `> 100 tok/s` | Rendimiento superior al intervalo RULA. |

El valor continuo observado debe conservarse siempre. La etiqueta nunca sustituye a `tokens_per_second`.

## Por qué existen

El objetivo es que el recomendador pueda expresar de forma sencilla si un modelo **entra en un intervalo práctico de rendimiento** sin convertir ese dato en una valoración global del modelo.

Ejemplo:

```json
{
  "tokens_per_second": 7.8,
  "performance_class": "CABE"
}
```

Otro ejemplo:

```json
{
  "tokens_per_second": 42.0,
  "performance_class": "RULA"
}
```

## Regla de frontera

El valor `10 tok/s` pertenece a **RULA**, no a CABE. Así evitamos solapamientos:

```text
< 1          → No CABE
1 ≤ x < 10   → CABE
10 ≤ x ≤ 100 → RULA
> 100        → RULA+
```

## Lo que CABE/RULA NO significan

```text
CABE/RULA ≠ JGB
CABE/RULA ≠ calidad del modelo
CABE/RULA ≠ benchmark general
CABE/RULA ≠ precio
CABE/RULA ≠ memoria
CABE/RULA ≠ compatibilidad universal
```

La misma arquitectura puede tener distinto `tok/s` según modelo, cuantización, runtime, contexto, carga, hardware y configuración. Por ello toda medición debe conservar su contexto experimental.

## Medición mínima

Una observación válida debe conservar, cuando estén disponibles:

- modelo y variante;
- artefacto/cuántización;
- runtime/backend;
- hardware;
- contexto relevante;
- workload;
- `tokens_per_second`;
- fecha de medición;
- origen de la medición;
- método de medición;
- evidencia asociada.

Una cifra procedente de una fuente externa debe seguir identificada como evidencia externa. No se transforma automáticamente en medición LEONES.

## Flujo

```text
MODELO + ARTEFACTO + RUNTIME + HARDWARE + WORKLOAD
                         ↓
                  MEDICIÓN tok/s
                         ↓
                 VALIDACIÓN DATOS
                         ↓
              ┌──────────┴──────────┐
              ↓                     ↓
          valor continuo       clasificación
              ↓                     ↓
       tokens_per_second     CABE / RULA / RULA+
              └──────────┬──────────┘
                         ↓
                    RECOMENDADOR
```

## Subfases

- H09.1 — definición de CABE/RULA 🟢
- H09.2 — contrato de medición 🟡
- H09.3 — extractor/normalizador de tok/s ⚪
- H09.4 — clasificación automática ⚪
- H09.5 — integración con hardware y recomendador ⚪
- H09.6 — pruebas y auditoría ⚪
- H09.7 — validación final ⚪

## Criterio de cierre

H09 solo podrá declararse 🟢 cuando exista una implementación reproducible que:

1. conserve el `tok/s` original;
2. aplique exactamente los límites anteriores;
3. no solape CABE y RULA;
4. conserve el contexto de cada medición;
5. distinga evidencia externa de medición LEONES;
6. tenga pruebas automáticas para las fronteras `1`, `10` y `100` tok/s;
7. esté integrada con el recomendador;
8. tenga documentación pedagógica suficiente.

## Documentación relacionada

- [`../2026-08-jgb-systematic/`](../2026-08-jgb-systematic/)
- [`../2026-08-hardware-matrix/`](../2026-08-hardware-matrix/)
- [`../2026-08-atlas-expanded/`](../2026-08-atlas-expanded/)
