# JALÓN 4 — Selección de runtimes

## Alcance operativo

JALÓN 4 reduce la ejecución física a dos familias y conserva el resto como conocimiento de referencia.

### SOHO / workstation

- `llama.cpp` — runtime base y referencia física.
- `FreeToken` — aceleración/offload en GPU NVIDIA.
- `AirLLM` — ejecución con offload por capas.
- `ollama` — servicio local orientado a uso sencillo y baja concurrencia.

### CPD / servidor multiusuario

- `vLLM` — serving multiusuario, batching y caché KV paginada.
- `SGLang` — serving multiusuario, batching y caché de prefijo/radix.

## Fuera de la lista operativa

`MLX/MLX-LM`, `ExLlama`, `OpenVINO`, `ONNX Runtime GenAI` y `TensorRT-LLM` no forman parte de la lista operativa de JALÓN 4. Sus fichas y conocimiento técnico se conservan como referencia para futuras selecciones por plataforma.

## Regla de ejecución

Ningún runtime se considera validado por aparecer en el registro. Todo runtime con `physical_test_required=true` debe producir evidencia compatible con `runtime-benchmark-evidence.v1.1` antes de ser recomendado por medición.

## Estrategia Ubuntu mínima

Antes de Ubuntu se validan contratos, registry, selección, preflight y tests. En Ubuntu sólo quedan las comprobaciones dependientes del host, instalación/servicio cuando proceda y ejecución física. El preflight debe fallar de forma explícita y no instalar paquetes ni descargar modelos por su cuenta.

## Orden físico previsto

1. `llama.cpp`
2. `ollama`
3. `AirLLM`
4. `FreeToken`
5. `vLLM`
6. `SGLang`

La comparación final sólo utilizará ejecuciones que conserven identidad del modelo, runtime, hardware, versión, parámetros y evidencia íntegra.
