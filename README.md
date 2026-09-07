# LEONES

**Local Ecosystem of Open Neural Expert Systems**

IA local con criterio: descubrir, estimar, elegir, preparar, verificar, medir y evidenciar — sin confundir ESTIMATED con MEASURED.

| Fase | Estado | Nota |
|------|--------|------|
| **RC4** | 🟡 **En desarrollo** | Decisión fijada · capa de recomendación endurecida · orquestador MEASURED listo · **E2E físico pendiente** |
| **RC3** | 🟢 **Fase cerrada** (2026-09-05) | Sonda LEONES + elección Magnitude/ODS; handoffs MEASURED no incluidos en el cierre |

## RC4 — estado actual (2026-09-07)

**Regla de autoridad:** LEONES descubre el hardware y conserva procedencia. FitLLM/LLMFit es preselector **opcional** (ESTIMATED). El usuario elige modelo y stack. Magnitude u ODS preparan/ejecutan. Solo una ejecución física autorizada produce MEASURED.

### Implementado

- `USER_INTENT[]` obligatorio · feed HF + Artificial Analysis ≤100 · intersección con CLI LLMFit
- hasta 3 candidatos ESTIMATED o `insufficient` (sin padding)
- `scripts/rc4_release_gate.py` · `scripts/rc4_ubuntu_preflight.py` · `scripts/rc4_resource_preflight.py`
- inventario y desinstalación independiente: `scripts/rc4_component_inventory.py` · `scripts/uninstall.sh`
- cadena post-recomendación: `scripts/rc4_measured_chain.py` (selección humana → stack → runtime → A01 → MEASURED)
- `install.sh` instala/verifica las piezas RC4: **FitLLM/LLMFit + Osmantic ODS + Magnitude**

### Evidencia Aspire (Ubuntu)

- 2026-09-06: release gate PASS · tests contractuales PASS · preflight `insufficient` (1/3) en ~7 GB RAM
- 2026-09-06/07: `measured_chain` con `measured: false` sin autorización/ejecución; Ollama presente (`hermes3:latest`, `qwen2.5:0.5b-instruct-q4_K_M`)

### Pendiente de fase

- MEASURED E2E en host real con modelo instalado + doble autorización
- Acta: `docs/completed/RC4-DECISION-FITLLM-RECOMMENDER-2026-09-06.md`
- Contrato: `docs/RC4-ARCHITECTURE.md`
- STRICT cadena: `docs/completed/RC4-STRICT-MEASURED-CHAIN-2026-09-07.md`

## Arranque

```bash
git clone https://github.com/robertosantosx2/LEONES.git
cd LEONES
git checkout rc4-fitllm-recommender
./install.sh             # instala/verifica FitLLM + ODS + Magnitude
./leones                 # RC4: inventario + intención + recomendación
./leones --inventory     # solo inventario / ofertas de uninstall
./leones --rc2           # wizard histórico RC2
```

### Bootstrap RC4

`./install.sh` usa los instaladores oficiales de cada componente y evita instalaciones Python globales para LLMFit. ODS requiere Docker operativo. Magnitude requiere Node.js/npm. Si un componente ya existe, se conserva y se verifica en lugar de reinstalarlo.

Componentes instalados/verificados:

- **FitLLM / LLMFit** — preselector ESTIMATED; no autoriza ejecución ni medición.
- **Osmantic ODS** — stack de ejecución/aplicación; su instalador oficial gestiona la pila.
- **Magnitude** — stack/agente de ejecución; se instala como `@magnitudedev/cli`.
- Hermes / Oh My Hermes — capas opcionales conservadas del bootstrap anterior.

### Preflight y cadena MEASURED

```bash
python3 scripts/rc4_release_gate.py
python3 scripts/rc4_resource_preflight.py --path .
python3 scripts/rc4_ubuntu_preflight.py \
  --purpose programming --purpose reasoning \
  --out results/physical-rc4-$(date +%Y%m%d)/ubuntu-preflight.json

# plan (measured=false)
python3 scripts/rc4_measured_chain.py --model-id demo --stack none --json

# E2E físico (sustituir por un modelo REAL de `ollama list`)
python3 scripts/rc4_fitllm_recommend.py --purpose programming --json > /tmp/rec.json
python3 scripts/rc4_measured_chain.py \
  --recommendation /tmp/rec.json \
  --model-id qwen2.5:0.5b-instruct-q4_K_M \
  --stack none \
  --execute --authorize-execution --authorize-measurement \
  --out results/physical-rc4-measured/chain.json
```

Tests (requieren `pytest`):

```bash
python3 -m pip install --user pytest   # si no está
python3 -m pytest tests/test_rc4_component_inventory.py tests/test_rc4_fitllm_recommend.py -q
```

## Cadena canónica

```text
USER_INTENT[]
      ↓
resource + ubuntu preflight
      ↓
HF + AA → feed ≤100 → LLMFit CLI → intersección → ≤3 ESTIMATED | insufficient
      ↓
selección humana → stack (Magnitude|ODS|none) → runtime → A01 → MEASURED
```

Desinstalación independiente (LEONES al final):

```bash
bash scripts/uninstall.sh --dry-run --fitllm
bash scripts/uninstall.sh   # menú interactivo
```

## Gate

- RC3: `scripts/rc3_release_gate.py` (no declara MEASURED físicos)
- RC4: `scripts/rc4_release_gate.py` — **implementado**; no declara MEASURED hasta evidencia física

## Principio LEONES

> **Los proveedores pueden proponer. FitLLM puede recomendar. El usuario elige. Solo una ejecución controlada sobre el equipo real puede producir una medición LEONES.**

Web: `web/estado.html` · `web/rc4.html` · `web/inicio-rapido.html` · `web/operacion.html`
