# Informe integral del hilo «Verificación modelo CUDA» — 2026-10-21

## 1. Objetivo

Verificar qué motores podían ejecutar Qwen3.5-4B en el equipo Ubuntu físico con una NVIDIA RTX 3050 Laptop de 4 GiB, comparar rendimiento práctico y documentar resultados reproducibles para LEONES. El trabajo evolucionó desde comprobaciones de instalaciones y formatos hasta un benchmark secuencial de cuatro motores.

## 2. Entorno confirmado

- Sistema: Ubuntu nativo, arquitectura x86_64.
- CPU: Intel Core i7-12650H.
- RAM: aproximadamente 14 GiB.
- GPU: NVIDIA RTX 3050 Laptop, 4.096 MiB VRAM.
- Driver: 580.178.04; `nvidia-smi` reportaba CUDA 13.0.
- Artefacto GGUF para llama.cpp/RustingStrata/Mistral.rs: `~/llama.cpp-cuda/models/qwen3.5-4b-Q4_K_M.gguf`.
- Artefacto MLX para TensorFold: caché de Hugging Face `mlx-community/Qwen3.5-4B-MLX-4bit`.
- Script principal: `~/benchmarks/benchmark_qwen35_4b_three_engines_fixed_v2.sh` (el nombre del script quedó con «three_engines», aunque el benchmark final incluye cuatro motores).
- Salida de la ejecución final: `~/qwen35-4b-benchmark-fixed-20261021-003555/`.

## 3. Comprobaciones y motores excluidos

### SGLang

Se inspeccionó como opción, pero no se completó una ejecución real de Qwen3.5-4B en este entorno. Se dejó fuera del benchmark final. Una prueba de resolución/dry-run de dependencias no se considera inferencia verificada.

### KTransformers

Se inspeccionó el repositorio local `~/ktransformers`, rama `qwen3.5`, HEAD `1eafb76`. La ruta/documentación observada estaba orientada a Qwen3.5 MoE-400B y despliegues de gran tamaño; no se encontró una ruta verificada específica para Qwen3.5-4B ni reglas/arquitectura adecuadas en las comprobaciones hechas. No se completó instalación, compilación ni inferencia; se excluyó, sin afirmar incompatibilidad universal.

### vLLM + plugin GGUF

Se intentó validar vLLM 0.32.0 junto con `vllm-gguf-plugin 0.0.5`. La carga falló por discrepancia de nombre de arquitectura: el plugin identifica `qwen35`, mientras la arquitectura HF esperada es `qwen3_5`. Quedó excluido de la comparación funcional. No se atribuye el fallo a todos los usos de vLLM ni se considera un benchmark.

### Mistral.rs

Se añadió como cuarto motor verificado en la ronda final. El servidor llegó a responder a la API compatible con OpenAI y produjo las tres respuestas medidas; resultó más lento que los otros motores en este protocolo.

## 4. Motores ejecutados en el benchmark final

### TensorFold native

- Ejecutable de TensorFold native 1.1.1 bajo `~/tensorfold-test/...`.
- Modelo: `mlx-community/Qwen3.5-4B-MLX-4bit`.
- Endpoint local: `http://127.0.0.1:18084/v1`.
- El log indicó carga del modelo en 8,6 segundos.
- Tres solicitudes medidas, todas HTTP 200.
- Mediana: latencia 0,707 s; generación 54,74 tok/s; TTFT 0,131 s.

### llama.cpp CUDA

- Ejecutable: `~/llama.cpp-cuda/build-cuda/bin/llama-server`.
- Modelo: `qwen3.5-4b-Q4_K_M.gguf`.
- Endpoint local: `http://127.0.0.1:18085/v1`.
- Log confirmó «loading model» y «model loaded»; la extracción disponible no da una duración de carga normalizada y comparable.
- El log de generación contiene avisos de tensores no usados que se ignoraron; no impidieron que el servidor respondiera correctamente.
- Tres solicitudes medidas, todas HTTP 200.
- Mediana: latencia 0,834 s; generación 47,50 tok/s.

### RustingStrata

- Binario: `~/rusting-strata-test/target/release/strata`.
- Modelo GGUF Q4_K_M.
- Endpoint local: `http://127.0.0.1:18086/v1`.
- El log reportó plan de memoria weights+state+scratch de 2.656 MB, KV de 8 MB para contexto 256 y prefill de 29 MB; luego indicó que escuchaba en el puerto.
- Tres solicitudes medidas, todas HTTP 200.
- Mediana de latencia: 0,839 s.
- No se obtuvo un tok/s interno compatible ni TTFT en esta prueba; esos campos se conservan como n/d.
- Existía además un benchmark específico de motor anterior, ejecutado con `--gpu --ctx 1024 --pp 128,512 --tg 64 --reps 3`, que registró prefill 915,3–986,5 tok/s y decode 46,1–46,7 tok/s. Ese workload no se mezcla con las métricas API del benchmark final.

### Mistral.rs

- Se verificó el servidor en el puerto 18087.
- Log: «Loading model weights» a las 22:35:58.892824Z y «Model loaded» a las 22:36:01.575175Z; diferencia aproximada 2,682 s para esa fase.
- Tras cargar pesos, el proceso continuó inicializando funciones PTX de CUDA; la API `/v1/models` respondió después. Por tanto, 2,682 s no representa todo el arranque hasta readiness.
- Tres solicitudes medidas, todas HTTP 200.
- Mediana de latencia: 6,175 s; generación: 6,19 tok/s.
- Prefill registrado por el runtime: 40,107; 31,746; 36,946 tok/s en las tres pruebas.

## 5. Protocolo de benchmark final

- Ejecución secuencial; un motor activo a la vez.
- Prompt igual, temperatura 0.
- Contexto: 256.
- Prompt: 30 tokens.
- Límite de salida: 32 tokens.
- Tres requests medidos por runtime, más warm-up separado.
- Todos los doce requests medidos devolvieron HTTP 200.
- El resumen no fusiona TTFT, latencia total, carga del modelo y throughput de generación: son métricas distintas.

## 6. Resultados finales

| Motor | Mediana latencia request | Mediana generación | TTFT | Carga |
|---|---:|---:|---:|---|
| TensorFold MLX-4bit | 0,707 s | 54,74 tok/s | 0,131 s | 8,6 s explícitos en log |
| llama.cpp CUDA GGUF Q4_K_M | 0,834 s | 47,50 tok/s | n/d | No aislada con métrica normalizada |
| RustingStrata GGUF Q4_K_M | 0,839 s | n/d | n/d | n/d |
| Mistral.rs GGUF Q4_K_M | 6,175 s | 6,19 tok/s | n/d | 2,682 s para la fase «Loading model weights» → «Model loaded» |

TensorFold generó aproximadamente un 15,2 % más rápido que llama.cpp en la medición mediana. RustingStrata estuvo cerca de llama.cpp en latencia total. Mistral.rs fue sustancialmente más lento.

## 7. Interpretación y límites

1. Los cuatro motores completaron inferencia real local de Qwen3.5-4B y respondieron HTTP 200.
2. No es una comparación estrictamente homogénea: TensorFold usa MLX-4bit; los demás, GGUF Q4_K_M. La arquitectura de pesos, cuantización, placement y métricas internas pueden variar.
3. Son muestras cortas de un único equipo; no representan throughput sostenido, concurrencia, calidad, consumo energético ni generalización a otras GPUs.
4. No hay TTFT comparable para tres de los cuatro motores; no debe inventarse.
5. La latencia de request no debe convertirse en tok/s de RustingStrata por división simple, porque incluye costes que no equivalen al decode.
6. La carga de pesos, inicialización CUDA y disponibilidad HTTP son fases distintas.
7. La prueba valida los runtimes de forma independiente; no demuestra integración E2E con ODS, Magnitude o LEONES Runtime.

## 8. Artefactos y trazabilidad

El directorio local de la ejecución final es `~/qwen35-4b-benchmark-fixed-20261021-003555/` e incluye `results.csv`, `summary.md`, `benchmark.log`, logs de los servidores, `results.jsonl`, `warmup.jsonl` y metadatos de entorno. El repositorio publica el informe, una tabla CSV de métricas y esta reconstrucción cronológica; no se afirma que los logs brutos estén subidos.

## 9. Estado final

- **Verificados:** TensorFold, llama.cpp CUDA, RustingStrata y Mistral.rs.
- **Excluidos por esta ronda:** SGLang, KTransformers y vLLM con el plugin GGUF probado.
- **Ganador de esta configuración:** TensorFold en latencia y generación medidas.
- **Pendiente para una comparación más rigurosa:** repetir con protocolo y artefacto idénticos cuando sea posible, capturar TTFT de los cuatro, registrar VRAM pico por fase y medir explícitamente proceso-start, carga de pesos y primera respuesta HTTP por separado.
