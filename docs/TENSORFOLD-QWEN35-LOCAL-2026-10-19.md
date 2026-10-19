# TensorFold local: pruebas Qwen3.5 en Ubuntu — 2026-10-19

## Estado

Registro de una prueba física local realizada en el equipo del usuario. Se distinguen explícitamente los resultados **MEASURED** de los datos estimados por TensorFold y de las pruebas aún pendientes.

## Equipo y entorno

- Sistema: Ubuntu, arquitectura `x86_64`.
- CPU: Intel Core i7-12650H.
- RAM: 14 GiB.
- GPU: NVIDIA GeForce RTX 3050 Laptop, 4 GiB VRAM.
- Driver NVIDIA: 580.178.04.
- CUDA que informa `nvidia-smi`: 13.0.
- TensorFold native: 1.1.1, backend CUDA, dispositivo `nvidia-sm86`.
- Directorio de prueba: `~/tensorfold-test/tensorfold-1.1.1-linux-x86_64`.
- Servidor de prueba 2B: `127.0.0.1:18083`.
- ODS no fue modificado durante estas pruebas.

## Prueba A — Qwen3.5-2B-MLX-4bit

### Modelo

- Repositorio: `mlx-community/Qwen3.5-2B-MLX-4bit`.
- Revisión local: `93760be4f1f69842a46bc13dbdc0f19e291392a3`.
- Cuantización: 4 bits, group 64.
- TensorFold lo ejecutó con `--backend cuda`, a pesar de que el nombre del repositorio incluye MLX.

### Configuración usada

Variables:

```bash
export TENSORFOLD_NO_UPDATE_CHECK=1
export TENSORFOLD_CUDA_MEMORY_LIMIT_GB=3.4
export TENSORFOLD_MEMORY_RESERVE_GIB=0.5
export HF_HUB_OFFLINE=1
```

Arranque:

```bash
./bin/tensorfold-native serve \
  "mlx-community/Qwen3.5-2B-MLX-4bit" \
  --backend cuda \
  --host 127.0.0.1 \
  --port 18083 \
  --context 1024 \
  --max-tokens 32 \
  --no-thinking
```

TensorFold confirmó que el servidor estaba activo en `http://127.0.0.1:18083/v1` y que el modelo estaba cargado. La API `/v1/models` respondió correctamente.

### Resultados MEASURED

Primera generación, límite de 32 tokens:

- Resultado: respuesta en español generada correctamente; truncada por el límite de tokens solicitado.
- Velocidad reportada: **95,08 tokens/s**.
- Tiempo hasta el primer token: **88,2 ms**.
- Tiempo de generación reportado: **0,326 s**.
- VRAM observada después de la inferencia: **2.411 MiB / 4.096 MiB** en total.
- Proceso `tensorfold-native`: aproximadamente **2.388 MiB** de VRAM.
- GPU: lectura de 50 °C en la prueba posterior; utilización 100 % en el instante capturado.

Segunda generación, límite de 128 tokens:

- Resultado: generación en español correcta; termina a mitad de una frase por alcanzar `max_tokens: 128`.
- Velocidad reportada: **105,71 tokens/s**.
- Tiempo hasta el primer token: **94,1 ms**.
- Tiempo de generación reportado: **1,201 s**.
- Tokens de salida reportados: **128**.
- VRAM observada: **2.411 MiB / 4.096 MiB**.
- GPU: **100 %** de utilización en la captura de `nvidia-smi`; temperatura **50 °C**.
- La respuesta API informó `finish_reason: "length"`, coherente con el límite impuesto.

Estas cifras son dos observaciones breves, no un benchmark sostenido ni una comparación controlada.

### Conclusión de la prueba A

**MEASURED — OK:** TensorFold 1.1.1 realizó inferencia real por CUDA con Qwen3.5-2B-MLX-4bit en la RTX 3050 Laptop y expuso una API compatible con OpenAI en localhost. En las dos muestras cortas se observó una velocidad de aproximadamente 95–106 tokens/s y uso de VRAM total de unos 2,4 GiB.

## Prueba B — Qwen3.5-4B-MLX-4bit

### Descarga y metadatos

- Repositorio: `mlx-community/Qwen3.5-4B-MLX-4bit`.
- Revisión descargada: `32f3e8ecf65426fc3306969496342d504bfa13f3`.
- Cuantización: 4 bits, group 64.
- Descarga completada correctamente mediante `tensorfold-native pull`.
- Tamaño de pesos informado: **2,85 GiB** (3.061.131.350 bytes).
- Estimación de memoria de `tensorfold-native info`: **4,85 GiB**, calculada como pesos más un margen de ejecución de 2,00 GiB.

### Resultados MEASURED — ejecución CUDA completada

- **MEASURED:** TensorFold 1.1.1 arrancó el modelo 4B en la RTX 3050 Laptop con backend CUDA y sirvió la API en `http://127.0.0.1:18084/v1`.
- Carga del modelo: **6,4 s**.
- Configuración: contexto **512**, `--no-thinking`, generación greedy; puerto local **18084**.
- Registro de arranque: `model 2.75 GiB; 1 stream at once, 0.21 GiB each at a 512-token window; 0.3 GiB left after a 0.5 GiB reserve`. TensorFold mantuvo la caché de prompts de 3,0 GiB en memoria de host, sin staging de dispositivo.
- Primera generación de 64 tokens: **53,64 tokens/s**, TTFT **193 ms**, prefill **190 ms**, generación **1,174 s**; salida en español correcta, limitada por `max_tokens`.
- Segunda generación de 128 tokens: **53,42 tokens/s**, TTFT **212 ms**, prefill **209 ms**, generación **2,377 s**; salida en español estructurada, truncada por `max_tokens`.
- VRAM observada tras la segunda generación: **3.143 MiB / 4.096 MiB** en total; proceso TensorFold **3.120 MiB**; temperatura **43 °C** en la captura.
- `/v1/models` respondió y anunció el modelo `Qwen3.5-4B-MLX-4bit`, contexto máximo servido 512.

### Interpretación

- **MEASURED — OK:** la inferencia 4B sí funciona con CUDA en esta GPU usando la configuración probada.
- La estimación genérica de `tensorfold-native info` (4,85 GiB) no impidió la ejecución con el presupuesto CUDA y la gestión de memoria que aplicó el servidor.
- Comparación preliminar, no controlada: 2B registró 95,08–105,71 tokens/s y 2.411 MiB de VRAM con contexto 1.024; 4B registró 53,42–53,64 tokens/s y 3.143 MiB con contexto 512. Las diferencias de contexto y configuración impiden tratarlo como benchmark perfectamente equivalente.
- No se ha validado todavía una sesión larga ni un contexto mayor para 4B.

## Seguridad y alcance

- Estas pruebas no requieren cambiar la configuración de ODS.
- Los endpoints se ligaron a `127.0.0.1`, no a todas las interfaces de red.
- La prueba de inferencia se hizo en el hardware físico descrito arriba; no es una estimación de FitLLM.
- No se debe borrar la caché de Hugging Face que contiene los pesos 4B.
- Para reproducir la prueba 2B, el modelo y la revisión descritos arriba deben seguir disponibles en la caché local.

## Próximos pasos

1. Probar Qwen3.5-4B en formato GGUF `Q4_K_M` con `llama.cpp` y CUDA, manteniendo TensorFold como referencia.
2. Mantener la prueba aislada en otro puerto localhost; no cambiar ODS ni su `.env`/Compose.
3. Registrar versión/commit de llama.cpp, origen y hash del GGUF, argumentos de compilación/ejecución, contexto, TTFT, tokens/s, VRAM y resultado de generación.
4. Comparar MLX/TensorFold y GGUF/llama.cpp con el mismo prompt, contexto y límites de salida cuando sea posible.
5. No borrar las cachés ni el modelo MLX ya descargado.


### Intento de arranque B1 — presupuesto CUDA insuficiente (2026-10-19)

Comando ejecutado con el servidor 4B, contexto 512 y variables:

```bash
export TENSORFOLD_CUDA_MEMORY_LIMIT_GB=3.4
export TENSORFOLD_MEMORY_RESERVE_GIB=0.5
```

TensorFold respondió:

```text
the checkpoint's 2.8 GiB of weights do not fit the 0.8 GiB the CUDA memory budget grants (1.3 GiB free less a 0.5 GiB reserve, under TENSORFOLD_CUDA_MEMORY_LIMIT_GB)
```

- **MEASURED:** el intento de carga fue rechazado antes de arrancar el servidor.
- TensorFold informó de 1,3 GiB de memoria CUDA libre y un presupuesto utilizable de 0,8 GiB tras aplicar la reserva de 0,5 GiB.
- El presupuesto CUDA estaba limitado además por `TENSORFOLD_CUDA_MEMORY_LIMIT_GB=3.4`.
- **No es una prueba de que el modelo 4B sea incompatible**, ni una prueba de inferencia completada. Indica que el presupuesto disponible en ese momento no alcanza para los pesos.
- **Siguiente diagnóstico:** comprobar `nvidia-smi` y verificar que el proceso del servidor 2B terminó de verdad. No aumentar los límites a ciegas ni arrancar dos modelos simultáneamente.
