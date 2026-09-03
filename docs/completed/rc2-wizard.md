# Guía: wizard RC2 (`./leones`)

**Estado:** implementado · operador canónico del beta tester

## Propósito

Conducir a un humano desde hardware real hasta una decisión explícita de
medir A01, sin convertir ninguna aceptación genérica en autorización de
ejecución.

## Qué NO hace

- No sustituye LLMFit, ODS ni Magnitude.
- No inventa PASS de verificación ni MEASURED de benchmark.
- No convierte un id Hugging Face/GGUF en un modelo Ollama.
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
consentimiento instalación + verify_physical
        ↓
model_runtime_resolver (declarativo)
        ↓
preflight runtime/artefacto
        ↓
consentimiento A01
        ↓
a01_runtime_benchmark + (ollama | llama.cpp) bridge
        ↓
evidence en .leones/rc2-a01/
```

## Scripts principales

| Script | Función |
|--------|---------|
| `scripts/rc2_wizard.py` | Operador / diálogo |
| `scripts/rc2_beta_session.py` | Gates |
| `scripts/rc2_i18n.py` | Catálogo ES/EN/ZH |
| `scripts/integrations/verify_physical.py` | Stack PASS/FAIL |
| `runtime_selection/model_runtime_resolver.py` | Modelo → runtime |
| `scripts/a01_runtime_preflight.py` | Ollama model check |
| `scripts/a01_runtime_benchmark.py` | Medición canónica |
| `scripts/ollama_a01_runtime.py` | Puente Ollama |
| `scripts/llama_cpp_a01_runtime.py` | Puente llama.cpp |

## Invariantes

1. Un idioma por sesión.
2. `real_installation` solo con observación física del stack.
3. Resolución ≠ instalación ≠ medición.
4. A01 solo tras consentimiento específico.
5. Runtime/artefacto ausente → bloqueo, no medición falsa.

## Documentos de contrato

- `docs/RC2-L-INTEGRATED-BETA-JOURNEY.md`
- `docs/RC2-G-END-TO-END-BETA-FLOW.md`
- `docs/RC2-F-BENCHMARK-CONSENT.md`
- `docs/RC2-K-MULTILINGUAL-UI.md`
- `docs/RC2-H-STACK-CAPABILITY-PRESENTATION.md`
