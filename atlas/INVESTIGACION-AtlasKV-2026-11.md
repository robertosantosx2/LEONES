# Investigación: AtlasKV — Augmenting LLMs with Billion-Scale Knowledge Graphs in 20GB VRAM

**Fecha**: 19 de noviembre de 2026  
**Repo**: LEONES (Libre Open Agent Stack)  
**Origen**: Tuit de @HowToPrompt__ (https://x.com/HowToPrompt__/status/2123302413583135028) + paper arXiv:2510.17934 + repo oficial HKUST-KnowComp/AtlasKV.  
**Estado del paper**: Aceptado en **ICLR 2026**. Versión v2 (13 abr 2026).

---

## 1. Resumen ejecutivo

**AtlasKV** propone un paradigma *paramétrico* de integración de conocimiento que hace que el pipeline clásico de RAG (vector DB + retrieval + long context) quede obsoleto para knowledge graphs de gran escala.

### Afirmaciones centrales (paper + tuit)

- Integrar **1.000 millones de triples** de knowledge graph directamente en el mecanismo de atención de un LLM.
- Coste de VRAM en inferencia: **< 20 GB**.
- Complejidad sub-lineal en tiempo y memoria (gracias a HiKVP).
- **Cero** retrievers externos, **cero** contexto largo inflado, **cero** reentrenamiento al añadir conocimiento nuevo.
- Mantiene fuerte *knowledge grounding* y generalización usando la atención inherente del LLM.

En palabras del tuit:  
> “RAG is officially cooked. […] no vector DB, no Pinecone bill, no chunking nightmares.”

Esto es extremadamente relevante para LEONES: el stack local ya contempla RAG (Qdrant en ODS) y busca minimizar dependencias externas, latencia y coste de memoria en hardware de consumo.

---

## 2. Problema que resuelve

RAG (paradigma no-paramétrico) tiene costes crecientes con la escala:

| Problema RAG a gran escala | Consecuencia |
|----------------------------|--------------|
| Búsqueda externa (ANN)     | Latencia de inferencia |
| Contexto recuperado largo  | Mayor VRAM + peor atención |
| Chunking + embeddings      | Pérdida de estructura de grafo |
| Actualización de conocimiento | Re-indexación / re-embedding |
| Dependencia de servicios   | Pinecone / Weaviate / Qdrant bill + complejidad operativa |

AtlasKV cambia el paradigma: el conocimiento del KG se traduce a memorias Key-Value *nativas* de atención y se accede de forma jerárquica y sparse.

---

## 3. Componentes técnicos clave

### 3.1 KG2KV (Knowledge Graph → Key-Value)

Convierte triples `(h, r, t)` en datos Q-K-V alineados con el mecanismo de atención del LLM:

- Genera consultas naturales, claves y valores de alta calidad.
- Produce embeddings de claves y valores offline (usando sentence encoders: all-MiniLM-L6-v2, text-embedding-ada-002, text-embedding-3-large).
- El modelo aprende a “atender” a estas memorias externas como si fueran parte de su contexto interno.

Resultado: el conocimiento estructurado del grafo se vuelve *atención-compatible* sin necesidad de recuperar texto y meterlo en el prompt.

### 3.2 HiKVP (Hierarchical Key-Value Pruning)

El componente que permite la escala a 1B triples con <20 GB:

- Organiza las claves en una **jerarquía de 3 capas** (UMAP + Gaussian Mixture Models para clustering).
- En inferencia solo se trae a GPU un subconjunto pequeño de candidatos por capa (top-t selection + CPU-GPU offloading).
- Complejidad resultante (según paper):
  - Tiempo: O((C_t √M + N) · N · D)
  - Memoria: O((C_m √M + N) · (N + D))
  - donde M = tamaño del KG, N = longitud de secuencia, D = dimensión, y C_t / C_m son constantes pequeñas.

Esto es lo que convierte un coste lineal (o peor) en sub-lineal y hace viable el 1B en 20 GB.

### 3.3 Características de diseño

- No requiere reentrenamiento del LLM base al añadir nuevos triples (solo actualizar la memoria KV jerárquica).
- Usa la atención nativa del modelo → mejor grounding y generalización que enfoques que “inyectan” texto recuperado.
- Comparado con KBLaM (trabajo previo del mismo linaje), AtlasKV escala mucho mejor y obtiene accuracy superior en datasets OOD.

---

## 4. Números reportados (paper)

| Métrica | AtlasKV | Notas |
|---------|---------|-------|
| Escala de KG | 1B triples | |
| VRAM inferencia | < 20 GB | Incluye modelo + memoria KV activa |
| Accuracy @1 / @5 (varios OOD) | Claramente superior a KBLaM | Ej: ATLAS-Pes2o, ATLAS-CC, Enron |
| Retrievers externos | 0 | |
| Long context prior | 0 | |
| Reentrenamiento al añadir conocimiento | No necesario | |

KBLaM ya superaba los 40 GB con solo 100K triples; AtlasKV mantiene el presupuesto bajo 20 GB hasta 1B.

---

## 5. Código y recursos oficiales

- **Paper**: https://arxiv.org/abs/2510.17934  
- **Repo oficial**: https://github.com/HKUST-KnowComp/AtlasKV  
- **Licencia del repo**: (verificar en el momento de uso; actualmente abierto para investigación).  
- Datasets pre-construidos: ATLAS-Wiki-QKV, ATLAS-CC-QKV, datasets sintéticos al estilo KBLaM.  
- Checkpoints de entrenamiento publicados (AtlasKV entrenado en ATLAS-CC-QKV, 3K steps, varios encoders).

Instalación típica (resumen):

```bash
conda create -n atlaskv python=3.9
conda activate atlaskv
git clone https://github.com/HKUST-KnowComp/AtlasKV.git
cd AtlasKV
pip install -e .
# + huggingface-cli login para modelos Llama
```

El pipeline completo incluye generación de datos KG2KV, embeddings, hierarchical clustering y scripts de entrenamiento/evaluación.

---

## 6. Implicaciones directas para LEONES

### 6.1 Oportunidad estratégica

LEONES ya tiene:
- Capa de conocimiento estructurado (**Atlas**).
- Integración RAG clásica en ODS (Qdrant + embeddings).
- Enfoque *local-first*, hardware de consumo, minimización de dependencias externas y de latencia.

AtlasKV ofrece un camino alternativo (o complementario) para conocimiento factual/estructurado a gran escala **sin** pagar el impuesto de retrieval + contexto largo en cada request.

### 6.2 Casos de uso potenciales en el ecosistema LEONES

1. **Conocimiento canónico de Atlas**  
   Convertir triples o hechos verificados del Atlas canónico en memorias KG2KV y servirlos vía atención nativa en lugar de (o además de) retrieval textual.

2. **Agentes locales con grounding fuerte**  
   Especialistas de dominio (legal, técnico, hardware, etc.) que necesitan acceso a bases de conocimiento grandes sin inflar el contexto ni depender de un vector store siempre activo.

3. **Reducción de VRAM en stacks modestos**  
   Hardware objetivo típico de LEONES (RTX 3050/4050/4060, 8–16 GB, laptops) se beneficia enormemente de métodos que mantienen el coste de memoria bajo control al crecer el conocimiento.

4. **Actualización incremental de conocimiento**  
   Añadir hechos nuevos sin reentrenar el LLM ni reindexar todo un corpus → alineado con la filosofía de evidencia y promoción verificada del Atlas.

5. **Comparativa futura con RAG clásico**  
   Benchmarks LEONES deberían medir:  
   - Latencia end-to-end  
   - VRAM pico  
   - Accuracy de grounding  
   - Coste de actualización de conocimiento  
   entre (a) Qdrant-style RAG y (b) AtlasKV-style parametric KV.

### 6.3 Riesgos y limitaciones a tener en cuenta

- **Estado actual**: investigación + código abierto de laboratorio (HKUST + Huawei). No es todavía un runtime “plug-and-play” listo para producción local como llama.cpp u Ollama.
- **Dependencias**: entrenamiento y construcción de la jerarquía requieren recursos; la inferencia es la parte ligera.
- **Tipo de conocimiento**: optimizado para triples de KG. Texto libre o documentos largos no estructurados siguen necesitando otros enfoques (RAG, long-context, etc.).
- **Procedencia y trazabilidad**: al “hornear” conocimiento en la memoria de atención, se pierde la facilidad de citar “fuente exacta + timestamp” que ofrece un retrieval clásico. LEONES debe preservar la capa de evidencia y no mezclar “conocimiento paramétrico” con “medición verificada”.
- **Licencia y reproducibilidad**: verificar siempre la licencia del código y de los datasets antes de incorporarlos a cualquier pipeline de LEONES.

### 6.4 Clasificación según el contrato de fuentes de LEONES

| Aspecto | Clasificación provisional |
|---------|---------------------------|
| Fuente / descubrimiento | Paper ICLR 2026 + repo oficial |
| Estado recomendado | `research-candidate` |
| Puede alimentar medición LEONES directamente | No (hasta que exista ejecución y benchmark propio) |
| Tipo de contribución | Mecanismo / paradigma de integración de conocimiento |
| Acción inmediata | Documentar, seguir, preparar hipótesis de experimentación |

---

## 7. Próximos pasos sugeridos (ordenados)

1. **Corto plazo (documentación)**  
   - Mantener esta ficha actualizada.  
   - Añadir entrada en `docs/sources/` siguiendo el contrato de fichas de conocimiento cuando se formalice.

2. **Mediano plazo (experimentación controlada)**  
   - Reproducir el pipeline de evaluación del paper en hardware LEONES (empezar con escalas pequeñas: 10k–100k triples).  
   - Medir VRAM real, latencia y accuracy de grounding vs. baseline RAG (Qdrant) en los mismos hechos.

3. **Largo plazo (integración arquitectónica)**  
   - Evaluar si tiene sentido un “AtlasKV backend” opcional para el Router / agentes cuando el conocimiento es altamente estructurado y de gran volumen.  
   - Definir límites claros entre:  
     - conocimiento paramétrico (AtlasKV-style),  
     - retrieval no-paramétrico (RAG),  
     - y mediciones/evidencia verificada de LEONES.

4. **Seguimiento**  
   - Vigilar releases del repo HKUST-KnowComp/AtlasKV.  
   - Buscar implementaciones más ligeras o ports a backends locales (llama.cpp style, GGUF, etc.) si aparecen.

---

## 8. Fuentes primarias

- Paper: Huang et al., *AtlasKV: Augmenting LLMs with Billion-Scale Knowledge Graphs in 20GB VRAM*, arXiv:2510.17934 (v2, 13 Apr 2026). Aceptado ICLR 2026.  
- Repo oficial: https://github.com/HKUST-KnowComp/AtlasKV  
- Tuit origen de esta investigación: https://x.com/HowToPrompt__/status/2123302413583135028  
- Abstract y recursos adicionales: https://arxiv.org/abs/2510.17934 y página del paper en Hugging Face Papers.

---

## 9. Nota de trazabilidad LEONES

Este documento es **investigación / prospección**. No constituye:
- medición LEONES,
- aprobación de componente ejecutable,
- ni promoción a catálogo canónico del Atlas.

Cualquier claim de rendimiento o VRAM se mantiene en la capa de **evidencia externa / estimación** hasta que LEONES ejecute y registre sus propias mediciones bajo el pipeline de evidencia (reported → reproducible → verified).

---

*Documento generado el 19 de noviembre de 2026 a partir del paper oficial, el repo público y el hilo de X. Sigue el protocolo de documentación de Atlas y el contrato de fuentes de conocimiento de LEONES.*
