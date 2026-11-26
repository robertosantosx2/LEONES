# Auditoría del loader NASM y runtime bare-metal

**Proyecto:** llm.asm-qwen4B  
**Upstream:** `alesha-pro/llm.asm`  
**Commit auditado:** `48feccbfd57cb669440f31ff64958d95bb8b848e`  
**Fecha:** 26 de noviembre de 2026  
**Método:** inspección estática de código fuente remoto fijado; sin compilación ni ejecución.

## 1. Archivos y rutas revisados

- `shared/transformer.asm`: `model_init`, resolución de punteros, cálculo y asignación del arena.
- `shared/constants.inc`: encabezado ASMBIN, offsets y estructura del contexto.
- `01-qwen3-inference/main.asm`: adquisición del tamaño real mediante `fstat` y llamada a `model_init`.
- `02-baremetal-os/kernel.asm`: lectura de los límites del módulo Multiboot y llamada al loader.
- `02-baremetal-os/runtime.asm`: `mem_init` y `sys_mmap_anon`.
- `02-baremetal-os/os_constants.inc`: offsets de Multiboot 1.

## 2. Hallazgo crítico: el tamaño del archivo no se valida dentro de model_init

La ruta Linux obtiene el tamaño mediante `fstat` y lo conserva en `r14`; la ruta bare-metal recibe el tamaño del módulo en `rsi`. Sin embargo, después de establecer `r15` como base y `r14` como tamaño, `model_init` comienza leyendo magic/version del encabezado y continúa leyendo campos sin una comprobación visible de que:

- `r14 >= 128` antes de leer el encabezado completo.
- `HDR_FILE_SIZE == r14`.
- El tamaño declarado no exceda el tamaño real.
- Los offsets y regiones de cada sección estén dentro de `[r15, r15+r14)`.

La ruta Linux mapea el archivo completo, pero mmap no valida semánticamente las lecturas posteriores: acceder a páginas más allá del final del archivo puede provocar SIGBUS. En bare-metal, una lectura fuera del módulo puede acceder a memoria física ajena al artefacto.

**Consecuencia:** el tamaño obtenido por el sistema operativo o el bootloader no constituye por sí mismo una validación del formato. La defensa debe residir en `model_init`, antes de cualquier lectura dependiente de offsets.

## 3. Hallazgo crítico: resolución de punteros sin validación previa

El loader lee `HDR_OFF_TOKENIZER`, suma la base y lee inmediatamente los sub-offsets `TOKH_OFF_B2T`, `TOKH_OFF_OFFSETS`, `TOKH_OFF_BYTES` y `TOKH_OFF_HT`. Hace lo mismo para embeddings, capas y norma final.

No se observan comprobaciones previas de rango para esas lecturas ni para las regiones a las que apuntan. La suma base + offset tampoco está protegida por una comprobación de overflow y límite.

El loader debe validar con aritmética de resta, evitando comprobar una suma que ya pudiera desbordar:

1. `offset <= file_size`.
2. `length <= file_size - offset`.
3. Solo después formar el puntero base + offset.

El encabezado tiene 128 bytes. Los subheaders y tablas deben comprobarse antes de leer sus campos, no después de haber construido punteros.

## 4. Hallazgo crítico: dimensiones y tamaños derivados sin validación suficiente

El loader copia dimensiones de 32 bits a registros de 64 bits y calcula:

- `q_dim = n_heads * head_dim`.
- `kv_dim = n_kv_heads * head_dim`.
- Tamaños de buffers de activación.
- Scores de atención.
- KV-cache proporcional a capas × contexto × kv_dim × sizeof(float).
- Tamaño total del arena.

La revisión no encontró una fase de validación completa previa a estos cálculos que garantice dimensiones positivas, relaciones válidas, límites del kernel Q8 y ausencia de overflow en cada producto/suma.

Requisitos mínimos antes de reservar memoria o resolver datos del modelo:

- Dimensiones y contexto positivos.
- `n_heads % n_kv_heads == 0`, con ambos valores no nulos.
- `head_dim` compatible con RoPE.
- Dimensiones K de matrices múltiplos de 32 y no superiores a `Q8_MAX_K`.
- `n_layers`, vocabulario y contexto acotados por límites explícitos.
- Multiplicaciones y acumulaciones verificadas antes de aceptar cada tamaño.
- Rechazo de valores que no puedan representarse en el tamaño de arena o en el espacio de direcciones admitido.

No imponer `dim == q_dim`: Qwen3-4B tiene dim 2560 y q_dim 4096.

## 5. Coherencia del layout de capas

El loader lee `HDR_LAYER_STRIDE` y `HDR_OFF_LAYERS`, pero no se observa una verificación previa que demuestre que:

- El stride declarado sea al menos el tamaño calculado de una capa.
- `n_layers * layer_stride` quepa dentro del archivo sin overflow.
- La región de capas no solape tokenizer, embeddings o norma final.
- El orden y tamaños de matrices/normas coincidan con el layout de la versión.

La defensa debe validar el tamaño mínimo requerido por capa, el producto por número de capas y la región completa, manteniendo compatibilidad exacta con el layout canónico del exportador.

## 6. Runtime bare-metal: parser de mapa Multiboot insuficientemente acotado

En `02-baremetal-os/runtime.asm:mem_init`, la ruta de mmap:

- Lee `MBI_MMAP_ADDR` y `MBI_MMAP_LENGTH` y calcula el final del buffer.
- Lee campos de cada entrada, incluido el tipo en `[rbx+20]`.
- Avanza con `entry_size + 4`.

En el código revisado no aparecen comprobaciones suficientes de que cada entrada tenga al menos los campos consumidos, que el tamaño de entrada quepa en los bytes restantes, que el puntero avance sin overflow y que el recorrido termine exactamente dentro del buffer declarado. Una entrada truncada o malformada podría causar lecturas fuera del mapa o un bucle/avance incorrecto.

También se acumulan longitudes y se forman finales de regiones mediante sumas sin comprobaciones explícitas de overflow. El parser debe validar la estructura completa del mapa antes de usar una región como RAM utilizable.

## 7. Runtime bare-metal: límites del allocator

En `sys_mmap_anon`, el allocator alinea el puntero actual y el tamaño sumando 63, calcula el final mediante suma y lo compara con `g_heap_end`. No se observan comprobaciones de overflow para esas operaciones ni rechazo explícito de tamaño cero.

El endurecimiento debe comprobar:
- Heap inicializado y coherencia `heap_base <= heap_cur <= heap_end`.
- Alineación sin overflow.
- Tamaño alineado sin overflow.
- Capacidad mediante resta (`aligned_size <= heap_end - aligned_start`) antes de formar el final.
- Estado consistente ante fallo, sin modificar `g_heap_cur`.

Este endurecimiento es importante para que un tamaño de arena derivado de un encabezado inválido no pueda corromper el allocator.

## 8. Orden de validación recomendado

La implementación nativa debe seguir un orden estricto y no tocar datos dependientes de offsets antes de validar sus rangos:

1. Validar tamaño mínimo del archivo/módulo y cabecera completa.
2. Validar magic, versión, flags conocidos y coherencia versión/flags.
3. Validar tamaño declarado frente al tamaño real.
4. Validar dimensiones y relaciones, con límites compatibles con el kernel.
5. Validar offsets de secciones, orden, alineación y ausencia de solapamientos.
6. Calcular tamaños esperados con comprobación de overflow.
7. Validar stride y región completa de capas.
8. Validar header/subregiones/tokenizer y tablas BPE.
9. Solo entonces resolver punteros y calcular/reservar el arena.
10. Mantener errores de carga diferenciados y asegurar que el fallo no deje un contexto parcialmente inicializado.

El validador Python independiente sigue siendo una defensa y herramienta de diagnóstico, pero no sustituye estas comprobaciones dentro del binario NASM.

## 9. Plan de implementación y pruebas

### Fase A — especificación y límites
- Definir constantes máximas y relaciones válidas compartidas entre pruebas y loader.
- Documentar cada fórmula de tamaño del layout v1/v2.
- Diseñar helpers NASM para comprobaciones de rango y overflow, respetando ABI y registros preservados.

### Fase B — loader Linux
- Añadir validación antes de cualquier lectura fuera de los 128 bytes garantizados.
- Validar el archivo real obtenido por `fstat`.
- Rechazar artefactos truncados, offsets inválidos, regiones solapadas y dimensiones no soportadas.
- Compilar ambos modos `FAST_Q8=0` y `FAST_Q8=1`.

### Fase C — runtime bare-metal
- Validar límites del módulo antes de leer el encabezado.
- Endurecer parser del mmap Multiboot.
- Endurecer aritmética del bump allocator.
- Separar los cambios del loader del rediseño futuro de direccionamiento para modelos grandes.

### Fase D — regresión
- Fixtures válidos v1/v2 y archivos truncados de 0, 4, 127 y 128 bytes.
- Magic/version/flags inválidos.
- Tamaño declarado inferior/superior al real.
- Offsets al final del archivo, fuera del archivo, solapados y con overflow.
- Dimensiones cero, divisibilidad GQA inválida, K fuera de límites.
- Stride inferior al mínimo y capas que exceden el archivo.
- Mapas Multiboot con entradas truncadas, tamaños menores al mínimo, longitudes inconsistentes y sumas desbordadas.
- Arena cero, alineación desbordada, heap inconsistente y asignación justo en el límite.
- Regresión válida con Qwen3-0.6B antes de probar Qwen3-4B.

## 10. Estado y límites de esta auditoría

- Es una inspección estática del commit upstream fijado.
- No se han modificado los archivos NASM upstream ni el clon de referencia.
- No se ha compilado ni ejecutado un loader modificado.
- No se ha descargado ni exportado ningún modelo adicional.
- No se ha pedido intervención del MSI.
- Los hallazgos describen ausencia de defensas observables en el código revisado; no afirman que un checkpoint válido actual falle necesariamente.

**Conclusión:** el siguiente cambio debe ser una capa explícita de validación nativa en `shared/transformer.asm`, con pruebas sintéticas y compilación aislada. El runtime bare-metal requiere una segunda línea de endurecimiento independiente. No debe iniciarse todavía la exportación de Qwen3-4B.
