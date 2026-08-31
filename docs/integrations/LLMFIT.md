# LLMFit — integración LEONES

**Estado:** RC2-B fijado · integración de frontera

## Propósito

LEONES usa LLMFit como fuente especializada para **inteligencia de hardware y ajuste modelo/hardware**. LEONES no reimplementa sus heurísticas.

LLMFit detecta hardware local y puede producir recomendaciones JSON, análisis de ajuste, selección de cuantización, planificación de hardware y benchmarks de runtimes soportados. La interfaz de automatización documentada por LLMFit incluye `llmfit --json system`, `llmfit recommend --json` y `llmfit plan ... --json`. citeturn0search0turn0search1

## Frontera de responsabilidad

```text
hardware real
     ↓
LLMFit
     ↓
normalización LEONES
     ↓
candidatos / fit / estimaciones
     ↓
LEONES decide y presenta
     ↓
ODS / Magnitude
     ↓
runtime real
     ↓
benchmark LEONES
```

LLMFit **no** sustituye:

- la decisión LEONES;
- ODS;
- Magnitude;
- el runner canónico;
- el benchmark de tareas LEONES;
- la evidencia LEONES.

## Regla de estimación

Las recomendaciones y `estimated_tps` de LLMFit permanecen como **estimaciones**. Una medición física sólo se registra como `measured` después de una ejecución real del runner/protocolo LEONES.

LLMFit dispone además de `bench` para mediciones de runtimes locales y conserva benchmarks locales; esto no convierte automáticamente esos resultados en evidencia LEONES. La promoción a evidencia LEONES requiere pasar por el contrato de procedencia correspondiente. citeturn0search0turn0search2

## Hardware declarado vs observado

La integración permite conservar la diferencia entre:

- hardware observado por LLMFit;
- valores declarados/corregidos por el usuario;
- valores efectivos utilizados para la selección.

Si un campo no está disponible, LEONES conserva `null`/`unknown`; no lo inventa.

LLMFit documenta overrides de RAM, memoria/VRAM y CPU para sistemas donde la autodetección no sea suficiente. citeturn0search0

## Interfaz RC2

El adaptador `runtime_selection/llmfit.py` es deliberadamente pequeño y sin efectos laterales:

- comprueba si existe `llmfit`;
- construye una invocación JSON de recomendación;
- ejecuta únicamente cuando el caller lo solicita;
- conserva comando, versión y JSON bruto;
- normaliza hardware y candidatos sin perder procedencia;
- no instala LLMFit;
- no descarga modelos;
- no ejecuta benchmarks;
- no modifica el sistema.

La integración está cubierta por `tests/test_llmfit_integration.py`.

## Versión / fijación

RC2 debe registrar la versión/ref de LLMFit que se utilice en cada ejecución. No se debe interpretar `latest` como una versión reproducible.

La integración inicial se apoya únicamente en la interfaz CLI/JSON documentada; la incorporación de REST, MCP u otras interfaces queda fuera de RC2-B hasta que exista una necesidad concreta. citeturn0search0

## Decisión arquitectónica

**LLMFit es el instrumento de hardware/fit; LEONES es la capa de orquestación y decisión.**

Esto evita crear un tercer perfilador paralelo y mantiene la arquitectura coherente con el contrato LEONES → ODS/Magnitude.
