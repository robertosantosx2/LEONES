# LLMFit — integración histórica LEONES

**Estado:** RC2 histórico · **fuera del camino canónico RC3**

## Decisión RC3

LLMFit/FitLLM queda deliberadamente desacoplado de RC3.

- No es dependencia de instalación.
- No se instala durante RC3.
- No se invoca para descubrir hardware.
- No participa en la selección canónica RC3.
- No bloquea el arranque ni la medición.
- Se conserva como conocimiento histórico y como posible `CandidateProvider` futuro.

La arquitectura RC3 utiliza **Hermes como bootstrap de discovery y fit inicial**, seguido de normalización LEONES. El usuario elige después Magnitude u ODS.

```text
Hermes discovery
      ↓
hardware-profile.v1
      ↓
LEONES normalization
      ↓
candidate-set.v1
      ↓
user choice
   ┌──┴───────┐
Magnitude    ODS
   └──┬───────┘
      ↓
LEONES verification → measurement → evidence
```

## Por qué se conserva

LLMFit sigue siendo una fuente válida de conocimiento sobre ajuste modelo/hardware y puede recuperarse en el futuro como proveedor desacoplado. Su existencia no debe contaminar el bootstrap RC3 ni crear un segundo perfilador obligatorio.

La interfaz y los tests históricos de `runtime_selection/llmfit.py` pueden mantenerse mientras sean necesarios para reproducir o auditar RC2. Eso no implica que RC3 los ejecute.

## Frontera de evidencia

Cualquier recomendación, `estimated_tps` o benchmark producido por LLMFit sigue siendo evidencia externa/estimación hasta que una ejecución controlada pase por el protocolo de medición LEONES.

**ESTIMATED ≠ MEASURED.**

## Futuro `CandidateProvider`

Si LLMFit vuelve a incorporarse, deberá hacerlo detrás de un contrato genérico de proveedor, sin privilegios arquitectónicos:

```text
CandidateProvider
 ├── Hermes
 ├── Magnitude / fuentes de perfilado
 ├── ODS / catálogo
 └── LLMFit (futuro, opcional)
```

Todos los proveedores deberán entregar datos normalizables y conservar procedencia. LEONES seguirá siendo responsable de filtrar, verificar, medir y producir la evidencia final.

## Regla definitiva

> **LLMFit queda fuera de RC3. No se instala, no se ejecuta y no decide.**
>
> **Hermes descubre → LEONES normaliza → usuario elige → Magnitude/ODS preparan → LEONES mide y evidencia.**
