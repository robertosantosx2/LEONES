# LLMFit / FitLLM — fuera del camino canónico RC3

**Estado:** histórico / diferido  
**Rol en RC3:** ninguno (no dependencia, no arranque, no selección)

## Frontera

LLMFit/FitLLM queda **fuera del camino canónico RC3**. No se instala con LEONES, no bloquea el bootstrap y no participa en la selección RC3.

Se conserva como conocimiento histórico y como posible `CandidateProvider` futuro, completamente desacoplado de la instalación y del flujo físico.

## Regla de autoridad (RC3)

> **LEONES descubre el hardware → Hermes/OMH aportan ecosistema → usuario elige → Magnitude/ODS preparan → LEONES mide y evidencia.**

Cualquier cifra de fit o ranking externo es **ESTIMATED** / **reported**, nunca medición LEONES.

## Flujo canónico (referencia)

```text
LEONES physical probe (hardware_profile.py)
        ↓
hardware-profile.v1
        ↓
Hermes/OMH (ecosistema, no sonda física)
        ↓
candidate-set.v1
        ↓
usuario elige modelo + Magnitude | ODS
        ↓
verificación → medición → evidencia
```

## Qué NO hace LLMFit en RC3

- No es requisito de `./install.sh`
- No produce `hardware-profile.v1` autoritativo
- No autoriza ejecución ni medición
- No sustituye `scripts/hardware_profile.py`

## Procedencia

- Contrato RC3: `docs/RC3-ARCHITECTURE.md`
- STRICT: `docs/completed/RC3-STRICT-2026-09-05.md`
