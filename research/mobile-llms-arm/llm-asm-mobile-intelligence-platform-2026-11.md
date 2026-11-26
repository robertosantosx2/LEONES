# llm.asm Mobile Intelligence Platform — investigación de Linux móvil y bare metal ARM64

**Fecha de consolidación:** 2026-11-26  
**Línea LEONES:** [Mobile-LLMs-ARM](../../docs/subprojects/Mobile-LLMs-ARM/README.md)  
**Proyecto de referencia:** [alesha-pro/llm.asm](https://github.com/alesha-pro/llm.asm)  
**Estado:** investigación documental consolidada; arquitectura propuesta; validación física y prototipo ARM64 bare metal pendientes.

## 1. Resumen ejecutivo

Esta investigación evalúa cómo reutilizar teléfonos Android comercializados entre 2015 y 2022 (con variantes de al menos 2 GB de RAM) como nodos de inferencia, percepción y actuación. Se estudian dos vías distintas:

1. **Linux ARM64 sobre el hardware del teléfono:** arrancar una distribución móvil o un Linux adaptado al dispositivo, aprovechando el kernel y sus controladores.
2. **Bare metal ARM64:** arrancar un runtime/kernel propio sin ejecutar Linux o Android como sistema operativo anfitrión. Esto exige desarrollar una plataforma de bajo nivel específica para ARM64 y para cada familia de SoC.

La conclusión principal es que la vía Linux móvil es el camino práctico para obtener pronto inferencia, sensores, red y servicios. Bare metal es una línea de investigación de largo plazo, útil para estudiar un runtime mínimo y control directo del hardware, pero no debe confundirse con una simple recompilación ARM del kernel x86-64 existente.

El resultado estratégico es una arquitectura común —**llm.asm Mobile Intelligence Platform (MIP)**— con contratos compartidos para inferencia, sensores, agentes y API, y dos backends de plataforma: Linux ARM64 y bare metal ARM64.

## 2. Alcance y fuentes primarias

### 2.1 llm.asm

- Repositorio: https://github.com/alesha-pro/llm.asm
- PR #1, «Add native ARM64 Qwen3 inference with OpenCode and Metal»: https://github.com/alesha-pro/llm.asm/pull/1
- Árbol bare metal x86-64: https://github.com/alesha-pro/llm.asm/tree/main/02-baremetal-os

El repositorio separa tres líneas: inferencia Qwen3 en Linux x86-64, un sistema bare metal x86-64 y un entrenador Mini-GPT. El subproyecto `02-baremetal-os` demuestra una ruta bare metal sobre x86-64: arranque Multiboot, transición a long mode, memoria/paginación, interrupciones, SMP y dispositivos básicos. Su modelo se carga desde almacenamiento externo y el sistema proporciona memoria de trabajo y caché KV.

**Límite importante:** los resultados de rendimiento publicados para ese kernel corresponden a plataformas x86-64 de servidor/virtualización. No son una predicción válida para un teléfono ARM. La arquitectura, el ancho de banda, los controladores, la memoria disponible y la gestión térmica son diferentes.

### 2.2 PR #1: alcance real y límites

El PR #1 introduce una ruta de inferencia ARM64 para Qwen3, con NEON como backend CPU, un backend Metal experimental para Apple, un worker persistente y un servidor con API compatible con OpenAI. También adapta las llamadas de herramientas de Qwen al formato que espera OpenCode.

La revisión observada durante esta investigación lo mostraba como **Draft**, sin que se deba interpretar como mergeado o aceptado. El PR aporta una separación de responsabilidades valiosa entre motor, worker, servidor y cliente/agente.

Metal es una API de Apple y no es trasladable directamente a Android. Para Android/Linux ARM64 habrá que evaluar NEON, Vulkan Compute, OpenCL y, cuando proceda, SDK propietarios del fabricante (DSP/NPU). El PR ARM64 de inferencia tampoco constituye por sí mismo un port de `02-baremetal-os`: son dos trabajos diferentes.

## 3. Dos modelos de ejecución

| Dimensión | Linux móvil ARM64 | Bare metal ARM64 |
|---|---|---|
| Arranque | Bootloader del fabricante + kernel Linux adaptado | Boot chain del fabricante + kernel/runtime propio |
| Drivers | Reutiliza drivers del kernel cuando existen | Requiere drivers propios o interfaces firmware específicas |
| CPU | NEON y extensiones disponibles | NEON y extensiones disponibles, con inicialización propia |
| GPU/NPU | Posible mediante drivers/API disponibles | Extremadamente complejo; depende de firmware y documentación |
| Sensores | IIO, input, V4L2, ALSA, GPS y APIs del sistema según soporte | I2C/SPI/GPIO/DMA y drivers propios |
| Cámara | V4L2/libcamera cuando el ISP está soportado | ISP, MIPI CSI-2, DMA y firmware: dificultad extrema |
| Red | Stack Linux y drivers existentes | TCP/IP, Wi-Fi/BT y seguridad por implementar o portar |
| Viabilidad inicial | Media, muy dependiente del modelo | Baja para teléfono real; razonable empezar en QEMU |
| Uso recomendado | Prototipos y nodos de inferencia/percepción | Investigación de kernel mínimo y runtime especializado |

En teléfonos comerciales, «bare metal» no significa eliminar Boot ROM, firmware del fabricante, TrustZone o el cargador inicial. Significa ejecutar nuestro propio entorno como sistema operativo principal después de la cadena de arranque permitida por el dispositivo. El desbloqueo del bootloader y las políticas de Verified Boot pueden impedirlo.

## 4. Ecosistema Linux móvil y experiencias relacionadas

### 4.1 Distribuciones y plataformas

- [postmarketOS](https://github.com/postmarketOS) y su [wiki de dispositivos](https://wiki.postmarketos.org/wiki/Devices): referencia principal para Linux móvil; el soporte se debe comprobar por variante exacta.
- [Mobian](https://github.com/mobian-project): Debian para dispositivos móviles compatibles.
- [UBports / Ubuntu Touch](https://github.com/ubports): plataforma móvil Linux basada en Ubuntu.
- [Linux kernel](https://github.com/torvalds/linux), [U-Boot](https://github.com/u-boot/u-boot) y [ARM Trusted Firmware](https://github.com/ARM-software/arm-trusted-firmware): componentes de referencia de bajo nivel.

La compatibilidad debe registrarse por función, no como una etiqueta binaria «soportado». Que el teléfono arranque no implica que cámara, audio, GPS, módem, Wi-Fi, Bluetooth, acelerómetros o suspensión estén operativos. La presentación FOSDEM «Kernel support for Mobile Linux: The missing 20%» ilustra esta fragmentación por dispositivo: https://fosdem.org/2025/schedule/event/fosdem-2025-xxxxx/

### 4.2 Experimentos relevantes

- **Samsung Galaxy S9 Exynos / postmarketOS:** https://github.com/philipplinux/s9-postmarketos  
  Experimento headless con red, SSH, dashboard, gestión térmica y ejecución de llama.cpp en CPU. El autor informa alrededor de 5 tok/s en una configuración concreta; no es una medición comparable con otros dispositivos. La cámara no estaba operativa en el estado documentado y otras funciones seguían sin probar.
- **OnePlus 6 / 6T:** los avances de Linux muestran que llamadas, red, sensores, audio y cámara requieren trabajo independiente y que el estado puede variar por kernel y variante. Referencia comunitaria: https://www.reddit.com/r/oneplus/comments/l1ne81/

Estos ejemplos prueban que un teléfono antiguo puede convertirse en un nodo Linux útil, pero también que el soporte de periféricos es el principal coste de ingeniería.

## 5. Dispositivos candidatos para un banco de pruebas

La siguiente selección es una lista de candidatos técnicos, no un ranking de ventas ni una afirmación de que todos tengan soporte Linux completo. RAM, SoC y disponibilidad de desbloqueo varían por SKU y región.

| Dispositivo/familia | Plataforma | Motivo de interés | Riesgo/limitación |
|---|---|---|---|
| Poco F1 | Snapdragon 845; variantes habituales de 6 GB | Buen candidato Qualcomm para NEON, Vulkan y experimentación | Verificar estado real de port, cámara y bootloader |
| OnePlus 6/6T | Snapdragon 845; 6/8 GB | Contraste con experiencias de Linux móvil | Soporte desigual de periféricos |
| Samsung Galaxy S9 | Exynos 9810 en SM-G960F; 4 GB | Existe experimento postmarketOS identificable | Diferencias Exynos/Snapdragon y cámara |
| Google Pixel 3a | Snapdragon 670; 4 GB | Plataforma ARM relativamente documentada | Confirmar soporte de cada periférico |
| Samsung Galaxy S21 | Exynos 2100 o Snapdragon 888; 8 GB en variantes comunes | Objetivo avanzado para aceleradores y rendimiento | Complejidad de firmware, drivers y variante |

Para el inventario histórico de 2015–2022 pueden añadirse familias Galaxy S/A, Redmi/Redmi Note, Mi, OnePlus, Moto y LG. No se recomienda seleccionar únicamente por RAM: importan bootloader desbloqueable, soporte de kernel, documentación del SoC, almacenamiento, batería, refrigeración y disponibilidad de repuestos.

## 6. El teléfono como plataforma de percepción y robótica

El valor diferencial del móvil no es sólo ejecutar un LLM: incorpora cámara, micrófonos, IMU, GNSS, magnetómetro, barómetro y conectividad. Esos sensores pueden convertirlo en un nodo de percepción para robots, sistemas distribuidos y automatización.

### 6.1 Proyectos de referencia

| Proyecto | Repositorio | Aportación |
|---|---|---|
| ROS2 Android | https://github.com/kishore-saravanan/ros2-android | ROS 2 nativo en Android y exposición de sensores/cámaras a nodos ROS |
| ROS2 Phone Sensors | https://github.com/vtalpaert/ros2-phone-sensors | Puente de GPS, IMU, cámara y WebSocket hacia ROS |
| ROS2 Mobile Sensor Bridge | https://github.com/VedantC2307/ros2-mobile-sensor-bridge | Cámara, pose, audio, GPS, IMU y WebXR |
| Roboception | https://github.com/ramessri/roboception | Fusión de cámara, micrófono e IMU con modelos ONNX y ROS2 |
| RIO ROS2 | https://github.com/botforge-robotics/rio_ros2 | Interfaces de sensores móviles y actuadores/ESP32 |
| CellBot | https://github.com/PerinTumfo/CellBot | Cámara, IMU y GPS del teléfono conectados a PC y microcontroladores |
| Android DVS EdgeAI | https://github.com/JiaxuanJin/Android-DVS-EdgeAI-Vision-System | Análisis de movimiento y visión edge desde cámara e IMU |
| CHRONYX CORE | https://github.com/Sherin-SEF-AI/CHRONYX-CORE | Captura sincronizada de cámara, IMU, GNSS y micrófono con reloj monotónico y MCAP |
| Old Phone CCTV | https://github.com/AmitSaha9928/old-phone-cctv | Reutilización de móviles como cámaras de vigilancia con detección y alertas |

Los proyectos son referencias externas y sus descripciones no implican que LEONES los haya instalado, auditado o reproducido. La sincronización temporal de CHRONYX es especialmente relevante: los eventos de cámara, IMU, GNSS y audio deben compartir una base temporal monotónica, registrar incertidumbre/desfase y preservar timestamps originales.

### 6.2 Casos de uso potenciales

1. **Centinela local:** detección de movimiento/personas, eventos de audio, grabación y alertas sin enviar continuamente vídeo a la nube.
2. **Cerebro de robot:** cámara + IMU + GNSS para percepción, localización y planificación; ESP32 u otro microcontrolador ejecuta actuadores.
3. **Inspector industrial:** visión, OCR y análisis de vibración/sonido para inspección y mantenimiento.
4. **Estación ambiental:** sensores internos y externos, GNSS y registro temporal.
5. **Asistente offline:** voz, OCR, traducción y consulta local en situaciones sin conectividad.
6. **Nodo de emergencia:** comunicaciones locales, mapas, registro de incidencias y coordinación.
7. **Red distribuida de teléfonos:** nodos especializados de cámara, audio, inferencia o gateway coordinados por REDIL.

No se debe enviar cada fotograma al LLM. El pipeline debe usar detectores, OCR, ASR y estimadores especializados; el LLM recibe eventos, resúmenes y contexto temporal para razonar y planificar.

## 7. Arquitectura propuesta: Mobile Intelligence Platform (MIP)

### 7.1 Componentes lógicos

- `mobile-boot`: descubrimiento de plataforma, arranque y capacidades.
- `mobile-hal`: abstracción de CPU, memoria, temporizadores, sensores y aceleradores.
- `mobile-memory`: asignación, buffers, límites y presión de memoria.
- `mobile-sensors`: IMU, GNSS, magnetómetro, barómetro y sensores externos.
- `mobile-camera`: captura, buffers, timestamps, ISP y transporte de imágenes.
- `mobile-audio`: captura/reproducción, VAD, ASR y TTS.
- `mobile-fusion`: sincronización y fusión multimodal.
- `mobile-inference`: runtime LLM/VLM y modelos especializados.
- `mobile-agent`: planificación y uso de herramientas con permisos explícitos.
- `mobile-api`: API local compatible con OpenAI donde proceda.
- `mobile-network`: descubrimiento y comunicación entre nodos.
- `mobile-power`: telemetría térmica, energía, carga y throttling.

### 7.2 Backends de plataforma

**Backend Linux ARM64**

- Kernel y drivers del dispositivo.
- NEON para inferencia CPU.
- Vulkan/OpenCL/NNAPI o SDK del fabricante cuando estén realmente disponibles.
- V4L2/libcamera para cámara; ALSA/PulseAudio/PipeWire para audio según sistema; IIO/input y servicios GPS según soporte.
- Servicio local y adaptador de API.

**Backend bare metal ARM64**

- Inicialización de CPU, MMU, excepciones, temporizadores e interrupciones.
- Gestor de memoria, allocator, scheduler y sincronización SMP.
- UART primero; después GPIO, I2C, SPI y DMA.
- Runtime de inferencia NEON y API/transportes mínimos.
- Drivers de cámara, GPU, Wi-Fi y DSP sólo tras disponer de especificaciones/firmware y una plataforma concreta.

Los contratos de inferencia, mensajes, eventos, API y agente deben compartirse. El HAL y los drivers son específicos del backend.

### 7.3 Contratos de datos

Un evento de sensor debería contener al menos:

- `device_id`, `sensor_id`, `sequence`
- timestamp monotónico y dominio de reloj
- tipo, unidad y valores normalizados
- incertidumbre/calidad de la medida
- metadatos de calibración y orientación

Los fotogramas y buffers de audio no deben transportarse como grandes cadenas JSON. Se usarán referencias a buffers, memoria compartida o DMA cuando la plataforma lo permita, con metadatos y timestamps fuera de banda.

## 8. Memoria, modelos y rendimiento

Los perfiles deben reservar memoria para el sistema, buffers de cámara/audio, runtime, pesos y KV cache. La RAM nominal no equivale a RAM libre para inferencia.

- **2–4 GB:** modelos muy compactos, contextos modestos y concurrencia limitada; mantener percepción especializada ligera.
- **6–8 GB:** mayor margen para modelos compactos, contexto y servicios concurrentes, sujeto al sistema y a la cuantización.
- **Más memoria:** permite explorar VLM y pipelines más complejos, pero no elimina límites térmicos ni de ancho de banda.

La primera ruta de inferencia debe ser NEON/CPU para establecer un baseline reproducible. A continuación se compararán backends GPU/NPU por dispositivo. Deben medirse por separado TTFT, prefill, decode sostenido, RAM máxima, energía/token, temperatura, throttling, calidad de tarea y recuperación térmica. Los resultados de terceros no se incorporarán como mediciones LEONES.

## 9. Roadmap de prototipado

| Gate | Objetivo | Evidencia de salida |
|---|---|---|
| M0 — Revisión ARM64 | Auditar PR #1, fijar commit y validar builds/tests | SHA, logs, tests, limitaciones y estado de PR |
| M1 — QEMU bare metal | Crear arranque AArch64, UART, excepciones, MMU y allocator | Imagen reproducible y logs seriales |
| M2 — Inferencia ARM64 Linux | Compilar NEON y servidor API en dispositivo Linux/Android compatible | Comandos, hashes, API smoke test y benchmark |
| M3 — Sensores Linux | Captura IMU/GNSS/audio y cámara donde haya soporte | Timestamps, unidades, muestras y matriz de soporte |
| M4 — Fusión multimodal | Sincronizar eventos y registrar MCAP | Dataset corto reproducible y validación de desfases |
| M5 — Agente edge | LLM consume eventos y solicita acciones con aprobación | Casos de prueba, permisos y trazas |
| M6 — Bare metal progresivo | Añadir inferencia y drivers por fases sobre QEMU y placa ARM64 | Tests de host/QEMU y evidencia por periférico |
| M7 — Port a teléfono | Elegir SKU desbloqueable con documentación y soporte | Boot reproducible y matriz de periféricos |
| M8 — REDIL móvil | Coordinar varios teléfonos y nodos externos | Latencia E2E, fallos, energía y trazas |

No comenzar por cámara/GPU bare metal. El orden recomendado es QEMU → UART → memoria/MMU → excepciones/timers → scheduler/SMP → runtime mínimo → inferencia CPU → placa ARM64 → teléfono específico.

## 10. Riesgos y criterios de aceptación

- **Fragmentación por SKU:** registrar modelo exacto, SoC, región, RAM, bootloader y revisión de placa.
- **Firmware propietario:** documentar procedencia, licencia y posibilidad real de redistribución.
- **Drivers incompletos:** medir por periférico; no inferir soporte general a partir del arranque.
- **Boot chain bloqueada:** no modificar bootloader/firmware sin una campaña autorizada y un procedimiento de recuperación.
- **Temperatura y batería envejecida:** pruebas sostenidas, límites de carga y apagado seguro.
- **Privacidad:** procesar localmente por defecto, minimizar retención y exigir consentimiento para captura/transmisión.
- **Fuentes sociales:** Reddit/X sirven como pistas de descubrimiento; no sustituyen repositorios, commits, documentación primaria o reproducción.

La aceptación de una plataforma requiere: identificación de hardware; fuente y commit fijados; build reproducible; prueba funcional; logs/artefactos; mediciones con protocolo; fallos y limitaciones registrados. Un prototipo QEMU no cuenta como port validado a teléfono.

## 11. Búsqueda comunitaria: GitHub, Reddit y X

Se localizaron repositorios GitHub y debates Reddit enlazados en las secciones anteriores. La búsqueda en X no produjo publicaciones específicas suficientemente accesibles y verificables para atribuirles afirmaciones concretas; por tanto, no se incorporan citas ni conclusiones atribuidas a X. La prospección futura debe registrar URL, fecha, autor, commit/release y estado de verificación.

## 12. Encaje en LEONES

- **Mobile-LLMs-ARM:** línea de investigación y catálogo de dispositivos/runtimes.
- **Atlas:** procedencia, identidad de modelos, dispositivos, licencias y fuentes.
- **NEPENTHES:** protocolo de rendimiento, memoria, energía, temperatura y trazas.
- **Router:** selección de runtime/modelo según SoC, RAM y aceleradores disponibles.
- **REDIL:** federación de teléfonos y nodos heterogéneos.
- **LEONES Lab Agent:** inventario y pruebas supervisadas con recibos y aprobación explícita.

Este documento es una investigación arquitectónica, no una declaración de que los proyectos citados estén integrados ni de que exista un kernel ARM64 bare metal funcional en teléfono. La siguiente entrega técnica debe ser una auditoría reproducible del PR ARM64 y un primer prototipo bare metal AArch64 en QEMU, manteniendo separadas ambas líneas.

## Referencias adicionales

- postmarketOS: https://github.com/postmarketOS
- postmarketOS devices: https://wiki.postmarketos.org/wiki/Devices
- Mobian: https://github.com/mobian-project
- UBports: https://github.com/ubports
- U-Boot: https://github.com/u-boot/u-boot
- Linux: https://github.com/torvalds/linux
- ARM Trusted Firmware: https://github.com/ARM-software/arm-trusted-firmware
- libcamera: https://libcamera.org/
- ROS 2: https://github.com/ros2/ros2
- PX4: https://github.com/PX4/PX4-Autopilot
