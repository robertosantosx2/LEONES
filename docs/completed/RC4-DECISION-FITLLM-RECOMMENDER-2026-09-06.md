# RC4 · Decisión: FitLLM como recomendador de modelo

**Fecha:** 2026-09-06  
**Estado:** 🟡 Decisión de arquitectura fijada · implementación pendiente  
**Predecesor:** RC3 (fase **CERRADA**; no se reabre)

## 1. Motivo

RC3 cerró con sonda LEONES, contratos, web y observación física parcial.
La línea experimental *Hermes-only selector* (`rc3-hermes-task-benchmarks`)
no se promueve a canónica. RC4 redefine el tramo de **recomendación de modelo**.

## 2. Decisiones

1. **FitLLM / LLMFit es recomendador, no autoridad.**
   - Produce orientación ESTIMATED (ranking / fit).
   - No autoriza ejecución ni genera MEASURED.
   - El usuario puede elegir modelo **sin** FitLLM.

2. **LEONES arranca sin FitLLM.**
   - FitLLM no es dependencia dura de `./install.sh`.
   - Si el usuario pide recomendación y FitLLM no está: error claro en ese paso; el resto del producto sigue disponible.

3. **Hermes y OMH son opcionales.**
   - No seleccionan modelo en RC4.
   - Pueden usarse como agente / operación.
   - La interfaz debe explicar: función, peso en disco, RAM si se ejecutan, y si dejan procesos residentes o daemons.

4. **Tras instalar Magnitude u ODS, ofrecer desinstalar FitLLM.**
   - Motivación: FitLLM ya no aporta al camino de ejecución local.
   - La desinstalación es **opt-in** (nunca silenciosa).
   - No borrar evidencia ni perfiles LEONES al quitar FitLLM.

5. **Suite Leo001…Leo010 se conserva** como protocolo de medición/comparación.
   - Solo cambia quién **propone** el modelo antes del loop.
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
FitLLM (opcional)               (recomendación ESTIMATED)
        ↓
elección humana: modelo         (con o sin recomendación)
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

**LEONES descubre el hardware. FitLLM puede recomendar. El usuario elige modelo y stack. Magnitude u ODS preparan/ejecutan. LEONES verifica, mide y sentencia.**

## 5. Fuera de alcance de esta decisión

- Implementación completa del adaptador FitLLM.
- Reescritura del release gate (commits de implementación posteriores).
- Validación física MEASURED en Ubuntu.
- Promoción de la rama Hermes-selector a main.

## 6. Criterios de aceptación (implementación posterior)

- [ ] Docs RC4 + README + web operador alineados.
- [ ] Gate: FitLLM no hard-dep; Hermes no es selector canónico RC4.
- [ ] Sin FitLLM: arranque OK; recomendación degradada con mensaje explícito.
- [ ] Con FitLLM: candidatas/recomendación sin `execution_authorized` / sin MEASURED.
- [ ] Post-install Magnitude/ODS: prompt opt-in para desinstalar FitLLM.
- [ ] UI opcional Hermes/OMH: texto de peso disco/RAM/residencia.
- [ ] Leo001…Leo010 siguen referenciados como suite de medición.

## 7. Procedencia

- RC3 cierre: `docs/completed/RC3-CLOSED-2026-09-05.md`
- RC3 arquitectura: `docs/RC3-ARCHITECTURE.md`
- Esta decisión: `docs/completed/RC4-DECISION-FITLLM-RECOMMENDER-2026-09-06.md`
