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

### Estado de validación

- **MEASURED:** el repositorio fue descargado y TensorFold reconoció los metadatos.
- **ESTIMATED:** requisito de memoria de 4,85 GiB.
- **PENDIENTE:** cargar el modelo, completar una generación, comprobar estabilidad y medir velocidad/VRAM.
- El requisito estimado supera los 4 GiB de VRAM física. No se debe afirmar que el 4B funciona hasta obtener una ejecución real. El resultado del 2B no prueba que el 4B vaya a caber.
- Antes de la prueba 4B se recomendó parar el servidor 2B para evitar competir por VRAM y empezar con contexto 512, límite de salida 32 y puerto 18084. No se registra aquí como completado porque aún no se ha recibido una salida de ejecución que lo confirme.

## Seguridad y alcance

- Estas pruebas no requieren cambiar la configuración de ODS.
- Los endpoints se ligaron a `127.0.0.1`, no a todas las interfaces de red.
- La prueba de inferencia se hizo en el hardware físico descrito arriba; no es una estimación de FitLLM.
- No se debe borrar la caché de Hugging Face que contiene los pesos 4B.
- Para reproducir la prueba 2B, el modelo y la revisión descritos arriba deben seguir disponibles en la caché local.

## Próximos pasos

1. Arrancar el 4B con el servidor 2B detenido y contexto reducido.
2. Si arranca, probar `/v1/models` y una generación corta con `max_tokens: 32`.
3. Registrar la salida de TensorFold, JSON de generación y `nvidia-smi`.
4. Si hay error de memoria, conservar el error exacto y no elevar los límites a ciegas.
5. Comparar ambos modelos solo con el mismo prompt y límites, y distinguir tiempo hasta primer token, tokens/s, VRAM y estabilidad.
