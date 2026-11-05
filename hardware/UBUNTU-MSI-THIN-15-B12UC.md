# Perfil del equipo de pruebas Ubuntu — MSI Thin 15 B12UC

> Perfil recopilado de salidas reales compartidas por el usuario durante octubre–noviembre de 2026. No es un inventario en tiempo real. Los valores que pueden cambiar (kernel, driver, memoria libre, procesos y espacio disponible) deben volver a medirse antes de cada benchmark.

## Identificación

| Campo | Dato registrado |
|---|---|
| Sistema operativo | Ubuntu (distribución solicitada para toda la documentación LEONES; no sustituir por Debian) |
| Equipo | MSI Thin 15 B12UC |
| CPU | Intel Core i7-12650H |
| CPU lógica | 16 hilos lógicos reportados |
| GPU | NVIDIA GeForce RTX 3050 Laptop GPU |
| VRAM | 4 GiB (4096 MiB nominales) |
| Driver NVIDIA | 580.178.04 |
| CUDA reportada por NVIDIA | 13.0 |
| Kernel observado en un registro anterior | 7.0.0-38-generic |
| RAM total observada por `free -h` | 14 GiB |
| Swap | `/swap32.img`, 32 GiB |
| Disco raíz observado en un registro anterior | 937 GiB total, aproximadamente 674 GiB libres |

### Nota de consistencia de memoria

Los registros de memoria no son completamente coincidentes: `free -h` informó 14 GiB de RAM total, mientras que una salida de `dmidecode` mostró un módulo DDR4-3200 SODIMM de 8 GB y una capacidad máxima de 64 GB con dos ranuras. Conservar ambas observaciones con su procedencia; no inferir que una sustituye a la otra. Se necesita una nueva captura de `free -h`, `sudo dmidecode -t memory` y `sudo lshw -class memory` para resolver la discrepancia.

## Memoria física observada

- Un módulo detectado por `dmidecode`: 8 GB DDR4-3200 SODIMM (Controller0-ChannelA-DIMM0).
- Capacidad máxima indicada por SMBIOS: 64 GB.
- Dos ranuras indicadas por SMBIOS.
- En una prueba LFM3 anterior se observó presión de memoria: aproximadamente 8,9 GiB usados, 253 MiB libres y 2,0 GiB de swap usados. Es una muestra histórica, no el estado actual.

## GPU y CUDA

- NVIDIA RTX 3050 Laptop GPU, arquitectura Ampere (SM 8.6).
- 4096 MiB VRAM nominal.
- Driver 580.178.04; CUDA 13.0 reportada por `nvidia-smi`.
- En muestras anteriores en reposo se observaron temperaturas de 32–41 °C y consumos aproximados de 3–5,74 W; dependen del estado de la máquina.
- No se dispone de `nvcc` en PATH en los registros disponibles.
- Existe una compilación local CUDA de llama.cpp; no confundirla con el paquete Debian CPU-only.

## Software local relevante para inferencia

### llama.cpp

- Compilación CUDA local: `$HOME/llama-cpp-cuda/build/bin/llama-cli` (también se registró otra ruta de build en `build-cuda/bin`).
- Versión observada: `0.8.0-dev`, build 1, commit `c3df4b7`.
- Se instalaron enlaces en `/usr/local/bin/llama-cli` y `/usr/local/bin/llama-server` para priorizar la compilación CUDA local sobre los binarios Debian CPU.
- No asumir que `nvcc` está instalado solo porque llama.cpp tenga backend CUDA.

### TensorFold

- TensorFold 1.2.0 instalado en `~/.local/opt/tensorfold-1.2.0-linux-x86_64`.
- Binario: `tensorfold-native`.
- CUDA detectada, chip `nvidia-sm86`, sin NCCL.
- Capacidades observadas: Qwen3.5 con `mlx-q4g64` y `exl3`; Qwen3.5 MoE con `mlx-q4g64`, `modelopt-mixed` y `modelopt-nvfp4`; soporte añadido para Qwen4/Qwen4_text.
- TensorFold no ofrece soporte para la arquitectura Granite usada por TwIL-8B; no utilizarlo como backend de ese benchmark.

### Otros componentes observados

- OpenDcoder 0.5B en entorno Python 3.12, PyTorch 2.11.0+cu128; prueba anterior: aproximadamente 1,184 GiB VRAM y 140 posiciones/s a 16 pasos.
- Magnitude 0.2.15; servicio observado en puerto 10100.
- Hermes local v0.22.2; se estaba configurando Qwen3.5-4B con proveedor local y fallback Gemini.
- ODS 3.0.0 local; el usuario pidió no alterar el servicio llama-server por defecto ni servicios ODS/Hermes sin autorización.
- Servicios ODS observados: Hermes, LiteLLM, n8n, Open WebUI, Qdrant, SearXNG y TTS.

## Rutas de trabajo observadas

- Repositorio LEONES de trabajo: `~/leones-work/LEONES`.
- Repositorio ODS: `~/ods-git`; también existían instalaciones/rutas antiguas `~/ods` y `~/ODS/ODS`.
- llama.cpp CUDA: `~/llama-cpp-cuda`.
- Benchmarks TwIL-8B: `~/benchmarks/twil-8b-20261104`.
- Modelos locales: `~/models`.
- TensorFold 1.2.0: `~/.local/opt/tensorfold-1.2.0-linux-x86_64`.

Las rutas son referencias locales del entorno y no deben convertirse en rutas universales para otros usuarios.

## Reglas de reproducción y seguridad operativa

1. Ejecutar y registrar los comandos de inventario en Ubuntu antes de cada campaña.
2. Registrar fecha, kernel, driver, CUDA, RAM libre, swap, VRAM libre, procesos concurrentes y límites de potencia/temperatura.
3. Distinguir especificaciones declaradas de medidas reales.
4. No iniciar o detener servicios ODS/Hermes/llama-server ni reemplazar el runtime predeterminado sin autorización explícita.
5. No publicar hostname, número de serie, UUID, MAC/IP, tokens, credenciales ni rutas privadas innecesarias.
6. Los datos aquí descritos son un perfil del equipo de pruebas, no una plantilla de requisitos mínimos LEONES.
