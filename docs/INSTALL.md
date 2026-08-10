# LOAS — Manual breve de instalación y ejecución

Este manual explica cómo bajar LOAS desde GitHub y realizar la primera prueba local. Está pensado para Debian/Linux y hardware de consumo.

> **Importante:** LOAS está en desarrollo. La primera prueba recomendada es LOTB-0: Qwen3-8B Q4_K_M + llama.cpp, primero sin agente y después con Buddy.

## 1. Requisitos

Perfil recomendado para empezar: **H1 — 16 GB RAM**, CPU Intel i5/i7 o equivalente. Puede haber GPU o no.

Necesitas:

- Debian/Linux actualizado.
- Git.
- Python 3.
- compilador C/C++ y herramientas de construcción.
- suficiente espacio para el modelo GGUF.
- opcionalmente una GPU compatible con la configuración de llama.cpp.

## 2. Descargar LOAS

```bash
git clone https://github.com/robertosantosx2/LOAS.git
cd LOAS
```

Para guardar la versión que hayas probado, después de clonar:

```bash
git rev-parse HEAD
```

Guarda ese commit en el resultado metaLOAS.

## 3. Preparar el entorno

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip build-essential cmake
```

Crear un entorno Python si se necesita:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 4. Compilar llama.cpp

LOAS utiliza `llama.cpp` como backend inicial de referencia.

```bash
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
cmake -B build
cmake --build build --config Release -j$(nproc)
cd ..
```

El ejecutable del servidor suele quedar en `llama.cpp/build/bin/llama-server` y `llama-bench` en el mismo directorio de binarios.

Comprueba:

```bash
./llama.cpp/build/bin/llama-server --help
./llama.cpp/build/bin/llama-bench --help
```

## 5. Obtener LOTB-0

Baseline inicial:

**Qwen3-8B — Q4_K_M — GGUF**

Repositorio de referencia:

https://huggingface.co/Qwen/Qwen3-8B-GGUF

Puedes descargar el GGUF con Hugging Face CLI (`hf`/`huggingface-cli`) o mediante el método de descarga que prefieras.

Guárdalo, por ejemplo, en:

```text
~/models/loas/Qwen3-8B-Q4_K_M.gguf
```

Calcula y conserva su hash:

```bash
sha256sum ~/models/loas/Qwen3-8B-Q4_K_M.gguf
```

El SHA-256 debe acompañar a todo resultado reproducible.

## 6. Primera prueba: inferencia sin agente

Primero debemos saber qué puede hacer la máquina por sí sola.

Ejemplo:

```bash
./llama.cpp/build/bin/llama-bench \
  -m ~/models/loas/Qwen3-8B-Q4_K_M.gguf \
  -p 512 \
  -n 256
```

Haz un warm-up y después **tres mediciones**. Conserva la salida.

También puedes capturar la información del hardware:

```bash
python3 scripts/loas-hardware-report.py
```

Y registrar una instantánea del sistema:

```bash
scripts/loas-capture-run.sh
```

### Criterio inicial

- **< 10 tok/s:** la configuración no supera el umbral de usabilidad LOAS.
- **≥ 10 tok/s:** puede pasar a la fase agentic.
- **100 tok/s:** es el techo utilizado para comparativas, no un requisito.

## 7. Levantar el servidor local

```bash
./llama.cpp/build/bin/llama-server \
  -m ~/models/loas/Qwen3-8B-Q4_K_M.gguf \
  --host 127.0.0.1 \
  --port 8080 \
  -c 8192
```

La API local queda en `http://127.0.0.1:8080`.

Comprueba que responde:

```bash
curl http://127.0.0.1:8080/v1/models
```

**No expongas el servidor a Internet** durante estas primeras pruebas.

## 8. Conectar Buddy

Buddy es la pieza agéntica central de la configuración actual.

Repositorio:

https://github.com/juanje/buddy

Clónalo aparte:

```bash
git clone https://github.com/juanje/buddy.git
cd buddy
git rev-parse HEAD
```

Conserva el commit exacto utilizado.

La configuración de Buddy debe apuntar al endpoint OpenAI-compatible local de llama-server (`127.0.0.1:8080`) según la configuración admitida por la versión de Buddy instalada.

> No copies credenciales ni configuraciones privadas al repositorio LOAS.

## 9. Ejecutar LOTB agentic

Una vez conectado Buddy al modelo local, ejecuta las cinco tareas estándar:

```text
B01 — memoria/localidad
B02 — operación sobre archivos
B03 — tarea multietapa
B04 — recuperación ante fallo
B05 — coding local
```

Registra para cada tarea:

- éxito/fallo;
- tiempo;
- tool calls;
- errores;
- generación tok/s cuando esté disponible;
- observaciones.

La velocidad y la capacidad de completar la tarea son métricas diferentes.

## 10. Crear una contribución metaLOAS

Cuando hayas terminado, utiliza la plantilla:

```text
templates/metaLOAS-result.md
```

También puedes crear una plantilla limpia con:

```bash
scripts/metaloas-sanitize.sh results/metaLOAS/H1/ML-H1-QWEN3-8B-Q4KM-001.md
```

Revisa manualmente el fichero antes de publicarlo.

### Nunca incluyas

- nombre;
- email;
- usuario del sistema;
- hostname identificable;
- número de serie;
- UUID;
- MAC/IP;
- ubicación exacta;
- rutas personales;
- credenciales o tokens.

El resultado identifica el **experimento**, no a la persona.

## 11. Aportarlo al proyecto

La contribución recomendada es mediante Pull Request:

```text
results/
└── metaLOAS/
    └── H1/
        └── ML-H1-QWEN3-8B-Q4KM-001.md
```

No subas modelos GGUF, logs crudos ni datos personales.

## 12. Qué guardar para reproducibilidad

Cada resultado debe conservar, como mínimo:

- perfil H0/H1/H2/H3;
- CPU/RAM/GPU/VRAM;
- sistema operativo/kernel;
- commit de LOAS;
- commit de llama.cpp;
- commit de Buddy;
- modelo;
- cuantización;
- SHA-256 del modelo;
- parámetros del benchmark;
- tres mediciones después del warm-up;
- B01-B05;
- veredicto RULA/PRODUCTIVO.

## 13. Ruta rápida

Para una primera prueba H1:

```bash
git clone https://github.com/robertosantosx2/LOAS.git
cd LOAS
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip build-essential cmake
git clone https://github.com/ggml-org/llama.cpp.git
cmake -B llama.cpp/build llama.cpp
cmake --build llama.cpp/build --config Release -j$(nproc)
python3 scripts/loas-hardware-report.py
```

Después descarga **Qwen3-8B Q4_K_M**, calcula su SHA-256, ejecuta `llama-bench`, y solo si la máquina resulta adecuada pasa a `llama-server` y Buddy.

## 14. Filosofía de la primera ejecución

No intentes optimizar todo a la vez.

La secuencia correcta es:

**hardware → inferencia → servidor → agente → tareas → resultado metaLOAS**

Así podemos saber exactamente dónde está el límite de una configuración y comparar posteriormente otros modelos y backends como AirLLM, WASTE o KTransformers sin perder la trazabilidad.
