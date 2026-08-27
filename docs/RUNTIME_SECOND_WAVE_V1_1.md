# Segunda oleada de runtimes — V1.1

## Objetivo

Dejar cerrada la capa declarativa para la segunda oleada, sin afirmar ejecución física. El contrato común es:

```text
runtime-selection.v1
  -> runtime-registry.v1.1
  -> capability match
  -> trusted adapter
  -> host preflight
  -> runner
  -> runtime-benchmark.v1
  -> evidence
```

El adapter **no ejecuta** el runtime. Produce una `RuntimeExecutionSpec` con identidad, entrypoint declarado, métricas y requisitos de host. La ejecución queda exclusivamente en el runner cuando exista un host apropiado.

## Segunda oleada

| Runtime | Host principal | Formatos/capa | Validación física |
|---|---|---|---|
| vLLM | NVIDIA CUDA / AMD ROCm / host soportado | safetensors, GGUF, GPTQ, AWQ, FP8, INT8/4 | pendiente de host |
| SGLang | NVIDIA CUDA / AMD ROCm | safetensors, GPTQ, AWQ, FP8, INT8/4 | pendiente de host |
| MLX / MLX-LM | Apple Silicon, preferente | safetensors / MLX | macOS/Apple Silicon |
| ExLlama V2/V3 | NVIDIA CUDA | EXL2 / EXL3 / GPTQ | host CUDA |
| OpenVINO | Intel CPU/GPU/NPU | OpenVINO / ONNX | host Intel |
| ONNX Runtime GenAI | CPU/GPU/NPU según execution provider | ONNX | host con provider compatible |
| TensorRT-LLM | NVIDIA CUDA | TensorRT-LLM / safetensors | host NVIDIA |

Estas declaraciones proceden del contrato de runtime V1.1 y de la arquitectura documentada para motores de inferencia. No constituyen resultados de rendimiento.

## Contrato de cada adapter

Todos los adapters de la segunda oleada deben cumplir:

1. Identidad runtime → adapter inequívoca.
2. Modelo identificado.
3. Cuantización/formato declarado.
4. Arquitectura, modo y backend comprobables contra el registry.
5. Capacidades requeridas comprobables.
6. Entrypoint tomado únicamente del registry confiable.
7. Requisitos de host declarados, pero no inferidos como ejecución real.
8. `physical_test_required=true`.
9. Ninguna estimación puede convertirse en medición.
10. Toda medición física posterior debe pasar por `runtime-benchmark.v1` y conservar provenance.

## Host requirements

`host_requirements` es una lista declarativa. No significa que el host actual cumpla esos requisitos.

Ejemplos:

- `nvidia-cuda`: requiere validación de CUDA/NVIDIA en el host real.
- `apple-silicon-preferred`: reserva MLX/MLX-LM para validación apropiada de Apple Silicon.
- `intel-openvino-runtime`: requiere runtime OpenVINO instalado y dispositivo Intel compatible.
- `supported-execution-provider`: requiere identificar el Execution Provider real de ONNX Runtime GenAI.
- `serving-port-available`: solo puede verificarse cuando se prepara un servidor físico.
- `model-artifact-available`: exige que el artefacto exacto esté disponible y fijado por identidad/hash.

## Separación estimación / medición

La información externa de benchmarks o rendimiento sirve para conocimiento y selección. No se convierte en `measured_tps` de LEONES. Una medición válida debe proceder de una ejecución autorizada, con modelo, revisión, cuantización, contexto, protocolo, hardware, runtime, versión y `execution_id` registrados.

## Orden de validación física

1. **Debian:** runtimes compatibles con el host, empezando por llama.cpp ya preparado.
2. **Debian/CUDA si está disponible:** vLLM → SGLang → ExLlama → TensorRT-LLM.
3. **Debian/Intel si corresponde:** OpenVINO → ONNX Runtime GenAI.
4. **macOS/Apple Silicon:** MLX/MLX-LM.

No se instala ni ejecuta ninguno de estos runtimes como parte del contrato declarativo.

## Criterio de cierre de la segunda oleada declarativa

La segunda oleada está preparada cuando CI demuestra que los siete adapters:

- existen y están registrados;
- coinciden con su identidad del registry;
- aceptan un plan controlado compatible;
- rechazan incompatibilidades;
- exponen requisitos de host;
- no ejecutan procesos;
- generan una especificación apta para el runner;
- mantienen `physical_test_required=true`.

El siguiente salto ya no es de diseño: es **validación física en el host adecuado**.

## Base metodológica

La serie LLM de referencia establece que el motor debe elegirse después de considerar hardware, carga, memoria, formato y objetivo de servicio. Para benchmarking serio recomienda registrar modelo, cuantización, versión del motor, hardware, workload y métricas como TTFT, TPOT y tokens por segundo. También separa evaluación de desarrollo y prueba final, y exige congelar el protocolo antes de la medición final.
