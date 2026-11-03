# TensorFold Web — baseline funcional 0.1

**Fecha:** 2026-11-03  
**Estado:** baseline funcional validada por el usuario en equipo real.  
**Proyecto local:** `~/tensorfold-web`  
**Repositorio del motor:** [robertosantosx2/TensorFold](https://github.com/robertosantosx2/TensorFold)

## 1. Objetivo

TensorFold Web es una interfaz web ligera para conversar con un motor TensorFold local mediante una API compatible con el formato OpenAI Chat Completions. La implementación local evita dependencias de Node.js y paquetes Python de terceros: el puente HTTP está construido con la biblioteca estándar de Python.

Esta entrega registra el primer baseline funcional. No equivale a una distribución pública ni a un paquete instalable: el código fuente permanece en el equipo local del usuario.

## 2. Arquitectura validada

```text
Navegador (http://127.0.0.1:8787/)
        |
        v
Bridge Python (stdlib, puerto 8787)
        |
        | proxy HTTP /api/*
        v
TensorFold Engine 1.2.0 (127.0.0.1:8080)
        |
        v
NVIDIA RTX 3050 Laptop GPU (4 GiB, SM86)
```

Componentes locales observados:

- `index.html`: interfaz web.
- `tensorfold-web-bridge.py`: servidor estático y proxy API.
- `run-tensorfold-web.sh`: lanzador del bridge.
- `tensorfold-web.log`: registro del bridge.
- `tensorfold-web.pid`: PID guardado por el lanzador.

El bridge sirve la interfaz y expone las rutas permitidas del motor bajo `/api`. La ruta raíz normaliza la query string para que accesos como `/?utm_source=...` sigan sirviendo la página principal.

## 3. Configuración probada

| Elemento | Valor |
|---|---|
| Sistema | Ubuntu |
| Equipo | MSI Thin 15 B12UC |
| CPU | Intel Core i7-12650H |
| GPU | NVIDIA RTX 3050 Laptop, 4 GiB, SM86 |
| Motor | TensorFold 1.2.0 |
| Backend | CUDA |
| Modelo | `mlx-community/Qwen3.5-2B-MLX-4bit` |
| ID servido | `qwen3.5-2b` |
| API del motor | `http://127.0.0.1:8080/v1` |
| Interfaz | `http://127.0.0.1:8787/` |
| Contexto de la sesión | 2048 tokens |
| Thinking | desactivado en el comando de arranque |

El motor informó dispositivo CUDA SM86, carga correcta del modelo y estado saludable. El endpoint `/v1/models` devolvió el identificador `qwen3.5-2b`.

## 4. Validación funcional

Pruebas realizadas en la sesión del 2026-11-03:

1. El bridge respondió HTTP 200 en `/` y en la ruta raíz con query string.
2. `/api/health` devolvió estado saludable, versión 1.2.0, backend CUDA y dispositivo RTX 3050.
3. `/v1/models` del motor y `/api/v1/models` del bridge devolvieron el mismo modelo: `qwen3.5-2b`.
4. Se detectó un defecto de inicialización en el frontend: `setStatus()` intentaba escribir en `#sideStatus`, elemento que no existía. La excepción interrumpía `refresh()` antes de cargar el selector de modelos.
5. Se corrigió el acceso haciendo opcional la actualización de `#sideStatus`; tras recargar la página, el modelo apareció automáticamente.
6. El usuario confirmó que la interfaz y el selector funcionaban y, posteriormente, que una conversación real desde la web funcionaba correctamente.

**Resultado:** validación funcional E2E manual superada: navegador → bridge → API TensorFold → inferencia → respuesta en el chat.

No se asigna aquí una cifra de rendimiento: la validación de esta entrega fue funcional, no un benchmark controlado. Las mediciones anteriores de TensorFold Engine no deben atribuirse como benchmark de TensorFold Web.

## 5. Corrección aplicada al frontend

Cambio funcional aplicado en `index.html`:

```javascript
// Antes
$('#sideStatus').textContent=ok?'Online':'Offline';

// Después
if($('#sideStatus'))$('#sideStatus').textContent=ok?'Online':'Offline';
```

Se creó una copia local de seguridad llamada `index.html.bak-model-selector`. El bridge sirve el HTML desde disco, por lo que no fue necesario reiniciar el motor ni el bridge para aplicar el cambio; bastó una recarga completa del navegador.

## 6. Arranque local

Con TensorFold Engine ya iniciado en el puerto 8080:

```bash
cd ~/tensorfold-web
./run-tensorfold-web.sh
```

Abrir en el mismo equipo:

```text
http://127.0.0.1:8787/
```

El servicio está configurado para loopback. No se debe publicar directamente en una red no confiable: el tráfico HTTP no está cifrado. La opción de token del bridge es una barrera de autenticación, no sustituye TLS/VPN cuando se habilita acceso remoto.

## 7. Alcance y limitaciones del baseline

Incluido y probado:

- Interfaz de chat en navegador.
- Consulta de salud del motor.
- Descubrimiento de modelos mediante `/v1/models`.
- Proxy del endpoint `/v1/chat/completions`.
- Recepción de respuestas en el chat, incluido el flujo de conversación probado por el usuario.
- Implementación del bridge sin frameworks ni dependencias Python externas.

No queda acreditado todavía:

- Acceso multiusuario o despliegue público.
- TLS, gestión avanzada de usuarios o almacenamiento persistente de conversaciones.
- Pruebas de carga, concurrencia, límites de memoria o sesiones prolongadas.
- Compatibilidad con todos los motores o todas las extensiones de la API OpenAI.
- Distribución reproducible del código: los archivos fuente siguen en el equipo local y no se han publicado en este commit.

## 8. Próximos pasos

1. Mantener esta versión como baseline estable y conservar la copia local de seguridad.
2. Publicar el código fuente desde el equipo de desarrollo en una rama/versionado separado, después de revisar secretos, configuración y documentación.
3. Añadir pruebas automáticas para rutas, descubrimiento de modelos, errores HTTP y streaming SSE.
4. Añadir pruebas de seguridad antes de permitir conexiones fuera de loopback.
5. Medir TTFT, tokens/s y uso de VRAM con un protocolo reproducible, separando resultados del motor y del frontend.

## 9. Evidencia y trazabilidad

La evidencia disponible para este registro procede de los resultados de terminal y de la confirmación explícita del usuario durante la sesión: respuestas HTTP, JSON de salud y modelos, diagnóstico DOM y conversación real satisfactoria desde el navegador.

No se incluyen logs completos ni hashes de los archivos locales porque no se han transferido al repositorio durante esta operación. Este documento registra el estado validado, no pretende sustituir un artefacto reproducible ni una auditoría del código fuente.
