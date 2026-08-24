# Integraciones LEONES: LLMFit, ODS y Magnitude

Estas integraciones convierten herramientas externas en **perfiles medibles y documentados** sin convertirlas en dependencias estructurales de LEONES.

- **LLMFit — preselector hardware-aware**: reduce inicialmente el espacio de candidatos modelo ↔ máquina.
- **ODS — Servidor de Stacks IA**: despliega una pila local alrededor de inferencia, UI, agentes, RAG, workflows, voz e imagen.
- **Magnitude — Asistente personal IA**: instala un agente de coding local con motor de inferencia propio, perfilado de hardware y recomendación de modelos.

## Regla de frontera

Las herramientas externas siguen siendo responsables de su instalación, runtime y comportamiento interno. LEONES se ocupa de:

1. preflight;
2. consentimiento;
3. instalación reproducible cuando corresponda;
4. captura de configuración;
5. validación independiente;
6. benchmark;
7. separación `estimated` / `reported` / `observed` / `measured`;
8. publicación de evidencia solo con el consentimiento correspondiente.

La instalación **no implica telemetría**. La captura de datos es explícita y opt-in.

## Documentación

| Integración | README | Fuentes de conocimiento / piezas relacionadas |
|---|---|---|
| LLMFit | [LLMFIT/README.md](LLMFIT/README.md) | [`../sources/LLMFIT.md`](../sources/LLMFIT.md), [`../sources/LLMFIT-REAL-HARDWARE-2026-08-20.md`](../sources/LLMFIT-REAL-HARDWARE-2026-08-20.md), hardware matrix, CABE/RULA |
| ODS | [ODS/README.md](ODS/README.md) | [`../sources/ODS.md`](../sources/ODS.md), instalación, runtime y benchmark |
| Magnitude | [Magnitude/README.md](Magnitude/README.md) | [`../sources/MAGNITUDE.md`](../sources/MAGNITUDE.md), agente, skills y benchmark |

## Contratos y operación

- [Matriz de instalación por dispositivo](IN-DEVICE-INSTALLATION-MATRIX.md)
- [Contrato de datos](DATA-CONTRACT.md)
- [Plan E2E](E2E.md)
- [Resultado canónico](../RESULT_SCHEMA.md)
- [Arquitectura global](../ARCHITECTURE.md)
- [Índice documental](../README.md)

## Flujo común

```text
PREFLIGHT
   ↓
CONSENTIMIENTO
   ↓
INSTALACIÓN CONTROLADA / PRESELECCIÓN
   ↓
HEALTH / STATUS
   ↓
CAPTURA DE CONFIGURACIÓN
   ↓
BENCHMARK LEONES
   ↓
ESTIMATED ≠ OBSERVED ≠ MEASURED
   ↓
EVIDENCIA ATLAS (solo con consentimiento)
```

## Regla de evidencia

LLMFit puede producir una **estimación**; ODS puede producir una **configuración observada**; Magnitude puede producir una **recomendación** y una configuración seleccionada. Ninguno de esos resultados es automáticamente una medición LEONES.

La cadena canónica es:

```text
fuente externa
     ↓
evidencia / recomendación externa
     ↓
hipótesis LEONES
     ↓
ejecución
     ↓
medición LEONES
     ↓
Atlas / Router
```
