# Verificación uno a uno — Infraestructura IA local 2026

Fecha de revisión: 2026-08-20.

## Criterio

Se ha comprobado cada candidato contra su repositorio o ficha primaria actual. `verified-primary` significa que la existencia y naturaleza básica del proyecto quedan demostradas por fuente primaria; **no significa que LEONES haya medido su rendimiento**. `archived` significa que el proyecto existe pero ya no debe tratarse como opción activa equivalente a un proyecto mantenido. `unresolved` significa que la referencia del informe no permite establecer de forma suficiente una entidad primaria independiente.

## Runtimes / inferencia

| # | Candidato | Estado | Verificación |
|---:|---|---|---|
| 1 | Rabbit | 🟢 verified-primary | `ferrumox/rabbit` activo; runtime Rust, MoE y streaming de expertos desde disco documentados. La ejecución de Kimi K3 y sus cifras son evidencia del propio proyecto, no mediciones LEONES. |
| 2 | Lemonade | 🟢 verified-primary | `lemonade-sdk/lemonade` activo, Apache-2.0; servicio de aplicaciones IA locales desde GPU/NPU. |
| 3 | llama.cpp | 🟢 verified-primary | `ggml-org/llama.cpp` activo, MIT; CLI, servidor, benchmark, `fit-params`, cuantización y GGUF presentes en el código actual. |
| 4 | Ollama | 🟢 verified-primary | `ollama/ollama` activo, MIT; soporte de familias de modelos actuales y runtime local. |
| 5 | KoboldCpp | 🟢 verified-primary | `LostRuins/koboldcpp` activo; código KoboldCpp y KoboldAI Lite bajo AGPL-3.0, con dependencias MIT diferenciadas. |
| 6 | MLX / MLX-LM | 🟢 verified-primary | `ml-explore/mlx` activo; framework para Apple Silicon con APIs Python/C/C++/Swift y paquetes para macOS/Linux. |
| 7 | vLLM | 🟢 verified-primary | `vllm-project/vllm` activo, Apache-2.0; engine de inferencia/serving de alto throughput y eficiencia de memoria. |
| 8 | ExLlamaV2 | 🟡 archived | Repositorio existente pero archivado; el propio proyecto indica que el desarrollo continúa en ExLlamaV3. Mantener como referencia histórica/compatibilidad. |
| 9 | llamafile | 🟢 verified-primary | Proyecto actual bajo `mozilla-ai/llamafile`; código actual con Apache-2.0. Normalizar la antigua referencia `Mozilla-Ocho` al repositorio actual. |
| 10 | LocalAI | 🟢 verified-primary | `mudler/LocalAI` activo, MIT; engine abierto para LLM, visión, voz, imagen y vídeo, sin GPU obligatoria. |
| 11 | SGLang | 🟢 verified-primary | `sgl-project/sglang` activo, Apache-2.0; serving de LLM y multimodal. |
| 12 | TGI | 🟡 archived | `huggingface/text-generation-inference` archivado el 21-03-2026 y solo lectura. Mantener histórico. |
| 13 | TensorRT-LLM | 🟢 verified-primary | `NVIDIA/TensorRT-LLM` activo; LICENSE actual declara Apache-2.0, con componentes que pueden tener licencias diferenciadas. |
| 14 | Aphrodite Engine | 🟢 verified-primary | `dphnAI/aphrodite-engine` activo, AGPL-3.0; engine de serving/inferencia basado en tecnologías como vLLM y con múltiples cuantizaciones. |
| 15 | text-generation-webui / textgen | 🟢 verified-primary | Repositorio oobabooga activo; interfaz local para texto/visión/tool-calling/training, AGPL-3.0. |

## Servidores / aplicaciones / agentes

| # | Candidato | Estado | Verificación |
|---:|---|---|---|
| 16 | Fox | 🔴 unresolved | La referencia `ferrumox/rabbit/tree/fox` no corresponde actualmente a una rama `fox` ni existe `fox/README.md` en `main`. No promover. |
| 17 | GPT4All | 🟢 verified-primary | `nomic-ai/gpt4all` activo; LLM local en desktops/laptops sin API ni GPU obligatoria. LICENSE.txt: MIT. |
| 18 | Jan | 🟢 verified-primary | `janhq/jan` activo, offline/local-first y Apache-2.0. |
| 19 | AnythingLLM | 🟢 verified-primary | `Mintplex-Labs/anything-llm` activo, MIT; aplicación local-first con agentes, RAG, vector DB y multiusuario. Self-hosted permite operación local/air-gapped con telemetría opcional. |
| 20 | Tabby | 🟢 verified-primary | `TabbyML/tabby` activo; asistente de coding self-hosted. LICENSE actual: Apache-2.0 salvo excepciones indicadas para `ee/` y terceros. |

## Técnicas / investigación

| # | Candidato | Estado | Verificación |
|---:|---|---|---|
| 21 | DirectKV | 🔴 unresolved | No se ha localizado un repositorio primario inequívoco que permita confirmar la entidad descrita en el informe y sus claims de zero-copy KV. Mantener como hipótesis. |
| 22 | Colibrì | 🟢 verified-primary | Existe `JustVugg/colibri`; runtime C de dependencias mínimas para GLM-5.2 con streaming de expertos desde disco. Las cifras son claims del proyecto hasta benchmark LEONES. |
| 23 | AutoGPTQ | 🟡 archived | `AutoGPTQ/AutoGPTQ` archivado el 11-04-2025; el propio proyecto declara que ha detenido desarrollo y recomienda GPTQModel. Mantener histórico. |

## Modelos/familias del radar

| Modelo/familia | Estado | Resultado primario |
|---|---|---|
| Qwen3 235B-A22B | 🟢 verified-primary | Ficha oficial Hugging Face; Apache-2.0. |
| gpt-oss 120B | 🟢 verified-primary | Ficha oficial OpenAI en Hugging Face; Apache-2.0; documenta MXFP4 y capacidades agentivas. |
| Gemma 3 | 🟡 verified-primary / licencia no-OSI | Ficha oficial Google; pesos abiertos pero licencia `Gemma`, con términos propios y acceso gated. No clasificar como Apache/MIT. |
| Phi-4-mini-instruct | 🟢 verified-primary | Ficha oficial Microsoft; MIT. |
| Devstral Small 2505 | 🟢 verified-primary | Ficha oficial Mistral; Apache-2.0, 24B, 128k y soporte de inferencia local documentado. |
| Llama 4 Scout | 🟡 verified-primary / licencia comunitaria | Ficha oficial Meta; Llama 4 Community License, MoE 17B activados/109B totales y contexto de 10M. No clasificar como OSI. |
| Mistral Small 3.1 24B | 🟢 verified-primary | Ficha oficial Mistral; Apache-2.0 y configuración multimodal con 131072 posiciones. |
| Kimi K3 | 🟢 verified-primary | Colección oficial Moonshot en Hugging Face identifica Kimi K3 como 2.8T. Completar licencia/model card concreta antes de promocionar claims adicionales. |
| GLM-5.2 | 🟡 unresolved | No se ha establecido en esta revisión una ficha primaria inequívoca de `GLM-5.2` que permita validar todos los claims. Mantener ligado a la investigación Colibrì/Rabbit. |
| DeepSeek-V3.2 | 🟢 verified-primary | Ficha oficial DeepSeek en Hugging Face; MIT, 685B y soporte de inferencia con Transformers/vLLM documentado. |

## Resultado del quality gate

**23 proyectos revisados:**

- **18 `verified-primary`**.
- **3 `archived`**: ExLlamaV2, TGI, AutoGPTQ.
- **2 `unresolved`**: Fox, DirectKV.

**10 modelos/familias revisados:**

- **7 `verified-primary`**.
- **2 `verified-primary` con licencia diferenciada/no-OSI**: Gemma 3, Llama 4 Scout.
- **1 `unresolved`**: GLM-5.2.

Los proyectos verificados **no quedan convertidos en benchmarks LEONES**: la verificación demuestra identidad/estado/licencia/capacidades documentadas, no rendimiento físico propio.

## Decisión

Los `verified-primary` pasan de `candidate/unverified` a **`verified-primary / pending LEONES benchmark`** en el radar de Atlas/Prospector.

Los `archived` permanecen como referencias históricas.

Los `unresolved` permanecen en cola y **no generan recomendaciones ni entradas canónicas verificadas**.

```text
PRIMARY SOURCE
      ↓
IDENTITY / LICENSE / STATUS
      ↓
verified-primary
      ↓
LLMFIT
      ↓
RUNTIME + QUANTIZATION
      ↓
LEONES BENCHMARK
      ↓
measured
```
