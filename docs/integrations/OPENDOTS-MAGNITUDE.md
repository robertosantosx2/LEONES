# Integración OpenDots + Magnitude ICN

Estado: **compatibilidad implementada en el repositorio LEONES; validación E2E física pendiente**. OpenDots y el submódulo Magnitude no se parchean. LEONES proporciona una pequeña fachada HTTP para traducir las diferencias del ICN fijado en el submódulo a la superficie OpenAI que consume OpenDots.

## Auditoría del código real fijado por LEONES

El submódulo `subprojects/Magnitude` está fijado en el commit `c3ace06488737be5383087d965d0e4e629f4f00b`. Su `inference/README.md` documenta el Inference Control Node (ICN) con `/health` y `/v1/chat/completions` en el puerto 8080. El OpenAPI fijado confirma estas diferencias respecto a la API OpenAI convencional:

- `POST /v1/chat/completions` requiere `model_instance_id` y `stream`; la respuesta se define como Server-Sent Events (SSE).
- `GET /v1/models` devuelve el catálogo interno de Magnitude, no el objeto OpenAI `{ data: [{ id }] }`.
- `GET /v1/models/instances` devuelve las instancias cargadas y su estado `lifecycle`.

OpenDots utiliza `openaiCompatibleText` de `@tanstack/ai-openai/compatible`, con `api: 'chat-completions'`, y envía el modelo y los mensajes sin el campo específico `model_instance_id`. Por tanto, **apuntar directamente OpenDots al ICN no es compatible sin traducción**.

Referencias de código:
- [Magnitude ICN fijado en LEONES](https://github.com/robertosantosx2/magnitude/tree/c3ace06488737be5383087d965d0e4e629f4f00b/inference)
- [OpenAPI fijado: rutas y contratos](https://github.com/robertosantosx2/magnitude/blob/c3ace06488737be5383087d965d0e4e629f4f00b/packages/icn-protocol/openapi.json)
- [OpenDots: adaptador de modelo](https://github.com/CopilotKit/OpenDots/blob/main/src/server/dot-agent.ts)
- [OpenDots: variables de proveedor](https://github.com/CopilotKit/OpenDots/blob/main/docs/SETUP.md)
- [Licencia Magnitude](https://github.com/robertosantosx2/magnitude/blob/main/LICENSE)
- [Licencia OpenDots](https://github.com/CopilotKit/OpenDots/blob/main/LICENSE)

## Arquitectura implementada

```text
OpenDots / TanStack AI
    │  OPENAI_BASE_URL=http://127.0.0.1:10101/v1
    ▼
LEONES compatibility facade (loopback only)
    │  maps model alias -> model_instance_id + configuration ID; ensures SSE
    ▼
Magnitude ICN (127.0.0.1:8080)
    │
    ▼
Model instance already loaded and in Ready state
```

La fachada vive en `scripts/integrations/opendots_magnitude_proxy.mjs`. Solo publica `GET /health`, `GET /v1/models` y `POST /v1/chat/completions`; filtra los campos de petición al contrato del ICN, agrega `model_instance_id` y fuerza streaming porque el ICN fijado documenta SSE como respuesta. Escucha exclusivamente en `127.0.0.1` y no descarga ni carga modelos.

## Pasos de configuración

### 1. Arrancar Magnitude ICN y cargar un modelo

Desde el checkout del submódulo Magnitude, sigue las instrucciones de su `inference/README.md`. El ejemplo documentado es:

```bash
bun icn:serve -- --model /ruta/absoluta/modelo.gguf --model-alias modelo-local --bind 127.0.0.1:8080
```

Consulta las instancias activas:

```bash
curl -fsS http://127.0.0.1:8080/v1/models/instances | python3 -m json.tool
```

Selecciona el `instances[].id` de una instancia cuyo `lifecycle._tag` sea `Ready`. No uses un ID de catálogo, un nombre de archivo o un nombre de presentación en lugar del ID real de instancia.

### 2. Arrancar la fachada LEONES

En la raíz del repositorio LEONES:

```bash
MAGNITUDE_MODEL_INSTANCE_ID='ID_EXACTO_DE_INSTANCIA' OPENAI_MODEL=local node scripts/integrations/opendots_magnitude_proxy.mjs
```

Si el ICN usa otro host/puerto, define `MAGNITUDE_ICN_URL`. La fachada falla de forma visible si la instancia configurada no está disponible o no está en estado `Ready`.

### 3. Preparar OpenDots

Si aún no existe un checkout, el instalador opcional lo clona en `~/.local/share/leones/opendots` (o en `OPENDOTS_DIR`), verifica Node.js 24+, instala dependencias bloqueadas y crea `.env` solo si falta. No actualiza ni sobrescribe un checkout existente:

```bash
bash scripts/integrations/install_opendots.sh
```

Configura CopilotKit Intelligence siguiendo la [guía oficial de OpenDots](https://github.com/CopilotKit/OpenDots/blob/main/docs/SETUP.md).

### 4. Configurar OpenDots

En un checkout de OpenDots ya instalado, configura sus tres variables del proveedor. El helper valida el alias contra la fachada antes de modificar `.env` y conserva las demás variables:

```bash
bash scripts/integrations/configure_opendots_magnitude.sh /ruta/a/OpenDots local
```

Equivale a configurar:

```dotenv
OPENAI_API_KEY=local
OPENAI_BASE_URL=http://127.0.0.1:10101/v1
OPENAI_MODEL=local
```

El valor `local` para la clave es un marcador para clientes que exigen una clave; la fachada solo escucha en loopback y no implementa autenticación. No expongas el puerto 10101 a la red. Esta primera implementación soporta OpenDots y la fachada en el mismo host; el modo Docker/host-remoto queda fuera de alcance hasta añadir una configuración de red autenticada y probarla.

### 5. Ejecutar el smoke test

Con ICN, la instancia y la fachada en marcha:

```bash
OPENAI_MODEL=local bash scripts/integrations/opendots_magnitude_smoke.sh
```

El smoke test comprueba la lista OpenAI de modelos y una respuesta SSE no vacía que termina con `[DONE]`. No cambia servicios, no carga modelos y no tiene fallback remoto.

Después arranca OpenDots siguiendo su [guía oficial](https://github.com/CopilotKit/OpenDots/blob/main/docs/SETUP.md), con la configuración de Intelligence requerida, y prueba una conversación nueva, streaming, llamada real a una herramienta autorizada y revisión humana.

## Servicios conservados y límites de privacidad

Cambiar `OPENAI_BASE_URL` redirige solo la inferencia de texto. No hace que toda la aplicación sea local:

- **Conversaciones e historial:** OpenDots requiere CopilotKit Intelligence (servicio alojado, evaluación local Docker o despliegue self-hosted con licencia). La configuración del modelo no sustituye este servicio.
- **Voz:** la configuración de voz usa la API Realtime y no queda redirigida por `OPENAI_BASE_URL`.
- **Búsqueda web:** OpenDots usa Parallel por defecto. Puede conservarse de forma consciente o desactivarse con `WEB_SEARCH_PROVIDER=disabled`.
- **Ordenador del Dot:** OpenBot aporta el entorno aislado de navegador/archivos/terminal; no es el motor de inferencia.

No configurar fallback automático a un modelo remoto. No afirmar que todo OpenDots es offline mientras haya servicios alojados, voz remota o búsqueda externa.

## Dependencias y licencias

- OpenDots declara MIT y requiere Node.js `>=24`; usa CopilotKit/AG-UI, TanStack AI y `@tanstack/ai-openai`.
- Magnitude declara Apache-2.0 en su repositorio.
- CopilotKit Intelligence self-hosted está sujeto a licencia; la evaluación local documentada es una vista previa con requisitos de recursos y cuenta.
- Antes de distribuir un paquete combinado, auditar licencias transitivas y avisos de las versiones concretas fijadas en los lockfiles.

## Criterios de aceptación E2E

- [ ] El ICN está sano y la instancia seleccionada está en estado `Ready`.
- [ ] La fachada lista el alias OpenAI y entrega una respuesta SSE completa.
- [ ] OpenDots inicia una conversación real con el modelo local.
- [ ] Una herramienta autorizada se ejecuta de verdad; no basta con que el modelo afirme que la ejecutó.
- [ ] Si el ICN falla, OpenDots muestra el error y no usa un proveedor remoto como fallback.
- [ ] Se registran versiones, commit del submódulo, ID de instancia, latencia y memoria sin guardar prompts, archivos, conversaciones ni secretos.

Hasta completar las pruebas de OpenDots y herramientas, el estado es **fachada implementada y smoke test preparado; E2E real pendiente**, no integración funcional validada.
