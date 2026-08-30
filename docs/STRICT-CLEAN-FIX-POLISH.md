# LEONES — `-strict-`: limpiar, fijar y dar esplendor

## Propósito

Esta es una regla operativa del proyecto, no una sugerencia de estilo. Cuando una tarea se marque como `-strict-`, el trabajo debe terminar con una base coherente, verificable, explicada y reproducible.

## 1. Limpiar

**Limpiar** significa quitar lo que ya no aporta valor o puede inducir a error:

- duplicaciones de contratos, esquemas o lógica;
- nombres antiguos que contradigan el contrato vigente;
- scripts que hagan lo mismo por caminos distintos;
- restos de experimentos o soluciones temporales;
- comprobaciones que confundan estimación, observación, medición y evidencia;
- documentación que describa un flujo distinto del código real.

La limpieza no debe borrar evidencia histórica válida. La evidencia se conserva; lo que se elimina es la ambigüedad.

## 2. Fijar

**Fijar** significa convertir la decisión correcta en algo comprobable:

1. contrato canónico;
2. esquema cuando corresponda;
3. implementación mínima;
4. prueba automática;
5. invariante arquitectónica;
6. auditoría ejecutable;
7. evidencia cuando la operación sea física.

Un bloque no se considera cerrado sólo porque una prueba aislada pase.

## 3. Dar esplendor

**Dar esplendor** significa que otra persona pueda entender y utilizar el sistema sin reconstruir nuestra conversación.

### Documentación interna

Los comentarios deben explicar el **porqué**, no repetir línea por línea el código. Cuando una decisión pueda resultar extraña para alguien con pocos conocimientos de programación, el comentario debe explicar:

- qué problema resuelve;
- qué contrato está reutilizando;
- qué no debe hacer ese componente;
- qué pasaría si se introdujera una segunda lógica paralela.

### Documentación externa

Cada puerta de usuario debe tener documentación Markdown que explique, como mínimo:

- para qué sirve;
- cómo ejecutarla;
- qué entrada necesita;
- qué salida produce;
- cómo interpretar los estados;
- qué cosas **no** demuestra;
- cuándo hace falta hardware real.

## 4. Regla de arquitectura

LEONES debe reutilizar los contratos existentes. No se crea una segunda calculadora de scoring, benchmark, ranking o medición para resolver un problema que ya tiene una capa canónica.

La cadena debe conservar la separación:

```text
fuente / estimación
        ↓
decisión canónica
        ↓
selección de runtime
        ↓
ejecución real
        ↓
medición
        ↓
evidencia
        ↓
recomendación
        ↓
salida
        ↓
traza E2E
```

Cada capa transporta o valida la información que le corresponde; no sustituye silenciosamente a otra.

## 5. Auditoría estricta

Antes de cerrar un bloque `-strict-`:

```bash
git status --short
pytest -q
git diff --check
```

Después deben revisarse también los auditores de los jalones afectados. Si un auditor deja cambios de trabajo, hay que decidir explícitamente si esos cambios son evidencia que debe conservarse o un efecto no deseado que debe corregirse.

Los runners de auditoría deben ser idempotentes: ejecutarlos dos veces sobre la misma base no debe introducir diferencias funcionales espurias.

## 6. Criterio de cierre

Un bloque `-strict-` queda cerrado cuando:

- el contrato canónico está identificado;
- no existen duplicaciones funcionales conocidas;
- las invariantes importantes están automatizadas;
- las pruebas pasan;
- `git diff --check` pasa;
- la documentación describe el código real;
- los comentarios explican las decisiones difíciles;
- la evidencia física, si existe, conserva su procedencia;
- el árbol de trabajo queda limpio después de la auditoría y de conservar deliberadamente la evidencia necesaria.

## Aplicación desde el 27 de agosto de 2026

Esta regla se aplica al trabajo realizado desde el 27 de agosto de 2026 y a todo trabajo posterior cuando el usuario solicite literalmente **«limpia, fija y da esplendor»** o marque una tarea como **`-strict-`**.

La prioridad es siempre: **primero coherencia, después cierre, después siguiente jalón**.
