# Runtimes de referencia fuera de JALÓN 4

Estos runtimes permanecen documentados como conocimiento técnico y no forman parte de la selección operativa de JALÓN 4.

| Runtime | Motivo de exclusión operativa en JALÓN 4 | Reentrada futura |
|---|---|---|
| MLX / MLX-LM | Especialización Apple Silicon/unified memory; no es objetivo del host Ubuntu actual | Host Apple apropiado |
| ExLlama | Runtime GPU especializado; no aporta una segunda familia prioritaria frente a la selección actual | GPU NVIDIA y caso de uso específico |
| OpenVINO | Interesante para Intel CPU/GPU/NPU, pero no pertenece al carril SOHO/CPD elegido | Host Intel/NPU y prueba específica |
| ONNX Runtime GenAI | Capa generalista multiplataforma; se conserva como alternativa de backend | Caso ONNX/EP concreto |
| TensorRT-LLM | Muy orientado a serving acelerado NVIDIA y despliegues de CPD; se reserva para una fase específica de GPU NVIDIA | CPD NVIDIA con hardware apropiado |

La exclusión es de **selección**, no de conocimiento. Sus adaptadores/fichas pueden permanecer en el repositorio para futuras fases, pero no deben aparecer como candidatos operativos de JALÓN 4.
