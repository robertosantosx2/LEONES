# localmodel.run

## Identidad
- Fuente primaria: https://github.com/ansumanshah/localmodel.run
- Web: https://localmodel.run/
- Capa: preselector/compatibility knowledge.
- Estado LEONES: `research-candidate`.

## Qué es
Comprobador de compatibilidad modelo ↔ dispositivo que publica requisitos de memoria y verdicts por modelo y plataforma. Su enfoque incluye matemática explícita de memoria y fuentes por dato.

## Qué aporta
Es especialmente valioso para LEONES porque separa datos y cálculo: modelos, dispositivos, tamaños GGUF y fuentes se conservan de forma trazable.

## Evidencia
El proyecto declara 150+ modelos y modalidades adicionales, con datos que enlazan a fuentes primarias. El código es MIT y el dataset se publica bajo CC BY 4.0 según su documentación.

## Estimación
Para LLM de texto considera pesos cuantizados + KV cache + overhead del runtime. El verdict de compatibilidad y memoria requerida es una estimación del proyecto.

## Medición LEONES
Pendiente. LEONES debe contrastar sus veredictos con ejecuciones reales y mantener `estimated_*` separado de `measured_*`.

## Valor para LEONES
Puede servir como fuente de **datos de compatibilidad trazables** y como segundo estimador frente a LLMFit/CanIRun.ai.

## Integración propuesta
`modelo + hardware → localmodel.run estimate → cross-validation → runtime-selection.v1 → executor → benchmark → evidence`.

## Limitaciones
La compatibilidad matemática no garantiza rendimiento útil, estabilidad ni calidad funcional.

## Próximo paso
Estudiar el dataset, sus `sources[]` y el modelo de memoria; importar únicamente datos con procedencia conservada.