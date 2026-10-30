# LFM3-1.7B Uncensored GGUF — pruebas en Ubuntu

**Fecha:** 2026-10-30  
**Estado:** ejecución confirmada; evaluación preliminar, no benchmark exhaustivo.  
**Repositorio del modelo:** https://huggingface.co/AtomicChat/LFM3-1.7B-Uncensored-GGUF

## 1. Equipo y entorno

| Elemento | Dato |
|---|---|
| Sistema | Ubuntu (equipo local) |
| Equipo | MSI Thin 15 B12UC |
| CPU | Intel Core i7-12650H |
| RAM del sistema | 14,8 GiB |
| GPU | NVIDIA GeForce RTX 3050 Laptop GPU |
| VRAM física | 4 GiB |
| VRAM detectada por llama.cpp | 3768 MiB |
| Driver NVIDIA | 580.178.04 |
| CUDA indicada por nvidia-smi | 13.0 |
| llama.cpp | 0.8.0-dev, build 1 |
| Commit llama.cpp | c3df4b7 |
| Ejecutable | ~/llama-cpp-cuda/build/bin/llama-cli |
| Backend | CUDA |
| CPU threads | 6 |

La salida de `nvidia-smi` tomada antes de la prueba mostró 18 MiB de memoria GPU ocupada (4 MiB atribuidos a Xorg), 42 °C y 3 W. Es una captura en reposo, no una medición durante la inferencia.

## 2. Modelo y artefacto

| Campo | Resultado |
|---|---|
| Repositorio | `AtomicChat/LFM3-1.7B-Uncensored-GGUF` |
| Variante | `AD-Q4_K_M` |
| Archivo descargado | `LFM3-1.7B-Uncensored-AD-Q4_K_M.gguf` |
| Tamaño reportado por llama-bench | 1,05 GiB |
| Parámetros | 1,73 B |
| Tipo | Q4_K - Medium |
| Modalidad reconocida | text |

El archivo se descargó correctamente desde Hugging Face durante la ejecución de `llama-bench`.

## 3. Benchmark sintético con llama-bench

Comando ejecutado:

```bash
BIN="$HOME/llama-cpp-cuda/build/bin/llama-bench"

"$BIN" \
  -hf "AtomicChat/LFM3-1.7B-Uncensored-GGUF:AD-Q4_K_M" \
  -ngl 99 \
  -t 6 \
  -p 512 \
  -n 128 \
  -r 3 \
  -o md
```

Resultados observados:

| Prueba | Resultado |
|---|---:|
| Prompt processing, pp512 | 4326,68 ± 254,02 tok/s |
| Text generation, tg128 | 117,29 ± 0,27 tok/s |
| Backend | CUDA |
| Capas solicitadas en GPU | 99 |

La tabla identifica el backend como CUDA. El valor `-ngl 99` solicita el offload de todas las capas posibles; no se conserva en esta sesión un desglose de capas efectivamente descargadas ni una captura de VRAM durante la carga.

## 4. Prueba interactiva con llama-cli

Comando ejecutado:

```bash
BIN="$HOME/llama-cpp-cuda/build/bin/llama-cli"
LOG="$HOME/lfm3-1.7b-uncensored-test.log"

"$BIN" \
  -hf "AtomicChat/LFM3-1.7B-Uncensored-GGUF:AD-Q4_K_M" \
  -ngl 99 \
  -c 2048 \
  -t 6 \
  -n 256 \
  --temp 0.1 \
  --top-k 50 \
  --repeat-penalty 1.1 \
  -p "Explain how mixture-of-experts language models work, including routing, expert activation and memory requirements." \
  2>&1 | tee "$LOG"
```

Métricas comunicadas por la interfaz de llama-cli:

| Interacción | Prompt processing | Generation |
|---|---:|---:|
| Primera respuesta | 163,5 tok/s | 99,8 tok/s |
| Segunda respuesta | 1749,2 tok/s | 104,4 tok/s |
| Tercera respuesta | 1797,1 tok/s | 104,3 tok/s |

Son cifras mostradas por el propio CLI para esas interacciones; no equivalen a una repetición controlada de llama-bench. El procesamiento de prompts posteriores puede beneficiarse del contexto ya procesado y no debe compararse directamente con pp512.

## 5. Observaciones cualitativas

Durante la sesión se probaron:
- Explicación en inglés de conceptos MoE (enrutamiento, activación de expertos y memoria).
- Pregunta de conocimiento general sobre el Arco de Triunfo de Trajano.
- Petición de responder en español.

Observaciones:
- El modelo mostró el marcador `[Start thinking]` en la salida visible.
- En la consulta geográfica produjo una respuesta vacilante, con ubicaciones contradictorias y sin una localización fiable.
- La transcripción disponible no permite certificar una respuesta factual correcta a esa consulta.
- Estas interacciones son observaciones exploratorias, no una evaluación normalizada de calidad.

## 6. Resumen

| Indicador | Resultado |
|---|---:|
| Benchmark sintético generación | **117,29 tok/s** |
| Generación interactiva observada | **99,8–104,4 tok/s** |
| Benchmark sintético prefill | **4326,68 tok/s** |
| Prefill interactivo mostrado | **163,5–1797,1 tok/s** |
| Tamaño GGUF | **1,05 GiB** |
| GPU/backend | **RTX 3050 Laptop / CUDA** |
| Ejecución | **Confirmada** |

## 7. Límites y trabajo pendiente

No se midieron todavía:
- Pico de VRAM durante carga y generación.
- RAM máxima del proceso.
- Temperatura, potencia y frecuencia de GPU bajo carga.
- TTFT medido con metodología independiente.
- Calidad mediante un benchmark normalizado (por ejemplo, tareas de razonamiento, conocimiento, español y código).
- Comparación Q4_K_M frente a Q6_K.
- Servicio persistente mediante `llama-server`, concurrencia y latencia multiusuario.

**Conclusión:** LFM3-1.7B Uncensored Q4_K_M queda ejecutado y reconocido por llama.cpp CUDA en la RTX 3050 Laptop. La cifra sintética registrada es 117,29 tok/s y la generación interactiva observada ronda 100–104 tok/s. La calidad factual necesita evaluación adicional antes de extraer conclusiones generales.

## 8. Referencias

- Modelo: https://huggingface.co/AtomicChat/LFM3-1.7B-Uncensored-GGUF
- llama.cpp: https://github.com/ggml-org/llama.cpp
