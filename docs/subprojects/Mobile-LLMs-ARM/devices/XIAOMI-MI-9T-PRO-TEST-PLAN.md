# Xiaomi Mi 9T Pro — plan de pruebas de inferencia

**Proyecto:** LEONES / Mobile-LLMs-ARM  
**Plataforma:** Xiaomi Mi 9T Pro, 6 GB RAM declarados  
**Estado:** PLANNED — no se han ejecutado pruebas físicas  
**Ruta de entrada:** Android sin root; root y cambios de sistema quedan fuera de alcance.

## 1. Objetivo verificable

Determinar qué modelos compactos y runtimes pueden ejecutar inferencia local reproducible en el Mi 9T Pro, caracterizando rendimiento, memoria, estabilidad térmica y consumo. Separar capacidades detectadas, compatibilidad documental, ejecución funcional y benchmark medido.

## 2. Datos iniciales y desconocidos

Conocido por declaración del usuario: modelo, 6 GB RAM y CPU octa-core hasta 2,84 GHz. Confirmado por captura «Sobre el teléfono» (2026-11-23): MIUI Global 12.0.5 Estable (`12.0.5.0(QFKEUXM)`), Android 10, build `QKQ1.190825.002`, parche de seguridad 2021-04-01 y almacenamiento de 128 GB con 55,2 GB ocupados (≈72,8 GB libres, calculado). Pendiente: API level, root, ABI, kernel, firmware, memoria realmente disponible, versión Vulkan/driver, estado de batería y temperatura.

El Snapdragon 855, Adreno 640 y Hexagon 690 son la plataforma esperada del modelo comercial, pero deben confirmarse en el propio terminal antes de seleccionar backends.

## 3. Invariantes y seguridad

1. Comenzar sin root y sin modificar bootloader, recovery, particiones, kernel, ROM o firmware.
2. No desbloquear bootloader ni instalar módulos privilegiados para esta campaña.
3. No instalar APKs ni binarios desde fuentes no verificadas; registrar URL, versión, hash y licencia.
4. No ejecutar descargas de modelos sin comprobar tamaño, espacio y hash.
5. Mantener el teléfono refrigerado de forma pasiva, sin congeladores ni métodos que produzcan condensación.
6. No cargar el teléfono durante las mediciones energéticas; para pruebas térmicas largas, documentar explícitamente el estado de carga.
7. No recoger IMEI, serial, MAC, cuentas ni tokens. Redactar identificadores únicos en logs.
8. Parar ante thermal status severo, apagados, reinicios, batería hinchada, temperatura anómala o degradación del sistema.
9. El teléfono no se usará como servidor de red expuesto. Cualquier API será loopback o LAN aislada y autenticada cuando proceda.
10. No atribuir al DSP/NPU operaciones que no estén demostradas por trazas/logs de backend.

## 4. Secuencia de gates

El orden de ejecución es de menor a mayor dificultad. La clasificación de rendimiento esperado se trata por separado en la matriz de runtimes; no es una promesa de resultados.

### G0 — Inventario no-root (muy fácil, P0)

Conectar ADB y capturar de forma redactada:
- `adb devices -l`
- `adb shell getprop ro.product.model`
- `adb shell getprop ro.product.device`
- `adb shell getprop ro.board.platform`
- `adb shell getprop ro.build.version.release`
- `adb shell getprop ro.build.version.sdk`
- `adb shell getprop ro.build.fingerprint` (redactar identificadores únicos si aparecen)
- `adb shell uname -a`
- `adb shell getprop ro.product.cpu.abi`
- `adb shell getprop ro.product.cpu.abilist`
- `adb shell cat /proc/meminfo`
- `adb shell df -h /data`
- `adb shell dumpsys battery`
- `adb shell dumpsys thermalservice` (si está disponible)
- `adb shell cmd package list packages` solo si resulta necesario; no volcar datos personales.

Registrar Android, API, ABI, kernel, RAM, espacio y thermal status. Root se detectará de forma no invasiva; no ejecutar su ni instalar root checker propietario. Si ADB no está disponible, usar Termux y registrar diferencias.

**Gate:** perfil físico mínimo completo; los campos no expuestos quedan UNKNOWN, no se adivinan.

### G1 — Preparación de entorno y smoke test (fácil, P0)

Preferir Termux oficial y paquetes disponibles en sus repositorios, o un APK verificable de runtime. Registrar versión de Termux, Android ABI y origen de cada paquete. No depender de proot para el primer benchmark si existe binario ARM64 nativo.

Verificar:
- ejecución de un binario ARM64 inocuo;
- acceso a almacenamiento compartido solo si se concede permiso;
- memoria y límites de proceso;
- posibilidad de mantener pantalla/proceso activo sin cambiar políticas del sistema;
- integridad SHA-256 de binarios y modelos.

**Gate:** entorno reproducible, salida y códigos de retorno conservados.

### G2 — Baseline llama.cpp CPU con modelo ultracompacto (fácil-media, P0)

Runtime inicial: llama.cpp ARM64 CPU, sin GPU offload. Usar un GGUF pequeño y con licencia/model card revisadas. Orden sugerido:
1. SmolLM2-360M-Instruct en cuantización GGUF compatible, si existe artefacto verificado.
2. Qwen2.5-0.5B-Instruct GGUF Q4_K_M.
3. Qwen3-0.6B GGUF compatible, solo tras verificar disponibilidad, tokenizer y soporte de arquitectura en la versión fijada de llama.cpp.

No asumir que todos los modelos tienen GGUF oficial ni que el runtime soporta cualquier arquitectura. Fijar commit/binario y hash exacto del modelo.

Medir primero con prompt y salida cortos, contexto 512, batch conservador y un hilo; después 2, 4 y hasta 6 hilos, sin forzar los ocho núcleos a ciegas.

**Gate:** completar 5 repeticiones medidas tras warm-up, sin OOM/crash, con prompt y salida verificables.

### G3 — Afinado CPU y memoria (media, P0)

Barrido controlado:
- threads: 1, 2, 4, 6; 8 solo como experimento separado;
- afinidad/clústeres solo si se pueden identificar de forma fiable sin root;
- contextos: 512, 1024 y 2048, sujeto a memoria;
- cuantización y tamaño de modelo;
- batch/ubatch compatibles con la versión fijada;
- memoria máxima del proceso y memoria global disponible.

No variar varias dimensiones simultáneamente. Restablecer estado térmico entre series.

**Gate:** configuración ganadora definida por rendimiento sostenido y estabilidad, no solo pico de tokens/s.

### G4 — Escalado de modelos (media, P0/P1)

Escalar gradualmente: 0.5B → 0.6B → 1B/1.5B → 1.7B → 3B exploratorio. Para cada salto, estimar tamaño en disco y memoria de runtime antes de descargar. No iniciar 3B si el margen de RAM observado no es suficiente.

Modelos candidatos (no aprobados hasta verificar artefacto): Qwen2.5-1.5B-Instruct, Qwen3-1.7B, Llama 3.2-1B/3B y SmolLM2-1.7B. Mantener la misma tarea de evaluación y controlar tokenizer/plantilla de chat.

**Gate:** límite superior de tamaño/contexto que el dispositivo sostiene sin degradación crítica.

### G5 — GPU Adreno / Vulkan (media-alta, P1)

1. Inventariar Vulkan y driver.
2. Verificar que el binario/ruta seleccionada incluye backend Vulkan para Android/ARM64.
3. Ejecutar smoke test de backend.
4. Comparar CPU vs Vulkan con el mismo GGUF, contexto, prompt, generación, runtime commit y condiciones térmicas.
5. Barrer capas GPU de forma incremental y conservar logs.

No inferir que Vulkan disponible equivale a backend LLM funcional. No comparar cifras con configuraciones distintas.

**Gate:** mejora reproducible en una métrica acordada sin regresión inaceptable en memoria, estabilidad o energía.

### G6 — ExecuTorch / XNNPACK y LiteRT (alta, P1/P2)

Evaluar modelos y formatos oficialmente soportados por la versión elegida. Registrar delegados efectivos y particiones ejecutadas; la mera inicialización de XNNPACK/LiteRT no demuestra que el grafo completo use el backend.

Comparar latencia de inicialización, memoria, TTFT/latencia equivalente, throughput y calidad. Mantener el mismo hardware y protocolo.

**Gate:** inferencia real repetida y evidencia del backend usado.

### G7 — MLC LLM y aceleración Android (alta, P2)

Comprobar matriz actual de dispositivos/ABI/Android, toolchain, artefactos y soporte Vulkan. Compilación remota o cruzada antes de instalar. No invertir en una cadena que no declare compatibilidad con Adreno 640/Android detectado.

**Gate:** app/runtime instala y ejecuta localmente, con logs de backend y benchmark comparable.

### G8 — Qualcomm QNN / Hexagon 690 (muy alta, P2 exploratoria)

Primero revisar la matriz oficial de SoC/SDK y requisitos de firmware, Android y DSP. Determinar si el SDK disponible soporta específicamente Snapdragon 855/SM8150 y si el modelo/operadores elegidos están soportados.

Distinguir:
- librería instalada;
- dispositivo enumerado;
- sesión QNN creada;
- grafo particionado;
- operadores ejecutados en HTP/DSP;
- inferencia completa y repetible.

No desbloquear bootloader ni flashear firmware para intentar habilitar soporte. Si el Snapdragon 855 no está soportado por la versión del SDK, documentar el no-go con fuente y versión.

**Gate:** evidencia inequívoca de ejecución de operadores en el acelerador y resultado medido.

### G9 — Servicio local y REDIL (muy alta, P2)

Solo después de validar un runtime estable:
- API local compatible si el runtime lo permite;
- bind a loopback por defecto;
- acceso LAN opcional con autenticación, firewall y red de pruebas;
- health check, cola, límite de memoria y apagado seguro;
- latencia extremo a extremo y disponibilidad térmica;
- comparación inferencia local vs delegación al MSI.

No hacer particionado de capas/modelos entre dispositivos hasta demostrar que la transferencia no anula la ganancia.

**Gate:** nodo REDIL estable en sesión limitada, documentado y apagable.

## 5. Métricas obligatorias

- TTFT o tiempo hasta primera salida.
- Prefill tokens/s cuando la interfaz permita medirlo de forma válida.
- Decode tokens/s e ITL cuando haya streaming/token timestamps.
- Latencia total y tokens generados.
- RSS/peak RSS del proceso y memoria disponible del sistema.
- Temperatura/thermal status antes, durante y después.
- Estado y nivel de batería; energía solo si existe fuente de medida válida.
- Errores, OOM, reinicios, throttling y duración.
- Calidad: exactitud/criterio de tarea, idioma y cumplimiento de formato.

No presentar consumo mWh ni J/token si no existe medición energética física calibrada. Si solo hay variación de batería, etiquetarla como proxy de baja resolución, no energía medida.

## 6. Política de rendimiento esperado

No asignar cifras ni ordenar backends por tokens/s antes de medir. Hipótesis inicial: CPU llama.cpp es la ruta con mayor probabilidad de éxito; XNNPACK puede ser competitivo; Vulkan/MLC depende de driver y kernels; QNN/Hexagon es una incógnita de compatibilidad. El orden final se determinará por resultados sostenidos, memoria, energía y calidad.

## 7. Evidencias a archivar

Por ejecución:
- manifest JSON con schema_version y run_id;
- perfil de hardware y estado del sistema;
- runtime, commit/build, flags y backend efectivo;
- modelo, repositorio, revisión, licencia, archivo y SHA-256;
- prompt fixture versionado, tokens de entrada/salida y plantilla;
- warm-up y repeticiones;
- logs completos, resultados JSONL/CSV y checksums;
- estado térmico y batería;
- no-resultados y causas.

Estados: PLANNED → DISCOVERED → COMPATIBLE → REPRODUCED → MEASURED → REVIEWED. No saltar estados. El estado MEASURED requiere artefactos físicos identificados.

## 8. Checkpoint y parada

**Checkpoint actual:** captura visual recibida: Android 10 y MIUI Global 12.0.5 confirmados; almacenamiento ≈72,8 GB libre calculado. Falta inventario ADB/Termux para ABI, API level, SoC/board, kernel, memoria disponible y estado térmico. Root permanece UNKNOWN y no bloquea G0-G4. Revisar compatibilidad de runtime y modelos antes de descargar o instalar.

**Condición de parada:** inventario suficiente para seleccionar un binario ARM64 y un primer modelo GGUF con procedencia/hash; detenerse antes de instalación/descarga si hay incompatibilidad, poco espacio efectivo, riesgo térmico o necesidad de privilegios.


## 8.1 Checkpoint físico actualizado — 2026-11-24

G0 queda parcialmente completado con inventario Termux/SSH sin root:
- SoC Qualcomm SM8150 / plataforma msmnile confirmados por /proc/cpuinfo y getprop.
- Android 10 / API 29; ABI arm64-v8a; ocho CPU lógicas y máximos por CPU registrados en el perfil de hardware.
- RAM total 5.636.076 kB; disponible 2.712.940 kB en la instantánea; swap 2.621.436 kB total y 1.737.772 kB libre.
- /data: 62G disponibles.
- Batería: 80 %, salud GOOD, 23,5 °C, descargando.
- Sensores CPU/GPU y batería plausibles registrados; sensores con lecturas centinela o semántica desconocida excluidos. dumpsys thermalservice no devolvió datos visibles.
- ro.hardware.egl=adreno, OpenGL ES 3.2 y nodo /dev/kgsl-3d0 presentes; esto no acredita backend GPU de Termux. Vulkan y aceleración Adreno siguen sin verificar.
- Root permanece UNKNOWN; no se ha solicitado ni utilizado.

**Próximo gate:** G1 — verificar herramientas disponibles y elegir un artefacto llama.cpp ARM64 reproducible. Antes de instalar/compilar o descargar un modelo, comprobar compatibilidad Android/Termux, tamaño, hash y memoria. La primera ejecución seguirá siendo CPU-only y con modelo ultracompacto; Qwen2.5-Coder-3B no se utilizará como primer smoke test.
