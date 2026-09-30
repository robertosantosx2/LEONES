# ramvamp ↔ ODS ↔ LEONES
**Perfil:** runtime Rust CPU-first que ejecuta MoE cuantizados mediante streaming de expertos desde NVMe.
**Estado LEONES:** 🟢 fuente activa · 🟢 candidato prioritario · ⏳ benchmark ODS pendiente.

## 1. Resumen ejecutivo
ramvamp es especialmente relevante para ODS porque elimina la dependencia de GPU. Su diseño mantiene los pesos comunes memory-mapped y empaqueta los expertos en un formato `.rvmp`; sólo los expertos seleccionados por el router se leen desde NVMe mediante io_uring/O_DIRECT y una caché LFU por capa.
El proyecto declara Qwen3-30B-A3B como objetivo funcional actual y proporciona servidor OpenAI-compatible con `/v1/chat/completions`, streaming SSE, `/v1/models` y `/health`.

## 2. Arquitectura
`GGUF → repack .rvmp → common.bin mmap + expertos por capa → router → LFU cache → io_uring/O_DIRECT → CPU kernels`.
No pretende ser un servidor GPU generalista: su ventaja aparece cuando el cuello de botella es RAM.

## 3. Evidencia disponible
El README publica mediciones propias: aproximadamente 2 tok/s de decode para Qwen3-30B-A3B Q4_K_M en un equipo concreto, con 2.5–2.9 GiB de RAM bajo un límite de 3 GiB y un modelo de 17.35 GiB en disco. Estas cifras deben registrarse en LEONES como **reported** hasta reproducirlas.

## 4. Encaje con ODS
Es un candidato interesante para una categoría `cpu-nvme-moe`. Puede exponerse como servicio opcional:
`extensions/services/ramvamp/`.
ODS no debería convertir GGUF durante el arranque; la fase de instalación de LEONES debería realizar el repack y verificar checksum.

## 5. Hardware ODS
El diseño es compatible conceptualmente con el i7-12650H y evita exigir VRAM. El factor crítico será el NVMe y el rendimiento de CPU. Es probablemente más relevante para ODS en equipos sin GPU que para sustituir el llama-server de la RTX 3050.

## 6. Limitaciones
- Linux x86_64.
- Actualmente arquitectura/modelo muy acotados.
- Una petición simultánea no es el objetivo principal.
- Decode es I/O-bound.
- El formato propio añade paso de instalación y gestión de almacenamiento.

## 7. LEONES
Medir: tiempo de repack, tamaño .rvmp, RAM pico, page cache, lectura NVMe, cache hit, TTFT, prefill, decode, contexto y fidelidad frente a llama.cpp. La fidelidad es especialmente importante porque el runtime modifica la ruta de almacenamiento pero debe conservar semántica de los pesos.

## 8. Integración propuesta
Manifest con:
`cpu=true, cuda=false, nvme=true, moe=true, api=openai`.
El selector sólo lo ofrecería cuando haya suficiente almacenamiento y CPU, y cuando el modelo sea compatible.

## 9. Veredicto
| Área | Evaluación |
|---|---|
| CPU-only | 🟢 Excelente |
| Sin GPU | 🟢 |
| MoE grande | 🟢 |
| ODS OpenAI endpoint | 🟢 |
| RTX 3050 | 🟡 No necesaria |
| NVMe | 🟢 Crítico |
| Cobertura de modelos | 🔴 Limitada actualmente |
| Integración LEONES | 🟢 Alta |

**Clasificación:** P1 — candidato prioritario para perfiles CPU/NVMe.
**Fuente:** https://github.com/y0sif/ramvamp