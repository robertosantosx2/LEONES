# LOAS — Pila Ubuntu

Ubuntu es una plataforma de ejecución oficialmente contemplada por LOAS junto a Debian. La pila mantiene el mismo protocolo y las mismas métricas: cambiar de distribución no cambia el criterio de evaluación.

## Objetivo

Proporcionar una instalación sencilla para probar LOAS en hardware de consumo:

- 8 / 16 / 32 / 64 GB RAM
- Intel i5/i7 o AMD/ARM equivalente
- CPU solamente o GPU

La referencia inicial sigue siendo:

**Buddy → llama-server → llama.cpp → GGUF**

con LOTB-0:

**Qwen3-8B Q4_K_M**

## 1. Sistema base

Se recomienda una versión Ubuntu LTS de 64 bits actualizada.

```bash
sudo apt update
sudo apt upgrade -y
```

## 2. Dependencias

```bash
sudo apt install -y \
  git \
  build-essential \
  cmake \
  pkg-config \
  python3 \
  python3-venv \
  python3-pip \
  curl \
  wget \
  pciutils \
  procps
```

## 3. Descargar LOAS

```bash
git clone https://github.com/robertosantosx2/LOAS.git
cd LOAS
git rev-parse HEAD
```

El commit debe conservarse en cualquier resultado metaLOAS.

## 4. Compilar llama.cpp — CPU

```bash
git clone https://github.com/ggml-org/llama.cpp.git
cmake -S llama.cpp -B llama.cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build --config Release -j$(nproc)
```

Comprobar:

```bash
./llama.cpp/build/bin/llama-server --help
./llama.cpp/build/bin/llama-bench --help
```

## 5. GPU

La compilación de llama.cpp debe adaptarse a la GPU instalada. No se debe asumir que una configuración CUDA, Vulkan, ROCm, SYCL o Metal es válida para todas las máquinas.

La regla LOAS es registrar en metaLOAS:

- fabricante/modelo de GPU;
- VRAM;
- backend de aceleración;
- opciones de compilación relevantes;
- commit de llama.cpp.

### NVIDIA/CUDA

Si se dispone de una GPU NVIDIA y se desea utilizar CUDA, instalar primero un CUDA Toolkit compatible con la versión de Ubuntu y el driver instalado. Después, recompilar llama.cpp con la opción CUDA correspondiente a la versión de llama.cpp utilizada.

Antes de medir:

```bash
nvidia-smi
```

La salida técnica necesaria debe trasladarse al Markdown metaLOAS sin incluir datos personales.

### GPU sin soporte directo

Si no se utiliza una ruta GPU soportada por la compilación elegida, ejecutar el baseline en CPU. Es preferible una medición CPU reproducible a una configuración GPU no documentada.

## 6. Modelo

Descargar **Qwen3-8B Q4_K_M GGUF** desde su distribución oficial:

https://huggingface.co/Qwen/Qwen3-8B-GGUF

Por ejemplo:

```text
~/models/loas/Qwen3-8B-Q4_K_M.gguf
```

Calcular hash:

```bash
sha256sum ~/models/loas/Qwen3-8B-Q4_K_M.gguf
```

## 7. Detectar hardware

```bash
python3 scripts/loas-hardware-report.py
```

Y capturar la información técnica del sistema:

```bash
scripts/loas-capture-run.sh
```

Revisar siempre los archivos antes de compartirlos.

## 8. Primera medición

Ejecutar primero el benchmark nativo:

```bash
./llama.cpp/build/bin/llama-bench \
  -m ~/models/loas/Qwen3-8B-Q4_K_M.gguf \
  -p 512 \
  -n 256
```

Realizar un warm-up y después tres mediciones.

### Gate LOAS

```text
< 10 tok/s   → no supera el mínimo de usabilidad
>= 10 tok/s  → puede pasar a la fase agentic
100 tok/s    → techo comparativo
```

## 9. llama-server

```bash
./llama.cpp/build/bin/llama-server \
  -m ~/models/loas/Qwen3-8B-Q4_K_M.gguf \
  --host 127.0.0.1 \
  --port 8080 \
  -c 8192
```

Comprobar:

```bash
curl http://127.0.0.1:8080/v1/models
```

Mantener el endpoint en `127.0.0.1` durante las pruebas iniciales.

## 10. Buddy

```bash
git clone https://github.com/juanje/buddy.git
cd buddy
git rev-parse HEAD
```

Configurar Buddy para utilizar el endpoint local OpenAI-compatible de llama-server, según la configuración de la versión de Buddy instalada.

No introducir credenciales privadas en el repositorio LOAS.

## 11. Ejecución agentic

Ejecutar las tareas LOTB:

```text
B01 — memoria/localidad
B02 — operación sobre archivos
B03 — tarea multietapa
B04 — recuperación ante fallo
B05 — coding local
```

Registrar éxito, tiempo, tool calls y errores.

## 12. Ubuntu y metaLOAS

Una máquina Ubuntu puede aportar resultados exactamente igual que una Debian.

El resultado debe indicar:

```text
OS: Ubuntu <versión>
Kernel: <versión>
```

junto con CPU, RAM, GPU/VRAM, backend, commits, modelo, cuantización, SHA-256 y resultados.

No se publican datos personales ni identificadores del equipo que no sean necesarios para reproducir la medición.

## 13. Filosofía

Ubuntu no tiene una métrica distinta de Debian. LOAS compara **hardware + software + modelo + backend + protocolo**, no distribuciones Linux.

Si Ubuntu permite una configuración técnicamente superior en una misma máquina, esa diferencia debe demostrarse mediante medición LOTB/metaLOAS y no asumirse de antemano.
