# Guía: wizard RC2 (`./leones`)

**Estado:** implementado · operador canónico del beta tester

## Propósito

Conducir a un humano desde hardware real hasta una decisión explícita de
medir A01, sin convertir ninguna aceptación genérica en autorización de
ejecución.

## Qué NO hace

- No sustituye LLMFit, ODS ni Magnitude.
- No inventa PASS de verificación ni MEASURED de benchmark.
- No es un segundo runner: la medición la hace el pipeline RC1.

## Cómo arrancar

```bash
./install.sh   # exige llmfit en PATH
./leones
```

## Flujo de datos

```text
LLMFit (system + recommend)
        ↓
candidatos ESTIMATED
        ↓
elección humana (modelo + stack)
        ↓
consentimiento instalación
        ↓
verify_physical (observa host)
        ↓
consentimiento A01
        ↓
a01_runtime_benchmark + ollama_a01_runtime
        ↓
evidence en .leones/rc2-a01/
```

## Scripts principales

| Script | Función |
|--------|---------|
| `scripts/rc2_wizard.py` | Máquina de diálogo y orquestación |
| `scripts/rc2_beta_session.py` | Gates y estados |
| `scripts/rc2_i18n.py` | Catálogo ES/EN/ZH |
| `scripts/integrations/verify_physical.py` | PASS/FAIL real del stack |
| `scripts/a01_runtime_benchmark.py` | Medición canónica |
| `scripts/ollama_a01_runtime.py` | Puente modelo local → contrato A01 |

## Invariantes

1. Un idioma por sesión tras la primera pregunta.
2. `real_installation` solo con observación física.
3. A01 solo tras consentimiento específico.
4. Sin Ollama → bloqueo, no medición falsa.

## Mantenimiento

- Añadir cadenas: `scripts/rc2_i18n.py` + test de catálogo.
- Cambiar gates: `rc2_beta_session.py` + tests de transición.
- Cambiar checks físicos: `verify_physical.py` + `tests/test_verify_physical.py`.

## Documentos de contrato

- `docs/RC2-L-INTEGRATED-BETA-JOURNEY.md`
- `docs/RC2-G-END-TO-END-BETA-FLOW.md`
- `docs/RC2-F-BENCHMARK-CONSENT.md`
- `docs/RC2-K-MULTILINGUAL-UI.md`
- `docs/RC2-H-STACK-CAPABILITY-PRESENTATION.md`
