# LEONES

## Estado del proyecto

| Bloque | Estado | Resultado |
|---|---|---|
| V1 / A01 | 🟢 Cerrado | Cadena real de selección → ejecución → benchmark → evidencia |
| JALÓN 1 | 🟢 Cerrado | Base CI y contratos iniciales |
| JALÓN 2 | 🟢 Cerrado | Ejecución física + evidencia reproducible con llama.cpp |
| JALÓN 3 | 🟢 Cerrado | Contrato de medición real + auditoría física |
| JALÓN 4 | 🟢 **Cerrado** | Metodología AA + contratos de integración + benchmark de tareas + tiers |
| RC1 | 🟢 **Validado** | Ejecución efectiva end-to-end |
| RC2 | 🟢 **Histórica** | Beta previa; no es el camino canónico RC3 |
| **RC3** | 🟢 **CERRADA** (impl. + contratos + web + obs. física parcial Aspire) · medición completa = backlog | **`hardware_profile.py` → candidatos → Magnitude/ODS → medición LEONES** |
| **RC4** | 🟡 **Decisión fijada · implementación pendiente** | **FitLLM recomendador opcional → elección humana → Magnitude/ODS → Leo001…Leo010** |

## RC4 — recomendador FitLLM (en curso)

**Regla de autoridad RC4:** LEONES descubre el hardware. FitLLM puede recomendar (ESTIMATED). El usuario elige modelo y stack. Magnitude u ODS preparan/ejecutan. LEONES verifica, mide y sentencia.

- FitLLM **no** es dependencia dura de arranque; sin él se puede elegir modelo a mano.
- Hermes y OMH son **opcionales** (agente/ops), no selectores de modelo.
- Tras instalar Magnitude u ODS se puede **ofrecer** desinstalar FitLLM (opt-in).
- Suite **Leo001…Leo010** se conserva para medición.
- Acta: `docs/completed/RC4-DECISION-FITLLM-RECOMMENDER-2026-09-06.md` · Contrato: `docs/RC4-ARCHITECTURE.md`

## RC3 — arquitectura canónica (fase cerrada)

RC3 simplifica deliberadamente el camino de instalación y selección. **La sonda física canónica es `scripts/hardware_profile.py`.** Hermes participa como ecosistema local de runtime/model-fit y Oh My Hermes (OMH) como capa operativa de routing, workflows, handoffs y gates. LEONES normaliza, reconcilia y conserva la autoridad sobre verificación física, ejecución, medición y evidencia.

### Regla de autoridad (RC3)

**LEONES descubre el hardware. OMH organiza. El usuario elige. Magnitude u ODS preparan/ejecutan. LEONES verifica, mide y sentencia.**

### Handoff de usuario

- **Magnitude** → perfilado, tuning y ejecución por sus interfaces canónicas.
- **ODS** → instalación y stack local por sus interfaces canónicas.

## Instalación (contexto RC3 / transición RC4)

```text
INSTALAR LEONES
      ↓
scripts/hardware_profile.py
      ↓
hardware-profile.v1 → candidate-set.v1
      ↓
FitLLM (opcional, RC4) → recomendación ESTIMATED
      ↓
ELEGIR MODELO (con o sin recomendación)
      ↓
ELEGIR MAGNITUDE U ODS
      ↓
CONSENTIMIENTO → PREPARAR / INSTALAR
      ↓
[opcional] ofrecer desinstalar FitLLM
      ↓
VERIFICAR FÍSICAMENTE
      ↓
Leo001…Leo010 → MEDIR → EVIDENCIA
```

```bash
hermes doctor   # si están instalados
omh doctor
```

## Gate

RC3: `scripts/rc3_release_gate.py`. El gate **no** declara handoffs ni MEASURED físicos.
RC4: gate propio pendiente de implementación (FitLLM no hard-dep; Hermes no selector).

## RC2

RC2 permanece como línea histórica de validación.

## Interfaz de usuario

Norma de proyecto (idioma, consentimientos, estados, errores): [`docs/LEONES-INTERFACE-RULES.md`](docs/LEONES-INTERFACE-RULES.md).

## Principio LEONES

> **Los proveedores pueden proponer. FitLLM puede recomendar. El usuario elige. Solo una ejecución controlada sobre el equipo real puede producir una medición LEONES.**

RC3 está **cerrada como fase**. Ver `docs/completed/RC3-CLOSED-2026-09-05.md`. **RC4** redefine el tramo de recomendación de modelo; ver `docs/RC4-ARCHITECTURE.md`.
