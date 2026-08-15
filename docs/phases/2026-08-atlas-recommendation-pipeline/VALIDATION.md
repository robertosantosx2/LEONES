# Validación — Atlas → recomendador diario enriquecido

**Estado: 🟡 PROVISIONAL / EN VALIDACIÓN**

## Criterios de aceptación

| ID | Criterio | Evidencia requerida | Estado |
|---|---|---|---|
| V1 | El workflow arranca | GitHub Actions run con runner asignado | ✅ |
| V2 | Prospección e ingesta completan | pasos verdes | ✅ Run #6 |
| V3 | Se generan recomendaciones útiles | filas y perfiles hardware válidos | 🟡 Run #6: sí hay candidatos, pero matriz GPU = 0 |
| V4 | El merge conserva columnas previas | comparación de cabeceras/filas | ⏳ |
| V5 | Aparecen columnas nuevas críticas | validación automática | ✅ Run #6: 59 ficheros |
| V6 | JGB no se deriva de rendimiento | revisión del enriquecedor/salida | 🟡 contrato corregido; repetir |
| V7 | RULA no se deriva de CABE | revisión del enriquecedor/salida | 🟡 contrato corregido; repetir |
| V8 | No se inventa rendimiento | revisión de `tokens_per_second` | 🟡 no observado en #6; falta endurecer contrato |
| V9 | Publicación final correcta | commit generado por workflow | ✅ Run #6 |
| V10 | No hay pérdida de información | revisión de resultados publicados | ⏳ |
| V11 | Matriz hardware no vacía | al menos una fila de matriz | 🔴 Run #6: 0; ahora el workflow falla si vuelve a ocurrir |
| V12 | Recomendaciones no vacías | al menos una fila total | 🟡 Run #6: existen candidatos en perfiles concretos; la siguiente ejecución debe validarlo automáticamente |

## Ejecución de validación

### Run #4

- **Workflow:** `Atlas — Pipeline diario completo`
- **Run:** `#4`
- **Run ID:** `31878387802`
- **Resultado:** ❌ fallo durante la publicación por carrera de Git.

La ejecución sí llegó a generar resultados, pero el `push` fue rechazado porque `main` había avanzado durante la ejecución. Esta incidencia motivó la incorporación del mecanismo de `fetch + rebase + retry` en el workflow.

### Run #5

- **Workflow:** `Atlas — Pipeline diario completo`
- **Run:** `#5`
- **Run ID:** `31902230949`
- **Commit probado:** `e4bd724f891c0e4909f203eb35bf294c8c2334d0`
- **Resultado:** ❌ fallo temprano en `Descubrir modelos y ecosistema`.

El fallo fue un `FileNotFoundError` al escribir `data/discovery/models.json`; `models.py` no creaba previamente `data/discovery`.

### Run #6 — primera ejecución extremo a extremo

- **Workflow:** `Atlas — Pipeline diario completo`
- **Run:** `#6`
- **Run ID:** `31902361090`
- **Commit ejecutado:** `254193bc98682d6a90edf9926cebbe41328a3ddf`
- **Resultado:** ✅ workflow completado y publicado.

urlRun #6 en GitHub Actionshttps://github.com/robertosantosx2/LEONES/actions/runs/31902361090

### Resultado cuantitativo del Run #6

```text
209 modelos ingeridos
172 repositorios canónicos
209 registros marcados para verificación
67 registros en cola de evidencia externa
209 flags de calidad
0 hipótesis estructuradas
0 filas en atlas_hardware_matrix.csv
59 ficheros de recomendaciones validados estructuralmente
9 candidatos en cpu-i5-16gb
9 candidatos en cpu-i7-64gb
9 candidatos en rtx4060-8gb
```

El workflow completó correctamente todos sus pasos y publicó el commit `a786457`.

## Lectura correcta del Run #6

El verde demuestra **infraestructura E2E**, no la aceptación de la calidad de la salida.

### Lo que queda demostrado

1. Prospección, evidencia, ingesta, auditoría, hardware, recomendaciones y publicación se ejecutan dentro del workflow.
2. La ingesta procesa 209 registros.
3. La cola de evidencia externa se genera.
4. La auditoría genera 209 flags.
5. La publicación resistente a concurrencia funciona.
6. La validación estructural encuentra las columnas críticas.
7. Existen recomendaciones en algunos perfiles CPU y GPU.

### Lo que NO queda demostrado

#### 1. La matriz hardware sigue siendo el problema crítico

El Run #6 produjo:

```text
Matrix: 0 recommendation rows
```

La causa inmediata es que `atlas_hardware_matrix.py` genera perfiles compuestos, por ejemplo:

```text
cpu-intel-i5-16gb-rtx4060
```

mientras el feed puede contener un `hardware_id` específico como `rtx4060-8gb`. El recomendador anterior exigía igualdad exacta y descartaba la fila.

La matriz ya estaba diseñada para usar perfiles compuestos y no falsear una medición GPU-only como CPU+GPU; el defecto estaba en la compatibilidad del recomendador.

Se ha corregido `atlas_recommend_from_feed.py` para aceptar un hardware específico del feed cuando forma parte del perfil compuesto solicitado, manteniendo el perfil completo para cálculo de precios.

**Commit:** `043daa18ebeddb2f3660ed67c2fa09aa04c6b72e`

#### 2. El pipeline podía terminar verde con una matriz vacía

Esto era demasiado permisivo. Una matriz vacía no debe considerarse un resultado válido de una fase cuyo objetivo explícito es producir la matriz CPU × RAM × NVIDIA.

Se ha añadido una condición al workflow:

```text
matriz generada
     ↓
filas == 0 ? → FAIL
     ↓
continuar
```

También se exige que el conjunto de recomendaciones no tenga cero filas.

**Commit:** `7c56a9fb2a2cf4ce13107fbc88d90be86612c54d`

#### 3. CABE no debe derivarse de `fit_score`

El enriquecedor fue corregido anteriormente para no convertir un score compuesto en CABE. CABE/RULA/JGB y evidencia mantienen estados explícitos cuando no existe información suficiente.

**Commit:** `5be8dd2c74820cd6f35b2d78efebdd912431ecc3`

## Advertencia de Node.js

El Run #6 utilizó todavía:

```text
actions/checkout@v4
actions/setup-python@v5
```

El workflow actual de `main` ya utiliza `@v7` para ambas Actions, por lo que la siguiente ejecución debe comprobar que desaparece la advertencia.

## Estado después del Run #6

```text
PIPELINE E2E                 🟢 demostrado
PUBLICACIÓN ROBUSTA          🟢 demostrado
VALIDACIÓN ESTRUCTURAL       🟢 demostrada
CALIDAD DE DATOS             🟡 insuficiente
HIPÓTESIS                    🔴 0
MATRIZ HARDWARE              🔴 0 filas en #6; corrección aplicada
CABE/RULA/EVIDENCIA          🟡 contrato endurecido
RECOMENDACIONES              🟡 existen candidatos, pero falta validar la matriz
ACEPTACIÓN H10               🔴 NO ACEPTADA
```

## Próxima prueba válida

La siguiente ejecución debe partir de `main` después de:

```text
043daa18  → compatibilidad de hardware compuesto
7c56a9fb  → matriz/recomendaciones no pueden quedar vacías
```

Además debe verificar el cambio a `actions/checkout@v7` y `actions/setup-python@v7`.

### Criterios decisivos de la siguiente ejecución

```text
matriz hardware > 0 filas
        AND
recomendaciones totales > 0 filas
        AND
columnas críticas presentes
        AND
CABE/RULA/JGB no inferidos indebidamente
        AND
publicación correcta
```

Si todo eso se cumple, todavía revisaremos los contenidos antes de marcar H10 como **ACEPTADA**.

## Cierre

**H10 continúa abierta.**

El Run #6 demuestra que la infraestructura funciona, pero el `0` de la matriz hardware impide aceptar la fase. La siguiente ejecución es la prueba de cierre funcional de esta incidencia.
