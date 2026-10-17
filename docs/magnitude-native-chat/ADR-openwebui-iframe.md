# ADR: Open WebUI embebido en Magnitude mediante iframe

Fecha: 2026-10-17  
Estado: propuesta en validación; no asumir compatibilidad hasta probarla en ejecución.

## Decisión propuesta

Priorizar una integración opcional de Open WebUI dentro de una sección lateral **Chat** de Magnitude, antes de mantener un segundo cliente de chat propio. Open WebUI ya aporta historial, selector/modelos y streaming; Magnitude debe seguir siendo el motor y la interfaz de gestión.

Flujo objetivo:

`Magnitude → Chat (sidebar) → iframe local de Open WebUI → API OpenAI-compatible de Magnitude`

El puerto deseado `http://127.0.0.1:10101/` puede servir como entrada local de Chat si se demuestra que puede hacerse sin romper el servicio/API de Magnitude en `10100`. No debe arrancarse un segundo proceso oculto ni cambiarse el puerto principal silenciosamente.

## Lo confirmado sobre navegadores e iframes

Hay que separar tres características distintas:

1. **El elemento `<iframe>`** es ampliamente soportado por los navegadores modernos.
2. **Carga diferida** mediante `loading="lazy"` está soportada por los navegadores modernos y conviene usarla si Chat no está visible al abrir Magnitude.
3. **Nuevo tamaño intrínseco responsive de iframes** — `frame-sizing: content-height`, `window.requestResize()` y `<meta name="responsive-embedded-sizing" ...>` — es la novedad de Chrome 154 anunciada el 22 de septiembre de 2026. A la fecha de esta investigación, está marcada como disponibilidad limitada/experimental: las fuentes consultadas indican soporte en Chrome 154, no en Firefox ni Safari.

Fuentes primarias:
- Chrome for Developers, Chrome 154 (22 sep 2026): https://developer.chrome.com/blog/new-in-chrome-154
- MDN, `frame-sizing` (Limited availability): https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/frame-sizing
- MDN, `responsive-embedded-sizing` (Limited availability): https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/meta/name/responsive-embedded-sizing
- MDN, `window.requestResize()`: https://developer.mozilla.org/en-US/docs/Web/API/Window/requestResize
- MDN, elemento iframe: https://developer.mozilla.org/es/docs/Web/HTML/Reference/Elements/iframe
- Carga diferida: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#loading

### Consecuencia para un chat

El chat es una aplicación de altura completa, no un widget cuya altura deba ajustarse a todo su contenido. Por tanto, **no dependeremos de `frame-sizing: content-height` para el layout principal**. Usaremos un contenedor de altura disponible y un iframe con `width: 100%; height: 100%` (y `loading="lazy"` si la ruta no se ha abierto aún). El nuevo sizing puede evaluarse para embeds pequeños, pero no es necesario para la experiencia de chat y no debe ser requisito para Firefox/Safari.

## Distinción importante sobre Magnitude

La búsqueda de código en la rama principal de Magnitude encontró `iframe` en `packages/dom-extract/src/mappings.ts`, donde figura como elemento DOM que se expande/examina durante la extracción. La búsqueda del código por `frame-sizing` y `iframe component` no devolvió resultados. Esto no demuestra que no exista una implementación reciente en otra rama o PR; solo significa que no he identificado en la rama principal un componente de UI para incrustar aplicaciones externas. Antes de depender de ese cambio hay que identificar el commit/PR concreto.

## Bloqueos técnicos que deben probarse

1. **Política del servidor embebido:** comprobar `Content-Security-Policy: frame-ancestors` y `X-Frame-Options` de Open WebUI. Si bloquea el embedding, no desactivar globalmente las protecciones; preferir una configuración acotada o proxy local revisado.
2. **Cookies y sesión:** distintos puertos son distintos orígenes; el almacenamiento es separado y las políticas de cookies de terceros pueden afectar al inicio de sesión.
3. **Conectividad:** configurar Open WebUI para usar el endpoint OpenAI-compatible de Magnitude. Si Open WebUI corre en Docker, `127.0.0.1` dentro del contenedor no es el host.
4. **Ciclo de vida:** Chat debe mostrar un estado claro si Open WebUI no está instalado/no responde; no instalar ni iniciar servicios de forma inesperada.
5. **Seguridad local:** enlazar servicios solo a loopback por defecto, no incluir secretos en URL y no exponer la API sin autenticación a la red.
6. **Puerto 10101:** confirmar que no está ocupado y definir el comportamiento de colisión; conservar `10100` para la API.

## Plan de validación

- [ ] Identificar el commit/PR reciente de Magnitude que implementa el soporte de iframe y confirmar si es un componente de interfaz, no solo extracción DOM o automatización del navegador.
- [ ] Ejecutar Open WebUI local y verificar sus cabeceras HTTP y redirecciones.
- [ ] Configurar Open WebUI con el endpoint local de Magnitude y comprobar `/models` y una generación real.
- [ ] Abrir Open WebUI dentro de Chat en Chrome/Chromium y Firefox; revisar consola, cookies y streaming.
- [ ] Confirmar historial, selector de modelo y streaming de Open WebUI contra Magnitude.
- [ ] Verificar que el API de Magnitude en `10100` sigue sano y que `10101` no pisa otros servicios.
- [ ] Solo entonces decidir si se simplifica la implementación nativa propuesta en https://github.com/magnitudedev/magnitude/pull/202 o si se conserva como alternativa/fallback.

## Resultado actual

- Soporte del elemento `<iframe>` en navegadores: confirmado.
- Carga diferida `loading="lazy"`: opción recomendada para no cargar Chat hasta necesitarlo.
- Nuevo responsive intrinsic sizing de Chrome 154: confirmado, pero no multiplataforma; no es necesario para un chat de altura completa.
- Permiso de Open WebUI para ser embebido: pendiente de comprobación empírica.
- Componente de embedding externo ya implementado en la UI de Magnitude: no confirmado en la rama principal por las búsquedas realizadas.
- Integración final y prueba de generación: pendientes.
