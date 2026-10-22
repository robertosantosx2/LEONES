# Magnitude: rehacer la internacionalización de PR #193 con react-i18next

- **Estado:** preparación técnica en LEONES; no es todavía el PR de upstream.
- **Repositorio destino posterior:** `magnitudedev/magnitude`
- **Fork de trabajo conocido:** `robertosantosx2/magnitude`
- **PR anterior cerrado sin merge:** [#193 — feat(web): expand i18n to twelve languages](https://github.com/magnitudedev/magnitude/pull/193)
- **Rama de referencia del trabajo anterior:** `robertosantosx2/magnitude:feat/i18n-es-zh`
- **Rama LEONES:** `research/magnitude-react-i18next`
- **Decisión de diseño:** conservar el alcance, las traducciones y la auditoría de #193, sustituyendo la capa i18n artesanal por `i18next` + `react-i18next`.

## Objetivo

Preparar una nueva propuesta equivalente en funcionalidad a #193, pero integrada de forma idiomática con React mediante `react-i18next`. No reabrir ni reutilizar el PR cerrado como destino; crear una rama nueva en el fork de Magnitude y abrir un PR nuevo a `magnitudedev/magnitude:main` cuando la implementación y las validaciones estén completas.

La internacionalización no debe quedarse en un selector o en unas pocas pantallas: se mantiene la auditoría de textos visibles, accesibilidad, estados, hardware, errores conocidos y formato de calendario que se cubrió en #193.

## Inventario recuperado de #193

La versión cerrada de #193 confirma el inventario original de doce idiomas y 650 claves por catálogo. Esta nueva propuesta excluye Urdu por escribirse de derecha a izquierda y queda en **11 idiomas activos, 650 claves por catálogo**.
- Auditoría heredada de #193: cero claves ausentes, cero claves extra y cero discrepancias de marcadores de interpolación entre los doce catálogos originales; Urdu queda excluido de esta nueva entrega.
- Pruebas previas para cobertura de catálogos, traducciones representativas, allowlist de idiomas, mensajes de servicio conocidos y preservación de diagnósticos desconocidos.
- Todos los idiomas activos se escriben de izquierda a derecha (LTR); no se incluye ningún idioma RTL.
- Cambio de idioma persistido por perfil de navegador o aplicación de escritorio.
- Auditoría de textos visibles en filtros, adquisición/descarga, estados de modelos, métricas, categorías y especificaciones de hardware, accesibilidad, advertencias de red, errores de almacenamiento de apariencia y etiquetas de fecha/mes/día.
- Los nombres propios, modelos, proveedores, identificadores técnicos y comandos permanecen sin traducir.
- Los mensajes de servicio conocidos pueden localizarse; los diagnósticos desconocidos se conservan literalmente para no inventar una traducción.

### Idiomas activos

| Código | Idioma |
| --- | --- |
| `en` | Inglés |
| `es` | Español |
| `zh-CN` | Chino simplificado |
| `hi` | Hindi |
| `bn` | Bengalí |
| `fr` | Francés |
| `de` | Alemán |
| `ja` | Japonés |
| `pt` | Portugués |
| `it` | Italiano |
| `uk` | Ucraniano |

**Fuera del selector y de los recursos activos de esta entrega:** chino tradicional (`zh-TW`), indonesio (`id`) y coreano (`ko`). El vietnamita (`vi`) se excluyó explícitamente; no recrear su catálogo vacío ni activarlo. Los ficheros históricos de esos idiomas no deben incorporarse accidentalmente al allowlist.

## Código fuente de referencia que se debe aprovechar

La rama anterior `feat/i18n-es-zh` contiene los siguientes activos que deben revisarse y reutilizarse, no reescribirse desde cero:

- `web/src/i18n/catalogs/en.ts`
- `web/src/i18n/catalogs/es.ts`
- `web/src/i18n/catalogs/zh-CN.ts`
- `web/src/i18n/catalogs/hi.ts`
- `web/src/i18n/catalogs/bn.ts`
- `web/src/i18n/catalogs/fr.ts`
- `web/src/i18n/catalogs/de.ts`
- `web/src/i18n/catalogs/ja.ts`
- `web/src/i18n/catalogs/pt.ts`
- `web/src/i18n/catalogs/it.ts`
- `web/src/i18n/catalogs/uk.ts`
- `web/src/i18n/index.test.ts`: inventario de pruebas y comprobaciones de integridad.
- `web/src/i18n/index.ts`: fuente de comportamiento que hay que reemplazar, no copiar como implementación final.
- `.changeset/bright-lions-translate.md`: revisar y adaptar al changeset nuevo; no duplicar sin comprobar la política del repositorio.

La lista de archivos modificados por #193 también identifica componentes ya auditados. Hay que migrar sus llamadas de traducción a `useTranslation()` o a una abstracción React compatible, en vez de conservar funciones globales que leen el idioma en cada render:

`web/src/app.tsx`, `web/src/components/confirm-dialog.tsx`, `copy-command.tsx`, `discovery-visuals.tsx`, `folder-picker.tsx`, `harness-connections.tsx`, `harness-setup.tsx`, `memory-breakdown.tsx`, `model-error.tsx`, `model-fit.tsx`, `model-preference-slider.tsx`, `other-apps.tsx`, `page-skeletons.tsx`, `serving-usage-activity.tsx`, `serving-usage.tsx`, `ui/dialog.tsx`, `remote-access.tsx`, `run.tsx`, `entry/browser.tsx`.

También se deben revisar `web/src/i18n/index.test.ts` y la inicialización del punto de entrada. Esta lista procede del diff de #193; volver a comprobar contra el estado actual de `main` antes de portar, porque el upstream puede haber cambiado desde que se cerró el PR.

## Arquitectura objetivo

### Dependencias

Añadir en el workspace correcto y con el gestor de paquetes que ya use el repositorio:

- `i18next`
- `react-i18next`

No añadir detectores, backends o plugins adicionales si no aportan una necesidad real. La preferencia de idioma ya tiene una clave de compatibilidad que se debe conservar: `magnitude.language`.

### Recursos

Migrar los once catálogos existentes a recursos compatibles con i18next, preservando todas las traducciones y sus claves. Se puede conservar TypeScript si encaja con la configuración del proyecto; no es obligatorio convertirlos a JSON. Estructura sugerida:

```text
web/src/i18n/
  index.ts                 # instancia e inicialización única de i18next
  resources/
    en.ts
    es.ts
    zh-CN.ts
    hi.ts
    bn.ts
    fr.ts
    de.ts
    ja.ts
    pt.ts
    it.ts
    uk.ts
  index.test.ts
```

Se permite mantener el directorio `catalogs/` si eso reduce el tamaño del diff; lo importante es que cada catálogo sea un recurso i18next y no haya una segunda capa paralela de traducción. Mantener las claves existentes, excepto cuando una adaptación estrictamente necesaria a interpolación i18next quede cubierta por pruebas y revisión.

### Inicialización única

La implementación debe crear una sola instancia i18next y registrar `initReactI18next`. Configurar explícitamente:

- `fallbackLng: "en"`
- `supportedLngs` con exactamente los once códigos activos.
- `defaultNS`/namespace explícito y recursos tipados.
- `interpolation.escapeValue: false` para React.
- idioma inicial leído de forma segura de `localStorage["magnitude.language"]`; fallback a inglés si no existe, no es válido o el almacenamiento lanza una excepción.
- al cambiar idioma, persistir el valor cuando el almacenamiento esté disponible.
- actualizar `document.documentElement.lang` y mantener `dir="ltr"` para todos los idiomas activos.
- cambios de idioma reactivos en toda la interfaz, sin evento global manual ni estado React paralelo para mantener sincronizado el catálogo.

La persistencia debe funcionar tanto en navegador como en el renderer de escritorio, sin asumir que `localStorage` existe durante SSR/importación y sin romper la interfaz si el navegador bloquea el almacenamiento. Si se usa un detector estándar, verificar específicamente este caso de fallo; se prefiere un detector pequeño y seguro si permite conservar el comportamiento sin nuevas dependencias.

### Uso en componentes

- Usar `useTranslation()` dentro de componentes React.
- Para utilidades fuera de React, usar la instancia i18next central con una API explícita; no leer `localStorage` repetidamente para traducir.
- El selector llama a `i18n.changeLanguage(code)`; el cambio debe actualizar todos los componentes.
- Mantener los nombres de idiomas en su forma nativa y no traducir nombres de modelos, proveedores, comandos ni otros identificadores técnicos.
- Conservar el tratamiento de mensajes de servicio: mapear sólo mensajes conocidos y exactos a claves; dejar intactos los diagnósticos desconocidos. No traducir automáticamente errores arbitrarios ni inferir su significado.
- No cambiar el idioma del contenido generado por el modelo ni el idioma de diagnósticos desconocidos.

## Plan de migración

1. **Actualizar base:** consultar el estado actual de `magnitudedev/magnitude:main` y del fork; confirmar el estado cerrado de #193 y detectar cambios concurrentes. Crear una rama nueva, por ejemplo `feat/i18next-twelve-languages`, basada en el `main` actualizado del fork.
2. **Extraer activos:** copiar los once catálogos auditados de `feat/i18n-es-zh` sin alterar traducciones. Guardar un inventario/hash por catálogo antes de transformarlos.
3. **Añadir dependencias:** modificar el manifiesto y lockfile con el gestor oficial del repositorio.
4. **Implementar i18next:** recursos, instancia, fallback, allowlist, persistencia segura y sincronización `lang/dir`.
5. **Migrar el selector:** conservar el ajuste de idioma y su texto explicativo; comprobar que cambiar el idioma se refleja inmediatamente en web y desktop.
6. **Migrar llamadas:** sustituir la capa artesanal `useI18n/readLanguage/translate` por APIs i18next en los componentes identificados por el diff de #193. Revisar también los cambios que hayan entrado en `main` desde entonces.
7. **Migrar errores conocidos:** conservar la tabla de equivalencias de mensajes conocidos y el comportamiento de preservación de mensajes desconocidos, ahora conectado al recurso i18next.
8. **Portar y reforzar tests:** conservar las comprobaciones de los 650 mensajes y añadir pruebas específicas de inicialización, cambio de idioma, fallback, persistencia, storage bloqueado, `lang/dir`, renderizado React y mensajes desconocidos.
9. **Changeset y documentación:** crear un changeset apropiado según la política actual del repo y documentar los idiomas activos.
10. **Validar:** typecheck, lint, tests, build web, smoke en navegador y desktop, y comprobaciones del selector y de la dirección LTR. No afirmar que está listo hasta que los comandos reales hayan pasado.
11. **Revisar diff y abrir PR nuevo:** PR draft hacia `magnitudedev/magnitude:main`, explicando que sustituye la propuesta cerrada #193 y enumera los resultados de validación reales.

## Pruebas de aceptación obligatorias

### Integridad de catálogos

- [ ] Exactamente 11 idiomas activos en la allowlist.
- [ ] Cada recurso tiene exactamente las mismas 650 claves que el inglés, salvo cambios de upstream documentados.
- [ ] Ningún valor traducible está vacío o es accidentalmente una copia del inglés sin justificación.
- [ ] Cero marcadores de interpolación perdidos o añadidos. Adaptar el validador a la sintaxis que se elija (`{{name}}` si se usa interpolación i18next; conservar o transformar los antiguos `{name}` de forma sistemática).
- [ ] Ningún catálogo `zh-TW`, `id`, `ko` o `vi` se activa accidentalmente.

### Comportamiento

- [ ] Fallback a inglés para idioma ausente o no soportado.
- [ ] Selección persistente en browser y desktop, con almacenamiento bloqueado y sin `localStorage`.
- [ ] Cambio de idioma reactivo en todos los componentes sin recarga.
- [ ] `document.documentElement.lang` correcto y `dir=ltr` para todos los idiomas activos; no debe quedar configuración RTL específica.
- [ ] Textos visibles y etiquetas accesibles cubiertos por la auditoría de #193.
- [ ] Mensajes conocidos traducidos y diagnósticos desconocidos preservados literalmente.
- [ ] Fechas, meses y días localizados por idioma.
- [ ] Ningún texto visible añadido durante el port queda fuera de la auditoría.

### Validación de entrega

- [ ] Typecheck.
- [ ] Tests de la web.
- [ ] Build de producción.
- [ ] Smoke test navegador.
- [ ] Smoke test aplicación de escritorio.
- [ ] Revisión manual del selector y del flujo de persistencia.
- [ ] Comprobación LTR en los once idiomas activos.
- [ ] CI del PR autorizada y verde; no dejar un estado `action_required` presentado como éxito.
- [ ] Revisión lingüística recomendada, en especial hindi, bengalí, japonés y ucraniano, además de textos de seguridad.

## Estado real heredado (no confundir con validación nueva)

La descripción de #193 registró la auditoría estática de doce catálogos × 650 claves; esta propuesta conserva los once catálogos LTR, cero claves ausentes/extra y cero discrepancias de placeholders. También indicaba que tests, typecheck, build y smoke tests no estaban confirmados como satisfactorios y que la ejecución de GitHub Actions estaba bloqueada por `action_required`. Por tanto, esos resultados de auditoría son reutilizables como punto de partida, pero **no equivalen a una validación de la migración a react-i18next**. Todos los checks deben volver a ejecutarse después de portar.

## Referencias

- PR cerrado #193: https://github.com/magnitudedev/magnitude/pull/193
- Rama fuente: https://github.com/robertosantosx2/magnitude/tree/feat/i18n-es-zh/web/src/i18n
- Inicialización artesanal de referencia: https://github.com/robertosantosx2/magnitude/blob/feat/i18n-es-zh/web/src/i18n/index.ts
- Tests de referencia: https://github.com/robertosantosx2/magnitude/blob/feat/i18n-es-zh/web/src/i18n/index.test.ts

## Próximo paso técnico

Este documento deja fijados el alcance y el diseño en LEONES. La implementación ejecutable debe hacerse después en una rama nueva del fork `robertosantosx2/magnitude`, usando los catálogos anteriores y el `main` actualizado. No modificar ni reabrir #193; el resultado debe ser un PR nuevo con un diff limpio y validaciones repetidas.


## Revisión de upstream — 2026-10-22

Antes de portar la UI se revisó `magnitudedev/magnitude:main`, cuyo HEAD observado era `f81f3cb0b83afa6d08064b48da9b575bc3f81d8a`.

Cambios recientes relevantes:
- `f7170eae`: IDs de modelos locales legibles, configuración de modelos y reanudación de descargas.
- `f81f3cb0`: valores predeterminados de sampling unificados entre Chat Completions, Responses y Anthropic Messages.
- `web/package.json` usa Bun `1.4.2`; el workspace web tiene scripts `test`, `typecheck` y `build`.
- En el `main` revisado no se encontró integración activa de i18next ni `web/src/i18n/catalogs/en.ts`; el port debe partir de los componentes actuales, no reemplazar `app.tsx` completo con la versión antigua de #193.
- Las PR #202 (Native Chat) y #203 (localización del Native Chat) aparecen abiertas/draft en la consulta; #203 está apilada sobre #202. No se deben incorporar sus cambios de chat a este PR general ni asumir que forman parte de `main`.

## Estado de implementación preparatoria — 2026-10-22

Se creó una rama de trabajo en el fork a partir del HEAD upstream revisado:
[`feat/react-i18next-eleven-languages`](https://github.com/robertosantosx2/magnitude/tree/feat/react-i18next-eleven-languages).

Preparación remota ya aplicada en esa rama:
- Reutilizados los once catálogos activos de la rama histórica `feat/i18n-es-zh`, excluyendo `ur`, `zh-TW`, `id`, `ko` y `vi`.
- Convertidos los marcadores de interpolación `{variable}` a `{{variable}}` para i18next.
- Añadido el esqueleto de inicialización `i18next` + `initReactI18next`, con fallback inglés, allowlist de once idiomas, persistencia `magnitude.language`, compatibilidad con el evento `magnitude-language-change` y dirección LTR.
- Añadidas las dependencias `i18next` y `react-i18next` a `web/package.json`, una primera batería de pruebas de catálogos y la importación de inicialización en `web/src/run.tsx`.

**No se considera terminada la migración:** aún falta conectar el selector y migrar los componentes que muestran textos visibles, auditar el diff contra el `main` actual, regenerar `bun.lock` con Bun y ejecutar tests, typecheck, build y pruebas de navegador. Estas tareas necesitan un checkout local para revisar cambios, resolver posibles errores de tipos y validar el comportamiento real; es el siguiente punto para pasar a Ubuntu.
