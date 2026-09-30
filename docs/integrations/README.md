# Integraciones LEONES: LLMFit, ODS, Magnitude y WARP

Estas integraciones convierten herramientas externas en **perfiles medibles y documentados** sin convertirlas en dependencias estructurales de LEONES.

- **LLMFit — preselector hardware-aware**.
- **ODS — Servidor de Stacks IA**.
- **Magnitude — Asistente personal IA**.
- **WARP — runtime experimental para MoE grandes mediante paging desde NVMe**.

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

| Integración | README | Fuentes |
|---|---|---|
| LLMFit | [LLMFIT/README.md](LLMFIT/README.md) | [../sources/LLMFIT.md](../sources/LLMFIT.md) |
| ODS | [ODS/README.md](ODS/README.md) | [../sources/ODS.md](../sources/ODS.md) |
| Magnitude | [Magnitude/README.md](Magnitude/README.md) | [../sources/MAGNITUDE.md](../sources/MAGNITUDE.md) |
| WARP | [WARP/README.md](WARP/README.md) | [../sources/WARP.md](../sources/WARP.md) |

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

LLMFit puede producir una **estimación**; ODS puede producir una **configuración observada**; Magnitude puede producir una **recomendación**; WARP aporta evidencia externa y una configuración de runtime que debe validarse. Ninguno de esos resultados es automáticamente una medición LEONES.

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
