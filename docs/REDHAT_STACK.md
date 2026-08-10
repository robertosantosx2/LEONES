# LOAS — Pila Red Hat

Red Hat se incorpora como plataforma de ejecución contemplada por LOAS junto a Debian y Ubuntu. El protocolo de evaluación es el mismo: LOAS mide la combinación **hardware + sistema + backend + modelo + agente + tareas**, no la distribución por sí sola.

## Plataformas Red Hat

Esta guía está pensada para sistemas compatibles con el ecosistema Red Hat, especialmente:

- Red Hat Enterprise Linux (RHEL)
- Fedora, como entorno de desarrollo cercano al ecosistema Red Hat
- clones/derivados compatibles cuando la instalación de las dependencias sea equivalente

Para resultados metaLOAS debe indicarse exactamente la distribución y versión utilizada.

## Objetivo

Ejecutar la pila de referencia en hardware de consumo:

```text
Buddy
  ↓
llama-server
  ↓
llama.cpp
  ↓
GGUF
  ↓
CPU / GPU
```

Baseline inicial:

**Qwen3-8B Q4_K_M GGUF**

Perfiles:

- H0 — 8 GB
- H1 — 16 GB
- H2 — 32 GB
- H3 — 64 GB

## 1. Actualizar el sistema

En RHEL, utilizar las herramientas de paquetes disponibles en la versión instalada:

```bash
sudo dnf update -y
```

En sistemas Fedora igualmente:

```bash
sudo dnf upgrade -y
```

## 2. Dependencias

```bash
sudo dnf install -y \
  git \
  gcc \
  gcc-c++ \
  make \
  cmake \
  pkg-config \
  python3 \
  python3-pip \
  python3-devel \
  curl \
  wget \
  pciutils \
  procps-ng
```

Si la versión concreta de RHEL no proporciona alguna dependencia con esos nombres, debe utilizarse el repositorio habilitado oficialmente para esa versión o documentarse la alternativa utilizada.

## 3. Descargar LOAS

```bash
git clone https://github.com/robertosantosx2/LOAS.git
cd LOAS
git rev-parse HEAD
```

El commit debe quedar registrado en el resultado metaLOAS.

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

La ruta GPU depende de la tarjeta, driver y backend disponibles. No se debe asumir que una configuración CUDA, Vulkan, ROCm u otra es válida en todas las instalaciones Red Hat.

En metaLOAS registrar:

- GPU y VRAM;
- driver;
- backend;
- opciones relevantes de compilación;
- versión/commit de llama.cpp.

### NVIDIA

Si se utiliza una GPU NVIDIA, instalar un driver y CUDA Toolkit compatibles con la versión concreta de RHEL/Fedora y con la GPU. Después recompilar llama.cpp utilizando el backend CUDA correspondiente a la versión de llama.cpp.

Comprobar:

```bash
nvidia-smi
```

No copiar al repositorio información personal o identificadores innecesarios que puedan aparecer en salidas del sistema.

### CPU como referencia

Si la ruta GPU presenta problemas de compatibilidad, realizar primero la prueba CPU. Una medición CPU reproducible es preferible a una medición GPU que no pueda documentarse.

## 6. Modelo LOTB-0

Descargar:

**Qwen3-8B Q4_K_M GGUF**

Distribución de referencia:

https://huggingface.co/Qwen/Qwen3-8B-GGUF

Por ejemplo:

```text
~/models/loas/Qwen3-8B-Q4_K_M.gguf
```

Calcular SHA-256:

```bash
sha256sum ~/models/loas/Qwen3-8B-Q4_K_M.gguf
```

## 7. Identificar el hardware

```bash
python3 scripts/loas-hardware-report.py
```

Y, cuando proceda:

```bash
scripts/loas-capture-run.sh
```

Revisar siempre cualquier salida antes de compartirla.

## 8. Primera medición

Antes de utilizar Buddy, medir el motor de inferencia directamente:

```bash
./llama.cpp/build/bin/llama-bench \
  -m ~/models/loas/Qwen3-8B-Q4_K_M.gguf \
  -p 512 \
  -n 256
```

Realizar un warm-up y tres mediciones comparables.

### Umbral LOAS

```text
< 10 tok/s   → no supera el mínimo de usabilidad
>= 10 tok/s  → puede pasar a fase agentic
100 tok/s    → techo comparativo
```

## 9. Servidor local

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

Mantener el servidor limitado a `127.0.0.1` durante las pruebas iniciales.

## 10. Buddy

```bash
git clone https://github.com/juanje/buddy.git
cd buddy
git rev-parse HEAD
```

Configurar Buddy para utilizar el endpoint OpenAI-compatible local de `llama-server`, siguiendo la configuración correspondiente a la versión de Buddy utilizada.

No guardar credenciales ni configuraciones privadas dentro del repositorio LOAS.

## 11. LOTB agentic

Ejecutar:

```text
B01 — memoria/localidad
B02 — operación sobre archivos
B03 — tarea multietapa
B04 — recuperación ante fallo
B05 — coding local
```

Registrar éxito, tiempo, tool calls y errores.

## 12. metaLOAS

El resultado debe identificar exactamente el entorno:

```text
OS: RHEL <versión>
Kernel: <versión>
```

o, si procede:

```text
OS: Fedora <versión>
```

Añadir CPU, RAM, GPU/VRAM, backend, commits, modelo, cuantización, SHA-256 y mediciones.

No incluir nombres, emails, cuentas, hostname identificable, números de serie, UUID, MAC/IP, ubicación exacta, rutas personales, credenciales u otros datos personales.

## 13. Comparación con Debian y Ubuntu

No existe una métrica «Red Hat» distinta. Una comparación válida sería, por ejemplo:

```text
mismo hardware
+ mismo modelo
+ misma cuantización
+ mismo commit de llama.cpp
+ mismos parámetros
+ mismo protocolo LOTB
--------------------------------
RHEL vs Ubuntu vs Debian
```

Cualquier diferencia debe medirse y documentarse.

## 14. Nota sobre soporte y reproducibilidad

RHEL puede introducir diferencias prácticas por versión, repositorios habilitados, toolchain, drivers y políticas del sistema. Por eso metaLOAS exige registrar la versión exacta del sistema y de los componentes críticos.

La prioridad es **reproducibilidad**, no asumir que todas las versiones de RHEL/Fedora se comportan igual.
