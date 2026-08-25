# LLM Checker

## 1. Identidad y procedencia
- **Fuente primaria:** https://github.com/signerless/llm-checker
- **Capa LEONES:** preselector + scoring + runtime targeting.
- **Estado LEONES:** `research-candidate`.
- **Revisión:** 2026-08-25.
- **Licencia declarada por la fuente:** NPDL-1.0.

## 2. Qué es
LLM Checker se presenta como un **Intelligent Ollama Model Selector**. Analiza el hardware y recomienda modelos locales mediante scoring determinista sobre un registro multi-fuente. La versión documentada actualmente declara fuentes Hugging Face, Ollama y GPT4All, runtime targeting y estimación de memoria calibrada contra tamaños reales de Ollama. fileciteturn22file0

## 3. Por qué es relevante
Ataca una capa muy próxima al Router de LEONES:

```text
hardware
   ↓
model registry
   ↓
compatibility
   ↓
Quality / Speed / Fit / Context
   ↓
runtime target
   ↓
recommendation
```

La fuente declara catálogo multi-fuente de más de 33k artefactos exactos, más de 200 modelos en su catálogo empaquetado y detección multi-GPU. fileciteturn22file0

## 4. Evidencia primaria
La documentación actual declara:

- registro de artefactos Hugging Face/Ollama/GPT4All;
- scoring 4D: Quality, Speed, Fit, Context;
- detección Apple Silicon, NVIDIA, AMD, Intel Arc y CPU;
- estimación de memoria calibrada con tamaños reales de Ollama;
- `ai-run` con tokens/s observados durante ejecuciones;
- targeting de runtimes como Ollama, vLLM, MLX, llama.cpp y Transformers. fileciteturn22file0

Estas propiedades son evidencia documental de la fuente. Las métricas que el programa obtiene al ejecutar son **mediciones del propio LLM Checker**, no automáticamente mediciones LEONES.

## 5. Scoring
La idea central es separar cuatro dimensiones:

```text
Quality
Speed
Fit
Context
```

LEONES debe conservarlas como señales externas independientes. **No debe sumarlas directamente al score LEONES.**

La arquitectura correcta es:

```text
LLM Checker score
       ↓
external estimate
       ↓
candidate
       ↓
LEONES evidence + task + runtime + measurements
```

## 6. Catálogo multi-fuente
La evolución reciente del proyecto es especialmente relevante: el registro incorpora artefactos exactos de distintas fuentes y comandos de instalación/descarga por origen. fileciteturn22file0

Esto puede inspirar el Atlas en una dimensión concreta: distinguir **modelo lógico** de **artefacto instalable**.

```text
model family
   ↓
artifact
   ├─ source
   ├─ tag/revision
   ├─ quantization
   ├─ runtime
   └─ download/install command
```

LEONES no debe importar automáticamente ese catálogo; debe usarlo como referencia metodológica y conservar identidad Atlas propia.

## 7. Calibración
LLM Checker documenta un flujo de calibración que genera artefactos de resultado y una política de routing. La calibración utiliza una suite de prompts y puede producir una política reutilizable para `recommend`/`ai-run`. fileciteturn22file0

Esto es muy interesante para LEONES porque conecta:

```text
prompt suite
   ↓
model/runtime execution
   ↓
calibration artifact
   ↓
routing policy
```

Pero la política externa debe permanecer separada de `runtime-selection.v1`.

## 8. Medición externa vs medición LEONES
El proyecto declara que `ai-run` muestra velocidad en tokens/s durante respuestas locales. fileciteturn22file0

LEONES debe tratarlo como:

```text
llm-checker measured_tps
        ≠
LEONES measured_tps
```

Aunque ambos ejecuten el mismo modelo, las diferencias de prompt, warm-up, runtime, contexto, sampler, versión o hardware pueden cambiar el resultado.

## 9. MoE y sizing
La documentación de la versión actual declara una corrección importante: los modelos MoE se dimensionan por parámetros totales cuando el runtime mantiene los expertos residentes, evitando falsos `fit` en hardware pequeño. fileciteturn22file0

Esto debe compararse con el tratamiento de MoE de LLMFit y localmodel.run. No debemos asumir una fórmula universal: el criterio correcto depende del runtime y de la estrategia de residencia/offload.

## 10. Runtime targeting
La capacidad de seleccionar explícitamente runtime es una de las piezas más próximas a `runtime-selection.v1`.

Debe extraerse conceptualmente:

```text
runtime candidate
+ model artifact
+ hardware
+ policy
→ executable configuration
```

LEONES debe conservar su propio contrato y usar LLM Checker como fuente de hipótesis.

## 11. MCP
La fuente incluye un servidor MCP y herramientas para detectar hardware, recomendar, buscar, planificar GPU, verificar contexto, calibrar y ejecutar modelos. fileciteturn22file0

Esto abre una posible integración futura como **harness de conocimiento**, pero no debe introducir dependencia dura en el núcleo LEONES.

## 12. Relación con LLMFit
La propia documentación compara ambos proyectos y reconoce que resuelven problemas relacionados desde ángulos diferentes. fileciteturn22file0

Para LEONES:

```text
LLM-Hardware-Advisor → hardware + catálogo + fitness
localmodel.run       → modelo + dispositivo + trazabilidad
VRAMBudget           → matemática de memoria
LLMFit               → fit + speed + quality + context
LLM Checker          → catálogo + scoring + runtime + calibration
CanIRun.ai           → detección hardware desde navegador
```

La función de LEONES es **orquestar y verificar**, no elegir uno arbitrariamente como fuente soberana.

## 13. Medición LEONES
**Pendiente.**

El primer experimento debe fijar una máquina, un modelo y un runtime y comparar:

- score externo;
- memoria estimada;
- tokens/s externo cuando exista;
- resultado de `runtime-selection.v1`;
- measured TTFT/TPOT/tok/s;
- memoria real;
- resultado del grader.

## 14. Valor para LEONES
Muy alto en tres zonas:

1. **registry de artefactos**;
2. **scoring multidimensional** como señal externa;
3. **calibración** como precedente de políticas basadas en ejecuciones.

## 15. Limitaciones y licencia
La licencia declarada es NPDL-1.0 y debe verificarse antes de reutilizar código o datos. El catálogo y el scoring cambian con las releases. fileciteturn22file0

Además:

- score ≠ benchmark LEONES;
- catálogo ≠ Atlas;
- `ai-run` ≠ executor LEONES;
- política calibrada ≠ `runtime-selection.v1`.

## 16. Clasificación
**`research-candidate` → preselector/scoring de alto interés.**

## 17. Próximo paso
Analizar por separado `scoring-core`, detector, registry, calibración y herramientas MCP. Después construir un adaptador de solo lectura y un caso de cross-validation contra LLMFit.