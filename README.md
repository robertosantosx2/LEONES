# LEONES

**Local Ecosystem of Open Neural Expert Systems**

IA local con criterio: descubrir, estimar, elegir, preparar, verificar, medir y evidenciar — sin confundir ESTIMATED con MEASURED.

## RC4 — estado actual (2026-09-07)

**Regla de autoridad:** LEONES descubre el hardware y conserva procedencia. FitLLM/LLMFit es preselector (ESTIMATED). El usuario elige modelo y stack. Solo una ejecución física autorizada produce MEASURED.

### Flujo TUI fijado

```text
IDIOMA
  ↓
ESTADO DE LA MÁQUINA
  ├─ Hardware
  ├─ RAM / CPU / DISCO
  └─ IA instalada
       ├─ FitLLM
       ├─ ODS
       ├─ Magnitude
       ├─ LLMs
       └─ Agentes / harnesses
  ↓
si FitLLM falta → INSTALAR FitLLM
  ↓
PROPÓSITO(S) · selección múltiple
  ↓
HF + Artificial Analysis
  ↓
RECOMENDACIÓN FitLLM
  ↓
SELECCIÓN HUMANA
  ↓
STACK
  ├─ gestionar / instalar
  │    ├─ LLMs seleccionados
  │    ├─ instalar LLM concreto (ruta completa del fichero)
  │    ├─ ODS
  │    ├─ Magnitude
  │    └─ otros
  └─ desinstalar
       ├─ modelo
       ├─ FitLLM
       ├─ Magnitude
       └─ ODS
  ↓
RUNTIME
  ↓
BENCHMARK A01 → MEASURED
```

**No existe bootstrap obligatorio de todos los componentes.** `install.sh` solo instala el componente solicitado mediante `--fitllm`, `--ods`, `--magnitude`, etc. `--all` queda como operación explícita, no como comportamiento por defecto.

### Implementado

- `USER_INTENT[]` obligatorio · feed HF + Artificial Analysis ≤100 · intersección con CLI LLMFit.
- Hasta 3 candidatos ESTIMATED o `insufficient` (sin padding).
- Estado de máquina e inventario de componentes dentro de la TUI.
- Instalación bajo demanda desde la TUI para FitLLM, ODS y Magnitude.
- Gestión independiente de LLMs, ODS, Magnitude y otros componentes.
- Desinstalación independiente; LEONES se conserva como último nivel.
- Cadena post-recomendación: selección humana → stack → runtime → A01 → MEASURED.

## Arranque

```bash
git clone https://github.com/robertosantosx2/LEONES.git
cd LEONES
git checkout rc4-fitllm-recommender
./leones
```

Instalación explícita, si se desea hacerla fuera de la TUI:

```bash
./install.sh --fitllm
./install.sh --ods
./install.sh --magnitude
```

`./install.sh` sin argumentos **no instala nada** y muestra su ayuda.

## Evidencia y gate

- RC4: `scripts/rc4_release_gate.py`.
- Contrato: `docs/RC4-ARCHITECTURE.md`.
- Cadena estricta: `docs/completed/RC4-STRICT-MEASURED-CHAIN-2026-09-07.md`.
- E2E físico MEASURED sigue pendiente.

## Principio LEONES

> **Los proveedores pueden proponer. FitLLM puede recomendar. El usuario elige. Solo una ejecución controlada sobre el equipo real puede producir una medición LEONES.**

Web: `web/estado.html` · `web/rc4.html` · `web/inicio-rapido.html` · `web/operacion.html`
