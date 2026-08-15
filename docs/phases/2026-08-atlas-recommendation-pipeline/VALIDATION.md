# Validación — Atlas → recomendador diario enriquecido

**Estado: PROVISIONAL / EN VALIDACIÓN**

## Criterios de aceptación

La fase se podrá marcar como **ACEPTADA** cuando se cumplan todos los criterios siguientes:

| ID | Criterio | Evidencia requerida | Estado |
|---|---|---|---|
| V1 | El workflow arranca | GitHub Actions run con runner asignado | ⏳ |
| V2 | Prospección e ingesta completan | pasos verdes | ⏳ |
| V3 | Se generan recomendaciones | ficheros `recommendations_*.csv` | ⏳ |
| V4 | El merge conserva columnas previas | comparación de cabeceras/filas | ⏳ |
| V5 | Aparecen columnas nuevas críticas | validación automática | ⏳ |
| V6 | JGB no se deriva de rendimiento | revisión del enriquecedor/salida | ⏳ |
| V7 | RULA no se deriva de CABE | revisión del enriquecedor/salida | ⏳ |
| V8 | No se inventa rendimiento | revisión de `tokens_per_second` | ⏳ |
| V9 | Publicación final correcta | commit generado por workflow | ⏳ |
| V10 | No hay pérdida de información | revisión de resultados publicados | ⏳ |

## Ejecución de validación

Se lanzó manualmente:

- **Workflow:** `Atlas — Pipeline diario completo`
- **Run:** `#4`
- **Run ID:** `31878387802`
- **Estado inicial observado:** `queued`, esperando runner.

Esta ejecución constituye la evidencia de validación en curso, no una prueba de éxito.

## Prueba específica del enriquecedor

Entrada conceptual:

```text
CSV base
 ├── columnas históricas
 ├── recomendación
 └── evidencia existente
```

Salida esperada:

```text
CSV enriquecido
 ├── todas las columnas anteriores
 ├── JGB + estado
 ├── CABE + estado
 ├── RULA + estado
 ├── rendimiento si existe
 ├── memoria / KV / overhead
 ├── runtime / backend
 ├── evidencia
 └── incertidumbre
```

## Resultado esperado de la validación

El éxito no significa que todos los campos estén rellenos. Significa que:

1. el contrato se cumple;
2. los datos existentes sobreviven;
3. los datos desconocidos permanecen desconocidos;
4. las inferencias prohibidas no aparecen;
5. el workflow puede repetir el proceso diariamente.

## Cierre

Cuando el run real termine, este documento debe actualizarse con:

- conclusión del run;
- pasos relevantes;
- número de ficheros producidos;
- comprobaciones realizadas;
- commit de publicación;
- incidencias corregidas, si las hubiera;
- criterio final **ACEPTADA / NO ACEPTADA**.

Hasta entonces, **no marcar la fase como terminada**.
