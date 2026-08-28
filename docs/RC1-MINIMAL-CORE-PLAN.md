# LEONES RC1 — Plan del núcleo mínimo operativo

> **Estado: activo · rama: `rc1-minimal-core-v2`**
>
> Este documento convierte las reglas congeladas de `docs/LEONES-RULES.md` en un plan de ejecución concreto para llegar a una primera versión mínima, útil, medible y publicable de LEONES.

## 1. Objetivo de RC1

RC1 no pretende completar todo el ecosistema. Pretende demostrar una única cadena completa y reproducible:

```text
hardware de consumo
      ↓
LLMFit
      ↓
LEONES
  selección + decisión
      ↓
ODS / SOHO   o   Magnitude / asistente personal
      ↓
ejecución real
      ↓
benchmark LEONES
      ↓
evidencia física
      ↓
recomendación
      ↓
MANADA
```

El criterio de éxito es **integración completa con responsabilidades pequeñas**, no número de módulos.

## 2. Qué NO vamos a construir

RC1 evita deliberadamente:

- otro detector de hardware generalista;
- otro agente paralelo al Hermes que ya aporte ODS;
- otro benchmark propietario de terceros;
- otra base de modelos separada de Atlas;
- integración simultánea de todos los runtimes;
- una capa propia equivalente a Magnitude si Magnitude ya resuelve la capacidad;
- AirLLM o FreeToken dentro del núcleo antes de demostrar su necesidad.

Cada duplicación debe justificar por qué no puede resolverse mediante upstream, configuración o conector.

## 3. Arquitectura mínima

### 3.1 LLMFit: hipótesis inicial

[LLMFit](https://github.com/AlexsJones/llmfit) entra al principio del flujo. Su misión es reducir el espacio de búsqueda: qué modelos parecen razonables para el hardware detectado.

LEONES ya dispone de un adaptador pequeño (`automation/discovery/llmfit_adapter.py`) y de un puente a candidatos (`scripts/llmfit_to_recommendation_candidates.py`). Estos componentes se consideran **adaptadores**, no una segunda implementación de LLMFit.

Contrato esencial:

```text
LLMFit
  → fit / estimated_tps / requisitos
  → provenance = llmfit
  → estimate_only = true
  → measured_tps = null
```

Nunca se promociona una estimación LLMFit a `measured` sin una ejecución física LEONES.

### 3.2 LEONES: decisión

LEONES recibe el resultado de fit y lo cruza con:

- identidad y evidencia de Atlas;
- apertura/JGB cuando sea relevante;
- workload;
- contexto;
- cuantización;
- runtime disponible;
- memoria;
- VRAM;
- restricciones del usuario;
- evidencia de rendimiento ya existente.

Su salida es un **plan autorizado**, no una promesa de rendimiento.

### 3.3 Elección de ejecutor

Después de LLMFit → LEONES se decide la ruta de ejecución:

| Ruta | Uso RC1 |
|---|---|
| ODS | SOHO / nodo doméstico cuando ODS sea el mejor encaje |
| Magnitude | asistente personal cuando Magnitude sea el mejor encaje |

La decisión debe ser explícita y observable.

### 3.4 Hermes

Si se selecciona ODS, LEONES reutiliza el Hermes que aporte ODS. No se introduce un agente Hermes paralelo en LEONES.

La responsabilidad de LEONES sigue siendo:

```text
seleccionar → ejecutar/coordinar → medir → validar → conservar evidencia
```

### 3.5 Medición

El ejecutor puede ser ODS o Magnitude; el **benchmark canónico es LEONES**.

Esto evita mezclar:

- capacidad agentiva;
- rendimiento del runtime;
- rendimiento del hardware;
- resultado de la tarea.

## 4. Hardware de consumo: tiers RC1

El hardware de consumo es el caso prioritario. El tier no debe reducirse a una etiqueta de CPU.

### T0 — CPU básica / memoria limitada

- CPU-only o iGPU básica;
- aproximadamente 8 GB de RAM o menos;
- modelos pequeños/cuánticos;
- objetivo: ejecución local básica.

### T1 — portátil de entrada

- 8–16 GB RAM;
- CPU moderna y/o iGPU;
- modelos pequeños y medianos cuantizados;
- objetivo: asistente ligero.

### T2 — portátil/desktop medio

- 16–32 GB RAM;
- iGPU o GPU de consumo modesta;
- mayor margen de contexto y modelos medianos.

### T3 — GPU de consumo

- 8–16 GB de VRAM típica;
- 32 GB o más de RAM como configuración preferida;
- modelos medianos/grandes cuantizados;
- objetivo: asistente local competente.

### T4 — consumo alto / workstation doméstica

- GPU de consumo de mayor VRAM o configuración multi-GPU cuando proceda;
- RAM elevada;
- modelos grandes cuantizados y cargas agentivas más exigentes.

**Importante:** los tiers son una capa de clasificación, no una garantía de rendimiento. La medición física prevalece.

## 5. Primer recorrido que vamos a implementar

### Fase A — LLMFit

1. congelar el formato de entrada esperado;
2. documentar la versión/origen de LLMFit;
3. validar hardware detectado vs hardware declarado a LLMFit;
4. comprobar normalización de modelos;
5. comprobar que `estimated_tps` nunca contamina `measured_tps`;
6. añadir fixtures representativos de T0–T3;
7. dejar un comando reproducible para convertir una salida LLMFit en candidatos LEONES.

**No requiere Ubuntu** mientras usemos fixtures/salidas capturadas.

### Fase B — LEONES como filtro

1. mantener Atlas como fuente de identidad/evidencia;
2. aplicar runtime y workload antes de recomendar;
3. respetar contexto y memoria;
4. conservar procedencia de LLMFit;
5. producir plan autorizado;
6. rechazar explícitamente candidatos que no cumplen el contrato.

**No requiere Ubuntu.**

### Fase C — ODS y Magnitude

Primero se estudia qué capacidad ya proporciona cada proyecto.

```text
                 LLMFit
                    ↓
                 LEONES
                    ↓
          ┌─────────┴─────────┐
          ↓                   ↓
       ODS/SOHO        Magnitude/personal
          ↓                   ↓
          └─────────┬─────────┘
                    ↓
             ejecución real
```

No se implementan adaptadores grandes. Solo un contrato mínimo de entrada/salida y un conector si hace falta.

**La instalación real sí puede requerir Ubuntu**, pero solo después de cerrar el contrato.

### Fase D — AirLLM y FreeToken

No se incorporan al núcleo todavía.

Cuando ODS/Magnitude estén integrados se evalúa:

1. qué problema real resuelven;
2. si el upstream acepta la capacidad;
3. si existe API/interfaz estable;
4. si una contribución upstream elimina la necesidad de código LEONES;
5. si no, crear un adaptador fino.

Ruta congelada:

```text
AirLLM / FreeToken
        ↓
prueba de utilidad
        ↓
upstream ODS/Magnitude
        ↓
si no es viable → conector LEONES
```

### Fase E — Benchmark real

Una vez que el camino de ejecución esté cerrado:

1. instalar/verificar runtime;
2. fijar modelo y cuantización;
3. fijar contexto y prompt;
4. warm-up;
5. repetir mediciones;
6. capturar hardware;
7. conservar stdout/stderr;
8. generar `execution_id`;
9. validar evidencia;
10. comparar fit vs realidad.

**Aquí avisaremos antes de necesitar Ubuntu.**

### Fase F — Publicación en MANADA

Solo se publica como conocimiento operativo el resultado que conserve:

- procedencia;
- configuración;
- ejecución;
- medición;
- validación.

La publicación debe poder distinguir:

```text
estimado por LLMFit
        vs
medido por LEONES
```

## 6. Deprecación

Lo que ya exista en LEONES pero no pertenezca al camino RC1 se mueve a una rama `deprecated/pre-rc1-*` o queda explícitamente fuera del camino canónico según su utilidad histórica.

No se elimina evidencia histórica ni contratos que todavía sean necesarios para validar resultados anteriores.

## 7. Gates de RC1

### Gate 1 — Fit

- LLMFit funciona o su salida capturada es normalizable;
- hardware y candidato conservan procedencia;
- ninguna estimación se presenta como medida.

### Gate 2 — Decision

- LEONES produce un plan determinista;
- runtime/workload/contexto están fijados;
- el plan es auditable.

### Gate 3 — Executor

- ODS o Magnitude ejecuta el plan;
- Hermes se reutiliza donde corresponda;
- no hay agente duplicado innecesariamente.

### Gate 4 — Measurement

- benchmark LEONES obtiene evidencia física;
- hardware y runtime quedan registrados;
- resultado reproducible.

### Gate 5 — Publication

- evidencia validada;
- diferencia fit/medición preservada;
- publicación en MANADA trazable.

## 8. Política Ubuntu

Hasta Gate 3 se trabaja preferentemente en GitHub/CI/local no físico.

Se pide Ubuntu únicamente cuando el dato que falta no puede demostrarse de otra manera.

**Primera intervención Ubuntu prevista:** instalación/comprobación del ejecutor elegido y primera ejecución física RC1.

Cuando llegue ese momento el comando debe ser de tipo:

```text
comprobar → ejecutar → medir → conservar → validar
```

No:

```text
entrar en Ubuntu → improvisar arquitectura
```

## 9. Criterio de Release Candidate 1

RC1 queda listo cuando exista al menos una demostración completa sobre hardware de consumo:

```text
hardware
 → LLMFit
 → LEONES
 → ODS o Magnitude
 → tarea real
 → benchmark LEONES
 → evidencia validada
 → recomendación
 → MANADA
```

Y cuando el repositorio permita repetir el recorrido sin reinterpretar contratos.

## 10. Próximo trabajo inmediato

1. cerrar la documentación/contrato LLMFit;
2. completar fixtures de hardware de consumo;
3. auditar el selector para que LLMFit sea únicamente una señal de fit;
4. inventariar las capacidades reales de ODS y Magnitude;
5. definir el mínimo contrato de ejecución común;
6. revisar qué piezas pre-RC1 pasan a deprecated;
7. implementar tests de los gates;
8. **solo entonces** preparar Ubuntu.

## 11. Regla de cierre

> **Una ruta completa, pequeña y demostrable antes que un ecosistema grande e incompleto.**
