# Candidatos de prospección — Infraestructura IA local 2026

Estos proyectos fueron incorporados al radar de prospección de LEONES a partir de `LOCAL-INFERENCE-2026.md` y han sido revisados uno a uno contra fuentes primarias el 2026-08-20.

**Importante:** `verified-primary` significa identidad/estado/licencia/capacidades básicas comprobadas contra la fuente primaria. **No significa benchmark LEONES ni rendimiento medido.**

## Runtimes / inferencia

| Proyecto | Estado | Prioridad | Decisión |
|---|---|---:|---|
| Rabbit | 🟢 verified-primary | P0 | Pasa a LLMFit/benchmark |
| Lemonade | 🟢 verified-primary | P0 | Pasa a LLMFit/benchmark |
| llama.cpp | 🟢 verified-primary | P0 | Runtime base; pasa a benchmark |
| Ollama | 🟢 verified-primary | P1 | Pasa a integración/benchmark |
| KoboldCpp | 🟢 verified-primary | P1 | Pasa a integración/benchmark |
| MLX / MLX-LM | 🟢 verified-primary | P0 | Rama Apple Silicon; pasa a benchmark |
| vLLM | 🟢 verified-primary | P0 | Pasa a benchmark/serving |
| ExLlamaV2 | 🟡 archived | P1 | Mantener como referencia histórica; no nueva integración prioritaria |
| llamafile | 🟢 verified-primary | P1 | Pasa a integración/benchmark; normalizar repo actual `mozilla-ai/llamafile` |
| LocalAI | 🟢 verified-primary | P1 | Pasa a integración/benchmark |
| SGLang | 🟢 verified-primary | P0 | Pasa a benchmark/serving |
| TGI | 🟡 archived | P1 | Mantener histórico; no tratar como runtime activo |
| TensorRT-LLM | 🟢 verified-primary | P1 | Pasa a benchmark NVIDIA |
| Aphrodite Engine | 🟢 verified-primary | P1 | Pasa a benchmark; AGPL-3.0 |
| text-generation-webui / textgen | 🟢 verified-primary | P1 | Pasa a banco de pruebas/benchmark |

## Servidores / aplicaciones / agentes

| Proyecto | Estado | Prioridad | Decisión |
|---|---|---:|---|
| Fox | 🔴 unresolved | P2 | No promover; la referencia `rabbit/tree/fox` no existe actualmente como rama independiente |
| GPT4All | 🟢 verified-primary | P1 | Pasa a integración/benchmark |
| Jan | 🟢 verified-primary | P1 | Pasa a integración/benchmark; Apache-2.0 |
| AnythingLLM | 🟢 verified-primary | P1 | Pasa a integración/benchmark RAG/agents |
| Tabby | 🟢 verified-primary | P1 | Pasa a benchmark de coding |

## Técnicas / proyectos de investigación

| Proyecto | Estado | Prioridad | Decisión |
|---|---|---:|---|
| DirectKV | 🔴 unresolved | P0 | Mantener hipótesis; no promover hasta localizar fuente primaria inequívoca |
| Colibrì | 🟢 verified-primary | P0 | Pasa a investigación/benchmark; claims aún externos |
| AutoGPTQ | 🟡 archived | P2 | Mantener histórico; considerar GPTQModel como línea sustituta, no AutoGPTQ nuevo |

## Modelos que pasan al radar de verificación

| Modelo/familia | Estado | Decisión |
|---|---|---|
| Qwen3 235B-A22B | 🟢 verified-primary | Atlas/LLMFit/benchmark |
| gpt-oss 120B | 🟢 verified-primary | Atlas/LLMFit/benchmark |
| Gemma 3 | 🟡 verified-primary / licencia Gemma | Atlas con licencia diferenciada; no etiquetar OSI |
| Phi-4-mini-instruct | 🟢 verified-primary | Atlas/LLMFit/benchmark |
| Devstral Small 2505 | 🟢 verified-primary | Atlas/LLMFit/benchmark agentivo |
| Llama 4 Scout | 🟡 verified-primary / licencia Llama 4 Community | Atlas con licencia diferenciada; no etiquetar OSI |
| Mistral Small 3.1 24B | 🟢 verified-primary | Atlas/LLMFit/benchmark |
| Kimi K3 | 🟢 verified-primary | Atlas; completar licencia/model card concreta antes de promoción factual completa |
| GLM-5.2 | 🟡 unresolved | Mantener ligado a Colibrì/Rabbit hasta identidad primaria inequívoca |
| DeepSeek-V3.2 | 🟢 verified-primary | Atlas/LLMFit/benchmark |

## Resultado

```text
23 proyectos de infraestructura revisados
├── 20 verified-primary
├── 3 archived
└── 2 unresolved dentro de los 23 (Fox, DirectKV)

10 familias/modelos revisados
├── 7 verified-primary
├── 2 verified-primary con licencia no-OSI/diferenciada (Gemma 3, Llama 4 Scout)
└── 1 unresolved (GLM-5.2)
```

## Pipeline de promoción

```text
FUENTE PRIMARIA
      ↓
IDENTIDAD / LICENCIA / ESTADO
      ↓
verified-primary
      ↓
LLMFIT → primera estimación de encaje
      ↓
RUNTIME + CUANTIZACIÓN
      ↓
BENCHMARK LEONES
      ↓
measured
      ↓
RECOMENDADOR
```

Los `archived` no se eliminan del conocimiento: se conservan para trazabilidad histórica. Los `unresolved` no generan recomendaciones ni registros canónicos verificados.

## Informe detallado

[`LOCAL-INFERENCE-2026-VERIFICATION.md`](LOCAL-INFERENCE-2026-VERIFICATION.md)

## Regla de promoción

- repositorio descubierto ≠ software recomendado;
- licencia declarada ≠ clasificación OSI automática;
- benchmark externo ≠ medición LEONES;
- estimación LLMFit ≠ rendimiento medido;
- claim del proyecto ≠ hecho independiente.
