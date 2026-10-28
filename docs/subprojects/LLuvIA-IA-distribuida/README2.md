# LLuvIA — IA distribuida especializada (README2)

**Estado:** propuesta de arquitectura / investigación; no desplegada ni validada físicamente.  
**Proyecto padre:** [LEONES](https://github.com/robertosantosx2/LEONES) (Local Ecosystem of Open Neural Expert Systems).  
**Nombre del subsistema:** **LLuvIA IA-distribuida**.  
**Documento base:** [README original](https://github.com/robertosantosx2/LEONES/blob/main/docs/subprojects/LLuvIA-IA-distribuida/README.md).  
**Este archivo (README2):** extensión analítica orientada a decisión de hardware, selección de modelos y coste-rendimiento.

> **Principio LEONES (inalterable):**  
> Toda cifra de rendimiento que aparece aquí es **ESTIMATED**. Solo una ejecución física autorizada sobre el hardware real produce **MEASURED**.  
> No se reutilizan resultados de otras máquinas como mediciones propias.  
> Ningún modelo, runtime o proveedor se instala sin selección explícita del usuario.

---

## 1. Resumen ejecutivo (alineado con el original)

LLuvIA ofrece un único punto de entrada (API compatible OpenAI + interfaz LEONES) mediante un **enrutador global** que clasifica la intención y dirige cada solicitud al especialista más adecuado.

La hipótesis central **no** es sumar la RAM de todos los nodos como memoria unificada.  
Es **distribuir servicios independientes por especialidad**, con:

- API común
- Colas y límites de concurrencia
- Observabilidad y fallback
- Aislamiento de fallos

Una petición normal se resuelve en un solo nodo. Solo los flujos multimodales o agentivos coordinan varios servicios.

### Principios que se preservan de LEONES

| Principio | Aplicación en LLuvIA |
|-----------|----------------------|
| Local-first | Sin dependencia obligatoria de cloud |
| Componentes reemplazables | Interfaces documentadas, runtimes intercambiables |
| ESTIMATED ≠ MEASURED | Toda tabla de tok/s o latencia es provisional hasta medición real |
| Selección humana | El usuario elige modelo y stack; el sistema solo recomienda |
| Procedencia | Se registra hardware, artefacto, runtime y fecha de cada prueba |

---

## 2. Arquitectura lógica (resumen del original + refinamiento)

```
Usuario / Web / API / LEONES
            │
            ▼
┌───────────────────────────────────────┐
│          ENRUTADOR GLOBAL             │
│  • Clasificación de intención         │
│  • Políticas, cuotas, fallback        │
│  • Selección de nodo                  │
│  • API unificada (OpenAI-compatible)  │
└───────────────────┬───────────────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
    ▼               ▼               ▼
 [Chat]        [Decisión]       [Código]
 [Idiomas]     [Matemáticas]    [Imagen/OCR]
 [Audio/ASR]   [TTS]            [Vídeo]
 [RAG / DB]
    │
    └───────────────┬───────────────┘
                    ▼
         Métricas · Trazas · Auditoría
```

### Responsabilidades del enrutador (sin cambios respecto al original)

1. Clasificar intención (conversación, código, razonamiento, traducción, cálculo, imagen/documento, audio, TTS, vídeo, búsqueda documental).
2. Seleccionar servicio según capacidad, idioma, disponibilidad, carga y política.
3. Validar entradas y limitar contexto, duración de media y concurrencia.
4. Aplicar fallback local.
5. Devolver respuesta uniforme registrando modelo/runtime.
6. No enviar datos a servicios externos salvo configuración explícita.

La primera versión puede basarse en reglas deterministas + metadatos. Un clasificador pequeño solo se añade si las pruebas lo justifican.

---

## 3. Especialidades, candidatos y análisis de rendimiento (ESTIMATED)

Los nombres de modelos son **candidatos de evaluación**. Antes de fijar cualquier versión se debe verificar:

- Repositorio oficial y commit/revisión
- Licencia
- Artefacto exacto (GGUF, etc.)
- Runtime CPU compatible
- Calidad e idioma en el conjunto de pruebas LEONES

### 3.1 Tabla de especialistas (base del README original + alternativas evaluadas)

| Servicio | Candidato prioritario | Alternativa sólida | Runtime orientativo | Observaciones de rendimiento (ESTIMATED) |
|----------|-----------------------|--------------------|---------------------|------------------------------------------|
| **Chat / texto** | Liquid AI LFM2.5-1.2B-Instruct | Qwen2.5-1.5B / Phi-3.5-mini | llama.cpp / TensorFold | 15–40 tok/s en CPU moderno (16 GB) |
| **Razonamiento / decisión** | LFM2.5-8B-A1B (MoE) o LFM2.5-1.2B-Thinking | Qwen2.5-3B / 7B en nodo 32 GB | llama.cpp | MoE reduce activación, pero los pesos completos ocupan espacio |
| **Código** | Qwen2.5-Coder-3B-Instruct | Qwen2.5-Coder-7B (nodo 32–64 GB) | llama.cpp | 3B es usable en 16 GB; 7B necesita más margen |
| **Idiomas / traducción** | LFM2.5-1.2B-Instruct | Qwen2.5-3B multilingüe | llama.cpp | Evaluar por pares de idiomas; no asumir calidad uniforme |
| **Matemáticas** | LFM2.5-1.2B-Thinking + SymPy | Qwen2.5-3B + Python | llama.cpp + intérprete | El LLM propone; SymPy verifica |
| **Imagen / documentos / OCR** | LFM2.5-VL-1.6B | PaddleOCR + VLM pequeño | runtime VL compatible | OCR dedicado + interpretación semántica separados |
| **Audio (ASR)** | Whisper.cpp (base/small) | LFM2.5-Audio-1.5B (experimental) | whisper.cpp | Español validado obligatorio |
| **Voz (TTS)** | Piper | Coqui / otros TTS locales | Piper | Servicio ligero, independiente del LLM |
| **Vídeo** | FFmpeg + muestreo de fotogramas + VLM | Nodo GPU para modelos más pesados | FFmpeg + cliente VL | No es comprensión temporal completa |
| **RAG / embeddings** | Multilingual-e5-small / bge-m3 + Qdrant | BM25 + reranker pequeño | sentence-transformers / Qdrant | Indexación y generación desacopladas |

**Enlaces oficiales de modelos Liquid AI (LFM):**
- Sitio: https://www.liquid.ai/
- Modelos: https://www.liquid.ai/models
- Hugging Face: https://huggingface.co/LiquidAI
- GitHub organización: https://github.com/Liquid4All
- Blog LFM3 (oct 2026): https://www.liquid.ai/blog/lfm3

### 3.2 Estimaciones orientativas de tokens/s (CPU, cuantización Q4_K / Q5_K)

| Modelo (aprox.) | RAM mínima práctica | tok/s (CPU moderno, 1 hilo–varios) | Notas |
|-----------------|---------------------|------------------------------------|-------|
| 1.2B–1.5B       | 4–6 GB libres      | 25–55 tok/s                       | Ideal para nodos Clase A |
| 3B              | 6–8 GB libres      | 12–30 tok/s                       | Buen equilibrio calidad/coste |
| 7–8B            | 10–14 GB libres    | 6–18 tok/s                        | Mejor en Clase B (32 GB) |
| MoE 8B (activos ~1–2B) | 10–16 GB     | 15–35 tok/s (depende de expertos) | Medir memoria real de los pesos |

> Estas cifras son **ESTIMATED**. Deben medirse con el mismo runtime, cuantización, longitud de contexto y hardware concreto. El cuello de botella real suele ser ancho de banda de memoria, no solo número de núcleos.

### 3.3 Objetivo de eficiencia: ~50 tok/s por euro de coste hardware (orientativo)

El criterio de diseño prioritario es maximizar **tokens por segundo por euro de inversión en hardware**, manteniendo calidad usable y aislamiento de servicios.

| Perfil de nodo | Coste orientativo (2026, mercado de segunda mano / entry) | tok/s esperados (chat 1.5–3B) | tok/s por € (orden de magnitud) |
|----------------|----------------------------------------------------------|-------------------------------|---------------------------------|
| Clase A (16 GB, CPU decente) | 180–280 € | 20–40 | ~0.10–0.18 |
| Clase B (32 GB) | 280–420 € | 30–55 (modelos mayores) | ~0.10–0.15 |
| Clase C (32 GB + GPU 12–16 GB) | 450–700 € | 80–200+ (depende de modelo) | Variable; solo justifica si la carga es visual/generativa |

**Conclusión de diseño:**  
Para chat, código ligero, idiomas y RAG, **varios nodos Clase A** suelen dar mejor ratio tok/s/€ que un solo nodo caro. La GPU solo se justifica cuando las mediciones demuestran que el cuello de botella es computación visual o generación, no memoria/CPU.

---

## 4. Clases de hardware (sin cambios de fondo respecto al original)

### Clase A — nodo base CPU (recomendado como mayoría)

- Ubuntu x86-64
- 16 GB RAM instalados (recordar que no todo está libre)
- CPU con AVX2 (deseable)
- SSD ≥ 512 GB (1 TB preferible)
- Ethernet ≥ 1 GbE (2,5 GbE recomendable)
- Sin GPU

**Usos:** chat, idiomas, embeddings, RAG, TTS, ASR ligero, coordinación.

### Clase B — nodo CPU reforzado

- 32–64 GB RAM
- Más núcleos y buen ancho de banda de memoria
- NVMe ≥ 1 TB

**Usos:** código 7B, razonamiento más pesado, contextos largos, varios servicios en el mismo host.

### Clase C — nodo acelerado (opcional)

- 32–64 GB RAM + GPU NVIDIA 12–24 GB VRAM
- Drivers y runtime fijados

**Usos:** visión exigente, generación de imágenes, cargas que realmente se beneficien de CUDA. Debe existir fallback CPU.

---

## 5. Tamaño de despliegue y topología de referencia

| Perfil | Nodos | Comentario |
|--------|------:|------------|
| Prototipo mínimo | 4–5 | Agrupar servicios compatibles |
| Mínimo práctico | 6 | Separación razonable |
| Recomendado | 8 | Buen aislamiento + 1 nodo reforzado |
| Completo | 10 | Un servicio principal por nodo + margen |

**Topología orientativa de 10 nodos (igual que el original):**

1. Gateway / enrutador  
2. Chat  
3. Idiomas  
4. Matemáticas  
5. RAG / embeddings  
6. TTS  
7. Audio / ASR  
8. Vídeo / FFmpeg  
9. Código (preferible Clase B)  
10. Decisión / visión (Clase B o C)

El gateway puede residir en un nodo existente. Los servicios pueden reagruparse según mediciones reales de RAM, latencia y concurrencia.

---

## 6. Stack de software a evaluar

| Capa | Candidatos | Notas |
|------|------------|-------|
| Gateway | Servicio propio ligero o proxy OpenAI-compatible + Nginx/Traefik | Health checks, cuotas, fallback |
| Texto | llama.cpp, TensorFold, otros tras verificación | Fijar versión y artefacto |
| Visión | Runtime del VLM + OCR dedicado (PaddleOCR, etc.) | Separar OCR de interpretación |
| ASR | Whisper.cpp (español validado) | — |
| TTS | Piper | Ligero e independiente |
| Vídeo | FFmpeg + muestreo de fotogramas | — |
| RAG | Qdrant + embeddings multilingües | BM25/reranker opcional |
| Observabilidad | Latencia, TTFT, tok/s, RAM pico, CPU, cola, fallos | Logs sin secretos por defecto |

No interferir con instalaciones existentes de LEONES / ODS / otros componentes. Prototipar en puertos y directorios aislados.

---

## 7. Plan de validación (LEONES-compliant)

### Fase 0 — Inventario
- Hardware real de cada máquina (RAM libre, CPU, disco, red, SO)
- Licencias y artefactos exactos
- Toda previsión marcada como **ESTIMATED**

### Fase 1 — Especialista aislado
Por cada modelo registrar:
- Artefacto, cuantización, runtime y versión
- RAM máxima, CPU, tamaño de contexto
- TTFT, tok/s o tiempo de tarea
- Calidad e idioma en el set de pruebas LEONES
- Comportamiento bajo concurrencia

### Fase 2 — Enrutador
- Clasificación de intención
- Latencia añadida
- Aislamiento de datos
- Timeout, cancelación, fallback, mensajes de error claros

### Fase 3 — Carga combinada
- Varias especialidades en paralelo
- Detección de contención (RAM, CPU, disco, red)
- Recuperación ante caída de nodo

### Fase 4 — Decisión de escalado
Solo añadir RAM o GPU cuando las **métricas** identifiquen el cuello de botella. Una GPU no soluciona un problema de memoria, red o disco.

---

## 8. Proyectos y sistemas relacionados (con enlaces)

| Proyecto | Enfoque | Enlaces | Relación con LLuvIA |
|----------|---------|---------|---------------------|
| **llm-d** (CNCF Sandbox) | Inferencia distribuida a escala de clúster (vLLM/SGLang, Kubernetes-native) | [llm-d.ai](https://llm-d.ai/) · [GitHub](https://github.com/llm-d/llm-d) · [CNCF](https://www.cncf.io/projects/llm-d/) | Más orientado a datacenter; útil como referencia de enrutado, cache-aware routing y métricas |
| **exo** | Cluster doméstico de dispositivos (Apple Silicon + otros) | [GitHub exo-explore/exo](https://github.com/exo-explore/exo) | Compartir memoria entre máquinas; LLuvIA prefiere especialización por servicio |
| **Mesh-LLM** | Inferencia distribuida GGUF sobre QUIC/iroh | [GitHub Mesh-LLM/mesh-llm](https://github.com/Mesh-LLM/mesh-llm) | Alternativa P2P doméstica |
| **Petals** | Inferencia colaborativa / bit-torrent de capas | [petals.dev](https://petals.dev/) · [GitHub](https://github.com/bigscience-workshop/petals) | Diferente filosofía (compartir capas vs. servicios independientes) |
| **Distributed Llama** | Tensor parallelism en casa | [GitHub b4rtaz/distributed-llama](https://github.com/b4rtaz/distributed-llama) | Útil para modelos grandes en varios nodos |
| **LEONES / ODS / Magnitude** | Ecosistema local con criterio | [LEONES](https://github.com/robertosantosx2/LEONES) · [robertosantosx2.github.io/LEONES](https://robertosantosx2.github.io/LEONES/) | Padre y componentes de referencia de LLuvIA |

LLuvIA se diferencia por:

1. Especialización por dominio (no un único modelo grande partido).
2. Nodos modestos (16 GB) como unidad base.
3. Integración nativa con los principios de medición y selección humana de LEONES.

---

## 9. Perfiles X (Twitter) relevantes que hablan del tema

Perfiles y cuentas que publican o discuten activamente sobre inferencia distribuida, modelos on-device/edge, llm-d, Liquid AI / LFM, clusters domésticos o temas afines (octubre 2026):

| Perfil | Handle | Temática principal | Notas |
|--------|--------|--------------------|-------|
| Liquid AI | [@LiquidAI](https://x.com/LiquidAI) | Modelos LFM, LFM3, on-device, RIPL | Cuenta oficial de la compañía cuyos modelos son candidatos prioritarios en LLuvIA |
| llm-d | [@llm_d_ai](https://x.com/llm_d_ai) o búsqueda "llm-d" | Distributed inference, CNCF, Kubernetes | Proyecto CNCF de referencia para enrutado a escala |
| exo labs | [@exolabs](https://x.com/exolabs) | Cluster doméstico multi-dispositivo | Mencionado frecuentemente en discusiones de P2P/home clusters |
| Saim Safdar | [@cloudnativeboy](https://x.com/cloudnativeboy) | Cloud Native + llm-d, vLLM, K8s inference | Hilos detallados sobre la pila de serving (GPU → vLLM → llm-d) |
| Viviana Márquez | [@vivmarquez](https://x.com/vivmarquez) | Developer Relations @ Liquid AI | Respuestas técnicas sobre LFM3, idiomas, despliegue |
| Oliver Prompts | [@oliviscusAI](https://x.com/oliviscusAI) | Mesh LLM, distributed GGUF | Hilos sobre repartir modelos 70B+ entre dispositivos |
| Grok / xAI | [@grok](https://x.com/grok) | Respuestas técnicas sobre Mesh-LLM y similares | Útil para clarificaciones técnicas rápidas |

**Otras menciones frecuentes en conversaciones recientes:**
- Cuentas que discuten **Mesh-LLM**, **exo**, **Distributed Llama** y **Petals** en el contexto de “run 70B on spare hardware”.
- Desarrolladores de vLLM / SGLang que hablan de prefill/decode disaggregation y cache-aware routing (temas que llm-d formaliza).

> Recomendación: seguir [@LiquidAI](https://x.com/LiquidAI) y las cuentas de llm-d / exo para actualizaciones de modelos y de infraestructura distribuida. Las cifras de rendimiento en X deben tratarse siempre como **ESTIMATED** hasta medición propia.

---

## 10. Primeros hitos recomendados

1. **API común + enrutador determinista** funcionando con 2–3 especialistas (chat + código + RAG).
2. Mediciones reproducibles (RAM, TTFT, tok/s) en al menos un nodo Clase A real.
3. Fallback local y recuperación ante caída de un servicio.
4. Documentación de cada modelo con ficha LEONES (artefacto, licencia, fecha, hardware, resultados **MEASURED**).

El objetivo del primer hito **no** es desplegar diez modelos a la vez, sino demostrar:

- API unificada
- Enrutamiento correcto
- Fallback local
- Evidencia medible y reproducible

---

## 11. Referencias internas LEONES y enlaces clave

- README original LLuvIA: https://github.com/robertosantosx2/LEONES/blob/main/docs/subprojects/LLuvIA-IA-distribuida/README.md
- Repositorio LEONES: https://github.com/robertosantosx2/LEONES
- Sitio web LEONES: https://robertosantosx2.github.io/LEONES/
- Liquid AI: https://www.liquid.ai/ · https://huggingface.co/LiquidAI
- llm-d: https://llm-d.ai/ · https://github.com/llm-d/llm-d · https://www.cncf.io/projects/llm-d/
- Principios y vocabulario LEONES: `docs/ARCHITECTURE.md`, `docs/PILLARS.md` (dentro del repo)
- Cadena ESTIMATED → MEASURED: documentación RC4 y contratos de medición

---

*Documento generado como extensión analítica del README original de LLuvIA dentro del ecosistema LEONES.  
Todas las cifras de rendimiento son ESTIMATED hasta validación física en el hardware objetivo.  
Última actualización de enlaces y perfiles X: 2026-10-28.*
