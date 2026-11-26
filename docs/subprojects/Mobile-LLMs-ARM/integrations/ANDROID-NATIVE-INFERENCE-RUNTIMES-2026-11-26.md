# Runtimes nativos de inferencia LLM en Android — prospección y selección

**Fecha:** 2026-11-26  
**Proyecto:** LEONES / Mobile-LLMs-ARM  
**Plataforma objetivo:** Xiaomi Mi 9T Pro, Snapdragon 855 (SM8150), Adreno 640, 6 GB RAM, Android 10, ARM64  
**Estado:** `SOURCE_VERIFIED` para las fuentes y características documentadas; `PENDING_DEVICE_VALIDATION` para ejecución en el Mi 9T Pro.  
**Decisión provisional:** evaluar primero `tensai-app/llama.kt` como biblioteca de inferencia embebida; mantener PocketLLM y AiPaca como alternativas de API HTTP local.

## 1. Objetivo

Investigar motores y bibliotecas que ejecuten inferencia LLM directamente en Android, sin depender de Termux, proot ni un entorno Linux adicional. El objetivo operativo es que el teléfono pueda alojar conjuntamente:

- ROS 2 Android y sus nodos/sensores.
- Un runtime LLM nativo Android que cargue el GGUF local.
- Un puente ROS 2–LLM que intercambie intenciones estructuradas.
- La comunicación con micro-ROS Agent / ESP32 del robot.

La eliminación de Termux es una hipótesis de arquitectura que debe probarse. No se presupone que cualquier biblioteca nativa pueda integrarse directamente en el APK de ROS 2 Android: ABI, NDK, dependencias nativas, ciclo de vida y licencias deben verificarse.

## 2. Resultado ejecutivo

### Primera opción: llama.kt

Repositorio: https://github.com/tensai-app/llama.kt  
Commit observado en la rama `main` el 2026-11-26: `d3c306d60007a714d820cb50c76086bc07aec055`  
Commit URL: https://github.com/tensai-app/llama.kt/commit/d3c306d60007a714d820cb50c76086bc07aec055

Biblioteca Kotlin/JNI basada en llama.cpp. Carga GGUF directamente desde Android y expone una API Kotlin para cargar/liberar modelos, formatear chat, generar tokens en streaming, interrumpir inferencia y configurar contexto, hilos, capas GPU y KV cache.

El README declara:
- Android 10 o posterior y ABI `arm64-v8a`.
- NDK r27+, JDK 21, Android SDK 35.
- CPU ARM64 como backend funcional.
- Vulkan validado por el autor en Mali-G68.
- OpenCL compilado, pero sin validación física Adreno en el estado documentado.
- Rendimientos publicados en un MediaTek Dimensity 900; no trasladables al Snapdragon 855.
- API de visión `mtmd` aún no conectada al API Kotlin.

**Por qué encaja:** es una biblioteca de inferencia, no una aplicación completa. Permite incorporar el motor a un proceso Android existente y evita obligatoriamente un servidor HTTP entre ROS 2 y el runtime. La integración concreta con ros2-android aún requiere una prueba de compatibilidad de build y empaquetado.

### Alternativas

| Proyecto | Tipo | Capacidades documentadas | Evaluación para este caso |
|---|---|---|---|
| [tensai-app/llama.kt](https://github.com/tensai-app/llama.kt) | Biblioteca Kotlin/JNI | GGUF, streaming, control del motor, CPU y Vulkan | **Primera opción** para integración embebida |
| [Kimi-syl/PocketLLM](https://github.com/Kimi-syl/PocketLLM) | Aplicación Android + core JVM | llama.cpp JNI, Vulkan, CPU dispatch, API OpenAI HTTP, MCP y agente | Alternativa si conviene conservar una API HTTP local |
| [dojekon/AIPaca](https://github.com/dojekon/AIPaca) | Aplicación Android | llama-server en foreground service, API OpenAI, perfiles CPU/OpenCL/Hexagon | Referencia útil de empaquetado y servicio; optimización NPU probada principalmente en SM8650 |
| [Aatricks/llmedge](https://github.com/Aatricks/llmedge) | Biblioteca Android | GGUF/JNI, chat, sesiones, STT/TTS, OCR, RAG y backends GPU experimentales | Candidato secundario; API en desarrollo temprano y alcance muy amplio |
| [alibaba/MNN](https://github.com/alibaba/MNN) | Runtime móvil general | Runtime nativo y despliegue Android para modelos compatibles | Investigar como línea de optimización; comprobar formato y arquitectura LFM2 antes de seleccionarlo |
| [mlc-ai/mlc-llm](https://github.com/mlc-ai/mlc-llm) | Compilador/runtime | Despliegue Android, compilación específica por modelo/dispositivo y API de servicio | Alternativa si se acepta preparar/compilar modelos para su runtime |
| [pytorch/executorch](https://github.com/pytorch/executorch) | Runtime edge | Runtime Android C++/Java/Kotlin y flujos LLM | Más transformación del modelo; no es el camino inmediato para reutilizar el GGUF |

La presencia de una función en el README no acredita compatibilidad con el Mi 9T Pro ni con el modelo concreto.

## 3. Plataforma y modelo objetivo

La campaña existente del teléfono está documentada en:
- [Experimento LFM2-2.6B Q4_K_M con llama.cpp](../devices/XIAOMI-MI-9T-PRO-LLAMA-CPP-LFM2-2.6B-20261123.md)
- [Matriz de runtimes](../devices/XIAOMI-MI-9T-PRO-RUNTIME-MATRIX.md)
- [Plan de pruebas](../devices/XIAOMI-MI-9T-PRO-TEST-PLAN.md)

Identidad de modelo ya registrada:
- Archivo: `LFM2-2.6B-Q4_K_M.gguf`
- SHA-256: `384bc877b6c37064982f96885bef69e4475919f5969218ed4e3b9399ae0340df`
- Arquitectura GGUF: `lfm2`
- Tamaño aproximado: 1.5 GiB.
- llama.cpp CPU: dos ejecuciones exploratorias, prompt 21.6/22.1 tok/s y generación 11.4/11.3 tok/s.
- Contexto ensayado: 512; dos hilos.
- No se demostró aceleración Adreno, Vulkan, OpenCL, Hexagon ni QNN.

Estos resultados son línea base histórica, no promesa de rendimiento para llama.kt. La compatibilidad del soporte LFM2 debe comprobarse contra el commit concreto de llama.cpp incorporado por llama.kt.

## 4. Arquitectura propuesta

### Opción A — motor embebido en el proceso Android (preferida)

```text
Android / Mi 9T Pro
┌───────────────────────────────────────────────────────────┐
│ Aplicación Android / ROS 2 Android                       │
│                                                           │
│  ROS 2 nodes & sensors       Kotlin LLM service            │
│  camera / IMU / GNSS         llama.kt                      │
│       │                      JNI → llama.cpp              │
│       └──────────┬───────────┘       │                     │
│                  │                   GGUF LFM2-2.6B         │
│                  └──── llm_ros_bridge ──────┘              │
│                          │                                │
│             intent schema + policy/safety gate             │
└──────────────────────────┬────────────────────────────────┘
                           │ ROS 2 / micro-ROS
                           ▼
                    ESP32 → motor driver
```

Ventajas:
- No requiere Termux, proot ni un proceso servidor separado.
- Evita HTTP/loopback para la comunicación interna entre ROS y el motor.
- Permite controlar explícitamente la carga, descarga, cancelación y serialización de inferencia.
- Reduce la superficie de red y simplifica el ciclo de vida.

Riesgos/condiciones:
- ros2-android debe permitir añadir un módulo Kotlin/JNI o un servicio equivalente sin romper su build.
- Hay que comprobar que el runtime y ROS 2 usan NDK/STL/ABI compatibles y que no colisionan bibliotecas nativas.
- La inferencia no debe ejecutarse en el hilo principal ni bloquear el executor ROS 2.
- La app debe controlar ciclo de vida, servicio en primer plano si procede, restricciones de batería y recuperación ante presión de memoria.
- Debe existir una política de exclusión mutua: una inferencia a la vez, cancelación y límites temporales.

### Opción B — runtime Android con API HTTP local

PocketLLM o AiPaca pueden servir como referencia para una API OpenAI-compatible dentro del teléfono. ROS 2 consumiría `127.0.0.1` mediante HTTP.

Ventajas:
- Interfaz desacoplada y fácilmente sustituible.
- Facilita clientes externos y herramientas que ya hablan OpenAI API.
- Permite reiniciar el runtime sin reiniciar necesariamente los nodos ROS 2.

Costes:
- Dos procesos/app y gestión de ciclo de vida.
- Autenticación, permisos de red local, cleartext/TLS, disponibilidad del servicio y límites Android.
- Más copias/serialización y más puntos de fallo.
- El acceso loopback entre aplicaciones debe verificarse en Android real.

No elegir esta opción solo por disponer de una API OpenAI: el puente interno puede invocar una interfaz Kotlin directa y exponer HTTP únicamente si después se necesita para clientes externos.

## 5. Seguridad del robot

El LLM no debe publicar directamente comandos de motores. Su salida debe ser una intención declarativa validada, por ejemplo:

```json
{
  "intent": "move",
  "direction": "forward",
  "speed": 0.05,
  "duration_ms": 300
}
```

El controlador ROS 2 valida esquema, rangos, duración, estado del robot, autorización y caducidad antes de generar `/cmd_vel`. El nodo LLM debe operar inicialmente en modo read-only y luego con actuadores simulados.

La documentación del robot advierte que `/cmd_vel` puede mover el ESP32 cuando existe conexión con Agent; no debe tratarse como un topic inocuo. El watchdog documentado de 300 ms es una protección de software, no una garantía de parada mecánica. Las primeras pruebas físicas requieren ruedas elevadas, supervisión, parada física accesible y aislamiento de publicadores.

## 6. Plan de trabajo por gates

| Gate | Trabajo | Evidencia requerida | Estado |
|---|---|---|---|
| G0 | Fijar revisión de llama.kt y auditar licencia, submódulos, llama.cpp, ABI, NDK y build | Commit SHA, árbol de dependencias, licencia y configuración nativa | Parcial: commit de main registrado; auditoría completa pendiente |
| G1 | Confirmar soporte de arquitectura LFM2 en la revisión de llama.cpp usada | Código upstream, build y test de carga del GGUF | Pendiente |
| G2 | Crear APK mínimo Kotlin/JNI sin ROS 2 | APK instalable, carga/descarga, prompt fijo, salida íntegra y logs | Pendiente |
| G3 | Ejecutar en Mi 9T Pro | Identidad del dispositivo, memoria pico, temperatura, rendimiento y estabilidad | Pendiente — requiere teléfono |
| G4 | Integrar el runtime con ROS 2 Android | Build reproducible, lifecycle, concurrencia y test ROS sin actuadores | Pendiente |
| G5 | Conectar el puente a ESP32 en modo observación | Topics y heartbeat documentados; cero publicaciones de movimiento | Pendiente |
| G6 | Simulación de intenciones y gate de seguridad | Pruebas de esquema, límites, timeout, desconexión y cancelación | Pendiente |
| G7 | Pruebas físicas controladas | Protocolo de seguridad, parada física y evidencia de pruebas | Pendiente |

### Protocolo mínimo de medición

Repetir con el mismo GGUF y prompt de referencia, registrando:
- SHA-256 del modelo, commit del runtime y revisión exacta de llama.cpp.
- Android build, ABI, NDK, backend real, hilos, contexto, batch y KV cache.
- Tiempo de carga, TTFT, prefill tok/s, decode tok/s, latencia entre tokens.
- RSS/PSS y máximo de memoria del proceso; memoria global y swap antes/durante/después.
- Temperaturas por zona con identificación prudente, frecuencias y señales de throttling.
- Duración sostenida, errores, cancelación, recuperación y estabilidad.
- Hashes de logs y resultados exportados.

No comparar directamente métricas de README de otros SoC con resultados del Snapdragon 855.

## 7. Licencias y distribución

Antes de incorporar código o binarios:
- Registrar la licencia exacta y sus obligaciones para cada dependencia.
- llama.kt declara licencia MIT en su repositorio (verificar archivo LICENSE en el gate G0).
- AiPaca declara GPL-3.0-or-later; su adopción podría imponer obligaciones de distribución incompatibles con una integración cerrada.
- Revisar licencias de llama.cpp, submódulos y dependencias nativas; no inferir la licencia del conjunto a partir del wrapper.
- No copiar bibliotecas compiladas ni binarios propietarios de Qualcomm/Hexagon sin comprobar redistribución.

## 8. Decisión provisional

**Seleccionado para prototipo:** `tensai-app/llama.kt`, por ser una biblioteca Kotlin/JNI con GGUF y API de inferencia embebida, que puede evitar Termux y el servidor HTTP intermedio.

**No seleccionado todavía como runtime de producción:** no hay prueba de que el commit auditado cargue LFM2-2.6B en el Mi 9T Pro, ni de que su integración con ROS 2 Android sea compatible.

**Alternativas conservadas:** PocketLLM para API OpenAI local; AiPaca como referencia de servicio foreground y gestión del motor; llmedge, MNN y MLC-LLM para evaluación secundaria.

La decisión se revisará después de G0–G3. Si LFM2 no está soportado por la revisión de llama.cpp de llama.kt, no se debe parchear a ciegas: comparar actualización del submódulo, portabilidad del soporte LFM2 y coste de mantener un fork.

## 9. Fuentes primarias

- llama.kt: https://github.com/tensai-app/llama.kt
- llama.kt commit fijado: https://github.com/tensai-app/llama.kt/commit/d3c306d60007a714d820cb50c76086bc07aec055
- PocketLLM: https://github.com/Kimi-syl/PocketLLM
- AiPaca: https://github.com/dojekon/AIPaca
- llmedge: https://github.com/Aatricks/llmedge
- MNN: https://github.com/alibaba/MNN
- MLC-LLM: https://github.com/mlc-ai/mlc-llm
- ExecuTorch: https://github.com/pytorch/executorch
- ros2-android: https://github.com/kishore-saravanan/ros2-android
- Campaña LFM2-2.6B del Mi 9T Pro: ../devices/XIAOMI-MI-9T-PRO-LLAMA-CPP-LFM2-2.6B-20261123.md

---
**Registro HDAE:** prospección documental y selección provisional. No se ha instalado, compilado ni ejecutado ninguno de estos motores en el teléfono durante esta tarea. La aceptación técnica queda condicionada a los gates descritos.
