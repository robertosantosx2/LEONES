# ADR: Open WebUI embebido en Magnitude mediante iframe

Fecha: 2026-10-17  
Estado: propuesta en validación; no asumir compatibilidad hasta probarla en ejecución.

## Decisión propuesta

Priorizar una integración opcional de Open WebUI dentro de una sección lateral **Chat** de Magnitude, antes de mantener un segundo cliente de chat propio. Open WebUI ya aporta historial, selector/modelos y streaming; Magnitude debe seguir siendo el motor y la interfaz de gestión.

Flujo objetivo:

`Magnitude → Chat (sidebar) → iframe local de Open WebUI → API OpenAI-compatible de Magnitude`

El puerto deseado `http://127.0.0.1:10101/` puede servir como entrada local de Chat si se demuestra que puede hacerse sin romper el servicio/API de Magnitude en `10100`. No debe arrancarse un segundo proceso oculto ni cambiarse el puerto principal silenciosamente.

## Compatibilidad: lo que sí está confirmado

El elemento HTML `<iframe>` está ampliamente soportado en navegadores modernos (Chrome/Chromium, Firefox, Safari y Edge). MDN lo marca como Baseline/Widely available; Can I Use informa de soporte global aproximado del 97.5% en su tabla consultada.

Referencias:
- MDN: https://developer.mozilla.org/es/docs/Web/HTML/Reference/Elements/iframe
- Can I Use: https://caniuse.com/mdn-html_elements_iframe

Esto solo confirma que el navegador implementa el elemento. **No confirma que una web concreta permita ser cargada dentro de un iframe.**

## Distinción importante sobre Magnitude

La búsqueda de código en la rama principal de Magnitude encontró `iframe` en `packages/dom-extract/src/mappings.ts`, donde figura como elemento DOM que se expande/examina durante la extracción. Eso no demuestra que la interfaz web de Magnitude ya tenga un contenedor de iframe para incrustar aplicaciones externas. Hay que identificar y revisar el cambio reciente concreto al que se refiere la conversación antes de depender de él.

## Bloqueos técnicos que deben probarse

1. **Política del servidor embebido:** comprobar `Content-Security-Policy: frame-ancestors` y `X-Frame-Options` de Open WebUI. Si bloquea el embedding, no desactivar globalmente las protecciones; preferir una configuración acotada o proxy local revisado.
2. **Cookies y sesión:** distintos puertos son distintos orígenes; el almacenamiento es separado y las políticas de cookies de terceros pueden afectar al inicio de sesión.
3. **Conectividad:** configurar Open WebUI para usar el endpoint OpenAI-compatible de Magnitude. Si Open WebUI corre en Docker, `127.0.0.1` dentro del contenedor no es el host.
4. **Ciclo de vida:** Chat debe mostrar un estado claro si Open WebUI no está instalado/no responde; no instalar ni iniciar servicios de forma inesperada.
5. **Seguridad local:** enlazar servicios solo a loopback por defecto, no incluir secretos en URL y no exponer la API sin autenticación a la red.
6. **Port 10101:** confirmar que no está ocupado y definir el comportamiento de colisión; conservar `10100` para la API.

## Plan de validación

- [ ] Identificar el commit/PR reciente de Magnitude que implementa el soporte de iframe y confirmar si es un componente de interfaz, no solo extracción DOM o automatización del navegador.
- [ ] Ejecutar Open WebUI local y verificar sus cabeceras HTTP y redirecciones.
- [ ] Configurar Open WebUI con el endpoint local de Magnitude y comprobar `/models` y una generación real.
- [ ] Abrir Open WebUI dentro de Chat en Chrome/Chromium y Firefox; revisar consola, cookies y streaming.
- [ ] Confirmar historial, selector de modelo y streaming de Open WebUI contra Magnitude.
- [ ] Verificar que el API de Magnitude en `10100` sigue sano y que `10101` no pisa otros servicios.
- [ ] Solo entonces decidir si se simplifica la implementación nativa propuesta en https://github.com/magnitudedev/magnitude/pull/202 o si se conserva como alternativa/fallback.

## Resultado actual

- Soporte de `<iframe>` en navegadores: confirmado.
- Permiso de Open WebUI para ser embebido: pendiente de comprobación empírica.
- Componente de embedding externo ya implementado en la UI de Magnitude: no confirmado por la búsqueda realizada.
- Integración final y prueba de generación: pendientes.
