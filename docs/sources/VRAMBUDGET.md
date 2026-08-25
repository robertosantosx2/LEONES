# VRAMBudget

## 1. Identidad
- **Fuente primaria:** https://github.com/webdevtodayjason/vrambudget
- **Web:** https://vrambudget.com/
- **Capa LEONES:** estimador de memoria.
- **Licencia declarada:** MIT.
- **Estado LEONES:** `research-candidate`.
- **Revisión:** 2026-08-25.

## 2. Qué es
VRAMBudget intenta eliminar la falsa precisión de los calculadores que solo multiplican parámetros por bits. Su tesis es construir un **presupuesto de VRAM** y descontar explícitamente KV cache, overhead del framework y margen de seguridad antes de decidir qué cantidad de memoria queda para pesos. fileciteturn23file0

## 3. Modelo matemático declarado
La fuente parte de:

```text
VRAM ≈ params × (bits ÷ 8)
```

y posteriormente calcula un presupuesto de pesos:

```text
weights_budget = total_vram × (1 − safety)
                 − kv_cache × concurrency
                 − framework_overhead
```

La importancia para LEONES no es adoptar esta fórmula como verdad universal, sino hacer explícitos los **impuestos de memoria** que suelen desaparecer en calculadoras simples. fileciteturn23file0

## 4. Variables
El calculador expone VRAM, RAM, contexto, concurrencia y margen de seguridad. La propia documentación aclara que RAM está reservada para futuras estrategias de split y que actualmente no entra en el cálculo principal. fileciteturn23file0

Para LEONES esto es una distinción útil:

```text
GPU VRAM budget
≠
system RAM budget
≠
actual process memory
```

## 5. Catálogo
La fuente revisada declara 40 presets de GPU, 20 modelos curados y 9 formatos de cuantización. También incluye vista de búsqueda de Hugging Face y clasificaciones `fits / tight / over`. fileciteturn23file0

Estos números son estado del proyecto en la revisión, no datos permanentes del Atlas.

## 6. Cuantización
El catálogo contempla FP16/BF16, FP8/INT8, Q8_0, Q6_K, Q5_K_M, Q4_K_M, Q3_K_M, AWQ y GPTQ. fileciteturn23file0

Esto permite a LEONES estudiar el impacto de la cuantización sobre fit sin reducirlo a un único INT4/FP16 simplificado.

## 7. Contexto y concurrencia
Una aportación especialmente relevante es hacer visible que el KV cache escala con contexto y concurrencia. La fuente señala que con contextos largos el KV puede convertirse en el impuesto dominante. fileciteturn23file0

LEONES debe conservar, como mínimo:

```text
context_tokens
concurrency
kv_estimate
safety_margin
runtime_overhead_estimate
weights_budget
```

## 8. MoE
El catálogo distingue modelos MoE y contempla `activeParams`. fileciteturn23file0

Pero el presupuesto de VRAM debe seguir la política del runtime: parámetros activos por forward no significan necesariamente que solo esos pesos residan en memoria.

Por ello LEONES debe separar:

- total params;
- active params;
- resident params;
- offloaded params;
- runtime strategy.

## 9. Runtimes
La fuente lista Ollama, LM Studio, MLX/oMLX y vLLM como runtimes asociados al cálculo. fileciteturn23file0

Esto refuerza una regla del proyecto: **fit es una propiedad de modelo + cuantización + hardware + runtime + configuración**, no solo de modelo + VRAM.

## 10. Agent View Layer
VRAMBudget publica rutas `.agent` y un manifest agent-readable. fileciteturn23file0

Es interesante como referencia de UX máquina-máquina para LEONES, pero no debe confundirse con nuestro contrato de evidencia.

## 11. Estimación
Todo resultado `fits / tight / over` y todo presupuesto de memoria es una **estimación**.

No proporciona por sí mismo:

- TTFT;
- tok/s real;
- calidad;
- estabilidad;
- éxito funcional del workload.

## 12. Medición LEONES
**Pendiente.**

Debe utilizarse como calculador previo al benchmark:

```text
VRAMBudget
    ↓
weights budget
    ↓
CANDIDATO
    ↓
runtime-selection.v1
    ↓
executor
    ↓
measured memory + tok/s
```

## 13. Relación con localmodel.run
VRAMBudget aporta una fórmula de presupuesto y localmodel.run aporta un catálogo de datos medidos y trazables. La combinación es metodológicamente potente:

```text
VRAMBudget = cálculo
localmodel.run = datos de entrada trazables
LEONES = ejecución y verificación
```

## 14. Relación con LLMFit
LLMFit intenta producir una decisión multidimensional; VRAMBudget es deliberadamente más estrecho: **memoria**. Por eso debe utilizarse como componente/cross-check, no como competidor del selector.

## 15. Valor para LEONES
Alto. Puede servir para construir un `memory-fit-v1` independiente que audite los supuestos de otros estimadores.

## 16. Limitaciones
1. La fórmula es una aproximación.
2. Overhead depende del runtime.
3. KV cache depende de arquitectura y configuración.
4. Offload cambia radicalmente la interpretación de VRAM.
5. Fit no implica velocidad.
6. Fit no implica calidad funcional.
7. El catálogo es curado y puede quedar obsoleto.

## 17. Clasificación
**`research-candidate` → estimador/cross-check de memoria.**

## 18. Próximo paso
Implementar un conjunto común de casos y registrar diferencias entre VRAMBudget, localmodel.run, LLMFit y LLM Checker. Las discrepancias deben alimentar tests de memoria y no un promedio opaco.