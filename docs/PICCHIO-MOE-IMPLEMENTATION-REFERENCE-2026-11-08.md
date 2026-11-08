# Picchio MoE — Informe técnico consolidado y referencia de implementación

**Fecha de corte:** 2026-11-08  
**Proyecto:** [robertosantosx2/picchio](https://github.com/robertosantosx2/picchio)  
**Repositorio de conocimiento:** [robertosantosx2/LEONES](https://github.com/robertosantosx2/LEONES)  
**Estado:** investigación y diseño consolidados; implementación experimental pendiente de validación física.  
**Propósito de este documento:** ser la referencia principal para decidir, implementar, probar y documentar las siguientes mejoras de Picchio MoE. No es una declaración de que las mejoras propuestas estén implementadas ni aceptadas.

---

## 1. Resumen ejecutivo

Picchio busca ejecutar modelos Mixture-of-Experts (MoE) grandes en equipos modestos, combinando almacenamiento, RAM, CPU y VRAM. La máquina de referencia es un MSI Thin 15 B12UC con RTX 3050 Laptop de 4 GiB. El modelo experimental principal es Qwen3-30B-A3B-Instruct-2507 convertido a INT4, aproximadamente 20,6 GB distribuidos en 16 shards.

La investigación reciente ha comparado el estado actual de Picchio con dos proyectos externos:

- **TensorFold:** ideas de gestión explícita de memoria, transferencias asíncronas, ownership de buffers, eventos CUDA, concurrencia y admisión de trabajo.
- **tandem.cpp:** ejecución híbrida por experto, reparto CPU/GPU de los misses, prefetch de expertos de la siguiente capa y kernels CPU agrupados.

La conclusión central es que Picchio ya contiene piezas importantes —caché LRU de expertos en host, slots reutilizables, lectura paralela, AsyncLoader, prefetch host de la siguiente capa, caché LRU de expertos en VRAM y registro opcional de slabs pinned—, por lo que no conviene sustituirlas por otra caché o loader. La oportunidad está en cerrar el ciclo de vida de los datos y solapar las operaciones que hoy son síncronas.

**Orden recomendado:**

1. Instrumentar con precisión el flujo de expertos y la presión de memoria.
2. Implementar prefetch host→VRAM asíncrono de expertos de la siguiente capa, con stream CUDA separado, eventos y ownership explícito.
3. Mantener siempre una ruta síncrona de fallback.
4. Validar corrección, ausencia de carreras y mejora real mediante A/B en el equipo objetivo.
5. Solo después estudiar el reparto híbrido CPU/GPU por experto.
6. Adaptar el patrón de kernels CPU agrupados a los formatos INT4/INT3 de Picchio si los perfiles lo justifican.
7. Posponer doorbell/host-add, speculative decoding, MTP y otras arquitecturas complejas.

No se debe aumentar el límite de memoria pinned ni asumir una mejora de rendimiento antes de medir. Tampoco se deben extrapolar al MSI los benchmarks publicados por tandem.cpp o TensorFold en hardware de gama alta.

---

## 2. Alcance, procedencia y reglas de evidencia

Este informe consolida:
- el estado de Picchio y las pruebas locales comunicadas hasta la fecha;
- el diagnóstico de pinned host memory;
- la revisión arquitectónica de TensorFold;
- la revisión de tandem.cpp;
- las propuestas de adaptación y su orden de implementación;
- los riesgos, criterios de aceptación y plan de pruebas.

La revisión de TensorFold y tandem.cpp se centró en sus repositorios, documentación, árboles de código y módulos relevantes para memoria, transferencias, cachés, MoE, prefetch, kernels y benchmark. No debe interpretarse como una auditoría línea por línea de todos los archivos de esos proyectos ni de todo llama.cpp.

### 2.1 Etiquetas obligatorias

| Etiqueta | Significado |
|---|---|
| **MEASURED — MSI** | Resultado de una ejecución física en el equipo de referencia, con comando y condiciones conocidos. |
| **SELF-TEST — MSI** | Prueba local de funciones o kernels sintéticos; no demuestra rendimiento de inferencia. |
| **CI — GitHub** | Prueba ejecutada en runner alojado; no demuestra compatibilidad CUDA con la RTX 3050. |
| **SOURCE / EXTERNAL** | Dato o mecanismo descrito por un proyecto externo. |
| **ESTIMATED** | Hipótesis o cálculo aún no medido. |
| **PROPOSED** | Diseño recomendado, todavía no implementado o aceptado. |
| **PENDING** | Requiere prueba, inspección o validación adicional. |

No convertir claims de proyectos externos, resultados de CI ni estimaciones en mediciones LEONES.

---

## 3. Plataforma de referencia y restricciones

### 3.1 Hardware

- Portátil: MSI Thin 15 B12UC.
- CPU: Intel Core i7-12650H, 16 CPU lógicas.
- RAM observada en las sesiones: aproximadamente 14 GiB utilizables/visibles en `free -h`; inventario DMI previo mostraba un módulo DDR4-3200 de 8 GB y dos slots, con capacidad máxima declarada de 64 GB. Los valores de RAM deben volver a capturarse en cada campaña porque el entorno y el uso de swap pueden variar.
- GPU: NVIDIA RTX 3050 Laptop, 4 GiB VRAM, compute capability sm_86.
- Driver observado: 580.178.04; CUDA 13.x.
- Sistema: Ubuntu 26.04.1 LTS en las sesiones recientes.
- Swap: archivo `/swap32.img` de 32 GiB; no debe confundirse capacidad de swap con RAM disponible.

### 3.2 Modelo de referencia

- Qwen/Qwen3-30B-A3B-Instruct-2507.
- Conversión INT4 local, alrededor de 20,6 GB.
- 16 shards safetensors.
- Arquitectura observada: `Qwen3MoeForCausalLM`, hidden_size 2048, moe_intermediate_size 768, 48 capas, 128 expertos, top-8, vocab_size 151936.
- Los shards físicos siguen el patrón `model-xxxxx.safetensors`, sin sufijo `-of-00016`; el índice JSON no reflejaba exactamente los nombres físicos.
- El modelo supera ampliamente la VRAM y la RAM disponible; por ello, el tráfico de almacenamiento y la política de residencia son parte crítica del rendimiento.

### 3.3 Protecciones operativas

1. No modificar ni sobrescribir el ejecutable CPU baseline `~/picchio-lab/picchio`.
2. No sobrescribir la biblioteca CUDA funcional original `/tmp/libpicchio_cuda.so`.
3. No sobrescribir `~/picchio-pinned-test/libpicchio_cuda.so`.
4. Hacer builds experimentales en rutas separadas y conservar artefactos previos.
5. No ejecutar experimentos de gran presión de RAM sin revisar primero memoria, swap y procesos.
6. No instalar dependencias Python globalmente; el entorno de proyecto disponible es `~/picchio-lab/.venv`.
7. La validación final CUDA debe ejecutarse en la RTX 3050 real; un runner CPU de GitHub Actions no sustituye esa prueba.
8. En las sesiones de implementación remota, mantener los cambios en ramas aisladas y no tocar Ubuntu hasta que se solicite la campaña local.

---

## 4. Estado actual de Picchio

### 4.1 Componentes ya existentes

Picchio ya dispone de:
- caché host LRU para expertos;
- slots y buffers reutilizables;
- lectura paralela de expertos desde disco;
- AsyncLoader;
- prefetch host de la siguiente capa;
- caché LRU de expertos en VRAM;
- backend CUDA para operaciones MoE;
- ruta CPU de aplicación de expertos;
- registro opcional de slabs host con CUDA pinned memory;
- fallback a memoria pageable cuando el registro pinned no es posible.

Por tanto, no se recomienda crear una segunda caché host, un segundo loader general ni un segundo sistema LRU. Las nuevas piezas deben integrarse en el ciclo de vida actual y conservar sus invariantes.

### 4.2 Particularidades de la carga de expertos

En el worktree experimental se corrigió la búsqueda de nombres físicos de tensores para localizar entradas como:

`model.layers.%d.mlp.experts.%d.%s%s`

La función `expert_load_reusable` activa `slab_reusable=1`, crea slabs alineados y lee directamente tensores; gate_up y down manejan sus escalas. `free_slot_buffers` llama a `pgpu_host_unregister` antes de liberar slabs registrados. Estos detalles son relevantes para no introducir use-after-free cuando se añadan transferencias asíncronas.

### 4.3 Baseline de inferencia CPU

Configuración observada:
- `FLAT=0`
- `--ctx 512`
- `--pin-gb 4`
- `--threads 4`
- `--io-threads 4`
- `--max-tokens 128`
- `--no-reasoning`

Tres ejecuciones:
- 57,0 s (2,2 tok/s)
- 65,2 s (2,0 tok/s)
- 70,3 s (1,8 tok/s)

Resumen: media aproximada 64,2 s, mediana 65,2 s; cache hit alrededor del 79%; entre 10,8k y 11,1k lecturas de disco; RSS alrededor de 9,35 GB. La RTX no participó en esta ruta.

**Interpretación:** baseline de referencia válido para comparar bajo condiciones equivalentes; no es un límite universal de CPU ni garantiza que cada ejecución futura reproduzca esos tiempos.

### 4.4 Backend CUDA de expertos existente

Configuración relevante:
- `GPU_EXPERTS=1`
- `FLAT=0`
- router, dense y lmhead en CPU.

Ejecuciones observadas:
- 125 tokens / 78 s / 1,6 tok/s.
- 108 tokens / 57,2 s / 1,9 tok/s.
- 86 tokens / 48,5 s / 1,8 tok/s.

Cache hit GPU alrededor del 70%, unos 3,24 GB residentes. Durante las muestras de `nvidia-smi dmon`, utilización SM variable de 0–38%, memoria de 0–2%, potencia 7–9 W y temperatura cercana a 55 °C.

**Interpretación:** el offload CUDA de expertos funciona, pero no ha demostrado superar el baseline CPU. Las muestras no apuntan a saturación sostenida de GPU o límite térmico; el acceso a pesos, transferencias, misses y sincronización son sospechosos que deben instrumentarse, no causas ya demostradas.

### 4.5 Prueba pinned experimental

Dos ejecuciones de inferencia corta:
- 8 tokens, 18,9 s, 0,42 tok/s.
- 8 tokens, 26,8 s, 0,30 tok/s.

Ambas mostraron:
- contexto 30/512;
- reutilización de expertos 0%;
- cache hit 1052/4502 = 23,4%;
- 3450 lecturas de disco;
- RSS alrededor de 7,8–8,1 GB;
- dense alrededor de 4,30 GB;
- caché VRAM: 1485 hits / 1292 misses (53,5%), unos 3,24 GB.

Los tiempos de atención y MoE variaron entre ejecuciones. La segunda fue más lenta. Son pruebas diagnósticas de solo ocho tokens, no benchmarks estables y no demuestran mejora.

### 4.6 Self-test sintético

El ejecutable experimental `./picchio --self-test` pasó:
- forward sintético;
- RMSNorm;
- softmax;
- matmul F32;
- SiLU;
- async MoE byte-identical;
- RoPE;
- cuantización/matmul INT4 e INT3;
- pipeline split.

**Interpretación:** cobertura funcional sintética útil. No equivale a validar la nueva ruta CUDA pinned sobre el modelo real.

---

## 5. Diagnóstico de CUDA pinned host memory

### 5.1 Diseño implementado en la rama experimental

En `picchio_cuda.cu`:
- API opcional `pgpu_host_register` / `pgpu_host_unregister`;
- límite global de 128 MiB;
- slabs alineados a 4 KiB;
- mutex para `g_host_regs` y accounting;
- fallback a pageable memory si el registro falla;
- registro idempotente;
- estado de slot: 0 pending, 1 registered, -1 failed;
- un intento de registro por vida del slab;
- unregister antes de liberar el slab;
- `host_reg_fits` con comprobación de overflow;
- autotest `PGPU_PINNED_TEST` para registro, duplicados, unregister, alineación y límite.

Importante: **pinned no significa transferencia asíncrona**. En la implementación medida, las transferencias siguen usando `cudaMemcpy` síncrona; todavía no hay un pipeline de `cudaMemcpyAsync` con stream/eventos.

### 5.2 Diagnóstico instrumentado medido

Se construyó una biblioteca diagnóstica separada en `/tmp/libpicchio_cuda_diag.so`, sin sobrescribir la biblioteca funcional original.

Ejecución de ocho tokens:
- 17,5 s, 0,46 tok/s;
- cache hit 1052/4502 = 23,4%;
- 3450 lecturas de disco, 10,47 s acumulados;
- t_attn 2,87 s;
- t_moe 14,37 s;
- t_head 0,11 s;
- RSS 8,07 GB;
- 50 slabs registrados, 1277 fallidos;
- peak 127,3 MiB / 128 MiB.

Contadores de causa:
- cap: 1277;
- alignment: 0;
- CUDA: 0;
- bookkeeping: 0.

**Conclusión demostrada:** todos los fallos de registro observados fueron rechazos por el límite de 128 MiB. No se observaron fallos de CUDA, alineación ni bookkeeping en esa ejecución.

**Lo que no demuestra:** que subir el límite mejore tok/s, que todos los slabs sean útiles para DMA, ni que haya RAM suficiente para mantener más memoria pinned sin perjudicar el sistema.

### 5.3 Instrumentación adicional pendiente de medir

Se añadieron al código contadores de:
- intentos de registro;
- bytes solicitados acumulados;
- bytes bloqueados por el límite;
- tamaño mínimo y máximo de petición.

El log esperado será similar a:

`[gpu] pinned requests: <n> slabs, <total MiB> total, min <MiB>, max <MiB>; cap-blocked <MiB>`

Esta instrumentación está en GitHub, pero todavía no se ha construido y ejecutado en el equipo objetivo a fecha de corte.

### 5.4 Política para el límite pinned

Mantener 128 MiB como baseline. No cambiarlo en la primera implementación de transferencias asíncronas.

Escenarios para una campaña posterior, únicamente si el inventario de peticiones y la memoria disponible los justifican:
- 128 MiB: baseline.
- 192 MiB: +64 MiB.
- 256 MiB: +128 MiB.
- 384 MiB: +256 MiB, solo con evidencia clara de RAM libre y sin presión de swap.

No se atribuye a estos escenarios ninguna mejora de velocidad prevista.

---

## 6. Revisión de TensorFold y adaptaciones

Referencia de código externo: [ashhart/TensorFold](https://github.com/ashhart/TensorFold). Propuesta previa en Picchio: [TENSORFOLD_ADAPTATION_PROPOSAL.md](https://github.com/robertosantosx2/picchio/blob/research/tensorfold-adaptation/docs/TENSORFOLD_ADAPTATION_PROPOSAL.md).

TensorFold es un runtime nativo con rutas Metal/CUDA y subsistemas de memoria, cachés, concurrencia, prompt reuse y ejecución de modelos. Se revisaron especialmente memoria CUDA, transferencias, pools KV, prompt cache, lanes y rutas Qwen3.5.

### 6.1 Ideas aplicables

1. **Ledger unificado de memoria:** contabilizar host pageable, host pinned, VRAM, pesos residentes, staging, buffers temporales y KV. Distinguir capacidad reservada, ocupada y disponible.
2. **Ownership explícito de buffers:** cada buffer en transferencia debe tener propietario y estado inequívoco; no liberar ni reciclar hasta que el evento CUDA confirme la finalización.
3. **Transferencias asíncronas:** separar stream de copias y stream de cómputo, con dependencias mediante eventos.
4. **Admission control:** no iniciar prefetch si excede presupuestos de host pinned, VRAM o número de transferencias en vuelo.
5. **Límites y backpressure:** acotar bytes y peticiones simultáneas para evitar que el prefetch compita con inferencia o fuerce presión de memoria.
6. **Caché de prefijos/KV paginada:** ideas interesantes a largo plazo, pero no son prioridad para resolver el cuello de botella actual de expertos.

### 6.2 No duplicar sistemas

Picchio ya dispone de cachés LRU host/VRAM y loader asíncrono host. La adaptación debe añadir un ledger y un protocolo de transferencia en torno a esas estructuras, no crear un segundo sistema de gestión de pesos.

### 6.3 Orden

La idea más valiosa a corto plazo es ownership + eventos + transferencia asíncrona. Prompt cache, paged KV y speculative decoding deben quedar para una fase posterior, después de estabilizar el movimiento de expertos.

---

## 7. Revisión de tandem.cpp y adaptaciones

Referencia externa: [ewhacc/tandem.cpp](https://github.com/ewhacc/tandem.cpp). Propuesta previa: [TANDEM_CPP_ADAPTATION_PROPOSAL.md](https://github.com/robertosantosx2/picchio/blob/research/tensorfold-adaptation/docs/TANDEM_CPP_ADAPTATION_PROPOSAL.md).

tandem.cpp es un parche sobre llama.cpp que incorpora una caché MoE y rutas híbridas. La revisión se centró en `src/llama-moe-cache.cpp`, kernels CPU, grafo/backend CUDA, prefetch, doorbell y benchmark.

### 7.1 Reparto híbrido por experto

Mecanismo:
- los hits de caché GPU se calculan en GPU;
- los misses se dividen entre expertos que se suben a GPU y expertos que se calculan en CPU;
- CPU y GPU trabajan en paralelo;
- los resultados parciales se combinan.

tandem.cpp estima un split a partir de ancho de banda host→device y throughput CPU, con una regla aproximada de la forma:

`s = L / (L + kR)`

donde L representa ancho de banda de transferencia, R rendimiento de CPU y k un factor empírico. La política también usa mediciones de espera/idle y compuertas A/B para desactivar una ruta que no aporta mejora.

**Adaptación cautelosa:** empezar con splits fijos pequeños (por ejemplo 10%, 20%, 30%) solo entre misses cuyos pesos ya estén residentes en RAM. Nunca mandar a CPU una tarea que provoque lectura adicional desde SSD. La regla adaptativa L/R solo se considerará después de medir CPU, DMA y ancho de banda de RAM en este equipo.

### 7.2 Kernel CPU agrupado

tandem.cpp agrupa pares token/experto, reutiliza activaciones cuantizadas por token y procesa bloques de filas gate/up y down. Usa rutas SIMD y formatos Q2_0/IQ propios de llama.cpp.

Picchio trabaja con sus formatos INT4/INT3 y escalas gs64. No se deben copiar directamente kernels Q2_0 ni asumir compatibilidad de layout. La adaptación posible es conceptual:
- agrupar trabajos por experto;
- reutilizar cuantización de activaciones;
- procesar bloques de filas;
- reducir overhead de llamadas;
- aprovechar el pool de hilos existente.

### 7.3 Prefetch de expertos de la siguiente capa hacia VRAM

tandem.cpp predice expertos probables de la siguiente capa y los transfiere por un stream lateral. La inferencia de la capa actual continúa. Un kernel espera solo cuando necesita un slot todavía en estado UPLOADING.

Esta es la mejora de tandem.cpp con mayor prioridad para Picchio, porque ya existe prefetch host de siguiente capa, pero no un pipeline de transferencia asíncrona host→VRAM con eventos y espera diferida.

### 7.4 Doorbell / host_add

El patrón doorbell permite que un kernel GPU publique IDs/activaciones en memoria host pinned, un hilo CPU procese tareas y la GPU espere la señal y sume resultados.

Es potente pero requiere operadores nuevos, atomics/fences correctos, timeouts, shutdown seguro, integración del grafo y gestión de errores. Se pospone: complejidad demasiado alta para la fase actual.

### 7.5 Funciones que no deben adoptarse

- No usar tail-skip ni omitir expertos seleccionados: Picchio debe conservar la semántica exacta del top-k.
- No asumir que un miss de SSD puede calcularse en CPU con ventaja.
- No copiar formatos de cuantización incompatibles.
- No adoptar MTP/head Q4 específico de otros modelos sin demostrar compatibilidad con Qwen3-30B-A3B.
- No extrapolar resultados de RTX 4090 u otras GPU a la RTX 3050.

### 7.6 Benchmarks externos

Los resultados publicados por los autores de tandem.cpp —incluyendo cifras elevadas en RTX 4090 y modelos grandes— son **EXTERNAL / AUTHOR-REPORTED**. No son mediciones LEONES, no son comparaciones independientes y no permiten predecir el rendimiento del MSI. La documentación externa también advierte que los misses de SSD son un caso desfavorable y que la ruta CPU no resuelve la falta de residencia de pesos en RAM.

---

## 8. Diseño objetivo recomendado: GPU async prefetch

### 8.1 Objetivo funcional

Permitir que Picchio transfiera expertos ya cargados en slabs host hacia slots VRAM mientras la GPU calcula la capa actual, sin cambiar el resultado matemático ni liberar buffers antes de terminar la transferencia.

### 8.2 Invariantes

1. La ruta síncrona actual permanece disponible como fallback.
2. Un slot VRAM en estado UPLOADING no puede ser elegido para eviction ni reutilización.
3. Un slab host fuente no puede liberarse, modificarse ni desregistrarse mientras exista una copia DMA en curso.
4. La finalización de transferencia se determina por evento CUDA, no por temporizador ni por suposición.
5. Un kernel que consuma un slot pendiente debe esperar al evento correspondiente en el stream correcto.
6. Los fallos de creación de stream/evento, enqueue o sincronización deben degradar a la ruta segura y dejar estados/accounting consistentes.
7. El prefetch es especulativo: un error de predicción puede reducir rendimiento, pero nunca cambiar qué expertos se calculan.
8. No introducir pérdida de expertos, aproximaciones numéricas deliberadas ni cambios del router.
9. No aumentar el límite pinned como parte de esta fase.
10. La finalización del proceso debe drenar o cancelar de forma segura todas las transferencias pendientes antes de liberar recursos.

### 8.3 Estados propuestos

Para cada slot experto GPU:

- EMPTY: libre.
- RESIDENT: pesos válidos y disponibles.
- UPLOADING: transferencia en vuelo; no evictable ni consumible sin dependencia.
- FAILED: carga fallida; requiere fallback/reintento controlado.

Para el recurso host fuente:
- HOST_READY: slab válido y estable.
- DMA_IN_FLIGHT: fuente retenida por una transferencia.
- HOST_RELEASABLE: evento completado; ya puede reutilizarse o desregistrarse.

Los nombres exactos pueden adaptarse al código actual, pero las transiciones deben ser explícitas y auditables.

### 8.4 Pipeline propuesto

```text
Capa N: router + expertos actuales
        │
        ├── stream compute: ejecutar expertos residentes
        │
        └── host loader: preparar expertos candidatos de N+1
                         │
                         ▼
                 stream de transferencia
                 cudaMemcpyAsync H→D
                         │
                         ▼
                  evento por slot/lote
                         │
                         ▼
Capa N+1: al solicitar experto
        ├── RESIDENT  → ejecutar
        ├── UPLOADING → esperar evento en compute stream → ejecutar
        └── miss      → ruta síncrona segura / carga normal
```

La predicción inicial debe reutilizar la información de router disponible y las estructuras de prefetch existentes. No se necesita cambiar el router ni anticipar decisiones que Picchio no pueda justificar.

### 8.5 Admisión y límites

- Reutilizar el presupuesto VRAM y la política LRU actuales.
- Reservar slot antes de iniciar la transferencia.
- No contar un slot UPLOADING como libre.
- Limitar el número de transferencias en vuelo.
- Aplicar backpressure cuando no haya slots o presupuesto.
- No competir sin límite con el loader host.
- Instrumentar bytes transferidos, número de operaciones, duración, espera del consumidor, hit útil y prefetch desperdiciado.
- Mantener 128 MiB pinned como límite global inicial.

### 8.6 Aislamiento y compatibilidad

La implementación debe estar detrás de una opción experimental o feature flag. La desactivación debe restaurar el camino actual sin alterar configuración ni resultados. Los builds CPU y los self-tests deben seguir funcionando sin CUDA.

---

## 9. Plan de implementación por fases

### P0 — Observabilidad y contratos

Antes de cambiar el comportamiento:
- localizar y documentar los puntos exactos de reserva, eviction, carga, transferencia y liberación de slots;
- mapear quién posee cada slab host;
- medir categorías de misses: host hit, host miss/SSD, VRAM hit, VRAM miss, prefetch hit/miss;
- exponer métricas de transferencia y espera;
- completar el uso de contadores de peticiones pinned y tamaños;
- definir invariantes y asserts de estados.

**Gate P0:** métricas suficientes para explicar cada miss y cada transición; ninguna modificación del resultado de inferencia.

### P1 — Async H→D mínimo

- añadir stream de transferencia separado;
- añadir eventos CUDA para lotes o slots;
- implementar estado UPLOADING;
- impedir eviction/recycle mientras la transferencia esté en vuelo;
- mantener retenido el slab fuente;
- sincronizar al consumir, no globalmente;
- implementar fallback síncrono;
- feature flag desactivada por defecto.

**Gate P1:** self-test de estados/errores, test de transferencia, shutdown seguro, cero corrupción y equivalencia de resultados frente a la ruta síncrona.

### P2 — Prefetch de siguiente capa

- conectar el pipeline asíncrono al prefetch host ya existente;
- iniciar transferencias solo cuando la predicción y el presupuesto lo permitan;
- esperar de forma diferida al usar un slot;
- contar prefetch útil, desperdiciado y tardío;
- probar con prefetch apagado/encendido y mismo prompt.

**Gate P2:** ausencia de carreras, cero expertos omitidos y mejora reproducible en tiempo total o reducción de stalls sin regresión de memoria.

### P3 — CPU/GPU híbrido experimental

Solo después de P1/P2:
- ejecutar CPU únicamente sobre misses con pesos host-resident;
- reservar GPU para los demás misses y hits;
- empezar con split fijo y bajo;
- combinar resultados parciales;
- medir contención de RAM, CPU y PCIe;
- comparar logits/tokens y tolerancias;
- incorporar A/B gate que desactive la ruta si no gana.

**Gate P3:** mejora sostenida en el MSI, sin lectura SSD adicional en CPU path, sin presión de swap y con corrección numérica caracterizada.

### P4 — Kernel CPU agrupado

- perfilar overhead de llamadas y cuantización;
- adaptar agrupación de token/experto a INT4/INT3 gs64;
- reutilizar activaciones cuantizadas;
- procesar bloques de filas;
- comparar con implementación actual;
- no importar kernels incompatibles de llama.cpp.

**Gate P4:** mejora medida sobre la ruta CPU, con salida equivalente y sin aumentar peligrosamente la memoria temporal.

### P5 — Admisión por frecuencia / microbatch

Estudiar política de admisión de expertos por frecuencia cuando exista prefill multi-token o microbatch. No asumir beneficio en decode de un único token, donde cada experto seleccionado puede aparecer una sola vez.

### P6 — Doorbell y host-side execution

Posponer hasta que la arquitectura de streams, ownership y estados esté estable. Requiere diseño independiente de operadores, sincronización, atomics, errores y shutdown.

### P7 — KV paging, prompt cache y speculative/MTP

Investigación posterior. No forman parte del objetivo de optimizar el movimiento de expertos en esta fase.

---

## 10. Matriz de pruebas y aceptación

| Prueba | Comparación | Métrica | Criterio |
|---|---|---|---|
| Self-test CPU | antes/después | suite sintética | todo pasa |
| CUDA transfer test | sync vs async | bytes, errores, integridad | datos idénticos |
| Lifetime stress | liberar/reutilizar bajo carga | errores, carreras, corrupción | cero fallos |
| Eviction stress | slot RESIDENT/UPLOADING | transiciones | UPLOADING nunca evictado |
| Shutdown | cerrar con DMA pendiente | recursos y estado | drenaje seguro |
| Inference correctness | sync vs async | logits/tokens | equivalencia definida y sin expertos omitidos |
| Prefetch A/B | off vs on | tok/s, latencia, stalls, utilidad | mejora reproducible |
| Memory pressure | carga real | RSS, swap, pinned, VRAM | sin regresión peligrosa |
| Hybrid split | 0/10/20/30% CPU host-resident | tok/s, stalls, CPU, PCIe | solo aceptar si gana |
| CPU grouped | actual vs grouped | tiempo MoE, tok/s | mejora repetible |

### 10.1 Protocolo de benchmark

- mismo modelo, conversión, prompt, contexto y número de tokens;
- misma configuración de threads y de cachés;
- registrar commit SHA, flags, variables de entorno y versiones;
- separar warm-up de mediciones;
- ejecutar varias repeticiones y reportar mediana y dispersión;
- capturar `free -h`, `nvidia-smi`, temperatura, potencia, uso GPU, RSS y swap;
- no comparar ejecuciones de ocho tokens con benchmarks largos;
- no declarar mejora por una sola ejecución;
- archivar logs crudos y script reproducible en LEONES;
- registrar también fallos, no solo el mejor resultado.

### 10.2 Comparación mínima

Toda prueba de una nueva ruta debe incluir:
1. baseline CPU;
2. CUDA síncrono actual;
3. CUDA async sin prefetch especulativo;
4. CUDA async + prefetch;
5. CPU/GPU híbrido solo cuando P2 esté aceptado.

---

## 11. Riesgos técnicos y mitigaciones

| Riesgo | Consecuencia | Mitigación |
|---|---|---|
| Liberar slab durante DMA | corrupción / crash | ownership + evento |
| Evictar slot UPLOADING | corrupción de pesos | estado no evictable |
| Espera global CUDA | elimina solapamiento | wait por evento/slot |
| Exceso de prefetch | presión VRAM/RAM | admission control |
| Pinned excesivo | presión RAM / swap | cap 128 MiB inicial |
| CPU y DMA compiten por RAM | empeora ambas rutas | split fijo pequeño y medición |
| CPU lee misses desde SSD | latencia extrema | CPU path solo host-resident |
| Cambio de orden de reducción | diferencias numéricas | tests logits/tolerancia |
| Error de predicción | tráfico desperdiciado | fallback exacto |
| Error parcial CUDA | estado incoherente | rollback y ruta síncrona |
| Shutdown con trabajo pendiente | use-after-free | drenar eventos antes de liberar |
| Diferencia de arquitectura GPU | build/ejecución no compatible | probar sm_86 real |

---

## 12. Estado de GitHub y artefactos

### 12.1 Picchio

- Repositorio: [robertosantosx2/picchio](https://github.com/robertosantosx2/picchio).
- Rama de investigación: `research/tensorfold-adaptation`.
- En el último estado comprobado, la rama estaba 2 commits por delante de `main`, 0 detrás.
- Commit `dee170d`: propuesta TensorFold.
- Commit `a5d6ed959e7fae8b422842d3a9cb1435b7bd52bc`: propuesta tandem.cpp.
- Documentos:
  - [TENSORFOLD_ADAPTATION_PROPOSAL.md](https://github.com/robertosantosx2/picchio/blob/research/tensorfold-adaptation/docs/TENSORFOLD_ADAPTATION_PROPOSAL.md)
  - [TANDEM_CPP_ADAPTATION_PROPOSAL.md](https://github.com/robertosantosx2/picchio/blob/research/tensorfold-adaptation/docs/TANDEM_CPP_ADAPTATION_PROPOSAL.md)

### 12.2 Pinned host branch y PR

- Rama: `feature/cuda-pinned-host-slabs`.
- PR draft: [robertosantosx2/picchio#1](https://github.com/robertosantosx2/picchio/pull/1).
- No fusionar hasta validación CUDA física.
- Commits relevantes:
  - `e21b1df5b6b49a34b8a775484ca3c7c1a7dfcbe0`: categorías de fallos y cap overflow-safe.
  - `72f0068ebdc3cf33631ac274aff419c1a7787c3b`: un intento por slab y unregister.
  - `7d014c96a3a9ae92071ec74735936496abe4cf86`: instrumentación de tamaños.
  - `bccde99c4bb506c6744d1434f47ae324135769a4`: autotest de límites reforzado.
  - `c52dfcf1107063e40bae75b4a3c2b11d164b1764`: documentación de cobertura.
- CI GitHub Actions run `42433244049`: PASS.
- CI GitHub Actions run `42433398973`: PASS.
- Los runners usados validaron build CPU, self-test sintético y `git diff --check`; no compilaron ni ejecutaron la unidad CUDA en la RTX 3050.

### 12.3 Estado de implementación

A fecha de corte:
- el documento de adaptación TensorFold está en la rama de investigación;
- el documento de adaptación tandem.cpp está en la rama de investigación;
- el trabajo pinned host está en su rama/PR draft separado;
- no se ha implementado todavía el pipeline CUDA H→D asíncrono descrito en este documento;
- no se ha implementado el reparto híbrido CPU/GPU de tandem.cpp;
- no se ha abierto ni fusionado un PR de esas dos mejoras;
- no se han realizado pruebas locales de esas nuevas propuestas.

---

## 13. Decisiones y no-objetivos

### Decisiones recomendadas

1. P0 observabilidad antes de optimización.
2. P1/P2 async H→D y prefetch GPU de siguiente capa como primera mejora de rendimiento.
3. Mantener el camino síncrono como fallback y referencia.
4. Mantener el límite pinned de 128 MiB en esta primera fase.
5. Poner ownership y estados de slot por encima de micro-optimizaciones.
6. Separar la implementación en rama nueva, sin mezclarla con el PR pinned host.
7. CPU/GPU híbrido después, únicamente con pesos host-resident.
8. Mantener la semántica exacta top-k: no saltarse expertos.
9. Validar en sm_86 real antes de aceptar.
10. Conservar todos los resultados negativos y artefactos.

### No-objetivos de la primera fase

- No cambiar router, top-k ni matemáticas de los expertos.
- No omitir expertos.
- No cambiar cuantización o formato de pesos.
- No aumentar pinned memory.
- No introducir doorbell/host_add.
- No implementar speculative decoding/MTP.
- No reemplazar cachés o loader existentes.
- No afirmar que se acelera hasta medirlo.

---

## 14. Próxima campaña en Ubuntu

Cuando se autorice la fase local, la campaña debe realizarse en pasos pequeños y controlados, un bloque de comandos por turno, esperando la salida antes del siguiente paso.

Orden:
1. capturar estado Git y SHA de la rama de implementación;
2. capturar memoria, swap, GPU y procesos;
3. compilar en directorio experimental aislado;
4. ejecutar self-tests;
5. ejecutar test CUDA de copia y lifetime;
6. ejecutar inferencia corta de corrección;
7. ejecutar A/B con prompt y tokens fijos;
8. repetir mediciones;
9. archivar logs, CSV, comandos y hashes en LEONES.

No ejecutar esta campaña automáticamente ni tocar los artefactos protegidos indicados en la sección 3.3.

---

## 15. Referencias

- [Picchio — repositorio](https://github.com/benmaster82/picchio)
- [Picchio — fork de trabajo](https://github.com/robertosantosx2/picchio)
- [Picchio — PR pinned host #1](https://github.com/robertosantosx2/picchio/pull/1)
- [TensorFold — repositorio](https://github.com/ashhart/TensorFold)
- [Propuesta de adaptación TensorFold](https://github.com/robertosantosx2/picchio/blob/research/tensorfold-adaptation/docs/TENSORFOLD_ADAPTATION_PROPOSAL.md)
- [tandem.cpp — repositorio](https://github.com/ewhacc/tandem.cpp)
- [Propuesta de adaptación tandem.cpp](https://github.com/robertosantosx2/picchio/blob/research/tensorfold-adaptation/docs/TANDEM_CPP_ADAPTATION_PROPOSAL.md)

---

## 16. Regla de uso de este documento

Este informe es la referencia de diseño para la implementación de Picchio MoE. Antes de cada cambio:
1. identificar la fase y el gate al que pertenece;
2. revisar los invariantes de la sección 8;
3. mantener separadas las ramas experimentales;
4. añadir tests y métricas antes de optimizar;
5. registrar qué está implementado, qué está medido y qué sigue siendo hipótesis;
6. actualizar este documento cuando cambie una decisión o se obtenga nueva evidencia.

**La prioridad no es reproducir tandem.cpp ni TensorFold: es adaptar sus mecanismos útiles al código, formatos, límites de memoria y hardware real de Picchio, conservando corrección y trazabilidad LEONES.**


## 17. Auditoría adicional: prefetch CUDA de expertos (2026-11-08)

Una revisión directa de `picchio.c` y `picchio_cuda.cu` en la rama `feature/cuda-pinned-host-slabs` (PR #1, HEAD `c52dfcf1107063e40bae75b4a3c2b11d164b1764`) ha precisado el estado real de P1:

### 17.1 Lo que Picchio ya tiene

Picchio ya implementa prefetch predictivo **host/disk**:
- `predict_topk_into()` estima expertos de una capa futura.
- `prefetch_issue()` reserva slots de la caché host.
- `prefetch_run_job()` carga los expertos desde disco en un worker.
- `slot_loading` / `slot_set_loading` publican la disponibilidad con acquire/release.
- `cache_load_batch()` y `cache_load_batch_async()` coordinan los misses reales con los slots precargados.
- `g_gpu_prefetch` activa esta predicción en ejecuciones con GPU.

Esto evita repetir una lectura si la predicción acierta, pero no equivale a precargar pesos en VRAM.

### 17.2 Lo que falta

En `picchio_cuda.cu`, `get_expert()` sigue reservando memoria de dispositivo y subiendo los pesos mediante `cudaMemcpy` síncrono. No hay:
- stream CUDA de subida separado;
- `cudaMemcpyAsync` para pesos de expertos;
- evento de disponibilidad por experto;
- estado UPLOADING separado de READY;
- lease que impida reciclar el slab host mientras DMA lo lee;
- protección de LRU para buffers GPU pendientes o en uso.

El registro `cudaHostRegister` de PR #1 no produce por sí mismo solapamiento: las copias continúan siendo síncronas. No se atribuirá mejora de rendimiento al pinned host hasta que exista transferencia asíncrona y se mida.

### 17.3 Diseño propuesto

Se ha publicado el diseño detallado en [CUDA_EXPERT_PREFETCH_DESIGN.md](https://github.com/robertosantosx2/picchio/blob/research/gpu-expert-prefetch-design/docs/CUDA_EXPERT_PREFETCH_DESIGN.md), PR [#2](https://github.com/robertosantosx2/picchio/pull/2), todavía Draft y solo documental.

Invariantes principales:
1. Dos streams explícitos: compute y upload.
2. Estados de entrada GPU: ABSENT, ALLOCATING, UPLOADING, READY y FAILED.
3. Evento CUDA tras la última copia; el stream de cómputo espera solo al experto que necesita mediante `cudaStreamWaitEvent`.
4. Un host slab no se libera ni recicla hasta que termina la transferencia DMA; requiere lease/referencia.
5. Ni una entrada UPLOADING ni una entrada con lease de cómputo puede ser expulsada por LRU.
6. La admisión especulativa cuenta contra el presupuesto VRAM desde el momento de reservar buffers.
7. Primera versión limitada al top-k de una sola capa futura; si no hay espacio, se omite el prefetch.
8. Si la fuente no está pinned o falla cualquier paso, se conserva el upload síncrono actual.
9. No usar `cudaDeviceSynchronize()` en el bucle de tokens.
10. La optimización debe permanecer desactivada por defecto hasta pasar tests CUDA y benchmarks pareados.

### 17.4 Secuencia de implementación

- **P1a:** introducir streams explícitos sin cambiar el comportamiento; probar paridad numérica y teardown.
- **P1b:** subir un único experto de forma asíncrona con evento y lease host; feature flag OFF por defecto.
- **P1c:** ampliar a top-k con admission control y métricas.
- **P2:** solo después de medir, investigar reparto adaptativo CPU/GPU.

### 17.5 Estado y límites

- PR #1 sigue Draft; no fusionar antes de validar CUDA en la RTX 3050.
- PR #2 sigue Draft; no contiene código CUDA ni afirma mejoras.
- Ninguna ejecución de Ubuntu o de la RTX 3050 se ha realizado en esta fase remota.
- No elevar el límite pinned de 128 MiB sin medir primero tamaños de petición y margen real de RAM/swap.
- El baseline CPU y la biblioteca CUDA funcional deben permanecer intactos.



---

## 18. Auditoría P1a: streams CUDA explícitos (2026-11-08)

### 18.1 Auditoría del backend

Se revisó el `picchio_cuda.cu` completo de PR #1, además de los límites de llamada y la gestión de slots en `picchio.c`.

El backend CUDA actual utiliza:
- copias `cudaMemcpy` síncronas;
- kernels lanzados en el stream por defecto;
- scratch device reutilizable entre llamadas;
- una LRU de expertos VRAM que asigna y libera buffers durante el forward;
- slabs host reutilizables y opcionalmente registrados con `cudaHostRegister`.

La interfaz C devuelve resultados host listos al caller. Por tanto, el caller puede reutilizar o liberar los punteros host justo después de cada llamada CUDA. El nuevo diseño debe conservar esta garantía.

### 18.2 Contrato P1a

Se propone una sola stream explícita no bloqueante para todas las copias y kernels, con sincronización al final de cada API pública. Esto establece orden explícito, pero **no introduce todavía solapamiento ni mejora de rendimiento**.

Puntos críticos:
1. Toda copia H2D/D2H y cada kernel debe usar la misma stream.
2. Cada retorno de error después de encolar trabajo debe drenar la stream antes de devolver el control al caller.
3. Las subidas parciales de expertos deben completar o drenar antes de liberar el slab host.
4. La LRU no puede liberar un buffer device mientras kernels pendientes lo referencien.
5. `pgpu_host_unregister` y el shutdown deben esperar a que no quede DMA pendiente.
6. La CPU fallback debe seguir siendo correcta después de cualquier error CUDA.

La sincronización solo en el camino de éxito no es suficiente: también hay que cubrir fallos de copia, asignación, kernel y D2H.

### 18.3 PR y CI

- PR [#4](https://github.com/robertosantosx2/picchio/pull/4): contrato y auditoría P1a, Draft y documental.
- Documento: [CUDA_STREAM_PLUMBING_P1A.md](https://github.com/robertosantosx2/picchio/blob/research/cuda-stream-plumbing-p1a/docs/CUDA_STREAM_PLUMBING_P1A.md).
- Se añadió workflow de compilación CUDA para `sm_86`, con compilación del backend, `PGPU_PINNED_TEST` y `PGPU_ROUTER_TEST`.
- La imagen de CI se fijó en `nvidia/cuda:13.4.3-devel-ubuntu24.04`, que coincide con la rama CUDA 13.4 usada en el MSI.
- La CI es **compile-only**: no ejecuta los binarios CUDA ni valida una GPU real. En la consulta de estado actual no aparecen ejecuciones ni checks asociados a los commits recientes; no se declara ningún PASS.
- PR #3 fue cerrado por duplicar el mismo trabajo y quedar desfasado; PR #4 es la propuesta activa.

### 18.4 Próximo paso y límite de validación

El siguiente paso de código será implementar P1a en una rama aislada, sin modificar el baseline CPU ni la biblioteca CUDA funcional. Antes de avanzar a P1b se requiere:
- compilación real con nvcc;
- self-tests pinned-host y router;
- comprobación de paridad numérica;
- prueba de error/fallback y teardown;
- ejecución controlada en la RTX 3050.

No se ha ejecutado Ubuntu ni se ha medido rendimiento nuevo durante esta fase remota. El P1a todavía no está implementado; PR #4 documenta el contrato y los riesgos que debe cumplir.
