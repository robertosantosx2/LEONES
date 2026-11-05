# Investigación: IA Local (on-device / offline) para Android y hardware ARM (no Apple)

**Fecha:** 5 de noviembre de 2026  
**Alcance:** Proyectos ejecutables en móviles Android o hardware ARM similar (excluyendo Apple Silicon). Enfoque en madurez, usabilidad y viabilidad en hardware antiguo o de bajas prestaciones (4-6 GB RAM, SoCs pre-2022/2023).  
**Fuentes:** GitHub, Hugging Face (LiteRT Community, colecciones GGUF móviles), comparativas 2026 y menciones recientes en X.com.

El ecosistema se centra en dos motores principales:
- **llama.cpp** (formato GGUF) → máxima libertad de modelos.
- **LiteRT-LM / MediaPipe / Google AI Edge** (formatos `.litertlm` / `.task`) → mejor integración NPU/GPU en Snapdragon y Tensor.

Casi todos requieren **arm64-v8a** (prácticamente todo Android desde ~2017-2019).

---

## Proyectos destacados (ordenados por madurez + utilidad práctica)

### 1. PocketPal AI (a-ghorbani/pocketpal-ai)
- **Propuesta**: App React Native (iOS + Android) que descarga y ejecuta cualquier GGUF desde Hugging Face vía llama.rn/llama.cpp. Incluye TTS on-device (ONNX/Kokoro), “Pals” (personas con system prompts), tools (calculadora, fecha, HTML), benchmarks integrados y leaderboard de dispositivos.
- **Madurez**: Alta. ~9k estrellas, releases frecuentes (v1.21+ a finales 2026), cientos de miles/millones de descargas, MIT, activa comunidad. Disponible en Play Store y APK.
- **Hardware bajo/antiguo**: Excelente. Modelos 0.5B-1.5B Q4_K_M (Qwen2.5-0.5B ~0.4 GB, Gemma-3-1B ~0.7 GB, Llama-3.2-1B) caben y corren en 4-6 GB RAM. En 6-8 GB se llega cómodo a 2-4B. Soporta GPU/Vulkan y NPU experimental en Snapdragon recientes.
- **Enlaces**: [GitHub](https://github.com/a-ghorbani/pocketpal-ai) · [pocketpal.dev](https://pocketpal.dev)  
  Modelos optimizados también en colecciones HF como `AmareshHebbar/pocketllm-models`.

### 2. OfflineLLM (jegly/OfflineLLM)
- **Propuesta**: Chat 100 % offline (cero permiso INTERNET en el manifest), cualquier GGUF vía llama.cpp con kernels ARM optimizados (dotprod/fp16/i8mm/SVE), GPU Vulkan opcional, cifrado de settings, bloqueo biométrico y firmas post-cuánticas.
- **Madurez**: Media-alta (~280 estrellas, releases activos, foco en privacidad extrema). APK “Vanilla” que importa GGUF.
- **Hardware bajo/antiguo**: Muy fuerte. Recomienda explícitamente gemma-3-270m (~300 MB) para 2-4 GB RAM, Qwen 0.8B para 4-6 GB. Dispatch automático de kernels según el SoC exacto. Android 13+ arm64.
- **Enlace**: [GitHub](https://github.com/jegly/OfflineLLM)

### 3. OlliteRT (NightMean/OlliteRT)
- **Propuesta**: Convierte el teléfono en servidor OpenAI-compatible (tipo “Ollama para Android”) usando LiteRT-LM. Descarga modelos `.litertlm` de HF, multimodal (visión/audio), tool calling experimental.
- **Madurez**: Media-alta (~613 estrellas, forks activos).
- **Hardware bajo/antiguo**: 6 GB mínimo (recomendado 8 GB+). Gemma-3 1B (~0.5 GB) es viable en gama media-baja; modelos E2B/E4B necesitan más.
- **Enlace**: [GitHub](https://github.com/NightMean/OlliteRT)

### 4. MLC-LLM + MLC Chat
- **Propuesta**: Motor de compilación (TVM) que genera kernels específicos por hardware (OpenCL Adreno, Mali, etc.). App MLC Chat permite descargar modelos precompilados y correr offline.
- **Madurez**: Muy alta (framework ~23k estrellas). App Android vía APK de releases de `binary-mlc-llm-libs`. Destaca en NPU Hexagon de Snapdragon (mejor que puro CPU en muchos tests 2026).
- **Hardware bajo/antiguo**: Bueno en Snapdragon medios/altos; en dispositivos muy viejos o sin buen OpenCL baja a CPU. Modelos pequeños (Phi, Qwen 1.5B, Gemma 2B) son usables.
- **Enlaces**: [mlc-ai/mlc-llm](https://github.com/mlc-ai/mlc-llm) + docs Android · APKs en [mlc-ai/binary-mlc-llm-libs](https://github.com/mlc-ai/binary-mlc-llm-libs)

### 5. Maid (Mobile-Artificial-Intelligence/maid)
- **Propuesta**: App React Native (Android) con llama.cpp local (GGUF) + proveedores remotos (OpenAI, Anthropic, Ollama, etc.) con tu propia key. Descarga de modelos desde HF, personas, export de chats.
- **Madurez**: Alta (~2.8k estrellas, reescritura a React Native en 2026, activa).
- **Hardware bajo/antiguo**: Similar a PocketPal; modelos 1-3B Q4 en 6 GB+.
- **Enlace**: [GitHub](https://github.com/Mobile-Artificial-Intelligence/maid)

### 6. Google AI Edge / LiteRT-LM + AI Edge Gallery
- **Propuesta**: Runtime oficial de Google para modelos on-device (Gemma 3/4 E2B/E4B, FunctionGemma, etc.). Formatos `.litertlm` optimizados. Gallery app facilita descarga y prueba.
- **Madurez**: Oficial y creciente. Modelos en Hugging Face `litert-community` (Gemma-4-E2B, Gemma-3 1B, etc.).
- **Hardware bajo/antiguo**: Gemma-3 1B y 270m son ideales para 4-6 GB. Aceleración NPU/GPU en Snapdragon 8 Gen y Tensor.
- **Enlaces**: [developers.google.com/edge](https://developers.google.com/edge) + HF [litert-community](https://huggingface.co/litert-community)

---

## Otros proyectos relevantes (especializados o emergentes)

- **TrueLarge-RT** (nareshis21/Truelarge-RT): Streaming layer-by-layer + mmap para correr modelos 20B-70B (incluso 70B Q2) en 4 GB RAM (ej. Realme 2 Pro). Extremadamente interesante para hardware antiguo, aunque velocidad baja (0.01- varios tok/s). Madurez baja-media.
- **DistAi** (alex8819/DistAi): Distribuye un modelo grande entre varios teléfonos ARM vía RPC de llama.cpp (pool de RAM/CPU). Útil para clusters de móviles viejos.
- **AndroidLM** (Phineas1500/AndroidLM): Asistente de investigación offline con MoE 35B streameado + corpus Wikipedia local. Requiere ~8-12 GB.
- **Solus**, **L-AI** (SmallAICreator), **LM Playground**, **PrismLocal**, **PocketOrca-LLM** (NPU Qualcomm específico), **llmedge**: Variantes GGUF o LiteRT con RAG, TTS/STT o foco servidor.
- **Termux + llama.cpp / Ollama**: Ruta power-user (no app GUI), máxima flexibilidad en ARM64.

---

## Valoración para hardware antiguo o bajas prestaciones (4-6 GB RAM, SoCs pre-2022/2023)

Los más recomendables son **PocketPal AI**, **OfflineLLM** y modelos pequeños vía LiteRT/MLC.

- **Modelos ideales**: Qwen2.5/3 0.5-0.8B, Gemma-3 270m-1B, Llama-3.2 1B, SmolLM, Phi-mini en Q4_K_M o INT4/8 (tamaños 0.3-1.2 GB).
- **Expectativa realista**: 5-20+ tok/s en 1B, menos en 3B; calor y throttling aparecen rápido.
- TrueLarge-RT o streaming de expertos (MoE) permiten modelos “imposibles” a costa de velocidad y almacenamiento.
- Evitar 7B+ densos en <8 GB sin técnicas especiales. Vulkan/OpenCL ayuda, pero en Mali antiguos a veces es inestable.

**Regla práctica de RAM**: modelo Q4 ≈ 0.5-0.6 × parámetros + overhead de contexto.

---

## Perfiles de X.com más activos o diferenciales (para seguir)

- **@a_ghorbani** (o búsqueda “a-ghorbani PocketPal”) — Desarrollador principal de PocketPal AI. Actualizaciones de releases, benchmarks y modelos.
- **@jegly** (o “jegly OfflineLLM”) — Autor de OfflineLLM; foco en privacidad extrema y optimizaciones ARM.
- Cuentas de ecosistema: busca “MLC Chat”, “LiteRT-LM”, “local LLM Android”, “GGUF Android” o perfiles como los de Liquid AI / SparkLLM cuando publican ports móviles.
- Comunidades amplias: sigue hashtags o búsquedas `#LocalLLM #AndroidAI #OnDeviceAI` y cuentas de revisores de apps offline.

---

## Fuentes principales de modelos

- Hugging Face → búsqueda “GGUF” + “mobile”/“Android”.
- Colecciones **litert-community** (Gemma E2B/E4B, 1B, FunctionGemma).
- bartowski, unsloth, Qwen, etc.

Siempre verifica el tamaño vs RAM disponible.

---

## Resumen ejecutivo

El panorama a noviembre 2026 es **maduro para uso diario privado en gamas medias** y **viable (con modelos pequeños) incluso en hardware de hace 3-5 años**.  

- **PocketPal + OfflineLLM** cubren la mayoría de casos de uso.
- **MLC / LiteRT** destacan cuando el SoC tiene buena aceleración NPU/GPU.

Este documento forma parte del Atlas de conocimiento de LEONES (Libre Open Agent Stack).
