# Kinetic — auditoría preliminar de arquitectura y código

Fecha: 2026-11-11  
Upstream: https://github.com/Veloresearch/kinetic  
Rama inspeccionada: `main` (el SHA exacto se fijará al ejecutar `scripts/import_kinetic.sh`)  
Estado: **STATIC REVIEW / PRELIMINAR**. No equivale a compilar, ejecutar ni auditar línea por línea todo el repositorio.

## 1. Identidad y alcance

Kinetic es un motor de inferencia local escrito en Rust, licencia Apache-2.0, que carga GGUF y ofrece CLI, servidor OpenAI-compatible y bindings. El README upstream declara CPU x86-64, CUDA NVIDIA y Vulkan, con fallback automático. El workspace declara Rust 1.91 o posterior.

El README anuncia compatibilidad con Qwen3.5 (dense y MoE), Gemma 4, Qwen3/Qwen2.5, Llama, LFM3/LFM2, Granite, OLMo 2, Falcon-H1 y otros. La compatibilidad debe verificarse por arquitectura, variante GGUF, backend y versión concretos; no asumir que cada combinación funciona.

## 2. Arquitectura observada

- Workspace Rust: `crates/*`; perfiles release con thin LTO y un codegen unit.
- CLI: `kinetic run/chat/serve/bench/doctor/pull/info/verify/verify-receipt`.
- Servidor: API OpenAI y Ollama; por defecto loopback (127.0.0.1).
- Runtime: selección CPU/CUDA/Vulkan, capas GPU configurables, contexto, hilos y caché de prompt.
- Mecanismos anunciados: RAD-1 (speculative decoding exacto), Warm Start, Zero Wait, Torque (CUDA Graphs / replay Vulkan), Convoy (concurrencia), Shortlist, Burst y Flywheel (MoE).
- GGUF compartido con llama.cpp; también formato .ktc propio.

## 3. Fortalezas potenciales para LEONES

1. Rust y CLI única facilitan empaquetado y reproducibilidad.
2. API OpenAI compatible permite un cliente común para pruebas funcionales y de latencia.
3. `kinetic bench --json` ofrece mediciones internas de carga, prefill, decode y memoria; debe contrastarse con medición externa.
4. Los mecanismos de aceleración pueden activarse/desactivarse mediante `--off`, útil para ablación.
5. Recibos de ejecución y verificación de salida permiten estudiar reproducibilidad.
6. GGUF permite reutilizar los mismos ficheros físicos en motores distintos.

## 4. Riesgos, límites y preguntas que requieren inspección/ejecución

| Área | Riesgo / pregunta | Verificación exigida |
|---|---|---|
| Comparabilidad | Defaults y sampling pueden diferir entre motores | Fijar parámetros explícitos y guardar la configuración efectiva |
| Exactitud | "Exact" depende de dispositivo, algoritmo y condiciones | Comparar greedy token a token con aceleraciones activadas/desactivadas |
| Warm Start | El estado cacheado beneficia prompts repetidos | Separar primera ejecución fría y repetición caliente; limpiar caché entre fases |
| Zero Wait | Depende del prefill anticipado del cliente | Excluirlo del benchmark básico; medirlo en suite interactiva independiente |
| Torque | Puede depender de CUDA Graphs, forma y estabilidad de buffers | A/B con `--off torque`, registrar backend, driver y fallos |
| Flywheel | La política CPU/GPU y la caché de expertos afecta latencia y memoria | Registrar expertos/cache si hay métricas; medir RAM, VRAM, swap y throughput |
| Convoy | El rendimiento agregado no equivale a latencia por usuario | Suite de concurrencia separada; registrar throughput total y percentiles por petición |
| Memoria | Reservas y cachés cambian el estado de la máquina | Muestrear VRAM/RAM/swap antes, durante y después; no confiar solo en cifras del motor |
| Soporte GPU | CUDA/Vulkan tienen cobertura desigual por familia | Forzar backend; registrar fallback real y rechazar comparaciones con backend distinto |
| API | Campos y métricas pueden variar entre implementaciones | Cliente tolerante; capturar cuerpo bruto, headers, errores y usage |
| Seguridad | Servidor local y comandos externos | Bind a 127.0.0.1, puertos efímeros, no exponer red, no descargar modelos durante benchmark |
| Licencia/marca | Apache-2.0 no concede derechos de marca | Retener LICENSE/NOTICE; seguir TRADEMARKS.md |

## 5. Revisión de código realizada

Archivos consultados en upstream:
- `README.md`: capacidades, comandos, dispositivos, modelos, benchmarks y privacidad.
- `Cargo.toml`: workspace, MSRV Rust 1.91, dependencias compartidas y perfil release.
- `crates/kinetic-cli/src/main.rs`: superficie CLI, argumentos y defaults de ejecución.
- `scripts/bench_vs_llamacpp.py`: metodología comparativa publicada.

Observaciones concretas:
- El README indica que `kinetic bench` mide load, prompt, generation, edit y peak memory, con salida JSON.
- El script upstream de comparación fuerza CPU mediante `CUDA_VISIBLE_DEVICES=-1` para la comparación plain; eso no es válido como sustituto de una comparativa CUDA en esta MSI.
- El mismo script usa el mejor resultado de varias repeticiones (best-of-N), que puede ocultar variabilidad. LEONES conservará todas las repeticiones y publicará mediana, p95 cuando proceda y dispersión.
- En la comparación edit, el script upstream usa un calentamiento y una sola medición; la suite LEONES separará warmup y repeticiones medidas, e impedirá que el prompt cache contamine el caso cold.
- El código CLI declara contexto por defecto 32768, selección automática de dispositivo y defaults propios de caché. LEONES no heredará esos defaults implícitamente: fijará valores explícitos por perfil.
- El README indica que Kinetic no contacta la red salvo `pull`; aun así, LEONES ejecutará con modelos locales y registrará cualquier acceso/descarga como fuera de alcance.

No se ha revisado aún el detalle de kernels CUDA, allocator, sincronización, scheduler, serialización de caché, algoritmos RAD-1, ni cada familia de modelo. Esas áreas quedan como fase 2 de auditoría con source snapshot fijado.

## 6. Gate de aceptación en LEONES

- [ ] Importar snapshot completo y guardar `UPSTREAM_COMMIT`.
- [ ] Retener LICENSE, NOTICE y TRADEMARKS.
- [ ] Compilar release en Ubuntu de la MSI y guardar log, versión Rust/CUDA y hashes.
- [ ] Ejecutar tests upstream disponibles y guardar resultados.
- [ ] Ejecutar `kinetic doctor`, `kinetic info` y `kinetic bench --json` con modelo local.
- [ ] Confirmar backend efectivo (CUDA, no fallback silencioso a CPU).
- [ ] Verificar memoria y estabilidad con Qwen3.5-4B Q4_K_M.
- [ ] A/B de RAD-1/Warm Start/Torque y comparar respuestas greedy.
- [ ] No marcar Kinetic como MEASURED en LEONES hasta tener ejecución física, logs y metadatos.

## 7. Fuentes

- https://github.com/Veloresearch/kinetic
- https://github.com/Veloresearch/kinetic/blob/main/Cargo.toml
- https://github.com/Veloresearch/kinetic/blob/main/scripts/bench_vs_llamacpp.py
- https://veloresearch.github.io/kinetic/benchmarks.html
- https://veloresearch.github.io/kinetic/devices.html

**Clasificación LEONES:** capacidades upstream = DECLARED; esta revisión = STATIC REVIEW; cualquier rendimiento en MSI = NOT MEASURED hasta ejecutar el plan.
