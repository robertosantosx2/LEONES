# RC4 · Decisión: FitLLM como preselector de modelo

**Fecha:** 2026-09-06  
**Estado:** 🟢 Decisión de arquitectura fijada  
**Predecesor:** RC3 (fase **CERRADA**; no se reabre)

## 1. Motivo

RC3 cerró con sonda LEONES, contratos, web y observación física parcial.
La línea experimental *Hermes-only selector* (`rc3-hermes-task-benchmarks`)
no se promueve a canónica. RC4 redefine el tramo de **preselección de modelo**.

## 2. Decisiones

1. **FitLLM / LLMFit es el preselector de RC4, no una autoridad.**
   - Produce una preselección de **3 LLM candidatos**.
   - La señal es ESTIMATED (fit / ranking).
   - No autoriza ejecución, no mide y no genera MEASURED.
   - El usuario puede elegir uno de los candidatos o un modelo válido fuera de la preselección.

2. **LEONES arranca sin FitLLM.**
   - FitLLM no es dependencia dura de `./install.sh`.
   - Si el usuario pide preselección y FitLLM no está: error claro en ese paso; el resto del producto sigue disponible.

3. **Hermes y OMH no forman parte de RC4.**
   - No seleccionan modelo.
   - No recomiendan modelos.
   - No participan en el camino canónico de preparación, ejecución o medición RC4.
   - Su arquitectura histórica no se reutiliza como capa oculta de RC4.

4. **Tras instalar Magnitude u ODS, ofrecer desinstalar FitLLM.**
   - Motivación: FitLLM ya no aporta al camino de ejecución local una vez tomada la decisión de modelo.
   - La desinstalación es **opt-in** (nunca silenciosa).
   - No borrar evidencia ni perfiles LEONES al quitar FitLLM.

5. **Suite Leo001…Leo010 se conserva** como protocolo de medición/comparación.
   - Solo cambia quién propone/preselecciona el modelo antes del loop.
   - Sin ejecución real: NOT CLAIMED / no MEASURED.

6. **RC3 permanece CERRADA.**
   - Documentos y tags de cierre RC3 no se reescriben como “abierta”.
   - RC4 es fase nueva con su propio contrato y gate.

## 3. Flujo canónico RC4

```text
UBUNTU / EQUIPO REAL
        ↓
scripts/hardware_profile.py     (sonda LEONES, obligatoria)
        ↓
hardware-profile.v1
        ↓
candidate-set.v1                (LEONES; sin measured_tps)
        ↓
FitLLM / LLMFit                  (3 candidatos · ESTIMATED)
        ↓
elección humana: modelo
        ↓
elección humana: Magnitude | ODS
        ↓
consentimiento
        ↓
preparar / instalar stack
        ↓
[opcional] ofrecer quitar FitLLM
        ↓
verificar físicamente
        ↓
Leo001 … Leo010
        ↓
medición → evidencia → recomendación final
```

## 4. Regla de autoridad

**LEONES descubre el hardware. FitLLM preselecciona 3 candidatos. El usuario elige modelo y stack. Magnitude u ODS preparan/ejecutan. LEONES verifica, mide y sentencia.**

## 5. Fuera de alcance de esta decisión

- Implementación completa del adaptador FitLLM.
- Reescritura del release gate (commits de implementación posteriores).
- Validación física MEASURED en Ubuntu.
- Promoción de la rama Hermes-selector a main.

## 6. Criterios de aceptación (implementación posterior)

- [ ] Docs RC4 + README + web operador alineados.
- [ ] Gate: FitLLM opcional y no hard-dep; Hermes/OMH fuera del camino canónico RC4.
- [ ] Sin FitLLM: arranque OK; preselección degradada con mensaje explícito.
- [ ] Con FitLLM: exactamente 3 candidatas/preselección sin `execution_authorized` y sin MEASURED.
- [ ] Post-install Magnitude/ODS: prompt opt-in para desinstalar FitLLM.
- [ ] Leo001…Leo010 siguen referenciados como suite de medición.

## 7. Procedencia

- RC3 cierre: `docs/completed/RC3-CLOSED-2026-09-05.md`
- RC3 arquitectura: `docs/RC3-ARCHITECTURE.md`
- Esta decisión: acta fijada el 2026-09-06
