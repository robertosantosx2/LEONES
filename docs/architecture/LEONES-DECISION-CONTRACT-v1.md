# LEONES — Decision Contract v1

**Estado:** contrato operativo de referencia
**Fase:** RC1 → JALÓN 3

## 1. Propósito

Este contrato fija cómo LEONES pasa de conocimiento y adecuación de hardware/modelo a una decisión de ejecución medible, sin crear un selector paralelo.

La autoridad de decisión pertenece a LEONES.

```text
Atlas / conocimiento
        │
        ▼
      LLMFit
        │
        │ adecuación modelo ↔ hardware
        ▼
 LEONES selection
        │
        │ decisión explícita
        ▼
 ┌──────┴──────┐
 ▼             ▼
ODS           Magnitude
SOHO          asistente personal
 └──────┬──────┘
        │ interfaz compatible
        ▼
   llama-server
        │
        ▼
   modelo local
        │
        ▼
  LEONES mide
        │
        ▼
 evidencia reproducible
        │
        ▼
 benchmark de tareas
        │
        ▼
     MANADA
```

## 2. Responsabilidades

### LEONES

LEONES es responsable de:

- interpretar el caso de uso;
- fijar hardware y restricciones disponibles;
- fijar el runtime antes de evaluar candidatos;
- consumir conocimiento de Atlas;
- consumir la adecuación aportada por LLMFit;
- aplicar sus propios gates de elegibilidad;
- decidir el candidato/ruta que pasa a ejecución;
- registrar qué información sustentó la decisión;
- medir la ejecución real;
- convertir la ejecución en evidencia reproducible;
- promover esa evidencia a benchmark de tareas y, posteriormente, a MANADA.

### LLMFit

LLMFit se trata como **fuente de adecuación/estimación**, no como autoridad de decisión.

Su salida puede aportar, cuando exista:

- identidad del modelo;
- clasificación de ajuste/fit;
- memoria requerida/estimada;
- rendimiento estimado;
- metadatos de hardware/modelo que expliquen la estimación.

Una estimación de LLMFit **no es una medición física de LEONES** y nunca debe presentarse como tal.

### ODS / SOHO

ODS/SOHO representan la vía de asistencia/ejecución correspondiente a ese subsistema. LEONES debe consumir su capacidad mediante un contrato de interfaz compatible, sin duplicar dentro de LEONES la implementación de su motor.

### Magnitude

Magnitude representa la vía de asistencia personal y profiling/ejecución que corresponda a su capacidad real. Sus datos se consumen como datos externos y deben conservar procedencia.

### llama-server

`llama-server` es la frontera de ejecución local compatible. El contrato de selección debe producir una configuración que pueda traducirse a una interfaz de ejecución reproducible.

## 3. Orden obligatorio

La decisión debe respetar este orden:

```text
use case
  ↓
hardware
  ↓
inference runtime
  ↓
optimization
  ↓
external estimators / fit evidence
  ↓
model eligibility
  ↓
LEONES ranking / decision
  ↓
runtime gate
  ↓
execution
  ↓
measurement
```

No se permite seleccionar un modelo y decidir posteriormente el runtime para justificarlo.

## 4. Evidencia y autoridad

| Dato | Naturaleza | Autoridad |
|---|---|---|
| Atlas | conocimiento/prospección | fuente de conocimiento |
| LLMFit fit | estimación/adecuación | evidencia externa |
| ODS/Magnitude | capacidad/dato externo | fuente externa |
| selección LEONES | decisión | **LEONES** |
| llama-server execution | ejecución observable | runtime |
| tok/s, latencia, memoria observada | medición | **LEONES** |
| benchmark de tareas | resultado de tarea | **LEONES** |

Las fuentes externas pueden informar una decisión, pero no pueden convertir una estimación en evidencia observada.

## 5. Identidad mínima de una decisión

Una decisión reproducible debe poder identificar, como mínimo:

- `decision_id`;
- fecha/hora UTC;
- workload/caso de uso;
- hardware identificado;
- runtime y versión;
- optimizaciones aplicadas;
- feed/versión de conocimiento utilizado;
- modelo y variante seleccionados;
- cuantización;
- contexto objetivo;
- evidencia LLMFit utilizada, si existe;
- fuente ODS/Magnitude utilizada, si existe;
- razones/gates de decisión;
- configuración que pasa al runtime gate.

La decisión debe ser auditable sin necesitar reconstruirla desde logs informales.

## 6. Separación de estimación y medición

Nunca mezclar:

```text
estimated_tps  ≠  measured_tps
estimated_memory  ≠  observed_memory
fit  ≠  execution_result
```

El resultado de LLMFit puede aparecer junto al resultado de LEONES, pero debe conservar una etiqueta de procedencia y naturaleza.

## 7. Regla de sustitución

LEONES no implementará una copia de LLMFit, ODS o Magnitude sólo para reproducir una función que ya proporcionan esos sistemas.

La integración debe ser mediante adapters/contratos pequeños y observables.

Si una capacidad externa desaparece, cambia su interfaz o no aporta la información necesaria, se documenta el hueco antes de crear una sustitución.

## 8. Regla de runtime

El runtime es una decisión explícita anterior a la valoración final del modelo.

El resultado debe poder pasar al `runtime_gate` y, si es aceptado, producir una configuración de ejecución compatible con `llama-server`.

## 9. Regla de medición

La medición real comienza **después** de que exista una decisión de selección válida y un runtime aceptado.

La medición debe producir evidencia reproducible que identifique modelo, revisión/artefacto, cuantización, contexto, runtime, hardware, protocolo, warm-up, repeticiones, tiempos y métricas observadas.

## 10. Benchmark de tareas

Los tokens/segundo son una métrica de runtime, no el objetivo final.

El siguiente nivel debe medir tareas completas: éxito, calidad verificable, latencia y coste de ejecución cuando proceda.

La evidencia de runtime sirve para demostrar que la ejecución ocurrió; el benchmark de tareas demuestra qué trabajo consiguió realizar el modelo.

## 11. Prohibiciones

- No crear un segundo selector que compita con `model_selector`/`selection_pipeline`.
- No convertir LLMFit en autoridad de decisión.
- No presentar resultados de ODS/Magnitude como mediciones de LEONES sin ejecutar el protocolo correspondiente.
- No mezclar estimaciones externas con observaciones locales.
- No seleccionar modelos antes de fijar runtime.
- No usar runners deprecated en nuevas rutas.
- No deprecar herramientas de descubrimiento/Atlas sin demostrar sustitución.

## 12. Criterio de cierre del contrato

El contrato se considera implementado cuando:

1. existe una entrada de decisión identificable;
2. LLMFit puede aportar adecuación sin asumir autoridad;
3. ODS/Magnitude pueden integrarse sin un motor paralelo;
4. runtime queda fijado antes de seleccionar;
5. la selección pasa por el runtime gate;
6. la ejecución puede llegar a `llama-server`;
7. la ejecución física produce evidencia canónica;
8. la evidencia puede alimentar el benchmark de tareas.

La ejecución física y la validación de rendimiento **requieren Ubuntu/hardware real**. Hasta ese punto, el contrato puede y debe cerrarse en GitHub.
