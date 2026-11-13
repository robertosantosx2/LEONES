# NEPENTHES · Informe cafe-llama.cpp + Qwen3.5-35B-A3B · 2026-11-13

**ID:** `NEPENTHES_cafe-llama.cpp_Qwen3.5-35B-A3B-IQ2_XXS_20261113`  
**Tipo:** ejecución independiente exploratoria  
**Estado:** ejecutada; evidencia primaria local; artefactos completos pendientes de incorporación al repositorio.

## 1. Objetivo y alcance

Registrar una ejecución funcional y monitorizada de Qwen3.5-35B-A3B IQ2_XXS con **cafe-llama.cpp**, siguiendo la metodología **Nepenthes**.

Esta es una prueba independiente. No constituye una comparación controlada con Tandem.cpp: no se igualaron ni verificaron todas las condiciones, y 89 de los 93 tokens del prompt fueron reportados como cacheados.

## 2. Motor

- **Motor:** `cafe-llama.cpp`
- **Repositorio local:** `~/cafe-llama.cpp-nepenthes`
- **Versión:** `0.7.0-dev`
- **Build:** `b1-de35160`
- **Commit:** `de35160`
- **Compilador:** GNU 15.2.0, Linux x86_64
- **Backend:** CUDA
- **Configuración de build:** Release, `GGML_CUDA=ON`, `GGML_CUDA_FA=ON`, `GGML_CUDA_GRAPHS=ON`
- **Binario:** `~/cafe-llama.cpp-nepenthes/build-nepenthes/bin/llama-server`
- **Endpoint:** `http://127.0.0.1:18086`
- **PID durante la prueba:** `21313`

Argumentos del servidor:

```bash
-m "$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf" \
--host 127.0.0.1 --port 18086 \
-c 2048 -b 128 -ub 64 -t 8 -tb 8 -ngl 99 \
--cpu-moe --moe-cache-mib 512 -np 1
```

El servidor ya estaba iniciado antes de la prueba. El runner no lo inició, detuvo ni reconfiguró.

## 3. Modelo

- **Modelo:** Qwen3.5-35B-A3B
- **Archivo:** `Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf`
- **Ruta:** `$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf`
- **Tamaño:** 10.665.148.928 bytes (aprox. 9,94 GiB)
- **Arquitectura GGUF:** `qwen35moe`
- **Parámetros:** 35B totales, A3B activos
- **Expertos:** 256 totales, 8 utilizados
- **Cuantización:** IQ2_XXS, 2,0625 bpw
- **Contexto declarado en metadatos:** 262.144 tokens
- **SHA-256:** no consignado en esta ficha; calcularlo desde el archivo original antes de publicar el paquete de evidencias.

## 4. Plataforma

- **Host:** MSI Thin 15 B12UC
- **Sistema:** Ubuntu
- **CPU:** Intel Core i7-12650H
- **RAM:** 14 GiB
- **Swap:** 32 GiB
- **GPU:** NVIDIA GeForce RTX 3050 Laptop, 4 GiB VRAM, sm_86
- **Driver:** 580.178.04
- **CUDA runtime:** 13.0
- **CUDA toolkit:** 13.4.92
- **Kernel:** 7.0.0-43-generic

## 5. Protocolo

Una petición independiente de generación para implementar `two_sum(nums, target)` en Python. El prompt exige complejidad O(n), tratamiento de negativos y duplicados, índices distintos, retorno `None` si no existe solución y tres casos de prueba.

Parámetros enviados:

- `temperature=0`
- `max_tokens=1536`
- `reasoning_format=deepseek`
- `reasoning_budget_tokens=128`
- `chat_template_kwargs.enable_thinking=true`
- `stream=false`

El campo `reasoning_budget_tokens=128` fue enviado en el cuerpo HTTP. No hay evidencia suficiente para afirmar que el servidor lo aplicó como límite efectivo.

## 6. Scripts y reproducción

Los scripts Nepenthes están publicados en:

- [Runner: run_NEPENTHES_cafe_independent_two_sum.py](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/run_NEPENTHES_cafe_independent_two_sum.py)
- [Inspector: inspect_NEPENTHES_cafe_independent_run.py](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/inspect_NEPENTHES_cafe_independent_run.py)
- [Monitor compartido: resource_monitor.py](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/resource_monitor.py)

Desde el directorio `repro/`, comprobar primero el endpoint y el PID real:

```bash
curl -fsS http://127.0.0.1:18086/health
pgrep -af 'llama-server.*18086'
```

Ejecutar la prueba en un directorio de salida nuevo:

```bash
python3 run_NEPENTHES_cafe_independent_two_sum.py \
  --pid "$PID" \
  --base-url http://127.0.0.1:18086 \
  --port 18086 \
  --model "$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf" \
  --output "$HOME/cafe-llama.cpp-qwen35-nepenthes-$(date +%Y%m%d-%H%M%S)"
```

Inspeccionar la ruta exacta generada por el runner:

```bash
python3 inspect_NEPENTHES_cafe_independent_run.py \
  "$HOME/cafe-llama.cpp-qwen35-nepenthes-AAAAMMDD-HHMMSS" \
  --show-content
```

El runner requiere Python 3 y el `resource_monitor.py` compartido en la ubicación documentada en la metodología. El runner se niega a sobrescribir un directorio de salida no vacío. El inspector trabaja sobre los datos guardados y no necesita el servidor activo.

## 7. Resultados medidos

| Métrica | Resultado |
|---|---:|
| HTTP | correcto |
| finish_reason | `stop` |
| Errores de petición | ninguno |
| Prompt tokens | 93 |
| Completion tokens | 1.060 |
| Cached prompt tokens | 89 |
| Prefill reportado | 26,62 tok/s |
| Generación | 31,03 tok/s |
| Caracteres de reasoning | 445 |
| Caracteres de contenido | 3.111 |
| CPU media del proceso | 99,74 % |
| CPU media del sistema | 6,97 % |
| GPU utilization media | 89,8 % |
| VRAM | 2.001 MiB estable |
| Temperatura GPU | 42–60 °C; media 55,86 °C |
| Potencia GPU | media 32,21 W |
| Swap-in del sistema | 90.112 bytes |
| Swap-out del sistema | 0 bytes |

La tasa de prefill no es una medición fría: 89/93 tokens fueron cacheados. Los contadores de swap y disco son del sistema y no se atribuyen exclusivamente al proceso.

## 8. Evaluación funcional

La implementación generada utiliza un diccionario hash y resuelve `two_sum` en O(n). El algoritmo trata correctamente negativos, duplicados y la condición de índices distintos; devuelve `None` cuando no encuentra solución.

Se observaron dos defectos editoriales en los ejemplos de prueba:

1. El caso etiquetado como duplicados utiliza `[3, 2, 4]`, que no contiene duplicados.
2. En el caso negativo, un comentario presenta primero un par cuya suma no coincide con el objetivo antes de indicar el par correcto.

La implementación principal es correcta, pero el bloque de pruebas generado no está completamente limpio y utiliza `print` en vez de aserciones.

## 9. Interpretación y limitaciones

- Es una ejecución independiente, no una comparación A/B con Tandem.cpp.
- El prefill está afectado por caché de prompt.
- No se ha demostrado que el servidor aplique el presupuesto de razonamiento enviado.
- No se han publicado aquí tres o más repeticiones independientes; por tanto, no se calculan mediana ni desviación entre repeticiones.
- Los datos de swap y disco son contadores globales del sistema.
- El hash del modelo debe incorporarse a la evidencia primaria para cerrar la identificación del artefacto.

## 10. Evidencia primaria

La ejecución original se guardó localmente en:

`~/cafe-llama.cpp-qwen35-independent-20261113/`

Ficheros conocidos:

- `manifest.json`
- `responses/independent-two-sum.json`
- `resources/resource_samples.jsonl`

Los logs, hashes y el paquete comprimido de evidencia completa siguen pendientes de incorporación al repositorio. Esta ficha no sustituye los datos originales.

## 11. Referencias

- [Metodología Nepenthes](tandem-qwen35-reasoning-budget-methodology-2026-11-12.md)
- [Plantilla reutilizable motor + modelo](NEPENTHES-engine-model-report-template.md)
- [Runner](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/run_NEPENTHES_cafe_independent_two_sum.py)
- [Inspector](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/inspect_NEPENTHES_cafe_independent_run.py)
