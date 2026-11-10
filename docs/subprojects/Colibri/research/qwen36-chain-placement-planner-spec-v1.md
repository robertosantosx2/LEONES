# Especificación del planner de colocación atómica Qwen3.6 CUDA

**Versión:** 1.0.0  
**Fecha:** 2026-11-10  
**Estado:** diseño técnico para implementación; no es evidencia de ejecución.  
**Ámbito:** Colibrì, rama `research/qwen36-cuda-chain-planner`.  
**Registro de decisiones:** LEONES mantiene esta especificación y sus pruebas de aceptación; el runtime y los tests ejecutables viven en Colibrì.

## 1. Problema que resuelve

La cadena CUDA Qwen3.6 no puede construirse con una colección parcial de matrices. El setup selecciona un dispositivo a partir de la primera matriz aceptada y rechaza las siguientes si pertenecen a otro dispositivo. La cadena necesita las proyecciones obligatorias de todas las capas y `lm_head` co-localizadas.

El placement actual por ofertas individuales puede repartir matrices entre dispositivos o dejar una carga parcial cuando una subida falla. Por tanto, el éxito de una oferta individual no demuestra que exista una cadena utilizable.

**Regla de diseño:** la cadena es una unidad indivisible de admisión. Se calcula su coste total, se elige un único dispositivo y se confirma todo el grupo o no se confirma nada. Los expertos solo reciben el presupuesto residual después de las reservas obligatorias.

## 2. Invariantes normativos

1. **Single-device:** todas las matrices requeridas por la cadena y `lm_head` pertenecen al mismo dispositivo.
2. **All-or-nothing:** `chain_ready` solo puede pasar a true después de confirmar todas las asignaciones y validar el conjunto completo.
3. **Reserve-first:** KV/mirror, scratch, buffers de runtime y margen de seguridad se reservan antes de calcular el presupuesto de expertos.
4. **No overcommit:** ningún presupuesto puede exceder la memoria admisible reportada para el dispositivo.
5. **No partial residue:** si falla una asignación/subida, se liberan todos los recursos adquiridos por el intento de cadena.
6. **Fallback explicit:** si ningún dispositivo puede alojar el conjunto, la cadena permanece apagada y la inferencia continúa por la ruta fallback ya soportada.
7. **Manual placement respected:** no reinterpretar silenciosamente `COLI_PLACE`. Si una selección manual contradice la co-localización, se informa del conflicto y se aplica una política explícita (rechazar cadena o fallback), nunca se mezcla con una colocación parcial.
8. **Checked arithmetic:** cada suma de bytes debe comprobar overflow; ante overflow, el plan se rechaza.
9. **Deterministic plan:** mismos tamaños, reservas, dispositivos y política deben producir la misma decisión.
10. **No performance assumption:** chain-ready no implica que CUDA sea más rápido que CPU; la decisión de rendimiento sigue siendo medible y separada.

## 3. Inventario de recursos

El inventario se construye antes de modificar estado del runtime. Cada tensor requerido debe aportar:

- identificador estable (familia, capa, nombre de proyección);
- bytes exactos de almacenamiento CUDA;
- alineación y requisitos de tipo/layout;
- disponibilidad de fuente host;
- si es obligatorio para la cadena o condicional por configuración;
- estado de carga actual y dispositivo, si ya está residente.

El conjunto debe incluir todas las proyecciones que consulta `q36cc_setup()`: Q/K/V/O, proyecciones de atención/gate, `dnproj`, `dnout`, shared expert gate/up/down, extras de Muse cuando apliquen y `lm_head`. La lista final debe derivarse de las condiciones reales del código de la familia, no de una lista duplicada escrita a mano que pueda quedar obsoleta.

El inventario debe fallar cerrado si falta un tensor obligatorio, el tamaño no está disponible o el layout no puede ser aceptado por la cadena.

## 4. Modelo de presupuesto

Para cada dispositivo candidato `d`:

```text
usable(d) = max(free(d) - safety_margin(d) - existing_reservations(d), 0)

chain_need = checked_sum(bytes(t) for t in required_chain_tensors)

chain_scratch = scratch_requirement(context, batch, chain_rows)
chain_total = checked_add(chain_need, chain_scratch)

expert_budget(d) = max(
    usable(d) - chain_total - other_mandatory_reservations(d),
    0
)
```

La implementación debe evitar restas sin comprobar y no debe sumar primero margen+reservas si esa suma puede desbordar. Es preferible una resta secuencial saturada con comprobación de cada término.

El presupuesto de cadena debe reflejar las reservas reales del runtime. No contar dos veces una reserva que ya esté restada de `free(d)`; cada fuente de memoria debe tener una única propiedad/contabilidad documentada.

### 4.1 Orden de prioridad

1. memoria ya ocupada por el proceso y otras aplicaciones (reflejada en free);
2. reservas explícitas ya comprometidas;
3. margen de seguridad;
4. matrices obligatorias de cadena;
5. scratch/buffers que necesita la cadena;
6. KV/mirror u otros buffers obligatorios que deban coexistir;
7. expertos/caché oportunista.

Si el runtime necesita otro orden por dependencias reales, debe documentarlo y demostrar que el total sigue siendo admisible.

## 5. Selección de dispositivo

El planner evalúa todos los dispositivos candidatos sin realizar uploads. Un dispositivo es candidato válido si:

- el backend y la arquitectura soportan todos los kernels necesarios;
- todos los tensores requeridos tienen fuente válida y layout compatible;
- `chain_total` cabe en `usable(d)`;
- el dispositivo satisface restricciones explícitas del usuario.

Política determinista recomendada:

1. respetar una selección manual compatible;
2. descartar dispositivos no compatibles o sin capacidad;
3. elegir el dispositivo con mayor margen residual tras reservar la cadena;
4. desempatar por índice/UUID estable.

El criterio de mayor margen residual evita elegir un dispositivo que apenas cabe si otro deja más espacio para expertos y scratch futuro. No se debe optimizar por carga instantánea sin una métrica estable.

Si no hay candidato, devolver `NO_FIT` con diagnóstico por dispositivo: bytes libres, reserva existente, chain_need, scratch_need y déficit. No subir ninguna matriz.

## 6. Protocolo de admisión en dos fases

### Fase A — PLAN (sin efectos laterales)

Producir una estructura inmutable:

- `status`: `READY`, `NO_FIT`, `MISSING_TENSOR`, `UNSUPPORTED_LAYOUT`, `OVERFLOW` o `INVALID_CONFIG`;
- dispositivo elegido;
- lista completa y ordenada de tensores;
- bytes por tensor y total;
- reservas aplicadas;
- scratch calculado y parámetros que lo determinan;
- presupuesto residual para expertos;
- motivo de rechazo por candidato.

El plan no reserva memoria CUDA, no altera mapas de residencia y no cambia el estado de la cadena.

### Fase B — COMMIT (con rollback)

1. Mantener `chain_ready=false`.
2. Adquirir/reservar el presupuesto del dispositivo elegido.
3. Subir los tensores en orden determinista.
4. Registrar cada recurso adquirido en un journal local del intento.
5. Validar que cada tensor reside en el dispositivo elegido y que el conjunto requerido está completo.
6. Inicializar scratch/estado de la cadena.
7. Ejecutar la validación final equivalente a los requisitos de `q36cc_setup()`.
8. Solo entonces publicar `chain_ready=true` y transferir la propiedad de los recursos al runtime.

Ante cualquier fallo:
- mantener `chain_ready=false`;
- liberar en orden inverso todos los recursos del journal;
- limpiar cualquier entrada de mapas/slots que apunte a memoria liberada;
- restablecer contadores y referencias del intento;
- registrar tensor y etapa causante;
- continuar por fallback sin reintentar parcialmente dentro del mismo intento.

El rollback debe ser idempotente. Una segunda llamada no puede liberar dos veces ni dejar referencias colgantes.

## 7. Interacción con `CUDA_EXPERT_GB` y `COLI_PLACE`

La corrección ya incorporada en la rama del fork limita el cap numérico de `CUDA_EXPERT_GB` a la capacidad admisible después del margen y `G_reserve`. El planner de cadena debe convertirse en la fuente de verdad del presupuesto residual, evitando dos contabilidades independientes.

- `CUDA_EXPERT_GB=auto`: expertos reciben el remanente después de reservas obligatorias.
- `CUDA_EXPERT_GB=N`: expertos reciben `min(N, expert_budget)`; si se recorta, se registra.
- `COLI_PLACE`: las reglas manuales se validan contra el plan global. No se permite que una orden manual distribuya los tensores obligatorios de cadena por varios dispositivos.
- Cadena desactivada: mantener el comportamiento de placement de expertos existente, salvo el límite de memoria ya corregido.

No cambiar silenciosamente la semántica de variables existentes. Los conflictos deben ser visibles en stderr/log estructurado.

## 8. Contrato de salida y telemetría

Cada intento debe producir un registro con:

| Campo | Descripción |
|---|---|
| `planner_version` | versión del algoritmo |
| `chain_requested` | si la cadena estaba solicitada/habilitada |
| `chain_ready` | resultado final, nunca provisional |
| `selected_device` | UUID/índice, null si no hay candidato |
| `required_tensor_count` | número de tensores obligatorios |
| `required_bytes` | suma comprobada |
| `scratch_bytes` | scratch calculado |
| `reserved_bytes` | reservas previas contabilizadas |
| `usable_bytes` | capacidad admisible |
| `expert_budget_bytes` | remanente calculado |
| `status` | código de resultado |
| `failed_tensor` | tensor causante, si aplica |
| `rollback_complete` | si todos los recursos del intento se liberaron |
| `fallback_reason` | razón legible |

Los valores desconocidos se representan como null/ausentes, no como cero. El log debe distinguir fallo de planificación (sin uploads) y fallo de commit (rollback ejecutado).

## 9. Pruebas de aceptación

La suite host/fake-CUDA debe probar como mínimo:

| ID | Caso | Aserción |
|---|---|---|
| PLAN-01 | un dispositivo con capacidad holgada | elige ese dispositivo y calcula remanente correcto |
| PLAN-02 | un dispositivo cabe justo | acepta sin underflow ni margen negativo |
| PLAN-03 | ningún dispositivo cabe | `NO_FIT`, cero uploads |
| PLAN-04 | dos GPUs caben solo fragmentos distintos | rechaza; no distribuye la cadena |
| PLAN-05 | tensor obligatorio ausente | `MISSING_TENSOR`, cero uploads |
| PLAN-06 | layout no soportado | `UNSUPPORTED_LAYOUT`, cero uploads |
| PLAN-07 | suma de tamaños desborda | `OVERFLOW`, cero uploads |
| PLAN-08 | cap experto numérico supera remanente | clamp al remanente |
| COMMIT-01 | todas las subidas terminan bien | cadena lista y todos los tensores co-localizados |
| COMMIT-02 | falla primera subida | rollback limpio |
| COMMIT-03 | falla subida intermedia | rollback de todas las subidas anteriores |
| COMMIT-04 | falla inicialización de scratch | rollback de matrices y scratch |
| COMMIT-05 | rollback invocado dos veces | no double-free ni referencias residuales |
| COMMIT-06 | tensor ya residente en dispositivo correcto | reutilización segura, propiedad bien definida |
| CONFIG-01 | `COLI_PLACE` compatible | se respeta la selección manual |
| CONFIG-02 | `COLI_PLACE` divide el grupo | conflicto explícito y fallback/rechazo total |
| CONFIG-03 | cadena deshabilitada | placement experto previo permanece disponible |
| REG-01 | RTX sm_86 con memoria limitada | sin sobreasignación; resultado reproducible en fake-CUDA |

Las pruebas deben inspeccionar tanto el resultado como los efectos laterales: llamadas de upload, bytes reservados/liberados, mapas de residencia y estado final de `chain_ready`.

## 10. Criterios de salida por etapa

**P0 — planner puro:** todas las pruebas PLAN pasan; no hay llamadas CUDA en el planner.  
**P1 — commit/rollback:** todas las pruebas COMMIT pasan con fake-CUDA y sanitización disponible.  
**P2 — integración:** `q36cc_setup()` solo se invoca con plan confirmado; fallback permanece operativo.  
**P3 — hardware:** compila y arranca en sm_86; logs muestran reservas coherentes y no hay OOM.  
**P4 — rendimiento:** comparación CPU vs cadena CUDA con prompt/contexto fijos, TTFT/prefill/decode y al menos tres repeticiones. No se declara aceleración solo por `chain_ready=true`.

## 11. Riesgos abiertos que deben resolverse en el código

- ¿Las reservas de `qt_reserve()` se descuentan una vez o pueden solaparse con memoria ya reflejada en CUDA free?
- ¿Qué objetos poseen las asignaciones de tensores si el placement falla a mitad?
- ¿Cómo se revierte una entrada de tensor ya publicada en un mapa global?
- ¿Qué proyecciones son condicionales por variante/configuración Qwen3.6?
- ¿Scratch se reserva antes o después de conocer el número de filas efectivo?
- ¿Cómo se preserva una matriz previamente residente y quién es responsable de liberarla?
- ¿Qué política aplica si el usuario fuerza `COLI_PLACE` incompatible con la cadena?

No resolver estas preguntas con supuestos. Cada una debe cerrarse con inspección de código y test que reproduzca el contrato.

## 12. Relación con el protocolo LEONES

Esta especificación concreta Gate B del [Protocolo de validación MoE v1](colibri-moe-validation-protocol-v1.md). Los IDs CHAIN-01…08 siguen siendo los escenarios de campaña; PLAN/COMMIT/CONFIG/REG son las pruebas unitarias que los implementan. Solo los resultados ejecutados y archivados como recibos MEASURED pueden considerarse evidencia de hardware.
