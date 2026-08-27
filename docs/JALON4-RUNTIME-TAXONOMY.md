# JALÓN 4 — Runtime taxonomy and selection

## Objetivo

Ampliar `runtime-selection` sin alterar `runtime-benchmark-evidence.v1.1`, que permanece cerrado por JALÓN 3.

## Taxonomía operativa

`deployment_class` describe dónde encaja principalmente un runtime:

- `local`: ejecución en equipo personal.
- `edge`: equipo local/edge con recursos limitados o especializados.
- `workstation`: estación de trabajo con GPU/CPU potente.
- `small_server`: servidor pequeño o dedicado.
- `datacenter`: servidor de producción en CPD.
- `distributed_datacenter`: despliegue distribuido entre múltiples aceleradores/nodos.

`serving_profile` describe la carga:

- `single_user`
- `low_concurrency`
- `multi_user`
- `high_throughput`
- `distributed`

## Clasificación registrada

| Runtime | Clases principales | Perfiles principales |
|---|---|---|
| llama.cpp | local, edge, workstation, small_server | single_user, low_concurrency |
| FreeToken | edge, workstation, small_server | single_user, low_concurrency, multi_user |
| AirLLM | local, edge, workstation, small_server | single_user, low_concurrency |
| Ollama | local, edge, workstation, small_server | single_user, low_concurrency, multi_user |
| MLX/MLX-LM | local, edge, workstation | single_user, low_concurrency, distributed |
| ExLlama | local, edge, workstation | single_user, low_concurrency, multi_user |
| OpenVINO | local, edge, workstation, small_server | single_user, low_concurrency, multi_user |
| ONNX Runtime GenAI | local, edge, workstation, small_server | single_user, low_concurrency, multi_user |
| vLLM | small_server, datacenter, distributed_datacenter | multi_user, high_throughput, distributed |
| SGLang | small_server, datacenter, distributed_datacenter | multi_user, high_throughput, distributed |
| TensorRT-LLM | datacenter, distributed_datacenter | multi_user, high_throughput, distributed |

Esta clasificación es **de selección**, no una afirmación de rendimiento. El rendimiento efectivo continúa requiriendo medición física bajo `runtime-benchmark-evidence.v1.1`.

## Regla de evidencia

No se transforma una capacidad declarada, estimación o benchmark externo en `measured_tps`. La ejecución física sigue siendo obligatoria cuando `physical_test_required=true`.

## Gate de JALÓN 4

Antes de cualquier prueba física deben quedar verdes:

1. esquema `runtime-selection.v1.1` válido;
2. registro completo y sin identidades duplicadas;
3. adapters compatibles con el límite del registry;
4. selección capaz de filtrar por `deployment_class` y `serving_profile`;
5. tests y CI verdes;
6. documentación de qué pruebas físicas son realmente ejecutables en el host.

## Intervención física

La intervención del usuario queda aplazada hasta que el repositorio pueda indicar **exactamente qué runtime, modelo, backend, comando y protocolo deben ejecutarse** en el Ubuntu físico.

No se solicita instalar ni ejecutar los runtimes de CPD en el equipo local cuando el hardware no sea su destino natural. Esos runtimes pueden quedar contractualmente preparados y se medirán posteriormente en hosts apropiados.

## Continuidad

JALÓN 3 permanece cerrado. Este jalón añade taxonomía y selección; no modifica el contrato de evidencia física.
