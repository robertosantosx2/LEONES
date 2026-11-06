# Pithos 0.5.0 + LFM3-1.7B Q4_K_M en RTX 3050 — Ubuntu (2026-11-06)

**Fecha de ejecución:** 6 de noviembre de 2026, aproximadamente 19:10–19:16 (hora local del equipo).  
**Estado:** ejecución local confirmada; servidor Pandora y API verificados; benchmark exploratorio de generación completado.  
**Equipo:** MSI Thin 15 B12UC · Intel Core i7-12650H · NVIDIA RTX 3050 Laptop GPU (4 GiB).  
**Perfil de hardware:** [Ubuntu MSI Thin 15 B12UC](../hardware/UBUNTU-MSI-THIN-15-B12UC.md).

## 1. Resumen ejecutivo

Se compiló Pithos 0.5.0 desde el repositorio oficial, se descargó y verificó el modelo LFM3-1.7B Q4_K_M y se ejecutó mediante Vulkan en la NVIDIA RTX 3050 Laptop.

La prueba larga produjo **4.096 tokens a 87,22 tok/s**, con un prefill reportado de **238,4 tok/s**. Antes de liberar la GPU de TensorFold se había realizado una prueba corta a 101,02 tok/s; no debe mezclarse con la medición larga ni tratarse como una comparación controlada.

El servidor Pandora quedó disponible en `127.0.0.1:18083`; el endpoint `/v1/models` respondió e identificó el modelo. Se detuvo TensorFold antes de la prueba larga. La captura posterior mostró Pithos como único motor de inferencia identificado en ejecución.

## 2. Hardware y entorno observado

| Campo | Valor |
|---|---|
| Sistema | Ubuntu 26.04.1 LTS |
| Kernel | Linux 7.0.0-42-generic |
| CPU | Intel Core i7-12650H |
| CPU lógica | 16 hilos |
| RAM reconocida por Pithos | 14,8 GB |
| GPU | NVIDIA GeForce RTX 3050 Laptop |
| VRAM nominal | 4.096 MiB |
| Driver NVIDIA | 580.178.04 |
| CUDA reportada por NVIDIA | 13.0 |
| Vulkan NVIDIA | 1.4.312 |
| Dispositivo Vulkan seleccionado | índice 1 |
| Motor | Pithos 0.5.0 |

Pithos detectó también la gráfica integrada Intel (Vulkan 1.4.335) y llvmpipe. La selección explícita `--gpu-device 1` corresponde a la RTX 3050 en el listado obtenido durante esta sesión.

## 3. Modelo y artefacto

- Familia: Liquid AI LFM3.
- Modelo: `LFM3-1.7B-Q4_K_M.gguf`.
- Repositorio de origen: `LiquidAI/LFM3-1.7B-GGUF`.
- Revisión descargada: `bad5729bba61d076fff20d2548e62526665af215`.
- Tamaño que informó Pithos: 1,02 GB.
- SHA-256 verificado por el instalador de Pithos: `3793e1e6e2266919d6e015287221b41100175a98eddaba92e111aed3b05c93c4`.
- Arquitectura detectada: LFM3, 24 capas, 11 bloques de atención (5 con ventana deslizante de 256) y 13 bloques convolucionales; dimensión 2048; vocabulario 128.000.

## 4. Compilación e integridad

Comandos utilizados:

```bash
cd ~
git clone https://github.com/benmaster82/Pithos.git
cd ~/Pithos
bash build.sh --test --download-model=lfm3-1.7b
```

Resultado observado:

- Compilación completada en `~/Pithos/build/pithos`.
- Se compilaron los binarios de pruebas de kernels, GPU, Vulkan y shell.
- Las pruebas de shell terminaron con **all passed (0 failed)**.
- El propio script indicó que las pruebas numéricas/GPU no se ejecutaron porque no se había proporcionado el GGUF de referencia durante esa fase de pruebas.
- El descargador verificó el tamaño y SHA-256 del GGUF y declaró el modelo listo.

La detección de la GPU se comprobó con `./build/pithos --list-gpus`. El backend Vulkan enumeró la RTX 3050 con 4.096 MB y el backend OpenCL también enumeró la NVIDIA con 3.768 MB.

## 5. Configuración de inferencia

Backend Vulkan, con el pase completo de inferencia en GPU:

- Pesos asignados a GPU: 1.063 MB.
- Matrices aceleradas: 154.
- Caché KV observada en ejecución CLI: 176 MB.
- Activaciones observadas: 8 MB.
- Pithos informó: `whole forward pass on the GPU`.

Comando de servidor utilizado:

```bash
cd ~/Pithos
./build/pithos \
  -m models/LFM3-1.7B-Q4_K_M.gguf \
  --gpu vulkan \
  --gpu-device 1 \
  --server \
  --host 127.0.0.1 \
  --port 18083
```

Endpoints:

- Pandora: `http://127.0.0.1:18083`.
- API compatible con OpenAI: `http://127.0.0.1:18083/v1`.

La consulta `curl -s http://127.0.0.1:18083/v1/models` devolvió HTTP correctamente y listó el identificador `LFM3-1.7B-Q4_K_M`. Los metadatos de la API indicaron `n_ctx=16384`; la prueba CLI larga reportó un contexto operativo de 8192 tokens. Son observaciones de interfaces/configuraciones distintas y se conservan separadas.

## 6. Resultados medidos

### 6.1. Prueba corta inicial — con TensorFold aún activo

Prompt: «Explica cómo funciona tu arquitectura y tus capacidades.»

| Métrica | Resultado |
|---|---:|
| Tokens de prompt | 21 |
| Tiempo de prompt | 0,15 s |
| Prefill reportado | 141,7 tok/s |
| Tokens generados | 410 |
| Tiempo de generación | 4,06 s |
| Velocidad de generación | 101,02 tok/s |
| Contexto reportado | 431 / 8192 |

Esta prueba se realizó antes de detener TensorFold. La instantánea de `nvidia-smi` de ese momento mostró TensorFold (PID 89997, 1.608 MiB) y Pithos (PID 110314, 1.430 MiB). Por tanto, **no representa una ejecución aislada de Pithos**.

### 6.2. Prueba larga — TensorFold detenido

Prompt: análisis técnico sobre ventajas y limitaciones de los modelos de lenguaje ejecutados localmente en ordenadores portátiles.

| Métrica | Resultado |
|---|---:|
| Tokens de prompt | 38 |
| Tiempo de prompt | 0,16 s |
| Prefill reportado | 238,4 tok/s |
| Tokens generados | 4.096 |
| Tiempo de generación | 46,96 s |
| Velocidad de generación | **87,22 tok/s** |
| Contexto reportado | 4.134 / 8.192 |

La velocidad de generación se mantuvo por encima de 87 tok/s durante una generación de 4.096 tokens. El prefill procede de un prompt corto y no debe extrapolarse a documentos largos.

### 6.3. Comparación descriptiva

La prueba larga registró 87,22 tok/s frente a 101,02 tok/s en la prueba corta. La segunda prueba es más representativa del rendimiento sostenido por su mayor número de tokens. No se trata de una comparación A/B controlada: cambian el prompt, la longitud de salida y la carga concurrente de GPU.

## 7. Aislamiento de GPU y estado de procesos

Antes de detener TensorFold, `nvidia-smi` mostró 3.072 MiB ocupados en total, con 1.608 MiB atribuidos a TensorFold y 1.430 MiB a Pithos.

Se envió `kill -TERM 89997` al proceso TensorFold. Tres segundos después, `nvidia-smi` mostró:

| Proceso | PID | Memoria GPU |
|---|---:|---:|
| Xorg | 6124 | 4 MiB |
| Pithos | 110314 | 1.430 MiB |
| TensorFold | — | ya no aparece |

La salida de `ps` filtrada para `tensorfold-native`, `llama-server`, `ollama` y `pithos` mostró únicamente Pithos. La memoria GPU total reportada fue 1.458 MiB. Esta captura es posterior a la parada de TensorFold; no es una medición de pico durante los 4.096 tokens.

## 8. Reproducción

Para reproducir la prueba larga con el servidor detenido (Ctrl+C en su terminal) y sin otros motores de inferencia activos:

```bash
cd ~/Pithos

./build/pithos \
  -m models/LFM3-1.7B-Q4_K_M.gguf \
  --gpu vulkan \
  --gpu-device 1 \
  -p "Escribe un análisis técnico de las ventajas y limitaciones de los modelos de lenguaje ejecutados localmente en ordenadores portátiles."
```

Registrar la salida completa, versión del binario, estado de procesos y `nvidia-smi` antes/durante/después. Para obtener una estadística robusta se recomienda repetir el mismo prompt varias veces con idénticos límites de generación y condiciones térmicas; este informe no inventa repeticiones que no se realizaron.

## 9. Limitaciones de esta campaña

- Una sola ejecución larga: no permite calcular media, mediana ni desviación entre repeticiones.
- No se capturó telemetría continua de VRAM, potencia, temperatura ni utilización durante la generación larga.
- El prompt de prefill es corto; 238,4 tok/s no caracteriza el prefill de contextos extensos.
- La prueba de 101,02 tok/s se realizó con TensorFold concurrente y se presenta separadamente.
- La suite de pruebas numéricas/GPU de compilación no se ejecutó; solo consta el resultado satisfactorio de las pruebas de shell.
- Se midió throughput, no calidad, exactitud factual ni capacidad de razonamiento del modelo.

## 10. Conclusión

La campaña confirma que Pithos 0.5.0 puede ejecutar LFM3-1.7B Q4_K_M en la RTX 3050 Laptop de 4 GiB mediante Vulkan, con el pase completo en GPU. La medición larga observada fue de **87,22 tok/s durante 4.096 tokens**, con un prefill de 238,4 tok/s para un prompt de 38 tokens.

El resultado es una referencia experimental válida para este equipo y esta configuración, no una clasificación universal de motores ni una comparación de calidad. La siguiente campaña debería repetir la prueba con protocolo fijo y telemetría continua.
