# LEONES

**Local Ecosystem of Open Neural Expert Systems**

IA local con criterio: descubrir, estimar, elegir, preparar, verificar, medir y evidenciar — sin confundir ESTIMATED con MEASURED.

## Perfiles y benchmarks de hardware

- Equipo de pruebas Ubuntu MSI Thin 15 B12UC: [perfil de hardware y software](hardware/UBUNTU-MSI-THIN-15-B12UC.md).
- TwIL-8B Q4_K_M en RTX 3050 Laptop con llama.cpp CUDA: [informe de benchmark y metodología](docs/TWIL-8B-Q4_K_M-RTX3050-2026-11-05.md).
- Pithos 0.5.0 + LFM3-1.7B Q4_K_M en RTX 3050 Laptop con Vulkan: [informe de ejecución y benchmark](docs/PITHOS-LFM3-1.7B-RTX3050-2026-11-06.md).
- Pithos 0.5.1 + LFM3-1.7B Q4_K_M: [comparativa CPU/Intel Vulkan/NVIDIA Vulkan y barrido PP/TG](docs/PITHOS-LFM3-1.7B-RTX3050-2026-11-07.md), con [CSV](artifacts/pithos-0.5.1-2026-11-07/benchmark-results.csv), [registro consolidado](artifacts/pithos-0.5.1-2026-11-07/benchmark-session.log) y [script reproducible](artifacts/pithos-0.5.1-2026-11-07/reproduce.sh).
- MiniCPM5-2B Q4_K_M en RTX 3050 Laptop con llama.cpp CUDA: [informe de benchmark MEASURED y evaluación de viabilidad DSpark](docs/MINICPM5-2B-RTX3050-2026-11-11.md).

## Registro extensible de motores y copias de código fuente

- [Registro de motores](configs/engines.registry.json): identidad, repositorio oficial, formato de modelo y estado de cada fuente.
- [Contrato de adaptadores](docs/ENGINE-ADAPTER-CONTRACT.md): cómo añadir motores sin modificar el núcleo del benchmark.
- [Política de copias reproducibles](docs/ENGINE-SOURCE-VENDORING.md): snapshots completos, commit/tree SHA, submódulos, Git LFS y licencias.
- [Vendor de fuentes](scripts/vendor_engines.py): crea `third_party/engines/<id>/source/<commit>/` y `SOURCE.json` sin sobrescribir snapshots anteriores.\n- [Captura de compilación](scripts/capture_engine_build.py): registra binario, hash, comando, log, compilador, backend y entorno.
- [Workflow GitHub Actions](.github/workflows/vendor-inference-engines.yml): importa las copias directamente en GitHub y las confirma en esta rama.

Motores registrados: Kinetic, TensorFold, Tandem.cpp/llama.cpp y RustInstrata. Las fuentes sin URL upstream verificada quedan marcadas como pendientes; nunca se sustituye una bifurcación local por el upstream sin declararlo.

## Kinetic — auditoría y benchmark cruzado (2026-11-11)

- Copia del código upstream Apache-2.0: `scripts/import_kinetic.sh` (compatibilidad) o `scripts/vendor_engines.py --engine kinetic` → `third_party/engines/kinetic/source/<commit>/`; el SHA y el árbol quedan registrados en `SOURCE.json`.
- [Auditoría estática preliminar](docs/KINETIC-SOURCE-AUDIT-2026-11-11.md).
- [Plan de benchmark Kinetic / TensorFold / Tandem.cpp / RustInstrata](docs/KINETIC-CROSS-ENGINE-BENCHMARK-PLAN-2026-11-11.md).
- [Harness serial con control de recuperación de recursos](scripts/engine_comparison.py).
- [Configuración de ejemplo](configs/engine-comparison.example.json).

Estado: plan y harness preparados; todavía no se han ejecutado pruebas comparativas en la MSI. Los adaptadores de TensorFold y RustInstrata requieren confirmar sus comandos de servidor locales antes de habilitarlos. Las mediciones se etiquetarán MEASURED solo tras ejecución física y conservación de logs.

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

## RC4 Beta

La rama `rc4-fitllm-recommender` dispone de una guía específica para los beta testers:

- `docs/RC4-BETA-TESTERS.md`

La beta debe tratar toda recomendación como `ESTIMATED` y toda medición como evidencia producida por una ejecución física real. No se deben reutilizar resultados de otras máquinas como mediciones propias.

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
