# Investigación y desarrollo: Chat integrado en Magnitude

**Fecha:** 17 de octubre de 2026  
**Estado:** investigación documentada; integración con Open WebUI pendiente de prueba; PR nativa #202 sigue en borrador.

## Objetivo

Incorporar una experiencia conversacional accesible desde la barra lateral de Magnitude, separando el uso de modelos de las funciones de administración. La arquitectura debe priorizar ejecución local, no introducir telemetría de prompts ni fallback en la nube por sorpresa, y conservar el servicio principal de Magnitude.

## Opciones estudiadas

### A. Chat nativo en Magnitude

La PR [#202](https://github.com/magnitudedev/magnitude/pull/202) propone una página Chat propia, reutilizando los componentes web y la API de inferencia de Magnitude.

Incluye en la rama de trabajo:

- Entrada Chat en el contrato compartido de navegación y en la barra lateral.
- Selector de modelos basado en los IDs devueltos por `/inference/v1/models`.
- Peticiones OpenAI-compatible a `/inference/v1/chat/completions`, con streaming SSE y renderizado incremental.
- Cancelación, nueva conversación, historial en `localStorage`, selección/eliminación de conversaciones y estados de error.
- Listener opcional adicional en `127.0.0.1:10101` para abrir directamente Chat; el servicio/API principal permanece en `127.0.0.1:10100`.
- Documentación de privacidad local y resolución de problemas.

**Límite de validación:** los cambios se prepararon mediante la integración de GitHub, pero no se ha ejecutado en este entorno el typecheck, los tests, el build web ni una generación real. La PR es un borrador y no se debe presentar como validada.

### B. Open WebUI embebido en una página Chat

Flujo propuesto:

`Magnitude → Chat en la barra lateral → iframe local de Open WebUI → API OpenAI-compatible de Magnitude`

La motivación es reutilizar en Open WebUI el historial, el selector de modelos y el streaming, evitando mantener dos clientes de chat si el embedding resulta fiable. Magnitude seguiría siendo el motor local y la superficie de gestión.

Un iframe básico podría tener esta forma ilustrativa:

```html
<iframe
  src="http://127.0.0.1:3000/"
  title="Chat de Open WebUI"
  loading="lazy"
  style="width: 100%; height: 100%; border: 0;"
></iframe>
```

La URL y el puerto son solo un ejemplo; deben confirmarse con la instalación real. Este fragmento no constituye una integración lista para producción.

## Hallazgos sobre iframe y tamaño adaptable

Hay que distinguir tres características:

1. **Elemento `<iframe>`:** ampliamente soportado por navegadores modernos.
2. **Carga diferida `loading="lazy"`:** opción ampliamente soportada para evitar cargar la interfaz de Chat hasta que se necesite.
3. **Nuevo tamaño intrínseco adaptable:** Chrome 154 anunció el 22 de septiembre de 2026 `frame-sizing: content-height`, `window.requestResize()` y el opt-in `<meta name="responsive-embedded-sizing" content="allow-origins=*">`. Las referencias consultadas lo marcan como de disponibilidad limitada/experimental, sin soporte confirmado en Firefox y Safari.

Para una aplicación de chat, la altura debe ocupar el contenedor disponible; no es necesario que el iframe crezca hasta abarcar todo el historial. Por tanto, la propuesta inicial es `width: 100%; height: 100%` y, cuando proceda, `loading="lazy"`. El nuevo tamaño adaptable no debe ser requisito para la integración.

### Fuentes primarias

- [Chrome for Developers — New in Chrome 154](https://developer.chrome.com/blog/new-in-chrome-154) (22-09-2026).
- [MDN — CSS `frame-sizing`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/frame-sizing).
- [MDN — `responsive-embedded-sizing`](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/meta/name/responsive-embedded-sizing).
- [MDN — `window.requestResize()`](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestResize).
- [MDN — elemento iframe](https://developer.mozilla.org/es/docs/Web/HTML/Reference/Elements/iframe).
- [MDN — carga diferida de iframe](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#loading).
- [Open WebUI — Hardening](https://docs.openwebui.com/getting-started/advanced-topics/hardening/).
- [Open WebUI — variables de entorno](https://docs.openwebui.com/reference/env-configuration/).

## Compatibilidad y seguridad: cuestiones sin resolver

Que el navegador soporte iframes no significa que Open WebUI permita ser incrustado. Antes de elegir esta opción hay que probar:

1. **Cabeceras del servidor:** inspeccionar `Content-Security-Policy` (especialmente `frame-ancestors`) y `X-Frame-Options`. La configuración de hardening de Open WebUI puede denegar el embedding. No desactivar globalmente protecciones de seguridad como solución rápida; preferir una configuración explícita y limitada, revisada.
2. **Autenticación, cookies y sesión:** distintos puertos representan orígenes distintos; las políticas de cookies y el almacenamiento separado pueden afectar al inicio de sesión.
3. **Conectividad de la API:** configurar Open WebUI para usar el endpoint compatible con OpenAI que exponga Magnitude. Si Open WebUI corre en Docker, `127.0.0.1` dentro del contenedor apunta al propio contenedor, no necesariamente al host.
4. **Streaming real:** verificar una generación completa, no solo que la página se renderiza.
5. **Ciclo de vida:** mostrar un error claro si Open WebUI no está instalado o no responde; no instalar ni iniciar servicios inesperadamente.
6. **Exposición de red:** mantener los servicios en loopback por defecto, no poner secretos en URLs y no exponer una API sin autenticación a la red.
7. **Colisión del puerto 10101:** confirmar que está libre. La API canónica de Magnitude debe seguir en 10100; el listener secundario no debe detener ni sustituir otro proceso.

## Qué se ha buscado en el código de Magnitude

La búsqueda en la rama principal encontró una referencia a `iframe` en `packages/dom-extract/src/mappings.ts`, donde se enumera como elemento DOM que se examina durante la extracción. Las búsquedas de `frame-sizing` y `iframe component` no localizaron un componente de interfaz para incrustar aplicaciones externas. Esto **no demuestra que no exista trabajo reciente en otra rama o PR**; queda pendiente identificar el commit/PR concreto al que se hacía referencia.

## Plan de validación

- [ ] Identificar el cambio reciente de Magnitude sobre iframe y confirmar si es un componente UI, no solo extracción DOM o automatización del navegador.
- [ ] Ejecutar Open WebUI local y revisar cabeceras HTTP, redirecciones y autenticación.
- [ ] Configurar Open WebUI contra la API local de Magnitude y comprobar listado de modelos y generación real.
- [ ] Probar embedding en Chromium y Firefox; revisar consola, cookies, sesión y streaming.
- [ ] Verificar historial y selector de modelo en la interfaz embebida.
- [ ] Comprobar salud de `127.0.0.1:10100` y el comportamiento de `10101`, incluido el caso de puerto ocupado.
- [ ] Ejecutar typecheck, tests y build de la rama de PR #202.
- [ ] Con evidencia, decidir si se simplifica la PR nativa, si se opta por Open WebUI o si se conserva Chat nativo como alternativa/fallback.

## Decisión provisional

**No sustituir todavía la implementación nativa por un iframe.** Primero comprobar que Open WebUI permite embedding seguro, mantiene sesión y se comunica correctamente con Magnitude. El chat debe seguir siendo local-first y la integración debe ser opt-in o fallar con un estado claro cuando el componente externo no esté disponible.

El patrón arquitectónico deseado sigue siendo separar la interfaz conversacional de la gestión, como en ODS, pero sin duplicar funcionalidades antes de validar la viabilidad técnica.

## Enlaces de trabajo

- [PR upstream #202 — Chat nativo](https://github.com/magnitudedev/magnitude/pull/202).
- [Rama de diseño y seguimiento en LEONES](https://github.com/robertosantosx2/LEONES/tree/feat/magnitude-native-chat).
- [Estado del trabajo](https://github.com/robertosantosx2/LEONES/blob/feat/magnitude-native-chat/docs/magnitude-native-chat/STATUS.md).
- [ADR Open WebUI + iframe](https://github.com/robertosantosx2/LEONES/blob/feat/magnitude-native-chat/docs/magnitude-native-chat/ADR-openwebui-iframe.md).


## Actualización de implementación — 17 de octubre de 2026

Se ha añadido a la rama controlada de `robertosantosx2/magnitude` una primera integración optativa de Open WebUI dentro de la página Chat:

- Botón **Open WebUI** en la vista nativa y retorno mediante **Back to native Chat**.
- Campo de URL configurable; por defecto sugiere `http://127.0.0.1:3000/`, que es un ejemplo y debe coincidir con la instalación real.
- Validación que limita el iframe a URLs HTTP(S) de loopback (`localhost`, `127.0.0.1`, `[::1]`), rechaza credenciales y esquemas no web, y elimina fragmentos.
- Persistencia local de la URL configurada y carga del iframe solo al abrir la vista.
- Pruebas unitarias escritas para URL válida, rechazo de hosts remotos, credenciales, esquemas no permitidos, valores malformados y fragmentos.
- Documentación de uso, seguridad y resolución de problemas en inglés dentro del fork.

**No está validado aún:** no se han ejecutado typecheck, tests, build ni pruebas end-to-end con Open WebUI real. La política CSP/X-Frame-Options, las cookies, el inicio de sesión, la conexión de Open WebUI a la API de Magnitude y el streaming real siguen pendientes de pruebas.


Guía de conexión en el fork (inglés): [Open WebUI with Magnitude](https://github.com/robertosantosx2/magnitude/blob/feat/native-chat-section/docs/clients/open-webui.mdx). Describe la URL de API que necesita Open WebUI, la diferencia entre ejecutar en el host y en Docker, los requisitos de API key/acceso de red y la lista de aceptación end-to-end.
