# Can I run this LLM?

## Identidad
- **Fuente:** https://canirunthisllm.com/
- **Capa:** calculadora hardware ↔ modelo.
- **Estado LEONES:** `research-candidate`.
- **Revisión:** 2026-08-25.

## Qué es
Herramienta web que cruza un hardware seleccionado con LLM locales y devuelve una primera estimación de compatibilidad, memoria y cuantización.

## Problema
Es una implementación independiente del problema que LEONES está resolviendo. Su principal utilidad aquí es **triangular estimadores**: cuando dos o más calculadores discrepan, la discrepancia revela una hipótesis que merece prueba.

## Evidencia
Los resultados se consideran claims de la calculadora externa. La fuente no se transforma en evidencia propia solo por coincidir con otra herramienta.

## Estimación
Fit, memoria y cuantización son estimaciones. No deben registrarse como `measured_tps`, `measured_memory` ni recomendación LEONES.

## Relación con CanIRun.ai
Ambas herramientas comparten el patrón «¿puedo ejecutar esto?». CanIRun.ai añade detección desde navegador; esta herramienta sirve como referencia externa independiente para el cálculo.

## Relación con LLMFit
LLMFit parte de hardware/intención para ordenar candidatos; esta herramienta sirve mejor como cross-check de un modelo/configuración concreta.

## Medición LEONES
Pendiente. Debe comprobarse el mismo modelo, cuantización, contexto y runtime indicado por la herramienta.

## Valor para LEONES
Medio-alto como **segunda opinión reproducible** dentro de la fase de prospección.

## Integración

```text
model + hardware
       ↓
external estimate
       ↓
cross-validation
       ↓
runtime-selection.v1
       ↓
executor → grader → benchmark
```

## Limitaciones
- No garantiza runtime disponible.
- No garantiza rendimiento útil.
- No garantiza estabilidad.
- Las estimaciones dependen de datos externos y pueden quedar obsoletas.

## Clasificación
`research-candidate`.

## Próximo paso
Comparar un conjunto fijo de modelos con LLMFit, localmodel.run, VRAMBudget y CanIRun.ai, conservando el resultado de cada fuente por separado.