# Hardware ARM con memoria unificada para inferencia local de IA
## Investigación técnica y plan de validación LEONES — 24 de octubre de 2026

**Estado:** investigación documental; las mediciones de hardware que no se hayan ejecutado físicamente se marcan como *publicadas por terceros*, nunca como MEASURED por LEONES.  
**Rama:** `research/arm-unified-memory-ai-2026-10`  
**Objetivo:** identificar hardware comprable y viable para inferencia local, priorizando Radxa Orion O6 de 64 GB y NVIDIA Jetson AGX Orin, con especial atención a Strata, GGUF, caché KV, descarga de expertos, drivers, PCIe, consumo y coste total.

## Resumen ejecutivo

1. **Radxa Orion O6 64 GB** es la opción de investigación abierta con mejor combinación de RAM unificada, expansión PCIe y precio de referencia. Tiene CPU CIX P1 ARMv9, GPU Arm Immortals G720 MC10, NPU anunciada de 30 TOPS, 64 GB LPDDR5 y PCIe Gen4 x8 físico. El precio de venta recomendado publicado en la presentación oficial fue 539 USD para la variante de 64 GB; no se ha confirmado una oferta final entregada en España con IVA, transporte y aduanas incluidos.
2. **Jetson AGX Orin 32 GB** es la ruta más sólida para validar motores CUDA ARM64 y gestión de memoria compartida. El fork `calvinvette/strata-inference-orin` publica pruebas reales en AGX Orin de 32 GB con JetPack 6.2/CUDA 12.6 y modelo GGUF MoE. Es evidencia más útil que una tabla TOPS comercial.
3. **Jetson AGX Orin Developer Kit 64 GB** tiene precio oficial anunciado de 3.499 USD; un distribuidor europeo puede cobrar bastante más. El kit de desarrollo de 64 GB conserva el rendimiento del kit original de 32 GB, según NVIDIA; no debe confundirse con las especificaciones del módulo de producción de 64 GB.
4. **No hay aún una comparación controlada Radxa O6 vs Jetson Orin** con el mismo modelo, cuantización, contexto, número de tokens, versiones de software y medición de pared. No se asignan tokens/s ni tokens/J a Radxa sin datos verificables.
5. Para LEONES, separar tres estados: **PUBLISHED** (terceros, con fuente), **ESTIMATED** (cálculo o estimación identificada) y **MEASURED** (ejecución física controlada, con logs y comandos). Las cifras publicadas no deben convertirse en resultados propios.

## 1. Plataformas evaluadas

### 1.1 Radxa Orion O6 (CIX P1)

Fuentes oficiales:
- Producto y vías de compra: https://radxa.com/products/orion/o6/
- Documentación: https://docs.radxa.com/en/orion/o6
- Especificación de bajo nivel: https://docs.radxa.com/en/orion/o6/low-level-dev
- PDF con precio minorista oficial publicado: https://dl.radxa.com/orion/o6/radxa_orion_o6_announcement_presentation_2024_12_18.pdf
- Proyecto comunitario de kernel CIX P1 (O6N, relacionado pero no idéntico en validación): https://github.com/AkaseToshiyuki/cix-p1-kernel-deploy

Especificaciones confirmadas por Radxa:
- SoC CIX P1, arquitectura ARMv9.2.
- CPU de 12 núcleos: 4 Cortex-A720 de rendimiento (hasta 2,6 GHz), 4 Cortex-A720 balanceados (hasta 2,4 GHz) y 4 Cortex-A520 eficientes (hasta 1,8 GHz).
- GPU Arm Immortals G720 MC10; documentación declara Vulkan 1.3 y OpenCL 2.2.
- NPU anunciada como 30 TOPS; la página de producto promociona 45 TOPS combinados CPU/GPU/NPU. Estas cifras no son benchmarks de LLM y no demuestran que la NPU pueda ejecutar un modelo GGUF.
- RAM LPDDR5, bus de 128 bits, 5500 MT/s, hasta 64 GB; ancho de banda declarado de hasta 100 GB/s.
- Ranura PCIe x16 física con conexión PCIe Gen4 x8. No implica x16 eléctrico.
- Ranura M.2 M-key PCIe Gen4 x4 para NVMe; M.2 E-key PCIe Gen4 x2.
- Dos interfaces Ethernet de 5 GbE.
- Alimentación: entrada USB-C PD de 20 V o conector ATX de 24 pines; PSU recomendada de al menos 65 W.
- La documentación indica que el paquete suele incluir placa, disipador Radxa 8420B, caja acrílica y shield de E/S; verificar el contenido del vendedor.

**Precio de referencia, no precio final de compra:** PDF oficial publicado: 8 GB 289 USD, 16 GB 329 USD, 32 GB 389 USD, 64 GB 539 USD. Es un precio minorista oficial anunciado en 2024, no una oferta actual con stock y envío confirmados. Página oficial: https://radxa.com/products/orion/o6/ (disponibilidad mediante socios autorizados). Antes de comprar, solicitar precio final en EUR con IVA español, transporte, garantía y plazo de entrega por escrito.

#### Valor real para LLM

La ventaja de O6 es tener 64 GB de RAM física compartida para CPU/GPU, con una GPU moderna y PCIe para expansión. Es una candidata para ejecutar modelos grandes cuantizados principalmente por CPU, probar backends Vulkan y experimentar con una GPU PCIe ARM-compatible.

Riesgos y límites:
- El controlador gráfico y el soporte del SoC son más jóvenes y menos estandarizados que CUDA en Jetson.
- El soporte Vulkan/OpenCL de la GPU no demuestra por sí solo que la versión de llama.cpp que se compile detecte correctamente la GPU, que todas las operaciones estén implementadas o que el backend sea más rápido que CPU.
- La NPU de 30 TOPS es un acelerador separado con SDK, operadores y formatos propios. No se debe dar por hecho que acepta GGUF ni que llama.cpp/Strata la utilicen.
- Los TOPS son irrelevantes como predictor directo de tokens/s para un modelo MoE si el runtime no puede ejecutar sus operaciones en ese acelerador.
- **Baseline oficial de llama.cpp en CPU publicado por Radxa:** DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf, 8 hilos, pp512 = 64,60 ± 0,27 tokens/s y tg128 = 36,29 ± 0,16 tokens/s. La guía fija el commit `4aced7a` y activa ARMv9/I8MM/dotprod/KleidiAI. Esto verifica una ruta GGUF/CPU para O6; no demuestra aceleración Vulkan ni rendimiento de MoE grande. Fuente primaria: https://docs.radxa.com/en/orion/o6/app-development/artificial-intelligence/llama-cpp
- No se ha encontrado en esta revisión un benchmark público suficientemente reproducible de O6 con un MoE de 30–35B en GGUF, con logs completos de tokens/s, RAM máxima y consumo de pared. Resultado: **no verificado**.

### 1.2 NVIDIA Jetson AGX Orin 32 GB / 64 GB

Fuentes:
- Página oficial Jetson Orin: https://www.nvidia.com/es-es/autonomous-machines/embedded-systems/jetson-orin/
- FAQ/precios de NVIDIA: https://developer.nvidia.com/embedded/faq
- Fork Strata para Orin: https://github.com/calvinvette/strata-inference-orin
- Benchmarks comunitarios del fork: https://github.com/calvinvette/strata-inference-orin/blob/main/docs/COMMUNITY_BENCHMARKS.md

Características relevantes:
- AGX Orin utiliza CPU ARM Cortex-A78AE y GPU NVIDIA Ampere integrada con memoria LPDDR5 compartida.
- Según SKU, NVIDIA publica hasta 64 GB de memoria y hasta 204,8 GB/s de ancho de banda para AGX Orin de 64 GB.
- El módulo de producción AGX Orin 64 GB se anuncia con hasta 275 TOPS y rango configurable de potencia 15–60 W; no confundir ese dato de módulo con el kit de desarrollo ni con consumo de pared de todo el sistema.
- NVIDIA indica un precio de 3.499 USD para el Jetson AGX Orin Developer Kit de 64 GB y especifica que su rendimiento es el mismo que el kit de desarrollo original de 32 GB, salvo la memoria.
- Los módulos de producción se venden aparte y requieren carrier board, fuente, refrigeración y almacenamiento apropiados. Para un primer experimento es preferible un kit completo o un sistema integrado que incluya esos componentes.

**Coste total:** el precio oficial de 3.499 USD no es coste entregado en España. Añadir IVA/importación si proceden, transporte, NVMe, alimentación/cableado y posible carcasa/refrigeración. Un resultado de shopping reciente mostró un listado europeo del kit a unos 4.800 EUR, pero no se considera una oferta auditada ni necesariamente comparable; comprobar stock, SKU, IVA, envío y devolución antes de decidir. Fuente oficial para MSRP: https://developer.nvidia.com/embedded/faq

### 1.3 Alternativas de más memoria

| Plataforma | RAM física compartida | Estado para esta investigación | Uso recomendado |
|---|---:|---|---|
| Radxa Orion O6 | Hasta 64 GB LPDDR5 | Especificaciones oficiales; benchmark LLM grande comparable no encontrado | Opción abierta para evaluar CPU/Vulkan y PCIe |
| Jetson AGX Orin | 32/64 GB según kit/módulo | Hay fork ARM64/CUDA con mediciones reales de 32 GB | Referencia para motor especializado y offload |
| Jetson Orin NX | 8/16 GB según SKU | CUDA maduro, memoria demasiado pequeña para varios MoE de 30B sin descarga agresiva | Modelos pequeños, visión y nodo de control |
| AMD BC-250 | 16 GB GDDR6 | Proyecto comunitario y Vulkan; arquitectura APU no ARM | Referencia económica alternativa, no objetivo ARM |
| Apple Silicon | Configuración dependiente del equipo | Memoria unificada madura, plataforma cerrada | Referencia de experiencia de usuario y rendimiento, no hardware abierto |

## 2. Evidencia reproducible: Strata en Jetson AGX Orin

Repositorio: https://github.com/calvinvette/strata-inference-orin  
Rama del port descrita por el proyecto: `feat/jetson-orin-arm64`.

El fork deriva de Strata y añade:
- compilación ARM64 para SM87;
- kernels CPU portables y backend ARM de ggml fijado;
- presupuesto unificado de RAM física para asignaciones CPU/GPU;
- expertos respaldados por ficheros cuando no caben en RAM;
- sincronización ARM para buffers host mapeados en CUDA y alternativas de registro;
- ajustes de caché VMM;
- instalación que conserva las bibliotecas CUDA de JetPack, evitando binarios x86 o paquetes CUDA de escritorio incompatibles.

Advertencia importante: el propio proyecto indica que CPU y GPU comparten los 32 GB del AGX Orin de prueba; no son 32 GB de RAM más otros 32 GB de VRAM. El runtime deja por defecto aproximadamente 6 GiB de margen físico y reserva otros 3 GiB para espacios de trabajo tardíos al calcular la caché automática de expertos. La memoria gestionada se admite para transferencia secuencial de propiedad, pero no se reporta acceso gestionado concurrente. El proyecto mantiene asignaciones de dispositivo y buffers de control mapeados en vez de reemplazar todo por managed memory.

### Resultados publicados por el fork (no medidos por LEONES)

Configuración documentada:
- Hardware: Jetson AGX Orin 32 GB.
- Sistema: JetPack 6.2, CUDA 12.6.68.
- Modo de potencia: MAXN y relojes desbloqueados.
- Modelo: Qwen3.8-Flash-Next Coder IQ1_M, expertos respaldados por archivos, MTP speculative de 4, prefill batch 64.
- Build inicial descrito como Strata 0.1.40.3; el repo también documenta validación posterior tras rebase a 0.1.41.

Resultados del build 0.1.40.3:
- Decode: mediana de 18,6–21,6 tokens/s en tres ejecuciones por tamaño de prompt con respuestas de 64 tokens.
- Prefill: mediana de 37,8–52,5 tokens/s para prompts de 172–1069 tokens.
- Contexto largo: 31.234 tokens procesados en 584 segundos en una prueba con contexto de 32K; respuesta esperada y seguimiento superados.
- RAM física disponible mínima reportada: 7,33 GiB; había swap en uso.
- Validación API: respuestas greedy repetidas, streaming OpenAI/Anthropic y recuperación tras cancelación superados.
- Visión: validación de encoder CPU/CUDA para una imagen de 56×56 y límite de encoder de 16 tokens.

Validación posterior del rebase a 0.1.41:
- Nueve capacidades de contexto desde 1K hasta 256K completadas.
- Con contexto 262.144, prompt de 261.936 tokens procesado a 58,5 tokens/s; luego 64 tokens generados a 6,6 tokens/s.
- RAM disponible mínima: 9,33 GiB; swap en uso.
- El contexto más grande reduce la caché automática de expertos y la velocidad de decode.

Interpretación:
- Es evidencia relevante de que un MoE con cuantización agresiva puede ejecutarse en Jetson Orin compartiendo RAM con la GPU y usando offload de expertos a fichero.
- No es prueba de que cualquier modelo de 30–35B funcione igual, ni de que la velocidad sea sostenible con refrigeración pasiva o a potencia limitada.
- El modelo Coder tiene expertos eliminados respecto al modelo completo; no equivale al modelo íntegro para tareas generales.
- Las pruebas de rendimiento no sustituyen a una validación independiente de calidad, seguridad y precisión numérica.
- Las cifras publicadas deben permanecer etiquetadas **PUBLISHED / THIRD-PARTY** en LEONES.

### Instalación indicada por el proyecto

Requisitos: AGX Orin 32 GB, JetPack 6.2, CUDA 12.6 y NVMe con espacio suficiente.

```bash
git clone --branch feat/jetson-orin-arm64 https://github.com/calvinvette/strata-inference-orin.git
cd strata-inference-orin
./setup.sh --cuda 12
```

Seguir el README y `docs/AI_SETUP.md` del repositorio en la revisión exacta que se vaya a medir. No exponer el servidor fuera de localhost sin configurar API key. Para reproducibilidad, guardar SHA de commit, versión de JetPack, modelo GGUF y hashes de los artefactos.

## 3. Controladores y backends: matriz de compatibilidad

| Plataforma / backend | Estado documental | Qué queda por verificar |
|---|---|---|
| Jetson Orin + CUDA + Strata ARM64 | Evidencia publicada en AGX Orin 32 GB | Repetición independiente, potencia limitada, modelos completos y métricas de pared |
| Jetson Orin + llama.cpp CUDA + GGUF | Vía de software ampliamente disponible en ARM64/CUDA, pero el rendimiento depende de build y modelo | Compilar versión fijada, confirmar capas GPU, KV cache, MoE y memoria |
| Orion O6 + llama.cpp CPU | ARM64 CPU como punto de partida razonable | Build limpio, kernels ARM, BLAS opcional y estabilidad |
| Orion O6 + llama.cpp Vulkan | GPU anuncia Vulkan 1.3; compatibilidad del runtime no se deduce de la especificación | `vulkaninfo`, backend Vulkan compilado, operaciones soportadas y benchmark contra CPU |
| Orion O6 + OpenCL | GPU anuncia OpenCL 2.2 | Backend concreto, disponibilidad de ICD, operadores y precisión |
| Orion O6 + NPU | NPU de 30 TOPS con SDK del fabricante | Si el SDK soporta el modelo/operadores; no asumir compatibilidad GGUF ni Strata |
| Orion O6 + GPU PCIe externa | Ranura PCIe Gen4 x8 física | IOMMU, kernel/driver ARM64 de GPU, ancho de enlace negociado, alimentación y compatibilidad de CUDA/ROCm |

Fuentes de software/controladores:
- Radxa O6: https://docs.radxa.com/en/orion/o6
- CIX P1 kernel deployment (proyecto comunitario para O6N, usar como pista, no como garantía de paridad O6): https://github.com/AkaseToshiyuki/cix-p1-kernel-deploy
- Strata Orin: https://github.com/calvinvette/strata-inference-orin
- llama.cpp: https://github.com/ggml-org/llama.cpp

El script comunitario CIX P1 informa de GPU disponible como `/dev/dri/card0` y PCIe probado con una NIC RTL8125 en un O6N; marca VPU/NPU como dependientes de firmware. Esto no valida por sí solo una O6 de venta, un runtime GGUF ni aceleración LLM por NPU. La variante O6N y O6 deben mantenerse diferenciadas en la matriz.

## 4. Coste total de propiedad (TCO) y compras

### 4.1 Radxa Orion O6 64 GB

**Precio de referencia publicado:** 539 USD (MSRP oficial anunciado en PDF de 2024; no equivale a cotización actual ni incluye impuestos/envío).

Enlaces de compra / distribución (stock y precio O6 64 GB deben confirmarse en la ficha de cada vendedor):
- Página oficial del producto y socios autorizados: https://radxa.com/products/orion/o6/
- OKdo, distribuidor global que Radxa lista en su página histórica de distribuidores: https://www.okdo.com/
- Innet24 (Alemania): https://www.innet24.de/
- Maker-store (Alemania): https://shop.maker-store.de/
- Allnet España: https://www.allnet.es/ — el directorio de Radxa publica contacto de ALLNET España en Carballo (A Coruña); solicitar cotización del SKU de 64 GB.
- Directorio de distribuidores (fuente Radxa, página archivada): https://wiki.radxa.com/Buy
- Documentación y contenido del paquete: https://docs.radxa.com/en/orion/o6
- Accesorio de alimentación oficial: desde la sección de accesorios de https://radxa.com/products/orion/o6/
- Almacenamiento NVMe: elegir un SSD M.2 2280 PCIe Gen4 x4 de 1–2 TB de vendedor con stock y factura en España; la ranura está confirmada por la documentación oficial.

No se ha podido confirmar en esta revisión una ficha de venta actual del SKU O6 64 GB con precio final en EUR. Estos enlaces son rutas verificables hacia vendedores/distribuidores, no prueba de stock, precio ni plazo de entrega.

Presupuesto que debe completarse con cotización real:
- Placa O6 64 GB: 539 USD como referencia histórica, **no precio entregado**.
- IVA, transporte, posible aduana/gestión: pendientes de cotización del vendedor.
- Fuente USB-C PD 20 V ≥65 W o fuente ATX compatible: coste pendiente según opción.
- NVMe 1–2 TB: coste pendiente de oferta y capacidad elegidas.
- Cableado/adaptadores y refrigeración extra: 0 € si el paquete incluye caja/disipador y basta la fuente elegida; en caso contrario añadir coste real.
- Total final España: **NO VERIFICADO**. No sumar cifras de accesorios no consultadas ni presentar una conversión de divisa como precio final.

La compra solo se recomienda después de confirmar por escrito SKU de 64 GB, stock, contenido del paquete, IVA, envío a España, garantía y política de devolución. Si el vendedor no puede facilitar esos datos, registrar la oferta como “lead”, no como compra disponible.

### 4.2 Jetson AGX Orin

**Ofertas europeas localizadas (consulta 24-10-2026; verificar antes de pagar):**

| Vendedor | SKU | Precio anunciado | IVA / disponibilidad | Enlace |
|---|---|---:|---|---|
| [Aetherix](https://aetherix.com/product/nvidia-jetson-agx-orin-developer-kit-64gb-945-13730-0055-000/) | Developer Kit 64 GB, 945-13730-0055-000 | 4.199,00 € | IVA incluido; la página indicaba 3 unidades en stock y envío gratuito por Europa | [Ficha](https://aetherix.com/product/nvidia-jetson-agx-orin-developer-kit-64gb-945-13730-0055-000/) |
| [RS España](https://es.rs-online.com/web/p/kits-de-desarrollo-de-procesadores/2539662) | Developer Kit 64 GB, 945-13730-0055-000 | 4.012,53 € | IVA incluido; la página indicaba 9 unidades disponibles para enviar y más desde otro centro | [Ficha](https://es.rs-online.com/web/p/kits-de-desarrollo-de-procesadores/2539662) |
| [Reichelt España](https://www.reichelt.com/es/es/shop/producto/kit_de_desarrollo_nvidia_jetson_agx_orin_cpu_de_12_nucleos_64-383698) | Developer Kit 64 GB, 945-13730-0055-000 | 3.967,06 € antes de IVA | Ficha indica IVA del 21 % adicional y envío desde 9,95 €; plazo indicado 4–5 días laborables | [Ficha](https://www.reichelt.com/es/es/shop/producto/kit_de_desarrollo_nvidia_jetson_agx_orin_cpu_de_12_nucleos_64-383698) |

Reichelt totaliza aproximadamente 4.800,14 € con IVA del 21 % antes del envío (3.967,06 × 1,21). Son precios visibles en páginas de producto, no garantía de que el checkout conserve stock o precio. Confirmar total final y distinguir el kit de desarrollo de un módulo suelto.

Enlaces:
- Especificaciones oficiales: https://www.nvidia.com/es-es/autonomous-machines/embedded-systems/jetson-orin/
- Precio oficial/FAQ: https://developer.nvidia.com/embedded/faq
- Distribuidores desde NVIDIA: usar el enlace “local distributor” de la FAQ oficial.

Presupuesto:
- AGX Orin Developer Kit 64 GB: 3.499 USD de precio oficial anunciado por NVIDIA. No es precio final en EUR.
- NVMe con espacio para modelos y packs: necesario/recomendado por el fork; seleccionar y presupuestar según capacidad.
- Alimentación y refrigeración: verificar si vienen incluidas en el kit específico; no duplicar componentes incluidos.
- IVA/transporte: cotizar con distribuidor europeo.
- Total final España: **NO VERIFICADO** hasta disponer de una oferta final.

Un módulo de producción AGX Orin no es un kit completo: sumar carrier board compatible, fuente, disipación, almacenamiento y carcasa. Comparar ofertas solo cuando el SKU y la lista de componentes coincidan.

### 4.3 Fórmula TCO para LEONES

Registrar por separado:
1. precio del hardware y SKU;
2. IVA e impuestos;
3. envío y tasas de gestión;
4. fuente, carcasa y refrigeración no incluidas;
5. NVMe;
6. adaptadores y cables;
7. consumo de pared medido durante idle, prefill y decode;
8. coste de electricidad según tarifa introducida por el usuario;
9. disponibilidad/garantía y plazo de reposición.

No comparar precio por TOPS. Métricas útiles: EUR por GB de RAM realmente disponible, tokens/s por vatio de pared, tokens generados por kWh y coste total por token para un workload especificado.

## 5. Plan de benchmark reproducible para LEONES

### Fase A — validar la máquina y los controladores

En cada sistema guardar:
- modelo/SKU, número de serie redactado, memoria física, kernel, distribución y firmware;
- `uname -a`, `lscpu`, `free -h`, `lsblk`, `dmesg` relevante;
- versión del driver GPU, Vulkan/OpenCL/CUDA;
- para Vulkan: salida de `vulkaninfo --summary`;
- para PCIe: `lspci -vv` y ancho/velocidad realmente negociados;
- sensores térmicos y límites de potencia disponibles;
- `tegrastats` en Jetson; para ambos sistemas, vatímetro externo en la toma como fuente primaria de consumo.

No afirmar “GPU acelerada” hasta que el log del runtime identifique el backend y la carga real de GPU.

### Fase B — baseline CPU y GPU

Usar la misma revisión fijada de llama.cpp cuando sea posible:
- primero prueba CPU pura;
- luego Vulkan en O6, si el backend compila y detecta el dispositivo;
- luego CUDA en Jetson;
- anotar commit de llama.cpp, flags de compilación, salida de `--version`/ayuda y logs completos.

Modelo inicial pequeño para validar instalación; después un modelo dense de 7–8B y, finalmente, el MoE seleccionado. No empezar por el modelo más grande antes de validar el runtime.

### Fase C — MoE y memoria

Prueba primaria de interés:
- un modelo Qwen3-30B-A3B o Qwen3.5-35B-A3B disponible en GGUF;
- registrar URL exacta, revisión, nombre de fichero, tamaño y SHA-256;
- cuantización idéntica entre plataformas, siempre que el formato sea compatible;
- contexto de 4K y después 8K, aumentando solo si no hay presión de memoria;
- tipo de KV explícito, batch/prefill, número de capas GPU, threads y offload registrados;
- distinguir modelo completo frente a variantes “Coder” con expertos eliminados;
- registrar fallos OOM, swap, uso de SSD y si se leen expertos desde fichero.

En Strata, usar la configuración publicada como baseline para reproducir primero el resultado de Orin. Después variar un único parámetro cada vez: contexto, presupuesto de caché de expertos, MTP, batch de prefill, KV y límite de potencia.

### Fase D — protocolo de medición

- Una carga de calentamiento y al menos 3 ejecuciones medidas por configuración.
- Prompt de contenido fijo y salida máxima fija; guardar tokens reales de entrada/salida.
- Reportar mediana y rango, no solo el mejor resultado.
- Separar tiempo de carga, TTFT, prefill tok/s, decode tok/s, latencia total y memoria máxima.
- Medir consumo en pared durante idle, prefill y decode; informar vatios medios y energía por generación.
- Para Strata, separar prefijos reutilizados de tokens nuevos y caché de expertos caliente de caché fría.
- Incluir logs por ejecución, JSON/CSV, script, commit y hash de modelo.
- Repetir con el límite de potencia sostenible, además de modo máximo, para comprobar el rendimiento continuo y la temperatura.
- Hacer una prueba de calidad/corrección (respuesta esperada o tarea con tests) para evitar que una salida truncada o fallida cuente como éxito.

### Tabla de resultados (rellenar únicamente con mediciones)

| Placa / backend | Modelo / cuantización | Contexto | Prefill tok/s | Decode tok/s | TTFT | RAM máxima / swap | W pared medio decode | tokens/J | Estado |
|---|---|---:|---:|---:|---:|---|---:|---:|---|
| Radxa O6 CPU | DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M (Radxa, terceros) | pp512 / tg128 | 64,60 ± 0,27 (pp512) | 36,29 ± 0,16 (tg128) | No publicado | No publicado | No publicado | No calculable | PUBLISHED; reproducir en O6 64 GB |
| Radxa O6 Vulkan | Pendiente | 4K | No medido | No medido | No medido | No medido | No medido | No medido | PENDIENTE |
| Jetson AGX Orin CUDA/Strata | Qwen3.8-Flash-Next Coder IQ1_M (terceros) | 32K | 37,8–52,5 tok/s en prompts cortos; caso 31.234 tokens/584 s | 18,6–21,6 tok/s (terceros) | No publicado aquí | ≥7,33 GiB libres; swap usado | No medido aquí | No medido aquí | PUBLISHED, tercero |
| Jetson AGX Orin CUDA/Strata | Qwen3.8-Flash-Next Coder IQ1_M (terceros, rebase 0.1.41) | 256K | 58,5 tok/s en prompt de 261.936 tokens | 6,6 tok/s (64 tokens) | No publicado aquí | ≥9,33 GiB libres; swap usado | No medido aquí | No medido aquí | PUBLISHED, tercero |

Los resultados de Orin anteriores no son comparables directamente con las filas de O6 pendientes: los tamaños de prompt, modelo, configuración y contexto difieren. No derivar tokens/J sin medición de potencia.

## 6. Riesgos y criterios de compra

**Radxa O6 — comprar solo si:**
- se acepta trabajo de integración de kernel/backend;
- el vendedor confirma versión de 64 GB y soporte/garantía;
- hay política de devolución si Vulkan/llama.cpp no funciona como se necesita;
- el objetivo incluye desarrollo de drivers y expansión PCIe, no solo “tokens/s listos para usar”.

**Jetson AGX Orin — elegir si:**
- el objetivo prioritario es reproducir Strata/CUDA y validar offload de expertos con menor incertidumbre;
- el coste alto está justificado por la madurez del ecosistema y el tiempo de ingeniería ahorrado;
- se acepta que los resultados publicados pertenecen a Orin 32 GB y a una cuantización/modelo concretos.

**No comprar aún** si el requisito es ejecutar un modelo MoE completo de 30–35B a una tasa de tokens/s mínima concreta: primero fijar el modelo, la cuantización, contexto y objetivo de rendimiento, y exigir un benchmark reproducible del mismo hardware o derecho de devolución.

## 7. Fuentes principales y nivel de confianza

1. Radxa Orion O6 oficial: https://radxa.com/products/orion/o6/ — alta confianza en especificaciones declaradas, no en rendimiento LLM.
2. Documentación O6: https://docs.radxa.com/en/orion/o6 — alta confianza en interfaces y configuración publicada.
3. PDF de precios oficiales históricos: https://dl.radxa.com/orion/o6/radxa_orion_o6_announcement_presentation_2024_12_18.pdf — fuente del MSRP anunciado, no de precio actual entregado.
4. NVIDIA Jetson Orin: https://www.nvidia.com/es-es/autonomous-machines/embedded-systems/jetson-orin/ — alta confianza en especificaciones oficiales.
5. NVIDIA FAQ: https://developer.nvidia.com/embedded/faq — alta confianza en precio oficial anunciado y distinción entre kit y módulo.
6. Strata Orin fork: https://github.com/calvinvette/strata-inference-orin — fuente primaria del port y de las mediciones publicadas por el autor; requiere reproducción independiente.
7. Protocolo de benchmarks Strata: https://github.com/calvinvette/strata-inference-orin/blob/main/docs/COMMUNITY_BENCHMARKS.md — buena guía de campos de medición y transparencia.
8. Kernel CIX P1 comunitario (O6N): https://github.com/AkaseToshiyuki/cix-p1-kernel-deploy — evidencia útil pero específica de O6N; no extrapolar sin comprobar.

## Conclusión

Para un ensayo centrado en motores de inferencia, **Jetson AGX Orin 32/64 GB es la plataforma de menor riesgo técnico gracias al fork Strata con resultados publicados y una ruta CUDA ARM64**. Se han localizado páginas de distribuidores europeos con precios anunciados de unos 4.012–4.199 € IVA incluido para el kit de 64 GB; comprobar disponibilidad y total final en el checkout.

Para un proyecto más abierto, con mayor RAM compartida y expansión PCIe, **Radxa Orion O6 64 GB es una candidata prometedora**. Ya existe un baseline oficial GGUF/CPU de 1.5B documentado por Radxa, pero falta la prueba decisiva: MoE de 30–35B, backend Vulkan comprobado, memoria máxima, swap y consumo de pared. No recomendar comprar la O6 solo por el dato de 100 GB/s o los TOPS anunciados hasta verificar ese caso de uso.

El próximo hito debe ser un benchmark físico comparable, no otra estimación basada en TOPS. LEONES debe conservar comandos, logs, configuraciones, hashes, fallos y consumo medido para que otra persona pueda repetirlo.
