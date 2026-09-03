# RC2-L — Recorrido beta integrado

**Estado:** 🟢 Implementado en el operador canónico (`./leones` → `scripts/rc2_wizard.py`)

## Fuente canónica

| Rol | Ruta |
|-----|------|
| Operador único del beta tester | `./leones` |
| Implementación | `scripts/rc2_wizard.py` |
| Sesión / gates | `scripts/rc2_beta_session.py` |
| i18n (un idioma por sesión) | `scripts/rc2_i18n.py` |
| Verificación física del stack | `scripts/integrations/verify_physical.py` |
| Resolución modelo → runtime | `runtime_selection/model_runtime_resolver.py` |
| Preflight Ollama | `scripts/a01_runtime_preflight.py` |
| Medición A01 | `scripts/a01_runtime_benchmark.py` |
| Puente Ollama | `scripts/ollama_a01_runtime.py` |
| Puente llama.cpp | `scripts/llama_cpp_a01_runtime.py` |
| Mapa visual (no ejecuta) | `scripts/rc2_ui.py` |

No hay un segundo wizard ni un segundo runner de benchmark.

## Recorrido implementado

```text
IDIOMA (es | en | zh)          ← una vez; el resto usa solo ese idioma
        ↓
HARDWARE + CANDIDATOS          ← LLMFit en vivo (ESTIMATED)
        ↓
MODELO                         ← decisión humana
        ↓
ODS / MAGNITUDE                ← resumen en el menú
        ↓
CONSENTIMIENTO INSTALAR
        ↓
INSTALADOR CANÓNICO            ← opcional (ahora / más tarde)
        ↓
VERIFICACIÓN FÍSICA DEL STACK  ← observa host; exit 0 ≠ PASS
        ↓
RESOLUCIÓN MODELO → RUNTIME    ← declarativa; no descarga
        ↓
PREFLIGHT RUNTIME/ARTEFACTO    ← Ollama model o llama-cli + ref
        ↓
¿A01?
   ├── NO → READY_FOR_BENCHMARK (nada medido)
   └── SÍ → handoff RC1 → measured → evidence (.leones/rc2-a01/)
```

## Invariantes

1. `ESTIMATED ≠ MEASURED`
2. Autorizar instalación ≠ instalar ≠ verificar stack ≠ resolver runtime ≠ autorizar benchmark
3. Sin `real_installation: true` del stack no hay benchmark
4. Un id GGUF/HF no se convierte silenciosamente en nombre Ollama
5. Sin runtime/artefacto disponible → `benchmark_blocked`, no MEASURED inventado
6. Un fallo no se publica como medición válida

## Hecho vs abierto

**Hecho**

- idioma único por sesión;
- resúmenes de stack;
- verify física ODS/Magnitude;
- resolución modelo→runtime;
- preflight Ollama / llama.cpp;
- consentimiento A01 + runner RC1.

**Abierto**

- reanudación de sesión persistida;
- más adaptadores A01 además de Ollama y llama.cpp;
- preparación autorizada de artefactos GGUF cuando aún no existen en el host.
