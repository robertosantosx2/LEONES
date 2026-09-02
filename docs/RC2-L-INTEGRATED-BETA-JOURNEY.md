# RC2-L — Recorrido beta integrado

**Estado:** 🟢 Implementado en el operador canónico (`./leones` → `scripts/rc2_wizard.py`)

## Fuente canónica

| Rol | Ruta |
|-----|------|
| Operador único del beta tester | `./leones` |
| Implementación | `scripts/rc2_wizard.py` |
| Sesión / gates | `scripts/rc2_beta_session.py` |
| i18n (un idioma por sesión) | `scripts/rc2_i18n.py` |
| Verificación física | `scripts/integrations/verify_physical.py` |
| Medición A01 | `scripts/a01_runtime_benchmark.py` + `scripts/ollama_a01_runtime.py` |
| Mapa visual (no ejecuta) | `scripts/rc2_ui.py` |

No hay un segundo wizard ni un segundo runner de benchmark.

## Recorrido implementado

```text
IDIOMA (es | en | zh)     ← se elige una vez; el resto usa solo ese idioma
        ↓
HARDWARE + CANDIDATOS     ← LLMFit en vivo (ESTIMATED)
        ↓
MODELO                    ← decisión humana
        ↓
ODS / MAGNITUDE           ← resumen + capacidades en el menú
        ↓
CONSENTIMIENTO INSTALAR
        ↓
INSTALADOR CANÓNICO       ← opcional (sí ahora / más tarde)
        ↓
VERIFICACIÓN FÍSICA       ← observa el host; exit 0 ≠ PASS
        ↓
¿A01?
   ├── NO → READY_FOR_BENCHMARK (nada medido)
   └── SÍ → handoff RC1
                 ↓
           Ollama A01 bridge (si ollama en PATH)
                 ↓
           measured → evidence en .leones/rc2-a01/
                 ↓
              COMPLETE
```

## Invariantes

1. `ESTIMATED ≠ MEASURED`
2. Autorizar instalación ≠ instalar ≠ verificar ≠ autorizar benchmark
3. Sin `real_installation: true` no hay benchmark
4. Sin consentimiento A01 no hay ejecución
5. Sin Ollama local, A01 queda `benchmark_blocked` (no se inventa MEASURED)
6. Un fallo no se publica como medición válida

## Hecho vs abierto

**Hecho implementado**

- elección de idioma única;
- resúmenes de stack en el menú;
- resumen post-consentimiento + comando de instalador;
- verificación física ODS/Magnitude;
- explicación y consentimiento A01;
- handoff y intento real vía runner RC1 + puente Ollama.

**Limitaciones conocidas**

- A01 físico requiere `ollama` en PATH y el modelo disponible localmente;
- la verificación ODS exige señal específica (CLI `ods` o imagen Docker con “ods”);
- la reanudación desde estado persistido aún no está implementada como producto.
