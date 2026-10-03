# Investigación: IA Local en Hardware de Consumo + Fine-Tuning

**Fecha**: 3 de octubre de 2026  
**Repo**: LEONES (Libre Open Agent Stack)  
**Origen**: Análisis de tuits de @Davidstout / webAI + PDF de Andrej Karpathy + búsqueda de perfiles similares en X + benchmarks LoRA actualizados.

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

## 5. Benchmarks de LoRA (análisis actualizado 2025-2026)

### 5.1 Resumen ejecutivo de LoRA

LoRA sigue siendo el método PEFT dominante. Los benchmarks más recientes confirman que, **cuando se configura bien** (rank, learning rate, batch size, capas a las que se aplica), recupera entre el **95-99 %** del rendimiento de Full Fine-Tuning (FullFT) en la mayoría de tareas de SFT e incluso en RL, mientras entrena solo el 0.1-3 % de los parámetros y reduce drásticamente VRAM y tiempo.

El gap con FullFT aparece principalmente cuando:
- El dataset es muy grande (> 20-50k ejemplos de alta calidad).
- Se necesita actualizar conocimiento “duro” del modelo base.
- El rank es demasiado bajo (r ≤ 4-8 en tareas de alta capacidad).

### 5.2 Rendimiento vs Full Fine-Tuning

| Fuente / Estudio | Hallazgo clave | Recuperación de FullFT |
|------------------|----------------|------------------------|
| Thinking Machines Lab (2025) | LoRA iguala FullFT en sample efficiency en SFT de tamaño pequeño-mediano e incluso en RL (ranks tan bajos como 1) | ~100 % en datasets no demasiado grandes |
| Post-Training Science (2026) | LoRA recupera mediana del **98 %** de la mejora de FullFT mientras entrena 3-13 % de parámetros | 98 % |
| ACL Findings 2025 (Rank Trade-offs) | En razonamiento LoRA a menudo **supera** a FullFT en ranks intermedios (16-64) | Competitivo o superior |
| Baseten Practical LoRA Research | Rank ≥ 8 iguala FullFT hasta ~30k ejemplos; ranks 1-4 saturan antes | Casi 100 % a partir de r=8 |

**Conclusión práctica**: para la mayoría de fine-tunes de dominio (instruction, razonamiento, agentes, lógica formal) LoRA es suficiente y preferible.

### 5.3 Efecto del Rank (r)

- **r = 1-4**: suficiente para tareas muy simples o datasets pequeños. Capacidad limitada.
- **r = 8-16**: sweet spot más usado (buen equilibrio calidad/coste).
- **r = 32-64**: óptimo en la mayoría de estudios recientes. A partir de ~64 el retorno decrece fuerte.
- **r ≥ 128**: casi nunca compensa el coste extra.

Estudios de 2025-2026 muestran que α = 2×r o α fijo en 16-32 suele funcionar mejor que α = r.

### 5.4 LoRA vs variantes (QLoRA, DoRA, etc.)

| Método | VRAM | Velocidad | Calidad relativa | Cuándo usarlo |
|--------|------|-----------|------------------|---------------|
| **LoRA** | Media | Más rápido | Referencia | Cuando el modelo cabe en BF16 |
| **QLoRA** | Muy baja (~0.4×) | Más lento (dequant) | Casi igual a LoRA | Cuando no cabe en VRAM (7B+ en 12-24 GB) |
| **DoRA** | Similar a LoRA | Un poco más lento | Mejor en datasets pequeños (<5-10k) | Preferido por muchos en 2026 para datasets medianos |
| **LoRA+** | Similar | Similar | Mejor en energía/memoria en SLMs | On-device / consumer GPUs |
| Variantes (PiSSA, AdaLoRA, SDS-LoRA…) | Variable | Variable | A veces mejor, a veces no | Solo si el batch size y LR están bien tuneados |

**Nota importante (2026)**: muchos papers de variantes muestran ganancias que desaparecen cuando se sintoniza correctamente el **batch size** de vanilla LoRA. El batch size es un hiperparámetro de primer orden.

### 5.5 Memoria y Hardware de consumo (muy relevante para LEONES)

Reglas prácticas 2026:

| Modelo | QLoRA (r=16) | LoRA (BF16) | Full FT |
|--------|--------------|-------------|----------------|
| 1-3B   | 4-8 GB      | 8-12 GB    | 16-24 GB |
| 7-8B   | 6-10 GB     | 16-24 GB   | 48 GB+   |
| 13-14B | 10-16 GB    | 24-40 GB   | Multi-GPU |
| 32B    | ~20 GB      | 48 GB+     | Cluster  |

QLoRA permite fine-tunear 7B-13B cómodamente en una RTX 4090/5090 o incluso en 12-16 GB con offloading.

### 5.6 Caso concreto: TwIL-LM3-Pro

webAI usó **LoRA SFT** como primera etapa del pipeline (junto con checkpoint fusion + WiSE-FT + GRPO).  
Resultado: +28-31 % relativo en lógica formal manteniendo casi intacta la capacidad held-out.  
Esto confirma que LoRA + técnicas de interpolación (WiSE-FT) es una combinación extremadamente efectiva para especialización sin catástrofe de olvido.

### 5.7 Recomendaciones prácticas (2026)

1. **Default actual**: DoRA o LoRA con **r=16** (o r=32 si tienes VRAM) + α=32.
2. Learning rate de LoRA suele ser ~10-33× más alto que FullFT (óptimo frecuente ~1e-3).
3. Aplica LoRA a **todas las matrices** (incluyendo MLP), no solo atención.
4. Usa QLoRA solo cuando el modelo no cabe en BF16.
5. Siempre mide **in-domain + held-out** (o usa WiSE-FT si el olvido es problema).
6. Batch size importa más de lo que la mayoría de papers reportan.

### 5.8 Limitaciones conocidas de LoRA

- Capacidad limitada en datasets muy grandes o actualizaciones de conocimiento factual profundo.
- Puede introducir “intruder dimensions” que causan olvido (se mitiga con ranks moderados y α adecuados).
- En RL de razonamiento muy largo a veces necesita ranks más altos o técnicas complementarias.

---

## 6. Claves de selección de modelos y técnicas (para LEONES)

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

## 7. Limitaciones y riesgos

- TwIL-LM3-Pro **no** es un asistente general con safety/preference tuning completo  
- Licencia no-comercial de webAI  
- Benchmarks de lógica formal son del harness propio de webAI → validar en datos propios  
- Karpathy muestra scores bajos en MMLU/GSM8K de nanochat porque el objetivo no es competir con frontier, sino demostrar utilidad controlable y barata

---

## 8. Fuentes primarias

- Tuit @Davidstout: https://x.com/Davidstout/status/2105367134876365135  
- Model card: https://huggingface.co/webAI-Official/TwIL-LM3-Pro  
- Blog webAI: https://www.webai.com/blog/meet-twil-lm3-pro-webai-s-next-step-in-local-reasoning  
- PDF Karpathy (compartido en hilo de @0xCodez): “Andrej Karpathy – Building Small Language Models…”  
- Perfiles X listados en sección 4  
- Benchmarks LoRA: Thinking Machines Lab (2025), Post-Training Science (2026), ACL Findings 2025, Baseten Practical LoRA Research, papers arXiv 2025-2026 sobre rank trade-offs, DoRA, QLoRA y batch-size bias.

---

## 9. Implicaciones para LEONES

Este material alimenta directamente:

- Selección de modelos para el runtime A01 / agentes locales  
- Recomendador de atlas (priorizar small + post-trained sobre frontier rentado)  
- Pipelines de post-training que se puedan reproducir en hardware de consumo  
- Criterios de “local-first” y ownership de los modelos  
- Decisiones de rank, α, batch size y cuándo usar QLoRA vs LoRA vs DoRA

**Próximos pasos sugeridos**:
1. Evaluar TwIL-LM3-Pro (Q4) en los benchmarks de runtime de LEONES  
2. Probar Unsloth para fine-tunes propios de agentes (r=16 o 32 + α=32)  
3. Incorporar WiSE-FT / merging en el pipeline de post-training del stack  
4. Actualizar el catálogo de atlas con estos perfiles y modelos  
5. Definir defaults de LoRA/DoRA/QLoRA según VRAM disponible en el runtime

---

*Documento generado a partir de análisis de X + fuentes públicas + benchmarks LoRA 2025-2026 · Octubre 2026*
