# Validación — Atlas → recomendador diario enriquecido

**Estado: 🟡 PROVISIONAL / EN VALIDACIÓN**

## Criterios de aceptación

La fase se podrá marcar como **ACEPTADA** cuando se cumplan todos los criterios siguientes:

| ID | Criterio | Evidencia requerida | Estado |
|---|---|---|---|
| V1 | El workflow arranca | GitHub Actions run con runner asignado | ✅ |
| V2 | Prospección e ingesta completan | pasos verdes | ✅ Run #6 |
| V3 | Se generan recomendaciones | ficheros `recommendations_*.csv` | ⚠️ generadas, pero calidad insuficiente |
| V4 | El merge conserva columnas previas | comparación de cabeceras/filas | ⏳ |
| V5 | Aparecen columnas nuevas críticas | validación automática | ✅ Run #6: 59 ficheros |
| V6 | JGB no se deriva de rendimiento | revisión del enriquecedor/salida | ⚠️ salida revisada; corrección adicional necesaria |
| V7 | RULA no se deriva de CABE | revisión del enriquecedor/salida | ⚠️ salida revisada; corrección adicional necesaria |
| V8 | No se inventa rendimiento | revisión de `tokens_per_second` | ⚠️ no se observó rendimiento inventado; falta endurecer contrato |
| V9 | Publicación final correcta | commit generado por workflow | ✅ Run #6 |
| V10 | No hay pérdida de información | revisión de resultados publicados | ⏳ |

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

El runner arrancó correctamente y el checkout fue correcto. El fallo concreto fue:

```text
FileNotFoundError: [Errno 2] No such file or directory:
'data/discovery/models.json'
```

La causa se identificó en `scripts/prospectors/models.py`: escribía directamente en `data/discovery/models.json` sin crear previamente el directorio.

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

El workflow completó correctamente todos sus pasos, incluido el `fetch + rebase + push`, y publicó el commit `a786457`.

## Lectura del Run #6

### Lo que queda demostrado

1. El pipeline extremo a extremo arranca y termina.
2. La prospección produce los artefactos de descubrimiento.
3. La ingesta procesa 209 registros.
4. La generación de evidencia funciona y produce una cola.
5. La auditoría de calidad funciona y genera 209 flags.
6. La publicación resistente a concurrencia funciona.
7. La validación estructural detecta las columnas críticas en 59 ficheros.

### Lo que NO queda demostrado

El workflow verde **no significa que H10 esté aceptado**. Los datos muestran problemas de contenido que deben resolverse antes del cierre.

#### 1. Las 209 flags de calidad requieren análisis

El auditor produjo una bandera para cada uno de los 209 registros. Esto indica que el feed descubierto todavía no dispone de la evidencia mínima necesaria para tratar esos registros como recomendaciones maduras.

#### 2. No se generaron hipótesis

`atlas_hypotheses.csv` contiene 0 hipótesis estructuradas. Esto significa que la nueva capa de hipótesis todavía no está aportando conocimiento accionable al pipeline.

#### 3. La matriz hardware produjo 0 filas

El Run #6 generó:

```text
Matrix: 0 recommendation rows
```

La revisión del código detectó una incompatibilidad de identificadores: la matriz construía perfiles como `intel-i5-16gb`, mientras que el recomendador utiliza identificadores canónicos del tipo `cpu-i5-16gb`. Además, una combinación CPU+GPU solo debe publicarse cuando existe evidencia para ese perfil combinado; no se debe reutilizar una medición GPU-only y presentarla como una medición CPU+GPU.

Se corrigió `scripts/atlas_hardware_matrix.py` para alinear los identificadores y exigir coincidencia exacta de perfiles combinados.

**Commit:** `1fb6a67eb867bf3b7fbe14cccb94fbe06ab7637c`.

#### 4. El enriquecedor estaba convirtiendo `fit_score` en CABE

El código anterior hacía:

```text
fit_score → CABE estimado
```

Esto no es aceptable para el contrato de LEONES: CABE debe representar viabilidad hardware-modelo y no debe aparecer como una simple traducción de un score compuesto.

También se estaba asignando `evidence_state=reported` por defecto, aunque el registro procediese de un descubrimiento todavía no verificado.

Se corrigió el enriquecedor para que:

```text
CABE desconocido → unknown
RULA desconocido → unknown
JGB desconocido → unknown
estado de evidencia ausente → unknown
```

y para que no derive CABE desde `fit_score`.

**Commit:** `5be8dd2c74820cd6f35b2d78efebdd912431ecc3`.

## Advertencia de Node.js

El Run #6 ejecutó todavía:

```text
actions/checkout@v4
actions/setup-python@v5
```

GitHub mostró la advertencia de Node.js 20. El workflow ya fue actualizado posteriormente para utilizar las versiones actuales basadas en Node 24.

Esta advertencia no causó el fallo del Run #6, porque el run terminó correctamente.

## Estado después del Run #6

```text
PIPELINE E2E                 🟢 demostrado
PUBLICACIÓN ROBUSTA          🟢 demostrado
VALIDACIÓN ESTRUCTURAL       🟢 demostrada
CALIDAD DE DATOS             🟡 insuficiente
HIPÓTESIS                    🔴 0
MATRIZ HARDWARE              🔴 corregir/repetir
CABЕ/RULA/EVIDENCIA          🟡 contrato endurecido, repetir
RECOMENDACIONES              🟡 generadas pero no aceptables aún
ACEPTACIÓN H10               🔴 NO ACEPTADA
```

## Próxima prueba válida

La siguiente ejecución debe partir de los commits que corrigen el contrato:

```text
5be8dd2  → enriquecimiento no inferencial
1fb6a67  → identificadores de matriz hardware
```

Además deberá comprobarse la actualización de las Actions para eliminar la advertencia de Node.js.

La próxima ejecución deberá demostrar especialmente:

```text
209 descubrimientos
      ↓
clasificación de calidad
      ↓
¿cuántos son realmente utilizables?
      ↓
hipótesis > 0 cuando exista evidencia suficiente
      ↓
matriz hardware con perfiles reales
      ↓
recomendaciones con campos técnicos coherentes
      ↓
CABE explícito o unknown
      ↓
evidence_state correcto
      ↓
RULA explícito o unknown
      ↓
publicación
```

## Criterio de éxito

El éxito no significa que todos los campos estén rellenos. Significa que:

1. el contrato se cumple;
2. los datos existentes sobreviven;
3. los datos desconocidos permanecen desconocidos;
4. las inferencias prohibidas no aparecen;
5. la matriz representa perfiles reales;
6. las recomendaciones distinguen evidencia de estimación;
7. el workflow puede repetirse diariamente.

## Cierre

**No marcar H10 como terminado todavía.**

El Run #6 demuestra que el pipeline funciona como infraestructura, pero todavía no demuestra que la salida sea suficientemente buena como conocimiento Atlas/recomendación.

La siguiente ejecución debe validar las correcciones de contenido antes de considerar H10 **ACEPTADA**.
