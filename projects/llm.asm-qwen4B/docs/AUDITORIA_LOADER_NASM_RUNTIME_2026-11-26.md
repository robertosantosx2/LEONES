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

**Conclusión:** existe ahora un guard ASMBIN NASM aislado con cobertura sintética amplia y CI verde, pero todavía no está conectado a `model_init`. El siguiente cambio debe ser una integración controlada solo después de cerrar las lagunas documentadas y añadir pruebas de `model_init` en Linux y BARE_METAL. El runtime bare-metal requiere una segunda línea de endurecimiento independiente. No debe iniciarse todavía la exportación de Qwen3-4B.


## 11. Validador NASM aislado y cobertura actual (27-11-2026)

Se ha añadido una primera implementación independiente en:

- `projects/llm.asm-qwen4B/tools/asmbin_validate.asm`
- `projects/llm.asm-qwen4B/tests/test_asmbin_validate.asm`

ABI: `int64 asmbin_validate(const void *base, uint64 actual_size)`, SysV x86-64 (`RDI=base`, `RSI=actual_size)). Devuelve cero o un error negativo; rechaza base nula y cabeceras truncadas antes de leer. El harness comprueba preservación de registros callee-saved y equilibrio de la pila.

La rutina comprueba:

- Magic, versiones v1/v2, flags conocidos y coherencia de escalas FP32/FP16.
- Tamaño declarado frente al tamaño real, bytes reservados de la cabecera y escalares FP32 positivos/finito.
- Dimensiones, GQA, EOS, límites Q8 y relaciones dimensionales.
- Alineación de 64 bytes, orden y extensiones de secciones, stride exacto de capa y final alineado del archivo.
- Layout canónico del tokenizer, offsets monótonos, límites de byte-to-token y tabla BPE.
- IDs/ranks BPE dentro del vocabulario, ranuras vacías canónicas, slot Fibonacci, cadenas de sondeo lineal sin huecos y claves duplicadas en la cadena.

El `layer_stride` se recalcula desde los cuatro vectores de normas y las siete matrices Q8 en el orden del exportador, con row-bytes específicos de v1/v2. La cadena de sondeo BPE se limita a 128 posiciones para acotar el coste.

El harness genera un fixture sintético de aproximadamente 9,7 MB, con layouts canónicos v1/v2 y un cluster BPE de colisión válido. Incluye casos negativos de puntero nulo, escalares no finitos/no positivos, cabecera truncada, offsets fuera de rango, secciones desalineadas, stride incorrecto, tokenizer no canónico, byte IDs inválidos, offsets no monótonos, BPE IDs/ranks inválidos, clave duplicada y cadena de sondeo rota.

Se ha añadido `tools/asmbin_validate_cli.c`: CLI Linux de solo lectura que mapea un archivo con `mmap(PROT_READ)` y llama al guard NASM. CI compila y enlaza el CLI, y comprueba que rechaza un archivo truncado con estado de salida 1. La validación sobre el ASMBIN real Qwen3-0.6B todavía está pendiente en el MSI.

**CI confirmada:** [run 45980051650](https://github.com/robertosantosx2/LEONES/actions/runs/45980051650). Los 20 tests Python pasan; el harness NASM se ensambla, enlaza y ejecuta con exit code 0; el upstream fijado compila con `FAST_Q8=1` y `FAST_Q8=0`. También pasan los gates completos V1, runtime-v1.1, RC4 y regresión general.

**Limitaciones explícitas:** no se comprueba unicidad/continuidad global de ranks, semántica de merges respecto al tokenizer original, ni todos los valores y subrangos de cada tensor. El límite de 128 probes es una política de esta implementación, no una propiedad universal del formato. No se ha integrado en `model_init`, no se ha compilado un loader upstream modificado y no se ha ejecutado ningún modelo adicional.

## 12. Punto de integración recomendado en model_init

En el commit upstream auditado, las dos rutas convergen con:

- `R15`: base del ASMBIN ya mapeado (Linux) o base del módulo Multiboot (BARE_METAL).
- `R14`: tamaño real del mapping/módulo.

El punto seguro es **inmediatamente después de la convergencia de ambas rutas y antes de la primera lectura de `[R15 + HDR_MAGIC]`**, antes de llamar a `matmul_set_fp16`, copiar dimensiones al contexto o resolver cualquier puntero. La llamada prevista es:

```nasm
    mov     rdi, r15
    mov     rsi, r14
    call    asmbin_validate
    test    rax, rax
    js      .err_asmbin
```

Requisitos para una futura integración:

1. Añadir el objeto NASM al build de Linux y BARE_METAL y resolver el símbolo sin duplicar la implementación.
2. Preservar el código de error del validador al liberar recursos. En Linux, desmapear `[R15,R15+R14)`; en BARE_METAL, usar la ruta de limpieza del módulo/arena (el `sys_munmap` upstream es no-op en el bump arena).
3. Confirmar que el validador preserva los registros callee-saved usados por `model_init`, en particular `R12` (`max_seq_override`).
4. Añadir pruebas de integración con fixtures válidos e inválidos a través de `model_init`, incluyendo que un fallo no deje `g_ctx` parcialmente inicializado ni cambie el modo FP16 global.
5. Mantener el guard antes de cualquier efecto global o resolución de punteros.

**No integrar todavía:** el guard actual sigue siendo parcial en ranks y semántica BPE. Primero cerrar esas limitaciones o documentar formalmente su aceptación, después ejecutar pruebas de loader Linux y BARE_METAL. No se necesita el MSI para preparar esta integración; será necesario para validar con el artefacto real Qwen3-0.6B y, más adelante, modelos mayores.
