# Validación — Atlas → recomendador diario enriquecido

**Estado: 🟡 PROVISIONAL / EN VALIDACIÓN**

## Criterios de aceptación

| ID | Criterio | Estado |
|---|---|---|
| V1 | El workflow arranca | 🟢 |
| V2 | Prospección e ingesta completan | 🟢 en run #4, pero sobre versión anterior |
| V3 | Se generan recomendaciones | 🟡 run #4 generó ficheros, pero 0 filas; repetir con workflow actual |
| V4 | El merge conserva columnas previas | ⏳ |
| V5 | Aparecen columnas nuevas críticas | ⏳ — #4 era anterior a este paso |
| V6 | JGB no se deriva de rendimiento | ⏳ |
| V7 | RULA no se deriva de CABE | ⏳ |
| V8 | No se inventa rendimiento | ⏳ |
| V9 | Publicación final correcta | 🔴 #4 falló en `git push` por divergencia de `main` |
| V10 | No hay pérdida de información | ⏳ |

## Ejecución #4 — resultado y diagnóstico

- **Workflow:** `Atlas — Pipeline diario completo`
- **Run:** `#4`
- **Run ID:** `31878387802`
- **Job ID:** `95052258510`
- **Conclusión:** `failure`
- **Duración:** aproximadamente 1m 44s.
- **Commit que el runner obtuvo:** `44086b8d97093d3e2be3c10e3bb12a80c0d59255`.

### Qué funcionó

Checkout, Python, ingesta, matriz NVIDIA y perfiles CPU/RAM terminaron correctamente. La ingesta informó:

```text
Atlas ingest: 209 model records; 209 require verification
```

La matriz informó:

```text
Matrix: 0 recommendation rows
```

Los perfiles CPU × RAM también devolvieron `0 recommendations`.

### Causa inmediata del fallo

El fallo que hizo terminar el job en rojo **no fue un error de Python ni del runner**. Se produjo al publicar:

```text
! [rejected] main -> main (fetch first)
error: failed to push some refs to 'https://github.com/robertosantosx2/LEONES'
hint: Updates were rejected because the remote contains work that you do not have locally.
```

El runner creó localmente:

```text
20a867b feat: ampliar matriz CPU RAM NVIDIA para IA
```

pero no pudo publicarlo porque `main` había avanzado mientras la ejecución estaba esperando/ejecutándose.

### Por qué ocurrió

La ejecución #4 utilizó una versión anterior del workflow. El runner hizo checkout del commit `44086b8...`. Después se incorporó al workflow la solución para publicación concurrente, mediante `git fetch origin main`, `git rebase origin/main` y reintentos de `git push`.

La versión actual de `.github/workflows/atlas-pipeline.yml` ya contiene esa protección y además las fases de evidencia externa, auditoría, hipótesis, enriquecimiento y validación de columnas.

Por tanto, **#4 no constituye una validación de la arquitectura completa actual**.

## Incidencia secundaria: cero recomendaciones

El run #4 produjo `0 recommendation rows` tanto en la matriz como en los perfiles CPU/RAM.

Es una señal que debe investigarse, pero no debe corregirse inventando recomendaciones. #4 se ejecutó con una versión anterior del pipeline que no contenía todavía el flujo completo:

```text
Prospección
   ↓
Evidencia externa
   ↓
Ingesta
   ↓
Evidencia externa regenerada
   ↓
Auditoría de calidad
   ↓
Hipótesis
   ↓
Matriz hardware
   ↓
Recomendaciones
   ↓
Enriquecimiento
   ↓
Validación
   ↓
Publicación robusta
```

Hay que repetir con el workflow actual y observar cuántos candidatos pasan realmente los filtros de evidencia/viabilidad.

## Prueba específica del enriquecedor

Entrada:

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

## Resultado esperado

El éxito significa que:

1. el contrato se cumple;
2. los datos existentes sobreviven;
3. los desconocidos permanecen desconocidos;
4. no aparecen inferencias prohibidas;
5. el workflow puede repetirse diariamente;
6. los resultados pueden publicarse aunque haya commits concurrentes en `main`.

## Siguiente ejecución obligatoria

**No conviene simplemente reejecutar el job #4 antiguo.** Debe ejecutarse el workflow actual desde `main`, porque #4 utilizó el commit anterior al cambio que incorporó enriquecimiento, validación y publicación robusta.

Procedimiento:

1. GitHub → **Actions**.
2. Seleccionar **Atlas — Pipeline diario completo**.
3. Pulsar **Run workflow**.
4. Seleccionar `main`.
5. Lanzar la ejecución.
6. Revisar especialmente `Auditar calidad del feed`, `Generar hipótesis desde evidencia empírica`, la matriz, los perfiles CPU/RAM, el enriquecimiento, la validación de columnas y `Publicar resultados sin perder commits concurrentes`.

## Cierre

Cuando la nueva ejecución termine, este documento debe actualizarse con conclusión, modelos descubiertos/ingeridos, recomendaciones generadas, ficheros enriquecidos, validación de columnas, resultado del push, commit publicado, incidencias y criterio final **ACEPTADA / NO ACEPTADA**.

Hasta entonces, **no marcar la fase como terminada**.
