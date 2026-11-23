# Mobile-LLMs-ARM — Roadmap técnico

Este roadmap organiza gates de investigación; no declara aceptación anticipada.

## G0 — Inventario y procedencia
- [ ] Consolidar proyectos Android, Linux ARM, runtimes, SDKs y aceleradores.
- [ ] Confirmar repositorio/fuente primaria, licencia, actividad y plataforma.
- [ ] Deduplicar y mantener historial; marcar candidatos no verificados.

## G1 — Matriz SoC/OS/acelerador
- [ ] ARM ISA: NEON, dotprod, i8mm y extensiones disponibles.
- [ ] Android API/ABI/NDK, root/no-root y restricciones de procesos.
- [ ] Linux móvil: kernel, firmware, GPU/NPU y estado de drivers.
- [ ] Qualcomm Hexagon/HTP, QNN/FastRPC; MediaTek y Exynos cuando haya documentación.
- [ ] Distinguir soporte teórico, compilación y ejecución probada.

## G2 — Runtime y modelos
- [ ] llama.cpp, MLC LLM, LiteRT y ExecuTorch.
- [ ] Termux/proot frente a app nativa/JNI.
- [ ] Modelos compactos, VLM, ASR/TTS, MoE ligeros y embeddings.
- [ ] Cuantización, KV cache, contexto, concurrencia y API local.

## G3 — Benchmark móvil NEPENTHES
- [ ] TTFT, prefill, decode y throughput sostenido.
- [ ] RAM, picos de memoria, energía por token y potencia.
- [ ] Temperatura, duración, thermal throttling y recuperación.
- [ ] Calidad de tarea junto al rendimiento.
- [ ] Guardar comandos, versiones, hashes, logs y CSV/JSON.

## G4 — Linux móvil y embedded
- [ ] postmarketOS, Ubuntu Touch y Linux ARM en dispositivos compatibles.
- [ ] Drivers, firmware, upstream status y restricciones de kernel.
- [ ] SBC/edge ARM como contraste, no sustituto de teléfono.

## G5 — Nodos y clústeres
- [ ] Teléfono como servidor local y nodo REDIL.
- [ ] Descubrimiento, health checks, colas, límites térmicos y scheduling.
- [ ] Medir red, latencia E2E y coste de particionado.
- [ ] Pool de teléfonos antiguos, energía, carga y seguridad.

## G6 — Curación e integración
- [ ] Revisión humana de candidatos, licencias y dependencias.
- [ ] Promoción selectiva a Atlas y adaptadores Router.
- [ ] Incorporación del protocolo a NEPENTHES si la evidencia lo justifica.
- [ ] Evaluar REDIL y publicar límites, fallos y no-resultados.

## Riesgos

| Riesgo | Control |
|---|---|
| Claims NPU no reproducibles | separar prefill/decode y exigir versiones/logs |
| SDK o firmware propietario | registrar disponibilidad, licencia y acceso real |
| Thermal throttling | sesiones largas y temperatura |
| Fragmentación Android | matriz por dispositivo/OS/SoC |
| Benchmarks incomparables | protocolo común y hashes |
| Fuentes sociales anecdóticas | marcar como pistas, no evidencia de ejecución |
| Scraping limitado | registrar errores y respetar términos |

G0 en implementación; G1-G6 pendientes. Solo pruebas físicas con artefactos permiten estado MEASURED.

## Campaña de dispositivo — Xiaomi Mi 9T Pro

Esta campaña concreta el trabajo G1-G3 para la plataforma móvil de referencia, sin alterar la autoridad del INDEX maestro de NEPENTHES.

- [Perfil de hardware](../../../hardware/XIAOMI-MI-9T-PRO-6GB.md)
- [Plan de pruebas y gates](devices/XIAOMI-MI-9T-PRO-TEST-PLAN.md)
- [Matriz de runtimes](devices/XIAOMI-MI-9T-PRO-RUNTIME-MATRIX.md)
- [Protocolo NEPENTHES móvil](devices/XIAOMI-MI-9T-PRO-BENCHMARK-PROTOCOL.md)

Checkpoint: Android/API, ABI, kernel, root y drivers UNKNOWN; almacenamiento libre >30 GB según el usuario. La campaña empieza sin root. No se autoriza modificación de bootloader, ROM, kernel ni firmware. No existen aún resultados físicos medidos. La matriz de rendimiento es una hipótesis de investigación y no un ranking observado.
