# Investigación: Gerbil SDK / Tune y post-entrenamiento en LEONES Evolution

**Estado:** Experimental / investigación  
**Rama:** `ods-evolution`  
**Ámbito:** post-training, especialización de modelos, edge inference y computación híbrida  
**Fecha:** 2026-10-02

## Resumen

Gerbil combina un runtime de inferencia orientado a JavaScript/WebGPU con **Gerbil Tune**, una capa para especializar modelos a partir de ejemplos y datos de uso. Para LEONES Evolution resulta interesante en dos frentes relacionados pero distintos:

1. **Gerbil Tune** como candidato para post-training y creación de especialistas/adapters.
2. **Gerbil SDK** como runtime complementario para browser, WebGPU y Node/edge.

La posición propuesta es:

```text
LEONES
  ↓
discovery / profiling / planning / evidence
  ↓
TangleML                  Gerbil Tune
workflow orchestration    specialist tuning
  ↓                         ↓
training / data          model / adapter
  └──────────────┬──────────┘
                 ↓
                ODS
                 ↓
       inference / agents / tools / services
```

Gerbil no debería convertirse en una dependencia estructural de ODS sin verificar antes la interoperabilidad de sus artefactos con los runtimes que ODS ya utiliza.

## 1. Encaje arquitectónico

LEONES no debe evolucionar alrededor de «local AI» como fin absoluto. El objetivo superior es libertad, independencia y control del usuario. La ejecución local es una opción importante, pero también pueden ser válidas infraestructura remota controlada, cloud compatible con los requisitos de independencia y computación híbrida.

En este contexto:

- **LEONES** decide, perfila, compara, valida y conserva evidencia.
- **TangleML** puede orquestar workflows reproducibles de datos/training/evaluación.
- **Gerbil Tune** puede especializar un modelo base mediante especialistas/adapters.
- **ODS** sigue siendo la plataforma de ejecución y operación de IA.

## 2. Gerbil Tune como post-training

El concepto más relevante para LEONES es la especialización de un modelo base:

```text
                  Base model
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
       support      refunds       SQL
       adapter      adapter      adapter
          │           │           │
          └───────────┴───────────┘
                      │
                 specialized
                   behavior
```

Esto añade una dimensión nueva al sistema de candidatos de LEONES:

```text
Candidate A
Qwen 3.5 2B

Candidate A+
Qwen 3.5 2B + support adapter

Candidate A++
Qwen 3.5 2B + SQL adapter

Candidate B
larger base model
```

LEONES puede comparar no solamente modelos, sino **modelo base + especialización**.

Las variables relevantes incluyen:

- calidad;
- latencia;
- throughput;
- RAM/VRAM;
- tamaño descargado;
- tamaño del adapter;
- compatibilidad del runtime;
- privacidad;
- portabilidad;
- licencia;
- reproducibilidad;
- disponibilidad de datos y pesos.

## 3. Capture y ciclo de mejora

Gerbil Tune incluye un concepto de captura de llamadas de inferencia para generar datasets JSONL. Esto puede encajar en un ciclo controlado de mejora:

```text
ODS
 │
 │ production inference
 ▼
task examples / logs
 │
 ▼
Capture / filtering / redaction
 │
 ▼
training dataset
 │
 ▼
Gerbil Tune / TangleML
 │
 ▼
specialist / adapter
 │
 ▼
ODS
 │
 ▼
independent benchmark
 │
 ├── candidate
 └── rejected
```

La promoción de una nueva especialización no debería quedar implícitamente en manos del sistema de autotrain. LEONES debe conservar la función de validación y decisión, con benchmark independiente y evidencia.

Los datos de producción deben tratarse como material potencialmente sensible. Antes de cualquier envío remoto deben verificarse redacción, consentimiento, cifrado, control de claves, retención y destino.

## 4. Relación con TangleML

Gerbil Tune y TangleML no tienen por qué competir.

**TangleML responde principalmente a:**

> ¿Cómo ejecuto reproduciblemente este workflow de ML?

**Gerbil Tune responde principalmente a:**

> ¿Cómo convierto ejemplos en un especialista o adapter utilizable?

Una arquitectura posible:

```text
LEONES
   │
   ├───────────────┐
   ▼               ▼
TangleML       Gerbil Tune
   │               │
data/training   specialist
evaluation      adapter
   │               │
   └───────┬───────┘
           ▼
      model artifact
           │
           ▼
          ODS
```

TangleML puede proporcionar el workflow reproducible alrededor de Gerbil Tune cuando resulte necesario: preparación, limpieza, generación, evaluación, benchmarking y empaquetado de evidencia.

## 5. Hybrid compute

El valor para LEONES no está en asumir que Tune debe ejecutarse siempre localmente o siempre en cloud. El workflow puede separar etapas:

```text
private dataset
      ↓
LOCAL
  preparation
  filtering
      ↓
REMOTE GPU
  training
      ↓
LOCAL
  sensitive evaluation
  benchmark
      ↓
ODS
  serving
```

Otra posibilidad:

```text
large teacher
      ↓
remote GPU
      ↓
synthetic data
      ↓
local filtering
      ↓
specialist training
      ↓
ODS
```

La decisión debe tener en cuenta hardware, memoria, aceleradores, coste, privacidad, tamaño de datos/modelo, tiempo, licencia, portabilidad e independencia.

## 6. Gerbil SDK como runtime complementario

Gerbil SDK merece una investigación separada del servicio Tune.

Su orientación WebGPU/JavaScript permite estudiar:

- browser inference;
- Node inference;
- edge execution;
- ejecución offline después de descargar/cachear modelos;
- integración con aplicaciones web;
- agents/tools y otras capas del SDK.

Esto puede ampliar el **Execution Fabric** de ODS:

```text
                 ODS EXECUTION FABRIC

 llama-server       Gerbil          remote providers
      │               │                    │
      └───────────────┼────────────────────┘
                      │
               capability registry
                      │
                 runtime selector
```

Gerbil no debe sustituir automáticamente a llama-server. Puede convertirse en otro execution provider cuando las capacidades de modelo, hardware y aplicación lo justifiquen.

## 7. Interoperabilidad con ODS

Este es el punto técnico que debe verificarse antes de una integración real.

El entorno ODS estudiado utiliza runtimes como `llama-server`. Gerbil utiliza su propio runtime y formato/flujo de artefactos.

No debe asumirse:

```text
Gerbil Tune artifact
        ↓
llama-server
```

hasta comprobar:

- formato de pesos;
- formato de adapters;
- compatibilidad LoRA;
- tokenizer;
- quantization;
- conversiones disponibles;
- soporte del runtime ODS;
- equivalencia de resultados;
- costes de conversión;
- pérdida de funcionalidad.

El PoC debe probar al menos:

```text
Gerbil Tune
     ↓
base + adapter
     ├──────────────► Gerbil runtime
     │
     └──────────────► ODS / llama-server
                         │
                         ▼
                  benchmark comparison
```

Si el artefacto solamente funciona de forma nativa en Gerbil, Gerbil puede seguir siendo válido como herramienta de post-training y runtime específico, pero aparecerá una dependencia adicional de runtime.

## 8. Licencia e independencia

La información pública consultada presenta el SDK como open source/MIT. Eso es favorable para su evaluación como componente tecnológico.

Sin embargo, **la licencia del SDK no demuestra por sí sola independencia de la infraestructura de Tune**.

LEONES debe distinguir:

| Capa | Evaluación inicial |
|---|---|
| Gerbil SDK | Open source / MIT declarado |
| Runtime local/browser | Interesante para independencia |
| Gerbil Tune | Servicio gestionado por defecto |
| Exportación de artefactos | Debe verificarse por flujo concreto |
| Self-hosting / on-prem | Debe verificarse para cada modalidad |
| Dependencia de infraestructura | Debe documentarse |
| Copyleft fuerte | No identificado como característica del SDK |
| Anti-captura cloud por licencia | No |

La independencia debe evaluarse sobre **software + pesos + datos + infraestructura + claves + portabilidad**, no solamente sobre la licencia del runtime.

## 9. Encaje con la evidencia LEONES

LEONES debe separar:

- `estimated`;
- `reported`;
- `observed`;
- `measured`.

Las afirmaciones de rendimiento de Gerbil no deben convertirse automáticamente en mediciones LEONES.

El PoC debería producir:

```text
configuration
   ↓
model / adapter provenance
   ↓
training metadata
   ↓
runtime
   ↓
hardware
   ↓
benchmark
   ↓
evidence package
```

## 10. Casos de uso candidatos

### Especialista pequeño

```text
general model
      ↓
small domain dataset
      ↓
adapter
      ↓
ODS
```

### Especialistas múltiples

```text
                  Base model
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
       support       SQL         legal
       adapter      adapter      adapter
          │           │           │
          └───────────┴───────────┘
                      ▼
                 ODS routing
```

La capa de routing es un punto para investigación futura: ODS/LEONES podrían seleccionar la combinación base + adapter según tarea y evidencia.

### Feedback loop

```text
ODS production
      ↓
capture
      ↓
redact / filter
      ↓
candidate dataset
      ↓
tune
      ↓
benchmark
      ↓
LEONES evidence
      ↓
promotion decision
```

## 11. Fit por área

| Área | Encaje |
|---|---|
| Specialist tuning | Alto |
| Adapters / LoRA | Alto, sujeto a verificación de formatos |
| Dataset capture | Alto |
| Synthetic/production examples | Alto |
| SFT / post-training | Alto, según modalidad |
| Continuous improvement | Experimental |
| Browser inference | Alto |
| WebGPU inference | Alto |
| Node/edge inference | Alto |
| Model serving principal de ODS | Complementario |
| Agents/tools | Complementario |
| Workflow orchestration | TangleML |
| Discovery | LEONES |
| Hardware profiling | LEONES |
| Benchmark | LEONES |
| Evidence governance | LEONES |
| License/provenance governance | LEONES |

## 12. PoC propuesto

Primera fase:

```text
LEONES-selected base model
        ↓
small controlled dataset
        ↓
Gerbil Tune
        ↓
specialist / adapter
        ↓
Gerbil runtime benchmark
        ↓
artifact inspection
```

Segunda fase:

```text
same base + adapter
        ↓
ODS compatibility test
        ↓
llama-server / other ODS runtime
        ↓
independent benchmark
        ↓
compare:
  quality
  latency
  memory
  artifact size
  portability
  reproducibility
```

Tercera fase:

```text
local preparation
        ↓
remote training backend
        ↓
local sensitive evaluation
        ↓
ODS deployment
        ↓
evidence
```

## 13. Riesgos y puntos abiertos

Antes de una integración estructural deben verificarse:

1. formato exacto de modelos y adapters;
2. interoperabilidad con los runtimes de ODS;
3. reproducibilidad del training;
4. exportación completa de artefactos;
5. dependencia de servicios gestionados;
6. self-hosting/on-prem;
7. gestión de secretos;
8. cifrado y control de claves;
9. retención/eliminación de datasets y artefactos;
10. tratamiento de PII en Capture;
11. licencias de modelos y datasets;
12. licencias de componentes de training;
13. soporte real de cada arquitectura/modelo;
14. rendimiento medido en hardware LEONES;
15. compatibilidad de quantization;
16. rollback/canary de especialistas.

Gerbil Tune no debe interpretarse como garantía automática de sandboxing cifrado, confidential computing o end-to-end encryption. Estas propiedades dependen de la infraestructura concreta.

## 14. Estado en LEONES Evolution

**Clasificación:** Experimental / integration candidate.

**Rol propuesto:**

> **Gerbil Tune — specialist tuning / adapter post-training layer**  
> **Gerbil SDK — WebGPU / browser / Node execution provider**

Posición:

```text
LEONES Planner
      │
      ├───────────────┐
      ▼               ▼
 TangleML        Gerbil Tune
      │               │
      └───────┬───────┘
              ▼
       model / adapter
              │
              ▼
             ODS
              │
       inference / agents
```

### Decisión provisional

**Incluir Gerbil Tune y Gerbil SDK en la investigación de LEONES Evolution, sin convertirlos todavía en dependencias estructurales de ODS.**

El siguiente paso recomendado es el PoC de interoperabilidad **Gerbil Tune → adapter → ODS**, manteniendo una ruta nativa Gerbil para comparación.

## Sources

- Gerbil Tune: https://www.gerbilsdk.com/tune
- Gerbil SDK: https://www.gerbilsdk.com/
- Gerbil documentation: https://www.gerbilsdk.com/docs/
- Gerbil Capture: https://www.gerbilsdk.com/docs/tune/capture
- Gerbil models: https://www.gerbilsdk.com/docs/models
