# llm.asm-qwen4B

Subproyecto de LEONES dedicado a estudiar la adaptación y ejecución
de Qwen3-4B mediante el motor de inferencia llm.asm.

## Objetivo

Ampliar experimentalmente el soporte existente de llm.asm para evaluar
Qwen3-4B, preservando la implementación funcional de Qwen3-0.6B.

## Repositorios

- LEONES: https://github.com/robertosantosx2/LEONES
- Upstream: https://github.com/alesha-pro/llm.asm
- Clon local independiente: `/home/ssantos/leones-work/llm.asm-qwen4B-reference`

## Referencia upstream

- Commit de referencia: `48feccbfd57cb669440f31ff64958d95bb8b848e`
- Rama reportada: `main`
- Clon superficial: profundidad 1

El clon upstream se mantiene fuera del árbol Git de LEONES.
No modificarlo como parte de los experimentos de adaptación.

## Líneas de trabajo

1. Auditoría de arquitectura y dimensiones de Qwen3-4B.
2. Análisis de las limitaciones del formato ASMBIN.
3. Adaptación del exportador de pesos.
4. Adaptación del motor x86-64 y sus límites de memoria.
5. Validación numérica frente a una implementación de referencia.
6. Inferencia, rendimiento y escalado de contexto.
7. Archivo reproducible de resultados y registros.

## Experimento de partida

El antecedente es la campaña Qwen3-0.6B archivada en:

`docs/benchmarks/llm-asm-qwen3-0.6b-context-2026-11-25.md`

Los nuevos experimentos tendrán registros y resultados propios.
No sobrescribirán los datos históricos.
