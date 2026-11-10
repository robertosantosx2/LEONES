# Auditoría de tandem.cpp para la evolución MoE de Colibrì

**Fecha de auditoría:** 2026-11-10  
**Repositorio analizado:** [ewhacc/tandem.cpp](https://github.com/ewhacc/tandem.cpp)  
**Commit upstream fijado:** `e1acb8877bfcf92b4ae7c9f0e0f1d896dbf6c683`  
**Base llama.cpp del patch:** `f5222f25c` (2026-10-28, según `BASE_COMMIT`)  
**Snapshot preservado en LEONES:** [research/moe/tandem.cpp](https://github.com/robertosantosx2/LEONES/tree/main/research/moe/tandem.cpp)  
**Destino de la adaptación:** [robertosantosx2/colibri, rama research/qwen36-cuda-chain-planner](https://github.com/robertosantosx2/colibri/tree/research/qwen36-cuda-chain-planner)

## 1. Alcance y método

Se ha consultado el árbol Git completo del repositorio upstream y se han recuperado todos sus ficheros de texto. El snapshot de LEONES coincide con el commit upstream documentado. El inventario contiene 10 entradas: README, LICENSE, BASE_COMMIT, build.sh, tandem.patch y cinco ficheros de benchmark/datos (el árbol recursivo incluye el directorio de datos GSM8K).

El patch tiene **432.439 bytes, 8.732 líneas, 35 ficheros afectados, 6.634 líneas añadidas y 227 eliminadas**. Se han revisado los contratos y las rutas principales de caché MoE, CPU/GPU híbrida, presupuesto de memoria, operaciones GGML/CUDA, planificación de grafo, prefill, lookahead, pinned memory y benchmarks. Esto es una auditoría de arquitectura y adaptación; no equivale a una compilación del patch ni a una validación en el MSI.

Fuentes primarias:
- [README upstream](https://github.com/ewhacc/tandem.cpp/blob/main/README.md)
- [Patch completo](https://github.com/ewhacc/tandem.cpp/blob/main/tandem.patch)
- [Script de construcción](https://github.com/ewhacc/tandem.cpp/blob/main/build.sh)
- [Metodología de benchmarks](https://github.com/ewhacc/tandem.cpp/tree/main/bench)
- [Snapshot preservado](https://github.com/robertosantosx2/LEONES/tree/main/research/moe/tandem.cpp)

## 2. Qué es realmente tandem.cpp

No es un motor de inferencia independiente. Es un patch grande sobre una revisión concreta de llama.cpp. El script clona llama.cpp, fija `f5222f25c`, aplica `tandem.patch` y compila `llama-server` con CUDA. No debe aplicarse directamente a Colibrì: el código de Colibrì es un runtime C/CUDA propio y no comparte las estructuras internas de llama.cpp.

La propuesta útil consiste en portar **algoritmos, métricas y contratos**, no el patch de 8.732 líneas ni las estructuras GGML.

### 2.1 Inventario de los 35 ficheros modificados

| Área | Ficheros principales | Función |
|---|---|---|
| Configuración | `common/arg.cpp`, `common/common.cpp`, `common/common.h` | caché auto, margen VRAM, defaults y reservas para draft |
| Backend GGML | `ggml-backend.cpp/.h`, `ggml.c`, `ggml.h`, CPU/CUDA | copias agrupadas, nuevas operaciones y sincronización |
| Caché MoE | `src/llama-moe-cache.cpp/.h`, `src/llama-moe-iq.h` | LRU, split CPU/GPU, kernels CPU, lookahead y doorbell |
| Grafo/contexto | `llama-context.cpp/.h`, `llama-graph.cpp/.h` | grafo pool, registros híbridos, prefill y MTP chain |
| Modelo/carga | `llama-model.cpp/.h`, `llama-quant.cpp` | expertos pinned, PLE GPU, gates GDN, vocab draft y fusiones |
| Kernels CUDA | `ggml-cuda/ggml-cuda.cu`, `mmvq.cu`, `mmvf.cu`, `gated_delta_net.cu`, `dsv4-hc.cu`, `hc-fused.cu/.cuh` | operaciones de sincronización, matvec, GDN y hyper-connections |
| Familias | `src/models/delta-net-base.cpp`, `src/models/qwen4exp.cpp`, `src/models/models.h` | optimizaciones específicas de Qwen4Exp/GDN |
| Servidor/speculation | `tools/server/server-context.cpp`, `common/speculative.cpp` | selección de profundidad especulativa y MTP |
| Profiling | `src/llama-prof.h` | perfiles de CPU, GPU, scheduler y latencias |

La mayor parte del cambio no es el algoritmo LRU: es la infraestructura necesaria para que el CPU calcule misses mientras la GPU continúa sin bloquear el grafo.

## 3. Algoritmos que sí nos interesan

### 3.1 Caché de expertos LRU

La estructura `moe_cache_lru` mantiene:
- mapa experto → slot por capa;
- clave slot → (capa, experto);
- lista doblemente enlazada de slots;
- cabeza como menos recientemente usado y cola como más recientemente usado;
- promoción de hits y expulsión del slot LRU.

La variante anterior SLRU se reemplaza por LRU simple. En `plan_hybrid`, además se cuentan las apariciones de cada experto en los tokens del microbatch. El planificador separa hits, misses y opcionalmente expertos descartados por `LLAMA_MOE_TAIL_SKIP`.

**Consecuencia:** LRU decide qué experto permanece residente, mientras que la frecuencia dentro del microbatch decide qué miss conviene calcular en CPU. Son dos decisiones distintas.

### 3.2 Split híbrido de misses

El algoritmo `plan_hybrid`:
1. recoge expertos únicos requeridos;
2. toca los hits LRU;
3. agrupa los misses y cuenta cuántos tokens usan cada experto;
4. ordena los misses por frecuencia;
5. admite aproximadamente `round(share * misses)` en la caché GPU;
6. devuelve los restantes al ejecutor CPU;
7. marca los pares CPU para que el camino GPU no aporte dos veces su resultado.

En la ruta exacta, los misses no se descartan. `LLAMA_MOE_TAIL_SKIP` es explícitamente aproximado: omite contribuciones y no renormaliza. **No se debe habilitar en Colibrì** en el camino de calidad exacta.

La ruta CPU del patch acepta determinadas formas SwiGLU y SwiGLU-OAI, con restricciones de sesgo, escalas y layout. Si la forma no es compatible, el patch advierte y vuelve a subir los misses a GPU. Esta comprobación de compatibilidad es un requisito importante: nunca enviar un experto a un kernel CPU que no reproduzca su semántica.

### 3.3 Cómo se solapan CPU y GPU

Hay dos mecanismos de sincronización relevantes:

- **Flag mode / `ggml_host_add`:** el worker CPU escribe un resultado en memoria host accesible por GPU; un kernel CUDA espera a que el host publique el flag y suma el resultado al parcial GPU. El flag contiene secuencia, ACK, tiempo de espera y timeouts.
- **Doorbell / `ggml_moe_doorbell`:** una operación CUDA escribe IDs (y, en modo híbrido, activaciones y pesos del router) en un bloque host pinned, publica una petición y espera la respuesta del hilo host. El host planifica slots, calcula el trabajo CPU y prepara descriptores de uploads; el dispositivo copia la respuesta y lee los pesos host para subir los expertos. El modo evita crear un split de scheduler por capa.

El doorbell está limitado a microbatches de hasta 8 tokens en esta implementación. No es una simple optimización de copia: introduce un protocolo concurrente GPU↔CPU con timeouts, fences, ownership de buffers y teardown de threads. Para Colibrì es una fase tardía, no el primer prototipo.

### 3.4 Control adaptativo de share

El patch ofrece:
- share fijo `LLAMA_MOE_CPU=0..1`;
- share automático;
- controlador por esperas CPU/GPU;
- regla basada en el ancho de banda host→device medido (`L`) y la tasa CPU medida (`R`): `share = L / (L + k·R)`, con `k` empírico;
- cambios graduales de 5 puntos porcentuales;
- una compuerta A/B que compara ventanas con ruta CPU activa e inactiva, porque el coste fijo de sincronización puede hacer peor la ruta híbrida cuando hay pocos misses.

La lección para Colibrì: no activar híbrido por el mero hecho de que haya misses. Medir primero si el coste de sincronizar y combinar es inferior al de subir los expertos. La decisión debe ser reversible y observable.

### 3.5 Prefill, lookahead y preread

El patch separa decode y prefill:
- decode híbrido en microbatches pequeños;
- prefill híbrido en lotes mayores, con una cuota de expertos poco usados por token;
- lookahead: aplicar el router de la capa siguiente a la entrada de expertos de la capa actual, predecir top-K y subir candidatos en un backend/stream secundario;
- lazy join: esperar la transferencia solo si la capa va a leer un slot todavía en escritura;
- preread: aprovechar huecos del pool CPU para leer expertos predichos desde RAM, cancelando el trabajo en bloques de 64 KiB si llega otro job.

El lookahead es especulativo pero lossless: un experto mal predicho solo desperdicia lectura/upload o desplaza otro slot; el routing real sigue mandando. Requiere telemetría de utilidad, cancelaciones y bytes inútiles.

## 4. Presupuesto de memoria y adecuación al MSI

### 4.1 Presupuesto automático

`--moe-cache-mib auto` reserva primero buffers de cómputo, consulta la memoria libre de cada GPU y descuenta un margen. Si hay modelo draft, añade su tamaño de fichero y una reserva adicional aproximada para KV/graphs. Si la caché calculada es menor de 256 MiB, se desactiva.

El patrón que debemos adoptar es **reservar antes de poblar la caché**:
- pesos densos y matrices de la cadena CUDA;
- estado recurrente y KV/mirrors;
- scratch de prefill;
- buffers de transferencias;
- margen de seguridad;
- solo entonces, presupuesto para expertos.

Esto conecta directamente con el problema actual de Colibrì: el tier de expertos no debe consumir memoria que después necesita `q36cc_setup` para que todas las proyecciones de la cadena estén en el mismo dispositivo.

### 4.2 Memoria host pinned: no copiar el modelo entero

El patch solo copia expertos mmap a memoria anónima pinned cuando la RAM física supera el tamaño total de expertos más 10 GiB. La tabla PLE usa una condición similar: modelo completo más 8 GiB. Si no cabe, conserva mmap. También advierte que los límites físicos no detectan límites de cgroup.

En el MSI:
- RAM: 14 GiB;
- GPU: RTX 3050 Laptop, 4 GiB, sm_86;
- swap: 31 GiB;
- modelo Qwen3.6-35B-A3B observado en Colibrì: alrededor de 23,1 GB.

Por tanto, **no es viable copiar todo el conjunto de expertos/modelo a pinned RAM** ni usar `-lm none` como configuración inicial. La ruta segura es mmap/page cache, límites estrictos de buffers pinned, y medir presión de RAM/swap. Swap no sustituye a RAM para buffers DMA ni elimina el coste de page faults.

### 4.3 Compatibilidad GPU

El README upstream dice que sus pruebas CUDA se realizaron en sm_89 y sm_120, no declara sm_86. Aunque el build permite especificar `-DCMAKE_CUDA_ARCHITECTURES=86`, eso no demuestra que el patch ni sus kernels estén validados en una RTX 3050. No extrapolar los resultados de RTX 4090/RTX 6000 Ada/DGX a sm_86.

## 5. Qué no debemos portar

1. El patch completo de llama.cpp: cambia 35 ficheros y depende de la revisión exacta `f5222f25c`.
2. `hc-fused.cu`, los cambios de DeepSeek-V4 HC y las fusiones `qwen4exp.cpp` como si fueran genéricos: son rutas específicas de Qwen4Exp/arquitecturas y layouts concretos.
3. MTP chain de llama.cpp sin mapear antes el contrato de MTP propio de Colibrì.
4. `LLAMA_MOE_TAIL_SKIP`: cambia la salida del modelo.
5. Copia pinned masiva de expertos en el MSI.
6. Multi-GPU como objetivo inicial: el README dice que solo `-sm layer` funciona con caché y que no se afinó la velocidad multi-GPU.
7. Benchmarks de otros equipos como evidencia de rendimiento local.

## 6. Mapeo con Colibrì

| Capacidad de tandem.cpp | Estado/contraparte en Colibrì | Adaptación recomendada |
|---|---|---|
| LRU de expertos GPU | tier de expertos y slot maps existentes | revisar política y añadir contadores de frecuencia por batch, sin duplicar la caché |
| Split CPU/GPU de misses | fallback CPU y uploads del tier | prototipo decode-only con share fijo y semántica exacta |
| Presupuesto auto de caché | `CUDA_EXPERT_GB`, `G_reserve`, `qt_reserve` | planner único que conozca reservas de la cadena antes de colocar expertos |
| Trunk/proyecciones densas | `COLI_PLACE`, `qt_trunk_offer`, `trunk_place_dense` | colocación atómica por conjunto de capa y dispositivo |
| Flag/doorbell | no asumir equivalente existente | añadir solo después de medir el coste de sincronización |
| Lookahead | no asumir equivalente completo | fase posterior, top-K medido y uploads cancelables |
| Prefill share | ruta de prefill de Colibrì | no mezclar con decode en la primera versión |
| Profiling | logs y benchmarks propios | contadores por capa: hit/miss, bytes, CPU, H2D, wait, idle |
| MTP/speculative | MTP propio de Colibrì | investigación separada, sin copiar APIs llama.cpp |

### 6.1 Hallazgo crítico para la cadena CUDA de Qwen3.6

El setup de la cadena requiere que las proyecciones necesarias de **todas las capas** y `lm_head` estén disponibles en el mismo dispositivo. El tier actual puede asignar componentes densos de forma independiente y algunas subidas pueden fallar individualmente. El log observado en el MSI indica que la primera `DeltaNet in_proj` no está en un dispositivo, por lo que la cadena queda desactivada.

La idea más valiosa de tandem.cpp no es su doorbell: es reservar el presupuesto de todas las estructuras antes de llenar la caché. Colibrì debe convertir el conjunto de tensores que necesita la cadena en una unidad de admisión/colocación, reservarlo íntegramente y solo después asignar expertos. Si el conjunto no cabe, usar un fallback explícito y medible; no dejar una colocación parcial que parezca una cadena viable.

## 7. Plan de adaptación por fases

| Fase | Trabajo | Criterio de salida |
|---|---|---|
| 0 — auditoría | inventario de tensores, bytes y dependencias de la cadena; mapa de reservas reales | tabla de bytes por dispositivo y causa exacta de cada rechazo |
| 1 — planner | plan conjunto de cadena + KV + scratch + expertos; no modificar aún el kernel CPU | test host determinista de presupuestos, overflow y fallback |
| 2 — placement | admitir la cadena como grupo indivisible de proyecciones por dispositivo | test fake-CUDA de co-localización y rollback completo |
| 3 — telemetría | contadores por capa de hit/miss, bytes H2D, CPU, wait/idle y ocupación | benchmark JSON reproducible |
| 4 — híbrido decode | share fijo 0/10/20/30/50%, solo expertos y activaciones soportadas | salida exacta frente a ruta de referencia; speedup neto positivo |
| 5 — share adaptativo | medición L/R + compuerta A/B con hysteresis | auto no peor que mejor share fijo dentro de tolerancia |
| 6 — prefill/lookahead | predicción top-K, doble buffer y cancelación | recall, utilidad, bytes inútiles y latencia ocultada medidos |
| 7 — doorbell | protocolo GPU-host con flags, timeouts y ownership formal | stress tests, timeouts, teardown y sanitización |
| 8 — SSD | streaming de expertos solo si RAM/page cache es el cuello demostrado | comparación SSD/RAM/VRAM con throughput real |

## 8. Matriz de validación para el MSI

La comparación debe utilizar el mismo modelo, prompt, contexto, sampler, número de tokens y presupuesto de VRAM.

| Variante | Objetivo |
|---|---|
| CPU experts / baseline | referencia sin caché híbrida |
| GPU tier actual | coste actual de cache hits y misses |
| cache LRU sin CPU misses | aislar efecto de residencia |
| híbrido fijo 10% | primer split conservador |
| híbrido fijo 20% | segundo punto |
| híbrido fijo 30% | tercer punto |
| híbrido auto + A/B | comprobar que el controlador elige bien |
| lookahead | medir uploads útiles y latencia escondida |

Registrar por ejecución:
- prompt tokens, completion tokens, TTFT, prefill tok/s, decode tok/s y wall time;
- hit/miss por capa, expertos admitidos/CPU, bytes subidos y evicted;
- tiempo CPU por experto y por fase;
- H2D bandwidth, latencia de upload, sincronización GPU y espera CPU;
- VRAM pico/libre, RSS, RAM disponible, swap y page faults;
- salida y comparación de logits/token cuando se valide exactitud.

Usar al menos 3 repeticiones por celda y alternar el orden de las variantes para reducir sesgo térmico/cache. W1 GSM8K y W4 long-context de tandem.cpp son referencias útiles, pero la campaña Colibrì debe incluir además un prompt fijo de código/razonamiento y pruebas de exactitud de logits. Los scripts upstream miden TTFT y generación en streaming; no miden directamente el tiempo de kernel ni sustituyen la telemetría interna.

## 9. Decisión

**Adoptar como diseño:** reserva anticipada, planner consciente de cadena, split híbrido exacto, medición CPU↔PCIe↔GPU, compuerta A/B y telemetría por capa.

**Aplazar:** doorbell, prefill share, lookahead y streaming SSD hasta que el planner base funcione y el cuello de botella esté identificado.

**No portar:** patch GGML, optimizaciones HC/MTP específicas de Qwen4Exp, tail-skip aproximado y copia pinned masiva.

Esta auditoría no declara que haya mejoras implementadas ni que exista un benchmark tandem.cpp en el MSI. El código de Colibrì debe modificarse y validarse en su propia rama; las pruebas CUDA finales se ejecutan en el hardware objetivo.


## 10. Hallazgo confirmado en la rama de Colibrì

La inspección del código de `c/qwen36_tier.c` confirmó una asimetría de presupuesto: `qt_reserve()` se restaba de la memoria libre en el modo automático, pero la rama de `CUDA_EXPERT_GB` numérico usaba directamente el número solicitado. Así, un límite explícito podía sobrepasar la memoria físicamente disponible después de descontar el margen de 1 GiB y las reservas de la cadena CUDA.

Se ha corregido en la rama [research/qwen36-cuda-chain-planner](https://github.com/robertosantosx2/colibri/tree/research/qwen36-cuda-chain-planner):
- capacidad utilizable = `max(VRAM libre - 1 GiB - qt_reserve, 0)`;
- en modo numérico, allowance = `min(CUDA_EXPERT_GB solicitado, capacidad utilizable)`;
- log explícito cuando el valor solicitado se recorta;
- test fake-CUDA para 2 GiB libres, cap solicitado 1,5 GiB, reserva 128 MiB y trunk 64 MiB; el presupuesto de expertos esperado es 832 MiB.

Commits:
- Código: `0e9c8fec2b1fa54cba4c9af63ce65011bc8f40d8` (seguido de corrección del formato del log en `ed3839b657f5e2a5e36909f29f2870059d80c318`).
- Test: `7c89c18bd17317d45541bc75a0075fa1a3c65a0b`.

La lectura de `q36cc_take()` confirma además que la cadena selecciona un dispositivo con su primera matriz y rechaza matrices posteriores en otro dispositivo. Por eso la cadena requiere co-localización global de todas las proyecciones obligatorias y `lm_head`, no solo parejas `dnproj/dnout` colocadas por capa. El `auto_place()` actual distribuye ofertas por capacidad restante y sus reglas locales no garantizan ese invariante global. La siguiente fase debe admitir la cadena como un grupo indivisible y escoger un único dispositivo candidato.

**Validación pendiente:** los commits están en GitHub, pero el test C no se ha ejecutado y no hay aún evidencia de compilación CUDA ni benchmark en la RTX 3050 sm_86. No presentar el cambio como validado en hardware.
