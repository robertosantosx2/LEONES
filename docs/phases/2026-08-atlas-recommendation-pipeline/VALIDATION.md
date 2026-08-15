# Validación — Atlas → recomendador diario enriquecido

**Estado: 🟡 PROVISIONAL / EN VALIDACIÓN**

## Criterios de aceptación

La fase se podrá marcar como **ACEPTADA** cuando se cumplan todos los criterios siguientes:

| ID | Criterio | Evidencia requerida | Estado |
|---|---|---|---|
| V1 | El workflow arranca | GitHub Actions run con runner asignado | ✅ |
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

### Run #4

- **Workflow:** `Atlas — Pipeline diario completo`
- **Run:** `#4`
- **Run ID:** `31878387802`
- **Resultado:** ❌ fallo durante la publicación por carrera de Git.

La ejecución sí llegó a generar resultados, pero el `push` fue rechazado porque `main` había avanzado durante la ejecución. Esta incidencia motivó la incorporación del mecanismo de `fetch + rebase + retry` en el workflow.

### Run #5 — versión actual del pipeline

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

La causa se identificó en `scripts/prospectors/models.py`: escribía directamente en `data/discovery/models.json` sin crear previamente el directorio. El propio `repos.py` sí crea ese directorio, pero `models.py` es el primer prospector ejecutado y por tanto no podía depender de él. fileciteturn65file0L2-L5

### Corrección aplicada

Se corrigió `scripts/prospectors/models.py` para ejecutar:

```python
os.makedirs('data/discovery', exist_ok=True)
```

antes de escribir el resultado.

**Commit de corrección:** `2e76d6374c1f48c6fef9be70a4764055a52abe70`.

La corrección es de infraestructura del prospector y no altera el contrato de los datos descubiertos.

## Qué NO demuestra todavía el run #5

El run #5 **no permite evaluar todavía**:

- calidad de la prospección;
- ingesta Atlas;
- evidencia externa;
- auditoría;
- hipótesis;
- matriz hardware;
- recomendaciones;
- enriquecimiento;
- validación de columnas;
- publicación.

Todos esos pasos fueron omitidos porque GitHub Actions detuvo el job al fallar el primer prospector.

## Próxima prueba válida

Debe lanzarse una nueva ejecución manual desde `main` **después del commit `2e76d6374c1f48c6fef9be70a4764055a52abe70`**.

No debe hacerse simplemente `re-run` del run #5, porque un re-run repetiría el commit probado `e4bd724...` y volvería a utilizar el `models.py` defectuoso.

## Criterio de éxito de la próxima ejecución

```text
checkout actual
     ↓
models.py crea data/discovery
     ↓
prospectors completan
     ↓
evidencia
     ↓
ingesta
     ↓
calidad
     ↓
hipótesis
     ↓
hardware
     ↓
recomendaciones
     ↓
enriquecimiento
     ↓
validación
     ↓
publicación resistente a concurrencia
```

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
