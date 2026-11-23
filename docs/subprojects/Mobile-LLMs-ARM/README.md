# Mobile-LLMs-ARM — investigación de IA local en móviles y sistemas ARM

Estado: investigación incorporada; catálogo y automatización en revisión mediante PR.

## Propósito

Investigar LLMs e IA local en Android ARM64, Linux móvil, Termux/proot, sistemas embebidos ARM y arquitecturas CPU+GPU+DSP/NPU. Medir compatibilidad, rendimiento sostenido, memoria, energía y temperatura.

## Catálogo

- [Observatorio HTML](../../../web/mobile-llms-arm.md)
- [Feed JSON](../../../data/observatory/mobile-llms-arm.json)
- [Registro de fuentes](../../../research/mobile-llms-arm/sources.json)
- [Generador](../../../scripts/research/mobile_llms_arm.py)
- [Roadmap](ROADMAP.md)

La publicación oficial es Markdown; JSON se conserva únicamente como intercambio interno en `data/observatory/`. La prospección se integra en Daily Atlas Prospection. GitHub y Reddit se consultan cuando sus APIs públicas están disponibles; X se mantiene como búsquedas directas hasta disponer de API autorizada.

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
