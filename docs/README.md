# LEONES — Índice documental canónico

Esta carpeta contiene la documentación técnica, arquitectónica, operativa, de decisiones y de diseño web de LEONES. Este README es el **mapa documental canónico**.

## Índice principal

### Fuentes de conocimiento

- [sources/README.md](sources/README.md) — registro de fuentes externas.
- [sources/LLMFIT.md](sources/LLMFIT.md) — LLMFit.
- [sources/AIRLLM.md](sources/AIRLLM.md) — AirLLM.
- [sources/ODS.md](sources/ODS.md) — ODS.
- [sources/MAGNITUDE.md](sources/MAGNITUDE.md) — Magnitude.
- [sources/WARP.md](sources/WARP.md) — WARP como runtime experimental para MoE grandes.

Las capas permanecen separadas: **fuente → evidencia → estimación → medición LEONES**.

### Integraciones

- [integrations/README.md](integrations/README.md) — índice de integraciones.
- [integrations/LLMFIT/README.md](integrations/LLMFIT/README.md) — LLMFit.
- [integrations/ODS/README.md](integrations/ODS/README.md) — ODS.
- [integrations/Magnitude/README.md](integrations/Magnitude/README.md) — Magnitude.
- [integrations/WARP/README.md](integrations/WARP/README.md) — integración propuesta WARP ↔ ODS ↔ LEONES.
- [integrations/DATA-CONTRACT.md](integrations/DATA-CONTRACT.md) — contrato de datos.
- [integrations/E2E.md](integrations/E2E.md) — validación E2E.

### Arquitectura y evidencia

- [ARCHITECTURE.md](ARCHITECTURE.md) — arquitectura global.
- [RESULT_SCHEMA.md](RESULT_SCHEMA.md) — resultado canónico.
- [completed/BENCHMARK-MEASURED-EVIDENCE.md](completed/BENCHMARK-MEASURED-EVIDENCE.md) — evidencia de benchmarks medidos.
- [completed/H09-CABE-RULA.md](completed/H09-CABE-RULA.md) — CABE/RULA.

## Mapa de relación

```text
PROSPECCIÓN
    ↓
ATLAS / IDENTIDAD / EVIDENCIA
    ↓
JGB + LICENCIAS + HARDWARE
    ↓
LLMFIT → FIT INICIAL
    ↓
MODELO + CUANTIZACIÓN + RUNTIME
    ├── llama-server
    ├── otros runtimes
    └── WARP → MoE grandes + NVMe paging
    ↓
BENCHMARK LEONES → MEDICIÓN
    ↓
CABE / RULA
    ↓
RECOMENDADOR / ROUTER
```

WARP queda documentado como **candidato experimental**. Sus resultados externos no se convierten en mediciones LEONES sin ejecución física y benchmark reproducible.
