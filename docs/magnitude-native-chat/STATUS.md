# Estado de desarrollo — Magnitude Native Chat

Fecha: 2026-10-17

## Repositorios y ramas

- LEONES diseño/prototipo: https://github.com/robertosantosx2/LEONES/tree/feat/magnitude-native-chat
- Especificación: [README.md](README.md)
- Prototipo navegable: [chat-prototype.html](chat-prototype.html)
- ADR Open WebUI mediante iframe: [ADR-openwebui-iframe.md](ADR-openwebui-iframe.md)
- Magnitude fork implementation: https://github.com/robertosantosx2/magnitude/tree/feat/native-chat-section
- PR upstream: https://github.com/magnitudedev/magnitude/pull/202

## Implementado en la rama de Magnitude

- Destino **Chat** en el contrato de navegación compartido y en la barra lateral web.
- Selector basado en IDs reales de `/inference/v1/models`.
- Peticiones a `/inference/v1/chat/completions` con SSE y render incremental.
- Cancelación de petición, nueva conversación, historial local, selección/eliminación de conversación y estados de error.
- Listener adicional loopback en `127.0.0.1:10101`; la raíz abre directamente Chat. El servicio/API principal conserva `10100`.
- Si `10101` está ocupado, el listener secundario registra una advertencia y no debe derribar el servicio principal.
- Documentación de privacidad local y resolución de problemas.

## Investigación Open WebUI + iframe

Se prioriza validar si Magnitude puede incluir Open WebUI en una sección **Chat** lateral, aprovechando su historial, selector de modelo y streaming, en lugar de mantener dos implementaciones de chat.

- El elemento `<iframe>` y `loading="lazy"` tienen soporte amplio en navegadores modernos.
- Chrome 154 anunció en septiembre de 2026 el nuevo sizing intrínseco `frame-sizing: content-height`, `window.requestResize()` y el opt-in `responsive-embedded-sizing`.
- Esa novedad de tamaño adaptable está marcada como experimental/limitada y no es compatible con Firefox/Safari según las referencias consultadas. No se necesita para una aplicación de chat de altura completa: la propuesta usa un iframe al 100% del contenedor y carga diferida al abrir Chat.
- El elemento iframe por sí solo no garantiza que Open WebUI permita el embedding. Falta comprobar `Content-Security-Policy`, `X-Frame-Options`, cookies/sesión, endpoint API, streaming y ciclo de vida.
- La búsqueda del código principal de Magnitude encontró una referencia a iframe en extracción del DOM, pero no confirmó un componente de UI para incrustar aplicaciones externas. La búsqueda de `frame-sizing` y `iframe component` tampoco devolvió resultados. Puede haber trabajo reciente en otra rama/PR que todavía hay que identificar.

Detalles y fuentes primarias: [ADR-openwebui-iframe.md](ADR-openwebui-iframe.md).

## Implementación Open WebUI en el fork

La rama `feat/native-chat-section` de [robertosantosx2/magnitude](https://github.com/robertosantosx2/magnitude/tree/feat/native-chat-section) ya contiene una vista Open WebUI opcional dentro de Chat, un validador que restringe URLs a loopback y tests unitarios para esa validación. La documentación de uso está en `docs/clients/local-chat.mdx` y la investigación técnica en `docs/clients/native-chat-research.md`.

Todavía no se han ejecutado los tests, el typecheck ni el build; tampoco se ha probado contra un servidor Open WebUI real. No considerar la integración validada.

## Estado de validación

**No validado localmente.** La integración GitHub permitió publicar commits y abrir la PR, pero esta sesión no ejecuta Bun/TypeScript ni tiene acceso al Magnitude instalado en Ubuntu. No se afirma que compile ni que la generación real funcione.

La PR está en borrador y las ejecuciones de GitHub Actions reportadas por el conector terminaron en `action_required`; no se ha podido verificar CI aprobado.

## Siguiente bloque de trabajo

1. Identificar el cambio concreto de Magnitude relacionado con iframe y confirmar que es un componente de UI.
2. Ejecutar Open WebUI y revisar sus cabeceras HTTP y redirecciones.
3. Configurar Open WebUI contra la API OpenAI-compatible local de Magnitude y probar generación real con streaming.
4. Probar el embedding en Chromium y Firefox, incluida la sesión/cookies.
5. Verificar que `10100` sigue sano y que `10101` no pisa servicios existentes.
6. Decidir con evidencia si se simplifica la PR nativa #202 o se conserva como alternativa/fallback.

## Decisión de diseño

Seguir el patrón arquitectónico de ODS: interfaz conversacional dedicada y separada de la gestión. Primero validar Open WebUI embebido; evitar duplicar funcionalidades sin evidencia de que el embedding sea viable. El prototipo HTML de LEONES sigue siendo una referencia de interacción, no código de producción.
