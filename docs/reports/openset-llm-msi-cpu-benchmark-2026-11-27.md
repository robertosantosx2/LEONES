# openset-llm en MSI Thin 15 B12UC — expediente reproducible

**Fecha:** 2026-11-27 (CET)  
**Estado:** experimento ejecutado y medido; expediente documental. No es una aceptación upstream ni una certificación independiente.  
**Repositorio del motor:** https://github.com/opensetlabs/openset-llm  
**Checkout local:** `~/openset-llm-test`  
**Commit del checkout registrado al iniciar la investigación:** `5710dc380f9c16954f03878852e4571e0aaf457e`  
**Versión declarada del proyecto:** 0.3.3

## 1. Objetivo

Medir inferencia CPU local de openset-llm en el MSI, comparar MTP (draft-mtp) con generación sin especulación, y determinar el efecto de contexto y número de hilos. Todas las cifras de velocidad son **tokens/s de generación** salvo que se indique explícitamente prompt/prefill.

No se evalúa GPU/CUDA: esta ruta del proyecto se ejecutó en CPU. No se evalúa temperatura en este expediente.

## 2. Plataforma física

| Elemento | Dato |
|---|---|
| Equipo | MSI Thin 15 B12UC |
| Sistema | Ubuntu 26.04.1 LTS |
| CPU | Intel Core i7-12650H |
| Hilos lógicos | 16 |
| ISA relevante | AVX2 + AVX-VNNI (256-bit) |
| AVX-512 VNNI/BW | No disponible en esta CPU |
| RAM instalada/utilizable reportada | 16 GB / aproximadamente 14 GiB |
| Swap | 32 GiB, `/swap32.img` |
| GPU instalada | NVIDIA RTX 3050 Laptop, 4 GiB; no usada en estas pruebas |

Las muestras puntuales compartidas durante la prueba mostraron el proceso `llama-server` con RSS aproximado de 6.4–6.6 GiB en las ejecuciones MTP y alrededor de 6.4 GiB en el snapshot de KV8. No son mediciones aisladas del consumo incremental del modelo: el sistema tenía procesos de escritorio activos y swap en uso.

## 3. Software, modelo y procedencia

- Proyecto: `opensetlabs/openset-llm`, release declarada 0.3.3.
- Checkout registrado: `5710dc380f9c16954f03878852e4571e0aaf457e`.
- Motor derivado: fork PrismML de llama.cpp, commit `e3de71522`.
- Compilación local: nativa `-march=native`; compilador GNU 15.2; build reportado como `0.2.0-dev`.
- Ruta CPU elegida por el instalador: AVX2 + AVX-VNNI; no AVX-512.
- Diez parches del proyecto aplicados al motor (`0001`–`0010`).
- Modelo: Bonsai-2-27B ternary PTQ1_0 con MTP grafted.
- Archivo: `$HOME/.openset-llm/models/model.gguf`.
- Tamaño: 6,212,666,656 bytes.
- SHA-256: `08e7d363c8cc0d56a8632d7f4dd1199f8bc68690fb50522093714cbf9b5235af`.
- Graft registrado: 851 tensores base + 15 tensores grafted (266 MB); block_count 64 → 65.
- Sidecar MTP de origen registrado durante la instalación: aproximadamente 1.27 GB. El modelo final grafted contiene los tensores incorporados.
- Build log local: `$HOME/.openset-llm/build.log`.
- Ejecutables construidos: `llama-bench`, `llama-cli`, `llama-server`.

**No se ha publicado ni adjuntado el peso GGUF al repositorio LEONES.** El SHA-256 permite verificar que el fichero local sea idéntico al medido, pero para reproducir se necesita obtener legalmente el mismo artefacto. Tampoco se han archivado en este expediente los diez parches ni el build log completo; se conserva su identificación y ubicación local.

## 4. Condiciones comunes de benchmark

Servidor escuchando en loopback: `http://127.0.0.1:8080`. Un solo slot/stream. Thinking desactivado. Resume/prefix-state habilitado por defecto por el wrapper. No se usó GPU.

### Petición de 128 tokens

Prompt exacto:

```text
Explain why AVX-VNNI can accelerate integer inference on a CPU. Answer in 5 concise bullet points.
```

Parámetros:
- `temperature: 0`
- `max_tokens: 128`
- `POST /v1/chat/completions`
- `prompt_tokens: 36` en la petición sin caché.

Comando de servidor de referencia para MTP:

```bash
./serve --spec --spec-depth 2 --ctx 2048 --threads 6
```

Para las comparaciones se cambiaron solo los argumentos expresamente indicados en la tabla de resultados. La salida completa de generación terminó con `finish_reason=length`, como se esperaba al alcanzar el límite de tokens.

### Petición de 512 tokens

Prompt exacto:

```text
Explain in detail how AVX2 and AVX-VNNI accelerate quantized neural network inference on modern Intel CPUs. Cover vector dot products, integer accumulation, instruction throughput, memory bandwidth, quantization, and practical limitations. Use a structured technical explanation.
```

Parámetros:
- `temperature: 0`
- `max_tokens: 512`
- `prompt_tokens: 64` en la primera petición sin caché.

Comando:

```bash
./serve --spec --spec-depth 2 --ctx 2048 --threads 6
```

La petición se repitió sin reiniciar el servidor. En la segunda repetición se informó `cached_tokens=60`; el prefill de esa repetición no es comparable, pero el tiempo de generación sigue siendo válido.

## 5. Resultados medidos

Las filas conservan los campos de timing JSON proporcionados por el servidor. `generation_tps` corresponde a `predicted_per_second`. Las medias se calculan sobre las repeticiones indicadas; no se mezclan las cargas de 128 y 512 tokens.

| Contexto | Hilos | MTP | KV | Tokens salida | Generación tok/s | Propuestas / aceptadas | Aceptación |
|---:|---:|---|---|---:|---:|---:|---:|
| 1024 | 8 | off | default | 128 | 4.1212 | — | — |
| 1024 | 8 | depth 2 | default | 128 | 4.7285 | 133 / 59 | 44.36 % |
| 1024 | 8 | depth 2 | default | 128 | 4.6361 | 133 / 59 | 44.36 % |
| 1024 | 8 | depth 3 | default | 128 | 4.3001 | 183 / 64 | 34.97 % |
| 2048 | 8 | depth 2 | default | 128 | 4.9233 | 133 / 59 | 44.36 % |
| 2048 | 8 | depth 2 | default | 128 | 4.7457 | 133 / 59 | 44.36 % |
| 4096 | 8 | depth 2 | default | 128 | 4.7547 | 133 / 59 | 44.36 % |
| 4096 | 8 | depth 2 | KV8 | 128 | 4.6374 | 133 / 59 | 44.36 % |
| 2048 | 6 | depth 2 | default | 128 | 4.9580 | 133 / 59 | 44.36 % |
| 2048 | 6 | depth 2 | default | 128 | 4.9810 | 133 / 59 | 44.36 % |
| 2048 | 4 | depth 2 | default | 128 | 4.3103 | 133 / 59 | 44.36 % |
| 2048 | 4 | depth 2 | default | 128 | 4.3149 | 133 / 59 | 44.36 % |
| 2048 | 6 | depth 2 | default | 512 | 5.3450 | 468 / 276 | 58.97 % |
| 2048 | 6 | depth 2 | default | 512 | 5.2664 | 468 / 276 | 58.97 % |

### Medias relevantes

| Conjunto | Media generación |
|---|---:|
| 8 hilos, contexto 2048, 128 tokens (2 runs) | 4.8345 tok/s |
| 6 hilos, contexto 2048, 128 tokens (2 runs) | 4.9695 tok/s |
| 4 hilos, contexto 2048, 128 tokens (2 runs) | 4.3126 tok/s |
| 6 hilos, contexto 2048, 512 tokens (2 runs) | 5.3057 tok/s |

La media de las dos pruebas de 512 tokens varía aproximadamente un 1.5 % entre ejecuciones. La aceptación MTP fue idéntica (276/468) en ambas.

### Campos prompt/prefill y caché

- Primera prueba 512 tokens: prompt 12.4273 tok/s, 64 tokens, caché 0.
- Segunda prueba 512 tokens: prompt 1.8466 tok/s, solo 4 tokens nuevos y 60 tokens cacheados. **No usar esta cifra para comparar prefill.**
- En pruebas de 128 tokens algunas repeticiones reutilizaron 32 tokens de prefijo. Comparar principalmente `predicted_per_second` para generación y no el prefill de caché con el prefill completo.
- Los 503 `Loading model` producidos inmediatamente después de algunos arranques fueron transitorios; no son mediciones y se excluyeron.

## 6. Interpretación y límites

1. MTP depth 2 superó el baseline sin MTP en las condiciones ensayadas.
2. En las pruebas de 128 tokens, 6 hilos tuvo la mayor media observada (4.9695 tok/s), por delante de 8 hilos (4.8345) y 4 hilos (4.3126).
3. La diferencia entre 6 y 8 hilos es pequeña (~2.8 %); se requieren más repeticiones intercaladas para atribuir causalidad con confianza.
4. MTP depth 3 fue inferior a depth 2 en el ensayo de contexto 1024.
5. KV8 en contexto 4096 redujo ligeramente el RSS observado (aproximadamente 180 MiB frente al snapshot sin KV8), pero la velocidad medida bajó alrededor de 2.5 %. Es un ahorro modesto, no una optimización de velocidad demostrada.
6. Las pruebas largas de 512 tokens alcanzaron 5.3057 tok/s de media y 58.97 % de aceptación MTP. No comparar directamente con el conjunto de 128 tokens: prompt y longitud de salida fueron distintos.
7. No se ha aislado el coste de memoria del proceso frente a los demás procesos del escritorio; los snapshots RSS son observaciones puntuales.
8. No hay medición de GPU, consumo energético, rendimiento térmico, energía por token ni comparación controlada con FP32. Las afirmaciones genéricas del texto generado por el modelo (por ejemplo, ahorro energético 5–10×) **no son resultados medidos de este experimento**.
9. Las atribuciones 6 hilos y 4 hilos se basan en la secuencia de ejecución y las instrucciones de arranque de esta sesión; los mensajes conservados no incluyen el banner de arranque completo de esas dos configuraciones. Por ello, su asociación con el número de hilos tiene evidencia conversacional, pero no una captura independiente del comando de arranque.
10. No se conservaron logs completos del servidor ni los JSON originales en disco. Los campos numéricos de este expediente se transcribieron de las respuestas JSON compartidas en la sesión. La reproducción futura debe generar y conservar sus propios JSON completos.

## 7. Reproducción paso a paso

### 7.1 Verificar el checkout y el artefacto

```bash
cd "$HOME/openset-llm-test" || exit 1
git rev-parse HEAD
sha256sum "$HOME/.openset-llm/models/model.gguf"
stat -c '%n %s bytes' "$HOME/.openset-llm/models/model.gguf"
```

El checkout esperado para esta campaña es `5710dc380f9c16954f03878852e4571e0aaf457e`; el hash esperado del GGUF es el indicado en la sección 3.

### 7.2 Ejecutar el servidor de referencia

```bash
cd "$HOME/openset-llm-test" || exit 1
./serve --spec --spec-depth 2 --ctx 2048 --threads 6
```

Esperar a que el log indique `model loaded` y `listening on http://127.0.0.1:8080`. No enviar la petición antes de que termine la carga.

### 7.3 Ejecutar y conservar el JSON de 128 tokens

```bash
curl -sS http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "messages": [
      {"role":"user","content":"Explain why AVX-VNNI can accelerate integer inference on a CPU. Answer in 5 concise bullet points."}
    ],
    "temperature":0,
    "max_tokens":128
  }' | tee run-128.json | python3 -m json.tool
```

### 7.4 Ejecutar y conservar el JSON de 512 tokens

```bash
curl -sS http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "messages": [
      {"role":"user","content":"Explain in detail how AVX2 and AVX-VNNI accelerate quantized neural network inference on modern Intel CPUs. Cover vector dot products, integer accumulation, instruction throughput, memory bandwidth, quantization, and practical limitations. Use a structured technical explanation."}
    ],
    "temperature":0,
    "max_tokens":512
  }' | tee run-512.json | python3 -m json.tool
```

Repetir cada carga al menos dos veces; conservar todos los JSON y anotar `cached_tokens`, `prompt_n`, `predicted_n`, `predicted_ms`, `predicted_per_second`, `draft_n` y `draft_n_accepted`.

### 7.5 Comparar hilos o contexto

Detener el servidor con Ctrl+C entre configuraciones. Cambiar una sola variable cada vez:

```bash
./serve --spec --spec-depth 2 --ctx 2048 --threads 4
./serve --spec --spec-depth 2 --ctx 2048 --threads 6
./serve --spec --spec-depth 2 --ctx 2048 --threads 8
./serve --spec --spec-depth 2 --ctx 4096 --threads 8
./serve --spec --spec-depth 2 --ctx 4096 --threads 8 --kv8
./serve --spec --spec-depth 3 --ctx 1024 --threads 8
./serve --no-spec --ctx 1024 --threads 8
```

Para comparaciones fiables, usar el mismo prompt, salida, modelo, estado de caché documentado y condiciones del sistema. Intercalar el orden de las configuraciones y realizar al menos tres repeticiones por configuración. No mezclar prefill con caché y prefill completo.

## 8. Artefactos y comprobación de integridad

Artefactos locales de referencia:
- Modelo: `$HOME/.openset-llm/models/model.gguf`.
- Build log: `$HOME/.openset-llm/build.log`.
- Código: `$HOME/openset-llm-test`.
- Scripts de benchmark incluidos en el checkout: `bench/`.
- Wrapper de ejecución: `serve`.

Para generar un paquete de evidencia posterior:

```bash
mkdir -p evidence
cp run-128.json run-512.json evidence/
sha256sum evidence/*.json "$HOME/.openset-llm/models/model.gguf" \
  > evidence/SHA256SUMS
```

No subir pesos GGUF, credenciales, rutas privadas innecesarias ni logs que puedan contener datos sensibles. Este expediente registra el hash, no redistribuye el modelo.

## 9. Estado final

- **MEASURED:** rendimiento de generación, prefill cuando no hay caché, aceptación MTP y snapshots puntuales de RSS descritos arriba.
- **REPRODUCIBLE PROCEDURE:** comandos, prompts, argumentos y hash de modelo documentados.
- **NOT INDEPENDENTLY REPRODUCED:** no se ha ejecutado una segunda máquina ni una campaña nueva desde este expediente.
- **NOT MEASURED:** energía, GPU, temperatura, tokens/s de una batería estándar externa, throughput concurrente multiusuario y calidad comparativa del modelo.
- **NEXT VALIDATION:** repetir intercaladamente 4/6/8 hilos con 512 tokens y guardar JSON + logs completos; confirmar los argumentos efectivos de arranque en cada ejecución.

---
Expediente creado a partir de las salidas de terminal aportadas durante la sesión de investigación del 2026-11-27. Las incertidumbres y ausencias de captura quedan explícitas para no presentar inferencias como evidencia física.
