# Plan de benchmark cruzado: Kinetic vs TensorFold vs Tandem.cpp vs RustInstrata

Fecha: 2026-11-11  
Equipo objetivo: MSI Thin 15 B12UC, Ubuntu, i7-12650H, RTX 3050 Laptop 4 GiB, RAM 14 GiB.  
Estado: plan reproducible; **todavía no hay resultados comparativos MEASURED**.

## 1. Objetivo

Ejecutar cada motor en serie, cargando un GGUF local, aplicando perfiles de parámetros y una batería fija de prompts. Tras cada perfil: detener el servidor, esperar su descarga, tomar medidas de la máquina y exigir que el estado vuelva a una banda comparable antes de cargar el siguiente perfil/motor. Guardar configuración, hashes, stdout/stderr, respuestas, muestras de recursos y métricas en un directorio de sesión.

Motores: Kinetic, TensorFold 1.2.3, Tandem.cpp (llama.cpp con configuración CPU-MoE/GPU según perfil) y RustInstrata.

## 2. Modelo y comparabilidad

Primera matriz recomendada:
- Modelo principal: misma familia y checkpoint Qwen3.5-4B. Kinetic y Tandem.cpp pueden usar el mismo GGUF+SHA-256; TensorFold puede requerir su artefacto MLX/EXL3 propio y RustInstrata puede tener otro formato. El harness permite un `model` distinto por motor.
- Modelo secundario opcional: MiniCPM5-2B, solo cuando se confirme soporte de arquitectura en cada motor.
- No convertir ni volver a cuantizar silenciosamente. Si los motores no aceptan el mismo fichero, registrar checkpoint de origen, formato, cuantización y hash individual. Esa ronda se etiqueta **COMPARACIÓN DE CHECKPOINT / CUANTIZACIONES EQUIVALENTES**, no comparación bit-a-bit.
- Un modelo no soportado se registra como UNSUPPORTED; no se sustituye silenciosamente.
- Solo se hará ranking directo estricto cuando el artefacto, tokenizer, plantilla de chat, contexto y cuantización sean realmente comparables.
- Fijar contexto 512 y 1024 inicialmente; ampliar solo después de validar estabilidad.
- Perfiles GPU: CUDA con 0/8 capas solo cuando el motor exponga el parámetro equivalente; backend real debe quedar registrado.
- CPU: 4 y 8 hilos; GPU: mismo número de hilos host cuando sea configurable.
- Parallel=1 en la suite base; concurrencia se medirá aparte.

## 3. Secuencia por motor y perfil

1. Tomar baseline de sistema (RAM disponible, swap, carga CPU, VRAM usada/total, GPU util/temp, procesos).
2. Validar que no hay otro servidor/modelo ocupando recursos; nunca matar procesos ajenos automáticamente.
3. Iniciar el motor con comando explícito y puerto loopback.
4. Esperar health endpoint; medir tiempo de carga y capturar log de arranque.
5. Lanzar warmup separado (no contabilizado).
6. Ejecutar prompts: extracción estructurada, razonamiento breve, código, resumen largo y español. Para cada prompt: temperatura, top_p, top_k si está soportado, seed, max_tokens, contexto y timeout explícitos.
7. Repetir según configuración; guardar respuesta completa, usage, TTFT, duración total, tokens/s (solo si usage está disponible) y errores.
8. Muestrear RAM/VRAM durante cada petición y conservar máximos observados.
9. Detener proceso con SIGTERM; esperar; SIGKILL solo al proceso hijo lanzado por el harness si no termina.
10. Esperar a que RAM/VRAM/utilización regresen a la banda de baseline; guardar post-unload y estabilidad.
11. Si no recupera estado comparable, marcar el siguiente perfil como BLOCKED_BASELINE y no continuar cargando motores.
12. Repetir desde el paso 1 para el siguiente motor.

## 4. Parámetros y ablaciones

Cada perfil reinicia el proceso, ya que contexto, backend, capas, caché y concurrencia suelen fijarse al cargar:
- `ctx`: 512 / 1024.
- `threads`: 4 / 8.
- `gpu_layers`: 0 / 8 (si existe).
- `parallel`: 1.
- Caché de prompt: OFF en baseline cold; ON en suite warm-start específica.
- Kinetic: baseline con aceleraciones activas; ablaciones separadas con `--off rad1,warm-start,zero-wait,torque,convoy` o subconjuntos. No mezclar métricas de ablación con baseline.
- TensorFold: registrar backend, reserve, contexto, segmentos y opciones CUDA efectivas.
- Tandem.cpp: registrar `--cpu-moe`, `LLAMA_MOE_CPU`, threads, batch/ubatch, ngl, KV cache y flags speculative.
- RustInstrata: registrar build, backend, flags de memoria/caché, threads y offload reales.

## 5. Tipos de prompt

Los prompts son idénticos y versionados por el propio script:
- extraction_json: salida JSON de campos fijos.
- reasoning: problema lógico breve con respuesta explicada.
- code_generation: función Python con tests mínimos.
- summarization: resumen de texto fijo de longitud suficiente.
- spanish: instrucción y respuesta en español.
Cada caso fija `temperature=0`, `top_p=1`, `seed=42`, `max_tokens` explícito para facilitar repetibilidad. Se puede añadir suite sampling aparte.

## 6. Métricas

- Load time (desde spawn hasta health ready).
- TTFT medido por primer fragmento SSE.
- Completion tokens y prompt tokens del campo usage (si el motor lo devuelve).
- Decode tok/s = (completion_tokens - 1) / (last_token_time - first_token_time), solo cuando se dispone de usage y timestamps de stream.
- Wall time total.
- RAM RSS del proceso y máximo RSS del proceso árbol (cuando disponible); RAM total disponible, swap usado.
- VRAM usada, GPU util, temperatura y potencia (si nvidia-smi lo soporta).
- Exit code, señal de terminación, estado de health y recuperación post-unload.
- Hash del modelo, binario, versión, comando, variables de entorno relevantes y snapshot del host.

No comparar métricas si cambian modelo/hash, prompt, contexto, backend, sampling o hardware. Publicar resultados por separado para CPU y CUDA.

## 7. Criterios de estado de máquina

La suite toma baseline en reposo al principio y después de cada unload. Por defecto:
- RAM disponible no debe caer más de 700 MiB respecto al baseline de sesión.
- VRAM usada no debe quedar más de 256 MiB sobre baseline.
- GPU util debe estar <= 5% durante 3 muestras consecutivas.
- No debe haber proceso de inferencia iniciado por la suite todavía vivo.
- Espera máxima de recuperación: 180 s; si no se recupera, abortar de forma segura.
Estos umbrales son configurables y quedan guardados en el manifiesto. No se borran page cache del kernel ni se fuerza `drop_caches`: eso distorsionaría el entorno y requiere privilegios.

## 8. Artefactos

Directorio `artifacts/engine-comparison/<timestamp>/`:
- `manifest.json`: host, SO/kernel, GPU/driver/CUDA, modelo y SHA, versiones, perfiles, prompts, comandos y thresholds.
- `results.jsonl`: un evento JSON por perfil/prompt y muestras.
- `summary.json`: resultados agregados y estados.
- `session.log`: log humano consolidado.
- `engines/<engine>/<profile>.stdout.log` y `stderr.log`.
- `responses/<engine>/<profile>/<prompt>.txt`.
- `machine/<engine>/<profile>/{before,during,after}.json`.

El script genera estos ficheros automáticamente. El manifiesto y cada evento deben conservar el SHA-256 individual del artefacto usado por cada motor; nunca asumir que todos cargaron el mismo fichero. Mantener los artefactos de cada sesión inmutables y enlazarlos desde el informe LEONES.

## 9. Ejecución

1. Importar Kinetic: `scripts/import_kinetic.sh`.
2. Preparar configuración: copiar `configs/engine-comparison.example.json` y ajustar comandos absolutos de los motores ya instalados.
3. Ejecutar primero un smoke test con un solo motor y contexto 512.
4. Ejecutar suite completa con el mismo modelo y perfiles.
5. Revisar que ningún motor haya hecho fallback y que cada perfil recuperó baseline.
6. Solo entonces publicar comparativa MEASURED.

Comando:
```bash
python3 scripts/engine_comparison.py --config configs/engine-comparison.json --model /ruta/Qwen3.5-4B-Q4_K_M.gguf
```

El harness no descarga modelos, no mata servicios preexistentes y no cambia drivers, swap ni configuración global.
