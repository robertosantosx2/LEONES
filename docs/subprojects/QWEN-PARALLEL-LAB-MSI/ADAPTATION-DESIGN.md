# Diseño de adaptación paralela — MSI / Ubuntu

Estado: diseño técnico derivado de la auditoría estática del upstream. No es todavía una validación de ejecución en el MSI.

## Decisión de arquitectura

Portar primero la capa de orquestación de ramas y mantener TensorFold como servidor de inferencia independiente. No portar en bloque los parches nativos de RTX 5090.

El experimento original no distribuye expertos de un MoE. Ejecuta varias solicitudes de generación independientes para propuestas de trabajo, comparte un prefijo de conversación y, en la variante experimental, usa una barrera nativa para iniciar el decode de las ramas de forma sincronizada. Un coordinador integra después las propuestas y ejecuta las comprobaciones.

## Auditoría de portabilidad

### Reutilizable con adaptación mínima

- Construcción de tareas independientes y validación de IDs/límites.
- Captura inmutable del historial y de snapshots de ficheros.
- Preflight de tokenización para calcular el prefijo común real.
- Cálculo de presupuesto de contexto y límite de tokens por propuesta.
- Streaming SSE, recepción de usage y registro de TTFT/tiempos.
- Cancelación del lote si falla una rama.
- Entrega de propuestas en memoria o en ficheros.
- Recibos JSON/JSONL, hashes y cálculo de throughput agregado.

El núcleo `shared-core.mjs` usa APIs estándar de Node (fetch, streams, AbortController, crypto y fs) en estas rutas. No necesita PowerShell para la generación paralela en sí.

### No portable tal cual

- Los lanzadores `.cmd` y `.ps1`, y la función `terminal()` que invoca `powershell.exe`.
- La instalación de OMP fijada por el upstream y su perfil Windows.
- El instalador `scripts/setup.py` en su modo build, que exige Windows/MSVC.
- Los binarios y kernels compilados para SM120 / CUDA 13.3.
- Los parches nativos de las variantes: no son parches SM86 ni deben aplicarse sobre TensorFold 1.2.3.

### Requisito nativo que no se debe confundir con PR #1879

La orquestación experimental espera que el servidor anuncie `capabilities.synchronized_start` y acepte `start_group`, además de `shared_prefixes`. La barrera nativa sincroniza el prefill y el primer ciclo de decode; lanzar varias peticiones HTTP con `Promise.all` no reproduce por sí solo esa semántica.

TensorFold PR #1879 trata la reserva perezosa del scratch CUDA de Qwen3.5. En la consulta de 2026-11-13 continúa abierto y sin merge. Su integración puede reducir la memoria reservada al cargar el modelo, pero **no implementa por sí sola** el protocolo de ramas sincronizadas del proyecto original. Ambas piezas requieren validación separada.

## Diseño por etapas

### Etapa A — harness Linux, sin cambios nativos

1. Crear un runner Node ESM para Linux que reutilice las funciones portables de construcción de peticiones, tokenización, SSE, presupuestos, cancelación y recibos.
2. Sustituir la terminal PowerShell por un adaptador Linux explícito (subprocess con cwd restringido, timeout, cancelación y límites de salida); no habilitar ejecución arbitraria en las ramas.
3. Mantener las ramas en modo solo propuesta: sin herramientas, sin escrituras y con snapshots idénticos.
4. Implementar modo `serial` y modo `concurrent-http` como controles experimentales. El segundo mide concurrencia del servidor existente, sin afirmar que exista una barrera sincronizada ni reutilización de KV.
5. Probar primero con una petición y después con dos. Registrar errores de admisión, latencia y memoria; nunca forzar doce ramas en el MSI.

### Etapa B — baseline en el MSI

- Modelo inicial: `mlx-community/Qwen3.5-4B-MLX-4bit`, servido por TensorFold CUDA.
- Mantener la instalación TensorFold 1.2.3 intacta. Usar una copia de trabajo/build aislada cuando exista una revisión candidata.
- Contexto inicial conservador y salida acotada; medir una rama antes de probar dos.
- Capturar GPU/VRAM, RSS, RAM disponible, swap, TTFT, prefill, decode, tokens completados y recibos de cada rama.
- Comparar serial frente a concurrent-http con idénticos prompts, snapshots y límites. Informar throughput agregado y latencia individual por separado.

### Etapa C — protocolo sincronizado nativo (trabajo posterior)

Solo después de disponer de una base TensorFold Linux/SM86 reproducible:

1. Auditar en upstream los puntos de admisión, caché de prefijo, scheduler y ciclo de decode.
2. Diseñar soporte SM86/Qwen3.5 para grupo de inicio y prefijo compartido; no copiar código SM120 sin demostrar compatibilidad.
3. Exigir admisión atómica del lote: o se admiten todas las ramas con presupuesto de memoria seguro, o se rechaza el grupo sin dejar peticiones parciales.
4. Añadir pruebas de concurrencia frente a ejecución individual, igualdad de prefijos tokenizados, cancelación, errores parciales y limpieza de recursos.
5. Exponer `synchronized_start` únicamente cuando la barrera real esté implementada y probada en hardware.

## Política de concurrencia inicial

- Una rama: baseline obligatorio.
- Dos ramas: primer experimento concurrente, condicionado a memoria y estabilidad.
- Tres/cuatro: solo tras superar dos ramas repetidamente sin OOM ni degradación inaceptable.
- Doce: fuera del objetivo inicial del MSI; no se presupone viable.

La RTX 3050 tiene 4 GiB de VRAM. El scheduler del harness no puede inferir que la memoria sea suficiente a partir del número de ramas; debe respetar la admisión del runtime y conservar un margen de seguridad.

## Criterios de aceptación

- Runner Linux arranca contra un servidor TensorFold ya activo y no lo inicia, detiene ni reconfigura.
- Preflight usa el tokenizador real del runtime; no aproxima el prefijo común contando caracteres.
- Las ramas reciben el mismo historial y snapshots, y no disponen de herramientas de escritura.
- Ninguna salida truncada o fallida se integra como propuesta completa.
- Cancelación y timeout dejan recibos verificables y no procesos hijos huérfanos.
- Serial y concurrent-http quedan claramente etiquetados; no se llaman sincronizados.
- Cada resultado conserva configuración, revisión de modelo/engine, hash de snapshots, uso de tokens, tiempos y telemetría de memoria.
- Solo se etiqueta como MEDIDO un resultado ejecutado realmente en el MSI.

## Fuentes técnicas

- [Upstream Qwen Parallel Lab](https://github.com/Maharajahu/qwen-parallel-lab-rtx5090-tensorfold)
- [Núcleo de ramas experimental12](https://github.com/Maharajahu/qwen-parallel-lab-rtx5090-tensorfold/blob/main/variants/experimental12/omp-agent/shared-core.mjs)
- [Extensión de coordinación experimental12](https://github.com/Maharajahu/qwen-parallel-lab-rtx5090-tensorfold/blob/main/variants/experimental12/omp-agent/shared-extension.mjs)
- [Descripción del motor experimental12](https://github.com/Maharajahu/qwen-parallel-lab-rtx5090-tensorfold/blob/main/variants/experimental12/README.md)
- [TensorFold PR #1879](https://github.com/ashhart/TensorFold/pull/1879)

