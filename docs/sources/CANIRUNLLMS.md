# CanIRunLLMs

## Identidad
- **Fuente:** https://canirunllms.com/
- **Capa:** calculadora de memoria/compatibilidad.
- **Estado LEONES:** `research-candidate`.
- **Revisión:** 2026-08-25.

## Qué es
Calculadora centrada en la pregunta física «¿cabe este LLM en mi memoria?». Su interés está en hacer explícitos pesos, VRAM/RAM, KV cache y diferencias entre precisiones/cuanti.

## Problema
Es una capa más estrecha que LLMFit: no pretende resolver toda la recomendación, sino reducir el riesgo de intentar modelos que exceden el presupuesto de memoria.

## Evidencia
La web se conserva como fuente de su metodología y resultados publicados. Son claims externos hasta que LEONES los reproduce.

## Estimación
La memoria requerida, fit y recomendación de cuantización son **estimaciones externas**.

## Medición LEONES
Pendiente. Debe contrastarse especialmente en modelos donde KV cache u overhead cambian el resultado respecto a una simple estimación por parámetros.

## Relación con VRAMBudget
Ambas herramientas ocupan la misma familia metodológica. VRAMBudget hace explícito un presupuesto de VRAM; CanIRunLLMs aporta una interfaz de decisión más directa. LEONES debe conservar ambas como referencias independientes.

## Relación con localmodel.run
localmodel.run destaca la trazabilidad de datos. CanIRunLLMs sirve principalmente como calculadora externa. La comparación puede revelar si dos herramientas producen el mismo verdict partiendo de datos diferentes.

## Valor para LEONES
Medio-alto como **cross-validator de memoria**. No debe convertirse en autoridad del selector.

## Integración

```text
hardware + model
       ↓
CanIRunLLMs estimate
       ↓
memory cross-check
       ↓
runtime-selection.v1
       ↓
executor / benchmark
```

## Limitaciones
- No demuestra velocidad.
- No demuestra calidad.
- KV cache depende de arquitectura/contexto.
- Runtime overhead depende del backend.
- Los datos externos pueden cambiar.

## Clasificación
`research-candidate`.

## Próximo paso
Crear casos límite: modelo que cabe justo, modelo que excede VRAM pero puede hacer offload y modelo MoE con diferencia entre parámetros activos y residentes.