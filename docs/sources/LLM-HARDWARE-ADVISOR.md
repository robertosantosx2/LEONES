# LLM-Hardware-Advisor

## Identidad
- Fuente primaria: https://github.com/gitstq/LLM-Hardware-Advisor
- Capa: preselector hardware-aware.
- Estado LEONES: `research-candidate`.

## Qué es
CLI que detecta CPU, GPU, RAM, disco y sistema operativo y recomienda LLM locales con cuantización, longitud de contexto y comandos para Ollama/llama.cpp.

## Qué problema resuelve
Reduce el espacio de búsqueda entre hardware disponible y modelos ejecutables, incluyendo el efecto de VRAM, cuantización y contexto.

## Fuente y evidencia
El README documenta detección mediante herramientas del sistema, una base integrada de modelos, puntuación de fitness 0–100, varias cuantizaciones y exportación JSON/Markdown. La fuente primaria debe conservarse como referencia; sus resultados siguen siendo externos a LEONES.

## Estimación
Su fitness score y sus cálculos de memoria/compatibilidad son **estimaciones externas**. Son útiles para generar candidatos, pero no equivalen a tok/s medidos por LEONES.

## Medición LEONES
Pendiente. Debe probarse con modelo/cuanti/runtime exactos y registrar TTFT, TPOT/tok/s, RAM/VRAM, I/O, contexto, estabilidad y resultado funcional.

## Valor para LEONES
Especialmente interesante por incorporar **RAM y disco** además de GPU/VRAM. Puede alimentar una comparación contra LLMFit y CanIRun.ai para estudiar qué variables predicen mejor el fit.

## Integración propuesta
`fuente → evidencia → estimación → candidate → runtime-selection.v1 → executor → grader → benchmark → measurement`.

## Limitaciones
Catálogo y heurísticas pueden quedar obsoletos; los scores dependen de sus supuestos y no sustituyen una ejecución real.

## Próximo paso
Verificar versión/release actual, extraer fórmula de scoring y ejecutar un caso controlado frente a LLMFit y CanIRun.ai.