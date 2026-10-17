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

## Investigación de la alternativa Open WebUI + iframe

Se ha documentado una alternativa para evitar mantener un chat propio: añadir **Chat** al menú lateral de Magnitude y mostrar una instancia local de Open WebUI, configurada para usar la API OpenAI-compatible de Magnitude.

- Compatibilidad del elemento HTML `<iframe>` en navegadores modernos: confirmada mediante MDN y Can I Use.
- Que Open WebUI permita ser cargado en un iframe: pendiente de verificar sus cabeceras `Content-Security-Policy` / `frame-ancestors` y `X-Frame-Options`.
- Que la reciente implementación de iframe en Magnitude sea un componente de UI para incrustar sitios: no confirmado. La búsqueda del código encontró una referencia en extracción/procesamiento DOM, que no basta para concluir que exista ese componente.
- Conexión de Open WebUI con el endpoint local de Magnitude, sesión/cookies, streaming y puertos 10100/10101: pendiente de prueba.
- La PR #202 sigue en borrador; se ha añadido un comentario indicando que la alternativa está bajo evaluación. No se afirma que la nueva arquitectura funcione.

Ver el plan y las condiciones en [ADR-openwebui-iframe.md](ADR-openwebui-iframe.md).

## Estado de validación de la implementación nativa

**No validado localmente.** La integración GitHub permitió publicar commits y abrir la PR, pero esta sesión no ejecuta Bun/TypeScript ni tiene acceso al Magnitude instalado en Ubuntu. No se afirma que compile ni que la generación real funcione.

La PR está en borrador y las ejecuciones de GitHub Actions reportadas por el conector terminaron en `action_required`; no se ha podido verificar CI aprobado.

Pendiente para pasar a Ready for review (nativa o alternativa iframe):

1. Identificar el cambio concreto de Magnitude relacionado con iframe y confirmar que se puede reutilizar desde la UI.
2. Verificar las políticas de embedding de Open WebUI y el comportamiento de sesión/cookies.
3. Configurar Open WebUI contra la API local de Magnitude y probar una generación real con streaming.
4. Autorizar/ejecutar workflows según las reglas de Magnitude y pasar typecheck/build.
5. Probar que `http://127.0.0.1:10101/` abre Chat y que `http://127.0.0.1:10100/health` sigue respondiendo, incluyendo colisión del puerto 10101.
6. Decidir con evidencia si se simplifica la PR para usar Open WebUI o se conserva el chat nativo como alternativa.

## Decisión de diseño

Se sigue el patrón de ODS: interfaz conversacional dedicada y separada de la gestión. Se prioriza validar si Open WebUI puede reutilizarse dentro de Magnitude mediante iframe, antes de invertir más en duplicar selector, historial y streaming. El prototipo HTML de LEONES sigue siendo una referencia de interacción, no código de producción.
