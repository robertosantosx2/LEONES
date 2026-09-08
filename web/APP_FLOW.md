# LEONES App — flujo guiado

La aplicación web **no ejecuta la infraestructura local en el navegador**. Explica el recorrido y conduce a las herramientas locales.

## Flujo canónico RC4

```text
Necesidad → USER_INTENT[]
   ↓
Hardware real (preflight / hardware-profile)
   ↓
Evidencia HF + Artificial Analysis (≤100)
   ↓
LLMFit CLI opcional → intersección evidence-backed
   ↓
≤3 ESTIMATED | insufficient
   ↓
Elección humana (modelo)
   ↓
Stack: Magnitude | ODS | none
   ↓
Runtime preflight (p. ej. Ollama)
   ↓
Consentimiento ejecución + medición (opt-in, independientes)
   ↓
A01 / trusted argv → MEASURED
   ↓
Evidencia / recomendación
```

Histórico RC2: `./leones --rc2` (wizard). No es el camino canónico RC4.

## Decisiones explícitas

- Instalar ≠ verificar ≠ autorizar benchmark.
- FitLLM puede desinstalarse de forma independiente tras elegir stack.
- ESTIMATED de FitLLM, ODS, Magnitude u otras fuentes **no** es medición LEONES.

## Qué aporta cada capa

| Capa | Rol |
|------|-----|
| LEONES | Autoridad: hardware, intersección, medición, evidencia |
| LLMFit | Preselector ESTIMATED opcional |
| Magnitude / ODS | Stack de ejecución (interfaces propias) |
| Hermes / OMH | Opcionales; no seleccionan modelo en RC4 |
