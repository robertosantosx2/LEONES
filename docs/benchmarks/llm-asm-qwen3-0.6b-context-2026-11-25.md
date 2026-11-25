# llm.asm + Qwen3-0.6B Q8_0 — inferencia CPU y escalado hasta contexto completo (2026-11-25)

**Fecha de ejecución:** 2026-11-25 (Europe/Madrid).  
**Clasificación LEONES:** `EXECUTED / FUNCTIONALLY VALIDATED / PERFORMANCE MEASURED` — campaña exploratoria de contexto; resultados de una ejecución por tamaño, no benchmark estadístico.  
**Equipo:** MSI Thin 15 B12UC · Intel Core i7-12650H · 14 GiB RAM · NVIDIA RTX 3050 Laptop 4 GiB (sm_86) · Ubuntu · driver NVIDIA 580.178.04 · runtime CUDA 13.0 · CUDA Toolkit 13.4.92.  
**Proyecto upstream:** [alesha-pro/llm.asm](https://github.com/alesha-pro/llm.asm).  
**Registro:** [robertosantosx2/LEONES](https://github.com/robertosantosx2/LEONES).

> Esta campaña se ejecutó en CPU. No se utilizó ni se atribuye aceleración a la RTX 3050. Las métricas se transcriben de la salida de terminal y de los registros locales compartidos durante la sesión. Los logs completos permanecen en el MSI; no se han transferido como ficheros brutos a este repositorio en esta revisión.

## 1. Código, compilación y modelo

| Componente | Valor |
|---|---|
| Repositorio | `https://github.com/alesha-pro/llm.asm.git` |
| Commit probado | `48feccbfd57cb669440f31ff64958d95bb8b848e` |
| Mensaje del commit | `Add FAST_Q8=1 INT8xINT8 AVX2+F16C kernel, .asmbin v2 FP16 scales, and parallel GQA attention` |
| Fase | `01-qwen3-inference` |
| Build | `make inference test-math FAST_Q8=1` |
| Ensayos matemáticos | Todos los tests de `scripts/test_math.py build/test_math` pasaron |
| Modelo original | `Qwen/Qwen3-0.6B` |
| Arquitectura | Qwen3, 28 capas, hidden size 1024, 16 attention heads, 8 KV heads, head_dim 128, intermediate size 3072, vocabulario 151936 |
| Pesos originales | BF16 Safetensors, 1.503.300.328 bytes |
| Modelo exportado | `models/qwen3-0.6b-q8_0.asmbin` |
| Formato | `.asmbin v2`, Q8_0, escalas FP16, flags `0x7` |
| Tamaño exportado | 643.469.504 bytes (613,66 MiB) |
| SHA-256 del `.asmbin` | `14dc92c18dfd4182be6627558f716b9e7c5ebf9bc657b0ff700304e5a6502796` |
| Tokenizer | BPE; 151.387 merges |
| Exportación | `scripts/export_weights.py --scale-dtype fp16`; 11,34 s |
| Binario de inferencia | `build/asm-llm` |

La compilación y las pruebas de kernels matemáticos/SIMD finalizaron correctamente. `make check` identificó un ELF estático x86-64 de 14.712 bytes, sin sección dinámica. No se ejecutó `make all`, que también construye fases posteriores ajenas a esta campaña.

## 2. Configuración de inferencia

- CPU: Intel Core i7-12650H; cuatro hilos en la campaña de escalado.
- Cuantización: Q8_0 exportada desde el checkpoint BF16 oficial.
- Build con `FAST_Q8=1`.
- Backend: CPU x86-64; no CUDA.
- Generación de las pruebas de escalado: 16 tokens por ejecución.
- Contextos: 512, 1.024, 2.048 y 4.096.
- Entrada sintética: token ID `198` repetido, que corresponde al token de nueva línea del tokenizer Qwen3.
- Entrada directa mediante `--tokens`, por lo que no se añadió la plantilla de chat.

La repetición de ID 198 se eligió para controlar exactamente la longitud de entrada y estresar la ruta de contexto. **No es un prompt lingüístico ni una evaluación de calidad de generación.** Las pruebas de escalado caracterizan capacidad, consumo y velocidad bajo una secuencia sintética.

## 3. Escalado de contexto

Cada fila corresponde a una ejecución individual. Prefill y decode son las velocidades reportadas por el propio ejecutable. RSS es el máximo residente informado por `/usr/bin/time -v`.

| Entrada | Contexto configurado | Ocupación entrada + salida | Prefill | Decode | RSS máximo | Tiempo total |
|---:|---:|---:|---:|---:|---:|---:|
| 400 | 512 | 416 / 512 | 80,76 tok/s (4,953 s) | 54,58 tok/s (0,275 s) | 714.704 KiB (698,0 MiB) | 5,23 s |
| 900 | 1.024 | 916 / 1.024 | 69,06 tok/s (13,033 s) | 45,50 tok/s (0,330 s) | 827.512 KiB (808,1 MiB) | 13,37 s |
| 1.800 | 2.048 | 1.816 / 2.048 | 54,88 tok/s (32,799 s) | 32,51 tok/s (0,461 s) | 1.028.176 KiB (1.004,1 MiB) | 33,28 s |
| 3.800 | 4.096 | 3.816 / 4.096 | 34,57 tok/s (109,934 s) | 18,42 tok/s (0,814 s) | 1.476.048 KiB (1.441,5 MiB) | 1:50,79 |
| **4.080** | **4.096** | **4.096 / 4.096** | **33,09 tok/s (123,307 s)** | **17,27 tok/s (0,869 s)** | **1.537.040 KiB (1.501,0 MiB)** | **2:04,22** |

### Validación de cada ejecución

| Entrada | Tokens de entrada verificados | Tokens generados verificados | Exit status | Swap reportado |
|---:|---:|---:|---:|---:|
| 400 | 400/400, todos ID 198 | 16 | 0 | 0 |
| 900 | 900/900, todos ID 198 | 16 | 0 | 0 |
| 1.800 | 1.800/1.800, todos ID 198 | 16 | 0 | 0 |
| 3.800 | 3.800/3.800, todos ID 198 | 16 | 0 | 0 |
| 4.080 | 4.080/4.080, todos ID 198 | 16 | 0 | 0 |

La última ejecución completó 4.080 tokens de entrada y 16 tokens de generación: **4.096 posiciones exactas**. El script de validación encontró los 4.080 IDs de entrada, verificó 16 IDs de salida y confirmó `Exit status: 0`.

### Interpretación

- El motor completó la inferencia en el límite de contexto declarado por el modelo, sin truncar la entrada ni la generación solicitada.
- El RSS máximo aumentó de 698,0 MiB (400 tokens) a 1.501,0 MiB (4.080 tokens).
- Entre 400 y 4.080 tokens, el prefill descendió de 80,76 a 33,09 tok/s y el decode de 54,58 a 17,27 tok/s.
- La tendencia es compatible con el coste creciente de atención y con la materialización de más páginas de KV-cache FP32. Estas mediciones no separan de forma causal el coste de atención, la KV-cache, el planificador y otros componentes.
- Las ejecuciones no reportaron swap del proceso. No se midieron aquí potencia, energía, temperatura bajo carga ni pico de VRAM.

**Límite estadístico:** una ejecución por longitud no permite calcular mediana, dispersión ni significancia. Las diferencias entre tamaños son observaciones de esta serie, no una caracterización estadística ni una comparación entre motores.

## 4. Referencia de rendimiento con prompt lingüístico

Antes de la serie sintética se ejecutó una inferencia corta con prompt en inglés, cuatro hilos y salida máxima 64:

- Prefill: 24 tokens, 87,02 tok/s.
- Decode: 59 tokens, 62,84 tok/s; terminó antes del límite por EOS.
- RSS máximo: aproximadamente 634,4 MiB.
- Tiempo de pared: aproximadamente 1,26 s en una ejecución anterior de referencia; las capturas corresponden a ejecuciones distintas.
- Sin swap reportado.

También se validó una entrada textual de 78 tokens en contexto 512: prefill 87,25 tok/s, decode 62,37 tok/s para 16 tokens y RSS máximo 651.896 KiB (~636,6 MiB). Esta prueba no llenó el contexto.

Estas referencias lingüísticas se mantienen separadas de la serie sintética de IDs 198.

## 5. Contexto y memoria de KV-cache

La inspección de `shared/transformer.asm` identificó una reserva de arena anónima para buffers de activación, atención y KV. Para Qwen3-0.6B, con 28 capas, 8 KV heads y dimensión por cabeza 128, la KV-cache K+V FP32 tiene una capacidad teórica de:

`2 × 28 × contexto × 1024 × 4 bytes`

| Contexto | Capacidad teórica K+V |
|---:|---:|
| 512 | 112 MiB |
| 1.024 | 224 MiB |
| 2.048 | 448 MiB |
| 4.096 | 896 MiB |

Son tamaños de capacidad reservada para la KV-cache, no una predicción directa del RSS. La memoria física residente depende de las páginas realmente tocadas durante la ejecución.

La opción `-c` limita el contexto solicitado al máximo del header del modelo; el checkpoint exportado declara 4.096 posiciones. La prueba de frontera confirmó el uso efectivo de todas ellas.

## 6. Reproducción

Desde el checkout aislado del experimento:

```bash
cd "$HOME/llm-asm-qwen3-experiment/source"

# Compilación y tests matemáticos
make inference test-math FAST_Q8=1
"$HOME/llm-asm-qwen3-experiment/.venv/bin/python" \
  scripts/test_math.py build/test_math

# Prueba de frontera: 4.080 tokens de entrada + 16 de generación
TOKENS="$(python3 -c 'print(",".join(["198"] * 4080))')"

/usr/bin/time -v ./build/asm-llm \
  -m models/qwen3-0.6b-q8_0.asmbin \
  --tokens "$TOKENS" \
  -n 16 -t 4 -c 4096 --print-tokens
```

La ruta aislada fue `$HOME/llm-asm-qwen3-experiment`; el repositorio upstream se clonó con profundidad 1. Los originales BF16 se conservaron y la exportación Q8_0 se creó como artefacto separado.

## 7. Registros de ejecución locales

Los logs completos permanecen en el MSI en:

- `~/llm-asm-qwen3-experiment/logs/context-scaling/direct-400-tokens.log`
- `~/llm-asm-qwen3-experiment/logs/context-scaling/direct-900-tokens.log`
- `~/llm-asm-qwen3-experiment/logs/context-scaling/direct-1800-tokens.log`
- `~/llm-asm-qwen3-experiment/logs/context-scaling/direct-3800-tokens.log`
- `~/llm-asm-qwen3-experiment/logs/context-scaling/direct-4080-boundary.log`

El log de la prueba de 78 tokens se guardó en `~/llm-asm-qwen3-experiment/logs/context-scaling/` con el nombre asignado durante esa ejecución. Los cinco logs de la serie principal no se han subido como artefactos binarios/textuales independientes en este commit; las cifras y validaciones anteriores proceden de las salidas compartidas en la sesión.

## 8. Conclusión y estado

**Resultado:** `PASS — FULL DECLARED CONTEXT (4096/4096)`.

La compilación de `llm.asm` probada ejecutó Qwen3-0.6B Q8_0 en CPU sobre el MSI, y completó una generación de 16 tokens al alcanzar exactamente el límite de 4.096 posiciones. La prueba confirma capacidad funcional de contexto para esta combinación concreta de commit, exportación, modelo y parámetros. No acredita calidad lingüística a contexto largo, estabilidad prolongada, rendimiento GPU ni comportamiento de otras versiones/modelos.

**Siguiente validación recomendada:** repetir 900 y 4.080 tokens con el mismo protocolo para obtener variabilidad; posteriormente probar prompts lingüísticos largos, manteniendo separados los resultados sintéticos y funcionales. La adaptación a Qwen3-4B queda fuera del alcance de este informe.

## 9. Referencias

- [Repositorio upstream llm.asm](https://github.com/alesha-pro/llm.asm).
- [Modelo oficial Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B).
- Logs locales enumerados en §7.
- Transcripción de terminal y resultados de validación compartidos durante la sesión del 2026-11-25.
