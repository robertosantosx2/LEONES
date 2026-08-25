# CanIRunLLMs

## Identidad
- Fuente primaria: https://canirunllms.com/
- Capa: calculadora de memoria/compatibilidad.
- Estado LEONES: `research-candidate`.

## Qué es
Herramienta orientada a comprobar si un LLM local cabe en la memoria disponible y comparar estrategias como FP16 y cuantización.

## Qué aporta
Su interés está en explicitar VRAM/RAM, pesos y KV cache y convertir esos datos en una decisión preliminar de compatibilidad.

## Evidencia
La web publica cálculos y recomendaciones de ejecución. Al ser un servicio externo, sus resultados se conservan como evidencia/metodología externa.

## Estimación
La memoria requerida y la compatibilidad son estimaciones. No deben convertirse en `measured_tps` ni en una recomendación LEONES sin ejecución.

## Medición LEONES
Pendiente.

## Valor para LEONES
Sirve como tercer punto de comparación en el bloque de estimadores de memoria y puede ayudar a localizar discrepancias entre modelos de cálculo.

## Próximo paso
Registrar versión/metodología y contrastar casos límite con VRAMBudget, LLMFit y localmodel.run.