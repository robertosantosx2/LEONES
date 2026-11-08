# REDIL — Investigación: manadas PC, manadas Android y federación de servicios

**Documento:** REDIL-investigacion  
**Estado:** propuesta de arquitectura e investigación; pendiente de prototipo y validación física.  
**Fecha:** 8 de noviembre de 2026  
**Proyecto:** LEONES → REDIL (Red distribuida de Inteligencia Artificial Local)

> Desarrolla las dos plataformas de nodos —ordenadores sin GPU dedicada y teléfonos Android— y su organización como manadas (clusters locales) que se federan para formar REDIL. Las topologías, presupuestos y rutas API son propuestas, no capacidades ya implementadas.

## 1. Resumen ejecutivo

REDIL debe organizarse en tres niveles:

1. **Dispositivo/nodo:** PC o teléfono que aporta recursos y ejecuta uno o varios motores/modelos.
2. **Manada:** conjunto coordinado de nodos que ofrece uno o varios servicios mediante una API local.
3. **REDIL federado:** conjunto de manadas que registran capacidades para que un plano de control común enrute trabajos entre ellas.

Dos líneas complementarias:

- **REDIL-PC:** ordenadores sin GPU dedicada, preferentemente Linux, que ejecutan inferencia CPU y servicios auxiliares. La primera referencia es Ubuntu Server mínimo; Buildroot o Yocto se estudiarán tras validar hardware, drivers y mantenimiento.
- **REDIL-ANDROID:** teléfonos Android que aportan CPU, GPU móvil y, cuando exista soporte real del fabricante/runtime, NPU/DSP. Se gestionan mediante una aplicación/servicio Android, no como servidores Linux convencionales.

La recomendación inicial es construir manadas mediante **réplicas de servicios** y **especialistas complementarios**. El particionado de un mismo modelo entre dispositivos queda como línea experimental avanzada: sumar la RAM de equipos distintos no crea memoria unificada, y la comunicación puede costar más que la capacidad añadida.

La unidad de integración de REDIL no es la máquina individual, sino el **servicio publicado por una manada**. Una manada PC puede publicar chat/código; una Android puede publicar OCR, clasificación o inferencia ligera; REDIL Core decide a cuál enviar cada petición y cómo componer el resultado.

## 2. Modelo conceptual: nodo → manada → REDIL

~~~mermaid
flowchart TB
  subgraph N["Nivel 1 · Dispositivos"]
    PC["PC Linux sin GPU dedicada"]
    AND["Teléfono Android"]
    ACC["Aceleradores opcionales: GPU / NPU / DSP"]
  end
  subgraph H["Nivel 2 · Manadas"]
    HPC["REDIL-PC Herd: réplicas, especialistas, scheduler"]
    HAND["REDIL-ANDROID Herd: nodos móviles, política térmica/energética"]
  end
  subgraph F["Nivel 3 · REDIL federado"]
    CORE["REDIL Core: registro, políticas, routing, observabilidad"]
    S1["Servicio: chat / código"]
    S2["Servicio: visión / OCR"]
    S3["Servicio: embeddings / RAG"]
  end
  PC --> HPC
  AND --> HAND
  ACC -.-> PC
  ACC -.-> AND
  HPC --> CORE
  HAND --> CORE
  CORE --> S1
  CORE --> S2
  CORE --> S3
~~~

### 2.1 Nodo

Cada nodo tiene identidad propia y declara capacidades observadas:

- CPU: arquitectura, ISA, núcleos/hilos y frecuencia si está disponible.
- Memoria: RAM total, disponible y límite operativo asignado al agente.
- Aceleradores: GPU/NPU/DSP, runtime, memoria y capacidades realmente verificadas.
- Almacenamiento: espacio libre, velocidad orientativa y modelos locales disponibles.
- Software: SO, ABI, runtime de inferencia y versiones.
- Estado: disponibilidad, carga, temperatura, alimentación/batería y conectividad.
- Políticas: servicios permitidos, cuota, privacidad, horario, límite de energía y concurrencia.

La capacidad anunciada debe distinguir **detectada**, **declarada por fabricante**, **soportada por runtime** y **medida**. No se anunciará NPU utilizable por el mero hecho de que el SoC la incluya.

### 2.2 Manada

Una manada administra recursos de un grupo de nodos y expone capacidades como servicios. Incluye coordinador/scheduler, inventario de modelos, cola de trabajos, monitor de salud, adaptadores de motores, API, políticas de admisión, telemetría y recuperación.

El coordinador no tiene que ser una máquina dedicada. En un prototipo puede ser uno de los nodos, con recuperación o elección de líder en fases posteriores.

### 2.3 REDIL federado

REDIL Core descubre y registra manadas, normaliza sus descripciones y enruta peticiones según modalidad, capacidad requerida, idioma/calidad validada, latencia, carga, disponibilidad, energía, privacidad y coste de comunicación.

Una manada puede publicar varios servicios; un servicio puede tener varias manadas proveedoras. La asignación lógica por servicio **no obliga** a dedicar hardware exclusivo: una máquina puede participar en varios pools si el scheduler aplica cuotas y evita sobreasignación.

## 3. Línea A — REDIL-PC: manadas de ordenadores sin GPU dedicada

### 3.1 Objetivo

Aprovechar PCs económicos, reutilizados o de bajo consumo, sin exigir GPU dedicada. El sistema base debe ser ligero, reproducible y mantenible, con motor de inferencia CPU y servidor API.

### 3.2 Sistema operativo

**Fase inicial recomendada: Ubuntu Server mínimo.** Permite validar drivers, compiladores, bibliotecas y motores con instrumentación y diagnóstico accesibles. Reduce el riesgo de diseñar un OS propio antes de conocer las necesidades reales.

**Fase de producto:**
- **Buildroot:** estudiar para imágenes pequeñas y controladas, con servicios y dependencias fijados.
- **Yocto:** estudiar si se necesita una distribución reproducible, perfiles de hardware, actualizaciones y mantenimiento a largo plazo.
- No decidir por tamaño mínimo teórico: el coste real depende de kernel, libc, TLS, runtime, modelos, cachés y herramientas de diagnóstico.

Un Linux embebido mínimo sigue siendo Linux. Zephyr no es una base apropiada para ejecutar llama.cpp como servidor de inferencia general; puede servir para microcontroladores auxiliares, sensores, gestión energética o periféricos.

### 3.3 Motor y servidor

- **llama.cpp / llama-server:** primera referencia para GGUF y CPU, sujeto a compatibilidad del modelo y arquitectura.
- **TensorFold u otros motores:** adaptadores opcionales según soporte, consumo y estabilidad.
- API HTTP compatible con OpenAI cuando corresponda, detrás del agente REDIL.
- Límites explícitos de memoria, contexto, batch y concurrencia.

El agente no debe acoplarse a un único runtime. Cada backend se implementa mediante un adaptador con operaciones normalizadas: descubrir modelos, cargar/descargar, health, inferir, cancelar, métricas y errores.

### 3.4 Perfiles de PC orientativos

| Perfil | RAM física | CPU / almacenamiento | Rol razonable |
|---|---:|---|---|
| PC básico | 8 GB | CPU básica moderna, SSD | Agente, router ligero, embeddings pequeños o tareas auxiliares |
| PC de entrada | 16 GB | 4–8 núcleos, SSD/NVMe | Modelos pequeños cuantizados, chat ligero, RAG, clasificación |
| PC medio | 32 GB | 6–12 núcleos, NVMe | Modelos 3–8B cuantizados según contexto y concurrencia |
| PC reforzado | 64 GB o más | Buen ancho de banda de memoria, NVMe | Modelos mayores, varias réplicas/servicios, contextos amplios |

Son categorías de planificación, no garantías de compatibilidad ni rendimiento. Deben contarse pesos, KV cache, buffers, tokenizer, runtime, sistema operativo y concurrencia. La RAM de distintos PCs no se suma como memoria local.

### 3.5 Red

- Ethernet gigabit como punto de partida; 2.5 GbE o superior cuando la carga lo justifique.
- Wi-Fi para administración o nodos auxiliares, no como primera opción para particionar inferencia token a token.
- Medir ancho de banda, RTT, jitter, pérdida y congestión bajo carga.
- Evitar transferir pesos completos en cada trabajo: usar caché local, hashes y distribución controlada de artefactos.

### 3.6 Estrategias de manada PC

1. **Réplicas:** varios PCs ejecutan la misma versión de un modelo/servicio. El scheduler distribuye peticiones independientes. Es la forma inicial más sencilla de aumentar throughput y disponibilidad.
2. **Especialistas:** cada nodo ejecuta una función distinta (chat, código, embeddings, OCR, ASR, TTS, RAG). El coordinador compone flujos si es necesario.
3. **Particionado/model parallel:** capas o bloques del mismo modelo en nodos diferentes. Solo tras validar un backend que implemente explícitamente el particionado. Requiere medir sincronización, red y latencia por token.

**Recomendación:** empezar con réplicas y especialistas. El beneficio de réplicas se ve principalmente en concurrencia y throughput agregado, no necesariamente en la velocidad de una única generación.

## 4. Línea B — REDIL-ANDROID: manadas de teléfonos

### 4.1 Objetivo

Convertir teléfonos Android disponibles en nodos voluntarios de cómputo local. Algunos SoC ofrecen GPU móvil y aceleradores especializados, pero su utilización depende de APIs, drivers, firmware, fabricante, runtime y versión Android.

### 4.2 Arquitectura de software

Android no debe tratarse como un servidor Ubuntu reducido. Propuesta:

- aplicación REDIL Android para enrolamiento, identidad, inventario, políticas y control;
- componente de inferencia nativo o biblioteca integrada mediante Android NDK cuando proceda;
- servicio en primer plano (foreground service) para trabajos habilitados, respetando restricciones Android;
- comunicación autenticada con el coordinador;
- gestión de trabajos interrumpibles y reanudables;
- interfaz para pausar, desconectar, limitar consumo o retirar el dispositivo.

No asumir que una tarea puede ejecutarse indefinidamente en background. Adaptarse a permisos, Doze, límites de procesos y políticas de cada versión.

### 4.3 Runtimes a investigar

| Tecnología | Papel posible | Condición / cautela |
|---|---|---|
| llama.cpp | Inferencia CPU y algunos backends móviles según build | Validar ABI, backend, memoria y modelos concretos |
| MLC LLM | Runtime LLM móvil con rutas de aceleración según plataforma | No asumir soporte universal para Adreno/Mali ni para todos los teléfonos |
| ExecuTorch | Runtime PyTorch para despliegues edge/móviles | Backend y operadores deben estar soportados para el dispositivo |
| Android NDK | Integración nativa y optimización CPU | No es un motor LLM ni habilita automáticamente la NPU |
| APIs del fabricante (QNN y otras) | Acceso a aceleradores específicos | Comprobar soporte, licencias, firmware, API y modelos convertibles |

Seleccionar runtime por combinación **modelo + SoC + versión Android + backend + precisión**, no por nombre comercial del teléfono.

### 4.4 Perfiles Android orientativos

| Perfil | RAM anunciada | Uso potencial | Política recomendada |
|---|---:|---|---|
| A1 | 4 GB | Control, preprocesado, OCR ligero si se soporta | Participación muy limitada |
| A2 | 6 GB | Tareas pequeñas, clasificación, embeddings ligeros | Límites estrictos de memoria y temperatura |
| A3 | 8 GB | SLM cuantizados y tareas multimodales pequeñas, sujeto a SoC | Perfil de experimentación inicial |
| A4 | 12 GB | Mayor margen para modelos pequeños y varias tareas | Medir RAM libre real |
| A5 | 16 GB o más | Candidatos más capaces y mayor contexto | No asumir que toda la RAM está disponible |

La RAM comercial incluye memoria usada por Android, GPU y procesos. Registrar memoria disponible en reposo y durante carga. Los modelos deben poder descargarse de memoria sin bloquear el dispositivo.

### 4.5 Energía, temperatura y disponibilidad

El scheduler Android debe conocer batería, alimentación, temperatura, throttling, carga CPU/GPU, memoria libre, estado de pantalla, conectividad y consentimiento del usuario.

Políticas posibles:
- no aceptar trabajos pesados por debajo de un umbral de batería configurable;
- priorizar tareas mientras el dispositivo está cargando;
- reducir batch, contexto y concurrencia al subir temperatura;
- detener admisión ante throttling severo;
- cancelar o devolver trabajos recuperables al desconectar;
- ofrecer modo manual, programado o siempre disponible bajo control explícito.

No fijar valores térmicos universales: umbrales y sensores varían por fabricante. Usar señales oficiales disponibles y registrar límites efectivos.

### 4.6 Conectividad

- Wi-Fi 6/6E/7: enlace práctico para prototipos; medir rendimiento real y congestión.
- Ethernet por adaptador USB-C: interesante para teléfonos fijos o bancos de pruebas, si se soporta.
- USB conectado a PC: útil para depuración, alimentación y laboratorio.
- Bluetooth: descubrimiento o control de bajo caudal; no transporte de inferencia distribuida.
- Red móvil: no usar por defecto para tráfico pesado; requiere autorización y límites de datos.

### 4.7 Especialidades apropiadas

La primera contribución Android puede ser preprocesamiento y servicios pequeños:
- OCR y extracción de texto;
- clasificación y etiquetado;
- embeddings pequeños;
- detección o preprocesamiento de imágenes;
- ASR/TTS ligero si runtime e idioma están validados;
- modelos compactos de chat o extracción;
- tareas batch tolerantes a desconexión.

## 5. Tres modos de cooperación dentro de una manada

### 5.1 Réplicas de servicio

Cada nodo contiene el mismo modelo y recibe solicitudes independientes.

**Ventajas:** simplicidad, escalado horizontal de throughput, tolerancia a fallos y despliegue gradual.

**Límites:** no aloja un modelo que no cabe en un nodo; requiere sincronizar versiones y cachés; el balanceo debe considerar carga y afinidad de sesión.

### 5.2 Especialistas complementarios

Cada nodo ejecuta una especialidad y la manada ofrece un servicio compuesto. Ejemplo: Android hace OCR; PC calcula embeddings; otro PC ejecuta el LLM; un nodo devuelve TTS.

**Ventajas:** encaja con hardware heterogéneo, evita mover todos los pesos a cada nodo y asigna el trabajo al acelerador adecuado.

**Límites:** el flujo acumula latencia; hay que versionar contratos y manejar errores parciales; aplicar políticas de privacidad entre etapas.

### 5.3 Particionado de un mismo modelo

Se distribuyen capas, tensores o expertos de un modelo entre nodos.

**Ventajas potenciales:** explorar modelos mayores que la memoria local de un equipo; repartir cómputo o memoria cuando el backend lo soporta.

**Límites:**
- no existe memoria unificada automática;
- cada token puede requerir comunicación y sincronización;
- Wi-Fi variable puede penalizar el rendimiento;
- ISA, runtimes y cuantizaciones diferentes complican la partición;
- la caída de un nodo puede invalidar la inferencia;
- el soporte depende del motor y arquitectura concretos.

llama.cpp dispone de mecanismos RPC experimentales, pero no deben considerarse automáticamente una base de producción segura o estable. Mantenerlos aislados en red privada y no exponerlos a Internet. Evaluar alternativas de model parallel solo con evidencia de mantenimiento, compatibilidad y pruebas reproducibles.

**Orden de prioridad:** réplicas → especialistas → particionado experimental.

## 6. Diseño de REDIL-NODE y contratos comunes

### 6.1 Agente REDIL-NODE

Agente común con implementaciones por plataforma:
- PC: servicio Linux administrado por systemd.
- Android: aplicación y componente de servicio Android, con sus reglas de ciclo de vida.

Responsabilidades: identidad criptográfica y enrolamiento; inventario y anuncio de capacidades; registro de runtimes/modelos; recepción de trabajos autorizados; ejecución mediante adaptadores; progreso, resultado, cancelación y error; métricas; actualización controlada; recuperación; límites locales y consentimiento.

### 6.2 Contrato de capacidad

Cada nodo publica un documento normalizado con:
- node_id, platform, os, architecture;
- cpu, memory_total, memory_available;
- accelerators[] con fabricante, tipo, backend y estado de validación;
- runtimes[] y versiones;
- models[] con identificador, revisión, hash, formato, cuantización y modalidad;
- services[] con tareas y límites;
- network con endpoints internos y métricas;
- health, thermal, power;
- policy con cuotas, consentimiento y límites.

No publicar identificadores personales del teléfono ni datos sensibles del usuario en el registro de capacidades.

### 6.3 Contrato de trabajo

Un trabajo define job_id, service, operation, input_ref o payload, requisitos de modalidad/modelo/idioma, deadline, prioridad, reintentos, máximos de tokens/contexto/tamaño, política de privacidad y si admite ejecución parcial, cancelación o reanudación.

Estados normalizados: queued, accepted, running, completed, failed, cancelled, expired, deferred.

Los resultados incluyen servicio, modelo/runtime/revisión, estado, métricas y procedencia cuando aplique.

### 6.4 Comunicación

Primera propuesta:
- HTTP/JSON para control y API pública;
- gRPC/Protocol Buffers si comunicación interna de alto volumen o streaming lo justifica;
- TLS en enlaces no locales;
- mTLS o credenciales de dispositivo para autenticación mutua;
- streaming para operaciones que lo necesiten;
- transferencia de archivos/modelos mediante canal separado, autenticado y con hash.

Un protocolo común no implica que todos los nodos deban usar el mismo runtime.

## 7. REDIL Core: federación de manadas por servicio

La federación se organiza por **capacidades lógicas**, no por obligación de tener un cluster físico exclusivo.

| Pool lógico | Capacidades publicadas | Proveedores posibles |
|---|---|---|
| REDIL-LLM | chat, resumen, generación, razonamiento | manada PC, nodos reforzados, móviles seleccionados |
| REDIL-CODE | generación, revisión, explicación y pruebas | PC CPU reforzados |
| REDIL-VISION | OCR, clasificación, VLM | Android, PC y nodos GPU opcionales |
| REDIL-EMBEDDINGS | embeddings y recuperación | PC CPU y móviles |
| REDIL-AUDIO | ASR/TTS | PC y Android |
| REDIL-AGENTS | ejecución de flujos y herramientas | nodos con sandbox y políticas |
| REDIL-ROUTER | routing, registro, cuotas y observabilidad | nodos de control redundantes |

Una misma manada puede publicar varios pools; un pool puede tener proveedores de varias manadas. Separar:
- **control plane:** registro, políticas, scheduler y configuración;
- **data plane:** payloads, inferencia, streaming y resultados;
- **observability plane:** métricas, trazas, eventos y auditoría.

### 7.1 Flujo mixto PC + Android

~~~mermaid
sequenceDiagram
  participant U as Cliente
  participant R as REDIL Core
  participant A as Manada Android
  participant P as Manada PC
  U->>R: Solicitud con imagen/documento
  R->>A: OCR / preprocesado autorizado
  A-->>R: Texto extraído + métricas
  R->>P: Embeddings / recuperación / LLM
  P-->>R: Respuesta estructurada
  R-->>U: Respuesta unificada + procedencia
~~~

Si el servicio principal puede resolver la petición en un solo nodo, el router debe evitar pasos innecesarios.

## 8. API propuesta

| Ruta propuesta | Función |
|---|---|
| POST /v1/chat/completions | Chat y generación |
| POST /v1/embeddings | Embeddings |
| POST /v1/vision/analyze | Análisis de imagen/documento |
| POST /v1/audio/transcriptions | ASR |
| POST /v1/audio/speech | TTS |
| POST /v1/agents/execute | Ejecución de flujos agentivos |
| GET /v1/services | Catálogo de servicios publicados |
| GET /v1/manadas | Inventario de manadas visibles |
| GET /v1/manadas/{id}/status | Salud y capacidad |
| POST /v1/jobs/{id}/cancel | Cancelación |

Estas rutas son diseño inicial, no endpoints implementados. El API gateway normaliza errores, autenticación, límites, streaming, timeouts y procedencia.

## 9. Seguridad, privacidad y confianza

- enrolamiento explícito y revocable de cada nodo;
- identidad criptográfica individual; no compartir una clave global;
- TLS y autenticación mutua entre agentes y coordinadores;
- autorización por servicio, nodo, operación y usuario;
- cuotas y límites de tamaño, contexto y concurrencia;
- sandbox para herramientas y agentes;
- separación de secretos de los logs;
- cifrado de artefactos sensibles en reposo cuando proceda;
- verificación de hash y procedencia de modelos;
- actualización firmada o canal autenticado;
- auditoría de asignación y ejecución;
- opción de retirar o pausar un teléfono en cualquier momento;
- no enviar datos a nube externa salvo configuración explícita.

No exponer directamente puertos RPC experimentales de motores de inferencia a redes públicas. Los workers aceptan trabajos únicamente del coordinador autenticado y con políticas aplicadas.

## 10. Topología experimental de referencia

### 10.1 Prototipo pequeño

- 1 PC Linux como coordinador y servidor API.
- 1 PC worker adicional con servicio replicado o especialista.
- 2 teléfonos Android como nodos voluntarios de tareas ligeras.
- Wi-Fi privada para primera validación; Ethernet para PCs si está disponible.

Objetivo: demostrar enrolamiento, inventario, envío de trabajo, respuesta, métricas y desconexión limpia.

### 10.2 Prototipo intermedio

- 4 PCs CPU-only: un coordinador lógico y tres workers.
- 4–6 teléfonos Android.
- Pools de chat, embeddings, OCR/preprocesado y audio ligero.
- Réplicas de un servicio para probar balanceo y throughput.
- Modelos almacenados localmente y registro central de hashes.

Objetivo: validar federación heterogénea, colas, políticas energéticas y recuperación.

### 10.3 Despliegue ampliado

Varias manadas PC por ubicación/servicio, una o más manadas Android, gateway redundante, registro de capacidades y modelos, observabilidad agregada, políticas inter-manada y particionado solo en laboratorio.

## 11. Roadmap de implementación

### Fase 0 — Especificación y contratos
- fijar vocabulario nodo/manada/servicio/federación;
- definir schemas de capacidad y trabajo;
- establecer identidad, enrolamiento y amenazas;
- definir API mínima y telemetría.

### Fase 1 — REDIL-PC mínimo
- agente Linux;
- adaptador llama.cpp/llama-server;
- descubrimiento y registro;
- manada de un nodo;
- API de chat y health;
- segundo nodo como réplica;
- métricas de throughput agregado y latencia individual.

### Fase 2 — REDIL-PC especialista
- servicios en diferentes workers;
- scheduler con cuotas;
- colas, cancelación, timeouts y fallback;
- caída/reincorporación de worker;
- benchmark Ethernet y Wi-Fi.

### Fase 3 — REDIL-ANDROID individual
- aplicación de enrolamiento;
- inventario de SoC, RAM y estado térmico/energético;
- inferencia pequeña local;
- envío de resultado al coordinador;
- pausa/desconexión y consentimiento.

### Fase 4 — Manada Android
- dos o más teléfonos;
- scheduler móvil;
- política térmica y de batería;
- tareas interrumpibles;
- evaluación de runtimes por SoC;
- comparación CPU/GPU/NPU cuando haya backend validado.

### Fase 5 — Federación REDIL
- registro de manadas;
- catálogo de servicios;
- routing entre manadas;
- flujo mixto PC/Android;
- autenticación y políticas inter-manada;
- observabilidad y auditoría.

### Fase 6 — Investigación de model parallel
- seleccionar modelo y backend compatibles;
- medir baseline single-node;
- probar dos nodos con red cableada;
- medir coste por token y comunicación;
- evaluar fallo de worker;
- comparar contra réplicas y especialistas;
- mantener experimental hasta demostrar ventaja.

## 12. Métricas y protocolo de benchmark

No reducir el éxito a tokens/s. Medir:
- latencia por petición: p50, p95 y p99;
- TTFT, prefill y decode;
- throughput agregado y concurrencia efectiva;
- calidad/tasa de éxito en conjunto de tareas;
- coste energético: Wh por petición o por 1.000 tokens;
- eficiencia móvil: tokens/Wh y degradación térmica;
- RAM pico, CPU, GPU/NPU y almacenamiento temporal;
- bytes por petición, RTT, jitter y retransmisiones;
- overhead de scheduler y transferencia;
- detección, failover y recuperación.

Protocolo:
1. fijar modelo, hash, tokenizer, cuantización y runtime;
2. fijar prompt, contexto, salida y sampling;
3. ejecutar baseline individual;
4. ejecutar cluster con la misma carga;
5. repetir y registrar variabilidad;
6. separar throughput agregado de velocidad de una respuesta;
7. medir estado térmico antes/durante/después en Android;
8. guardar logs, configuración, hardware y commit del agente;
9. clasificar resultados como ESTIMATED, UPSTREAM-REPORTED o LOCAL-MEASURED.

## 13. Riesgos y decisiones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Confundir suma de RAM con memoria compartida | Planificación imposible | Documentar el límite; particionado solo con backend explícito |
| Latencia de red en model parallel | Decode lento | Empezar con réplicas/especialistas; Ethernet; medir RTT y bytes/token |
| Fragmentación de runtimes Android | Soporte irregular | Matriz por SoC/ABI/runtime/modelo |
| Restricciones Android background | Workers desconectados | Foreground service autorizado, trabajos interrumpibles |
| Calor y batería | Throttling y desgaste | Scheduler térmico/energético, cuotas y pausa configurable |
| PC con RAM limitada | OOM y swap excesivo | Perfilado, límites de contexto/concurrencia y selección de modelo |
| Fallo del coordinador | Manada inutilizable | Recuperación o coordinador redundante |
| Exposición de RPC experimental | Riesgo de seguridad | Red privada, autenticación, no exponer a Internet |
| Modelos/licencias no verificadas | Riesgo legal y técnico | Registrar artefacto, hash y licencia |

### Decisiones recomendadas

1. Adoptar nodo → manada → REDIL federado.
2. Mantener REDIL-PC y REDIL-ANDROID como líneas distintas con contrato de nodo común.
3. Empezar con Ubuntu Server mínimo en PC; posponer Buildroot/Yocto.
4. Implementar agente Android nativo y respetar ciclo de vida del sistema.
5. Priorizar réplicas y especialistas; model parallel experimental.
6. Diseñar pools lógicos por servicio, permitiendo que recursos físicos participen en varios pools con cuotas.
7. Mantener API y scheduler independientes de llama.cpp y de cualquier runtime.
8. Tratar rendimiento como estimado hasta medirlo.
9. Integrar seguridad, consentimiento y privacidad desde el prototipo.
10. No declarar REDIL desplegada hasta pruebas reproducibles PC, Android y federación.

## 14. Fuentes técnicas para evaluación

Puntos de partida; compatibilidad efectiva debe fijarse por release, commit, modelo y dispositivo:
- llama.cpp: https://github.com/ggml-org/llama.cpp
- llama-server: https://github.com/ggml-org/llama.cpp/tree/master/examples/server
- MLC LLM: https://github.com/mlc-ai/mlc-llm
- ExecuTorch: https://github.com/pytorch/executorch
- Android NDK: https://developer.android.com/ndk
- Android foreground services: https://developer.android.com/develop/background-work/services/foreground-services
- Android thermal API: https://developer.android.com/reference/android/os/PowerManager
- Qdrant: https://github.com/qdrant/qdrant
- gRPC: https://grpc.io/
- OpenTelemetry: https://opentelemetry.io/
- K3s (solo para nodos Linux/PC; no propuesto como orquestador de teléfonos): https://docs.k3s.io/

La capacidad RPC de llama.cpp debe tratarse como experimental y evaluarse por versión, topología y configuración. REDIL mantiene su propio plano de control y expone backends mediante adaptadores, sin convertir una función interna de un motor en el protocolo de federación completo.

## 15. Glosario

- **Nodo:** dispositivo que aporta recursos.
- **Manada:** cluster coordinado de nodos que publica servicios.
- **REDIL Core:** plano de control y federación entre manadas.
- **Réplica:** instancia equivalente de un servicio/modelo para solicitudes independientes.
- **Especialista:** nodo o servicio optimizado para una tarea.
- **Model parallel / particionado:** división explícita de un modelo entre dispositivos.
- **Control plane:** registro, políticas, planificación y configuración.
- **Data plane:** ejecución, payloads y resultados.
- **Worker:** nodo que ejecuta trabajos asignados.
- **Scheduler:** componente que selecciona el worker según capacidad, carga y políticas.

---

**Estado final:** propuesta de investigación preparada para convertirse en especificación técnica. No se afirma que agentes, APIs, clusters PC/Android, aceleración NPU ni pruebas descritas estén implementados. El siguiente paso es cerrar schemas de capacidad/trabajo y construir un prototipo REDIL-PC de dos nodos antes de iniciar la integración Android.
