# VRAMBudget

## Identidad
- Fuente primaria: https://github.com/webdevtodayjason/vrambudget
- Web: https://vrambudget.com/
- Capa: estimador de memoria.
- Estado LEONES: `research-candidate`.

## Qué es
Calculadora centrada en responder qué LLM cabe en una GPU mediante presupuesto explícito de VRAM, con una colección de GPUs y modelos.

## Qué aporta
Su interés metodológico está en convertir la VRAM disponible en un presupuesto y separar el espacio de memoria de pesos, KV cache, overhead y margen de seguridad.

## Evidencia
La fuente pública describe el proyecto como “VRAM math” para 40+ GPUs y 20+ modelos. Estas cifras son características del proyecto y deben conservarse con fecha/revisión.

## Estimación
El resultado es una estimación de fit/memoria. No implica velocidad ni calidad funcional.

## Medición LEONES
Pendiente. Puede servir como cross-check matemático de la memoria prevista antes de lanzar un benchmark.

## Valor para LEONES
Refuerza la capa de **estimación** y ayuda a evitar que “cabe en VRAM” se interprete como “funciona bien”.

## Próximo paso
Revisar fórmula y dataset, comparar sus presupuestos con LLMFit/localmodel.run y diseñar casos de discrepancia para el quality gate.