# LEONES — instalación mínima (RC4)

La instalación debe ser pequeña: **Git + Python 3.10+**. LEONES no instala automáticamente ODS, Magnitude ni modelos.

## 0. FitLLM / LLMFit — opcional (RC4)

**En RC4, FitLLM no es dependencia dura de arranque.**

- Si está en el PATH (`llmfit`), participa en la intersección ESTIMATED.
- Si no está, LEONES arranca; la recomendación puede quedar `insufficient` o sin candidatos de intersección.
- Sus cifras son **ESTIMATED**, nunca MEASURED.

Instalación opcional:

```bash
curl -fsSL https://llmfit.axjns.dev/install.sh | sh -s -- --local
# o: uv tool install -U llmfit
command -v llmfit && llmfit --version
```

## 1. Descargar LEONES

```bash
git clone https://github.com/robertosantosx2/LEONES.git
cd LEONES
git checkout rc4-fitllm-recommender
```

## 2. Preparar (si existe install.sh)

```bash
./install.sh   # comprueba Python/Git; no debe exigir FitLLM como hard-dep en RC4
```

## 3. Ejecutar

```bash
./leones              # RC4: inventario + intención + recomendación
./leones --inventory  # solo inventario / ofertas uninstall
./leones --rc2        # wizard histórico
```

## 4. Preflight y MEASURED (Ubuntu)

```bash
python3 scripts/rc4_release_gate.py
python3 scripts/rc4_resource_preflight.py --path .
python3 scripts/rc4_measured_chain.py --model-id demo --stack none --json
# measured debe ser false sin --execute
```

E2E físico: model_id exacto de `ollama list` +
`--execute --authorize-execution --authorize-measurement`.

## Requisitos

- Linux recomendado para validación física.
- Git · Python 3.10+.
- FitLLM opcional · Ollama/runtime según medición.
- Internet cuando el stack o el feed lo necesiten.

## Regla

ESTIMATED ≠ MEASURED. El usuario elige. Solo la ejecución autorizada produce medición LEONES.
