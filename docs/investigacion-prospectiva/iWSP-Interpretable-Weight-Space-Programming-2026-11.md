# Investigación Prospectiva — Interpretable Weight-Space Programming (iWSP)

**Fecha de archivo:** 2026-11-18  
**Origen de la alerta:** post viral en X de @thesupermannx  
**Estado:** external-unvalidated (prospección técnica)  
**Tipo:** paper + paradigma emergente (WSP / iWSP)

---

## Resumen ejecutivo

Un paper de **Microsoft Research + JHU + Columbia + NYU** (noviembre 2026) introduce **Interpretable Weight-Space Programming (iWSP)**: un agente LLM escribe y refina los pesos y features de una red neuronal **directamente en código**, sin backpropagation ni optimizadores de gradiente.

El post viral afirmaba que «Microsoft just killed backpropagation». Eso es hype exagerado. El trabajo es real y útil, pero se orienta a **modelos pequeños, transparentes y científicos** (especialmente encoding models en neurociencia), no a reemplazar el entrenamiento a escala de modelos frontier.

iWSP es una extensión **interpretable** del paradigma más amplio **Weight-Space Programming (WSP)** introducido días antes (2 nov 2026) por el equipo de MIT CSAIL (Takehi, Teoh, Zhang, Khattab).

---

## Fuentes primarias

| Recurso | Enlace |
|---------|--------|
| Paper iWSP (alphaXiv) | https://www.alphaxiv.org/abs/2611.interpretable-weight-space-programming |
| Paper iWSP (arXiv) | https://arxiv.org/abs/2611.18114 |
| Código oficial iWSP | https://github.com/csinva/weight-space-programming-autoresearch |
| Thread del autor principal | https://x.com/y_mehtu (Yash Mehta) |
| Blog original WSP (MIT CSAIL) | https://rikiyat.github.io/blog/weight-space-programming/ |
| Logs y modelo editado WSP | Públicos en GitHub + Hugging Face |

**Autores principales iWSP:** Yash Mehta, Chandan Singh, Weijia Xu, Richard J. Antonello, Adeen Flinker, Nima Mesgarani, Michael F. Bonner, Nebojsa Jojic, Jianfeng Gao.

---

## Qué hace iWSP (hechos del paper)

1. Un agente LLM recibe una tarea y un harness de código restringido.
2. Escribe el modelo (pesos + features) **directamente en Python**.
3. Un evaluador fijo devuelve un score de validación (sin gradientes).
4. El agente itera (hipótesis → escritura → evaluación → refinamiento), imitando el flujo de un científico.
5. Auditorías de interpretabilidad: un agente describe el modelo en ≤200 palabras y otro lo reconstruye desde el texto.

**Resultados destacados:**
- 13 tareas algorítmicas (aritmética, sorting, GCD…): 100 % accuracy held-out, mediana ~166 parámetros (compresión ~29×).
- Encoding models de corteza visual (fMRI): supera 7 baselines interpretables y generaliza a NSD.
- Language fMRI: detectó un confound de posición de scan (drift de inicio/fin de scan).
- Audio ECoG: features acústicas interpretables que aportan varianza única frente a Whisper.

---

## Relación con Weight-Space Programming (WSP)

| Aspecto | WSP (MIT CSAIL, 2 nov 2026) | iWSP (Microsoft et al., ~12 nov 2026) |
|---------|-----------------------------|---------------------------------------|
| Objetivo principal | Leer / editar / escribir pesos de redes existentes | Construir modelos interpretables desde cero |
| Enfoque | Edición localizada (ej. quitar loops de razonamiento en Qwen) | Hipótesis explícitas + interpretabilidad forzada |
| Interpretabilidad | Secundaria | Requisito central + auditorías |
| Escala típica | Modelos pequeños + ediciones en 0.8B | Transformers compactos + encoding models |

WSP demostró que un LLM frontier puede editar 0.016 % de los pesos de Qwen3.5-0.8B y subir MATH-500 de 7.9 % a 48.1 % (principalmente cortando loops). iWSP lleva la idea a la construcción de modelos legibles por humanos.

---

## Ecosistema emergente (GitHub / HF / Reddit)

**Repositorios relevantes detectados (nov 2026):**

- `csinva/weight-space-programming-autoresearch` — código oficial iWSP
- `leofmarciano/weightspace` — framework genérico para WSP
- `Eppy-EpHard/AHA` — WSP sin LLM externo (self-supervised + LP)
- `emeraldant/WSP-Gym` — gym para entrenar agentes de reparación de pesos
- `suayptalha/wsr`, `nathanrs/weight-space-lp`, `cmpnd-ai/dspy-wsp`, `effl-lab/Weight-Space-Programming`, etc.

**Discusiones:**
- Reddit: r/LocalLLaMA, r/MachineLearning, r/mlscaling (principalmente alrededor del paper MIT original).
- Hugging Face: papers indexados, modelos editados, blogs experimentales (medicina, etc.).

---

## Relevancia para LEONES (criterio de prospección)

### ¿Por qué es interesante?

- **Interpretabilidad nativa**: los pesos se escriben como código legible. Alineado con el principio LEONES de no confundir ESTIMATED con MEASURED y de privilegiar evidencia transparente.
- **Edición sin entrenamiento**: permite intervenciones localizadas y reversibles (útil para harnesses, agentes y modelos pequeños locales).
- **Puente software ↔ pesos**: acerca la ingeniería de software clásica al espacio de pesos.

### Límites actuales (estado external-unvalidated)

- Funciona bien en modelos pequeños / features interpretables.
- No sustituye el entrenamiento a escala.
- Las ediciones en modelos frontier siguen siendo frágiles y de alcance limitado.
- Requiere agentes LLM potentes + harness cuidadoso.

### Posibles líneas de seguimiento LEONES

1. Evaluar si el harness de iWSP / weightspace puede integrarse como herramienta de un agente local.
2. Probar WSP-Gym o AHA en hardware de consumo (RTX 3050 class).
3. Monitorizar réplicas open-source y toolkits que no dependan de modelos frontier cerrados.
4. Documentar cualquier experimento local bajo el protocolo de evidencia LEONES (ESTIMATED → MEASURED).

---

## Clasificación de prospección

```text
Descubierto → OSI / licencia del código oficial pendiente de verificación
              → external-unvalidated
              → revisión técnica pendiente
              → evidencia local pendiente
```

**Acción recomendada:** mantener en radar de prospección. No incorporar todavía a Atlas ni a Router hasta disponer de evidencia MEASURED en hardware LEONES o de un harness reproducible y open.

---

## Referencias rápidas de X (18 nov 2026)

- Post original: https://x.com/thesupermannx/status/2123023351035924832
- Matizaciones: comentarios que destacan que no «mata» backpropagation; es un método de investigación para modelos transparentes.

---

*Archivado desde conversación de análisis de contenido X + búsqueda multiplataforma (X, Reddit, GitHub, Hugging Face, arXiv/alphaXiv).*
