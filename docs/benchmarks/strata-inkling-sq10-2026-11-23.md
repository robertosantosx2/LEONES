# Strata + Inkling-2-Mini SQ-10 — validación local en MSI (2026-11-23)

**Fecha de ejecución:** 2026-11-23 (hora local Europe/Madrid; sesión de validación de primera hora).  
**Estado:** inferencia funcional y flujo HTTP con historial validados; rendimiento observado, no benchmark normalizado.  
**Equipo:** MSI Thin 15 B12UC · Intel Core i7-12650H · 14 GiB RAM · NVIDIA RTX 3050 Laptop 4 GiB (sm_86) · Ubuntu · driver NVIDIA 580.178.04 · runtime CUDA 13.0 · CUDA Toolkit 13.4.  
**Repositorio de registro:** [robertosantosx2/LEONES](https://github.com/robertosantosx2/LEONES).

> Este informe registra las salidas y métricas que se compartieron desde el terminal durante la sesión. No se generó un paquete de logs/JSONL bruto en el MSI ni se transfirieron archivos de evidencia binaria a LEONES. Los resultados son evidencia funcional observada, no una campaña estadística repetida ni una comparación controlada contra otros motores.

## 1. Artefactos y versiones

| Componente | Valor registrado |
|---|---|
| Strata Terminal | `0.2.20` (build `0.1.66`, Python 3.12.15) |
| Motor general Strata | `0.1.66` |
| Motor Inkling | `0.1.66`, Linux x86-64, CUDA 13, `sm_86` |
| Build ID del motor publicado en feed | `2e87c08db18a+cuda13.0` |
| Modelo | Inkling-2-Mini SQ-10 |
| ID API | `inkling-2-mini-sq-10` |
| Archivo | `$HOME/Strata-data/models/inkling-2-mini/Inkling-2-Mini-SQ-10.strata` |
| Tamaño | 10,471,526,400 bytes (~9.75 GiB) |
| SHA-256 del modelo verificado previamente | `ac4d452ad03e4930abd9d46f9c5eec22b2f75a1da45a1e49bd24ccd58b065934` |
| Binario del motor | `$HOME/.local/share/strata/components/shapes/inkling2/engine/0.1.66-linux-x86_64-cuda-cuda13/strata-inkling` |

El feed firmado consultado para Strata 0.2.20 ofrecía el motor Inkling 0.1.66 para CUDA 13 y `sm_86`, con driver NVIDIA mínimo 580.65. El equipo tenía driver 580.178.04. La actualización se completó con `ok:true`; no se detuvo ni reinició ningún modelo durante la operación de actualización. La versión 0.1.65 quedó conservada en disco.

## 2. Configuración de ejecución

Lanzamiento efectuado:

```bash
strata launch \
  --family inkling-2-mini \
  --model SQ-10 \
  --context 8192 \
  --parallel 1 \
  --vision off \
  --drafting off \
  --tune skip \
  --no-tui \
  --yes \
  --restart \
  --output json
```

Perfil: `launch-sq-10-8k`.  
Nombre del perfil: `SQ-10 8K`.  
Endpoint: `http://127.0.0.1:8080`.

La comprobación de salud devolvió `status=ok`, `loaded=true`, `max_context=8192`, modelo `inkling-2-mini-sq-10`, servicio `strata`; visión e image generation desactivadas. `/v1/models` confirmó el modelo cargado y el límite de contexto de 8192.

### Memoria GPU observada

En la captura de `nvidia-smi` de las 07:40:13:

- VRAM ocupada: 3505 / 4096 MiB.
- Proceso `strata-inkling`: 3478 MiB.
- Temperatura: 43 °C.
- Utilización GPU en el instante de la captura: 0%.
- VRAM libre aproximada: 591 MiB.

Es una instantánea, no un máximo de memoria durante inferencia. La escasa holgura de VRAM es motivo para conservar el perfil validado y no inferir que caben contextos, paralelismo o modalidades mayores.

## 3. Pruebas funcionales de generación

Todas las llamadas se hicieron secuencialmente contra el endpoint OpenAI-compatible, con `temperature=0` y drafting desactivado.

| Prueba | Entrada / objetivo | Tokens prompt → salida | Prefill | Generación | Finalización |
|---|---|---:|---:|---:|---|
| 1 | Responder únicamente `OK.` | 21 → 4 | 13.6 tok/s | 2.8 tok/s | `stop` |
| 2 | Reproducir una frase exacta: “El modelo Inkling funciona correctamente.” | 28 → 9 | 14.3 tok/s | 2.3 tok/s | `stop` |
| 3 | Explicar en español la utilidad de una GPU (~40 palabras) | 39 → 58 | 17.4 tok/s | 1.8 tok/s | `stop` |
| 4 | Recuperar nombre y finalidad de NEPENTHES desde un historial de tres mensajes | 70 → 19 | 30.5 tok/s | 2.0 tok/s | `stop` |

La tercera respuesta fue coherente y explicó el procesamiento paralelo de operaciones matemáticas, matrices y redes neuronales. La cuarta respondió: “Tu proyecto se llama NEPENTHES y mide el rendimiento de operaciones CUDA.”

La prueba 4 envió en una sola petición un mensaje de usuario con el dato, un turno de asistente preestablecido (“Entendido.”) y la pregunta de seguimiento. Por tanto, acredita recuperación a partir del contexto incluido en el cuerpo de la petición, no persistencia autónoma de memoria del servidor.

## 4. Flujo de dos peticiones HTTP independientes

Se ejecutó un script Python con dos llamadas HTTP secuenciales:

1. Primera petición: el usuario indicó que el motor se llama TENSORFOLD y se utiliza para ejecutar modelos Qwen. El modelo respondió `Dato recibido.`, con `finish_reason=stop`.
2. El script capturó el contenido real de esa respuesta y lo incorporó como mensaje `assistant` en el historial de la segunda petición.
3. Segunda petición: preguntó el nombre y la finalidad del motor. El modelo respondió: “Tu motor de inferencia se llama TENSORFOLD y lo utilizas para ejecutar modelos Qwen.”

Resultado del script: `CONTEXTO ENTRE PETICIONES: CORRECTO`.  
Segunda petición: 24 tokens generados, `finish_reason=stop`, generación 1.9 tok/s.

**Interpretación:** se validó el patrón cliente-servidor de dos peticiones separadas cuando el cliente reenvía el historial, incluyendo la respuesta real generada en la primera. La API `/v1/chat/completions` se trató como stateless: esta prueba no demuestra memoria persistente entre peticiones si el cliente omite el historial. La primera petición del script no imprimió ni conservó las métricas de temporización en la salida compartida.

## 5. Resumen de evidencia

- 5 respuestas de generación visibles y coherentes (incluida la primera respuesta y la segunda respuesta de la prueba HTTP de dos llamadas).
- Finalización `stop` en todas las respuestas cuyo `finish_reason` se imprimió.
- No se observaron respuestas vacías en estas pruebas.
- Recuperación de datos de contexto validada en una petición con historial y en un flujo de dos peticiones donde el cliente reenvió el historial real.
- Velocidad de generación observada en las pruebas con temporización: 1.8–2.8 tok/s; no es una mediana ni una cifra de benchmark sostenido.
- Prefill observado: 13.6–30.5 tok/s; los prompts y longitudes varían, así que tampoco es una comparación normalizada.
- Drafting desactivado: `draft_n=0` en las respuestas que reportaron esos campos.
- No se ejecutó una prueba de carga, concurrencia, estabilidad prolongada, visión, herramientas, contexto máximo ni persistencia de memoria.

## 6. Conclusión y clasificación

**Clasificación LEONES:** `EXECUTED / FUNCTIONALLY VALIDATED / PERFORMANCE OBSERVED`.

Strata Terminal 0.2.20 con Inkling engine 0.1.66 ejecutó correctamente Inkling-2-Mini SQ-10 en la MSI RTX 3050 Laptop, con contexto 8192 y paralelismo 1, para generación de texto y recuperación de historial reenviado por el cliente.

La actualización del motor coincide con la desaparición del fallo de respuestas vacías observado en las pruebas previas con 0.1.65; los resultados antes/después son indicativos, pero esta campaña no es un experimento A/B controlado y no permite atribuir causalidad definitiva. La generación, entre 1.8 y 2.8 tok/s en las muestras, es lenta. Con ~591 MiB libres en la instantánea de VRAM, no se recomienda ajustar ahora el perfil ni ejecutar inferencias simultáneas.

Mantener como configuración de referencia:

- Strata Terminal 0.2.20 / build 0.1.66.
- Inkling engine 0.1.66 CUDA 13 / sm_86.
- Inkling-2-Mini SQ-10.
- Contexto 8192; paralelismo 1.
- Visión y drafting desactivados.
- Endpoint local `127.0.0.1:8080`.

## 7. Límites y datos pendientes

No se capturaron en esta sesión TTFT, consumo máximo de RAM, pico de VRAM, swap durante cada generación, potencia/energía, tokens por segundo por repetición ni logs brutos persistentes. Tampoco se generó un paquete de reproducción independiente. No comparar directamente estas cifras con los benchmarks de llama.cpp, TensorFold, Tandem.cpp, Pithos o Kinetic: cambian modelo, formato, motor, contexto, prompt, protocolo y longitud de salida.

Para convertirlo en benchmark normalizado haría falta un protocolo fijo, repeticiones, telemetría simultánea y conservación de JSON/logs. Esta anotación no implica integración de Strata en REDIL/ODS ni enrutamiento desde LEONES Runtime: registra únicamente una ejecución local del motor y su API.

## 8. Referencias de la campaña

- [Strata](https://github.com/Niko1221/Strata) — feed firmado y release 0.2.20 consultados durante la actualización.
- Servicio local probado: `http://127.0.0.1:8080/health`, `/v1/models`, `/v1/chat/completions`.
- Evidencia de ejecución: transcripción de terminal compartida en la sesión del 2026-11-23. No se publican claves ni datos privados.
