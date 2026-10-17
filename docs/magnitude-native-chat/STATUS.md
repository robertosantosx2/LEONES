# Estado de desarrollo — Magnitude Native Chat

Fecha: 2026-10-17

## Repositorios y ramas

- LEONES diseño/prototipo: https://github.com/robertosantosx2/LEONES/tree/feat/magnitude-native-chat
- Especificación: [README.md](README.md)
- Prototipo navegable: [chat-prototype.html](chat-prototype.html)
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

## Estado de validación

**No validado localmente.** La integración GitHub permitió publicar commits y abrir la PR, pero esta sesión no ejecuta Bun/TypeScript ni tiene acceso al Magnitude instalado en Ubuntu. No se afirma que compile ni que la generación real funcione.

La PR está en borrador y las ejecuciones de GitHub Actions reportadas por el conector terminaron en `action_required`; no se ha podido verificar CI aprobado.

Pendiente para pasar a Ready for review:

1. Autorizar/ejecutar los workflows según las reglas de Magnitude.
2. Pasar `web`, `client-common` y `acn` typecheck/build.
3. Añadir o ejecutar tests para parsing SSE, historial, cancelación y colisión de puerto.
4. Probar en máquina real que `http://127.0.0.1:10101/` abre Chat y que `http://127.0.0.1:10100/health` sigue respondiendo.
5. Verificar el comportamiento con el puerto 10101 ocupado por otro proceso.

## Decisión de diseño

Se siguió el patrón de ODS: interfaz conversacional dedicada, historial lateral, selector de modelo, streaming y estados de error; sin copiar su implementación ni sustituir la identidad visual de Magnitude. El prototipo HTML en LEONES es una referencia de interacción, no el código de producción.
