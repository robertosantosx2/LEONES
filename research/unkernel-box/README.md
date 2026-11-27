# Unkernel + Box: auditoría de código y prototipo de puente de inferencia

**Fecha de corte:** 2026-11-26  
**Repositorio auditado:** [pithings/unkernel](https://github.com/pithings/unkernel)  
**Commit fijado:** [`fd204d3130309c45ce51795c753c3b8ec1eaddfd`](https://github.com/pithings/unkernel/commit/fd204d3130309c45ce51795c753c3b8ec1eaddfd)  
**Rama LEONES:** `research/unkernel-box-investigation-2026-11-26`

## 1. Resumen ejecutivo

La auditoría identifica una vía de integración de bajo acoplamiento para ejecutar herramientas de Box dentro del guest Unkernel y delegar inferencia a un servicio que permanece en el host. La pieza clave es el mecanismo de host commands del SDK: el guest ejecuta un comando normal y Unkernel entrega al host un contexto con argumentos y streams estándar. Esto permite mantener fuera del guest las credenciales, el acceso a modelos y la conexión al motor de inferencia.

**Conclusión:** Unkernel ofrece una superficie plausible para alojar el entorno aislado de Box y conectar sus herramientas a un broker de inferencia host-side. No se ha demostrado todavía una VM real conectada a llama.cpp, ni aislamiento de seguridad suficiente para producción. La recomendación es validar primero el contrato guest/host con una VM mínima y un endpoint simulado; después conectar un motor real.

## 2. Alcance y reproducibilidad de la auditoría

Se fijó el repositorio al commit indicado arriba para evitar que una rama móvil altere las conclusiones. Se inspeccionaron los siguientes archivos del árbol:

- `js/core/vsock.ts`
- `js/core/instance.ts`
- `js/core/commands.ts`
- `js/core/tty.ts`
- `web/src/apps/agents/llama.ts`
- `web/src/apps/agents/ollama.ts`
- `web/src/apps/agents/fx-local.ts`
- `web/src/apps/agents/index.ts`
- `test/api.test.ts`
- documentación seleccionada bajo `.agents/`

Esta es una auditoría de las interfaces SDK/host bridge relevantes para el prototipo, no una auditoría exhaustiva del kernel, kwemu, JIT, MMU, aislamiento, filesystem o seguridad del proyecto completo. No se modificó Unkernel upstream.

## 3. Interfaces verificadas en el código

### 3.1 KernelHandle

La interfaz pública de instancia expone, entre otras, operaciones de ciclo de vida y E/S:

- Streams y terminal: `output`, `input`, `write`, `resize`, `sync`, `stop`.
- Estado y diagnóstico: `snapshot`, `stats`, `profile`, `memoryMiB`.
- Dispositivos: `display`, `evdev`, `frame`, `readFrame`, `sound`.
- Red y procesos: `vsock`, `spawn`, `attach`, `exec`, `connect`, `fetch`.
- Almacenamiento y comandos: `mount`, `mounts`, `addCommand`, `removeCommand`, `commands`.

La disponibilidad exacta depende de la imagen guest y de la configuración de instancia; la mera presencia del método en el SDK no prueba que cualquier imagen lo soporte.

### 3.2 Host commands: interfaz recomendada para Box

El código de `js/core/commands.ts` implementa `createKernel({ commands })` y el registro dinámico `vm.addCommand()`. El comando se presenta al guest como ejecutable en `/run/kw/bin/NAME`; el guest utiliza `kwcmd` y el transporte host/guest se apoya en vsock, con el puerto de control observado en 1020.

El handler host recibe un contexto `HostCommandContext` con campos relevantes:

- Identidad y ejecución: `name`, `args`, `env`, `cwd`, `pid`, `uid`, `gid`.
- Terminal: `isTTY`, `cols`, `rows`.
- E/S y cancelación: `stdin`, `stdout`, `stderr`, `signal`.

El handler puede devolver un código numérico, string, `Uint8Array`, objeto o `void`. El guest conserva la semántica de proceso (PID, stdio y estado de salida). `addCommand` espera a que el guest enlace el ejecutable; requiere el soporte `kwbox/kwcmd` en la imagen y el canal vsock operativo.

**Implicación arquitectónica:** `box-infer` puede ser un comando host-side invocado desde procesos guest, sin parchear el kernel ni compilar el motor LLM dentro de kwemu.

### 3.3 Vsock

`js/core/vsock.ts` implementa el transporte de streams con control de créditos/backpressure. La inspección identifica CID host 2 y guest 3, y operaciones de host como `listen`, `connect`, `receive`, `deviceReady` y `shutdown`. Los streams usan `ReadableStream<Uint8Array>` y `WritableStream<Uint8Array|string>`.

No se debe confundir esta inspección del transporte con una prueba de conectividad de una VM real.

### 3.4 Agentes e inferencia existentes

Se revisaron los adaptadores de agentes llama, Ollama y FX-local para comprender los puntos de integración existentes. La estrategia propuesta evita acoplar Box a un único proveedor: el broker host-side normaliza la petición y delega en un endpoint configurable compatible con OpenAI Chat Completions.

## 4. Arquitectura propuesta

```text
┌────────────────────────────── HOST ──────────────────────────────┐
│  Box Inference Broker                                            │
│  - endpoint /v1/chat/completions                                  │
│  - API keys y secretos fuera del guest                            │
│  - timeout, límites, cancelación y observabilidad                 │
│                 │                                                │
│          llama.cpp / TensorFold / otro provider                   │
│                                                                  │
│  Unkernel HostCommand: box-infer                                 │
│                 ▲                                                │
│                 │ kwcmd over vsock (control port 1020)           │
└─────────────────┼────────────────────────────────────────────────┘
                  │
┌─────────────────┼────────────── GUEST ───────────────────────────┐
│  Box workspace │                                                 │
│  agente / CLI ─┴─> /run/kw/bin/box-infer                         │
│  herramientas, archivos y estado del guest                       │
└──────────────────────────────────────────────────────────────────┘
```

Principios:

1. El guest no recibe API keys ni credenciales del proveedor.
2. El guest consume una interfaz de comando estable, no SDKs específicos de cada motor.
3. El host valida el esquema, aplica límites y controla timeout/cancelación.
4. El proveedor de inferencia se configura en el host y puede cambiarse sin modificar el guest.
5. El transporte y el contrato de comando se mantienen separados de la API del proveedor.

## 5. Prototipo lógico Box Inference Bridge

Se definió un handler host-side `box-infer` con el siguiente contrato:

- Entrada JSON por stdin desde el proceso guest.
- Mensajes con roles permitidos: `system`, `user`, `assistant`.
- Límite de entrada: 64 KiB; máximo 64 mensajes; máximo 32.000 caracteres por contenido.
- Límite de generación: máximo 2.048 tokens.
- Límite de respuesta: 1 MiB.
- Timeout y cancelación vinculados a la señal del proceso guest.
- Endpoint de proveedor compatible con OpenAI Chat Completions.
- Errores enviados por stderr; la clave API permanece en el host.
- Sin streaming de tokens en esta primera iteración.

### Validación registrada

La validación comunicada para el prototipo lógico fue **3/3 tests PASS** sobre Node.js 22, usando un endpoint HTTP simulado:

1. Respuesta correcta del proveedor simulado.
2. Rechazo de JSON malformado.
3. Rechazo de roles no permitidos.

**Límite de esta evidencia:** los tests del handler con un servidor simulado no prueban el arranque de Unkernel, el enlace del comando dentro del guest, el transporte vsock real ni una inferencia contra llama.cpp/TensorFold. El código fuente ejecutable y los logs originales del prototipo no forman parte de esta entrega documental; por ello no se presenta este registro como CI reproducible de este commit.

## 6. Seguridad y límites conocidos

Antes de cualquier uso no experimental deben añadirse y verificarse:

- Autorización por identidad de proceso/guest y política de comandos permitidos.
- Límites de concurrencia, cuota por guest y protección contra agotamiento de recursos.
- Política de tamaño también para salida y streams; límites de tiempo estrictos.
- Validación de URL/proveedor para evitar SSRF y destinos no autorizados.
- Redacción de secretos y datos sensibles en logs.
- Aislamiento y revisión de los permisos de filesystem/red del guest.
- Pruebas de cancelación, desconexión, backpressure, errores HTTP y respuestas sobredimensionadas.
- Evaluación de amenazas del host bridge y de la frontera guest/host.

No se han implementado en este prototipo streaming de tokens, herramientas/function calling, persistencia, cuotas, autorización granular ni un modelo completo de políticas.

## 7. Plan de validación por gates

| Gate | Trabajo | Evidencia necesaria | Estado |
|---|---|---|---|
| G0 | Auditoría SDK y fijación del commit | rutas y commit upstream | **REVIEWED** |
| G1 | Handler lógico y tests con endpoint simulado | código, logs y tests reproducibles | **TESTED según registro previo; artefactos fuente no incluidos aquí** |
| G2 | Arrancar una VM Unkernel real | log de arranque y versión/commit | **PENDING** |
| G3 | Registrar `box-infer` y ejecutarlo desde guest | stdout/stderr, exit code, PID y evidencia de kwcmd/vsock | **PENDING** |
| G4 | Conectar llama.cpp local mediante broker | petición/respuesta real, hashes/configuración del motor | **PENDING** |
| G5 | Endurecimiento y pruebas negativas | threat model, límites, cancelación, autorización y tests | **PENDING** |
| G6 | Evaluar integración en Box/LEONES | decisión arquitectónica y PR revisada | **PENDING** |

### Siguiente experimento recomendado

En un entorno de desarrollo aislado, arrancar una imagen Unkernel mínima que incluya `kwbox/kwcmd`, registrar un comando host de eco sin secretos ni acceso de red, invocarlo desde el guest y verificar el ciclo completo. Solo después sustituir el eco por el broker HTTP simulado y, finalmente, por llama.cpp. No requiere modificar el kernel upstream.

## 8. Fuentes primarias

- [Repositorio Unkernel](https://github.com/pithings/unkernel)
- [Commit auditado](https://github.com/pithings/unkernel/commit/fd204d3130309c45ce51795c753c3b8ec1eaddfd)
- [README fijado](https://github.com/pithings/unkernel/blob/fd204d3130309c45ce51795c753c3b8ec1eaddfd/README.md)
- [Árbol fijado](https://github.com/pithings/unkernel/tree/fd204d3130309c45ce51795c753c3b8ec1eaddfd)

## 9. Estado y criterio de aceptación

Este documento archiva una auditoría de interfaces y el diseño/registro de validación de un prototipo lógico. No declara que Box esté integrado, que Unkernel haya arrancado en una VM de pruebas, que el broker haya hablado con un motor real ni que la frontera guest/host sea segura para producción.

La investigación se considerará integrada en LEONES cuando las gates G2–G4 tengan evidencia reproducible y la evaluación de seguridad G5 haya sido revisada. La aceptación final requiere decisión humana conforme a HDAE.
