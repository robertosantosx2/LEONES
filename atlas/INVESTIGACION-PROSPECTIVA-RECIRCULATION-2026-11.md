# Investigación Prospectiva: Recirculation (Mozer et al., 2026)

**Fecha de archivo:** 18 de noviembre de 2026  
**Origen de la solicitud:** Análisis del post de X @HowToPrompt__ (status/2123076653689766052) + búsqueda de discusiones y reproducciones.  
**Paper principal:** [arXiv:2608.17981](https://arxiv.org/abs/2608.17981) — *Recirculation*  
**Autores:** Michael C. Mozer, Shoaib Ahmed Siddiqui, Danny Sawyer, Sunny Sanyal, Rosanne Liu (Google DeepMind + University of Texas at Austin)  
**Versión analizada:** v3 (28 Sep 2026)

---

## Resumen ejecutivo

Técnica de **inferencia** (training-free) que convierte un transformer feedforward estándar en un sistema dinámico al “filtrar” (leak) una fracción normalizada de las activaciones de una capa profunda hacia una capa superficial en el siguiente paso de secuencia.

- **Sin modificar pesos** del modelo original.
- Casi cero latencia adicional en la fase de **generación** (los stacks pueden correr en paralelo).
- Coste extra principalmente en **prefill** (procesamiento serial por token).
- Resultados destacados en familia Gemma3 (1B/4B/12B):
  - Reducción de perplexity ~8,5 % (básica) hasta ~23 % (adaptativa).
  - +21 % de precisión relativa en GSM8k.
  - Mejoras consistentes en otras tareas de generación y razonamiento.

La idea clave es que la inteligencia de seguimiento de estado (belief-state tracking) ya está latente en los pesos; solo hace falta un mecanismo de feedback temporal para explotarla. Se distingue de Chain-of-Thought, de looping de profundidad tradicional y del entrenamiento de transformers recurrentes.

---

## Mecánica (resumen técnico)

1. En cada paso de secuencia, después del forward pass normal, se toma la activación de una capa *source* (profunda).
2. Se normaliza y se “filtra” una fracción α hacia una capa *destination* (superficial) del siguiente token.
3. El residual stream permite esta operación de forma natural por su alineación lineal.
4. Variante **adaptativa**: hiperparámetros ligeros (o una red externa pequeña) ajustan cuánto recircular, manteniendo los pesos del LLM congelados.

El paper muestra mapas de calor source→destination con regiones robustas de mejora de perplexity en varias familias de modelos (Gemma3, Ministral3, Qwen3, Pythia, Phi2, etc.).

---

## Fuentes primarias y secundarias

| Tipo | Enlace / Referencia |
|------|---------------------|
| Paper | https://arxiv.org/abs/2608.17981 |
| HTML experimental | https://arxiv.org/html/2608.17981 |
| Resumen alphaXiv | https://www.alphaxiv.org/abs/2608.17981 |
| ArXivIQ (análisis) | https://arxiviq.substack.com/p/recirculation |
| Emergent Mind | https://www.emergentmind.com/papers/2608.17981 |
| The Ground Truth (walkthrough) | https://thegroundtruth.vercel.app/paper/recirculation |
| CryptoBriefing | https://cryptobriefing.com/deepmind-recirculation-transformer-context/ |

---

## Discusiones y cobertura en X (x.com)

- Post original analizado: [@HowToPrompt__](https://x.com/HowToPrompt__/status/2123076653689766052) (18 Nov 2026) — divulgación centrada en el “+21 % más inteligentes sin reentrenar”.
- Anuncio del coautor [@mc_mozer](https://x.com/mc_mozer).
- Threads técnicos de [@che_shr_cat](https://x.com/che_shr_cat) (Grigory Sapunov) con breakdown y trade-off prefill vs. ganancia GSM8k.
- Menciones de [@askalphaxiv](https://x.com/askalphaxiv), [@s_scardapane](https://x.com/s_scardapane), [@qubitium](https://x.com/qubitium) (enlace a reproducción), [@agopal42](https://x.com/agopal42), [@Keyuciallo](https://x.com/Keyuciallo).
- Comparaciones con AttnRes / residual feedback y otras ideas de looping.

La conversación destaca el carácter “cheating” de la técnica, utilidad para modelos pequeños y el coste de prefill serial.

---

## Reddit

- Hilo relevante en **r/singularity** (≈26 ago 2026): “A recirculation fix for running context”. Explica la mecánica, los números y da tips de implementación práctica (interceptar residual stream, normalizar y sumar tensor cacheado). Interés explícito para pipelines de inferencia local.
- Menciones laterales en contextos de recursive/looped reasoning (LocalLLaMA y similares), pero sin hilos masivos dedicados únicamente a este paper.

---

## Hugging Face

No se encontró Space, modelo o dataset oficial de alta visibilidad directamente del paper. En la página de arXiv aparecen enlaces genéricos a Hugging Face, pero no hay implementación canónica popular en el ecosistema HF al momento del archivo. Existen papers relacionados en Daily Papers sobre looped transformers, residual attention loops y latent refinement, pero no son el mismo método.

---

## GitHub y reproducciones

### Reproducción independiente principal
- **[ModelCloud/Recirculation](https://github.com/ModelCloud/Recirculation)** (Qubitium / ModelCloud)  
  - Best-effort independent reproduction.  
  - Evaluaciones en Gemma 3 1B Instruct (FP16) con pares de capas y α del paper.  
  - Resultados modestos pero en la dirección correcta en GSM8K Platinum, MMLU, etc.  
  - Documenta comandos, limitaciones de backend y artefactos.  
  - ~9 stars / 4 forks (a la fecha de captura).

alphaXiv también ofrece tooling de “Autoresearch / reproduce-paper” orientado a este trabajo.

### Proyectos / papers relacionados (espíritu similar, no idénticos)
- Técnicas de **looped transformers** (recurrencia de profundidad con pesos compartidos).
- ARLoop, Loopback Transformer, Hyperloop, Ouro/LoopLM.
- Métodos de latent refinement o recursive reasoning (p. ej. TRM de Samsung).
- Ideas de residual attention o feedback oculto.

---

## Implicaciones para LEONES / Atlas

- Técnica **training-free** y de bajo coste en generación → candidata a exploración en runtimes locales (llama.cpp, vLLM, sglang, etc.) si se implementa el hook de residual stream.
- Especialmente interesante para modelos pequeños o de recursos limitados: permite “pensar más profundo” sin aumentar parámetros.
- Trade-off claro: prefill serial puede ser costoso en contextos muy largos.
- Posible línea de experimentación futura: integrar recirculation como opción de runtime en el stack de LEONES o como post-procesamiento de capas en pipelines de agentes.

---

## Estado del arte al 18 Nov 2026

- Paper maduro (v3 con experimentos adicionales).
- Reproducción independiente disponible y funcional.
- Cobertura moderada en X y Reddit; aún no es un estándar de facto en librerías de inferencia mainstream.
- Valor prospectivo alto para sistemas offline / locales y para sacar más rendimiento de modelos ya entrenados sin reentrenamiento.

---

**Archivado en el Atlas de conocimiento de LEONES (Libre Open Agent Stack).**  
Fuente de la conversación original: análisis del post de X + búsquedas cruzadas en arXiv, X, Reddit, GitHub y Hugging Face.
