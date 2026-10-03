# Investigación: IA Local en Hardware de Consumo + Fine-Tuning

**Fecha**: 3 de octubre de 2026  
**Repo**: LEONES (Libre Open Agent Stack)  
**Origen**: Análisis de tuits de @Davidstout / webAI + PDF de Andrej Karpathy + búsqueda de perfiles similares en X.

---

## 1. Resumen ejecutivo

La frontera interesante de los LLMs se está moviendo **hacia abajo**: modelos pequeños (1–4B) bien post-entrenados que corren en hardware de consumo (CPU, 4 GB VRAM, laptops, incluso teléfonos) superan a modelos mucho más grandes en dominios específicos (lógica formal, razonamiento estructurado).

**Tesis clave**:
- “Everyone’s renting frontier models for jobs a 3B model could do. Small models are the future.” — Andrej Karpathy
- “AI is entering a post-training era. The advantage will belong to companies with the best pipelines.” — David Stout (webAI)

El secreto no es el tamaño, sino el **pipeline de post-training** (LoRA → fusion → WiSE-FT → GRPO/RL) + datos limpios + cuantización GGUF.

---

## 2. Caso de estudio: TwIL-LM3-Pro (webAI)

### 2.1 Datos técnicos

| Propiedad              | Valor                                      |
|------------------------|--------------------------------------------|
| Parámetros             | 3.66B                                      |
| Base                   | ibm-granite/granite-4.2-3b                 |
| Arquitectura           | Granite decoder-only (40 layers, hidden 2560) |
| Contexto               | 131.072 tokens                             |
| Q4_K_M                 | ≈ 2.09 GiB → corre en CPU o 4 GB VRAM      |
| Licencia               | webAI Non-Commercial License v1.0          |
| HF                     | [webAI-Official/TwIL-LM3-Pro](https://huggingface.co/webAI-Official/TwIL-LM3-Pro) |

### 2.2 Pipeline de post-training (el verdadero diferencial)

1. **LoRA SFT** sobre datos de lógica formal  
2. **Checkpoint fusion**  
3. **WiSE-FT** (Weight-space Interpolation) → gana dominio sin perder capacidad general  
4. **Entropy-weighted GRPO / MGPO** (RL con verificador programático)

**Resultado**: +28–31 % relativo en lógica formal (macro gate 0.431 → 0.554) mientras mantiene held-out casi intacto (10-dataset macro ≈ 0.790).

### 2.3 Benchmarks destacados

- Formal logic headline: líder entre small models  
  - +35 % vs VibeThinker-3B  
  - +24 % vs Qwen3.5-4B  
  - +47 % vs LFM2.5-8B-A1B  
- BBH logic subset: **95.4 %** (vs 61.1 % VibeThinker)  
- SVAMP: **95 %**  
- MuSR: **64.1 %**

Especializado en: entailment, rule induction, Lean formalization, semantic parsing.

---

## 3. Visión de Andrej Karpathy (PDF “Small Language Model Engineering 2026”)

### Tesis central
Un modelo pequeño entrenado con datos limpios puede lograr capacidades similares a uno grande entrenado en internet ruidoso, porque “limpia el ruido” y libera capacidad de pesos para razonamiento real.

### nanochat (referencia práctica)
- Pipeline completo en ~8.300 líneas de código  
- Entrena un clone funcional de ChatGPT en **3 h 51 min** en 8× H100 por **≈ $92**  
- Etapas: Pretrain (FineWeb-EDU) → Midtrain (chat + tools) → SFT → RL (opcional)  
- Un solo “dial” de tamaño (depth) controla el resto  
- Objetivo: “cognitive core” — razonamiento + tools, no conocimiento enciclopédico

> “A frontier model is a rented capability… A model you trained is a fixed asset.”

---

## 4. Perfiles de X relevantes (IA Local + Fine-Tune)

Perfiles que hablan activamente de **IA local en hardware de consumo** y lo logran (o impulsan) mediante **fine-tuning**:

| Perfil                    | Enfoque principal                          | Por qué es relevante |
|---------------------------|--------------------------------------------|----------------------|
| [@UnslothAI](https://x.com/UnslothAI) | Fine-tuning ultra-eficiente + app local   | LoRA/QLoRA optimizado para 3–12 GB VRAM. Entrenar y desplegar localmente. |
| [@maximelabonne](https://x.com/maximelabonne) | Post-training & merges                    | Head of Post-Training @ Liquid AI. Guías y GGUF optimizados para local. |
| [@Davidstout](https://x.com/Davidstout) / [@thewebAI](https://x.com/thewebAI) | Modelos 3–4B + post-training avanzado    | TwIL-LM3-Pro: LoRA + WiSE-FT + GRPO para lógica formal on-device. |
| [@ggerganov](https://x.com/ggerganov) | llama.cpp + GGUF                          | Backbone del ecosistema local. Hace posible que los fine-tunes corran en consumer hardware. |
| [@lmstudio](https://x.com/lmstudio)   | Interfaz fácil para modelos locales       | Facilita correr GGUF (incluyendo fine-tunes) en laptops. |
| [@ollama](https://x.com/ollama)       | Ejecución local simple                    | Un comando para correr modelos fine-tuned. |
| [@NousResearch](https://x.com/NousResearch) | Fine-tunes de alta calidad (Hermes, etc.) | Modelos pensados para correr bien localmente. |

**Otros de interés**:
- Cuentas que publican abliteration + LoRA de Qwen (uncensored que corren en 5–6 GB)
- @t_mux / @ViggleAI (fine-tunes de imagen/video en GGUF/LoRA)

### Recomendación de seguimiento prioritario
1. @UnslothAI  
2. @maximelabonne  
3. @Davidstout / @thewebAI  
4. @ggerganov  
5. @lmstudio

---

## 5. Claves de selección de modelos y técnicas (para LEONES)

### Criterios de decisión

1. **Tarea dominante**  
   - Lógica formal / reglas / compliance → TwIL-LM3-Pro o equivalentes especializados  
   - Razonamiento general + chat → 7–8B o frontier según presupuesto  
   - On-device / privacidad → ≤ 4B + GGUF Q4/Q5

2. **Restricciones de hardware**  
   - CPU / 4 GB VRAM → Q4 ≈ 2 GiB es el sweet spot actual  
   - Latencia crítica → modelos con generaciones cortas + alta throughput

3. **Trade-off in-domain vs held-out**  
   - Usar **WiSE-FT / interpolación de pesos** cuando se quiere especializar sin colapsar generalización

4. **Costo total de ownership**  
   - API frontier = coste variable + riesgo  
   - Modelo propio pequeño = coste fijo de entrenamiento + inferencia casi gratis

### Técnicas de post-training recomendadas (orden práctico)

| Técnica                  | Cuándo usarla                              | Notas |
|--------------------------|--------------------------------------------|-------|
| LoRA / PEFT SFT          | Casi siempre como primera etapa            | Bajo coste, alto control |
| Checkpoint fusion / merging | Cuando hay varios buenos checkpoints     | Combina fortalezas |
| WiSE-FT                  | Especialización sin perder generalización  | Clave en TwIL-LM3-Pro |
| GRPO / MGPO (RL)         | Tareas verificables (lógica, math, code)   | Entropy-weighted ayuda estabilidad |
| Datos limpios domain-matched | Siempre                               | Más importante que el tamaño en muchos casos |

### Checklist rápida

- [ ] ¿La tarea es mayoritariamente lógica formal / reglas? → Probar TwIL-LM3-Pro primero  
- [ ] ¿Necesito offline / hardware modestísimo? → GGUF Q4 de ≤ 4B  
- [ ] ¿Tengo datos de dominio limpios y verificables? → Invertir en SFT + RL  
- [ ] ¿Me importa conservar capacidad general? → Incluir WiSE-FT  
- [ ] ¿Cuántas de mis llamadas realmente necesitan un 70B+? → Medirlo  
- [ ] ¿Puedo entrenar yo mismo? → Preferir pipelines transparentes (Unsloth, nanochat-style)

---

## 6. Limitaciones y riesgos

- TwIL-LM3-Pro **no** es un asistente general con safety/preference tuning completo  
- Licencia no-comercial de webAI  
- Benchmarks de lógica formal son del harness propio de webAI → validar en datos propios  
- Karpathy muestra scores bajos en MMLU/GSM8K de nanochat porque el objetivo no es competir con frontier, sino demostrar utilidad controlable y barata

---

## 7. Fuentes primarias

- Tuit @Davidstout: https://x.com/Davidstout/status/2105367134876365135  
- Model card: https://huggingface.co/webAI-Official/TwIL-LM3-Pro  
- Blog webAI: https://www.webai.com/blog/meet-twil-lm3-pro-webai-s-next-step-in-local-reasoning  
- PDF Karpathy (compartido en hilo de @0xCodez): “Andrej Karpathy – Building Small Language Models…”  
- Perfiles X listados en sección 4

---

## 8. Implicaciones para LEONES

Este material alimenta directamente:

- Selección de modelos para el runtime A01 / agentes locales  
- Recomendador de atlas (priorizar small + post-trained sobre frontier rentado)  
- Pipelines de post-training que se puedan reproducir en hardware de consumo  
- Criterios de “local-first” y ownership de los modelos

**Próximos pasos sugeridos**:
1. Evaluar TwIL-LM3-Pro (Q4) en los benchmarks de runtime de LEONES  
2. Probar Unsloth para fine-tunes propios de agentes  
3. Incorporar WiSE-FT / merging en el pipeline de post-training del stack  
4. Actualizar el catálogo de atlas con estos perfiles y modelos

---

*Documento generado a partir de análisis de X + fuentes públicas · Octubre 2026*
