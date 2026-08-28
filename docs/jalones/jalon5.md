# JALÓN 5 — Contrato de decisión LEONES → ODS | Magnitude → LLMFit

**Estado:** 🟠 CONTRATO FIJADO · VALIDACIÓN DE HOST PENDIENTE  
**Base:** `rc1-minimal-script-cleanup`

## 1. Objetivo

Cerrar la cadena de decisión sin crear un segundo sistema paralelo de selección.

JALÓN 5 define cómo LEONES consume señales de **ODS/Magnitude** y **LLMFit**, las conserva con procedencia y las transforma en una decisión explícita de candidato. No convierte estimaciones en mediciones.

## 2. Roles canónicos

- **ODS / Magnitude:** perfilado y/o benchmark externo del encaje modelo ↔ hardware, conservando fuente y versión.
- **LLMFit:** estimación rápida de fit y recursos; es una señal `estimated`, no una medición LEONES.
- **LEONES selector:** aplica los gates de tarea, hardware, runtime, memoria, contexto y evidencia; ordena candidatos.
- **JALÓN 3:** aporta la medición física real y evidencia `runtime-benchmark-evidence.v1.1`.

## 3. Orden de decisión

```text
selección de tarea
      ↓
hardware del usuario
      ↓
ODS / Magnitude + LLMFit
      ↓
Atlas / evidencia técnica
      ↓
runtime permitido por JALÓN 4
      ↓
selector LEONES
      ↓
CANDIDATE / BENCHMARK_REQUIRED
      ↓
JALÓN 3 — medición real
      ↓
recomendación respaldada por evidencia
```

## 4. Reglas

1. Una fuente externa nunca puede escribir `measured`.
2. LLMFit conserva siempre `estimate_only: true`.
3. ODS/Magnitude conserva fuente, versión/revisión y timestamp cuando exista.
4. El selector LEONES sigue siendo la autoridad de elegibilidad y ranking.
5. El runtime debe estar decidido antes de evaluar el modelo.
6. Una cifra medida local prevalece para rendimiento local únicamente cuando pertenece a una ejecución identificada y validada.
7. Las estimaciones no se sobrescriben: se conservan como hipótesis históricas.
8. Un candidato sin evidencia suficiente puede quedar como `BENCHMARK_REQUIRED`, pero no como `measured`.

## 5. Contrato de salida

La salida machine-readable se ajusta a `schemas/leones-ods-magnitude-decision.v1.json` y debe permitir reconstruir:

- hardware objetivo;
- workload;
- runtime requerido;
- señales ODS/Magnitude;
- señales LLMFit;
- evidencia Atlas;
- decisión del selector;
- motivo de la decisión;
- necesidad de benchmark físico;
- procedencia y timestamps.

## 6. Tiers de hardware

Los tiers de hardware se derivarán de las capacidades y límites realmente declarados por ODS/Magnitude y LLMFit. LEONES no inventa una métrica de rendimiento para sustituirlos.

El tier es una **clasificación de capacidad/encaje**, no una cifra universal de tok/s.

## 7. Qué queda fuera

- ejecutar ODS/Magnitude automáticamente durante CI;
- instalar herramientas externas de forma implícita;
- convertir fit estimado en rendimiento medido;
- crear un benchmark paralelo a ODS/Magnitude;
- fabricar tiers a partir de umbrales arbitrarios de tok/s.

## 8. Criterio de cierre

JALÓN 5 queda operativo cuando el contrato y su runner demuestren en CI que las señales externas están separadas de la medición, que la decisión tiene procedencia completa y que el selector LEONES sigue siendo la autoridad final.

La validación de una instalación real de ODS/Magnitude queda para Ubuntu cuando sea necesaria.
