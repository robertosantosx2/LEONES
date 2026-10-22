# llama-quik: experimento de caché/paginación de expertos MoE — informe de cierre

**Fecha:** 2026-10-22  
**Estado:** detenido por fallo CUDA; no apto para uso  
**Clasificación de evidencia:** ejecución física local observada en el equipo del operador; no es benchmark validado ni resultado de producción  
**Equipo:** Ubuntu, Intel Core i7-12650H, ~14 GiB RAM, NVIDIA RTX 3050 Laptop (4 GiB VRAM, SM 8.6), driver 580.178.04, CUDA Toolkit 13.4.92  
**Repositorio experimental:** [C5Hackr/llama-quik](https://github.com/C5Hackr/llama-quik)  
**Ruta local:** `~/llama-quik`  
**Modelo:** `Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf`  
**Ruta del modelo:** `~/benchmarks/qwen3.5-35b-a3b-iq2-xxs/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf`

## Resumen ejecutivo

Se compiló correctamente el fork `llama-quik` con CUDA 13.4.92 para `sm_86` (ggml 0.15.2, commit indicado por la compilación: `c12cf47`). El servidor cargó el modelo MoE de 35B-A3B y arrancó en `127.0.0.1:18083`.

La inferencia inicial con el pager respondió HTTP 200, pero la respuesta no satisfizo el prompt porque el límite de tokens se consumió en `reasoning_content` y el campo `content` quedó vacío. En una segunda petición, cuando el profiler alcanzó aproximadamente 47.680 accesos, el código activó la reserva de slots de expertos GPU y el proceso terminó con `CUDA error: an illegal memory access was encountered`.

**Conclusión:** detener el uso del backend GPU de promoción JIT de expertos. No se identificó la causa raíz y no se debe afirmar que el fallo se deba a un único defecto confirmado. No se justifica seguir depurando hasta que exista una hipótesis concreta y una mejora esperada medible frente a `llama.cpp` estable.

## Hardware y compilación

- GPU: NVIDIA RTX 3050 Laptop, 4 GiB VRAM, arquitectura SM 8.6.
- Driver NVIDIA: 580.178.04; `nvidia-smi` mostraba CUDA 13.0.
- Toolkit utilizado en la compilación: CUDA 13.4.92, `/usr/local/cuda-13.4`.
- Compilación CUDA completada; binario del servidor: `~/llama-quik/build-cuda/bin/llama-server`.
- RAM del host: aproximadamente 14 GiB. Durante la carga se observó presión de memoria y uso de swap.

## Configuración del servidor

El servidor se inició en segundo plano con esta configuración:

```bash
BIN="$HOME/llama-quik/build-cuda/bin/llama-server"
MODEL="$HOME/benchmarks/qwen3.5-35b-a3b-iq2-xxs/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf"
DIR="$HOME/benchmarks/qwen3.5-35b-a3b-iq2-xxs"

nohup "$BIN" \
  --model "$MODEL" \
  --host 127.0.0.1 \
  --port 18083 \
  --ctx-size 512 \
  --n-gpu-layers 99 \
  --fit off \
  --threads 4 \
  --moe-expert-pager \
  --moe-expert-log \
  --moe-expert-trace \
  --moe-expert-cache-vram-mib 1024 \
  --moe-expert-vram-reserve-mib 512 \
  > "$DIR/llama-quik-moe-pager-background.log" 2>&1 &
```

PID observado al arrancar: `203190`. El proceso terminó por el fallo CUDA; no debe suponerse que el PID siga activo.

### Opciones del pager identificadas

- `--moe-expert-pager`: activa el modo pager/control plane y el fallback MoE a CPU.
- `--moe-expert-pager-no-auto-tune`: desactiva el auto-tuning.
- `--moe-expert-whole-layer-cache`: modo de caché por capa completa.
- `--moe-expert-cache-experts N`: slots/expertos cacheados; el valor automático documentado era 64.
- `--moe-expert-prefetch N`: prefetch del control plane.
- `--moe-expert-cache-policy POLICY`: políticas LRU/LFU/LFRU del control plane.
- `--moe-expert-cache-vram-mib N`: presupuesto de caché GPU.
- `--moe-expert-vram-reserve-mib N`: reserva de VRAM; valor predeterminado documentado 512 MiB.
- `--moe-expert-vram-max-mib N`: límite máximo de VRAM, 0 en la configuración observada.
- `--moe-expert-log`, `--moe-expert-trace`, `--moe-expert-log-every N`: diagnóstico.
- `--moe-expert-pinned-cpu`: opción del control plane.

## Peticiones y resultados

### Primera petición: respuesta HTTP válida, resultado semántico incompleto

Petición a `/v1/chat/completions`:

```json
{
  "messages": [
    {"role": "user", "content": "Responde exactamente: MOE PAGER OK"}
  ],
  "max_tokens": 32,
  "temperature": 0,
  "stream": false
}
```

Resultado observado:
- HTTP 200.
- Tiempo total: 7,283 s.
- Prompt: 19 tokens, 14,25 tok/s.
- Generación: 32 tokens, 5,51 tok/s.
- `content` vacío; `reasoning_content` consumió el límite de tokens.

**Interpretación:** no cuenta como respuesta correcta ni como benchmark de calidad. El dato de 5,51 tok/s es solo la tasa de esa ejecución limitada y no demuestra que el pager sea mejor que el baseline.

### Estado del profiler antes del crash

Configuración registrada por los logs:
- `cache_experts=64`, `prefetch=8`, `policy=lfru`.
- `hard_backend=true`, `auto_tune=true`.
- `cache_vram_mib=1024`, `vram_reserve_mib=512`, `vram_max_mib=0`.
- `auto_profile=true`, `target_accesses=50000`.
- Reserva de arena CUDA0: 1.024 MiB.

Informes del profiler:
- `ready=false`, `decode_calls=3`, `accesses=7360`, `selected_cache=64/64`, `selected_hit_rate=6.41%`, `cached_tensors=0`, `cached_layers=0`, backend `gpu-cache-arena-reserved(cpu-moe-fallback)`.
- Más adelante: `decode_calls=19`, `accesses=12480`, `selected_hit_rate=5.67%`, todavía `ready=false` y sin tensores/capas cacheados.
- Durante la segunda petición, el contador avanzó por 27.200, 32.320, 37.440, 42.560 y 47.680 accesos; el profiler continuaba informando `ready=false` y `cached_tensors=0`, `cached_layers=0`.

### Segunda petición: fallo del proceso

La segunda llamada HTTP, con `chat_template_kwargs: {"enable_thinking": false}` y `max_tokens: 96`, terminó con:
- `curl: (52) Empty reply from server`.
- `HTTP_STATUS=000`.
- Tiempo total: 75,647548 s.
- Log inmediatamente anterior al error: `allocated 48 per-expert slot tensors across 16 hot layers on CUDA0 (802.00 MiB, 64 slots/tensor)`.
- Error: `CUDA error: an illegal memory access was encountered`, reportado desde `ggml/src/ggml-cuda/ggml-cuda.cu:105` a través del manejador de errores CUDA.
- El proceso servidor desapareció. Después del fallo no aparecía como proceso activo en `nvidia-smi`; la memoria disponible del host se recuperó a aproximadamente 3,1 GiB.

La línea 105 es el punto de reporte del error CUDA y no demuestra necesariamente que el acceso inválido se originase en esa línea: los errores CUDA asíncronos pueden manifestarse en una llamada posterior.

## Lectura técnica del código inspeccionado

### Diseño

El modo experimental crea tensores sintéticos de slot-cache con el eje de expertos reducido a `n_slots`. El metadato asocia el tensor GPU de slots con el tensor original CPU y mantiene:
- `n_experts = src->ne[2]`;
- `n_slots = min(requested_slots, n_experts)`;
- `cpu_expert_stride_bytes = src->nb[2]`;
- `gpu_slot_stride_bytes = dst->nb[2]`;
- `copy_bytes = min(cpu_expert_stride_bytes, gpu_slot_stride_bytes)`.

En `ggml_cuda_moe_mul_mat_id_slot_cache`, el código copia los IDs desde GPU a host, selecciona slots, copia el experto elegido con `cudaMemcpyAsync(..., cudaMemcpyHostToDevice, ...)`, remapea los IDs a slots y despacha el `mul_mat_id` CUDA normal.

### Riesgos por investigar si se retoma

Son hipótesis, no causas confirmadas:

1. **Memoria de origen de la copia:** el código usa `meta->cpu_tensor->data` directamente como origen de `cudaMemcpyHostToDevice`. Debe verificarse que el buffer sea realmente host-accessible y que esa ruta sea válida para el backend asignado.
2. **Strides y tamaño de copia:** usar `min(src->nb[2], dst->nb[2])` puede ocultar una discrepancia y truncar datos. Aún no se han comparado los strides reales de todos los tensores afectados.
3. **Vida útil de la memoria temporal:** `slot_ids_dev` se reserva mediante `ggml_cuda_pool_alloc`; hay que comprobar si su asignación puede volver al pool antes de que terminen los kernels asíncronos que la consumen.
4. **Coherencia del remapeo y expulsión:** verificar que ningún experto necesario en la misma operación se expulse antes de usar los IDs remapeados, y que el número de IDs únicos no exceda los slots disponibles.
5. **Layout del tensor:** `ids_slot` hereda la forma/strides del tensor original y cambia su puntero de datos. Debe validarse que el layout remapeado concuerde con el tensor de slot-cache y con las expectativas del kernel.
6. **Sincronización y reporte asíncrono:** determinar qué operación origina el acceso inválido, no inferirlo solo de la ubicación donde CUDA notifica el error.

API relevante inspeccionada: `ggml_backend_tensor_get()` delega la lectura al `get_tensor` del buffer backend, después de comprobar que el tensor y el rango sean válidos. Podría servir para leer el origen mediante el backend, con staging host y manejo correcto de offsets, si se decide continuar.

## Archivos de logs y resultados locales

En `~/benchmarks/qwen3.5-35b-a3b-iq2-xxs/`:
- `llama-quik-moe-pager-background.log`
- `llama-quik-moe-pager-generation.json`
- `llama-quik-moe-pager-generation-2.json`
- `llama-quik-moe-pager.pid`

La presencia actual de esos ficheros no se ha vuelto a comprobar al escribir este informe.

## Decisión y criterios de reapertura

**Decisión actual: PAUSAR.** No ejecutar de nuevo la configuración de promoción GPU con `--moe-expert-pager` y backend duro activado hasta que se instrumente o corrija una hipótesis verificable.

Reabrir solo si:
1. hay una hipótesis concreta respaldada por inspección del código;
2. se añade instrumentación/validación antes de copiar y lanzar kernels;
3. se prueba primero con un caso mínimo reproducible y se comprueba estabilidad;
4. se compara contra `llama.cpp` estable con el mismo modelo, cuantización, prompt, contexto y límite de salida;
5. se registra tasa de generación, prompt processing, latencia al primer token, RAM, swap, VRAM, estabilidad y corrección de la respuesta.

No basta con eliminar el crash: la caché debe aportar una mejora medible para justificar su mantenimiento.

## Relación con LEONES y TensorFold

Este experimento no cambia el runtime predeterminado de ODS ni establece que `llama-quik` sea un runtime soportado por LEONES. Clasificación: investigación exploratoria de motor/inferencia, resultado fallido/no concluyente.

El siguiente paso de trabajo es retomar **TensorFold** por separado, sin arrastrar este backend experimental ni tratar sus resultados como baseline. Las mediciones de TensorFold deben registrarse de forma independiente y con la misma regla LEONES: distinguir resultados ESTIMATED, reportes de terceros y MEASURED físico reproducido.

---
*Informe consolidado a partir de los comandos, logs y fragmentos de código observados en la sesión del 22 de octubre de 2026. Los datos que no se volvieron a comprobar se identifican expresamente como tales.*
