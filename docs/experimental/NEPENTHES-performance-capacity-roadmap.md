# NEPENTHES — hoja de ruta de rendimiento y capacidad

**Estado:** diseño de investigación y plan de implementación; no implica que las optimizaciones del motor estén ya implementadas.  
**Issue:** [#148 — ruta rápida y ejecución out-of-core](https://github.com/robertosantosx2/LEONES/issues/148)  
**Motor de referencia:** Tandem.cpp 0.8.0-dev, commit `f5222f25c18da062ab2b8a2dbbfbf4feae398566`.

## 1. Misión y criterio de éxito

NEPENTHES debe ayudar a desarrollar y comparar motores con dos objetivos independientes:

- **FAST PATH:** obtener la menor latencia y el mayor rendimiento posibles cuando el conjunto de trabajo cabe en los recursos rápidos.
- **CAPACITY PATH:** completar inferencias cuyo conjunto de pesos no cabe en VRAM ni en RAM, utilizando niveles de memoria más lentos y backpressure. El rendimiento puede caer drásticamente; la condición de éxito es progreso verificable y respuesta correcta sin corrupción ni fallo por presión evitable.

No se debe intercambiar capacidad por velocidad en silencio. El modo elegido, la política de memoria y sus límites deben quedar registrados en cada manifiesto.

No se promete que cualquier modelo pueda ejecutarse: siguen existiendo límites por arquitectura, operadores, formato, direccionamiento, tamaño de almacenamiento, contexto y compatibilidad de backend.

## 2. Arquitectura de investigación

| Capa | Responsabilidad | Evidencia requerida |
|---|---|---|
| NEPENTHES runner | Ejecutar una petición contra un servidor ya iniciado; no gestionar el ciclo de vida del servidor | Request/response, parámetros efectivos, tiempos, exit/status |
| Telemetría | Muestrear proceso, CPU, GPU, RAM, VRAM, swap, PSI, PCIe y almacenamiento | Muestras con timestamp, unidades y procedencia |
| Profiling | Importar perfiles Nsight y datos CPU cuando existan | SQLite/rep, versiones de herramientas, configuración de captura |
| Análisis | Correlacionar fases, transferencias, kernels, esperas y presión de memoria | Scripts reproducibles y resultados derivados |
| Contratos de memoria | Registrar presupuesto, asignaciones, residencia, eviction y fallback | Eventos de memoria con IDs, tamaños, nivel y causa |
| Runtime experimental | Implementar políticas de cache, prefetch, streaming y fallback en el motor | Cambios de código y pruebas unitarias/integración |
| Informes | Separar medición, estimación, hipótesis y limitaciones | Informe + manifest + hashes + datos primarios |

NEPENTHES es la metodología y harness; Tandem.cpp es el motor. No mezclar responsabilidades ni presentar una mejora del harness como una optimización del runtime.

## 3. Fase A — línea base y perfilado

### Métricas obligatorias

- Tiempo de carga y tiempo hasta modelo listo.
- Prefill: tokens, milisegundos y tokens/s.
- Decode: tokens, milisegundos y tokens/s.
- Latencia total y tiempo por token, con percentiles cuando haya repeticiones suficientes.
- CPU: utilización por proceso/hilo cuando sea medible, frecuencia y presión PSI.
- Memoria: RSS, HWM, RAM disponible, swap usada y actividad swap-in/out.
- GPU: utilización, VRAM, clocks, temperatura, potencia y PCIe RX/TX.
- CUDA: kernels, memcpy por dirección/tipo/tamaño, API host, sincronizaciones y grafos.
- Resultado funcional: stop/length/error, truncamiento y validación de la respuesta.

### Reglas de interpretación

1. Las duraciones de API CUDA host no son duración de ejecución GPU.
2. Los bytes acumulados transferidos no son memoria residente.
3. PCIe global no identifica por sí solo transferencias de pesos ni de expertos.
4. IDs de correlación de dominios distintos no se deben unir sin validar su semántica.
5. Ausencia de muestras CPU no equivale a cero actividad CPU.
6. Una captura que incluye carga del modelo no puede describirse como captura exclusiva de inferencia.
7. Toda hipótesis causal debe señalar qué datos la sostienen y qué alternativa no se ha descartado.

### Caso de partida del 14-11-2026

La captura correlacionada registra 159 secuencias GPU:
`moe_weighted_reduction_f32 → k_host_add_wait → k_host_add`.

También registra 44.488 operaciones memcpy y 7.604 sincronizaciones de stream. El hilo `llama-server` concentra las 84.116 llamadas CUDA Runtime observadas. La base no contiene tablas de muestreo CPU ni de planificación, por lo que no permite medir directamente la duración del trabajo CPU que publica el resultado. Los 52 solapamientos entre waits y sincronizaciones deben analizarse como intervalos relacionados, no como dos costes independientes.

Estos datos son baseline descriptivo; no demuestran todavía qué cambio de runtime aumentaría el rendimiento.

## 4. Fase B — optimización del FAST PATH

Investigar en este orden, midiendo cada hipótesis de forma aislada:

1. **Coste de sincronización:** reducir barreras y sincronizaciones innecesarias; medir latencia y throughput.
2. **Transferencias:** agrupar operaciones pequeñas, reducir bytes redundantes y validar pinned/pageable memory.
3. **Solapamiento:** prefetch y transferencias asíncronas donde exista trabajo independiente; verificar solapamiento real en el timeline.
4. **Planificador CPU/GPU:** reducir tiempo ocioso sin saturar CPU ni introducir más presión de memoria.
5. **CUDA Graphs:** medir coste de captura/instanciación, reutilización y condiciones de invalidez.
6. **Kernels:** optimizar solo los kernels dominantes después de aislar su coste real.
7. **MoE cache:** mejorar localidad, retención y anticipación de expertos usando trazas de routing verificadas.

Cada cambio debe tener: hipótesis, métrica objetivo, control, test, riesgo, resultado y decisión de conservar/revertir. No combinar varias optimizaciones en una única comparación.

## 5. Fase C — CAPACITY PATH y memoria jerárquica

Diseñar una política de residencia explícita con niveles:

- **L0 — GPU:** memoria de máxima velocidad y presupuesto estricto.
- **L1 — RAM:** staging/cache de CPU; memoria pinned solo cuando el coste y el límite lo justifiquen.
- **L2 — almacenamiento:** pesos/bloques no residentes, leídos bajo demanda o anticipadamente.
- **L3 — swap del sistema:** recurso de último respaldo, no nivel de cache controlado ni sustituto de RAM.

La política debe ser consciente de los límites de cada nivel y evitar sobreasignar buffers temporales. La especificación completa está en [diseño de memoria jerárquica](NEPENTHES-memory-tiering-design.md).

## 6. Fase D — MoE

Para cada experto o bloque, cuando el motor permita observarlo, registrar:

- ID de capa y experto.
- Evento de routing y momento de uso.
- Nivel de residencia antes/después.
- Hit/miss, eviction y motivo.
- Bytes leídos/escritos y latencias.
- Prefetch solicitado, completado, cancelado o tardío.
- Espera del consumidor y si hubo trabajo independiente que se solapó.

No inferir un routing por capa a partir de contadores agregados. Cuando el runtime no exponga esa información, declarar el límite y usar una métrica agregada.

## 7. Fase E — validación de capacidad

Matriz mínima:

| Escenario | Condición | Resultado requerido |
|---|---|---|
| S0 | Pesos y KV caben en VRAM | FAST PATH de referencia |
| S1 | Pesos exceden VRAM, caben en RAM + VRAM | Inferencia con offload y límites |
| S2 | Pesos exceden RAM disponible | Streaming desde almacenamiento, si el backend lo soporta |
| S3 | Contexto/KV es el límite dominante | Control de contexto/KV o error explícito y recuperable |
| S4 | Presión de memoria externa | Backpressure, no corrupción; cancelar o degradar con diagnóstico |
| S5 | Modelo/operador no compatible | Rechazo temprano, preciso y sin OOM tardío evitable |

Para cada escenario: medir progreso de tokens, latencia, peak RSS/VRAM, swap-in/out, I/O, fallos, respuesta y hashes. La prueba debe tener límites configurables de tiempo, disco y memoria. No lanzar stress tests destructivos ni llenar el almacenamiento.

## 8. Fase F — comparabilidad

- Fijar modelo y SHA-256, cuantización, motor/commit, backend, parámetros, contexto, prompt y generación.
- Distinguir caché fría/caliente y carga de modelo de inferencia.
- Ejecutar repeticiones suficientes para variabilidad; reportar mediana y dispersión.
- No comparar resultados de máquinas distintas como A/B directo.
- Mantener datos primarios inmutables; generar derivados aparte.
- Informar tanto throughput como capacidad máxima alcanzada y estabilidad.

## 9. Puertas de entrega

### Gate 1 — Instrumentación
- [ ] Runner y monitor registran configuración efectiva.
- [ ] Fases load/prefill/decode/close están separadas.
- [ ] Perfilado CUDA se interpreta correctamente.
- [ ] Perfilado CPU está presente o su ausencia queda declarada.
- [ ] Tests de parsers y agregadores pasan.

### Gate 2 — FAST PATH
- [ ] Baseline reproducible.
- [ ] Una optimización medida de forma aislada.
- [ ] Sin regresión funcional.
- [ ] Mejora estadísticamente defendible o resultado negativo documentado.

### Gate 3 — CAPACITY PATH
- [ ] Contrato de memoria y límites implementados.
- [ ] Cache/streaming/fallback tienen tests.
- [ ] Al menos un caso que exceda VRAM se completa.
- [ ] Un caso que exceda RAM disponible se completa si el backend lo soporta, o se rechaza tempranamente con explicación.
- [ ] No hay corrupción ni OOM evitable en los escenarios admitidos.

### Gate 4 — prueba Ubuntu
- [ ] Guía con prerequisitos y comandos exactos.
- [ ] Límites seguros y criterios de parada.
- [ ] Artefactos y hashes reproducibles.
- [ ] Usuario puede ejecutar la batería sin que el runner inicie, pare o reconfigure servicios por su cuenta.

## 10. Secuencia de implementación

1. Cerrar y archivar el baseline de Nsight actual.
2. Completar esquema de eventos de memoria y parser de perfiles.
3. Añadir perfiles CPU en una captura nueva, solo cuando el usuario autorice una nueva campaña.
4. Instrumentar memoria persistente/temporal y KV/cache en el runtime.
5. Añadir benchmarks FAST PATH controlados.
6. Diseñar e implementar una política de residencia L0/L1/L2.
7. Añadir tests de presión y fallback.
8. Medir MoE cache/prefetch y optimizar.
9. Publicar PRs de runtime separados en Tandem.cpp y PR de harness/documentación en LEONES.
10. Preparar guía Ubuntu y solicitar al usuario la prueba física.

## 11. No objetivos / seguridad

- No prometer ejecución de todo modelo, formato o arquitectura.
- No usar swap como si fuera VRAM/RAM rápida.
- No sacrificar integridad de datos para mantener un proceso vivo.
- No iniciar/detener servicios ni benchmarks en el equipo del usuario sin autorización.
- No modificar cafe-llama.cpp.
- No limpiar ni sobrescribir working trees locales del usuario.
- No declarar MEASURED lo que solo sea estimado, simulado o inferido.
