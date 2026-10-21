# Experimento LEONES: clúster de tres AMD BC-250, modelos grandes, conversaciones largas y hot swap

**ID:** `EXP-BC250-3N-HOTSWAP-KV-001`  
**Fecha:** 2026-10-21  
**Estado:** PLAN DE EXPERIMENTO — no ejecutado; no contiene mediciones propias de LEONES  
**Hardware objetivo:** 3 × AMD BC-250, 16 GB GDDR6 UMA nominal por placa  
**Runtime de referencia:** `llama.cpp` + Vulkan/RADV + RPC  
**TensorFold:** fuente de ideas de diseño, no runtime validado en BC-250  
**Principio:** medir primero, cambiar una sola variable cada vez, mantener un perfil estable recuperable.

---

## 1. Resumen ejecutivo

El experimento estudia cómo aprovechar tres nodos AMD BC-250 para dos tipos de carga que se alternan:

1. **Modelo grande:** un único modelo que no cabe holgadamente en una placa y necesita repartir capas/recursos entre varios nodos.
2. **Conversación muy larga:** sesiones con prefijos repetidos, historial extenso y KV cache costosa; interesa reutilizar estado, evitar recomputar el prefijo y conservar sesiones sin agotar la memoria.

Se investigarán ideas inspiradas en TensorFold —reutilización de prompt/estado, planificación de memoria, cambios de modelo y recuperación de conversaciones— y en MCDMA —reducir el coste del movimiento de estado—, pero sin presuponer que esos proyectos soporten BC-250. La documentación pública actual de TensorFold enumera Apple Silicon/Metal y NVIDIA/CUDA, y advierte que su adaptador no activa un clúster genérico ni ejecución distribuida mixta. En este experimento TensorFold no es dependencia de ejecución: sus conceptos se traducen a pruebas independientes sobre el runtime Vulkan.

La estrategia tiene dos carriles:

- **Carril A, modelo grande:** reparto de capas/modelo en tres BC-250 mediante RPC de `llama.cpp`, tras validar que la versión elegida soporta el número de workers y el split deseados.
- **Carril B, conversaciones largas:** caché de prefijos y gestión de sesiones; medir la persistencia real de KV state disponible en el motor. No se afirmará que KV cache es transferible entre nodos hasta demostrar compatibilidad de formato, arquitectura, posiciones, tipos K/V, tokenizer, versión y layout.

El *hot swap* se define de forma estricta como un cambio controlado de modelo/perfil/worker con continuidad del servicio o recuperación de sesión. No equivale a que las tres memorias físicas formen una RAM coherente. Tampoco se desalojará el KV de una conversación activa para cargar otro modelo sin una política explícita de persistencia y recuperación.

## 2. Preguntas de investigación

**RQ1 — Capacidad:** ¿qué modelos y cuantizaciones se pueden ejecutar de forma estable con 1, 2 y 3 nodos?

**RQ2 — Escalado:** ¿qué mejora o penalización añade el tercer nodo en prefill, generación, TTFT y tiempo total?

**RQ3 — Conversaciones largas:** ¿cuánto tiempo y memoria se ahorran al reutilizar un prefijo o sesión frente a recalcular el historial?

**RQ4 — Hot swap:** ¿qué política permite alternar un modelo grande y una sesión larga sin OOM, pérdida silenciosa de estado ni pausas descontroladas?

**RQ5 — Transporte:** ¿la red es el cuello de botella? ¿Compensa mejorar Ethernet o estudiar transporte de memoria más directo?

**RQ6 — TensorFold:** ¿qué ideas son transferibles conceptualmente y cuáles requieren características no disponibles en Vulkan/BC-250?

## 3. Hechos, hipótesis y límites

### Hechos de partida documentados

- La BC-250 usa memoria UMA: la RAM del sistema y los recursos accesibles por GPU compiten por el mismo presupuesto físico; no se deben sumar sin más los 16 GB nominales como memoria utilizable por el modelo.
- Existe una implementación comunitaria de dos nodos BC-250 con coordinador `llama-server`, worker `ggml-rpc-server`, Vulkan y una red backend dedicada de 2.5 GbE.
- `llama.cpp` RPC permite distribuir recursos/capas según la versión y configuración, pero no crea memoria coherente entre máquinas.
- El RPC de llama.cpp no debe exponerse a Internet ni a redes no confiables; tratarlo como protocolo privilegiado sin autenticación suficiente.
- La documentación pública de TensorFold enumera rutas de ejecución Metal en Apple Silicon y CUDA en NVIDIA. La ejecución nativa Vulkan en BC-250 no está acreditada en esta documentación.

### Hipótesis por comprobar

- **H1:** el tercer nodo aumenta el conjunto de modelos/quantizaciones que caben, aunque la generación no escale linealmente.
- **H2:** el tercer nodo puede empeorar tok/s en modelos que ya caben en dos, debido a comunicaciones y sincronización.
- **H3:** conservar y reutilizar prefijos es más beneficioso para conversaciones largas que mover KV cache entre hosts.
- **H4:** para hot swap, mantener pesos de modelos en SSD local y precargar el siguiente perfil es menos arriesgado que desalojar estado de una conversación activa.
- **H5:** una política de afinidad de sesión + presupuesto de memoria + caché LRU/TTL da mejor continuidad que cambiar libremente de nodo por petición.
- **H6:** RDMA/DMA-BUF o acceso remoto directo a memoria no deben abordarse hasta que los benchmarks identifiquen un cuello de botella real en las copias/red.

## 4. Topología propuesta

### Roles lógicos

- **BC250-1 — coordinador/API:** servicio `llama-server`, métricas, admisión de peticiones y registro de evidencia. Su GPU también puede alojar una parte del modelo distribuido.
- **BC250-2 — worker A:** `ggml-rpc-server`, enlazado exclusivamente a la red privada de backend.
- **BC250-3 — worker B:** `ggml-rpc-server`, enlazado exclusivamente a la red privada de backend.

La topología final depende de la versión de `llama.cpp`; no fijar de antemano una sintaxis de múltiples workers ni asumir que el reparto será equilibrado. Validar `--help`, logs de inicialización, dispositivos enumerados y capas realmente asignadas antes de benchmark.

### Redes

Separar cuando el hardware lo permita:

1. **Gestión:** SSH, administración y actualizaciones.
2. **API:** clientes al coordinador; no exponer workers.
3. **Backend/RPC:** red privada entre coordinador y workers, preferiblemente Ethernet cableado dedicado. Medir 2.5 GbE primero; 10 GbE solo si hay evidencia de cuello de botella.

Esquema de direcciones ilustrativo, no configuración para copiar:
- Gestión: red local existente.
- Backend: coordinador `10.250.0.1`; worker A `10.250.0.2`; worker B `10.250.0.3`.
- RPC: puerto configurado por la versión, restringido por firewall a las IP necesarias.

No mezclar estos ejemplos con la red real sin revisar rutas y colisiones. No asignar gateway/DNS al backend dedicado si no se necesitan. Comprobar `iperf3`, latencia, errores y drops antes de inferencia.

### Almacenamiento

- Cada nodo mantiene los pesos que necesita en SSD local cuando sea posible.
- Un NAS puede distribuir el catálogo, pero no se usa como ruta de lectura durante benchmarks salvo que ese sea el objeto medido.
- Cada artefacto de modelo tiene identificador, cuantización, tamaño y SHA-256.
- SSD local reduce tiempo de carga/cambio; no implica por sí mismo más tokens/s una vez que los pesos están residentes.

## 5. Perfiles de carga

### Perfil L — modelo grande distribuido

Objetivo: hallar el mayor modelo/cuanti que funcione estable con 1, 2 y 3 nodos.

- Empezar por un modelo MoE de pocos parámetros activos conocido en el inventario local, y luego uno mayor que fuerce el reparto. No descargar automáticamente ni sustituir el modelo activo.
- Mantener fijo el mismo archivo/hash, cuantización, prompt, salida y contexto al comparar número de nodos.
- Comparar split automático con split explícito solo si la versión ofrece una opción soportada y se puede verificar el reparto.
- Una prueba se considera fallida si arranca pero produce errores Vulkan/RPC, tokens corruptos, OOM, resets o degradación térmica sostenida.

### Perfil C — conversación larga

Objetivo: reducir recomputación del historial y conservar sesiones largas.

Separar cuatro casos:

1. **C0 — sin reutilización:** conversación completa enviada en cada turno; referencia de coste.
2. **C1 — caché de prefijo en el mismo proceso:** mismo modelo, tokenizer y prefijo idéntico; medir tokens prefijados y latencia de reanudación.
3. **C2 — conversación larga con compactación/resumen:** conservar una nota de estado estructurada y los últimos turnos; medir pérdida de información frente a historial completo.
4. **C3 — reinicio del servicio:** probar solo si el runtime soporta de forma documentada guardar/restaurar estado compatible. Si no existe esa función, marcarlo como no soportado, no simular persistencia con un archivo de KV arbitrario.

La caché KV no es universalmente portable: depende de arquitectura, versión del modelo, tokenizer, posición RoPE, configuración de atención, tipos K/V y formato interno. No copiar bytes de KV entre procesos o nodos hasta establecer un contrato y un test de equivalencia.

### Perfil H — alternancia y hot swap

Simular una carga realista alternando:
- sesión larga que necesita retener/reusar prefijo;
- petición ocasional a un modelo grande;
- vuelta a la sesión anterior.

Comparar tres políticas:

- **H0 — parada/carga fría:** parar perfil A, cargar perfil B y reabrir la conversación desde texto.
- **H1 — pesos precargados en SSD y sesión fijada:** cachear artefactos, pero una sola instancia activa; al cambiar, conservar historial/estado de sesión de forma lógica y reconstruir KV si no es portable.
- **H2 — instancias separadas, solo si cabe memoria:** un servicio para el modelo de sesión y otro para el modelo grande, con presupuesto de RAM/GTT explícito y sin sobrecomprometer la UMA.

No se recomienda hot swap in-place de pesos mientras hay una petición activa. El cambio debe ser transaccional: detener admisión, drenar solicitudes, registrar el estado, cambiar runtime, verificar identidad/modelo/salud, probar una generación corta y reabrir tráfico; ante fallo, restaurar el perfil anterior y demostrar recuperación.

## 6. Plan de fases y puertas de decisión

### Fase 0 — inventario y seguridad

Por nodo registrar:
- hostname/MAC, revisión de placa, firmware, CU activas y clocks;
- kernel, Mesa/RADV, Vulkan device, versión de `llama.cpp` y flags de compilación;
- RAM, GTT, TTM, VRAM reportada, almacenamiento y espacio libre;
- NIC, chipset USB-Ethernet si aplica, velocidad negociada y topología;
- temperaturas, ventiladores, potencia en pared y perfil estable de recuperación.

**Gate 0:** no avanzar si las tres placas no son individualmente estables o no se puede recuperar cada configuración.

### Fase 1 — línea base de un nodo

- Ejecutar un benchmark corto y repetible en BC250-1.
- Capturar carga del modelo, TTFT, prefill tok/s, generación tok/s, total, RAM/GTT, temperaturas y errores.
- Repetir al menos 3 veces después de una ejecución de calentamiento; informar mediana y rango, no solo la mejor cifra.
- No cambiar firmware, clocks, TTM y runtime a la vez.

**Gate 1:** modelo y salida reproducibles; no hay errores de cálculo ni OOM.

### Fase 2 — dos nodos

- Añadir BC250-2 como worker RPC en la interfaz privada.
- Probar modelo que cabe en un nodo y modelo que requiere dos, si están disponibles.
- Comparar con Fase 1 y guardar logs de asignación de capas y tráfico de red.
- Medir reinicio con caché de tensores del worker habilitada y deshabilitada solo si esa opción existe en el commit fijado.

**Gate 2:** conexión restringida, reparto confirmado y resultados repetibles.

### Fase 3 — tres nodos

- Añadir BC250-3 como segundo worker siguiendo la sintaxis exacta de la versión fijada.
- Verificar que el tercer dispositivo aparece en logs y que realmente recibe trabajo.
- Repetir la misma matriz de modelo, contexto y salida.
- Comparar 1 vs 2 vs 3 nodos en capacidad, latencia y tok/s.

**Gate 3:** tercer nodo aporta capacidad o mejora cuantificada; si no, registrar por qué y conservar el perfil de dos nodos.

### Fase 4 — caché de prefijos y sesiones largas

- Fijar un modelo y prompt de sistema.
- Preparar conversaciones de longitud creciente que quepan de forma segura en el presupuesto: 8K, 16K, 32K y, solo si hay memoria, 64K+ tokens.
- Usar exactamente el mismo prefijo para la prueba de reutilización; una sola diferencia de token invalida la comparación de cache hit.
- Registrar tiempo de prefill, tokens reutilizados si el motor los expone, memoria KV, tiempo de generación y calidad.
- Repetir con cambios de modelo, reinicio y compactación por separado.

**Gate 4:** solo declarar “KV persistente” si el estado se restaura y se valida; la simple conservación del historial textual no equivale a KV cache persistida.

### Fase 5 — hot swap y recuperación

- Definir dos perfiles: `large-model` y `long-session`.
- Implementar inicialmente un controlador externo/manual de cambio; no tocar ODS ni producción en esta fase.
- Secuencia: `stage → drain → checkpoint/logical state → stop → load → verify identity → health/generation test → route → evidence`.
- Inyectar fallos controlados: worker no disponible, modelo/hash incorrecto, timeout de carga, memoria insuficiente, API no saludable.
- Verificar que el coordinador no anuncia el perfil nuevo antes de completar la prueba de generación y que restaura el anterior ante fallo.
- Mantener una salida de emergencia: perfil pequeño conocido que quepa en el nodo coordinador, si se ha validado previamente.

**Gate 5:** ningún cambio deja un estado ambiguo; todo fallo termina en perfil previo restaurado o servicio explícitamente no disponible.

### Fase 6 — cuello de botella de red y memoria

Solo después de medir las fases anteriores:
- comparar 1/2.5/10 GbE si el hardware está disponible;
- separar tiempo de prefill, comunicación y decode cuando sea posible;
- perfilar copias de buffers, uso de CPU y latencia;
- investigar RDMA/DMA-BUF como rama de I+D, no requisito para el primer resultado.

**Gate 6:** no invertir en adaptadores ni implementar una ruta DMA nueva sin evidencia de que la red/copia domina el tiempo total.

## 7. Matriz mínima de pruebas

| ID | Nodos | Perfil | Contexto | Política | Resultado buscado |
|---|---:|---|---:|---|---|
| B1 | 1 | Modelo que cabe | 8K | Cold | Baseline |
| B2 | 2 | Mismo modelo | 8K | Cold | Coste RPC |
| B3 | 3 | Mismo modelo | 8K | Cold | Coste del tercer nodo |
| L1 | 1 | Modelo grande | Contexto fijo | Cold | Confirmar límite local |
| L2 | 2 | Modelo grande | Mismo | Cold | Capacidad/velocidad |
| L3 | 3 | Modelo grande | Mismo | Cold | Capacidad/velocidad |
| C1 | 1 | Conversación larga | 8K–64K+ | Sin caché | Referencia de prefill |
| C2 | 1 | Conversación larga | Igual | Prefijo reutilizado | Ahorro de recomputación |
| C3 | 3 | Conversación larga | Igual | Sesión fijada | Coste del reparto |
| H1 | 3 | Alternancia de perfiles | Igual | Carga fría | Tiempo de cambio |
| H2 | 3 | Alternancia de perfiles | Igual | Pesos locales precopiados | Ahorro de carga |
| H3 | 3 | Sesión larga + modelo grande | Igual | Recuperación lógica | Continuidad tras swap |
| N1 | 3 | Modelo fijo | Igual | Red alternativa | Impacto de red |

No es obligatorio ejecutar todas las combinaciones si el hardware no permite el contexto/modelo. Registrar `not_run` y motivo en vez de completar con estimaciones.

## 8. Métricas y protocolo

### Métricas por ejecución

- `run_id`, fecha, perfil, número de nodos y roles.
- Modelo, origen, revisión/hash SHA-256, cuantización, tokenizer/template.
- Commit de llama.cpp, flags de build, backend y CLI exacta.
- `n_ctx`, longitud de entrada/salida, tipo K/V, paralelismo, split y capas asignadas.
- TTFT; prefill tok/s; decode tok/s medio; tasa de primeros 100 tokens si se compara con el protocolo de referencia; duración total.
- Latencia p50/p95 bajo concurrencia; errores, timeout, OOM y reinicios.
- RAM libre, GTT/VRAM, swap, CPU/GPU, clocks, temperaturas, potencia en pared.
- Tráfico/throughput/latencia de cada enlace y retransmisiones/drops.
- Cache hit/miss, tokens prefijados/reutilizados si están expuestos, tiempo de carga y tamaño del estado guardado.
- Resultado de equivalencia/calidad; cualquier cambio de salida por variabilidad del muestreo.

### Reglas

1. Al menos 3 repeticiones válidas por condición, tras warm-up.
2. Fijar prompt, tokens de salida, parámetros de muestreo, contexto, cuantización y temperatura.
3. Reportar mediana, rango y p95 cuando corresponda.
4. Separar mediciones de red sintética de resultados de inferencia.
5. No comparar cifras de fuentes comunitarias como si fueran mediciones propias.
6. Registrar el entorno completo; no cambiar de commit entre condiciones de una misma comparación.

## 9. Diseño de hot swap

### Estados del controlador

`ACTIVE_A → DRAINING → STATE_CAPTURED → STOPPED_A → LOADING_B → VERIFYING_B → ACTIVE_B`

Ante cualquier error desde `LOADING_B`:
`ROLLBACK_B → RESTORE_A → VERIFY_A → ACTIVE_A`

Si no se puede recuperar A:
`UNAVAILABLE` con motivo y evidencia; nunca anunciar falsamente `ACTIVE_A`.

### Estado de sesión

Mantener por separado:
- historial textual canónico y metadatos de la conversación;
- resumen/nota de continuidad, si se aplica compactación;
- estado KV, solo cuando el motor soporte explícitamente guardado/restauración compatible;
- identidad de modelo/tokenizer/template y hash del runtime;
- posición de tokens y configuración de atención relevante.

Si el estado KV no es portable, reconstruirlo desde historial/prefijo con el modelo original o reanudar con una nota compactada, dejando claro que la segunda opción puede cambiar la fidelidad. No restaurar KV bajo otro modelo o cuantización por defecto.

### Política de admisión y caché

- Reservar memoria de sistema y margen de seguridad; no usar el máximo nominal de UMA como presupuesto de pesos.
- No permitir que peticiones concurrentes consuman toda la memoria destinada a KV.
- Mantener afinidad de sesión con el nodo/perfil mientras exista estado residente.
- TTL/LRU solo para estados inactivos; nunca desalojar silenciosamente una sesión activa.
- Precargar pesos en SSD local y verificar hash antes de la ventana de swap.
- Evitar ejecutar simultáneamente dos modelos pesados salvo que una medición demuestre margen real de RAM/GTT.
- Registrar cada eviction, cache miss, reconstrucción de KV y cambio de modelo.

## 10. Cómo usar ideas de TensorFold sin asumir soporte

| Idea | Adaptación propuesta | Estado |
|---|---|---|
| Reutilización de prefijos | Probar caché de prompt de llama.cpp con prefijo exacto | Por medir en BC-250 |
| Reanudación de conversación | Historial canónico; KV solo con soporte explícito del motor | Por validar |
| Presupuesto de memoria | Planificador LEONES de RAM/GTT/KV/contexto por perfil | Diseño |
| Hot swap | Controlador transaccional stage/drain/verify/rollback | Diseño |
| Speculative decoding/MTP | No incluir en la línea base; evaluar solo si build/modelo Vulkan lo soporta | Fuera de alcance inicial |
| MCDMA/RDMA | Investigación de transporte tras demostrar cuello de botella | I+D posterior |
| TensorFold como motor | No usar como backend BC-250 hasta que exista soporte Vulkan/AMD documentado y probado | No soportado por evidencia actual |

## 11. Riesgos y mitigaciones

- **RPC expuesto:** aislar backend, firewall de allowlist, no bind a interfaz pública.
- **OOM/agotamiento UMA:** contextos incrementales, una variable cada vez, margen de RAM/GTT, sin swap automático de perfiles en producción.
- **Corrupción o incompatibilidad de KV:** no serializar/restaurar KV por métodos no documentados; pruebas de equivalencia antes de habilitar.
- **Degradación térmica:** validar ventilación y potencia sostenida en cada placa.
- **Cambio de versión:** fijar commit y hashes; repetir baseline al actualizar.
- **Tercer nodo sin beneficio:** conservar configuración de dos nodos como alternativa documentada.
- **Pérdida de conversación en swap:** historial lógico durable y prueba de recuperación antes de detener el servicio anterior.
- **TensorFold no compatible:** tratarlo como referencia conceptual, no dependencia.
- **Confundir capacidad con rendimiento:** reportar capacidad de modelo, TTFT, prefill y decode por separado.

## 12. Artefactos de evidencia LEONES

Guardar por ejecución, sin modelos ni datos privados en Git:
- `artifacts/benchmarks/bc250-3n/<run_id>/manifest.json`
- `artifacts/benchmarks/bc250-3n/<run_id>/metrics.json`
- `artifacts/benchmarks/bc250-3n/<run_id>/logs/`
- `artifacts/benchmarks/bc250-3n/<run_id>/environment.txt`
- `artifacts/benchmarks/bc250-3n/<run_id>/sha256sums.txt`

El manifiesto debe incluir estado de evidencia `PLANNED | OBSERVED | MEASURED | REPRODUCED | FAILED`; modelo/quant/hash; hardware y software; perfil; comandos exactos; métricas; desviaciones; y enlace a este plan. Nunca registrar tokens de API, conversaciones privadas ni pesos de modelos.

### Plantilla de resultado

```json
{
  "experiment_id": "EXP-BC250-3N-HOTSWAP-KV-001",
  "run_id": "TODO",
  "status": "PLANNED",
  "nodes": 3,
  "profile": "large-model | long-session | hot-swap",
  "runtime": {
    "name": "llama.cpp",
    "commit": "TODO",
    "backend": "Vulkan/RADV",
    "build_flags": "TODO"
  },
  "model": {
    "id": "TODO",
    "quantization": "TODO",
    "sha256": "TODO"
  },
  "workload": {
    "input_tokens": null,
    "output_tokens": null,
    "context_tokens": null,
    "kv_type_k": "TODO",
    "kv_type_v": "TODO"
  },
  "metrics": {
    "ttft_ms": null,
    "prefill_tok_s": null,
    "decode_tok_s_median": null,
    "total_seconds": null,
    "model_load_seconds": null,
    "kv_restore_seconds": null,
    "network_mbps": null,
    "ram_gtt_per_node": {},
    "power_w_per_node": {},
    "temperature_c_per_node": {}
  },
  "evidence": {
    "classification": "NOT_MEASURED",
    "logs_path": "TODO",
    "notes": []
  }
}
```

## 13. Criterios de éxito

El experimento se considerará exitoso cuando:

1. El mismo modelo se ejecute de forma estable y documentada con 1, 2 y 3 nodos, con reparto confirmado.
2. Se identifique un caso donde el tercer nodo aumente capacidad o una métrica de rendimiento de forma reproducible.
3. Se mida el beneficio real de reutilización de prefijo para conversaciones largas.
4. Se complete un cambio de perfil con verificación de identidad, prueba de generación y rollback demostrado.
5. Se pueda recuperar una conversación después del cambio, distinguiendo KV restaurada de historial reconstruido.
6. Toda cifra esté clasificada como medida, reproducida, observada, estimada o no ejecutada.

No es requisito que tres nodos sean más rápidos en todos los casos ni que TensorFold funcione en BC-250.

## 14. Orden de ejecución recomendado

1. Inventario y estabilidad térmica de los tres nodos.
2. Baseline de un nodo.
3. Reproducir el clúster de dos nodos.
4. Incorporar el tercer worker y validar el reparto.
5. Medir modelos grandes en 1/2/3 nodos.
6. Medir caché de prefijo en un proceso estable.
7. Medir sesiones largas y política de compactación.
8. Simular hot swap lógico, sin manipular KV binaria.
9. Añadir persistencia de estado solo si el runtime la documenta.
10. Perfilar red/copia y decidir si tiene sentido investigar RDMA/DMA-BUF.

## 15. Fuentes

- [LEONES: AMD BC-250 — características, inferencia, clúster, red y RPC](../sources/AMD-BC-250-LLM-CLUSTER.md)
- [4claps/bc250-llama-cluster — estado validado de dos nodos](https://github.com/4claps/bc250-llama-cluster/blob/main/docs/current-state.md)
- [4claps/bc250-llama-cluster — arquitectura](https://github.com/4claps/bc250-llama-cluster/blob/main/docs/architecture.md)
- [wdonega/bc250-llm-setup — Vulkan/RPC y metodología](https://github.com/wdonega/bc250-llm-setup)
- [llama.cpp upstream](https://github.com/ggml-org/llama.cpp)
- [TensorFold — brief y soporte declarado](https://tensorfold.dev/brief)
- [TensorFold — guía y límites de ejecución distribuida](https://tensorfold.dev/guide)
- [MCDMA — investigación de acceso/transporte de memoria](https://github.com/ashhart/MCDMA)

---

**Conclusión:** la ruta principal es tres BC-250 + Vulkan/RADV + `llama.cpp` RPC. TensorFold aporta ideas para caché, estado y planificación, pero no se considera runtime compatible. El primer objetivo no es “memoria compartida” en sentido físico: es medir el reparto del modelo y el ahorro de recomputación, y construir un hot swap transaccional que preserve la conversación sin arriesgar el servicio estable.
