# JALÓN 3 — Protocolo de medición real

> **Estado: CERRADO 🟢**  
> **Contrato operativo de medición física de LEONES.**

**Rama:** `jalon3-measurement-protocol`  
**Commit de cierre de código:** `275782e1eac39c3059dc4f6b5766680b5dcac86a`  
**Fecha de cierre:** 2026-08-28  
**Resultado de la auditoría final:** 256 tests OK, `git diff --check` OK, árbol limpio y `HEAD == origin/jalon3-measurement-protocol`.

---

## 1. Propósito

JALÓN 3 convierte el protocolo de medición real de LEONES en un **contrato operativo cerrado**.

El objetivo no es producir una cifra aislada de rendimiento. El objetivo es que cualquier cifra que LEONES promocione como medición propia pueda responder de forma trazable a estas preguntas:

- qué modelo se ejecutó;
- qué revisión o identidad concreta tenía;
- qué artefacto y cuantización se utilizaron;
- qué runtime lo ejecutó;
- qué versión exacta del runtime estaba disponible;
- sobre qué hardware se ejecutó;
- con qué sistema operativo y arquitectura;
- con qué contexto;
- con qué prompt/protocolo;
- con qué límites de generación;
- cuántos warm-ups se realizaron;
- cuántas mediciones se realizaron;
- qué ocurrió durante la ejecución;
- qué throughput y latencias observó el runtime;
- cuándo ocurrió;
- qué ejecución concreta produjo el dato;
- qué artefactos conservan la evidencia;
- y si el resultado superó los contratos de validación de LEONES.

### Principio rector

> **Una medición no es solamente un número: es un número + sus condiciones + su procedencia + su ejecución + su evidencia.**

Esto evita el error clásico de convertir una cifra de benchmark en una propiedad universal del modelo. Un resultado físico pertenece, en primer lugar, a una **configuración experimental concreta**.

---

# 2. Qué queda cerrado

JALÓN 3 cierra la transición entre el diseño de medición y su utilización operativa.

El recorrido canónico queda definido como:

```text
selección
    ↓
runtime-selection
    ↓
plan autorizado
    ↓
runtime real
    ↓
ejecución física
    ↓
medición
    ↓
captura del hardware real
    ↓
evidencia
    ↓
validación
    ↓
promoción/publicación
    ↓
recomendación
```

La arquitectura ya no necesita rediseñarse cuando se cambie de máquina o de runtime: lo que cambia es la **instancia experimental** y su evidencia.

---

# 3. Distinción fundamental de estados de conocimiento

LEONES mantiene separados los siguientes estados:

| Estado | Significado | ¿Es medición física LEONES? |
|---|---|---:|
| `estimated` | cálculo o estimación | No |
| `reported` | dato declarado por una fuente | No |
| `observed` | configuración observada | No necesariamente |
| `measured` | resultado de una ejecución física controlada | **Sí** |
| `verified` | dato que superó el quality gate correspondiente | Depende del origen |
| `unknown` | todavía no demostrado | No |

Por tanto:

```text
estimación externa ≠ medición LEONES
benchmark publicado ≠ medición LEONES
compatibilidad estimada ≠ rendimiento observado
rendimiento observado ≠ verdad universal
```

Una medición física puede convertirse posteriormente en evidencia verificada si supera los contratos de calidad, pero la verificación **no borra su procedencia**.

---

# 4. Contrato experimental mínimo

Toda medición reproducible debe fijar, directa o indirectamente, al menos:

### Identidad del modelo

- `model_id` / referencia canónica;
- nombre legible;
- revisión, commit, tag o referencia equivalente cuando esté disponible;
- formato del artefacto;
- cuantización;
- ruta o identificador del artefacto;
- tamaño;
- SHA-256 cuando el artefacto físico pueda hashearse.

### Runtime

- nombre del runtime;
- versión exacta o revisión disponible;
- adaptador utilizado;
- comando efectivo ejecutado;
- parámetros relevantes;
- backend/aceleración cuando aplique.

### Hardware

- CPU;
- número de núcleos físicos cuando pueda determinarse;
- hilos lógicos;
- arquitectura;
- RAM física total;
- GPU(s), si existen;
- VRAM, si está disponible;
- ancho de banda de memoria cuando esté disponible;
- PCIe H2D cuando esté disponible;
- otras medidas específicas del runtime cuando proceda.

### Protocolo de inferencia

- contexto;
- prompt;
- formato de entrada;
- límite de salida;
- temperatura y otros parámetros que puedan afectar a la ejecución, si se utilizan;
- número de warm-ups;
- número de mediciones;
- criterio de descarte/repetición;
- condición de finalización.

### Evidencia

- `execution_id`;
- timestamp UTC;
- stdout/stderr o equivalente;
- resultado normalizado;
- artefactos generados;
- hashes;
- relación entre ejecución y benchmark;
- estado de validación.

---

# 5. Hardware: captura en el instante de ejecución

JALÓN 3 introduce una regla especialmente importante: **el hardware utilizado por la ejecución debe proceder del host que realmente ejecuta la prueba**, no de una etiqueta introducida manualmente antes del benchmark.

El flujo de A01 quedó endurecido para capturar el perfil físico mediante `scripts.hardware_profile.profile()` antes de autorizar/registrar la ejecución.

Esto evita una clase de contaminación muy peligrosa:

```text
hardware declarado
       ≠
hardware ejecutado
```

La evidencia debe conservar el segundo.

## 5.1 CPU

El perfilador intenta obtener el modelo de CPU mediante fuentes Linux independientes del idioma, priorizando `/proc/cpuinfo` y utilizando `lscpu` como fuente estructurada complementaria.

El perfil conserva por separado:

- `cores`: núcleos físicos cuando pueden determinarse;
- `threads`: hilos lógicos;
- `architecture`;
- `model`.

En la máquina utilizada para la auditoría final se obtuvo:

```text
Intel(R) Core(TM) i5-1035G1 CPU @ 1.00GHz
4 physical cores
8 logical threads
x86_64
```

## 5.2 Memoria

Las decisiones de encaje utilizan preferentemente `total_bytes`, no la memoria libre instantánea.

Esto es deliberado: la memoria disponible cambia con el estado del sistema y no debe convertirse accidentalmente en la capacidad física nominal del host.

En la auditoría final:

```text
RAM física: 7.0 GiB aproximadamente
```

El perfil conserva también `available_bytes` como observación instantánea, pero no sustituye a la capacidad total para las decisiones de model-fit.

## 5.3 Red

`network_bandwidth()` intenta leer velocidades de enlace expuestas por sysfs.

Una interfaz que no exponga velocidad, una interfaz virtual o un error de permisos no invalida el perfil completo.

Por ello un resultado como:

```json
{}
```

es una ausencia de medición de ancho de banda, no una afirmación de ancho de banda cero.

No se ejecuta tráfico de red para inferir una velocidad que el contrato no haya solicitado.

---

# 6. Llama.cpp como primer runtime físico

El primer runtime físico consolidado de LEONES es **llama.cpp**, por su capacidad de ejecución local y su amplio soporte de hardware y cuantización.

La documentación oficial actual de llama.cpp mantiene como vías principales `llama-cli`, `llama-server`, construcción desde fuente y binarios publicados. También documenta soporte de cuantizaciones GGUF y múltiples backends. Véase el [README oficial de llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/README.md).

La documentación específica de la CLI mantiene `-m/--model` para el modelo y documenta los parámetros de ejecución disponibles en la versión actual: [llama.cpp CLI README](https://github.com/ggml-org/llama.cpp/blob/master/tools/cli/README.md).

### Regla LEONES

El adaptador no convierte la CLI en una caja negra. Construye una lista de argumentos separada, verificable y sin shell intermedio.

---

# 7. Contrato de comando llama.cpp

El adaptador `scripts/runtimes/llama_cpp_adapter.py` tiene la firma:

```python
build_command(
    executable: str,
    model_path: str,
    prompt: str,
    *,
    context_tokens: int | None = None,
    max_output_tokens: int = 128,
) -> list[str]
```

La forma básica conserva el contrato histórico:

```text
llama-cli -m MODEL -p PROMPT
```

Cuando se solicita una ejecución explícitamente acotada, el adaptador genera:

```text
llama-cli -m MODEL -p PROMPT --simple-io --single-turn -c CONTEXT -n OUTPUT
```

El modo acotado es el contrato relevante para una medición determinista porque:

- evita depender de interacción de terminal;
- fija el contexto;
- fija el máximo de salida;
- establece una condición de finalización explícita;
- mantiene los argumentos separados y auditables.

La auditoría final ejecutó el contrato en forma puramente determinista mediante aserciones y obtuvo:

```text
LLAMA.CPP CONTRACT: PASS
```

### Importante

La rama mantiene deliberadamente el comportamiento histórico de `build_command()` cuando no se especifica `context_tokens`. El endurecimiento se activa cuando la ejecución se declara explícitamente acotada.

Esto evita romper consumidores heredados mientras el camino de benchmark utiliza siempre una configuración controlada.

---

# 8. Repetición y warm-up

El protocolo separa dos conceptos:

### Warm-up

Las primeras ejecuciones pueden incluir costes que no representan el régimen estable que queremos comparar: carga de pesos, inicialización de backend, asignación de memoria, compilación/JIT cuando exista, inicialización de kernels o cachés.

El warm-up se conserva como metadato experimental y **no debe mezclarse silenciosamente con las muestras principales**.

### Medición

Las ejecuciones principales se realizan después del warm-up y se conservan como muestras individuales.

El número de muestras debe quedar registrado, no inferido retrospectivamente.

Cuando existen cinco ejecuciones físicas, por ejemplo, LEONES debe conservar las cinco y cualquier promedio debe ser derivable de ellas. El promedio no sustituye al histórico de muestras.

---

# 9. Métricas

## 9.1 Tokens por segundo

`tokens_per_second` / `measured_tps` representa el throughput observado bajo las condiciones de la ejecución.

No significa:

> "este modelo produce siempre X tokens/s".

Significa:

> "esta configuración concreta produjo X tokens/s bajo este hardware, runtime, modelo, cuantización, contexto, prompt y protocolo".

## 9.2 Latencia

Cuando está disponible, LEONES debe conservar las magnitudes de latencia relevantes por separado, especialmente:

- TTFT — time to first token;
- tiempo total de generación;
- tiempo de pared;
- latencia media por token cuando pueda derivarse correctamente.

No deben mezclarse estas magnitudes con throughput sin conservar su definición.

## 9.3 Memoria

Cuando sea posible, se conserva la memoria utilizada/observada junto con la memoria física del host y, si existe, VRAM.

La memoria de hardware y la memoria utilizada por una ejecución son variables distintas.

## 9.4 Consumo energético

El consumo solo debe registrarse cuando exista una fuente de medición real o un mecanismo suficientemente trazable.

Si no existe, debe permanecer ausente/`unknown`, nunca inventado mediante una estimación presentada como medición.

---

# 10. Metodología y relación con Artificial Analysis

LEONES adopta una idea metodológica importante de [Artificial Analysis](https://artificialanalysis.ai/methodology): las cifras de rendimiento tienen valor cuando describen condiciones reales de uso y cuando las condiciones de comparación se mantienen controladas.

Su metodología de rendimiento para APIs insiste en medir la experiencia real del usuario y no el máximo teórico de una plataforma. Véase [Artificial Analysis — Performance Benchmarking](https://artificialanalysis.ai/methodology/performance-benchmarking).

LEONES traslada esa filosofía al **runtime físico local**, pero no afirma que ambos experimentos sean equivalentes.

### Diferencia fundamental

Artificial Analysis mide principalmente endpoints/sistemas de inferencia disponibles para usuarios. LEONES, en este jalón, mide:

```text
host físico del usuario
        +
runtime local
        +
modelo/artefacto local
        +
configuración controlada
        +
ejecución real
```

Por tanto:

> **Las métricas LEONES son evidencia local reproducible, no una réplica de un benchmark de proveedor.**

Esta separación evita comparar directamente números que proceden de condiciones incompatibles.

---

# 11. Evidencia real A01 utilizada como prueba de cierre

La auditoría final verificó el artefacto:

```text
artifacts/a01-ollama-real-result-v5.json
```

Y confirmó:

```text
status             = success
evidence           = measured
measurement_kind   = real
measured_tps       = 47.9714
execution_id       = 3a5f9e90-b8c5-4fb9-a801-b9413420f9a4
```

Hardware registrado:

```text
Intel(R) Core(TM) i5-1035G1 CPU @ 1.00GHz
RAM: 7.0 GiB
```

La prueba también verificó que el bloque `hardware` de la evidencia coincide con el hardware del `execution_plan`:

```text
hardware consistency: PASS
```

### Qué demuestra este resultado

Demuestra que LEONES ya puede conservar una medición real asociada a una ejecución identificable y a un perfil hardware concreto.

### Qué NO demuestra

No demuestra que `47.9714 tok/s` sea una propiedad universal de Ollama, del modelo, del CPU i5-1035G1 ni de cualquier otra máquina.

Es una observación de una ejecución concreta.

---

# 12. Quality gates de JALÓN 3

El cierre se consideró válido porque la auditoría final cumplió simultáneamente:

```text
WORKTREE: CLEAN
256 tests passed
DIFF CHECK: PASS
LLAMA.CPP DEFAULT: PASS
LLAMA.CPP BOUNDED: PASS
A01 REAL: PASS
hardware consistency: PASS
HEAD == origin/jalon3-measurement-protocol
```

Resultado:

> **JALÓN 3 — AUDITORÍA FINAL COMPLETADA**

---

# 13. Qué queda fuera del jalón

Cerrar el protocolo no significa que todas las mediciones físicas futuras ya estén ejecutadas.

Quedan fuera del cierre, como trabajo de los siguientes jalones:

- medir una batería amplia de modelos;
- ejecutar sistemáticamente la matriz de hardware;
- medir todos los runtimes;
- comparar backends en condiciones equivalentes;
- incorporar GPU/VRAM/PCIe con mediciones reales cuando estén disponibles;
- añadir consumo energético físico donde exista instrumentación;
- ampliar TTFT y métricas de generación a todos los runners;
- automatizar la publicación de benchmarks físicos;
- alimentar de forma completa el recomendador con evidencia medida.

JALÓN 3 cierra el **contrato**, no el universo de mediciones.

---

# 14. Evidencia externa y enlaces de referencia revisados

Los enlaces principales utilizados para fundamentar el protocolo se revisaron contra documentación pública de sus proyectos:

### llama.cpp

- [Repositorio oficial](https://github.com/ggml-org/llama.cpp)
- [README oficial](https://github.com/ggml-org/llama.cpp/blob/master/README.md)
- [CLI README](https://github.com/ggml-org/llama.cpp/blob/master/tools/cli/README.md)
- [Server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [Server benchmark README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/bench/README.md)

El README oficial documenta ejecución local con `llama-cli`, servidor OpenAI-compatible, GGUF, cuantizaciones y múltiples backends. La documentación de servidor y CLI se mantiene separada, por lo que LEONES no debe asumir que un parámetro válido para un modo es automáticamente válido para otro.

### Ollama

- [Repositorio oficial](https://github.com/ollama/ollama)
- [README oficial](https://github.com/ollama/ollama/blob/main/README.md)
- [Documentación](https://github.com/ollama/ollama/tree/main/docs)

La documentación actual de Ollama mantiene rutas específicas para Linux, macOS, Windows, Docker, API y otros usos. LEONES conserva Ollama como runtime independiente de llama.cpp y no mezcla sus métricas sin una metodología común.

### Artificial Analysis

- [Metodología general](https://artificialanalysis.ai/methodology)
- [Performance benchmarking](https://artificialanalysis.ai/methodology/performance-benchmarking)

La metodología sirve como referencia conceptual para condiciones controladas, experiencia real y separación entre rendimiento observado y máximo teórico. LEONES adapta esos principios al entorno local y declara explícitamente la diferencia de alcance.

### Hugging Face

- [Hugging Face](https://huggingface.co/)
- [Model Hub](https://huggingface.co/models)

Para modelos GGUF, llama.cpp documenta el uso de repositorios compatibles de Hugging Face. LEONES debe conservar la identidad del repositorio/revisión y del archivo concreto cuando estos datos formen parte de la evidencia.

---

# 15. Política de enlaces en la documentación LEONES

Los README y documentos de LEONES deben preferir:

1. documentación oficial del proyecto citado;
2. repositorio oficial;
3. documentación versionada cuando exista;
4. fuente primaria del modelo o runtime;
5. fuentes secundarias solo cuando aporten contexto y se identifiquen como tales.

Un enlace no debe utilizarse como sustituto de la evidencia experimental.

En particular:

```text
README externo
     ↓
fuente de contexto
     ↓
contrato LEONES
     ↓
ejecución real
     ↓
evidencia LEONES
```

La existencia de documentación oficial no convierte una cifra publicada allí en `measured` por LEONES.

---

# 16. Reproducibilidad

Una tercera persona debe poder reconstruir la procedencia de una medición a partir de:

```text
execution_id
    + timestamp UTC
    + model identity
    + artifact identity/hash
    + runtime/version
    + command
    + hardware
    + context
    + prompt/protocol
    + warm-ups
    + repetitions
    + observed metrics
    + stdout/stderr
    + evidence artifact
```

Si falta un dato que sea imprescindible para interpretar la cifra, debe declararse como desconocido o no disponible.

**Nunca se rellena silenciosamente.**

---

# 17. Regla de promoción

Una cifra solo puede pasar de una capa de conocimiento a otra si existe evidencia suficiente para justificar el salto.

Ejemplo:

```text
reported
   ↓
observed
   ↓
measured
   ↓
validated
   ↓
verified
```

Cada transición requiere su propio criterio.

En particular, un benchmark externo nunca debe promocionarse automáticamente a `measured`.

---

# 18. Relación con la recomendación

El valor final de JALÓN 3 no es el benchmark aislado.

La arquitectura objetivo de LEONES es:

```text
modelo
  ↓
identidad Atlas
  ↓
hardware del usuario
  ↓
fit / compatibilidad
  ↓
runtime autorizado
  ↓
medición física
  ↓
evidencia
  ↓
benchmark medido
  ↓
CABE/RULA u otras métricas derivadas
  ↓
recomendación
```

La recomendación puede utilizar una medición, pero debe conservar el vínculo con su evidencia y con las condiciones bajo las que se obtuvo.

Esto permite responder no solo:

> "¿Qué modelo es bueno?"

sino:

> **"¿Qué modelo, con qué cuantización, en qué runtime y sobre qué hardware, ha demostrado funcionar en estas condiciones?"**

---

# 19. Checklist de cierre

- [x] Contrato de medición definido.
- [x] Identidad del modelo contemplada.
- [x] Cuantización contemplada.
- [x] Artefacto/hash contemplado.
- [x] Runtime y versión contemplados.
- [x] Comando ejecutado contemplado.
- [x] Hardware real capturado.
- [x] RAM total diferenciada de RAM disponible.
- [x] CPU física diferenciada de hilos lógicos.
- [x] Ausencia de velocidad de red tratada como dato desconocido, no cero.
- [x] Contexto y límite de generación contemplados.
- [x] Warm-up y repeticiones contemplados.
- [x] `execution_id` contemplado.
- [x] Timestamp UTC contemplado.
- [x] stdout/stderr y artefactos contemplados.
- [x] Evidencia `measured` separada de estimaciones/reportes.
- [x] A01 real validado.
- [x] Consistencia hardware evidencia ↔ execution plan validada.
- [x] Adaptador llama.cpp probado.
- [x] Comando acotado llama.cpp probado.
- [x] 256 tests pasan.
- [x] `git diff --check` limpio.
- [x] Rama remota sincronizada.
- [x] Enlaces principales de README/documentación externa revisados.

---

# 20. Veredicto

## 🟢 JALÓN 3 CERRADO

JALÓN 3 establece el **contrato operativo de medición real de LEONES**.

Desde este punto, el trabajo futuro debe concentrarse en **ejecutar mediciones bajo el contrato**, no en volver a decidir qué significa una medición.

La siguiente ejecución física deberá seguir el principio:

```text
seleccionar
→ autorizar
→ ejecutar
→ medir
→ conservar
→ validar
→ publicar
```

Y nunca:

```text
medir
→ interpretar después las condiciones
→ reconstruir la evidencia
```

**La evidencia se captura en el momento de la ejecución.**

---

## Referencias internas

- `scripts/hardware_profile.py`
- `scripts/runtimes/llama_cpp_adapter.py`
- `scripts/run_a01_selected.py`
- `scripts/selection_pipeline.py`
- `scripts/runtime_benchmark_evidence.py`
- `scripts/runtimes/run_llama_cpp_selected.py`
- `artifacts/a01-ollama-real-result-v5.json`
- `tests/test_llama_cpp_adapter.py`
- `tests/test_run_llama_cpp_selected.py`
- `tests/test_run_and_record_benchmark_integration.py`
- `tests/contracts/test_llama_cpp_adapter_v11.py`
- `tests/contracts/test_runtime_selection_benchmark_e2e_v11.py`
