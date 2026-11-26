# Mobile-LLMs-ARM — investigación de IA local en móviles y sistemas ARM

Estado: investigación incorporada; catálogo y automatización en revisión mediante PR.

## Propósito

Investigar LLMs e IA local en Android ARM64, Linux móvil, Termux/proot, sistemas embebidos ARM y arquitecturas CPU+GPU+DSP/NPU. Medir compatibilidad, rendimiento sostenido, memoria, energía y temperatura.

## Catálogo

- [Observatorio HTML](../../../web/mobile-llms-arm.html)
- [Feed JSON](../../../web/data/mobile-llms-arm.json)
- [Registro de fuentes](../../../research/mobile-llms-arm/sources.json)
- [Generador](../../../scripts/research/mobile_llms_arm.py)
- [Roadmap](ROADMAP.md)
- [Dossier llm.asm: Linux móvil, bare metal ARM64 y Mobile Intelligence Platform](../../../research/mobile-llms-arm/llm-asm-mobile-intelligence-platform-2026-11.md)

El HTML es autocontenido y offline. La prospección se integra en Daily Atlas Prospection. GitHub y Reddit se consultan cuando sus APIs públicas están disponibles; X se mantiene como búsquedas directas hasta disponer de API autorizada.

## Taxonomía

| Área | Investigación |
|---|---|
| Android | runtimes nativos, JNI, NDK, no-root/root, API servers |
| Linux móvil | postmarketOS, Ubuntu Touch, Debian/Ubuntu ARM64, Termux/proot |
| CPU | ARM NEON, dotprod, i8mm y extensiones disponibles |
| GPU | Adreno, Mali, Vulkan, OpenCL y drivers |
| DSP/NPU | Qualcomm Hexagon/HTP, QNN, MediaTek APU, Exynos |
| Modelos | LLM compactos, VLM, MoE, ASR, TTS y embeddings |
| Sistemas | agentes locales, nodos edge y clústeres de teléfonos |
| Eficiencia | cuantización, KV cache, prefill/decode, energía y throttling |

## Evidencia y estados

- discovered: hallazgo automático.
- pending_review: requiere inspección primaria.
- source_verified: fuente y metadatos confirmados; no implica ejecución.
- reproduced: prueba documentada en dispositivo identificado.
- measured: benchmark con protocolo y artefactos.
- rejected/archived: descartado o archivado con motivo.

No convertir estrellas, README, cifras sociales o benchmarks de terceros en mediciones LEONES. Registrar SoC, RAM, sistema operativo, runtime/commit, backend, modelo/hash/cuanti­zación, contexto, hilos, duración, TTFT, prefill, decode, energía y temperatura.

## Integraciones potenciales

- Atlas: identidad, procedencia y licencias.
- NEPENTHES: protocolo de benchmark móvil y observabilidad.
- Router: selección según SoC, RAM y aceleradores.
- REDIL: teléfono como nodo heterogéneo.
- LEONES Lab Agent: inventario y recibos de pruebas con aprobación explícita.

La automatización publica descubrimientos, no aprueba, recomienda, instala, ejecuta ni integra proyectos externos.

## Plataforma de referencia — Xiaomi Mi 9T Pro

La campaña del [Xiaomi Mi 9T Pro de 6 GB](../../../hardware/XIAOMI-MI-9T-PRO-6GB.md) tiene documentación específica:

- [Plan de pruebas por gates](devices/XIAOMI-MI-9T-PRO-TEST-PLAN.md)
- [Matriz de runtimes y orden de evaluación](devices/XIAOMI-MI-9T-PRO-RUNTIME-MATRIX.md)
- [Protocolo de benchmark móvil NEPENTHES](devices/XIAOMI-MI-9T-PRO-BENCHMARK-PROTOCOL.md)
- [Primera inferencia LFM2-700M con llama.cpp (2026-11-23)](devices/XIAOMI-MI-9T-PRO-LLAMA-CPP-LFM2-700M-20261123.md)
- [Experimento LFM2-2.6B Q4_K_M con llama.cpp (2026-11-23)](devices/XIAOMI-MI-9T-PRO-LLAMA-CPP-LFM2-2.6B-20261123.md)

El primer camino es Android sin root. La versión de Android, API, ABI, kernel, root y capacidades GPU/DSP siguen UNKNOWN hasta el inventario físico. El espacio libre comunicado (>30 GB) no sustituye la comprobación de espacio efectivo ni de RAM disponible.

La primera prueba física demostró carga y generación CPU con LFM2-700M-Q4_K_M: 120.4 tokens/s de prefill y 40.2 tokens/s de generación en una única ejecución exploratoria. Posteriormente, LFM2-2.6B-Q4_K_M se cargó y generó texto en dos ejecuciones CPU con configuración idéntica: 21.6/22.1 tokens/s de prompt y 11.4/11.3 tokens/s de generación; la repetición terminó con código 0. Ambas campañas siguen siendo exploratorias y no constituyen benchmarks sostenidos NEPENTHES. Véanse los informes enlazados para hashes, parámetros, memoria, sensores y límites. La zona térmica 54 (`pm8150b-wp-therm`) permanece sin identificar.

La campaña no presupone que AIPerf, NVML, Nsight/CUPTI o QNN sean ejecutables en el teléfono. Se preservará la separación entre runner móvil, fuentes de telemetría Android y normalización posterior en NEPENTHES.
