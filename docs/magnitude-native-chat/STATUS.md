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


Guía operativa en inglés para configurar Open WebUI contra Magnitude: https://github.com/robertosantosx2/magnitude/blob/feat/native-chat-section/docs/clients/open-webui.mdx. Incluye el caso Docker/host, el acceso de red/API key y la lista de pruebas end-to-end. La guía es documentación, no evidencia de que las pruebas se hayan superado.


## Criterios de aceptación para la entrega upstream

La PR existente [#202](https://github.com/magnitudedev/magnitude/pull/202) es el único destino upstream para este trabajo; no abrir una PR duplicada. Mantenerla en borrador hasta que la validación esté respaldada por resultados verificables.

- [ ] **Magnitude sigue siendo el servicio principal:** inferencia local y administración no se sustituyen ni se deshabilitan.
- [ ] **Chat desde la barra lateral:** la navegación es accesible y los estados de carga/error están cubiertos.
- [ ] **Open WebUI es optativo:** validar CSP/X-Frame-Options, autenticación/sesión, conexión al endpoint de Magnitude y streaming real. Si falla, el Chat nativo sigue disponible.
- [ ] **Puerto 10100:** comprobar salud del servicio principal y API antes y después de abrir Chat.
- [ ] **Puerto 10101:** listener adicional solo en loopback; si está ocupado, no matar ni sustituir al proceso existente y mantener sano 10100.
- [ ] **Pruebas automatizadas:** typecheck de web, client-common y ACN; pruebas unitarias de streaming SSE, cancelación, historial, validador URL y listener opcional.
- [ ] **Build y CI:** web build y workflows de GitHub Actions completados sin bloqueos de autorización.
- [ ] **Prueba de ejecución real:** modelo listado, generación con streaming, cancelación y persistencia; registrar entorno y resultados.
- [ ] **Seguridad:** no aceptar hosts remotos ni credenciales en la URL del iframe; no relajar CSP globalmente, no filtrar secretos y no exponer servicios fuera de loopback por defecto.
- [ ] **Documentación upstream en inglés:** configuración, arquitectura, privacidad, límites conocidos, puertos, troubleshooting y evidencia de validación.
- [ ] **Revisión final:** actualizar el cuerpo de la PR #202 con resultados reales; solo marcarla lista para revisión cuando los checks anteriores estén satisfechos o las limitaciones restantes estén explícitamente acordadas con mantenedores.

## Registro de evidencias

No se debe declarar una casilla completada solo porque exista código o documentación. Para cada comprobación, registrar comando o procedimiento, resultado, commit probado y enlace al workflow/log cuando exista. En este momento, typecheck, tests, build, CI aprobado y smoke test de inferencia/Open WebUI siguen pendientes de evidencia.


## Seguimiento de implementación — 17 de octubre de 2026 (continuación)

Se ha avanzado en la rama de implementación del fork robertosantosx2/magnitude (feat/native-chat-section):

- Se ha extraído el procesamiento de eventos SSE a web/src/components/chat-stream.ts.
- Se ha añadido web/src/components/chat-stream.test.ts para cubrir deltas incrementales, marcador [DONE], líneas de keepalive, errores del servidor y JSON malformado.
- Se ha añadido una acción New chat visible en pantallas estrechas; antes el único botón estaba dentro de la barra lateral oculta en móvil.
- La navegación web confirma que / en el puerto 10101 selecciona chat, mientras que 10100 mantiene la página inicial normal. La selección se hace según window.location.port, sin cambiar el servicio de inferencia.

Commits recientes del fork: b720f279, 9ee2d5db, 690d08cc, dcc9cece, e98013a3 (la rama puede recibir commits adicionales).

### Validación y bloqueo actual

La consulta de GitHub Actions para el HEAD observado de la PR #202 devolvió workflows con conclusión action_required, no un resultado de tests fallidos ni un CI aprobado. Hace falta que una persona con permisos en el repositorio upstream autorice la ejecución de los workflows de la contribución externa. No se debe afirmar que las pruebas pasan hasta que se ejecuten.

La nueva cobertura SSE está escrita, pero no ejecutada. Siguen pendientes:
- Typecheck y tests del workspace, incluido el nuevo test SSE y el test del validador de URL.
- Build web.
- Prueba end-to-end contra Open WebUI real (cabeceras, login/sesión, API, streaming, Chromium y Firefox).
- Prueba de inferencia local y de los puertos 10100/10101, incluido el puerto 10101 ocupado.
- Confirmación de CI después de autorizar workflows.

La PR upstream #202 continúa abierta y en borrador. No se debe marcar lista para revisión hasta obtener estas evidencias o acordar explícitamente las limitaciones restantes con los mantenedores.
