# Reglas básicas de LEONES

Estas reglas son **normas básicas del proyecto**, no recomendaciones opcionales.

## 1. Código y documentación avanzan juntos

Todo cambio funcional relevante debe documentarse al mismo tiempo en:

- código;
- documentación técnica del repositorio;
- web pública de LEONES cuando afecte a su arquitectura, operación, metodología o uso.

No se considera terminado un bloque si solo está implementado en código.

## 2. Simplicidad

> **Scripts sencillos que hagan las menores cosas posibles y estén muy documentados.**

Un script debe tener una responsabilidad clara. La composición de muchos scripts pequeños es preferible a un programa monolítico.

## 3. Autonomía

LEONES debe ser capaz de ejecutar modelos localmente por sí mismo. Ninguna aplicación de escritorio concreta es una dependencia estructural.

## 4. Backend independiente

llama.cpp, KTransformers, Unsloth, Ollama, vLLM, MLX, TensorRT-LLM y otros son adaptadores. El núcleo de LEONES no puede depender conceptualmente de uno de ellos.

## 5. Evidencia reproducible

Los resultados de ejecución, cuantización, fine-tuning y benchmarks deben conservar modelo, versión, configuración, hardware y estado de evidencia suficientes para reproducirlos.

## 6. Cambios pequeños y verificables

Cada bloque debe poder probarse aisladamente. Evitar introducir varias responsabilidades nuevas en un único cambio cuando puedan separarse.

## 7. No sobreingeniería

No añadir abstracciones, frameworks o dependencias hasta que una necesidad real las justifique.

## 8. Documentación viva

La documentación debe describir el estado real del sistema. Si el código cambia una decisión arquitectónica, la documentación debe cambiar en el mismo bloque.
