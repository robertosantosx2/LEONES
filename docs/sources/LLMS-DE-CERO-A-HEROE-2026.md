# LLMs de Cero a Héroe — fuente de conocimiento LEONES

**Fuente de origen:** serie de Ahmad Osman (@TheAhmadOsman), compilada en agosto de 2026.

**Material incorporado:** `serie_llm_de_cero_a_heroe_2026.md` de la biblioteca de trabajo de LEONES.

**Tipo:** fuente de conocimiento / fundamentos técnicos / metodología de evaluación.

**Clasificación LEONES:** `source-inspiration`.

## 1. FUENTE / DESCUBRIMIENTO

La serie reúne seis piezas sobre: matemática de memoria GPU para LLM; ancho de banda de memoria para IA local; motores de inferencia; funcionamiento práctico de LLMs; proyectos de ingeniería LLM; y disciplina de evaluación limpia.

La serie propone, entre otras ideas, separar capacidad de memoria, ancho de banda y pila de software; distinguir prefill de decode; incluir KV cache, batching y overhead del runtime en el presupuesto; y elegir el runtime después de considerar hardware, workload, contexto, concurrencia, formato y objetivo de servicio.

## 2. EVIDENCIA

El contenido de la serie es evidencia documental de lo que **la fuente afirma**, no evidencia experimental de LEONES. Sus afirmaciones de hardware, runtimes y rendimiento deben conservar condiciones y contrastarse con documentación primaria y mediciones actuales.

Un principio especialmente relevante para LEONES es que un benchmark/test deja de ser una prueba limpia si se optimiza directamente contra él. La fuente recomienda separar entrenamiento, validación y prueba, congelar protocolos, controlar contaminación y distinguir evaluación de desarrollo de auditoría.

## 3. ESTIMACIÓN

La serie sirve como base para formular hipótesis de selección y presupuesto, por ejemplo:

```text
memoria total ≈ pesos + KV cache + overhead runtime + batch/concurrencia + margen
```

También orienta a considerar bandwidth, contexto, arquitectura densa/MoE, prefill/decode e interconexión. Estas relaciones son **criterios/estimaciones conceptuales**, no mediciones LEONES.

LEONES no debe convertir las cifras de la serie en predicciones universales de tokens/s para una máquina concreta sin pasar por su propio modelo de estimación y, posteriormente, por medición.

## 4. MEDICIÓN LEONES

**No aplica directamente.**

La serie no produce ejecuciones del pipeline LEONES. Las hipótesis derivadas de ella deben desembocar en pruebas reales de hardware/runtime/workload. Cuando exista una medición, se registrará independientemente con modelo, runtime, versión, hardware, configuración, workload, TTFT, TPOT/tok/s, memoria, grader y evidence ID.

## 5. Valor para LEONES

La fuente alimenta principalmente el diseño conceptual de `runtime-selection.v1`, la comprensión de cuellos de botella y el contrato de benchmarks. No tiene autoridad para seleccionar un runtime concreto ni para sustituir evidencia primaria.

**Próximo gate:** usar sus principios como criterios de diseño y comprobarlos contra los benchmarks reproducibles de LEONES.
