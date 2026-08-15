# Fase H10 — Atlas → recomendador diario enriquecido

**Estado: 🟢 ACEPTADA**

## 1. Objetivo

Convertir la generación diaria de recomendaciones del Atlas en un proceso automático, trazable y resistente a errores que conecte:

```text
Prospección
    ↓
Evidencia externa
    ↓
Ingesta
    ↓
Evidencia técnica
    ↓
Calidad
    ↓
Hipótesis
    ↓
Matriz CPU × RAM × NVIDIA
    ↓
Recomendador
    ↓
Enriquecimiento
    ↓
Validación
    ↓
Publicación
```

La fase no pretende demostrar que todos los valores estén medidos experimentalmente. Conserva estados como `unknown`, `reported`, `reproducible` y `verified` y no convierte ausencia de evidencia en falsa precisión.

## 2. Qué queda aceptado

H10 queda aceptada porque el workflow diario ejecutó de extremo a extremo todos los pasos críticos y la salida superó los controles funcionales definidos:

- prospección e ingesta completadas;
- evidencia externa generada;
- evidencia técnica generada;
- clasificación T0/T1/T2/T3 funcionando;
- auditoría de calidad ejecutada;
- hipótesis ejecutadas, aun con 0 hipótesis estructuradas en esta ejecución;
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

El runner utilizó `actions/checkout@v7` y `actions/setup-python@v7`, eliminando la advertencia anterior asociada a Node.js 20 en las acciones usadas.

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

El workflow publicó sus resultados correctamente en `main` mediante el mecanismo de `fetch + rebase + retry`.

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
| V9 | JGB/CABE/RULA no se sustituyen por un score único | 🟢 contrato documentado |
| V10 | Rendimiento no se inventa | 🟢 |
| V11 | Publicación resistente a concurrencia | 🟢 |
| V12 | Actions actualizadas | 🟢 checkout/setup-python v7 |

## 5. Arquitectura aceptada

```text
                         LEONES / ATLAS
                               │
                         PROSPECCIÓN
                               │
                               ▼
                      EVIDENCIA EXTERNA
                               │
                               ▼
                            INGESTA
                               │
                               ▼
                         CALIDAD / QA
                               │
                               ▼
                         EVIDENCIA TÉCNICA
                               │
                       ┌───────┴────────┐
                       │ T0/T1/T2/T3    │
                       └───────┬────────┘
                               │
                               ▼
                       MATRIZ HARDWARE
                 CPU × RAM × NVIDIA / VRAM
                               │
                               ▼
                         RECOMENDADOR
                               │
                   ┌───────────┼───────────┐
                   ▼           ▼           ▼
                  JGB        CABE        RULA
                   │           │           │
                   └───────────┼───────────┘
                               ▼
                  rendimiento / memoria /
                  runtime / evidencia /
                     incertidumbre
                               │
                               ▼
                       ENRIQUECIMIENTO
                         NO DESTRUCTIVO
                               │
                               ▼
                          VALIDACIÓN
                               │
                               ▼
                          PUBLICACIÓN
```

## 6. Contrato T0/T1/T2/T3

### T0
No existe evidencia técnica estructurada suficiente.

### T1
Existe identidad técnica útil: arquitectura, parámetros, contexto, runtime, backend u otra señal equivalente. No implica viabilidad hardware.

### T2
Existe evidencia suficiente para iniciar una evaluación de viabilidad, especialmente tamaño observado de pesos y runtime. El contexto no es requisito para alcanzar T2.

### T3
T2 más rendimiento observado con evidencia identificable.

```text
T0 → T1 → T2 → T3
```

No se sustituye esta clasificación por un score.

## 7. Semántica de contexto

El proyecto distingue:

```text
context_supported
    ↓
capacidad demostrada del modelo

context_target
    ↓
objetivo del perfil hardware/uso

context_recommended
    ↓
min(context_supported, context_target)
```

Por ello un modelo que demuestra 8K puede recomendarse en un equipo cuyo objetivo sea 16K a 8K. No se afirma que soporte 16K.

Cuando el contexto no está demostrado, se conserva `unknown`; no se fabrica el valor.

## 8. Invariantes

1. **JGB es independiente** de rendimiento, precio y hardware.
2. **CABE no implica RULA.**
3. **No se inventa rendimiento.**
4. **Evidencia externa no equivale a medición LEONES.**
5. **La matriz vacía es un FAIL.**
6. **Las recomendaciones vacías son un FAIL.**
7. **El enriquecimiento no destruye columnas existentes.**
8. **La incertidumbre forma parte del dato.**
9. **Hardware y runtime son dimensiones explícitas.**
10. **La publicación debe ser resistente a concurrencia.**

## 9. Incidencias que dieron lugar al diseño final

### I1 — Matriz vacía
La primera ejecución E2E podía terminar con 0 filas de matriz. Se convirtió en condición explícita de fallo.

### I2 — Compatibilidad de hardware compuesto
Los perfiles compuestos podían no coincidir exactamente con identificadores específicos del feed. Se ajustó la compatibilidad sin perder la identidad del perfil completo.

### I3 — Contexto confundido con capacidad del hardware
Se exigía que el modelo soportara el máximo contexto objetivo del perfil. Se separaron capacidad demostrada y objetivo de configuración.

### I4 — T2 sin contexto
T2 no exige contexto. Se ajustó el recomendador para permitir recomendaciones preliminares con contexto `unknown`, manteniendo la incertidumbre.

### I5 — Carrera de publicación
La publicación directa podía fallar si `main` avanzaba. Se incorporó `fetch + rebase + retry`.

### I6 — Advertencia de Node.js 20
Se actualizaron `actions/checkout` y `actions/setup-python` a v7.

## 10. Limitaciones que permanecen abiertas

Aceptar H10 **no significa que todo el sistema de recomendación esté terminado**.

Siguen abiertas:

- cobertura y depuración continua del Atlas;
- JGB sistemático completo;
- CABE/RULA con mediciones reales;
- benchmarks reproducibles en hardware real;
- calidad y cobertura de hipótesis;
- evaluación agentiva;
- router dinámico;
- optimización multiobjetivo;
- TCO y coste por tarea.

H10 demuestra la infraestructura diaria y el contrato entre capas. No demuestra que todas las recomendaciones sean equivalentes a benchmarks reales.

## 11. Cierre formal

```text
IMPLEMENTAR   🟢
     ↓
VALIDAR       🟢
     ↓
ACEPTAR       🟢
     ↓
DOCUMENTAR    🟢
     ↓
ENLAZAR       🟢
     ↓
H10 CERRADA   🟢
```

**H10 queda oficialmente ACEPTADA.**

## 12. Próximo hito

La siguiente prioridad del roadmap es **H06 — Open LLM Atlas ampliado**, porque la calidad, cobertura, procedencia y estructura del conocimiento del Atlas son la base sobre la que se apoyan las siguientes capas de JGB, hardware y recomendación.

H10 queda como infraestructura operativa diaria que alimentará esa evolución.

## Trazabilidad

- Workflow: `.github/workflows/atlas-pipeline.yml`
- Evidencia técnica: `scripts/atlas_technical_evidence.py`
- Matriz: `scripts/atlas_hardware_matrix.py`
- Recomendador: `scripts/atlas_recommend_from_feed.py`
- Enriquecedor: `scripts/atlas_recommendation_enrich.py`
- Esquema: `atlas/schema.json`
- Protocolo: `docs/DOCUMENTATION_PROTOCOL.md`
- Decisiones: [`DECISIONS.md`](DECISIONS.md)
- Arquitectura: [`ARCHITECTURE.md`](ARCHITECTURE.md)
- Validación: [`VALIDATION.md`](VALIDATION.md)
