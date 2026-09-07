# RC4 · STRICT · Preflight Ubuntu Aspire A515-55

**Fecha:** 2026-09-06  
**Modo:** limpia, fija y da esplendor  
**Host:** Aspire A515-55 (Ubuntu, ~7 GB RAM)  
**Rama:** `rc4-fitllm-recommender`  
**PR:** #82

## 1. Qué se limpió

- Firma obsoleta del preflight Ubuntu: `recommend(use_case=...)` ya no existe.
- API canónica única: `recommend(user_intent=[...], max_context=...)`.
- Flag CLI único: `--purpose` repetible (intención múltiple obligatoria).
- Resolución de `--out` relativo respecto al ROOT del repositorio (evita `ValueError` de `Path.relative_to`).

## 2. Qué se fijó

| Elemento | Fuente canónica |
|---|---|
| Decisión FitLLM opcional | `docs/completed/RC4-DECISION-FITLLM-RECOMMENDER-2026-09-06.md` |
| Arquitectura | `docs/RC4-ARCHITECTURE.md` |
| Puente de evidencia | `docs/RC4-EVIDENCE-BRIDGE.md` |
| Recomendador | `scripts/rc4_fitllm_recommend.py` |
| Preflight Ubuntu | `scripts/rc4_ubuntu_preflight.py` |
| Preflight recursos | `scripts/rc4_resource_preflight.py` |
| Gate estático | `scripts/rc4_release_gate.py` |
| Runner por defecto | `scripts/rc4_runner.py` / `./leones` |
| Tests | `tests/test_rc4_fitllm_recommend.py`, `tests/test_rc4_release_gate.py` |

Invariantes no negociables:

```text
USER_INTENT[] obligatorio y múltiple
      ↓
HF + AA → feed LEONES ≤100
      ↓
LLMFit CLI real ≤100 (sin flags inventados)
      ↓
intersección por identidad (evidence_backed_intersection)
      ↓
hasta 3 ESTIMATED  |  insufficient (sin padding)
      ↓
execution_authorized = false
measurement_authorized = false
measured = false
```

## 3. Evidencia de esta sesión

### Gate y tests (Aspire)

```text
RC4 RELEASE GATE: PASS
tests/test_rc4_fitllm_recommend.py + test_rc4_release_gate.py → 6 passed
```

### Resource preflight

- ODS instalado (`~/ods`)
- Magnitude 0.0.11
- LLMFit 1.1.10 en `/usr/local/bin/llmfit`
- RAM total ~7.03 GB; available ~2.0 GB en el momento de la sonda
- Disco libre ~62 GB en el path del repo
- `installation_budget.status = ready_for_next_gate`

### Ubuntu preflight (corrida canónica)

```text
python3 scripts/rc4_ubuntu_preflight.py \
  --purpose programming --purpose reasoning \
  --out results/physical-rc4-20260906/ubuntu-preflight-aspire.json

RC4 UBUNTU PREFLIGHT: PASS
  hardware: hardware-profile.v1
  FitLLM: insufficient (1/3 candidates)
  execution_authorized: False
  measurement_authorized: False
  measured: False
  artifact: results/physical-rc4-20260906/ubuntu-preflight-aspire.json
```

**Lectura correcta de `insufficient`:** en este hardware la intersección HF/AA × catálogo LLMFit no alcanzó tres identidades respaldadas. El contrato prohíbe rellenar candidatos. No es un fallo del preflight.

## 4. Scripts RC4 — mapa pedagógico

```text
rc4_runner.py              entrada humana → purposes[] → recommender
rc4_fitllm_recommend.py    feed evidencia + CLI LLMFit + intersección
rc4_ubuntu_preflight.py    hardware_profile + recommend (solo preflight)
rc4_resource_preflight.py  memoria/disco + software instalado
rc4_release_gate.py        invariantes de docs/decisión (estático)
rc4_component_cost.py      costes ESTIMATED (UNKNOWN si no hay cifra)
rc4_install_lifecycle.py   pares install/uninstall + offer opt-in FitLLM
```

Qué **no** hacen estos scripts:

- no instalan modelos por sí solos;
- no ejecutan inferencia;
- no marcan MEASURED;
- no tratan estimaciones externas como medición local;
- no usan Hermes/OMH como selector.

## 5. Web alineada

Páginas que reflejan este estado (ya no «RC4 código pendiente»):

- `web/rc4.html` — contrato y flujo evidence-backed
- `web/estado.html` — RC4 decisión + capa recomendación endurecida; MEASURED abierto
- `web/operacion.html` — camino con intersección y preflight
- `web/inicio-rapido.html` — comandos actuales
- `web/scripts.html` — inventario RC4

## 6. Abierto (no cerrado en esta sesión)

- Cadena completa hasta runtime físico + Leo001…Leo010 + evidencia MEASURED
- Quality gate global de `scripts/` (106 avisos históricos fuera de `rc4_*`)
- Workflows A01/V1 legacy en rojo en PR #82 (ajenos al núcleo RC4)
- Cierre formal de RC4 como fase (sigue 🟡 hasta MEASURED reproducible)

## 7. Cómo repetir en Ubuntu

```bash
git fetch origin && git checkout rc4-fitllm-recommender
git pull --ff-only origin rc4-fitllm-recommender
python3 scripts/rc4_release_gate.py
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -q pytest
python -m pytest tests/test_rc4_fitllm_recommend.py tests/test_rc4_release_gate.py -q
deactivate
python3 scripts/rc4_resource_preflight.py
python3 scripts/rc4_ubuntu_preflight.py \
  --purpose programming --purpose reasoning \
  --out results/physical-rc4-20260906/ubuntu-preflight-aspire.json
```

## Procedencia

- Commits de alineación API: `52786eb`, `45fc5f6`
- Artefacto local: `results/physical-rc4-20260906/ubuntu-preflight-aspire.json`
- Metodología: `docs/STRICT-LIMPIA-FIJA-ESPLENDOR.md`, `docs/DOCUMENTATION_PROTOCOL.md`
