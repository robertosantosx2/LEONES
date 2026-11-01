# Corrección de asignación CUDA diferida para Qwen3.5-4B — TensorFold PR #1879

**Fecha de consolidación documental:** 2026-11-02  
**Estado:** parche implementado, compilado y ejecutado en GPU real; PR upstream abierto y pendiente de revisión/fusión.  
**Issue de origen:** [ashhart/TensorFold #1827 — CUDA memory regression: Qwen3.5-4B no longer fits on a 4 GB RTX 3050](https://github.com/ashhart/TensorFold/issues/1827).  
**Pull request:** [ashhart/TensorFold #1879 — fix(cuda): allocate Qwen3.5 scratch lazily](https://github.com/ashhart/TensorFold/pull/1879).  
**Commit:** [14f6500d1fa43e113a5c28493ea6ea13b0ae7f67](https://github.com/robertosantosx2/TensorFold/commit/14f6500d1fa43e113a5c28493ea6ea13b0ae7f67).  
**Rama:** `fix/qwen35-cuda-lazy-scratch`.  
**Fork:** [robertosantosx2/TensorFold](https://github.com/robertosantosx2/TensorFold).  
**Base upstream:** `ashhart/TensorFold:main`.

> Este informe amplía la [auditoría estática inicial](CUDA-MEMORY-REGRESSION-2026-11-01.md). La auditoría identificó el coste de reservar scratch para 4096 filas. El trabajo posterior implementó una estrategia de asignación diferida y la validó en la RTX 3050. No debe confundirse la validación del nuevo ciclo de vida del scratch con una demostración A/B exhaustiva de que todos los rechazos históricos de admisión temprana quedan resueltos.

---

## 1. Resumen ejecutivo

Se implementó una corrección en el motor CUDA de la familia Qwen3.5 de TensorFold para evitar que el scratch de forward y el workspace de proyección INT8 se reserven de forma anticipada junto con los pesos del modelo.

La corrección cambia el ciclo de vida de esos recursos:

1. El arena de pesos deja de incorporar por adelantado el scratch de forward.
2. El scratch CUDA se solicita de forma diferida cuando una operación `forward` lo necesita.
3. Su capacidad se dimensiona por las filas requeridas por la operación, no por una reserva máxima incondicional.
4. Si la operación posterior necesita más filas, el scratch crece geométricamente.
5. Antes de liberar o sustituir memoria se sincroniza el trabajo CUDA pendiente y se destruyen los CUDA Graphs que podrían conservar punteros a la reserva anterior.
6. El workspace INT8 de prompt también se asigna bajo demanda y puede crecer.
7. Los fallos de crecimiento limpian los metadatos de propietario/capacidad para permitir un nuevo intento coherente.

El cambio se ha compilado para `sm_86`, se han ejecutado 43 pruebas host y se ha probado la ejecución CUDA real en la RTX 3050 Laptop de 4 GiB. En las pruebas registradas se alcanzaron operaciones de hasta 512 filas, con salidas byte-identical entre los paths step/window comparados a 64, 256 y 512 filas. La generación decode medida en esa ejecución fue aproximadamente 56.5 tokens/s.

**Resultado:** corrección técnica publicada como PR no fusionado. El PR está abierto, no es draft y el último estado consultado indicaba `mergeable: true`. La revisión y aceptación corresponden a los mantenedores upstream.

## 2. Equipo, sistema y modelo de referencia

### Hardware y software

| Elemento | Valor registrado |
|---|---|
| Equipo | MSI Thin 15 B12UC |
| CPU | Intel Core i7-12650H |
| CPU lógica | 16 hilos |
| RAM del sistema | 14.8 GiB |
| GPU | NVIDIA GeForce RTX 3050 Laptop |
| VRAM | 4 GiB |
| Compute capability | 8.6 (`sm_86`) |
| Driver NVIDIA | 580.178.04 |
| CUDA del driver | 13.0 |
| CUDA Toolkit / nvcc | 13.4.92 |
| Sistema | Ubuntu 26.04.1 |
| Kernel registrado | 7.0.0-38-generic |

La tarjeta dispone de 4 GiB físicos. La memoria utilizable para un proceso CUDA es menor por la reserva del driver, el contexto CUDA, el escritorio gráfico y cualquier otro proceso que esté usando la GPU.

### Modelo

- Repositorio HF: [mlx-community/Qwen3.5-4B-MLX-4bit](https://huggingface.co/mlx-community/Qwen3.5-4B-MLX-4bit).
- Snapshot local registrado: `32f3e8ecf65426fc3306969496342d504bfa13f3`.
- Archivo principal: `model.safetensors`.
- Tamaño observado: 3,034,300,695 bytes (aprox. 2.83 GiB).
- Familia: Qwen3.5 texto denso, no variante MoE.

Ruta de caché local registrada:

```text
~/.cache/huggingface/hub/models--mlx-community--Qwen3.5-4B-MLX-4bit/snapshots/32f3e8ecf65426fc3306969496342d504bfa13f3
```

## 3. Antecedentes: diagnóstico inicial

La auditoría estática anterior estudió el aumento de capacidad de prompt de 128 a 4096 filas. Según las fórmulas del código y la geometría del checkpoint, reconstruyó:

| Componente | 128 filas | 4096 filas |
|---|---:|---:|
| Scratch escalado por filas | 19.484 MiB | 623.500 MiB |
| Scratch fijo aproximado | 189.685–190.685 MiB, según inclusión del sampling scratch | 190.685 MiB |
| Scratch total reconstruido | ≈209.169 MiB | ≈814.185 MiB |

El incremento reconstruido era aproximadamente 605 MiB. Estas cifras eran cálculos derivados de las fórmulas de asignación, no lecturas de VRAM.

La auditoría también separó dos fenómenos:

- **Reserva del motor:** el scratch se dimensionaba a partir de la capacidad máxima de filas.
- **Admisión temprana de pesos:** la comprobación de presupuesto podía rechazar los pesos antes de que se crease el arena del motor.

Esta separación sigue siendo importante. La nueva estrategia evita la reserva anticipada del scratch; no demuestra por sí sola que cualquier rechazo temprano de pesos de versiones anteriores tuviese exactamente esa causa. Para cerrar esa cuestión se necesita una reproducción A/B con el mismo estado GPU, checkpoint, variables de entorno y comando.

La auditoría histórica completa permanece en [CUDA-MEMORY-REGRESSION-2026-11-01.md](CUDA-MEMORY-REGRESSION-2026-11-01.md).

## 4. Objetivo de ingeniería

El objetivo no fue reducir precisión, cambiar el modelo, eliminar comprobaciones de memoria ni revertir globalmente los kernels de prompt de 4096 filas.

El objetivo fue desacoplar:

- la capacidad funcional que un kernel puede admitir;
- la cantidad de filas que necesita una operación concreta;
- la memoria que el motor reserva físicamente en ese momento.

La memoria temporal debe existir cuando se necesita y con capacidad suficiente para la operación, manteniendo la posibilidad de crecer para operaciones posteriores más grandes.

### Propiedades que debía preservar la corrección

- No reservar el scratch completo de forward durante la creación del arena de pesos.
- No degradar la ruta CUDA existente de inferencia.
- No dejar CUDA Graphs apuntando a buffers liberados o sustituidos.
- No liberar memoria mientras el stream todavía pueda estar usándola.
- Permitir que una operación posterior requiera más filas.
- Recuperarse de un fallo de asignación sin dejar metadatos de capacidad falsos.
- Aplicar el mismo principio al workspace INT8 de prompt.
- Mantener el cambio localizado en la familia Qwen3.5 CUDA.

## 5. Implementación: archivos modificados

El commit modifica exactamente cinco archivos: **230 inserciones y 28 eliminaciones**.

| Archivo | Responsabilidad del cambio |
|---|---|
| `zig/src/families/qwen3_5/cuda_engine.zig` | Separa la reserva de pesos del scratch de forward y gestiona la asignación/crecimiento diferidos del scratch. |
| `zig/src/families/qwen3_5/cuda_engine_tail.zig` | Integra el ciclo de vida del scratch con las rutas finales del motor y su limpieza. |
| `zig/src/families/qwen3_5/cuda_prompt_int8.zig` | Hace diferida y redimensionable la reserva del workspace de proyección INT8 de prompt. |
| `zig/qwen35_prompt_int8_host.zig` | Añade pruebas host para la gestión del workspace INT8, crecimiento y recuperación. |
| `zig/qwen35_verify_host.zig` | Añade cobertura host de los invariantes de capacidad y gestión de recursos asociados. |

### 5.1 Separación del arena de pesos

Antes, la construcción del arena contabilizaba conjuntamente los bytes de pesos y el scratch medido del motor. El nuevo enfoque evita que el scratch de forward se convierta en una obligación de memoria inicial al cargar los pesos.

La reserva temporal pasa a producirse en el camino de ejecución que la necesita. Así, la carga inicial no exige reservar de antemano el máximo de activaciones temporales de prompt.

### 5.2 Asignación diferida y crecimiento

El scratch se crea cuando `forward` lo requiere. La capacidad solicitada se relaciona con el número de filas de la operación.

Cuando una llamada necesita más capacidad que la disponible, la reserva puede crecer geométricamente. El crecimiento geométrico evita una reasignación por cada incremento pequeño y amortiza el coste de futuras expansiones.

La capacidad efectiva y el propietario de la reserva deben representar siempre la memoria realmente disponible. Por eso, una asignación fallida no puede dejar un valor de capacidad que haga creer al motor que existe un buffer mayor del que se ha conseguido reservar.

### 5.3 Sincronización y CUDA Graphs

Una reserva CUDA puede estar siendo utilizada por trabajo ya enviado al stream. Además, un CUDA Graph capturado puede conservar referencias a direcciones de dispositivo.

Por tanto, no basta con liberar el buffer anterior y sustituir el puntero. Antes de reemplazar o destruir el scratch, el código sincroniza el trabajo CUDA pertinente y destruye los graphs que podrían conservar punteros obsoletos.

Este orden de vida útil es parte esencial de la corrección: evita que una optimización de memoria introduzca accesos a memoria liberada o referencias inválidas en un replay posterior.

### 5.4 Workspace INT8 de prompt

El workspace de proyección INT8 deja de reservarse de forma anticipada al máximo. Se crea cuando la ruta INT8 lo necesita y puede crecer según el número de filas requerido.

También se contempla el fallo de crecimiento: el estado de propietario y capacidad se limpia para que un intento posterior pueda volver a reservar correctamente.

La validación registrada incluye crecimiento progresivo hasta batches de 128 filas.

### 5.5 Recuperación tras errores

Los tests host cubren estados de asignación diferida, crecimiento, fallo y recuperación. La intención es asegurar que el motor no conserva metadatos obsoletos tras un error de asignación.

No se interpreta un test host como sustituto de la validación de CUDA real: ambas capas se ejecutaron y se documentan por separado.

## 6. Validación reproducible registrada

### 6.1 Compilación CUDA para la GPU objetivo

Comando ejecutado:

```bash
cd ~/tensorfold

zig build qwen35-cuda \
  -Dnvcc=/usr/local/cuda/bin/nvcc \
  -Dsm=86 \
  -Doptimize=ReleaseFast \
  --summary all
```

Resultado:

- **114/114 build steps completados correctamente.**
- Arquitectura objetivo: `sm_86`.
- Optimización: `ReleaseFast`.
- Toolkit utilizado: CUDA 13.4.92.
- No se registró fallo de compilación en esta ejecución.

### 6.2 Tests host

Para evitar que un resultado previo de caché se confundiese con una ejecución real, se usó un directorio de caché Zig temporal:

```bash
cd ~/tensorfold

zig build \
  --cache-dir /tmp/tensorfold-zig-host-cache \
  test-qwen35-prompt-int8-host \
  test-qwen35-prompt-layout-host \
  test-qwen35-attention-path-host \
  test-qwen35-prompt-moe-host \
  --summary all
```

Resultado:

| Suite | Tests |
|---|---:|
| `test-qwen35-prompt-moe-host` | 13 |
| `test-qwen35-attention-path-host` | 13 |
| `test-qwen35-prompt-layout-host` | 12 |
| `test-qwen35-prompt-int8-host` | 5 |
| **Total** | **43** |

**43 passed, 0 failed, 0 skipped.**

Estas pruebas cubren las suites host indicadas; no deben describirse como 43 pruebas de GPU.

### 6.3 Higiene del diff

Se ejecutó:

```bash
git diff --check
```

Resultado: sin errores de whitespace/conflictos detectados por esa comprobación.

### 6.4 Ejecución CUDA en hardware real

Se ejecutó el motor CUDA sobre la NVIDIA RTX 3050 Laptop de 4 GiB, compute capability 8.6.

Resultados registrados:

- Operaciones step/window hasta 512 filas.
- Salidas byte-identical entre los paths step/window comparados para 64, 256 y 512 filas.
- Prompt probado hasta 512 filas.
- Decode observado alrededor de **56.5 tokens/s**.
- Crecimiento progresivo del workspace INT8 de prompt hasta batches de 128 filas.
- No se registraron errores CUDA en las ejecuciones descritas.

La igualdad byte a byte está limitada a las rutas y tamaños que se compararon. **No equivale** a una comparación contra `draft:false`, ni valida automáticamente todas las rutas de cache, concurrencia o backends.

### 6.5 Resumen de evidencia

| Validación | Resultado | Alcance |
|---|---|---|
| Build CUDA | 114/114 | Compilación `sm_86`, ReleaseFast |
| Tests host | 43/43 | Cuatro suites host Qwen3.5 |
| Diff check | Limpio | Higiene textual del diff |
| CUDA real | Correcto en ejecuciones registradas | RTX 3050 Laptop 4 GiB |
| Step/window | Byte-identical | 64, 256 y 512 filas entre paths comparados |
| Prompt | Hasta 512 filas | Ejecución registrada |
| Decode | ≈56.5 tok/s | Medición de esta ejecución; no benchmark A/B |
| INT8 workspace | Crecimiento hasta 128 filas | Ruta opcional de prompt INT8 |

## 7. Qué demuestra y qué no demuestra esta validación

### Demostrado por las pruebas registradas

1. El parche compila para la arquitectura real de la RTX 3050 (`sm_86`).
2. Las cuatro suites host indicadas pasan: 43/43.
3. La ejecución CUDA real funciona en el hardware objetivo en los escenarios probados.
4. Las operaciones step/window comparadas producen salidas byte-identical a 64, 256 y 512 filas.
5. Se ejercitó el crecimiento del workspace INT8 hasta 128 filas.
6. La comprobación `git diff --check` no detectó problemas.

### No demostrado / pruebas pendientes

No se ha afirmado que estas validaciones se hayan realizado:

- Comparación de salida de draft frente a `draft:false`.
- Prompts reanudados frente a prompts frescos.
- Ejecución concurrente frente a ejecución aislada.
- Benchmark A/B de decode antes/después con protocolo idéntico.
- Benchmark A/B de prefill frío/TTFT antes/después.
- Ejecución con `tools/bench_openai.py`.
- Ejecución con `tools/bench_cache.py --require-cold`.
- Validación en Metal.
- Validación en Vulkan.
- Validación en HIP.
- Prueba exhaustiva de todos los tamaños parciales, concurrencia y ciclos de captura/replay en todos los escenarios de producción.
- Reproducción A/B controlada entre TensorFold 1.1.2 y releases afectadas con idéntico estado GPU, checkpoint y reserva.
- Confirmación de que el parche resuelve todos los posibles rechazos tempranos de admisión de pesos.

La ausencia de esas pruebas se mantiene explícita para no inflar el alcance de la evidencia.

## 8. Diferencia entre la auditoría inicial y la corrección

| Aspecto | Auditoría estática inicial | Trabajo posterior |
|---|---|---|
| Tipo de trabajo | Inspección de código y fórmulas | Modificación, tests, build y GPU real |
| Reserva de scratch | Identifica reserva asociada a capacidad máxima | Scratch separado del arena de pesos y diferido |
| Capacidad | Reconstrucción del coste 128 vs 4096 | Capacidad temporal según filas requeridas, con crecimiento |
| Workspace INT8 | Identifica reserva opcional por máximo de filas | Asignación diferida y redimensionable |
| Seguridad de punteros | Riesgos identificados en lifetimes/graphs | Sincronización y destrucción de graphs antes de reemplazar buffers |
| Pruebas host | Ninguna en esa auditoría | 43/43 |
| Build CUDA | Ninguna en esa auditoría | 114/114 para `sm_86` |
| GPU real | Ninguna en esa auditoría | RTX 3050 real, hasta 512 filas |
| Estado upstream | No había parche | PR #1879 abierto |

La primera auditoría no se sobrescribe: documenta la investigación que motivó el parche. Este informe registra el cambio de estado desde hipótesis de diseño a implementación validada en los escenarios descritos.

## 9. Publicación upstream y trazabilidad Git

### Commit

- Repositorio: [robertosantosx2/TensorFold](https://github.com/robertosantosx2/TensorFold).
- Rama: `fix/qwen35-cuda-lazy-scratch`.
- Commit corto: `14f6500d1`.
- SHA completo: `14f6500d1fa43e113a5c28493ea6ea13b0ae7f67`.
- Mensaje: `fix(cuda): allocate Qwen3.5 scratch lazily`.
- Cambios: 5 archivos, 230 inserciones, 28 eliminaciones.

### Pull request

[PR #1879 — fix(cuda): allocate Qwen3.5 scratch lazily](https://github.com/ashhart/TensorFold/pull/1879)

Metadatos verificados en la última consulta:

| Campo | Estado |
|---|---|
| Repositorio destino | `ashhart/TensorFold` |
| Base | `main` |
| Head | `robertosantosx2:fix/qwen35-cuda-lazy-scratch` |
| Commit head | `14f6500d1fa43e113a5c28493ea6ea13b0ae7f67` |
| Estado | Open |
| Draft | No |
| Merged | No |
| Mergeable | True en la última consulta |
| Archivos cambiados | 5 |
| Inserciones | 230 |
| Eliminaciones | 28 |

La descripción del PR incluye motivación, implementación, entorno, recibos de validación, exactitud, velocidad medida, pruebas pendientes y checklist. El checklist deja sin marcar las validaciones que no se han realizado.

**Estado de publicación:** enviado a revisión upstream; no fusionado. El estado `mergeable: true` es una instantánea de la consulta y puede cambiar con nuevas actualizaciones de la rama base o de GitHub.

## 10. Reproducción del entorno y comprobaciones útiles

Los siguientes comandos sirven para volver a identificar el entorno y revisar la rama/commit. No son una afirmación de que se hayan ejecutado todos de nuevo al preparar este documento.

### Identidad de la GPU

```bash
nvidia-smi
nvcc --version
```

### Revisar checkout local

```bash
cd ~/tensorfold

git status --short --branch
git log -1 --oneline --decorate
git show --stat --oneline 14f6500d1fa43e113a5c28493ea6ea13b0ae7f67
git diff 14f6500d1^ 14f6500d1 --check
```

### Repetir build

```bash
cd ~/tensorfold

zig build qwen35-cuda \
  -Dnvcc=/usr/local/cuda/bin/nvcc \
  -Dsm=86 \
  -Doptimize=ReleaseFast \
  --summary all
```

### Repetir suites host

```bash
cd ~/tensorfold

zig build \
  --cache-dir /tmp/tensorfold-zig-host-cache \
  test-qwen35-prompt-int8-host \
  test-qwen35-prompt-layout-host \
  test-qwen35-attention-path-host \
  test-qwen35-prompt-moe-host \
  --summary all
```

Los comandos de ejecución end-to-end dependen de la configuración local y del binario generado. Antes de una repetición hay que verificar el ejecutable, el snapshot del modelo, la memoria libre y los procesos GPU; no debe iniciarse un servidor adicional sobre un puerto ya ocupado ni confundirse un resultado de caché con una ejecución nueva.

## 11. Próximos pasos recomendados

Orden propuesto para completar la evidencia sin ampliar innecesariamente el cambio:

1. Esperar revisión de mantenedores y responder a observaciones con evidencia reproducible.
2. Ejecutar comparación A/B con TensorFold 1.1.2 y la rama del parche, mismo snapshot, mismo comando, mismo reserve y GPU en estado equivalente.
3. Registrar carga, memoria libre antes/después, memoria máxima si está instrumentada, prefill/TTFT frío y decode.
4. Ejecutar comparación de salida frente a `draft:false` si el escenario usa speculative/draft.
5. Probar prompt fresco y reanudado.
6. Probar ejecución aislada y concurrente.
7. Revisar resultados de CI del PR y conservar logs.
8. Considerar Metal/Vulkan/HIP solo si el cambio alcanza esas rutas o si la revisión upstream lo solicita.

No se debe marcar como resuelto el issue upstream ni declarar el PR fusionado antes de una confirmación real del mantenedor.

## 12. Referencias

- [Issue upstream #1827](https://github.com/ashhart/TensorFold/issues/1827).
- [PR upstream #1879](https://github.com/ashhart/TensorFold/pull/1879).
- [Commit del parche](https://github.com/robertosantosx2/TensorFold/commit/14f6500d1fa43e113a5c28493ea6ea13b0ae7f67).
- [Fork TensorFold](https://github.com/robertosantosx2/TensorFold).
- [Checkpoint Qwen3.5-4B MLX 4-bit](https://huggingface.co/mlx-community/Qwen3.5-4B-MLX-4bit).
- [Auditoría estática inicial en LEONES](CUDA-MEMORY-REGRESSION-2026-11-01.md).

---

## 13. Estado final LEONES

**CLASIFICACIÓN:** IMPLEMENTACIÓN REALIZADA / BUILD CUDA CORRECTO / TESTS HOST 43 DE 43 / EJECUCIÓN GPU REAL CORRECTA EN LOS CASOS REGISTRADOS / PR UPSTREAM ABIERTO.

El cambio corrige el patrón de reserva anticipada de scratch para los caminos Qwen3.5 CUDA cubiertos por el parche. La evidencia física respalda la ejecución en la RTX 3050 de 4 GiB hasta 512 filas y el crecimiento del workspace INT8 hasta 128 filas.

**Pendiente:** revisión y fusión upstream, benchmarks A/B rigurosos, cobertura de draft/reanudación/concurrencia y cualquier validación adicional solicitada por los mantenedores.

La documentación distingue expresamente hechos medidos, resultados de tests, cálculos históricos y pruebas aún no realizadas.


## 14. Instalación local de TensorFold y relación con el checkout de desarrollo

Esta sección registra la disposición local del software para que el experimento pueda reproducirse sin confundir el binario de una versión instalada con el código fuente del PR.

### 14.1 Repositorio de desarrollo

El checkout utilizado para inspeccionar, modificar, compilar y validar el parche está en:

```text
~/tensorfold
```

Remotos registrados:

| Nombre | URL | Función |
|---|---|---|
| `origin` | `https://github.com/ashhart/TensorFold.git` | Repositorio upstream |
| `fork` | `https://github.com/robertosantosx2/TensorFold.git` | Fork donde se publicó la rama del parche |

Rama de trabajo publicada:

```text
fix/qwen35-cuda-lazy-scratch
```

Commit validado:

```text
14f6500d1fa43e113a5c28493ea6ea13b0ae7f67
```

El commit contiene los cinco archivos descritos en la sección 5. La compilación CUDA y las pruebas host indicadas en este informe se realizaron desde el árbol de desarrollo `~/tensorfold`; no se deben atribuir automáticamente esos resultados a un binario precompilado instalado por separado.

Comprobaciones locales útiles:

```bash
cd ~/tensorfold

# Identidad del checkout, rama y estado de trabajo
git status --short --branch
git branch --show-current
git log -1 --format='%H%n%s'

# Remotos y relación con upstream/fork
git remote -v

# Resumen exacto del parche publicado
git show --stat --oneline 14f6500d1fa43e113a5c28493ea6ea13b0ae7f67

# Comprobar el diff del commit
git show --format= --check 14f6500d1fa43e113a5c28493ea6ea13b0ae7f67
```

### 14.2 Binario instalado de TensorFold

Además del checkout de desarrollo, el historial local registra una instalación versionada de TensorFold 1.1.6:

```text
~/.local/opt/tensorfold-1.1.6-linux-x86_64/bin/tensorfold-native
```

Esta ruta corresponde al binario instalado de la versión 1.1.6 y debe tratarse como una instalación independiente del ejecutable generado desde la rama del PR.

Para inventariarlo sin asumir que el binario sigue presente:

```bash
TF_BIN="$HOME/.local/opt/tensorfold-1.1.6-linux-x86_64/bin/tensorfold-native"

if [ -x "$TF_BIN" ]; then
    ls -lh "$TF_BIN"
    "$TF_BIN" --version 2>&1 || true
    "$TF_BIN" --help | head -80
else
    echo "No se encuentra el binario registrado: $TF_BIN"
fi
```

**Precaución de trazabilidad:** no usar el nombre de versión 1.1.6 para identificar el binario compilado con el parche. Para una repetición del experimento hay que registrar explícitamente si se ejecutó el binario instalado o el artefacto recién compilado desde `~/tensorfold`, junto con su ruta y hash.

### 14.3 Historial de versiones que motivó la investigación

El historial del experimento contiene estos hitos:

| Versión | Evidencia registrada | Interpretación |
|---|---|---|
| TensorFold 1.1.2 | Ejecución histórica de Qwen3.5-4B en la RTX 3050: carga ≈7.2 s, decode ≈54.2 tok/s, prefill ≈0.195 s y TTFT ≈0.198 s | Referencia histórica funcional en el mismo equipo; no es una prueba A/B contemporánea |
| TensorFold 1.1.4 | Primera versión publicada que incorporó el cambio upstream de chunks de prompt de hasta 4096 filas, según la auditoría del commit | Punto de introducción del cambio de arquitectura de prompt |
| TensorFold 1.1.5 | Se registró rechazo de memoria al intentar cargar Qwen3.5-4B; pesos ≈2.8 GiB frente a presupuesto CUDA ≈2.6 GiB | Evidencia de fallo de admisión en esa configuración; no demuestra por sí sola que el scratch fuera la causa |
| TensorFold 1.1.6 | Se registraron nuevos rechazos OOM durante la investigación; binario local versionado en `~/.local/opt/tensorfold-1.1.6-linux-x86_64/` | Versión instalada que conviene mantener separada del checkout parcheado |
| TensorFold 1.2.0 | También se registraron rechazos OOM durante la investigación | Requiere reproducción controlada para determinar el punto exacto de fallo |
| Checkout con PR #1879 | Build CUDA 114/114, tests host 43/43 y ejecución real en RTX 3050 hasta 512 filas | Evidencia directa del código parcheado, no de un release publicado |

Las cifras de 1.1.2 son mediciones históricas del usuario. No deben compararse como benchmark A/B concluyente con los ≈56.5 tok/s de la ejecución del parche: no se ha demostrado que ambos registros usaran exactamente el mismo protocolo, contexto, estado térmico, estado de VRAM, warmup, número de repeticiones y binario.

### 14.4 Toolchain CUDA y Zig

Toolchain registrado para la compilación de la rama:

| Componente | Versión/ruta |
|---|---|
| CUDA Toolkit | 13.4.92 |
| Compilador CUDA | `/usr/local/cuda/bin/nvcc` |
| Driver NVIDIA | 580.178.04 |
| CUDA reportado por driver | 13.0 |
| GPU target | `sm_86` |
| Optimización Zig | `ReleaseFast` |
| Zig | Build system Zig del checkout; la versión exacta del ejecutable Zig no quedó consignada en el recibo actual |

Para completar el inventario en una futura repetición:

```bash
zig version
command -v zig
/usr/local/cuda/bin/nvcc --version
nvidia-smi
uname -a
lsb_release -a 2>/dev/null || cat /etc/os-release
```

No se debe inventar una versión exacta de Zig a partir del éxito de `zig build`; el dato quedó pendiente de captura.

### 14.5 Checkpoint local y caché Hugging Face

El snapshot utilizado quedó almacenado bajo la caché estándar de Hugging Face:

```text
~/.cache/huggingface/hub/models--mlx-community--Qwen3.5-4B-MLX-4bit/snapshots/32f3e8ecf65426fc3306969496342d504bfa13f3
```

Archivo principal:

```text
model.safetensors
```

Tamaño registrado: 3,034,300,695 bytes. El snapshot ID es el identificador de revisión de contenido registrado en la caché; debe anotarse en toda repetición, incluso si el repositorio HF publica después una revisión nueva.

Comprobaciones:

```bash
MODEL="$HOME/.cache/huggingface/hub/models--mlx-community--Qwen3.5-4B-MLX-4bit/snapshots/32f3e8ecf65426fc3306969496342d504bfa13f3"

if [ -d "$MODEL" ]; then
    du -sh "$MODEL"
    stat -c '%n %s bytes' "$MODEL/model.safetensors"
    sha256sum "$MODEL/model.safetensors"
else
    echo "No se encuentra el snapshot local registrado"
fi
```

El hash SHA-256 no quedó registrado en el recibo original; el comando anterior permite capturarlo en una nueva ejecución. No debe rellenarse retrospectivamente con un valor supuesto.

### 14.6 Servicios, puertos y aislamiento de experimentos

En el último inventario disponible no había un servidor TensorFold activo en los puertos 8080 ni 18084. Este dato es una observación histórica, no una garantía sobre el estado actual del equipo.

Antes de repetir pruebas, inspeccionar procesos y sockets:

```bash
pgrep -a -f 'tensorfold|llama-server|llama.cpp' || true
ss -ltnp | grep -E ':(8080|18084)\\b' || true
nvidia-smi
```

El equipo mantiene otros entornos de inferencia local (entre ellos ODS/Hermes y servidores llama.cpp en experimentos separados). No se debe detener, reconfigurar ni reemplazar el `llama-server` por defecto para ejecutar este ensayo. Usar un puerto de prueba libre y documentarlo en el recibo de cada repetición.

No se ha registrado en este informe un puerto de servicio utilizado durante la validación CUDA del PR; por ello no se atribuye uno.

### 14.7 Inventario de espacio y memoria del sistema

El historial local registra un disco raíz de aproximadamente 937 GB, con unos 674 GB libres en una captura anterior. También registra un swapfile `/swap32.img` de 32 GB; el antiguo `/swap.img` de 4 GB fue retirado/deshabilitado. El uso de swap variaba entre capturas y llegó a aproximadamente 11 GB durante descargas el 2026-10-26.

Estos valores son históricos y no describen necesariamente el estado del sistema el día de una futura prueba. Para un recibo reproducible, capturar:

```bash
free -h
swapon --show
df -h /
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS
```

La VRAM disponible es el límite inmediato de este caso, pero la RAM, el swap y el espacio libre pueden afectar la carga del checkpoint, la compilación y el comportamiento del sistema durante pruebas largas.

### 14.8 Plantilla de recibo para una repetición local

Guardar junto a cada resultado el siguiente inventario, completado con los valores observados en esa ejecución:

```bash
cd ~/tensorfold

{
  echo "=== FECHA ==="
  date --iso-8601=seconds
  echo "=== CHECKOUT ==="
  pwd
  git status --short --branch
  git log -1 --format='%H%n%s'
  git remote -v
  echo "=== ZIG ==="
  zig version
  echo "=== CUDA ==="
  /usr/local/cuda/bin/nvcc --version
  echo "=== GPU ==="
  nvidia-smi
  echo "=== SISTEMA ==="
  uname -a
  cat /etc/os-release
  free -h
  swapon --show
  df -h /
  echo "=== PROCESOS Y PUERTOS ==="
  pgrep -a -f 'tensorfold|llama-server|llama.cpp' || true
  ss -ltnp | grep -E ':(8080|18084)\\b' || true
  echo "=== MODELO ==="
  MODEL="$HOME/.cache/huggingface/hub/models--mlx-community--Qwen3.5-4B-MLX-4bit/snapshots/32f3e8ecf65426fc3306969496342d504bfa13f3"
  stat -c '%n %s bytes' "$MODEL/model.safetensors" 2>&1 || true
  sha256sum "$MODEL/model.safetensors" 2>&1 || true
} 2>&1 | tee "local-environment-$(date +%Y%m%d-%H%M%S).log"
```

Este recibo permite diferenciar una regresión del código de diferencias de versión, estado de GPU, ocupación de VRAM, checkpoint o toolchain.

### 14.9 Límites de lo que se conoce de la instalación

Se conserva deliberadamente esta distinción:

- Está registrada la ruta del checkout, los remotos, la rama y el commit publicado.
- Está registrada la ruta del binario instalado TensorFold 1.1.6.
- Está registrado el snapshot del modelo y el tamaño de `model.safetensors`.
- Están registradas las versiones CUDA, driver, GPU y sistema usadas en la validación.
- No se dispone en el recibo actual de la versión exacta de Zig.
- No se conserva el SHA-256 original del checkpoint.
- No se ha fijado un puerto de servidor para la ejecución CUDA del PR.
- El estado de procesos, puertos, VRAM, swap y disco cambia con el tiempo y debe capturarse de nuevo antes de cada benchmark.

Esta sección evita presentar datos de inventario histórico como si fueran lecturas actuales y hace explícitos los campos que conviene registrar para elevar la reproducibilidad.
