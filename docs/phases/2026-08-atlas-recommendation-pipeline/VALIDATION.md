# Validación — H10 Atlas → recomendador diario enriquecido

**Estado: 🟢 ACEPTADA**

## 1. Criterios de aceptación

| ID | Criterio | Evidencia | Estado |
|---|---|---|---|
| V1 | El workflow arranca | Run #18 con runner asignado | 🟢 |
| V2 | Prospección e ingesta completan | pasos verdes; 209 modelos | 🟢 |
| V3 | Evidencia técnica se genera | 39/209 reportados; T0=187, T1=5, T2=17, T3=0 | 🟢 |
| V4 | Matriz hardware no vacía | 32.128 filas | 🟢 |
| V5 | Recomendaciones no vacías | 59 ficheros, 859 filas validadas | 🟢 |
| V6 | Columnas críticas presentes | validación automática | 🟢 |
| V7 | Enriquecimiento ejecutado | candidatos enriquecidos en los 59 ficheros | 🟢 |
| V8 | JGB/CABE/RULA independientes | contrato y código revisados | 🟢 |
| V9 | No se inventa rendimiento | contrato de evidencia y estados | 🟢 |
| V10 | Publicación resistente a concurrencia | fetch + rebase + retry; push correcto | 🟢 |
| V11 | Actions actualizadas | checkout@v7 + setup-python@v7 | 🟢 |
| V12 | Resultado publicado | `Atlas publicado correctamente` | 🟢 |

## 2. Ejecución de cierre

### Run #18

- **Workflow:** `Atlas — Pipeline diario completo`
- **Run ID:** `31912695040`
- **Commit de entrada:** `a3c6631cb8588b7d11679358b61f2e553eed2a44`
- **Commit publicado por el workflow:** `2d0deed`

urlRun #18 en GitHub Actionshttps://github.com/robertosantosx2/LEONES/actions/runs/31912695040

### Evidencia técnica

```text
Technical evidence: reported=39/209
T0=187
T1=5
T2=17
T3=0
```

Esto demuestra que el sistema mantiene perfiles T2 incluso cuando el contexto no está completo y permite que la capa posterior decida la recomendación concreta.

### Matriz

```text
Matrix: 32128 recommendation rows
Filas de matriz hardware: 32128
```

La condición de fallo de matriz vacía se ejecutó y no se activó.

### Perfiles CPU/RAM

La ejecución generó recomendaciones para todos los perfiles de familias Intel i3/i5/i7/i9 y AMD Ryzen 3/5/7/9 en 2/4/8/16/32/64/128 GB. El número de candidatos varió según la configuración: 5, 15, 16 o 17 en los perfiles generales de la ejecución.

### Perfiles específicos conservados

La ejecución también enriqueció perfiles concretos existentes, incluyendo `cpu-i5-16gb`, `cpu-i7-64gb` y `rtx4060-8gb`, con 9 candidatos en cada uno en esta ejecución.

### Validación estructural

```text
OK: 59 ficheros de recomendaciones validados; 859 filas
```

La validación exigió como mínimo:

```text
cabe
cabe_status
rula
rula_status
jgb_status
evidence_state
evidence_type
uncertainty
```

## 3. Publicación

El workflow realizó:

```text
git add
    ↓
git commit
    ↓
git fetch origin main
    ↓
git rebase origin/main
    ↓
git push origin HEAD:main
```

Resultado:

```text
Atlas publicado correctamente
```

## 4. Incidencias resueltas durante la validación

### A — Matriz vacía
Se endureció el pipeline para que cero filas sea fallo explícito.

### B — Hardware compuesto
Se corrigió la compatibilidad entre perfiles hardware compuestos y hardware específico del feed.

### C — Contexto
Se separó `context_supported` de `context_target` y se calculó `context_recommended` sin inventar capacidad.

### D — T2 sin contexto
T2 puede alimentar la evaluación preliminar sin fabricar contexto. Cuando falta, permanece `unknown`.

### E — Publicación concurrente
Se incorporó rebase/retry para evitar falsos fallos por avance de `main`.

### F — Actions Node.js
El run de cierre confirma `actions/checkout@v7` y `actions/setup-python@v7`.

## 5. Lo que queda demostrado

H10 demuestra que existe una infraestructura automática diaria capaz de:

1. descubrir y reunir modelos;
2. construir evidencia;
3. ingerirla;
4. clasificar evidencia técnica;
5. auditar calidad;
6. construir hipótesis cuando las hay;
7. construir la matriz hardware;
8. generar recomendaciones;
9. enriquecerlas sin destruir la información existente;
10. validar el contrato de salida;
11. publicar los resultados de forma resistente a concurrencia.

## 6. Lo que no queda demostrado

El cierre de H10 no significa que:

- todos los modelos estén empíricamente benchmarkeados;
- T3 tenga cobertura amplia;
- CABE/RULA sean mediciones físicas completas;
- todas las recomendaciones sean equivalentes a una prueba de ejecución real;
- el Atlas tenga cobertura definitiva;
- JGB esté sistemáticamente completo;
- el ranking multiobjetivo final esté terminado.

Estas cuestiones pertenecen a hitos posteriores.

## 7. Resultado

```text
H10 = 🟢 ACEPTADA
```

La aceptación se basa en la ejecución real del Run #18 y no solamente en que el workflow haya terminado con código de salida 0.
