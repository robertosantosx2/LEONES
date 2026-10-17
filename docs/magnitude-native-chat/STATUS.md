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


## Plan de validación bajo control de LEONES — 17 de octubre de 2026

El propietario no tiene permisos administrativos en `magnitudedev/magnitude`, por lo que no puede autorizar los workflows de la PR upstream. Esto no impide validar el código en el fork controlado `robertosantosx2/magnitude`.

Se añadió en la rama `feat/native-chat-section` el workflow `.github/workflows/native-chat-validation.yml` (commit `c0c173f5b7c3dbca038cb80a55948c531e7f518b`). Se dispara al actualizar esa rama o manualmente desde Actions, y ejecuta en el fork:

1. instalación reproducible con Bun 1.4.2 y lockfile congelado;
2. typecheck de `packages/client-common`;
3. typecheck web;
4. suite de pruebas web, incluida la nueva prueba de parser SSE;
5. build web.

**Este workflow está preparado, no validado todavía:** hasta consultar una ejecución real no se puede afirmar que haya pasado. Si GitHub Actions está desactivado en el fork, el propietario del fork debe habilitarlo en Settings → Actions; después se puede ejecutar desde la pestaña Actions → “Native Chat validation (fork)” → Run workflow.

La validación local/integrada de Open WebUI, la inferencia real y el comportamiento de puertos requieren además un entorno ejecutable con Magnitude y un servidor/modelo local. No se simularán como pruebas superadas. Los resultados del fork se registrarán como evidencia de desarrollo, pero no sustituyen la autorización ni los checks requeridos por la PR #202 upstream.


## Seguimiento — corrección del cierre SSE

En el fork de Magnitude se corrigió el lector de streaming para que deje de leer al recibir el marcador terminal SSE `[DONE]`, cancele el lector sin depender de que el servidor cierre la conexión inmediatamente y reconozca cancelaciones usando `Error.name === "AbortError"`.

- Commit: `0cebd29df64b2b1058263d26a4f027a2063232d1`
- PR #202 actualizada con el alcance de la corrección y el workflow de validación del fork.
- No se ha confirmado todavía que GitHub Actions haya ejecutado el workflow del fork; la corrección está publicada, pero no verificada mediante tests.
- La validación funcional requiere aún ejecutar las pruebas, typecheck y build; después, en Ubuntu, probar generación real, cancelación, Open WebUI y los puertos 10100/10101.


### Segunda corrección de ciclo de vida

Se corrigió también la eliminación de una conversación durante una generación: el envío se aborta y la finalización del stream ya no debe reinsertar esa conversación en el historial local.

- Commits de seguimiento: `9a35fdc0`, `f31faab8`, `2695baec`.
- La PR #202 se actualizó para reflejar este cambio.
- Estas correcciones siguen pendientes de verificación por tests y typecheck; no equivalen a una validación ejecutada.


### Ampliación del workflow de CI del fork

El workflow `.github/workflows/native-chat-validation.yml` incluye ahora también el typecheck de `packages/acn`, para cubrir el código de servidor que crea el listener opcional.

- Commit de workflow: `cad987813b465b4b4ae76a29c59a12491ec04077`.
- Se actualizó el cuerpo de la PR #202 con esta cobertura.
- No se dispone de un resultado de ejecución verificable a través de la integración de GitHub utilizada en esta sesión; el estado continúa siendo **pendiente de ejecución/confirmación**.


## CI del fork — resultado y corrección (17 de octubre de 2026)

La primera ejecución verificable del workflow del fork ya terminó. Run [#6](https://github.com/robertosantosx2/magnitude/actions/runs/39020134309), probado sobre el commit `cad987813b465b4b4ae76a29c59a12491ec04077`:

- Instalación reproducible con Bun 1.4.2: **superada**.
- Typecheck `packages/client-common`: **superado**.
- Typecheck `web`: **superado**.
- Typecheck `packages/acn`: **superado**.
- Suite de tests web: **falló**, con 182 tests superados y 1 fallido de 183.
- Build web: **no ejecutado**, porque el workflow se detuvo al fallar la suite.

El test fallido fue `web/src/styles/tailwind-boundaries.test.ts`: encontró en la nueva UI de Chat los tonos Tailwind `red-50`, `red-900`, `red-950` y `blue-950`, que no existen en las escalas exportadas por `packages/client-common/src/utils/palette.ts`. Se corrigió `web/src/components/chat-page.tsx` para usar tonos ya definidos: fondo de error `rose-200/30`, tonos oscuros `red-800`/ `slate-900` y tonos azules `blue-900`.

- Commit correctivo: `0e4722c81b56836e8f9bdebc3224b9e71163bcce`.
- Run de validación posterior: [#7](https://github.com/robertosantosx2/magnitude/actions/runs/39020998471), en cola al registrar esta actualización.
- El cierre de GitHub mostró además una advertencia de submódulo `inference/native/llama-cpp-rs` sin URL en `.gitmodules`; no fue la causa del fallo de tests, pero debe revisarse si afecta a otras tareas de CI.

No considerar todavía superados los tests ni el build hasta que el run #7 termine. Sigue pendiente la prueba real de inferencia, cancelación, listener 10100/10101 y Open WebUI; la PR upstream #202 permanece en borrador.


### Estado del run #7 al último seguimiento

El run [#7](https://github.com/robertosantosx2/magnitude/actions/runs/39020998471), sobre el commit `0e4722c81b56836e8f9bdebc3224b9e71163bcce`, ha progresado después de la corrección:

- Instalación: superada.
- Typecheck `packages/client-common`: superado.
- Typecheck `web`: superado tras el cambio de tonos.
- Typecheck `packages/acn`: en ejecución al consultar el estado.
- Tests web y build: pendientes de ejecución.

Por tanto, la corrección de paleta ha superado los dos typechecks visibles hasta ahora, pero todavía no hay resultado final del workflow. No afirmar que el run está verde hasta que concluya.


## Resultado final de validación automatizada del fork — 17 de octubre de 2026

El run [#7 de Native Chat validation (fork)](https://github.com/robertosantosx2/magnitude/actions/runs/39020998471), para el commit `0e4722c81b56836e8f9bdebc3224b9e71163bcce`, terminó con conclusión **success**.

Pasos completados con éxito:
- Instalación reproducible con Bun 1.4.2 y lockfile congelado.
- Typecheck de `packages/client-common`.
- Typecheck de `web`.
- Typecheck de `packages/acn`.
- Suite de tests de Web.
- Build de Web.

Esto confirma que la corrección de la paleta eliminó el fallo de la ejecución #6 y que el workflow configurado pasa en el fork. Es una validación automatizada del workspace cubierto; no demuestra todavía la inferencia real, el comportamiento de puertos en ejecución ni la compatibilidad del iframe con una instancia Open WebUI auténtica.

### Bloqueante siguiente: pruebas de integración en Ubuntu

La fase siguiente necesita ejecutar Magnitude con un modelo local y probar:
1. `/health`, `/inference/v1/models` y una generación real con streaming y cancelación.
2. Que `127.0.0.1:10100` conserva la administración y la API.
3. Que `127.0.0.1:10101` abre Chat y, si el puerto está ocupado, el proceso principal sigue sano sin apropiarse del puerto ajeno.
4. Open WebUI real: CSP, X-Frame-Options, login/sesión, API y streaming en navegador.
5. Que borrar una conversación durante la generación no la vuelve a introducir en el historial.

La PR upstream [#202](https://github.com/magnitudedev/magnitude/pull/202) sigue abierta como borrador. Los checks upstream que requieren autorización del mantenedor y la revisión del mantenedor siguen siendo pasos distintos de este workflow del fork.


### Detalle de logs del run #7

Se inspeccionaron los logs del job, no solo el resumen:
- Vitest: **16 archivos de test y 183 tests superados**.
- Build Vite: completado; 5.849 módulos transformados.
- El build muestra un aviso no bloqueante: el bundle JavaScript principal queda por encima de 500 kB minificados (aprox. 1.245 kB, gzip aprox. 379 kB). No rompe la compilación, pero se puede optimizar con code splitting en una iteración posterior.
- Durante la limpieza del checkout GitHub mostró un warning de Git sobre el submódulo `inference/native/llama-cpp-rs` sin URL en `.gitmodules`. El job terminó correctamente y no fue la causa de fallo; merece una revisión independiente del repositorio.

La validación CI del fork está, por tanto, verde. No se ha encontrado en esta sesión un test automatizado de integración que arranque el segundo listener real y fuerce un conflicto de puerto; esa comprobación sigue en la lista de pruebas de runtime.
