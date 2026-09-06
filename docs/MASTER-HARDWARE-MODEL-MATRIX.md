# LEONES — Cuadros maestros hardware → LLM

**Contrato:** `leones-master-hardware-model-matrix.v1`  
**Snapshot:** 2026-09-02  
**Fuente de inteligencia:** Artificial Analysis Intelligence Index v4.1.1  
**Fuente de ajuste hardware:** LLMFit

## Regla canónica

Cada cruce representa el **LLM de mayor puntuación en Artificial Analysis** entre los modelos abiertos que pasan el filtro de hardware.

```text
hardware (CPU + RAM + GPU)
          ↓
       LLMFit
          ↓
 modelos que caben / quantización
          ↓
 Artificial Analysis
          ↓
 MAX(Intelligence Index)
          ↓
       LEONES
```

LLMFit detecta RAM/VRAM, soporta NVIDIA, AMD e Intel Arc y evalúa rutas GPU, CPU+GPU/offload y CPU. Su base usa estimaciones de memoria por cuantización y puede simular hardware con overrides.

Artificial Analysis v4.1.1 define el Intelligence Index a partir de nueve evaluaciones y permite filtrar modelos por pesos abiertos. El snapshot actual muestra a **Qwen3.8 27B (xhigh) = 52** como el modelo abierto pequeño de mayor puntuación visible; Qwen3.5 9B Reasoning = 22, Qwen3.5 4B Reasoning = 20 y G9v3-3B = 16.

> **Importante:** esta primera matriz es un *snapshot reproducible* con un catálogo de candidatos verificados. No se debe interpretar como una fotografía permanente de AA. El selector de producción debe refrescar el catálogo y dejar que LLMFit determine el fit/quant exacto.

## Candidatos AA incluidos en el snapshot

| Modelo | Parámetros | AA Intelligence | Estado AA |
|---|---:|---:|---|
| Qwen3.8 27B (xhigh) | 27B | **52** | medido |
| Qwen3.5 27B (Reasoning) | 27.8B | 35 | medido |
| Qwen3.5 35B A3B (Reasoning) | 36B / 3B activos | 30 | estimado |
| Qwen3.5 9B (Reasoning) | 9.7B | 22 | medido |
| Qwen3.5 4B (Reasoning) | 4.7B | 20 | medido |
| G9v3-3B | 3B | 16 | medido |

## Criterio de cálculo del snapshot

Para hacer la matriz auditable sin sustituir LLMFit, el snapshot usa la aproximación documentada por LLMFit para Q4 como referencia:

- VRAM ≈ parámetros × 0,5 GB × 1,1
- RAM ≈ parámetros × 0,5 GB × 1,2
- si cabe en VRAM, ruta GPU;
- si no cabe en VRAM pero cabe en RAM, ruta de offload/CPU;
- si no cabe, se prueba el siguiente candidato.

En producción, **la cuantización no se fija en Q4**: LLMFit selecciona dinámicamente la mejor cuantización que cabe, desde Q8_0 hacia Q2_K.

## Intel Core i5 / AMD Ryzen 5

| GPU (orden de potencia de referencia) | VRAM | 2 GB RAM | 4 GB RAM | 8 GB RAM | 16 GB RAM | 32 GB RAM | 64 GB RAM |
|---|---:|---|---|---|---|---|---|
| 1. RTX 5090 (NVIDIA) | 32 GB | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |
| 2. RTX 4090 (NVIDIA) | 24 GB | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |
| 3. RX 7900 XTX (AMD) | 24 GB | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |
| 4. RTX 5080 (NVIDIA) | 16 GB | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |
| 5. RX 9070 XT (AMD) | 16 GB | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |
| 6. RTX 4080 SUPER (NVIDIA) | 16 GB | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |
| 7. RTX 5070 Ti (NVIDIA) | 16 GB | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |
| 8. RX 9070 (AMD) | 16 GB | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |
| 9. RX 9060 XT 16GB (AMD) | 16 GB | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |
| 10. RTX 5060 Ti 16GB (NVIDIA) | 16 GB | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |
| 11. RTX 4060 Ti 16GB (NVIDIA) | 16 GB | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |
| 12. RTX 5070 (NVIDIA) | 12 GB | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |
| 13. Arc B580 (Intel) | 12 GB | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |
| 14. RTX 3060 12GB (NVIDIA) | 12 GB | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |
| 15. Arc B570 (Intel) | 10 GB | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |
| 16. RTX 4060 (NVIDIA) | 8 GB | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |
| 17. RX 7600 (AMD) | 8 GB | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |
| 18. Arc A580 (Intel) | 8 GB | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |
| 19. RTX 3050 6GB (NVIDIA) | 6 GB | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |
| 20. GTX 1650 4GB (NVIDIA) | 4 GB | G9v3-3B · AA 16 | Qwen3.5 4B (Reasoning) · AA 20 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.5 9B (Reasoning) · AA 22 | Qwen3.8 27B (xhigh) · AA 52 | Qwen3.8 27B (xhigh) · AA 52 |

## Intel Core i7 / AMD Ryzen 7

**Misma selección intelectual que i5/Ryzen 5 para un mismo binomio RAM+GPU; el i7/Ryzen 7 cambia la expectativa de rendimiento, no la puntuación AA.** La matriz usa los mismos cruces para evitar introducir una diferencia artificial de calidad de modelo.

## Intel Core i9 / AMD Ryzen 9

**Misma selección intelectual que i5/Ryzen 5 para un mismo binomio RAM+GPU; el i9/Ryzen 9 cambia la expectativa de rendimiento, no la puntuación AA.** La matriz usa los mismos cruces para evitar introducir una diferencia artificial de calidad de modelo.

## Interpretación

La separación i5/Ryzen 5, i7/Ryzen 7 e i9/Ryzen 9 se conserva porque **el CPU sí afecta a rendimiento y a la ruta de ejecución**, pero no debe alterar artificialmente el Intelligence Index del modelo. Dos CPUs pueden seleccionar el mismo LLM y después producir velocidades locales muy distintas.

Por ello LEONES mantiene separadas estas dos decisiones:

1. **Selección intelectual:** mayor AA entre modelos que caben.
2. **Selección operativa:** LLMFit + runtime + benchmark físico de LEONES.

Una vez ejecutado el benchmark físico, la evidencia local puede enriquecer la recomendación, pero no sustituye ni reescribe la puntuación AA.

## Estado

`v1` — **implantado como contrato maestro y snapshot de referencia**.

La siguiente evolución debe generar las tres tablas automáticamente desde `data/master_hardware_model_matrix.v1.json`, consumiendo el JSON de LLMFit y un snapshot de AA para que ningún modelo quede codificado manualmente en la lógica de selección.
