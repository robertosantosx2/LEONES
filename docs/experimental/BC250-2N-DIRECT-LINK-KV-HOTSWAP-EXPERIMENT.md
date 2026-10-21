# Experimento LEONES: dos AMD BC-250, enlaces directos Ethernet/USB y hot swap de estado

**ID:** `EXP-BC250-2N-DIRECT-LINK-KV-HOTSWAP-001`  
**Fecha:** 2026-10-21  
**Estado:** PLAN EXPERIMENTAL — pendiente de ejecución y mediciones LEONES  
**Hardware:** 2 × AMD BC-250, cada una con 16 GB GDDR6 UMA nominal  
**Runtime de referencia:** `llama.cpp` + Vulkan/RADV + RPC  
**Transporte inicial:** Ethernet punto a punto sin switch; comparación con adaptadores USB 3.x a 2.5GbE en enlace punto a punto  
**Ámbito:** modelos grandes, conversaciones largas, reutilización de prefijos/KV, hot swap y pruebas de red/memoria.

> **Distinción esencial:** “enlace USB” en este plan significa adaptadores de red USB 3.x → Ethernet 2.5GbE en ambos nodos, unidos por un cable Ethernet directo, sin switch. No significa conectar los dos puertos USB-A de las placas con un cable USB-A↔USB-A. Un cable USB convencional no crea una red host-to-host segura ni un canal RDMA automáticamente. MCDMA es una implementación específica para Apple Silicon/NVIDIA y no se puede trasladar directamente a BC-250.

---

## 1. Objetivo

Aislar cuánto influyen el transporte y las técnicas de gestión de estado en un clúster de dos BC-250. El estudio es una prueba controlada que precede al experimento de tres nodos `EXP-BC250-3N-HOTSWAP-KV-001`.

Queremos responder:

1. ¿Se puede conectar coordinador y worker directamente sin switch y mantener una red de gestión separada?
2. ¿Qué diferencia hay entre usar la Ethernet integrada (habitualmente 1 GbE) y adaptadores USB 3.x a 2.5GbE?
3. ¿La diferencia de red cambia el rendimiento de `llama.cpp` RPC o la red no es el cuello de botella?
4. ¿Cómo afectan el reparto de capas, la caché de tensores del worker y la carga fría/caliente?
5. ¿Qué mejora aporta la reutilización de prefijos para conversaciones largas?
6. ¿Qué políticas de hot swap conservan la continuidad de sesión sin asumir que el estado KV es portable?
7. ¿Qué evidencias justificarían investigar DMA-BUF/RDMA en una fase posterior?

## 2. Arquitectura base

- **Nodo A — coordinador:** `llama-server`, GPU Vulkan local, API de cliente y logs.
- **Nodo B — worker:** `ggml-rpc-server` (el nombre del binario depende de la versión de llama.cpp; verificar `--help`), GPU Vulkan local y caché de tensores si está disponible.
- **Gestión:** Ethernet integrada o red de administración existente para SSH/paquetes/API, sin confundirla con el enlace medido.
- **Backend experimental:** un único enlace punto a punto dedicado entre A y B, sin switch.
- **Almacenamiento:** modelo y artefactos copiados a SSD local; NAS solo para distribución, no para la prueba principal.

```text
Cliente/API ── red de gestión ── Nodo A (llama-server + Vulkan)
                                      │
                                      │ backend directo, sin switch
                                      │ Ethernet o USB-2.5GbE
                                      ▼
                              Nodo B (RPC worker + Vulkan)
```

RPC no crea memoria física compartida ni coherencia de memoria entre equipos. Los pesos/capas se asignan entre dispositivos; las transferencias siguen teniendo coste de red.

## 3. Variantes de enlace

### N0 — referencia con enlace de gestión

Solo para medir la condición inicial y verificar que cada placa funciona individualmente. No usar esta condición para inferir el rendimiento de un backend dedicado si el tráfico de gestión comparte el enlace.

### N1 — Ethernet integrada directa

- Conectar el puerto Ethernet integrado de A directamente al de B con un cable compatible.
- Configurar IPs estáticas en una subred privada exclusiva, sin gateway ni DNS en esa interfaz.
- Comprobar velocidad negociada, MTU, errores y throughput.
- Mantener SSH/API por una segunda interfaz de gestión cuando sea posible. Si no hay segunda interfaz, establecer una ventana de administración segura y documentar que los planos están compartidos.
- Esta variante probablemente quede limitada a 1 GbE, sujeto a negociación y hardware reales.

### N2 — USB 3.x a 2.5GbE directo

- Instalar un adaptador USB 3.x → 2.5GbE en cada nodo; unir ambos adaptadores con Ethernet directamente, sin switch.
- Confirmar chipset y controlador Linux, enumeración estable, velocidad negociada de 2.5 Gb/s, USB link speed y ausencia de resets.
- Asignar IPs estáticas y limitar RPC al backend.
- Fijar las interfaces por MAC permanente en scripts/Ansible, no por nombres USB que pueden cambiar tras reinicio.
- Registrar CPU del host y temperatura de los adaptadores bajo carga; el rendimiento real puede quedar limitado por el adaptador, el bus USB, el controlador o la CPU.

### N3 — USB 2.5GbE como enlace alternativo y recuperación

Repetir N2 tras reiniciar ambos nodos, desconectar/reconectar el adaptador y cargar la red al mismo tiempo que la inferencia. Medir robustez y tiempo de recuperación; no solo throughput máximo.

### Fuera de alcance de N1/N2

No intentar conectar directamente dos puertos USB host con un cable USB-A↔USB-A ni asumir que USB-C ofrece DMA compartido. Un enlace RDMA requiere NICs, drivers, memoria registrada y soporte de software específicos. El MCDMA de Ash Hart utiliza una arquitectura Apple Silicon/NVIDIA y hardware/controladores concretos; no es evidencia de que dos BC-250 puedan usar RDMA por USB.

## 4. Seguridad y red

- Backend sin ruta por defecto, DNS ni exposición a redes no confiables.
- Firewall: permitir puerto RPC solo desde la IP backend del coordinador.
- No escuchar RPC en una interfaz pública. El protocolo RPC de llama.cpp no debe tratarse como autenticado.
- La API del coordinador también debe estar restringida a clientes autorizados.
- Verificar las rutas antes y después de configurar el enlace para no perder la administración remota.
- Guardar el estado de red anterior y tener acceso físico/recuperación antes de cambiar rutas.
- No usar IPs ilustrativas sin comprobar colisiones en la red real.

Ejemplo de direccionamiento de laboratorio (adaptar a la red real):

| Nodo | Interfaz backend | Dirección ilustrativa |
|---|---|---|
| A | NIC dedicada elegida | `10.250.0.1/30` |
| B | NIC dedicada elegida | `10.250.0.2/30` |
| B | RPC | `10.250.0.2:50052` |

Validación Linux (sustituir las interfaces y direcciones reales):

```bash
ip -br link
ip -br addr
ip route
sudo ethtool <INTERFAZ_BACKEND>
ip -s link show <INTERFAZ_BACKEND>
iperf3 -s
# En el otro nodo:
iperf3 -c <IP_BACKEND_SERVIDOR> -P 1
iperf3 -c <IP_BACKEND_SERVIDOR> -P 4
```

Repetir en ambos sentidos cuando proceda, con MTU por defecto inicialmente. No optimizar MTU/Jumbo Frames hasta tener baseline reproducible y compatibilidad de extremo a extremo.

## 5. Matriz de pruebas de red

| ID | Enlace | Switch | Condición | Qué se mide |
|---|---|---|---|---|
| NET-0 | Gestión existente | según LAN | Solo salud | Línea base funcional |
| NET-1 | Ethernet integrada | No | Punto a punto | Throughput, RTT, errores |
| NET-2 | USB 3.x → 2.5GbE | No | Punto a punto | Throughput, RTT, CPU, resets |
| NET-3 | USB 2.5GbE | No | Tras reinicio | Persistencia y recuperación |
| NET-4 | Mejor enlace de NET-1/2 | No | Inferencia sostenida | Tráfico, drops y estabilidad bajo carga |
| NET-5 | Enlace seleccionado | No | Fallo de enlace inducido | Detección, fallo seguro y recuperación |

Por cada condición: 3 ejecuciones válidas como mínimo, con salida en ambos sentidos si la herramienta lo permite; registrar mediana, rango y pérdidas/errores. El número nominal del adaptador no se reporta como throughput real.

## 6. Matriz de inferencia: controlar variables

### Perfil M — modelo distribuido

Comparar en las mismas condiciones:
- A solo, modelo que quepa localmente;
- A + B por RPC, el mismo modelo;
- A + B por RPC, un modelo/cuanti que no quepa holgadamente en A.

Mantener idénticos hash del GGUF, cuantización, contexto, prompt, tokens de salida, parámetros de muestreo, versión de `llama.cpp`, flags de compilación, tipo K/V y modo de split. Guardar logs que confirmen el dispositivo remoto y las capas realmente asignadas.

Medir:
- TTFT, prefill tok/s, decode tok/s y duración total;
- tiempo de carga fría y reinicio con caché de tensores del worker, si existe en esa versión;
- CPU, RAM/GTT, temperaturas, potencia en pared;
- tráfico backend durante carga de pesos, prefill y decode.

La condición “modelo más grande” debe evaluarse como capacidad y estabilidad además de velocidad. Un split puede ser más lento para el mismo modelo, pero habilitar un modelo/cuanti que no cabe en una placa.

### Perfil P — prefijo y conversación larga

1. **P0, sin reutilización:** reenviar historial completo en cada turno; referencia de recomputación.
2. **P1, prefijo idéntico:** repetir el mismo prompt de sistema y prefijo exacto para medir la caché de prompt que el motor realmente exponga.
3. **P2, sesión extendida:** crecer por pasos de 8K, 16K, 32K y solo ampliar a 64K+ si la memoria es segura.
4. **P3, reinicio:** comprobar si la versión fija documenta guardar/restaurar sesión o KV. Si no, marcarlo como no soportado.
5. **P4, compactación:** comparar historial completo con resumen estructurado y últimos turnos; esta técnica conserva estado semántico, pero no es equivalente a mantener la KV exacta.

La KV depende del modelo, tokenizer, configuración de atención/RoPE, posiciones, tipos K/V, versión y layout. No copiar un blob KV entre procesos o nodos sin una interfaz documentada y una prueba de equivalencia. La caché de prefijos del motor puede residir en memoria del host y no es automáticamente KV de GPU transferible.

### Perfil H — hot swap entre modelo grande y sesión larga

Escenario: una conversación larga está activa; llega una petición que necesita un modelo mayor; después se vuelve a la conversación.

Comparar:

- **H0 — cold swap:** drenar peticiones, guardar historial canónico, parar A, cargar modelo B, verificarlo y reanudar la conversación desde texto.
- **H1 — pesos precopiados:** tener el archivo de B en SSD local, verificar hash y medir cuánto se ahorra en distribución/carga; la KV se reconstruye si no existe restauración soportada.
- **H2 — instancias separadas:** solo si RAM/GTT y margen térmico lo permiten. No sobrecomprometer UMA ni desalojar silenciosamente una sesión activa.
- **H3 — fallback:** si B no carga, volver a A o marcar servicio no disponible; nunca anunciar modelo activo antes de un health check y una generación de prueba.

Secuencia transaccional:
`ACTIVE_A → DRAIN → CAPTURE_LOGICAL_STATE → STOP_A → LOAD_B → VERIFY_HASH/IDENTITY → HEALTH_TEST → ACTIVE_B`

Ante fallo:
`LOAD_FAILED → RESTORE_A → VERIFY_A → ACTIVE_A`; si no se recupera, `UNAVAILABLE` con evidencia.

El estado lógico debe incluir historial, modelo/tokenizer/template, configuración, posiciones y metadatos. Solo etiquetar como “KV persistida” si el runtime la guarda/restaura de forma documentada y se verifica equivalencia.

## 7. Técnicas que se investigarán

| Técnica | Aplicación en este experimento | Riesgo/condición |
|---|---|---|
| RPC de `llama.cpp` | Repartir capas/recursos entre A y B | No es memoria física compartida; RPC aislado |
| Caché de tensores del worker | Evitar retransmitir pesos al reiniciar, si la versión lo soporta | Verificar flag y comportamiento del commit fijado |
| Caché de prefijos | Reducir prefill repetido en conversaciones | Prefijo debe ser idéntico; medir hit real |
| KV cache cuantizada | Reducir memoria por token/contexto si backend/modelo lo soportan | Comparar calidad y estabilidad; no asumir soporte uniforme |
| Historial canónico + resumen | Reanudar tras cambio de modelo | Puede perder detalles; no equivale a KV |
| Hot swap transaccional | Cambio de modelo con drain, health check y rollback | No cambiar pesos durante una petición activa |
| Pesos precopiados | Reducir carga fría/distribución | SSD acelera carga, no necesariamente decode |
| USB 2.5GbE | Enlace backend económico dedicado | Adaptador/controlador/USB pueden ser cuello de botella |
| DMA-BUF/RDMA | Rama futura si profiler demuestra cuello de botella | No implementado ni acreditado en BC-250 por este plan |
| Ideas de TensorFold | Planificación de memoria, estado y reutilización | TensorFold no se asume compatible con BC-250/Vulkan |

## 8. Procedimiento paso a paso

### Fase 0 — inventario y salvaguardas
- Registrar placa, firmware, CUs, kernel, Mesa/RADV, Vulkan, TTM/GTT, versión/commit de llama.cpp, SSD, adaptadores USB y MACs.
- Validar cooling, sensores, ventiladores, PSU y estabilidad de cada placa por separado.
- Exportar configuración de red previa y confirmar acceso local de recuperación.

**Gate:** no avanzar si hay inestabilidad, errores Vulkan o una recuperación de red no probada.

### Fase 1 — red directa
- Ejecutar NET-1 y NET-2 con el mismo protocolo, sin inferencia.
- Medir throughput, RTT, errores, CPU, resets y estabilidad tras reinicio.
- Elegir enlace provisional por resultados reales, no por velocidad nominal.

### Fase 2 — RPC
- Fijar commit de llama.cpp y build con Vulkan + RPC.
- Levantar worker B en la IP backend únicamente y permitir el puerto desde A.
- Ejecutar una respuesta determinista pequeña, verificar salud, dispositivo remoto y logs.
- Repetir con enlace Ethernet integrado y USB 2.5GbE.

**Gate:** si el modelo o los logs no muestran uso real del worker, no contabilizar la prueba como distribuida.

### Fase 3 — modelos
- Baseline A local.
- Modelo pequeño en A+B.
- Modelo grande distribuido en A+B.
- Repetir con enlace seleccionado y comparar métricas y estabilidad.

### Fase 4 — conversaciones
- Fijar modelo, template y prefijo; medir P0/P1 con contextos incrementales.
- Registrar coste de prefill y memoria del KV si es visible.
- Probar reinicio/restauración solo si la interfaz de la versión lo documenta.
- Separar resultados de caché de prefijo, KV persistida y resumen semántico.

### Fase 5 — hot swap
- Ejecutar H0/H1/H2 solo en entorno de prueba, sin servicio de producción.
- Inyectar fallo de carga, hash incorrecto, worker caído, timeout y agotamiento de memoria.
- Confirmar rollback o estado no disponible; revisar que el coordinador no enrute a un modelo sin verificar.

### Fase 6 — decisión
- Seleccionar Ethernet directo o USB 2.5GbE según mediciones y estabilidad.
- Mantener la alternativa documentada como fallback.
- Investigar DMA-BUF/RDMA solo si se demuestra que transporte/copia domina una fracción significativa del tiempo total.

## 9. Métricas por ejecución

- `run_id`, timestamp, enlace, adaptadores/chipsets, MAC, velocidad negociada, MTU.
- `iperf3` throughput por dirección, RTT, pérdidas, drops, resets USB, uso CPU.
- Hardware/firmware/kernel/Mesa/RADV y versión de llama.cpp, flags y CLI.
- Modelo/hash/cuanti, contexto, tokens entrada/salida, tipos K/V, split/capas.
- TTFT, prefill tok/s, decode tok/s, total, carga fría/caliente.
- Cache hit/miss y tokens prefijados si el motor lo expone; memoria KV y tiempo de restauración si existe.
- RAM/GTT, swap, temperatura, clocks, potencia por nodo, errores.
- Salud API/RPC y resultado de generación determinista.
- Evidencia: `PLANNED | OBSERVED | MEASURED | REPRODUCED | FAILED | NOT_SUPPORTED`.

Mínimo 3 repeticiones válidas por condición, tras warm-up. Informar mediana y rango; incluir p95 cuando haya concurrencia. No reportar resultados comunitarios como mediciones LEONES.

## 10. Artefactos

Guardar logs y métricas, no pesos ni conversaciones privadas, en:

```text
artifacts/benchmarks/bc250-2n-direct-link/<run_id>/
  manifest.json
  metrics.json
  environment.txt
  network/
  llama.cpp/
  hot-swap/
  sha256sums.txt
```

Manifiesto de ejemplo:

```json
{
  "experiment_id": "EXP-BC250-2N-DIRECT-LINK-KV-HOTSWAP-001",
  "run_id": "TODO",
  "status": "PLANNED",
  "link": {
    "mode": "direct-ethernet | usb-2.5gbe",
    "switch_used": false,
    "adapter_model": "TODO",
    "negotiated_mbps": null,
    "iperf3_mbps": null,
    "rtt_ms": null,
    "drops": null,
    "usb_resets": null
  },
  "runtime": {
    "name": "llama.cpp",
    "commit": "TODO",
    "backend": "Vulkan/RADV",
    "rpc_enabled": true
  },
  "workload": {
    "profile": "large-model | long-session | hot-swap",
    "model_sha256": "TODO",
    "quantization": "TODO",
    "input_tokens": null,
    "output_tokens": null,
    "context_tokens": null
  },
  "metrics": {
    "ttft_ms": null,
    "prefill_tok_s": null,
    "decode_tok_s": null,
    "total_seconds": null,
    "model_load_seconds": null,
    "kv_restore_seconds": null,
    "ram_gtt_by_node": {},
    "temperature_by_node": {},
    "power_w_by_node": {}
  },
  "evidence": {
    "classification": "NOT_MEASURED",
    "logs_path": "TODO",
    "notes": []
  }
}
```

## 11. Criterios de éxito

1. Dos nodos estables, con administración recuperable y RPC restringido.
2. Comparación reproducible de Ethernet directo y USB 2.5GbE directo, sin switch.
3. Confirmación de qué enlace es mejor bajo inferencia, no solo en `iperf3`.
4. Prueba de modelo distribuido con evidencia de uso real de la GPU remota.
5. Medición de ahorro de prefijo en conversación larga, sin confundirlo con KV portable.
6. Hot swap con verificación de identidad y rollback demostrado.
7. Ninguna afirmación de RDMA/USB-memory-sharing sin una prueba específica del mecanismo.
8. Resultados etiquetados como medidos, reproducidos, fallidos, no soportados o no ejecutados.

## 12. Decisiones que se tomarán con los datos

- Si USB 2.5GbE aporta rendimiento real o solo más throughput sintético.
- Si la red limita el prefill, la distribución de pesos o el decode.
- Si conviene dedicar el enlace más rápido al backend o reservarlo para transferencia de modelos/estado.
- Si las conversaciones largas se benefician más de la caché de prefijos, del tipo K/V o de compactación lógica.
- Si el hot swap es aceptable con reconstrucción de KV o requiere investigar una interfaz de persistencia específica.
- Si hay evidencia suficiente para estudiar DMA-BUF/RDMA; no comprar hardware especializado antes de este punto.

## 13. Referencias

- [4claps/bc250-llama-cluster — TL;DR de dos nodos y enlace directo USB 2.5GbE](https://github.com/4claps/bc250-llama-cluster/blob/main/docs/TLDR.md)
- [4claps/bc250-llama-cluster — arquitectura](https://github.com/4claps/bc250-llama-cluster/blob/main/docs/architecture.md)
- [4claps/bc250-llama-cluster — estado validado](https://github.com/4claps/bc250-llama-cluster/blob/main/docs/current-state.md)
- [wdonega/bc250-llm-setup — multi-nodo y caché RPC](https://github.com/wdonega/bc250-llm-setup)
- [llama.cpp upstream](https://github.com/ggml-org/llama.cpp)
- [Ash Hart MCDMA — documentación e instalación](https://github.com/ashhart/MCDMA)
- [LEONES: clúster AMD BC-250](../sources/AMD-BC-250-LLM-CLUSTER.md)
- [LEONES: experimento de tres nodos, KV y hot swap](./BC250-3N-HOTSWAP-KV-EXPERIMENT.md)

---

**Conclusión:** primero comparar dos enlaces punto a punto sin switch; después ejecutar el mismo benchmark RPC con ambos. Para conversaciones largas, medir caché de prefijo y política de sesión por separado. El acceso directo a memoria/RDMA queda como investigación futura y no se atribuye al cable USB ni al RPC convencional.
