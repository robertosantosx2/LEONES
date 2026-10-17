# Integración OpenDots + Magnitude (API compatible con OpenAI)

Estado: **implementación en preparación; no validada físicamente**. Esta integración usa configuración de proveedor, sin parchear OpenDots ni modificar el submódulo Magnitude. El contrato debe probarse contra las versiones instaladas.

## Resultado de la auditoría

- OpenDots lee `OPENAI_API_KEY`, `OPENAI_MODEL` y `OPENAI_BASE_URL` en el servidor y usa `OPENAI_BASE_URL` para el endpoint de inferencia.
- La documentación actual de Magnitude publica una API compatible con OpenAI en `http://127.0.0.1:10100/inference/v1`, con `GET /models` y `POST /chat/completions` (JSON y streaming). El ID del modelo debe ser exactamente el campo `id` devuelto por `/models`.
- Por tanto, **la ruta A es compatible a nivel de contrato HTTP documentado**. Todavía hay que verificar el comportamiento de la versión instalada, el streaming y las llamadas a herramientas en OpenDots con el modelo elegido.

Fuentes primarias:
- [OpenDots README](https://github.com/CopilotKit/OpenDots)
- [OpenDots setup: variables del proveedor y servicios de conversación](https://github.com/CopilotKit/OpenDots/blob/main/docs/SETUP.md)
- [Magnitude API overview](https://docs.magnitude.dev/api/overview)
- [Magnitude API endpoints](https://docs.magnitude.dev/api/endpoints)
- [Magnitude network access](https://docs.magnitude.dev/api/network-access)

## Configuración

En el `.env` del servidor OpenDots:

```dotenv
OPENAI_API_KEY=local
OPENAI_BASE_URL=http://127.0.0.1:10100/inference/v1
OPENAI_MODEL=REEMPLAZAR_POR_ID_EXACTO_DE_MAGNITUDE
```

`local` es un valor de relleno para clientes que exigen una clave; en el mismo equipo, Magnitude no requiere autenticación para la API local. No usar este valor si OpenDots accede a Magnitude desde otro dispositivo o contenedor.

Obtén los IDs disponibles:

```bash
curl -fsS http://127.0.0.1:10100/inference/v1/models
```

Copia un `data[].id` exacto en `OPENAI_MODEL`. No supongas que el nombre comercial o el nombre del archivo es el ID de la API.

### Si OpenDots se ejecuta dentro de Docker

Desde el contenedor, `127.0.0.1` apunta al propio contenedor, no al host. En Magnitude hay que habilitar **Network access**, configurar una clave de API y reiniciar el servicio. Usa en OpenDots:

```dotenv
OPENAI_API_KEY=REEMPLAZAR_POR_LA_CLAVE_DE_MAGNITUDE
OPENAI_BASE_URL=http://host.docker.internal:10100/inference/v1
OPENAI_MODEL=REEMPLAZAR_POR_ID_EXACTO_DE_MAGNITUDE
```

Mantén la API restringida a loopback cuando OpenDots se ejecute directamente en el host. No abras el puerto 10100 a Internet. Para acceso entre dispositivos, utiliza una red privada o túnel SSH y la clave configurada en Magnitude. Nunca guardes claves reales en Git.

## Servicios que permanecen separados

Configurar `OPENAI_BASE_URL` cambia el proveedor de **inferencia de texto**, no toda la infraestructura de OpenDots:

- **Conversaciones e historial:** OpenDots requiere CopilotKit Intelligence (servicio alojado, evaluación local Docker o despliegue self-hosted con licencia). El modelo local no reemplaza este servicio.
- **Voz:** la configuración documentada de voz usa la API Realtime y no queda redirigida por `OPENAI_BASE_URL`.
- **Búsqueda web:** OpenDots usa Parallel por defecto. Para desactivarla explícitamente, configura `WEB_SEARCH_PROVIDER=disabled`; también puede conservarse si el usuario acepta ese servicio externo.
- **OpenBot:** proporciona el entorno de ejecución de ordenador del Dot (navegador/archivos/terminal), no el motor de inferencia.

No afirmar que la aplicación es completamente local mientras haya servicios alojados, voz remota o búsqueda externa configurados. No configurar un fallback automático a un modelo remoto.

## Dependencias y licencias

- OpenDots declara licencia MIT y requiere Node.js `>=24` en su `package.json`; sus dependencias incluyen CopilotKit/AG-UI, TanStack AI y `@tanstack/ai-openai`.
- Magnitude declara Apache-2.0 y ofrece el endpoint compatible con OpenAI documentado arriba.
- La licencia MIT de OpenDots no elimina las condiciones de servicios externos. CopilotKit Intelligence self-hosted está sujeto a licencia; la evaluación local documentada es una vista previa con requisitos de recursos y cuenta.
- Auditar las licencias transitivas y avisos de dependencias en los lockfiles de las versiones concretas antes de distribuir un paquete combinado.

## Verificación

1. Arranca Magnitude y descarga/selecciona un modelo.
2. Configura `OPENAI_MODEL` con el ID exacto obtenido en `/models`.
3. Ejecuta el smoke test desde el host:

   ```bash
   OPENAI_MODEL='ID_EXACTO' scripts/integrations/opendots_magnitude_smoke.sh
   ```

   Para un endpoint de red que requiere autenticación, define también `MAGNITUDE_BASE_URL` y `MAGNITUDE_API_KEY`.

4. Arranca OpenDots con su configuración normal de Intelligence y envía un mensaje nuevo. Comprueba que responde el modelo local.
5. Prueba streaming y al menos una herramienta autorizada por el Dot; confirma que la llamada a herramienta se ejecuta, no solo que el modelo escribe texto diciendo que la ha ejecutado.
6. Revisa logs de ambos servicios y confirma que no se ha usado ningún proveedor remoto para inferencia.
7. Registra versión de OpenDots, versión/commit de Magnitude, modelo/ID, configuración de red, resultado, latencia y memoria. No registres prompts privados, contenido de archivos, conversaciones ni secretos.

### Criterios de aceptación

- `GET /models` lista el modelo configurado.
- `POST /chat/completions` devuelve texto no vacío.
- Streaming entrega eventos y termina correctamente.
- OpenDots inicia una conversación real con ese modelo.
- Las herramientas permitidas funcionan en una prueba real con revisión humana.
- Si Magnitude está apagado o no disponible, OpenDots falla de forma visible; no hay fallback remoto silencioso.
- Los servicios de conversación y otras integraciones se conservan, con sus límites de privacidad documentados.

Hasta completar los pasos 4–7, el estado de integración es **API configurada/documentada, E2E pendiente**, no integración funcional validada.
