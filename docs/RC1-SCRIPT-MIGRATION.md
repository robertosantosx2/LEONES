# RC1 — Scripts mínimos, claros y reutilizables

> **Estado: vigente para Release Candidate 1.**
>
> LEONES no gana calidad por tener más scripts. Gana calidad cuando cada script necesario tiene una responsabilidad pequeña, una interfaz explícita, evidencia trazable y documentación suficiente para que otra persona pueda usarlo sin conocer el historial del proyecto.

## 1. Objetivo

RC1 consolida el principio:

> **mínimo código necesario + máxima documentación útil + cero duplicación funcional.**

La limpieza no consiste en reescribir todo el repositorio. Consiste en identificar el camino mínimo que necesita la versión operativa, reutilizar las piezas que ya resuelven ese problema y retirar del camino principal lo que pertenece a arquitecturas anteriores.

La investigación, Atlas, el conocimiento y sus fuentes **no se eliminan**. Permanecen como infraestructura de conocimiento y pueden alimentar el núcleo cuando aporten valor.

## 2. Núcleo operativo RC1

El recorrido mínimo que queremos poder ejecutar es:

```text
hardware_profile
      ↓
LLMFit / fuentes de fit
      ↓
selection_pipeline
      ↓
plan de runtime autorizado
      ↓
runtime existente (ODS/Magnitude cuando corresponda)
      ↓
medición LEONES
      ↓
evidencia
      ↓
MANADA
```

`llama.cpp` permanece como runtime físico de referencia para validar el contrato de medición y como fallback técnico de bajo nivel. No se convierte en un sistema de recomendación paralelo.

### Piezas que se consideran reutilizables en RC1

| Pieza | Responsabilidad | Estado |
|---|---|---|
| `scripts/hardware_profile.py` | observar el hardware local | núcleo |
| `scripts/selection_pipeline.py` | convertir hardware + conocimiento + fit en un plan | núcleo |
| `scripts/runtimes/llama_cpp_adapter.py` | traducir un plan autorizado a llama.cpp | núcleo de medición |
| `scripts/runtimes/run_llama_cpp_selected.py` | ejecutar un plan ya autorizado | núcleo de medición |
| `scripts/runtime_benchmark_evidence.py` | validar/conservar evidencia de benchmark | núcleo de evidencia |
| `scripts/check_script_quality.py` | impedir que la limpieza se degrade | herramienta de mantenimiento |

Esta lista es deliberadamente corta. Un script no entra en el núcleo porque exista: entra porque una dependencia real del recorrido RC1 lo necesita.

## 3. Qué significa "esplendoroso"

Un script reutilizado en RC1 debe cumplir simultáneamente:

1. **Responsabilidad única.** Su nombre y su primera documentación deben decir qué problema resuelve.
2. **Interfaz visible.** Los argumentos, entradas y salidas deben poder entenderse sin leer toda la implementación.
3. **Comentarios con criterio.** Se explica el porqué de decisiones no obvias; no se llena el código de comentarios redundantes.
4. **Sin magia.** No instala paquetes, descarga modelos, publica datos ni cambia el repositorio salvo que esa sea precisamente su responsabilidad.
5. **Sin duplicación.** Si otra pieza ya conoce una regla, el script la reutiliza.
6. **Errores útiles.** Un fallo debe indicar qué contrato no se cumple y qué revisar.
7. **Datos honestos.** `estimated`, `reported`, `observed`, `measured` y `verified` nunca se mezclan.
8. **Determinismo razonable.** A igualdad de entradas y entorno, el script debe producir el mismo tipo de resultado.
9. **Pruebas.** Todo comportamiento modificado conserva o amplía sus pruebas.
10. **Documentación externa.** `scripts/README.md` explica el papel del script dentro del recorrido, mientras el propio script explica su contrato local.

## 4. Regla especial para medición

Los scripts de medición tienen una frontera estricta:

```text
selección ≠ ejecución ≠ medición ≠ evidencia ≠ publicación
```

El selector puede decidir qué probar. No puede fingir que lo ha medido.

El runner puede ejecutar. No puede convertir automáticamente cualquier salida en `verified`.

El registrador puede conservar. No puede fabricar una ejecución que no ocurrió.

La publicación debe consumir evidencia aceptada y nunca sustituirla.

## 5. Qué pasa a `deprecated`

No se borrará código histórico simplemente porque no sea necesario para RC1.

La política es:

```text
NO ES NÚCLEO RC1
       ↓
¿tiene consumidor activo?
   ├── sí → conservar fuera del camino mínimo
   └── no
       ↓
¿es histórico o experimental valioso?
   ├── sí → mover a deprecated con nota de procedencia
   └── no → eliminar solo con evidencia de que no tiene consumidores
```

El movimiento a `deprecated` debe ser trazable y acompañado de una nota que indique:

- por qué deja de ser núcleo;
- qué pieza lo sustituye, si existe;
- si conserva valor histórico;
- qué pruebas o consumidores siguen dependiendo de él;
- y qué condición permitiría recuperarlo.

**No se hará una gran mudanza destructiva en una sola operación.** La migración será incremental para que CI pueda demostrar que no se rompe el camino operativo.

## 6. No duplicar ODS ni Magnitude

RC1 no construye un runtime/agente alternativo para competir con los proyectos que ya aportan esa capacidad.

La frontera es:

```text
LEONES
  ├─ conocimiento / Atlas
  ├─ hardware / LLMFit
  ├─ decisión de qué probar
  ├─ medición independiente
  └─ evidencia y publicación

ODS / Magnitude
  └─ capacidades de ejecución que realmente aporten upstream
```

Hermes se conserva donde ODS ya lo utilice. AirLLM y FreeToken se estudiarán posteriormente como aportaciones upstream o conectores, no como una tercera arquitectura paralela de LEONES.

## 7. Documentación interna y externa

Cada script del núcleo debe tener:

### Dentro del `.py`

- propósito;
- entradas;
- salidas;
- límites;
- decisiones no obvias;
- errores de contrato importantes.

### En `README.md`

- para qué sirve dentro de LEONES;
- cuándo usarlo;
- cuándo **no** usarlo;
- ejemplo mínimo;
- formato de salida;
- dependencia del siguiente paso;
- enlace a su contrato o evidencia.

La documentación no debe repetir literalmente todo el código. Debe explicar el modelo mental que permite utilizarlo correctamente.

## 8. Criterio de cierre de una pieza

Una pieza queda "limpia, fija y con esplendor" cuando:

```text
responsabilidad clara
        +
interfaz explícita
        +
comentarios de diseño útiles
        +
README operativo
        +
pruebas
        +
ningún consumidor accidental
        =
PIEZA RC1 ACEPTADA
```

Si para entender un script hay que reconstruir la historia de LEONES, todavía no está limpio.

## 9. Regla de trabajo a partir de ahora

Antes de crear un script nuevo se debe responder:

1. ¿Qué pregunta concreta no responde ya una pieza existente?
2. ¿Podemos reutilizar una función o módulo sin crear otra capa?
3. ¿Es parte del núcleo RC1 o una herramienta auxiliar?
4. ¿Qué entrada y salida tendrá?
5. ¿Cómo se probará sin hardware físico?
6. ¿Qué parte necesitará Ubuntu para validarse realmente?

Si la respuesta a la primera pregunta es "ninguna", **no se crea el script**.

## 10. Principio de cierre

> **LEONES debe contener el mínimo código que hace falta para unir conocimiento, decisión, ejecución medida y evidencia. Todo lo demás debe ser conocimiento reutilizable, integración externa o historia documentada; nunca complejidad accidental.**
