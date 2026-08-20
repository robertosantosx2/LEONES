# Verificación uno a uno — Infraestructura IA local 2026

Fecha de revisión: 2026-08-20.

## Criterio

Se ha comprobado cada candidato contra su repositorio o ficha primaria actual. `verified-primary` significa que la existencia y naturaleza básica del proyecto quedan demostradas por fuente primaria; **no significa que LEONES haya medido su rendimiento**. `archived` significa que el proyecto existe pero ya no debe tratarse como opción activa equivalente a un proyecto mantenido. `unresolved` significa que la referencia del informe no permite establecer de forma suficiente una entidad primaria independiente.

## Runtimes / inferencia

| # | Candidato | Estado | Verificación |
|---:|---|---|---|
| 1 | Rabbit | 🟢 verified-primary | Repositorio `ferrumox/rabbit` activo. README documenta runtime Rust, MoE, streaming de expertos desde disco y ejecución de Kimi K3; además aporta pruebas de corrección y números de una ejecución de 128 GB. Los números son claims/mediciones del proyecto, no mediciones LEONES. |
| 2 | Lemonade | 🟢 verified-primary | `lemonade-sdk/lemonade` activo, Apache-2.0; el proyecto se describe como servicio de aplicaciones IA locales desde GPU/NPU. |
| 3 | llama.cpp | 🟢 verified-primary | `ggml-org/llama.cpp` activo, MIT. El código actual incluye CLI, servidor, benchmark, `fit-params`, cuantización y soporte GGUF. |
| 4 | Ollama | 🟢 verified-primary | `ollama/ollama` activo, MIT. El repositorio actual muestra soporte para familias actuales y la licencia MIT. |
| 5 | KoboldCpp | 🟢 verified-primary | `LostRuins/koboldcpp` activo. El propio repositorio identifica KoboldCpp y KoboldAI Lite como AGPL-3.0 y diferencia las dependencias MIT. |
| 6 | MLX / MLX-LM | 🟢 verified-primary | `ml-explore/mlx` activo; framework de arrays para Apple Silicon con APIs Python/C/C++/Swift y paquetes para macOS/Linux. La ficha actual lo identifica como MIT. |
| 7 | vLLM | 🟢 verified-primary | `vllm-project/vllm` activo, Apache-2.0; engine de inferencia/serving de alto throughput y eficiencia de memoria. |
| 8 | ExLlamaV2 | 🟡 archived | El repositorio existe y describe inferencia local para GPUs consumer, pero está archivado; el propio proyecto indica que el desarrollo continúa en ExLlamaV3. Debe conservarse como tecnología histórica/compatibilidad, no como primera opción de nuevo desarrollo. |
| 9 | llamafile | 🟢 verified-primary | El proyecto actual está bajo `mozilla-ai/llamafile`; archivos actuales llevan Apache-2.0. La referencia histórica `Mozilla-Ocho` debe normalizarse al repositorio actual. |
| 10 | LocalAI | 🟢 verified-primary | `mudler/LocalAI` activo, MIT; engine abierto para LLM, visión, voz, imagen y vídeo y no requiere GPU. |
| 11 | SGLang | 🟢 verified-primary | `sgl-project/sglang` activo, Apache-2.0; serving de LLM y multimodal, con foco en rendimiento y serving. |
| 12 | TGI | 🟡 archived | `huggingface/text-generation-inference` fue archivado el 21-03-2026 y es solo lectura. Debe mantenerse como referencia histórica, no como runtime activo prioritario. |
| 13 | TensorRT-LLM | 🟢 verified-primary | `NVIDIA/TensorRT-LLM` activo; licencia Apache-2.0 según LICENSE actual. Mantiene componentes y dependencias con licencias diferenciadas cuando corresponde. |
| 14 | Aphrodite Engine | 🟢 verified-primary | Proyecto activo actualmente en `dphnAI/aphrodite-engine`; AGPL-3.0; engine de inferencia/serving que integra trabajo de vLLM y múltiples cuantizaciones. |
| 15 | text-generation-webui / textgen | 🟢 verified-primary | Repositorio activo de oobabooga; interfaz local para texto/visión/tool-calling/training, AGPL-3.0. La denominación actual es `textgen` en el README, aunque el repositorio mantiene el nombre histórico. |

## Servidores / aplicaciones / agentes

| # | Candidato | Estado | Verificación |
|---:|---|---|---|
| 16 | Fox | 🔴 unresolved | La referencia del informe apuntaba a `ferrumox/rabbit/tree/fox`, pero el repositorio actual no expone una rama `fox` y tampoco existe el archivo `fox/README.md` en `main`. No se promueve a entidad independiente hasta encontrar fuente primaria actual. |
| 17 | GPT4All | 🟢 verified-primary | `nomic-ai/gpt4all` activo; ejecuta LLM localmente en desktops/laptops y no requiere API ni GPU. LICENSE.txt contiene MIT. |
| 18 | Jan | 🟢 verified-primary | `janhq/jan` activo, offline/local-first y Apache-2.0. La documentación actual muestra además releases recientes. |
| 19 | AnythingLLM | 🟢 verified-primary | `Mintplex-Labs/anything-llm` activo, MIT; aplicación local-first con agentes, RAG, vector DB y soporte multiusuario. La documentación de self-hosted confirma operación local/air-gapped con telemetría opcional. |
| 20 | Tabby | 🟢 verified-primary | `TabbyML/tabby` activo, asistente de coding self-hosted. LICENSE actual: Apache-2.0 para el contenido fuera de las excepciones `ee/` y componentes de terceros. Soporta GPUs consumer. |

## Técnicas / investigación

| # | Candidato | Estado | Verificación |
|---:|---|---|---|
| 21 | DirectKV | 🔴 unresolved | No se ha localizado durante esta revisión un repositorio primario inequívoco que permita confirmar la entidad descrita en el informe y sus claims de zero-copy KV. Se conserva como hipótesis de investigación, no como software verificado. |
| 22 | Colibrì | 🟢 verified-primary | Existe repositorio independiente `JustVugg/colibri`. Su README lo presenta como runtime C de dependencias mínimas para GLM-5.2, con streaming de expertos desde disco. Sus cifras deben considerarse claims del proyecto hasta benchmark LEONES. |
| 23 | AutoGPTQ | 🟡 archived | `AutoGPTQ/AutoGPTQ` fue archivado el 11-04-2025. El propio proyecto indica que ha detenido el desarrollo y recomienda migrar a GPTQModel. Se conserva por relevancia histórica de GPTQ, no como dependencia nueva.

## Modelos/familias del radar

| Modelo/familia | Estado | Resultado primario |
|---|---|---|
| Qwen3 235B-A22B | 🟢 verified-primary | Ficha oficial en Hugging Face; Apache-2.0. |
| gpt-oss 120B | 🟢 verified-primary | Ficha oficial OpenAI en Hugging Face; Apache-2.0; ficha documenta MXFP4 y capacidades agentivas. |
| Gemma 3 | 🟡 verified-primary / licencia no-OSI | Ficha oficial Google en Hugging Face; pesos abiertos pero licencia `Gemma`, con términos de uso propios y acceso gated. No clasificar como Apache/MIT. |
| Phi-4-mini-instruct | 🟢 verified-primary | Ficha oficial Microsoft; MIT. |
| Devstral Small 2505 | 🟢 verified-primary | Ficha oficial Mistral; Apache-2.0, 24B, 128k y soporte de inferencia local documentado. |
| Llama 4 Scout | 🟡 verified-primary / licencia propietaria comunitaria | Ficha oficial Meta; Llama 4 Community License, MoE 17B activados/109B totales y contexto de 10M. No clasificar como OSI. |
| Mistral Small 3.1 24B | 🟢 verified-primary | Ficha oficial Mistral; Apache-2.0 y configuración multimodal con 131072 posiciones. |
| Kimi K3 | 🟢 verified-primary | Colección oficial Moonshot en Hugging Face identifica Kimi K3 como 2.8T. La licencia y detalles de despliegue deben registrarse desde la ficha/model card concreta antes de promocionar claims adicionales. |
| GLM-5.2 | 🟡 unresolved en esta revisión | La referencia del informe se relaciona con Colibrì/Rabbit, pero no se ha establecido aquí una ficha primaria inequívoca de `GLM-5.2` que permita validar todos los claims aportados. Mantener como candidato ligado a la investigación de runtimes hasta completar identidad primaria. |
| DeepSeek-V3.2 | 🟢 verified-primary | Ficha oficial DeepSeek en Hugging Face; MIT, 685B parámetros y soporte de inferencia con Transformers/vLLM documentado. |

## Resultado del quality gate de esta pasada

- **20 proyectos con fuente primaria suficiente**.
- **3 proyectos históricos/archivados:** ExLlamaV2, TGI, AutoGPTQ.
- **2 referencias sin entidad primaria suficientemente demostrada:** Fox, DirectKV.
- **1 candidato de modelo pendiente de identidad primaria inequívoca:** GLM-5.2.
- Los proyectos verificados **no quedan convertidos en benchmarks LEONES**: la verificación demuestra identidad/estado/licencia/capacidades documentadas, no rendimiento físico propio.

## Decisión

Los candidatos `verified-primary` pueden pasar de `candidate/unverified` a **`verified-primary / pending LEONES benchmark`** en el radar de Atlas/Prospector.

Los `archived` permanecen como referencias históricas.

Los `unresolved` permanecen en cola y **no deben generar recomendaciones ni entradas canónicas verificadas**.

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
