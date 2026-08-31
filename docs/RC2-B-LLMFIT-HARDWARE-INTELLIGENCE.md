# RC2-B — LLMFit Hardware Intelligence

**Estado:** 🟢 Contrato fijado · implementación de frontera creada  
**Predecesor:** RC2-A — orquestación  
**Siguiente:** RC2-C — selección humana

## Decisión

RC2-B incorpora **LLMFit como instrumento especializado de hardware → modelo/fit**. LEONES no implementará un perfilador heurístico paralelo.

LLMFit ya proporciona detección de RAM/CPU/GPU/VRAM, scoring de fit, estimación de velocidad, selección de cuantización, recomendaciones JSON y planificación de hardware. También dispone de benchmarking local, pero sus mediciones no se convierten automáticamente en evidencia LEONES. citeturn0search0turn0search1

## Contrato

```text
HARDWARE REAL
     ↓
LLMFIT
     ↓
LLMFIT JSON + PROVENANCE
     ↓
NORMALIZACIÓN LEONES
     ↓
CANDIDATOS / FIT / ESTIMACIONES
     ↓
LEONES
     ↓
ODS / MAGNITUDE
```

### LLMFit hace

- detectar hardware;
- calcular ajuste de modelos y variantes;
- aportar candidatos;
- aportar cuantización cuando esté disponible;
- aportar estimaciones claramente identificadas;
- aportar datos de procedencia y versión.

### LEONES hace

- conservar la procedencia;
- diferenciar `observed`, `declared`, `estimated` y `measured`;
- presentar candidatos al usuario;
- permitir corrección/declaración cuando la detección sea incompleta;
- decidir la siguiente etapa;
- delegar ODS/Magnitude a sus contratos propios;
- ejecutar y medir mediante el runner canónico;
- producir evidencia LEONES.

## No hace LLMFit dentro de LEONES

No instala stacks, no decide por el usuario, no sustituye ODS/Magnitude y no se convierte en runner de benchmark LEONES.

## Interfaz inicial

`runtime_selection/llmfit.py` ofrece una frontera CLI/JSON mínima:

```python
build_recommend_command(...)
run_recommend(...)
normalise_hardware(...)
normalise_candidates(...)
```

La integración es deliberadamente sin efectos laterales hasta que RC2 solicite explícitamente ejecutar el proceso.

## Procedencia

Cada resultado debe conservar como mínimo:

- fuente: `llmfit`;
- versión/ref;
- comando utilizado;
- JSON bruto;
- hardware normalizado;
- candidatos normalizados;
- distinción entre estimación y medición.

LLMFit documenta salida JSON para consumo por scripts/agentes mediante `llmfit recommend --json`, además de `llmfit --json system` y `plan ... --json`. citeturn0search0

## Hardware observado y declarado

LEONES debe permitir que el usuario corrija un dato cuando la autodetección no sea fiable. La corrección no borra el valor observado: ambos quedan registrados y el valor efectivo se marca como declarado/override.

LLMFit documenta overrides de memoria/VRAM, RAM y núcleos CPU para casos de autodetección incompleta o simulación. citeturn0search0

## Criterios de aceptación RC2-B

- [x] Existe una frontera LLMFit aislada.
- [x] No se crea un perfilador LEONES paralelo.
- [x] La salida machine-readable se conserva.
- [x] Hardware ausente permanece `null`/`unknown`.
- [x] Las estimaciones permanecen estimaciones.
- [x] Hay tests del adaptador sin requerir hardware real.
- [ ] Ejecutar LLMFit contra hardware real de beta tester.
- [ ] Validar el mapeo completo del JSON real de la versión/ref fijada.
- [ ] Integrar candidatos en RC2-C.

## Punto de intervención Ubuntu

**No es necesario todavía.** El contrato y el adaptador se pueden validar en CI con fixtures. Ubuntu será imprescindible cuando queramos comprobar que LLMFit detecta correctamente un host físico y cuando fijemos la versión/ref que utilizarán los beta testers.

## Regla final

> **LLMFit mide/estima el fit del hardware; LEONES decide qué hacer con ese conocimiento y sólo LEONES convierte una ejecución de su runner en evidencia LEONES.**
