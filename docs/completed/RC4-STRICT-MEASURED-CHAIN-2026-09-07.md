# RC4 STRICT — cadena selección humana → stack → runtime → Leo/A01 → MEASURED

**Fecha:** 2026-09-07  
**Modo:** limpia, fija y da esplendor  
**Rama:** `rc4-fitllm-recommender`

## Problema

La capa de recomendación produce solo `ESTIMATED`. El orquestador canónico debe:

1. no auto-ejecutar desde la recomendación;
2. exigir selección humana de `model_id`;
3. registrar stack (`magnitude|ods|none`);
4. observar runtime (A01/Ollama) sin inventar comandos;
5. exigir doble autorización (`--authorize-execution` + `--authorize-measurement`);
6. marcar `measured=true` solo tras ejecución real exitosa.

## Fuente canónica

| Pieza | Ruta |
|-------|------|
| Orquestador | `scripts/rc4_measured_chain.py` |
| Preflight recursos | `scripts/rc4_resource_preflight.py` (Hermes, OMH, Ollama) |
| Inventario / uninstall | `scripts/rc4_component_inventory.py`, `scripts/uninstall.sh` |
| Runtime A01 | `scripts/a01_runtime_preflight.py`, `scripts/run_a01_selected.py` |
| Tests inventario | `tests/test_rc4_component_inventory.py` |

## Cadena fijada

```text
ESTIMATED recommendation
        ↓
human selection (model_id)
        ↓
stack choice
        ↓
runtime preflight (OBSERVED)
        ↓
--execute + --authorize-execution + --authorize-measurement
        ↓
A01 / trusted argv (no shell from model text)
        ↓
MEASURED evidence envelope  OR  next_gate explícito
```

## Reglas

- `ESTIMATED ≠ MEASURED`
- autorizaciones opt-in
- Hermes/OMH no seleccionan modelo
- placeholder shell `<modelo…>` **no** es un model_id válido

## Evidencia Aspire (2026-09-06/07)

- `rc4_release_gate.py` → PASS
- preflight: RAM ~7 GB, ODS detectado, Ollama presente
- `measured_chain … --model-id demo` → `measured: false`
- modelos OBSERVED: `hermes3:latest`, `qwen2.5:0.5b-instruct-q4_K_M`
- instalar pytest si falta: `pip install --user pytest`

## Validación física (Ubuntu)

```bash
ollama list
python3 scripts/rc4_fitllm_recommend.py --purpose programming --json > /tmp/rec.json
python3 scripts/rc4_measured_chain.py \
  --recommendation /tmp/rec.json \
  --model-id qwen2.5:0.5b-instruct-q4_K_M \
  --stack none \
  --execute --authorize-execution --authorize-measurement \
  --out results/physical-rc4-measured/chain.json
```

Solo entonces `measured` puede ser `true`. RC4 fase **no** se cierra hasta ese E2E.
