# Runtime selection V1.1

V1.1 amplía la ejecución sin modificar el contrato de evidencia de V1.

## Camino único

```text
selector
  -> runtime-selection.v1
  -> runtime_registry.v1.1
  -> capability match
  -> trusted adapter
  -> runner
  -> runtime-benchmark.v1
  -> evidence / Router
```

El selector no conoce comandos, módulos Python ni entrypoints concretos. El registry declara capacidades y un entrypoint confiable; el adapter valida la selección y prepara la ejecución. El runner es el único que ejecuta.

## Runtimes registrados

- llama.cpp
- FreeToken
- AirLLM
- Ollama
- vLLM
- SGLang
- MLX / MLX-LM
- ExLlama V2 / V3
- OpenVINO
- ONNX Runtime GenAI
- TensorRT-LLM

Cada entrada declara identidad, versión, modos, arquitecturas, formatos, backends, capacidades, entrypoint, disponibilidad, extracción de métricas y si requiere prueba física.

## Verificación

La regresión común verifica todos los adapters con fixtures controlados. No descarga modelos, no necesita GPU y no convierte `estimated_tps` en `measured_tps`.

El puente `runtime-benchmark.v1` conserva runtime, versión, modelo, cuantización, hardware, workload, protocolo y provenance. Solo un resultado producido por el runner puede pasar al puente de evidencia.

## Gates

- runtime desconocido: bloqueado;
- runtime no disponible en el host: bloqueado;
- plan no autorizado: bloqueado;
- entrypoint no confiable: bloqueado;
- incompatibilidad de arquitectura/formato/modo/backend/capacidad: bloqueado;
- ausencia de medición: no hay evidencia de rendimiento medido.

FreeToken conserva su gate específico de elegibilidad dentro de su adapter; las cifras publicadas externamente siguen siendo evidencia externa, no medición LEONES.

## Pruebas físicas

La CI solo valida el contrato y el flujo con fixtures controlados. Las pruebas físicas de cada runtime quedan reservadas al host adecuado. Esto incluye, entre otros, Apple Silicon para MLX/MLX-LM, CUDA/NVIDIA para TensorRT-LLM y ExLlama, y hosts Intel adecuados para OpenVINO.

La existencia de un adapter no implica que el runtime haya sido ejecutado físicamente por LEONES.
