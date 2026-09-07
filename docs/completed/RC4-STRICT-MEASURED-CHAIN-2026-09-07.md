# RC4 STRICT — cadena selección humana → stack → runtime → Leo/A01 → MEASURED

**Fecha:** 2026-09-07  
**Modo:** limpia, fija y da esplendor  
**Rama:** `rc4-fitllm-recommender`

## Problema

La capa de recomendación produce solo `ESTIMATED`. Faltaba un orquestador canónico que:

1. no auto-ejecute desde la recomendación;
2. exija selección humana de `model_id`;
3. registre stack (`magnitude|ods|none`);
4. observe runtime (A01/Ollama) sin inventar comandos;
5. exija doble autorización (`--authorize-execution` + `--authorize-measurement`);
6. marque `measured=true` solo tras ejecución real exitosa.

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
- `execution_authorized` y `measurement_authorized` son opt-in
- Hermes/OMH no seleccionan modelo
- Ollama runtime no se desinstala por defecto; modelos sí (`--llms`)
- LEONES (`.leones/`) se ofrece al final del uninstall

## Validación sin host físico

```bash
python3 -m pytest tests/test_rc4_component_inventory.py -q
python3 scripts/rc4_resource_preflight.py --path . | head
python3 scripts/rc4_measured_chain.py --model-id demo --stack none --json
# measured debe ser false sin --execute
```

## Validación física (Ubuntu)

```bash
python3 scripts/rc4_fitllm_recommend.py --purpose programming --json > /tmp/rec.json
python3 scripts/rc4_measured_chain.py \
  --recommendation /tmp/rec.json \
  --model-id <id_instalado_en_ollama> \
  --stack none \
  --execute --authorize-execution --authorize-measurement \
  --out results/physical-rc4-measured/chain.json
```

Solo entonces `measured` puede ser `true`.

## Cierre STRICT de esta pieza

- Contrato + script + tests de inventario + docs + web alineada.
- **No** se declara RC4 fase cerrada: el MEASURED E2E en host real sigue siendo el gate final de fase.
