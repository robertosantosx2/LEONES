# Picchio — subproyecto de LEONES

**Estado:** implementación de registro CUDA pinned-host subida al fork; pendiente de compilación y validación en la MSI RTX 3050. La mejora no se considera validada ni se le atribuye aceleración todavía.

## 1. Repositorios y ramas

- Upstream: https://github.com/benmaster82/picchio
- Fork de desarrollo: https://github.com/robertosantosx2/picchio
- Rama experimental: [`feature/cuda-pinned-host-slabs`](https://github.com/robertosantosx2/picchio/tree/feature/cuda-pinned-host-slabs)
- PR de código: [#1 — bounded CUDA-pinned host registration](https://github.com/robertosantosx2/picchio/pull/1)
- Último commit de código registrado: `aa15756f19da5951f10d73768880c7df05937e14` (rama experimental).
- Informe actualizado en LEONES: commit `5c613f34ea1751b18b8f1a2707d48f433f9a4343`; índice actualizado en `3fd7e71b73fede804d14837735936496abe4cf93`.
- Rama de documentación LEONES: `subproject/picchio-bootstrap-2026-11-08`
- Rama local de investigación: `~/picchio-lab`

El código se desarrolla en el fork. El upstream permanece intacto. LEONES conserva el diseño, la metodología, las métricas y las evidencias; no se copia el código fuente al repositorio de documentación ni se declara un submódulo hasta decidir y validar una revisión concreta.

## 2. Plataforma de referencia

- MSI Thin 15 B12UC.
- Intel Core i7-12650H, 16 CPU lógicas.
- NVIDIA RTX 3050 Laptop, 4 GiB VRAM, compute capability `sm_86`.
- Driver NVIDIA 580.178.04; CUDA Toolkit 13.4.
- Ubuntu 26.04.1 LTS, kernel 7.0.0-42-generic.
- Memoria observada por el sistema: aproximadamente 14 GiB; la configuración física consultada mostró un módulo DDR4-3200 de 8 GB y dos ranuras posibles. Revisar la discrepancia antes de dimensionar buffers pinned de mayor tamaño.
- Swap configurada: 32 GiB. El swap no debe contarse como RAM física disponible para memoria pinned.

## 3. Modelo y configuración de referencia

- Modelo: Qwen/Qwen3-30B-A3B-Instruct-2507, convertido a INT4.
- Directorio de datos local: `/home/ssantos/picchio-data/qwen3-30b-a3b-int4`.
- 16 shards SafeTensors; tamaño aproximado 20,6 GB.
- 48 capas MoE; 128 expertos por capa; top-8.
- Hidden dimension 2048; dimensión intermedia MoE 1536.
- Expertos INT4, group size 64; gate/up fusionados.
- Contexto de prueba: 512; generación máxima configurada: 128 tokens.
- Caché host con `--pin-gb 4` (este presupuesto de Picchio es caché host normal, no CUDA pinned memory).

Un slab de experto reutilizable ocupa aproximadamente 2,546 MiB incluyendo los datos auxiliares descritos en la inspección. El payload de pesos y escalas es aproximadamente 2,532 MiB. El tamaño real depende del layout y de los biases.

## 4. Resultados de referencia — MEASURED

### CPU baseline

Pruebas comparables con `FLAT=0`, contexto 512, `--pin-gb 4`, 4 threads CPU, 4 I/O threads, máximo 128 tokens y `--no-reasoning`.

| Ejecución | Tiempo | Rendimiento |
|---|---:|---:|
| CPU 1 | 57,0 s | 2,2 tok/s |
| CPU 2 | 65,2 s | 2,0 tok/s |
| CPU 3 | 70,3 s | 1,8 tok/s |
| Media temporal | 64,2 s | — |
| Mediana temporal | 65,2 s | — |

La caché registró aproximadamente 79 % de aciertos; 10,8–11,1 mil lecturas de disco; RSS aproximado de 9,35 GB. Estas cifras son una referencia de las ejecuciones ya realizadas, no una garantía de rendimiento futuro.

### Backend CUDA de expertos — antes de pinned-host

| Ejecución | Tokens | Tiempo | Rendimiento |
|---|---:|---:|---:|
| CUDA 1 | 125 | 78,0 s | 1,6 tok/s |
| CUDA 2 | 108 | 57,2 s | 1,9 tok/s |
| CUDA 3 | 86 | 48,5 s | 1,8 tok/s |

- Caché de expertos en VRAM: aproximadamente 70,3–71,5 % de hit.
- Pesos residentes: aproximadamente 3,24 GB.
- Monitorización: framebuffer máximo observado 3760 MiB; uso SM variable, normalmente 0–38 %; memoria GPU 0–2 %; potencia 7–9 W; temperatura máxima observada 55 °C.
- Conclusión: la ruta CUDA funciona y ejecuta cómputo real, pero las pruebas iniciales no demuestran ventaja frente a CPU (CPU: 1,8–2,2 tok/s; CUDA: 1,6–1,9 tok/s).

No atribuir las diferencias a una causa única: las muestras son pocas y los tiempos/tokens generados no son idénticos.

## 5. Diagnóstico técnico y cuello de botella probable

La inspección del código y de las trazas permite identificar costes potenciales; no demuestra todavía cuánto aporta cada uno al tiempo total:

1. **H2D síncrono:** los pesos de experto que no están en la caché VRAM se transfieren mediante `cudaMemcpy(..., cudaMemcpyHostToDevice)`.
2. **Memoria host pageable:** los slabs reutilizables se asignan alineados, pero originalmente no se registraban como CUDA pinned. El runtime puede necesitar staging interno para transferirlos.
3. **Asignaciones CUDA y LRU:** cada miss puede implicar varios `cudaMalloc`, transferencias y una evicción LRU; `cudaFree` puede introducir sincronización.
4. **Hit ratio VRAM incompleto:** con aproximadamente 70 % de hit, siguen existiendo misses que requieren upload.
5. **Demasiados lanzamientos pequeños:** top-8 ejecuta cuatro kernels por experto (gate/up, SwiGLU, down y acumulación), más el kernel de inicialización del acumulador. Son aproximadamente 33 lanzamientos por capa MoE y 1584 por token para 48 capas, sin contar otros kernels.
6. **Sin solapamiento H2D/compute en esta ruta:** las copias actuales son síncronas y no se usan streams CUDA para solapar transferencias con cómputo.
7. **La GPU no parece saturada:** las muestras de SM, memoria y potencia no muestran utilización sostenida alta. No es evidencia suficiente para descartar límites de CPU, sincronización, ancho de banda o coste de lanzamiento.

## 6. Propuesta de mejora — plan completo

### Fase A — pinned host slabs, conservando sincronía (implementada en el fork; pendiente de prueba)

Objetivo: evitar staging pageable en las transferencias H2D de los expertos que salen de los slabs reutilizables.

- Registrar los slabs host con `cudaHostRegister` y `cudaHostRegisterPortable`.
- Mantener una cuota agregada máxima de 128 MiB, independiente del presupuesto `PIN_GB` de la caché host.
- Exigir alineación de 4 KiB; rechazar rangos no alineados sin comprometer la inferencia.
- Mantener memoria pageable como fallback automático cuando el registro falle o se alcance el límite.
- Evitar registrar repetidamente el mismo slab: guardar el estado pinned en el propio `ESlot`.
- Reintentar en un uso posterior si un intento falló; no penalizar permanentemente ese slab.
- Desregistrar antes de liberar un slab; conservar el registro cuando el slab reutilizable se recicla.
- Limpiar registros pendientes al apagar el backend.
- Proteger el registro global con mutex, contabilizar bytes activos/pico y fallos.
- Añadir prueba independiente `PGPU_PINNED_TEST` para registro, idempotencia, desregistro, alineación y límite.
- Mantener `cudaMemcpy` síncrono; no introducir streams ni `cudaMemcpyAsync` en esta fase.

**Criterio de aceptación:** self-test CUDA correcto, sin registros huérfanos, fallback pageable correcto y ejecución de inferencia estable. Después, comparar A/B con el backend anterior usando el mismo prompt, contexto, tokens, semilla y estado de caché.

### Fase B — medición del coste de misses y gestión VRAM (siguiente)

- Instrumentar por separado tiempo de `cudaMalloc`, H2D, kernels, D2H y evicción.
- Registrar bytes subidos, misses, hit ratio, número de evicciones y tiempo de sincronización.
- Comparar política LRU actual con una política que proteja los expertos activos del token y favorezca reutilización temporal.
- Evaluar asignación de bloques/pool de memoria GPU para reducir `cudaMalloc/cudaFree` en el camino crítico.
- No aumentar el presupuesto VRAM por encima de lo que permita la RTX 3050 de 4 GiB y el escritorio.

### Fase C — transferencia asíncrona y solapamiento (no implementada)

- Introducir streams y `cudaMemcpyAsync` solo cuando la Fase A esté validada.
- Separar explícitamente buffers host/device y establecer eventos para impedir que el loader recicle un slab mientras la transferencia está en curso.
- Diseñar doble buffering o pipeline de expertos seleccionados.
- Medir si el solapamiento real compensa la complejidad y el coste de sincronización.
- Mantener fallback síncrono en caso de error.

### Fase D — reducir lanzamientos de kernels (no implementada)

- Evaluar fusión de kernels por experto: gate/up + activación SwiGLU y/o down + acumulación.
- Explorar procesamiento por lote de expertos top-k cuando el layout y la precisión lo permitan.
- Validar equivalencia numérica CPU/CUDA antes de medir velocidad.
- Reducir overhead de lanzamiento sin cambiar la semántica de router, escalado ni acumulación.

### Fase E — benchmark y decisión

- A/B con la misma versión del modelo, prompt, seed, contexto, número de tokens y estado de caché.
- Al menos 3 ejecuciones por variante, separando warm-up y mediciones.
- Registrar tok/s de decode, latencia total, prefill, RSS, RAM pinned, VRAM, hit/miss, potencia y temperatura.
- Comparar contra CPU baseline y biblioteca CUDA previa.
- Promover a rama estable solo si la precisión y la estabilidad se mantienen y la mejora es repetible.

## 7. Implementación actual en el fork

Rama: `feature/cuda-pinned-host-slabs`; PR [#1](https://github.com/robertosantosx2/picchio/pull/1).

Archivos modificados:

- `picchio_cuda.h`: API pública opcional de registro/desregistro y contrato de alineación, límite y fallback.
- `picchio_cuda.cu`: registro global protegido por mutex, límite 128 MiB, comprobación de alineación, registro idempotente, rollback si falla la reserva de bookkeeping, errores de desregistro visibles, contadores y pico de memoria pinned, limpieza en shutdown y self-test `PGPU_PINNED_TEST`.
- `picchio.c`: estado `slab_cuda_pinned` por `ESlot`; registro una sola vez tras éxito; reintento si falla; desregistro antes de liberar; el backend antiguo sigue siendo compatible porque los símbolos se resuelven opcionalmente con `dlsym`.

### Estado de validación

- [x] Diseño y cambios de código subidos a la rama experimental del fork.
- [x] PR de código abierta para revisión.
- [x] Informe y metodología archivados en este subproyecto.
- [ ] Compilar con CUDA Toolkit 13.4 en Ubuntu.
- [ ] Ejecutar `PGPU_PINNED_TEST` en la RTX 3050.
- [ ] Ejecutar inferencia real con la biblioteca experimental en un directorio aislado.
- [ ] Comparar A/B frente a la biblioteca CUDA anterior y CPU baseline.
- [ ] Revisar estabilidad, limpieza de registros y métricas.
- [ ] Decidir si se integra la PR.

**No se ha compilado ni ejecutado todavía este código en la MSI.** Los cambios se han realizado en GitHub; no se ha modificado `~/picchio-lab`, el ejecutable `./picchio` ni `/tmp/libpicchio_cuda.so`. La PR no está mergeada.

## 8. Procedimiento seguro para la validación local

1. Confirmar remotos, rama y estado de `~/picchio-lab` antes de cualquier operación Git.
2. No hacer checkout ni reset sobre un árbol local con cambios.
3. Crear un clon o worktree aislado del fork y de la rama experimental.
4. Inspeccionar el Makefile y las dependencias antes de compilar.
5. Compilar la biblioteca experimental con nombre y ruta separados; usar un directorio de prueba aislado para que el loader resuelva allí su `libpicchio_cuda.so`.
6. Mantener intacta la biblioteca funcional `/tmp/libpicchio_cuda.so` y el ejecutable CPU.
7. Ejecutar primero self-test; solo si pasa, realizar inferencia controlada.
8. Archivar logs, SHA de commit, configuración, métricas y resultado A/B en LEONES.

## 9. Referencias

- [Repositorio upstream](https://github.com/benmaster82/picchio)
- [Fork de desarrollo](https://github.com/robertosantosx2/picchio)
- [Rama experimental](https://github.com/robertosantosx2/picchio/tree/feature/cuda-pinned-host-slabs)
- [PR de implementación](https://github.com/robertosantosx2/picchio/pull/1)
- [LEONES — subproyectos](../README.md)
