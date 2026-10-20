# Prueba local: Qwen3.5-4B GGUF con llama.cpp y RTX 3050

**Fecha:** 2026-10-20  
**Estado:** prueba de inferencia local completada; servidor HTTP e integración con otros componentes pendientes.

## Entorno

- Sistema: Ubuntu, ejecución nativa.
- Proyecto: `~/llama.cpp-cuda`.
- Binario: `build-cuda/bin/llama-cli`.
- GPU: NVIDIA GeForce RTX 3050 Laptop, 4 GiB de VRAM.
- Driver NVIDIA: `580.178.04`.
- CUDA indicada por `nvidia-smi`: `13.0`.
- Build de llama.cpp: `b11740-6fa4f6cd3`.

## Modelo y verificación

- Identificador usado: Qwen3.5-4B GGUF.
- Archivo local: `~/llama.cpp-cuda/models/qwen3.5-4b-Q4_K_M.gguf`.
- Tamaño descargado: aproximadamente 2,59 GiB.
- Cuantización detectada por llama.cpp: `Q4_K - Medium`.
- SHA-256 esperado y obtenido: `c3c2cf023efdbd913c2363a14d5c7266db5e05c4602f1c0790eaed567d8aff23`.
- La descarga y la comprobación SHA-256 finalizaron correctamente.

## Comando ejecutado

```bash
cd ~/llama.cpp-cuda

./build-cuda/bin/llama-cli \
  -m "$PWD/models/qwen3.5-4b-Q4_K_M.gguf" \
  -ngl 99 \
  -c 512 \
  -n 128 \
  --temp 0 \
  --no-display-prompt \
  -p "Responde en español en una frase: ¿qué ventajas tiene ejecutar un modelo de IA localmente?" \
  --chat-template-kwargs '{"enable_thinking":false}'
```

El modelo respondió de forma coherente en español. Métricas que mostró esa ejecución:

- Procesamiento del prompt: **141,2 tokens/s**.
- Generación: **42,4 tokens/s**.
- Contexto configurado: **512 tokens**.
- Generación máxima solicitada: **128 tokens**.

Las velocidades son las informadas por esa ejecución concreta, no un benchmark repetido.

## Evidencia de uso de GPU

Salida de `nvidia-smi` tomada el 2026-10-20 a las 17:49:12:

- VRAM total: 4096 MiB.
- VRAM ocupada: 2831 MiB.
- Proceso `./build-cuda/bin/llama-cli`: 2808 MiB de VRAM.
- Temperatura: 42 °C.
- Utilización instantánea: 0 % en el momento de la captura, posterior a la generación.

La memoria asociada al proceso y la opción `-ngl 99` son evidencia de que se usó la GPU; la captura se tomó en reposo y no mide utilización durante la generación.

## Conclusiones

1. El archivo GGUF se descargó y su SHA-256 coincidió con el valor esperado.
2. `llama-cli` cargó el modelo y produjo una respuesta válida en español.
3. La ejecución utilizó memoria de la RTX 3050 Laptop.
4. La prueba confirma inferencia local con llama.cpp y CUDA; **no** confirma todavía integración con Magnitude, TensorFold, ODS ni LEONES Runtime.

## Siguientes pruebas pendientes

- Repetir la prueba con un protocolo de benchmark consistente.
- Probar `llama-server` en un puerto libre y verificar `/health` y `/v1/chat/completions`.
- Medir VRAM y utilización durante generación, además de latencia y longitud de contexto.
- Mantener la prueba aislada: no modificar el servidor llama.cpp activo ni la configuración de ODS.
- Evaluar por separado el acceso desde Magnitude y la posible integración con ODS/LEONES; no darla por implementada hasta superar pruebas específicas.
