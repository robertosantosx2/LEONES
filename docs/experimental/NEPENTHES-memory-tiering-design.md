# NEPENTHES — diseño de memoria jerárquica y ejecución out-of-core

**Estado:** diseño técnico propuesto; no es una implementación runtime.  
**Relacionado:** [hoja de ruta de rendimiento y capacidad](NEPENTHES-performance-capacity-roadmap.md) · [issue #148](https://github.com/robertosantosx2/LEONES/issues/148).

## 1. Objetivo

Permitir que un runtime ejecute un modelo cuyo conjunto de pesos supera la VRAM disponible y, cuando sea técnicamente posible, también la RAM disponible. La estrategia debe intercambiar rendimiento por capacidad de forma explícita, predecible y observable.

El requisito no es «que nunca falle». Es:

- Detectar pronto si una arquitectura/operación no es compatible.
- Respetar presupuestos de memoria por nivel.
- Mantener progreso cuando existe una ruta válida de transferencia y cómputo.
- Aplicar backpressure antes de agotar recursos.
- Fallar con diagnóstico recuperable cuando la ejecución no sea viable.
- No corromper pesos, estado KV ni resultados.

## 2. Niveles y responsabilidades

| Nivel | Recurso | Uso propuesto | Riesgo principal |
|---|---|---|---|
| L0 | VRAM | Kernels, working set activo, buffers GPU y cache caliente | OOM/fragmentación |
| L1 | RAM | Pesos staging, cache de bloques, buffers host y metadatos | Presión del sistema |
| L2 | SSD/HDD | Fuente persistente de bloques/pesos y backing store | I/O lento y latencia |
| L3 | Swap | Respaldo administrado por el kernel, no cache explícita del runtime | Thrashing y latencias impredecibles |

El runtime debe contabilizar por separado pesos, KV cache, activaciones, scratch/workspace, staging, metadatos y caches. No usar una sola cifra de «memoria del modelo».

## 3. Presupuesto de memoria

Antes de cargar o aceptar una petición, estimar y después medir:

- VRAM total, libre y reserva del runtime.
- RAM física disponible y presupuesto máximo del proceso.
- Tamaño de pesos por tensor/bloque y formato.
- KV cache según contexto, batch, secuencias y arquitectura.
- Scratch y buffers temporales por operador.
- Memoria pinned y límites de staging.
- Overhead de allocator, fragmentación y CUDA Graphs.
- Espacio de almacenamiento y ancho de banda disponible.

El presupuesto debe incluir margen configurable. Nunca asumir que «memoria libre observada» seguirá libre al iniciar la petición.

## 4. Unidad de paginación y residencia

La unidad puede ser tensor, shard, bloque, capa o experto según restricciones del formato y backend. Debe ser suficientemente grande para evitar miles de operaciones minúsculas, pero suficientemente pequeña para caber en los presupuestos y permitir eviction útil.

Cada unidad necesita un descriptor con:

- Identidad estable (modelo, tensor/bloque/capa/experto).
- Offset y tamaño en el archivo.
- Formato/dtype y alineación.
- Estado de residencia L0/L1/L2.
- Referencias activas y evento de último uso.
- Operaciones en vuelo y dependencias.
- Versión/hash cuando sea posible.
- Estado: absent, loading, ready, in_use, evict_pending, error.

La transición de estado debe ser segura frente a concurrencia. No expulsar un bloque mientras un kernel o transferencia lo está usando.

## 5. Política de cache

Políticas a comparar, no asumir una ganadora:

- LRU: baseline sencillo; puede fallar ante scans secuenciales.
- LFU/decay: favorece expertos recurrentes; requiere controlar el envejecimiento.
- LRU-K / frecuencia + recencia: combina reutilización y localidad temporal.
- Cache particionada: reserva espacio para hot set y deja cuota para streaming.
- Cache MoE informada por routing: usa trazas de expertos, con prefetch condicionado a confianza.

Toda política debe tener límites duros por nivel, contadores hit/miss/eviction, bytes y latencia. Evitar oscilación de bloques y thrashing.

## 6. Prefetch y pipeline

Pipeline candidato:

1. El planificador determina el siguiente conjunto de unidades.
2. Comprueba residencia y dependencias.
3. Reserva espacio de destino con presupuesto.
4. Emite lectura L2→L1 y/o transferencia L1→L0 asíncrona.
5. Marca evento de disponibilidad.
6. El consumidor espera solo si el bloque no está listo.
7. Tras el último uso, actualiza recencia/frecuencia y libera referencias.
8. Eviction se ejecuta cuando el bloque no está en uso ni en vuelo.

Medir por separado tiempo de lectura, transferencia, espera del consumidor y tiempo de cómputo solapado. No afirmar solapamiento si el timeline no lo demuestra.

Prefetch debe poder cancelarse, limitarse y retroceder cuando el patrón de acceso no se confirma. Nunca llenar VRAM/RAM con predicciones especulativas sin cuota.

## 7. Backpressure y degradación controlada

Cuando no haya espacio:

1. Intentar reutilizar una unidad ya residente.
2. Esperar a que terminen referencias en vuelo.
3. Evictar unidades elegibles según política.
4. Reducir prefetch y concurrencia.
5. Serializar operaciones para disminuir working set.
6. Usar streaming directo desde L2 si el backend lo permite.
7. Reducir contexto/batch solo si el usuario o configuración lo permite.
8. Devolver un error explícito si no existe una ruta compatible.

No reducir silenciosamente precisión, contexto o calidad de salida. Registrar toda degradación.

## 8. Fallos y recuperación

Casos que deben tener tratamiento explícito:

- Fallo de asignación GPU o pinned host.
- Error de lectura, EOF o archivo truncado.
- Hash o metadatos inconsistentes.
- Transferencia asíncrona fallida.
- Eviction concurrente con consumidor.
- Cancelación durante carga.
- Memoria disponible que cae externamente.
- Almacenamiento lleno o desconectado.
- Operador que requiere tensor completo y no admite streaming.
- KV cache mayor que el presupuesto.

La recuperación debe liberar recursos parciales y dejar el runtime en estado conocido. No reintentar indefinidamente OOM ni ocultar errores.

## 9. MoE: expertos como unidades de residencia

Si la arquitectura y el formato lo permiten, tratar expertos como unidades cacheables. Registrar routing por token/capa, hit/miss, prefetch y coste de carga. Mantener siempre disponibles los pesos compartidos y componentes obligatorios del modelo según su contrato.

No asumir que A3B significa que solo 3B de pesos deben residir: los expertos pueden activarse de forma dinámica y el working set depende de routing, contexto y estrategia de cache.

## 10. KV cache y contexto

Los pesos no son el único límite. El KV cache crece con contexto, capas, cabezas KV, dimensión y secuencias. Debe tener presupuesto y política propios.

Investigar:
- cuantización KV cuando esté soportada;
- paginación/bloques de KV;
- reutilización de prefijos;
- eviction solo de estados que el contrato permita descartar;
- offload de KV con latencia medida;
- control explícito de contexto y número de secuencias.

No mezclar memoria de pesos y KV en el mismo contador ni asumir que offload de pesos resuelve el límite de contexto.

## 11. Instrumentación mínima del runtime

Evento estructurado recomendado:

| Campo | Significado |
|---|---|
| timestamp_ns | Reloj monotónico |
| request_id | Petición |
| unit_id | Tensor/bloque/experto/KV |
| operation | read, stage, upload, prefetch, hit, miss, evict, wait, fallback, error |
| source_tier / target_tier | Niveles de memoria |
| bytes | Tamaño |
| duration_ns | Duración |
| queue_wait_ns | Espera antes de iniciar |
| consumer_wait_ns | Espera del consumidor |
| reason | Motivo de decisión |
| status | Resultado |
| memory_before / memory_after | Presupuesto/uso observado, con unidad |

El formato de evento debe versionarse y ser parseable offline. Evitar logs por token demasiado costosos en modo normal; ofrecer niveles de instrumentación.

## 12. Matriz de pruebas

| Prueba | Preparación | Aserción |
|---|---|---|
| Cache hit | Repetir unidad | No vuelve a leer desde nivel inferior |
| Cache miss | Unidad ausente | Carga y transición correctas |
| Eviction | Presupuesto lleno | Solo expulsa unidades sin referencias |
| Prefetch útil | Acceso anticipado conocido | Reduce espera sin exceder cuota |
| Prefetch inútil | Predicción no consumida | Se cancela/expulsa sin bloquear |
| OOM GPU | Presupuesto L0 agotado | Backpressure/eviction/fallback, no corrupción |
| RAM limitada | Presupuesto L1 agotado | Streaming o error temprano |
| I/O lento | Lectura artificialmente lenta en test | Progreso y tiempos contabilizados |
| Cancelación | Cancelar durante carga | Libera recursos y termina en estado estable |
| Integridad | Corromper archivo de fixture | Detecta error y no consume datos inválidos |
| KV pressure | Contexto excede cuota | Control explícito o error recuperable |
| Operador no streaming | Tensor indivisible supera presupuesto | Rechazo temprano y diagnóstico |

## 13. Orden de prototipos

1. Añadir contador y presupuesto de memoria por categoría.
2. Introducir unidad de residencia y estados sin cambiar política por defecto.
3. Probar cache LRU de bloques en CPU con fixtures pequeños.
4. Añadir transferencia asíncrona y referencias seguras.
5. Añadir presupuesto GPU y eviction de unidades no usadas.
6. Añadir streaming L2→L1.
7. Añadir MoE routing-aware cache/prefetch.
8. Añadir política KV independiente.
9. Validar presión de memoria y fallos.
10. Comparar FAST PATH y CAPACITY PATH.

Cada etapa debe ser una PR pequeña, con test y benchmark de control. La política nueva debe poder desactivarse para comparar y hacer rollback.

## 14. Perfil de referencia Ubuntu

La máquina de referencia actual tiene RTX 3050 Laptop de 4 GiB, 14 GiB RAM y 32 GiB swap. Es adecuada para demostrar offload y presión de memoria, pero no para validar rendimiento general ni capacidad máxima de todos los modelos.

Las pruebas locales deberán definir límites conservadores y observar RSS, memoria disponible, swap-in/out, VRAM, I/O y progreso. No ejecutar una prueba de almacenamiento que llene el disco ni una prueba que agote deliberadamente la memoria del escritorio.
