# Fase H10 — Atlas → recomendador diario enriquecido

**Estado: 🟢 ACEPTADA**

## 1. Objetivo

Convertir la generación diaria de recomendaciones del Atlas en un proceso automático, trazable y resistente a errores que conecte prospección, evidencia, ingesta, matriz, recomendador, enriquecimiento, validación y publicación.

## 2. Qué queda aceptado

H10 queda aceptada porque el workflow diario ejecutó de extremo a extremo todos los pasos críticos y la salida superó los controles funcionales definidos:

- prospección e ingesta completadas;
- evidencia externa y técnica generadas;
- clasificación T0/T1/T2/T3 funcionando;
- auditoría de calidad ejecutada;
- matriz hardware no vacía;
- recomendaciones CPU/RAM y GPU generadas;
- enriquecimiento no destructivo ejecutado;
- validación de columnas críticas superada;
- publicación en `main` completada.

## 3. Evidencia de aceptación — Run #18

**Workflow:** `Atlas — Pipeline diario completo`  
**Run ID:** `31912695040`  
**Commit ejecutado:** `a3c6631cb8588b7d11679358b61f2e553eed2a44`

urlRun #18 en GitHub Actionshttps://github.com/robertosantosx2/LEONES/actions/runs/31912695040

### Resultados observados

```text
209 modelos ingeridos
172 repositorios canónicos
209 registros requieren verificación
67 registros en cola de evidencia externa
39/209 con evidencia técnica reportada
T0 = 187
T1 = 5
T2 = 17
T3 = 0
209 flags de calidad
0 hipótesis estructuradas
32.128 filas de matriz hardware
59 ficheros de recomendaciones validados
859 filas de recomendaciones validadas
```

## 4. Criterios de aceptación

| ID | Criterio | Resultado |
|---|---|---|
| V1 | Workflow arranca | 🟢 |
| V2 | Prospección e ingesta completan | 🟢 |
| V3 | Evidencia técnica se genera | 🟢 |
| V4 | T0/T1/T2/T3 se calculan | 🟢 |
| V5 | Matriz hardware no vacía | 🟢 32.128 filas |
| V6 | Recomendaciones no vacías | 🟢 859 filas validadas |
| V7 | Columnas críticas presentes | 🟢 |
| V8 | Enriquecimiento no destructivo | 🟢 |
| V9 | JGB/CABE/RULA no se sustituyen por un score único | 🟢 |
| V10 | Rendimiento no se inventa | 🟢 |
| V11 | Publicación resistente a concurrencia | 🟢 |
| V12 | Actions actualizadas | 🟢 |

## 5. Arquitectura aceptada

```text
PROSPECCIÓN → EVIDENCIA → INGESTA → QA → EVIDENCIA TÉCNICA
                                      ↓
                                   T0/T1/T2/T3
                                      ↓
                               MATRIZ HARDWARE
                                      ↓
                                RECOMENDADOR
                               ↙     ↓      ↘
                             JGB   CABE     RULA
                                      ↓
                              ENRIQUECIMIENTO
                                      ↓
                                  VALIDACIÓN
                                      ↓
                                  PUBLICACIÓN
```

## 6. Contrato T0/T1/T2/T3

- **T0:** no existe evidencia técnica estructurada suficiente.
- **T1:** existe identidad técnica útil.
- **T2:** existe evidencia suficiente para iniciar evaluación de viabilidad.
- **T3:** T2 más rendimiento observado con evidencia identificable.

No se sustituye esta clasificación por un score.

## 7. Contexto

El proyecto distingue `context_supported`, `context_target` y `context_recommended`. Si el contexto no está demostrado, se conserva `unknown`.

## 8. Invariantes

1. JGB es independiente de rendimiento, precio y hardware.
2. CABE no implica RULA.
3. No se inventa rendimiento.
4. Evidencia externa no equivale a medición LEONES.
5. Una matriz vacía es FAIL.
6. Recomendaciones vacías son FAIL.
7. El enriquecimiento no destruye columnas existentes.
8. La incertidumbre forma parte del dato.
9. Hardware y runtime son dimensiones explícitas.
10. La publicación debe resistir concurrencia.

## 9. Limitaciones que permanecen abiertas

Aceptar H10 **no significa que todo el sistema de recomendación esté terminado**. Siguen abiertas la cobertura completa del Atlas, JGB sistemático, CABE/RULA con mediciones reales, benchmarks reproducibles, evaluación agentiva, router dinámico, TCO y optimización multiobjetivo.

## 10. Documentación relacionada

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`DECISIONS.md`](DECISIONS.md)
- [`VALIDATION.md`](VALIDATION.md)
- **Guía pedagógica de mantenimiento:** [`../../completed/H10-ATLAS-RECOMMENDER-PIPELINE.md`](../../completed/H10-ATLAS-RECOMMENDER-PIPELINE.md)
- [`../../RESULT_SCHEMA.md`](../../RESULT_SCHEMA.md)

## 11. Trazabilidad de código

- Workflow: `.github/workflows/atlas-pipeline.yml`
- Matriz: `scripts/atlas_hardware_matrix.py`
- Recomendador: `scripts/atlas_recommend_from_feed.py`
- Ranking económico: `scripts/atlas_economic_rank.py`
