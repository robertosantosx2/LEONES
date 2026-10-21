# AMD BC-250: Características técnicas, inferencia LLM y clusters de IA locales

**Ficha de prospección / investigación** — LEONES · Fuentes de conocimiento  
Fecha de captura: 2026-10-21  
Estado: ESTIMATED + evidencia comunitaria (no medición LEONES propia)

---

## Resumen ejecutivo

La **AMD BC-250** es una placa de minería excedentaria basada en un APU semi-custom de la familia PS5 (“Oberon” / “Cyan Skillfish”, gfx1013). Combina CPU Zen 2 + GPU RDNA 2 con **16 GB GDDR6 unificada**. La comunidad la ha convertido en una plataforma barata y viable para **inferencia local de LLMs** (Vulkan + llama.cpp / Ollama) y **clusters** mediante RPC de llama.cpp.

Es especialmente atractiva por el ratio precio / memoria / ancho de banda y por la madurez de los unlocks comunitarios (8 núcleos CPU + hasta 40 CUs GPU).

---

## Características técnicas

| Componente | Especificación |
|------------|----------------|
| **CPU** | Zen 2 (“Oberon”), 6c/12t de fábrica (~3,5 GHz). Desbloqueable a 8c/16t (hasta ~3,9-4,0 GHz) |
| **GPU** | RDNA 2 / “RDNA 1.5” (gfx1013 / Cyan Skillfish). 24 CUs de fábrica; hasta 40 CUs desbloqueables |
| **Memoria** | 16 GB GDDR6 UMA, bus 256-bit, ~14 Gbps → ~448 GB/s teóricos (medidos ~350-410 GB/s) |
| **Almacenamiento** | 1× M.2 2280 (PCIe 2.0 ×2 o SATA III, ~1 GB/s máx.) |
| **I/O** | 1× DisplayPort 1.4, 2× USB 3.0, 2× USB 2.0, 1× GbE |
| **Alimentación** | 1× PCIe 8-pin (12 V). TDP ~220 W; real 50-85 W idle, 160-235 W carga |
| **Formato** | Placa de minería personalizada (~310-340 × 115 mm) |
| **OS** | Linux (Mesa/RADV Vulkan). Windows sin drivers GPU oficiales |

**Notas importantes**:
- FPU recortada (similar a PS5) → ~15 % menos rendimiento en cargas AVX2 pesadas.
- VCN (video encode/decode) bloqueado.
- Requiere refrigeración activa y buena PSU en el rail de 12 V (≥300 W recomendado).
- Kernel y TTM (`ttm.pages_limit`) deben ajustarse para aprovechar los 16 GB unificados.

---

## Inferencia de LLMs

**Backend principal**: Vulkan (llama.cpp + Mesa/RADV). ROCm/HIP experimental.

**Rendimientos típicos comunitarios** (llama.cpp Vulkan, quant Q4/IQ2-IQ4, 24-40 CUs):

- 7-9B densos: ~50-80+ tok/s
- 14B densos: ~20-35 tok/s
- MoE Qwen3.x 30-35B-A3B (~3B activos): **55-80+ tok/s**
- GPT-OSS 20B / similares: 45-87 tok/s
- Híbridos Mamba (Granite 4.0-H Tiny): 100-130 tok/s
- Densos 27-32B: 10-20 tok/s
- Contexto largo: muchos modelos llegan a 64K-100K+

El unlock a 40 CUs aporta ~1,3× en generación y ~1,5× en prefill de media.

**Motores recomendados**:
- llama.cpp (Vulkan) — principal
- Ollama (capa fácil sobre Vulkan)
- llmtune (control de flotas y perfiles por arquitectura)
- forks optimizados para gfx1013
- stable-diffusion.cpp para imagen

**Modelos ideales**: MoE de pocos parámetros activos (Qwen 3.x A3B), 7-14B densos de calidad, híbridos Mamba para contexto largo.

---

## Clusters de IA

Viable y económico. Cada placa es un nodo completo (CPU + GPU + 16 GB).

- Método: **llama.cpp RPC** (layer / model parallelism) sobre Ethernet (1 GbE de serie; se recomienda 2,5 GbE).
- Ejemplos comunitarios:
  - 2 placas → Qwen3.6-35B-A3B Q4 ~60 tok/s @ 64K
  - 4 placas (~500 USD) → Next Flash IQ3_XXS ~60-70 tok/s @ 100K; o 2 instancias 35B-A3B ~145 tok/s
  - 6 placas → combinaciones Flash + 35B
- Herramientas: **llmtune** (netboot PXE, control de modelos, clustering).

Limitaciones: latencia de red, generación no escala linealmente, gestión de calor y potencia.

---

## Enlaces a repositorios, documentación y hilos relevantes

### Documentación y guías principales
- [AMD BC250 Documentation (elektricM)](https://elektricm.github.io/amd-bc250-docs/) — documentación canónica comunitaria
- [SkillFishOS – Hardware BC-250](https://skillfishos.com/en/docs/hardware-bc250/)
- [akandr/bc250](https://github.com/akandr/bc250) — guía completa Ollama + Vulkan + benchmarks + Signal bot
- [oldrigrevive – Guía AMD BC-250](https://oldrigrevive.com/guides/amd-bc-250/) (también [versión ES](https://oldrigrevive.com/es/tutoriales/tarjeta-amd-bc-250/))
- [katzzero/bc250-unofficial-community-guide](https://github.com/katzzero/bc250-unofficial-community-guide)
- [mothenjoyer69/bc250-documentation](https://github.com/mothenjoyer69/bc250-documentation)
- [bc-250.com Wiki – AI Inference](https://bc-250.com/wiki?article=linux%2F12-ai-inference)

### Unlocks y herramientas de hardware
- [bc250-40cu-unlock](https://github.com/duggasco/bc250-40cu-unlock) (y variantes comunitarias)
- cyan-skillfish-governor (SMU)
- bc250_memcfg (ajuste de split UMA)

### Inferencia y clustering
- [cachenetics/llmtune](https://github.com/cachenetics/llmtune) — motor de inferencia + control plane de flotas para BC-250
- [TechMakesArt/llama.cpp-bc250](https://github.com/TechMakesArt/llama.cpp-bc250) — fork con optimizaciones Vulkan gfx1013
- [TobiaszJ/qw6](https://github.com/TobiaszJ/qw6) — motor nativo para Qwen 3.6-35B-A3B en BC-250
- [akandr/bc250-rocm](https://github.com/akandr/bc250-rocm) — investigación ROCm/HIP vs Vulkan

### Artículos y reseñas
- [Tom’s Hardware – Benchmarking AMD’s BC-250](https://www.tomshardware.com/pc-components/cpus/benchmarking-amds-bc-250-offering-steam-machine-like-performance-at-half-the-price-unlocking-40-cus-eight-zen-2-cores-on-the-repurposed-ps5-apu)
- [Hackaday – Re-Enable All Compute Units](https://hackaday.com/2026/06/09/re-enable-all-compute-units-on-the-ps5-like-bc-250-cryptomining-card/)
- [Aftermath – Bless The BC250](https://aftermath.site/bc250-steam-machine-budget-computer/)
- [VideoCardz – 40 CU unlock](https://videocardz.com/newz/amd-bc-250-ps5-apu-unlock-exposes-all-40-gpu-cus-for-budget-steam-machine-alternative)

### Hilos de comunidad (Reddit / LocalLLaMA)
- [Running Next Flash IQ3_XXS at ~70 tok/s… 4× BC-250](https://www.reddit.com/r/LocalLLaMA/comments/1x2yv1b/running_next_flash_iq3_xxs_at_70_toks_with_100k/)
- [Two BC-250 running Qwen3.6-35B-A3B at 60 tok/s](https://www.reddit.com/r/LocalLLaMA/comments/1wou3gr/my_foray_into_local_ai_two_bc250_ex_mining_apus/)
- [Update on the “Monstrosity” – 6 BC-250 cluster](https://www.reddit.com/r/LocalLLaMA/comments/1wviphh/update_on_the_monstrosity_6_bc250_board_cluster/)
- [r/BC250Gaming](https://www.reddit.com/r/BC250Gaming/)

### X / Twitter (actividad reciente)
Búsquedas útiles: `BC-250 (LLM OR llama.cpp OR Ollama OR cluster OR tok/s)`. Hay posts de clusters de 4-6 placas, comparaciones con P100 y anuncios de AliExpress.

### Otras referencias
- [llama.cpp Vulkan performance discussion](https://github.com/ggml-org/llama.cpp/discussions/10879) (incluye entradas BC-250)
- BIOS community: [gitlab.com/TuxThePenguin0/bc250-bios](https://gitlab.com/TuxThePenguin0/bc250-bios/)

---

## Relevancia para LEONES

- **Hardware de bajo coste** con 16 GB UMA de alto ancho de banda → candidato interesante para perfiles “memory-constrained / bandwidth-friendly” en LLMFit y matrices de hardware.
- Excelente para **MoE de pocos parámetros activos** y modelos híbridos.
- Permite clusters baratos → posible entrada en prospección de “flotas de nodos económicos”.
- Stack actual maduro en Vulkan; ROCm aún experimental → clasificar como runtime Vulkan-first.

**Clasificación LEONES**:
- Tipo: fuente de conocimiento / prospección de hardware
- Nivel de evidencia: comunitaria (benchmarks públicos + repos) — **no** medición física LEONES propia
- Acción sugerida: valorar inclusión en matriz de hardware y en candidatos de runtime locales 2026

---

*Documento generado a partir de investigación web + repositorios comunitarios (2026-10-21). Actualizar cuando aparezcan nuevas mediciones o cambios de driver/Mesa.*


---

## Ampliación: red, almacenamiento, PCIe y diseños de cluster (2026-10-21)

### Referencias adicionales

- [wdonega/bc250-llm-setup](https://github.com/wdonega/bc250-llm-setup): guía reproducible para Ubuntu, Vulkan/RADV, TTM/GTT, servicios systemd y pruebas de dos nodos.
- [4claps/bc250-llama-cluster](https://github.com/4claps/bc250-llama-cluster): despliegue Ansible sobre Fedora, coordinador y worker RPC.
- [Resumen de topología 4claps](https://github.com/4claps/bc250-llama-cluster/blob/main/docs/TLDR.md): red backend, prerequisitos y parámetros validados.
- [Guía comunitaria no oficial](https://github.com/katzzero/bc250-unofficial-community-guide): montaje, refrigeración y almacenamiento.
- [BC-250 and the search for Cheap Compute](https://www.reddit.com/r/LocalLLaMA/comments/1tj4unp/amd_bc250_and_the_search_for_cheap_compute/): experiencia comunitaria sobre CU unlock, rendimiento y consumo.
- [Experiencia con cluster llama.cpp](https://www.reddit.com/r/BC250Gaming/comments/1w2qtp4/llamacpp_cluster_for_local_ai/): dos nodos, PSU compartida y NIC USB 2.5GbE.
- [llama.cpp upstream](https://github.com/ggml-org/llama.cpp): revisar versiones y cambios antes de reproducir benchmarks.

### Red: opciones y arquitectura recomendada

Separar la red en dos planos: (1) gestión: SSH, Ansible, actualizaciones y API; (2) backend privado: tráfico RPC entre nodos. La Ethernet integrada de 1 Gb/s es suficiente para administración, pero para el enlace de inferencia conviene probar 2.5 GbE dedicado.

| Opción | Uso | Consideraciones |
|---|---|---|
| GbE integrado | Gestión y API | Sin coste adicional; no mezclarlo necesariamente con RPC |
| USB 3.x a 2.5GbE | Backend dedicado | Confirmar chipset Linux, velocidad negociada y estabilidad bajo carga |
| Enlace directo 2.5GbE | Dos nodos | Barato, sin switch; IP estática y sin gateway |
| Switch 2.5GbE | 2–8 nodos | Fácil de ampliar; VLAN y firewall bien definidos |
| 10GbE SFP+ / RJ45 | Uplink o experimentación | Más coste, consumo y calor; no garantiza más tok/s si la red no es el cuello de botella |
| Wi-Fi | Gestión auxiliar | No recomendado para RPC por jitter y variabilidad |
| NAS/NFS | Catálogo compartido y distribución | Para benchmarks, copiar el modelo al SSD local y no medir accidentalmente el NAS |

Topología de referencia comunitaria para dos nodos: coordinador 10.250.0.1/30, worker 10.250.0.2/30, RPC en worker:50052. Es solo un ejemplo; adaptar a la red real. El backend no debería tener gateway ni DNS. RPC no debe exponerse a Internet ni a una LAN no confiable: es una interfaz privilegiada y no debe considerarse autenticada.

Comprobaciones Linux:

```bash
ip -br link
ip -br addr
ip route
sudo ethtool <INTERFAZ>
ip -s link show <INTERFAZ>
iperf3 -s                 # servidor
iperf3 -c <IP_SERVIDOR> -P 4
```

Medir velocidad negociada, errores, drops y throughput antes y durante inferencia. Para un despliegue seguro, permitir RPC solo desde la IP del coordinador mediante firewall y enlazar el servicio a la interfaz backend.

### SSD y opciones PCIe

La BC-250 no es una placa ATX con varias ranuras PCIe estándar. La opción documentada es un M.2 2280, descrito según revisión como PCIe 2.0 ×2 o SATA III. El enlace limita el rendimiento de un NVMe moderno; el SSD más rápido no suele aumentar los tok/s una vez cargados los pesos, pero sí reduce tiempos de instalación, carga y cambio de modelo.

- **NVMe M.2 2280 PCIe**: opción preferente si la revisión de placa negocia PCIe. Un SSD Gen3/Gen4 normalmente negocia a la velocidad máxima que permita la placa; no pagar una prima por cifras Gen4/Gen5 que no se pueden aprovechar.
- **M.2 SATA 2280**: comprarlo solo tras confirmar que esa ranura/revisión soporta SATA. Un módulo SATA no funciona en una ranura exclusivamente PCIe.
- **SSD SATA o NVMe por USB 3.x**: opción práctica para pesos, copias y traslado de modelos; el puente USB y el puerto son el límite.
- **NAS/NFS**: útil para mantener una biblioteca compartida; copiar localmente los modelos antes de benchmark.
- **PXE/netboot**: alternativa avanzada para flotas uniformes, con modelos y cachés mantenidos localmente.
- **USB flash**: reservar para instalación/rescate, no para inferencia sostenida de modelos grandes.

Sobre un SSD “por PCIe”: no asumir que hay un slot x4/x16 libre. Un adaptador M.2-a-PCIe puede servir como experimento si firmware, alimentación y espacio lo permiten, pero seguirá limitado por las lanes disponibles (PCIe 2.0 ×2 en la configuración descrita). Puede fallar el arranque o la enumeración y no es la recomendación para un nodo fiable. Un adaptador con varias ranuras no crea lanes ni ancho de banda adicionales. Verificar revisión, protocolo M.2, longitud 2280, alimentación y espacio antes de comprar.

### Ideas de topología para LEONES

1. **Coordinador + worker**: un nodo ejecuta llama-server y su GPU; el segundo ofrece ggml-rpc-server. Los clientes solo conocen la API del coordinador.
2. **Tres planos de red**: gestión por GbE integrado, RPC por USB 2.5GbE dedicado y catálogo de modelos por NAS/VLAN independiente.
3. **Pool de instancias independientes**: cada BC-250 sirve su propio modelo y un router distribuye peticiones. Puede aumentar throughput agregado, pero no suma la memoria UMA de varios nodos para una sola inferencia.
4. **Cluster modular de 4–6 nodos**: switch 2.5GbE y uplink 10GbE; añadir nodos solo tras medir latencia, potencia, temperatura y rendimiento.
5. **Arquitectura híbrida**: BC-250 para MoE de pocos parámetros activos o modelos pequeños; host x86 con más RAM para coordinación, embeddings, reranking y modelos que no caben.
6. **Nodo de distribución**: equipo de gestión descarga modelos, verifica hashes y los replica; los nodos de inferencia no necesitan acceso general a Internet.
7. **Degradación controlada**: mantener un modelo pequeño local en el coordinador si falla un worker; no anunciar el modelo distribuido como disponible cuando falta un nodo.
8. **Banco de pruebas de red**: comparar enlace directo, switch 2.5GbE y uplink 10GbE manteniendo constantes modelo, cuantización, contexto, versión, prompt y split.
9. **Operación eficiente**: medir vatios en pared por nodo y por token útil; automatizar parada segura si falla la ventilación o aparecen errores de cálculo.
10. **Edge fleet**: inventario por MAC permanente, imágenes reproducibles, perfiles conservadores, actualización canary de un nodo y despliegue por lotes.

### Compilación orientativa de llama.cpp con Vulkan y RPC

La guía Ubuntu enlazada propone este punto de partida; confirmar los requisitos del upstream y el entorno Mesa antes de usarlo:

```bash
sudo apt install -y build-essential cmake git libcurl4-openssl-dev \
  glslc libvulkan-dev spirv-headers spirv-tools
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
cmake -B build -DGGML_VULKAN=ON -DGGML_RPC=ON
cmake --build build --config Release -j"$(nproc)"
```

Confirmar que vulkaninfo detecta RADV y no llvmpipe. Guardar commit de llama.cpp, kernel, Mesa, parámetros TTM, temperatura, cuantización, contexto y KV cache en cada resultado. Las instrucciones de Ubuntu y Fedora no deben mezclarse sin revisar paquetes, firewall, servicios y rutas.

### Criterios de seguridad y evidencia

- Calificar cada placa individualmente antes de desbloquear CUs o alterar BIOS, frecuencias, tensión o refrigeración. No copiar tablas de routing de CUs de otra unidad.
- Validar refrigeración sostenida, sensores y ventiladores antes de habilitar servicios automáticos.
- Si la API del coordinador no usa autenticación, restringirla a la LAN confiable o situar un proxy autenticado delante.
- Registrar potencia en pared, temperaturas, frecuencia, RAM libre, GTT, errores Vulkan, contexto, KV cache, prefill y generación.
- Para comparativas, fijar prompt, tokens de entrada/salida, contexto, cuantización, versión y parámetros del runtime; informar latencia p50/p95 además de tok/s.
- Las cifras comunitarias son evidencia de terceros, no mediciones físicas de LEONES ni garantías de que otra placa obtenga lo mismo.

---

## Ampliación avanzada: optimización Vulkan, ROCm/HIP y RPC multinodo

Esta sección integra el contenido proporcionado como documento complementario. Las variables y comandos son **opciones experimentales**, no ajustes universales: deben validarse con la versión de Mesa, kernel, firmware y llama.cpp instalada.

### Arquitectura y gestión de energía

- **APU**: Cyan Skillfish, gfx1013; familia relacionada con el silicio de PS5. La BC-250 combina CPU Zen 2 y GPU con memoria GDDR6 unificada.
- **Memoria**: 16 GB compartidos por CPU y GPU. La memoria reservada y la disponible para Vulkan no son necesariamente iguales; driver, buffers, kernel y TTM consumen recursos.
- **Energía y refrigeración**: estas placas pueden mantener un consumo base significativo y no comportarse como un PC convencional en reposo. Dimensionar PSU, rail de 12 V y refrigeración para carga continua; medir consumo en pared.
- Los datos de núcleos, CUs, clocks, consumo y desbloqueos varían según revisión y modificaciones de firmware. Verificar la unidad física antes de aplicar perfiles.

### llama.cpp con Vulkan: variables experimentales

Vulkan sobre Mesa/RADV es la ruta de referencia comunitaria para gfx1013. La compatibilidad exacta depende de Mesa y del build de llama.cpp.

~~~bash
# Probar solo si se observan límites de asignación Vulkan en modelos/contextos grandes:
export GGML_VK_FORCE_MAX_ALLOCATION_SIZE=2000000000

# Mitigación experimental de artefactos gráficos con RADV:
export RADV_DEBUG=nohiz

# Alternativa histórica para diagnosticar problemas de compute en versiones antiguas:
# export RADV_DEBUG=nocompute
~~~

**No aplicar todas las variables a ciegas.** Ejecutar primero sin overrides, cambiar una sola variable cada vez y comparar logs, estabilidad, rendimiento y resultados. Las opciones de RADV pueden variar entre versiones. GGML_VK_FORCE_MAX_ALLOCATION_SIZE no aumenta la memoria física: su efecto depende de la versión del backend Vulkan.

### Split de memoria UMA / firmware

El firmware puede ofrecer opciones para dividir o reservar memoria entre CPU y GPU. Una reserva como 12 GB para GPU y 4 GB para sistema es solo un **perfil candidato de prueba**, no una recomendación universal: puede dejar memoria insuficiente para el sistema, servicios o buffers del driver.

1. Anotar la configuración original y preparar recuperación antes de cambiar firmware.
2. Probar un split conservador y verificar memoria visible por el sistema y Vulkan.
3. Medir un modelo representativo, incluyendo contexto y KV cache.
4. Cambiar una sola variable y conservar el perfil estable.
5. Documentar que Vulkan puede reportar menos memoria efectiva que la reservada en firmware.

### ROCm/HIP: ruta alternativa y experimental

ROCm/HIP no debe considerarse equivalente en madurez a Vulkan para esta APU. Puede interesar para cargas específicas y experimentos con rocBLAS, pero requiere builds, kernels y parches compatibles con gfx1013.

~~~bash
# Override experimental citado por proyectos comunitarios; no es universal:
export HSA_OVERRIDE_GFX_VERSION=10.1.0
~~~

Referencias:
- [akandr/bc250-rocm](https://github.com/akandr/bc250-rocm)
- [GabriWar/bc250-rocm-working](https://github.com/GabriWar/bc250-rocm-working)

El override no convierte automáticamente una GPU no soportada en una plataforma oficialmente soportada. Validar detección de dispositivo, kernels, exactitud, estabilidad y rendimiento. Mantener Vulkan como configuración de referencia.

### RPC de llama.cpp: workers y coordinador

RPC permite que un coordinador use recursos de otros equipos, pero no crea memoria físicamente unificada ni garantiza escalado lineal. El reparto depende de la versión, modelo, cuantización, split de capas/tensores y red.

**Worker** — escuchar solo en la interfaz backend privada:

~~~bash
./rpc-server -H <IP_BACKEND_DEL_WORKER> -p 50052
~~~

**Coordinador** — comprobar primero las opciones admitidas por la versión instalada:

~~~bash
./llama-server --help
# Consultar la sintaxis exacta de --rpc y los parámetros de offload
# antes de lanzar el servidor.
~~~

Direcciones ilustrativas: workers 192.168.1.51:50052 y 192.168.1.52:50052. No copiar estas direcciones si no corresponden a la red real. Las opciones de CLI cambian entre versiones y forks; consultar --help y el commit utilizado.

**Seguridad:** evitar escuchar en 0.0.0.0 en equipos con interfaces públicas o LAN no confiable. Limitar el puerto RPC al coordinador mediante firewall y no publicarlo en Internet.

### Red para inferencia distribuida

- Priorizar Ethernet cableada dedicada para RPC.
- Preferir NIC nativas compatibles cuando existan; USB 2.5GbE es una alternativa económica, pero medir latencia, uso de CPU y estabilidad.
- Separar gestión, API y RPC si es posible.
- Medir throughput con iperf3, latencia y pérdida antes y durante la inferencia.
- Comparar 1 GbE, 2.5 GbE y 10 GbE sin asumir que la red sea el cuello de botella.

### Repositorios de soporte incorporados

- [akandr/bc250](https://github.com/akandr/bc250) — instalación base, Ollama/Vulkan y pruebas.
- [elektricm/amd-bc250-docs](https://elektricm.github.io/amd-bc250-docs/) — documentación comunitaria de hardware y software.
- [GabriWar/bc250-rocm-working](https://github.com/GabriWar/bc250-rocm-working) — investigación de ROCm y cargas relacionadas con Stable Diffusion.
- [llama.cpp upstream](https://github.com/ggml-org/llama.cpp) — opciones actuales de CLI, Vulkan y RPC.

### Plan de validación LEONES

Registrar por ejecución:
- Identificador/revisión de placa y configuración de firmware/UMA.
- Kernel, Mesa/RADV, runtime, commit y flags de compilación.
- Variables de entorno activas, backend y red.
- Modelo, hash, cuantización, contexto, KV cache y offload.
- Prefill tok/s, generación tok/s, latencia, RAM/GTT, temperaturas, clocks, consumo en pared y errores.
- En pruebas distribuidas: número de workers, latencia/throughput de red, capas asignadas y comportamiento al desconectar un worker.

Clasificar cada resultado como **medición LEONES**, **reproducción comunitaria** o **hipótesis por validar**. No presentar variables, split de memoria ni resultados de terceros como hechos comprobados en una unidad LEONES hasta reproducirlos.
