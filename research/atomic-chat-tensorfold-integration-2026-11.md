# Atomic Chat + TensorFold: integración nativa Linux/NVIDIA

**Fecha:** 2026-11-05  
**Estado:** propuesta técnica en LEONES; no es una integración implementada ni una validación upstream.  
**Rama de trabajo:** `research/atomic-chat-tensorfold-linux-cuda`  
**Objetivo:** preparar una implementación revisable para `AtomicBot-ai/atomic-chat-core` y, cuando corresponda, los cambios de interfaz en `AtomicBot-ai/Atomic-Chat`.

## 1. Objetivo

Incorporar TensorFold como motor local seleccionable en Atomic Chat, conservando el router y la API OpenAI-compatible que ya ofrece Atomic Chat. TensorFold debe ejecutarse como runtime propio, con ciclo de vida gestionado por Atomic, sin sustituir ni modificar los motores existentes.

La primera entrega se limita a **Linux x86_64 + NVIDIA CUDA**. La compatibilidad de otros sistemas, arquitecturas y aceleradores queda fuera de esta primera fase.

## 2. Evidencia y punto de partida

### Atomic Chat

- Aplicación: https://github.com/AtomicBot-ai/Atomic-Chat
- Núcleo de inferencia: https://github.com/AtomicBot-ai/atomic-chat-core
- Configuración de runtimes: https://github.com/AtomicBot-ai/atomic-chat-conf

El README de `atomic-chat-core` describe el núcleo TypeScript, el servidor OpenAI-compatible en `http://localhost:1337/v1` y los runtimes locales y gestionados. La versión inspeccionada durante esta investigación es `0.21.4`.

Las instrucciones de `atomic-chat-core/AGENTS.md` sitúan el ciclo de vida de motores gestionados en `src/runtime/managed-text/`, los adaptadores específicos en `src/runtime/<engine>/`, la coordinación en `src/core/managed-engines.ts` y los contratos públicos en `src/contracts/`.

El patrón gestionado actual está orientado a motores en contenedores (TensorRT-LLM, vLLM y SGLang). Sus descriptores se publican en `atomic-chat-conf/runtimes/` y contienen metadatos, no comandos ni scripts. No se debe asumir que ese patrón Docker sea automáticamente el adecuado para TensorFold.

### TensorFold

- Repositorio: https://github.com/ashhart/TensorFold
- Guía de ejecución: https://tensorfold.dev/guide
- Guía de API: https://tensorfold.dev/guide

TensorFold Native ofrece un servidor HTTP local con API OpenAI-compatible. La guía documenta `/health`, `/v1/models` y `/v1/chat/completions`, además de streaming y otros endpoints compatibles. El ejemplo de CLI utiliza:

```bash
tensorfold serve MODEL --name local-model --port 8080 \
  --parallel 1 --context 8192
```

En el paquete Linux el ejecutable nativo puede llamarse `tensorfold-native`; la interfaz exacta debe detectarse con `--version`, `capabilities --json` y `serve --help`. No se debe codificar como requisito que el usuario tenga el alias de shell `tensorfold`.

### Equipo de referencia LEONES

La máquina de validación disponible es un MSI Thin 15 B12UC con Ubuntu, Intel Core i7-12650H, NVIDIA RTX 3050 Laptop de 4 GiB VRAM y driver NVIDIA 580.178.04 / CUDA 13.0. TensorFold Native 1.2.0 está instalado en:

`~/.local/opt/tensorfold-1.2.0-linux-x86_64/bin/tensorfold-native`

La salida de capacidades registrada para 1.2.0 incluye `qwen3_5` con `mlx-q4g64` y `exl3`, y `qwen3_5_moe` con `mlx-q4g64`, `modelopt-mixed` y `modelopt-nvfp4`. Son capacidades declaradas por ese binario; cada familia/formato/modelo debe superar una prueba real antes de anunciarse como compatible en Atomic Chat.

## 3. Decisión arquitectónica propuesta

### No integrar TensorFold como un proxy manual

La solución no debe limitarse a pedir al usuario que arranque TensorFold en el puerto 8080 y configure un proveedor genérico. Eso serviría como workaround inmediato, pero no cumpliría el objetivo de que TensorFold sea un motor integrado, visible y gestionable desde Atomic Chat.

### Adaptador de proceso nativo

La hipótesis preferida es implementar TensorFold como un runtime nativo supervisado por el core:

1. El core localiza y valida el ejecutable `tensorfold-native` (o una ruta configurada explícitamente).
2. El core comprueba versión, capacidades, plataforma, driver y modelo antes del arranque.
3. El core selecciona un puerto loopback libre y arranca TensorFold como proceso hijo con argumentos separados (sin shell).
4. El core espera una señal real de disponibilidad mediante `/health` y verifica el modelo en `/v1/models`.
5. El router de Atomic Chat envía las peticiones al endpoint local de TensorFold, manteniendo la API pública de Atomic en `:1337/v1`.
6. El core supervisa logs, errores, parada, cancelación y limpieza del proceso.
7. La interfaz permite seleccionar TensorFold y sus modelos, y muestra los estados reales del motor.

Debe reutilizarse el ciclo de vida y las utilidades compartidas de `src/runtime/shared/` y el gateway común cuando el contrato actual lo permita. No se debe duplicar el servidor HTTP público ni crear un segundo router.

### Decisión pendiente de confirmar con el código

Antes de escribir el adaptador hay que determinar si la abstracción `managed-text` admite de forma limpia un motor nativo sin contenedor. Si sus invariantes exigen Docker/WSL, no se debe forzar TensorFold dentro de esa ruta: se añadirá una abstracción de runtime nativo reutilizando los contratos comunes de sesión, ocupación GPU, readiness y routing. Esta decisión requiere pruebas de diseño sobre la versión actual del core y, si cambia una decisión estable, un ADR.

## 4. Contrato funcional de la primera entrega

### Detección y preflight

- Linux x86_64 y NVIDIA CUDA como única plataforma declarada inicialmente.
- Detectar el binario sin instalar ni reemplazar software del host.
- Obtener versión y capacidades desde el propio ejecutable.
- Verificar que el modelo local existe y que su familia/formato está declarado por el motor.
- Comprobar driver, GPU y memoria disponible antes de iniciar.
- Mostrar un error accionable cuando el motor, modelo o GPU no sean compatibles.

### Modelo y almacenamiento

TensorFold trabaja con checkpoints nativos (por ejemplo, directorios de modelo de Hugging Face), no debe tratarse como si fuese un servidor GGUF. La primera implementación debe definir una única fuente de verdad para el directorio del modelo y evitar descargas duplicadas.

La fase inicial puede aceptar un directorio local ya descargado. La descarga/importación gestionada por Atomic se añadirá solo después de verificar cómo TensorFold resuelve repositorios, revisiones, caché, archivos y cancelación. No se debe anunciar que Atomic puede descargar cualquier modelo que TensorFold acepte.

### Servidor y API

- Bind exclusivo a `127.0.0.1`.
- Puerto dinámico reservado por el core; no asumir el puerto 8080.
- ID de modelo estable y verificable a través de `/v1/models`.
- Readiness real por `/health`, con timeout y logs diagnósticos.
- Compatibilidad inicial: `/v1/chat/completions`, incluidos mensajes normales y streaming SSE.
- Las opciones de generación se pasan solo cuando TensorFold las admite.
- Las funciones no compatibles (herramientas, visión, JSON/structured output, embeddings, audio, etc.) se declaran explícitamente y se rechazan de forma clara; no se simula soporte.
- La autenticación interna puede permanecer desactivada si el servidor solo escucha en loopback; si el core habilita clave, debe usar un archivo de permisos restrictivos y no exponerla en argv ni logs.

### Recursos y convivencia

- Integrar TensorFold en el control de ocupación GPU de Atomic para evitar cargas simultáneas incompatibles.
- Una sola carga residente por GPU, salvo que el contrato actual demuestre que puede coordinarse de forma segura.
- Respetar la memoria disponible y los límites de contexto/paralelismo.
- No terminar procesos ajenos ni cambiar drivers, CUDA, Docker, llama.cpp, Ollama, TensorFold o servicios existentes del usuario.
- El cierre de Atomic debe parar únicamente el proceso TensorFold que el core haya creado y cuya identidad pueda verificar.

## 5. Alcance por fases

### Fase A — LEONES: investigación y especificación

- Registrar contratos actuales de Atomic Core.
- Verificar CLI/API de TensorFold 1.2.0 en Ubuntu + CUDA.
- Definir el modelo de proceso, puertos, readiness, parada y logs.
- Identificar las superficies de core, configuración y UI que habrá que modificar.
- Preparar una matriz de capacidades y pruebas reproducibles.

### Fase B — LEONES: prueba de concepto

- Crear un pequeño harness independiente que arranque TensorFold como proceso hijo.
- Verificar detección de versión/capacidades.
- Cargar un checkpoint compatible que ya exista localmente.
- Probar `/health`, `/v1/models`, chat no-stream y streaming.
- Verificar cierre limpio, timeout, proceso muerto, puerto ocupado y error de memoria.
- Registrar comandos, salida, versiones y resultados sin publicar credenciales ni datos privados.

La prueba de concepto no debe modificar la instalación de Atomic Chat ni los servicios locales existentes.

### Fase C — Atomic Chat Core

- Implementar el adaptador y contratos necesarios.
- Añadir settings, selección de motor y rutas de carga/descarga/cancelación según las convenciones actuales.
- Integrar ocupación GPU, readiness, health, logs y routing.
- Añadir tests unitarios, de contrato, e2e y live opt-in.
- Ejecutar `npm run verify` y las pruebas live en una máquina Linux NVIDIA antes de declarar aceptación.

### Fase D — Atomic Chat App y configuración

- Exponer TensorFold en la UI de motores/modelos.
- Añadir configuración/descriptor solo si el diseño final lo requiere.
- Actualizar versión del core fijada por la aplicación.
- Verificar instalación limpia, actualización y rollback.
- Preparar PR(s) separados si el core, la aplicación y `atomic-chat-conf` requieren repositorios distintos.

## 6. Criterios de aceptación

- [ ] El core detecta TensorFold 1.2.0 y muestra sus capacidades reales.
- [ ] Se puede seleccionar un checkpoint local compatible sin convertirlo a GGUF.
- [ ] El core inicia el proceso con argv seguro y puerto loopback dinámico.
- [ ] Readiness y listado de modelos se verifican antes de ofrecer el motor como disponible.
- [ ] Atomic Chat responde a través de su API `:1337/v1` usando TensorFold como backend.
- [ ] Streaming funciona o se documenta con precisión cualquier limitación.
- [ ] La parada/cancelación no afecta a procesos que no pertenezcan al core.
- [ ] La gestión GPU evita cargas concurrentes inseguras.
- [ ] Los fallos de memoria, incompatibilidad y ausencia del binario se presentan con mensajes útiles.
- [ ] Los motores existentes siguen funcionando sin cambios.
- [ ] Tests y aceptación live reproducibles pasan en Linux + NVIDIA.

## 7. Fuera de alcance inicial

- macOS/Metal, Windows, WSL, AMD/ROCm y CPU-only.
- Instalación automática privilegiada de drivers, CUDA o dependencias del sistema.
- Contenerizar TensorFold sin una necesidad técnica demostrada.
- Convertir checkpoints GGUF a formatos nativos o viceversa.
- Declarar soporte universal de modelos, visión, herramientas, embeddings o audio.
- Cambiar el comportamiento del backend llama.cpp existente.

## 8. Referencias

- Atomic Chat: https://github.com/AtomicBot-ai/Atomic-Chat
- Atomic Chat Core: https://github.com/AtomicBot-ai/atomic-chat-core
- Atomic Chat Core agent instructions: https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/AGENTS.md
- Atomic Chat Core plan: https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/PLAN.md
- Atomic Chat runtime configuration: https://github.com/AtomicBot-ai/atomic-chat-conf
- TensorFold: https://github.com/ashhart/TensorFold
- TensorFold CLI guide: https://tensorfold.dev/guide
