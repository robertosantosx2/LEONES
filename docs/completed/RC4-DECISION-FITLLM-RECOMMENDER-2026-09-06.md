# RC4 · Decisión: FitLLM como preselector de modelo

**Fecha:** 2026-09-06  
**Estado:** 🟢 Decisión de arquitectura fijada + adenda de integración  
**Predecesor:** RC3 (fase **CERRADA**; no se reabre)

## Adenda de integración — 2026-09-06

La CLI real de LLMFit 1.1.10 no ofrece un flag soportado para inyectar en `recommend` un catálogo externo construido por LEONES. **RC4 no inventa esa interfaz.**

La implementación canónica separa dos superficies y las cruza por identidad:

```text
USER_INTENT[] → HARDWARE DETECTADO → HF + ARTIFICIAL ANALYSIS → feed LEONES ≤100
                                                        │
                         ┌──────────────────────────────┘
                         │
                         ▼
                 LLMFit CLI ≤100
                         │
                         └── identidad normalizada ──┐
                                                     ▼
                                      evidence-backed intersection
                                                     ▼
                                               hasta 3 ESTIMATED
                                                     ▼
                                               selección humana
```

### Reglas fijadas

- **FitLLM/LLMFit es preselector**, no autoridad.
- **FitLLM no es dependencia dura** de instalación o arranque.
- El feed externo no se atribuye a LLMFit como si hubiese sido puntuado internamente.
- La salida LLMFit solo puede aportar candidatos con respaldo en el feed.
- La procedencia HF/AA queda en `evidence_provenance`.
- La frontera se declara como `selection_boundary = evidence_backed_intersection`.
- El límite es 100 en el feed y 100 en la consulta LLMFit.
- Menos de tres coincidencias produce `insufficient`; no hay padding.
- Los candidatos permanecen `ESTIMATED`.
- `execution_authorized`, `measurement_authorized` y `measured` permanecen en `false`.
- Tras Magnitude/ODS, la oferta de desinstalar FitLLM es **opt-in**.

## Decisión original, resumida

1. **FitLLM/LLMFit es preselector, no autoridad.**
2. **FitLLM es opcional**, no dependencia dura de instalación/arranque.
3. **Hermes y OMH están fuera del camino canónico RC4**; sus referencias históricas no se borran.
4. Tras Magnitude/ODS puede ofrecerse la desinstalación de FitLLM, siempre opt-in.
5. **Leo001…Leo010** se conserva para medición/comparación.
6. **RC3 permanece CERRADA.**

## Flujo canónico RC4

```text
UBUNTU / EQUIPO REAL
        ↓
USER_INTENT[]                 obligatorio · múltiple · no vacío
        ↓
resource preflight
        ↓
hardware detectado
        ↓
Hugging Face + Artificial Analysis
        ↓
LEONES evidence feed          ≤100
        ↓
LLMFit / FitLLM CLI            ≤100 · catálogo propio
        ↓
intersección respaldada
        ↓
hasta 3 ESTIMATED
        ↓
elección humana
        ↓
elección de stack + consentimiento
        ↓
preparar / instalar
        ↓
verificación física
        ↓
Leo001…Leo010
        ↓
medición → evidencia MEASURED
```

## Separación de autoridad

**LEONES** descubre y normaliza hardware, conserva la intención y mantiene la procedencia. **Hugging Face** y **Artificial Analysis** aportan evidencia externa. **LLMFit** preselecciona desde su propio catálogo. **LEONES** exige respaldo en el feed antes de proponer. El **usuario** elige. El runtime físico mide.

## Estados

| Estado | Significado |
|---|---|
| `DECLARED` | dato declarado por usuario/fuente |
| `ESTIMATED` | estimación o preselección previa a ejecución |
| `OBSERVED` | observación externa/local sin ser necesariamente benchmark final |
| `MEASURED` | ejecución física protocolizada en el equipo real |

Nunca se promociona automáticamente `ESTIMATED` a `MEASURED`.

## Criterios de aceptación de esta capa

- [x] Intención múltiple obligatoria antes de recomendar.
- [x] Feed HF + AA con máximo 100 registros.
- [x] LLMFit consultado mediante CLI real, sin flags inventados.
- [x] Intersección explícita y trazable.
- [x] Hasta tres candidatos `ESTIMATED`.
- [x] `insufficient` cuando faltan coincidencias; sin padding.
- [x] Sin autorización de ejecución ni medición.
- [ ] Validación física completa de la cadena en Ubuntu.

## Procedencia

- `docs/RC4-ARCHITECTURE.md`
- `docs/RC4-EVIDENCE-BRIDGE.md`
- `scripts/rc4_fitllm_recommend.py`
- `scripts/collect_model_evidence.py`
- `runtime_selection/llmfit.py`
- `tests/test_rc4_fitllm_recommend.py`
