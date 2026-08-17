# LEONES — Marco de diseño y desarrollo web

**Documento normativo y de referencia obligatoria para la web de LEONES.**

- **Estado:** vigente
- **Ámbito:** `web/` y todos sus recursos, scripts y procesos de publicación
- **Principio rector:** **minimalista para el humano, estructurada para la máquina**
- **Última revisión:** 2026-08-17

> Este documento no es una guía de estilo opcional. Es el contrato que debe seguir cualquier nueva página, modificación o refactor de la web de LEONES.

---

## 1. Objetivo

La web de LEONES debe permitir que una persona pueda **entender, revisar y auditar** el proyecto rápidamente, sin que la interfaz compita con el contenido.

La web debe ser:

1. **Funcional:** todos los enlaces, menús y recursos deben funcionar.
2. **Minimalista:** sólo se incorpora decoración que ayude a comprender o navegar.
3. **Legible:** el contenido debe poder revisarse cómodamente por una persona.
4. **Semántica:** el HTML debe expresar la estructura real del documento.
5. **Mantenible:** cada responsabilidad debe estar en el fichero apropiado.
6. **Accesible:** teclado, foco, etiquetas semánticas y estados deben estar contemplados.
7. **Robusta:** el contenido debe seguir siendo visible aunque falle JavaScript.
8. **Coherente:** una nueva página debe parecer parte de LEONES sin copiar CSS de otra página.
9. **Auditable:** las decisiones importantes deben poder localizarse y explicarse.

---

## 2. Decisiones congeladas

Estas decisiones forman parte del sistema y no deben modificarse casualmente.

### 2.1. Separación de responsabilidades

```text
HTML       → contenido y estructura semántica
CSS        → presentación y layout
JavaScript → comportamiento e interacción
SVG        → identidad gráfica e iconografía
GitHub     → versión, revisión y publicación
Prettier   → formato automático del código
```

**Los SVG no son el formato de los esquemas técnicos de LEONES.** Logos e iconografía pueden utilizar SVG; mapas, esquemas, flujos y diagramas técnicos deben mantenerse en ASCII.

Nunca se debe resolver un problema de contenido mediante JavaScript ni un problema de navegación modificando indiscriminadamente el CSS del contenido.

### 2.2. Una navegación común

Toda la web debe utilizar una única navegación común.

La navegación se implementa mediante:

```text
web/assets/js/navigation.js
web/assets/css/navigation.css
```

La navegación **no debe definir el diseño interno de las páginas**.

`navigation.css` sólo puede controlar:

- menú lateral
- migas de pan
- botón de navegación móvil
- backdrop móvil
- estados de navegación
- enlace "Saltar al contenido"
- espacio reservado para el menú

No debe controlar:

- `.main` o `main` como contenido
- `.wrap`
- tarjetas de contenido
- grids propios de una página
- héroes específicos
- tipografía específica de una página
- diagramas
- tablas
- componentes funcionales de una sección

Esta separación evita exactamente el tipo de regresión que hemos sufrido con `pila.html` y `proyectos.html`.

---

## 3. Estructura de directorios

La estructura preferida es:

```text
web/
├── index.html
├── *.html
├── assets/
│   ├── css/
│   │   ├── navigation.css
│   │   └── *.css
│   ├── js/
│   │   ├── navigation.js
│   │   └── *.js
│   └── graphics/
│       ├── logos/
│       └── *.svg
└── data/
    └── *.json
```

### Regla

Los recursos nuevos deben colocarse en la carpeta que corresponda a su responsabilidad. No se deben crear nuevas carpetas paralelas por conveniencia.

Las rutas antiguas sólo se mantienen cuando exista una razón de compatibilidad documentada.

---

# 4. HTML

## 4.1. Principios

Todo HTML nuevo debe ser:

- HTML5 válido y bien formado.
- Indentado y tabulado.
- Legible sin herramientas especiales.
- Semántico.
- Documentado cuando la estructura no sea obvia.
- Libre de estilos y scripts innecesarios incrustados.
- Libre de HTML comprimido en una sola línea.

**Nunca:**

```html
<!doctype html><html><head>...</head><body>...</body></html>
```

**Siempre:**

```html
<!doctype html>
<html lang="es">
    <head>
        ...
    </head>

    <body>
        ...
    </body>
</html>
```

Prettier debe mantener este formato automáticamente.

---

## 4.2. Cabecera mínima

Cada página debe declarar al menos:

```html
<!doctype html>
<html lang="es">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="description" content="Descripción específica de la página." />
        <title>LEONES · Nombre de la página</title>

        <link rel="stylesheet" href="assets/css/navigation.css" />
    </head>
```

La descripción debe describir la página, no repetir una descripción genérica del proyecto.

---

## 4.3. Estructura semántica

Preferir:

```html
<header>
<nav>
<main>
<section>
<article>
<aside>
<footer>
```

sobre una colección indiscriminada de `<div>`.

Cada página debe tener **un único `<main>`**.

El contenido principal debe poder identificarse mediante:

```html
<main id="main">
```

El `id="main"` permite que la navegación proporcione el enlace de salto al contenido.

---

## 4.4. Encabezados

La jerarquía debe ser lógica:

```text
h1
├── h2
│   ├── h3
│   └── h3
└── h2
```

No se deben utilizar encabezados sólo porque su tamaño visual resulte conveniente.

Una página debe tener un **`h1` que identifique claramente su propósito**.

---

## 4.5. Componentes

Los componentes repetidos deben utilizar clases con nombres claros y estables.

Ejemplo:

```html
<section class="content-card" aria-labelledby="objective-title">
    <h2 id="objective-title">Objetivo</h2>
    <p>...</p>
</section>
```

Evitar nombres genéricos que puedan entrar en conflicto con otras páginas:

```text
.box
.wrap
.item
.card2
.blue
```

Si una clase tiene un significado global, debe formar parte del sistema global y documentarse.

---

# 5. CSS

## 5.1. Principio fundamental

**El CSS global debe ser pequeño y conservador.**

El CSS común no debe intentar rediseñar todas las páginas.

La regla de oro es:

> Si una regla sólo es necesaria para una página, no pertenece al CSS global.

---

## 5.2. Navegación

`navigation.css` es un CSS especializado.

Debe usar selectores acotados al componente:

```css
.leones-nav-runtime .site-side {
    ...
}
```

No se deben introducir reglas globales del tipo:

```css
.wrap + .wrap {
    display: none;
}

main {
    ...
}

.card {
    ...
}
```

en el CSS de navegación.

Especialmente prohibido:

```css
!important
```

como mecanismo normal de resolución de conflictos.

Un `!important` debe ser excepcional y justificarse en un comentario.

---

## 5.3. CSS de página

Una página puede tener su CSS específico, pero debe estar claramente aislado.

Preferir:

```css
.page-hero {
    ...
}

.page-content {
    ...
}

.content-card {
    ...
}
```

frente a modificar componentes globales sin necesidad.

---

## 5.4. Variables

Las variables globales deben representar decisiones reales del sistema.

Ejemplo:

```css
:root {
    --leones-nav-width: 232px;
    --leones-nav-bg: #ffffff;
    --leones-nav-border: #d8e0e7;
    --leones-nav-text: #315d7d;
    --leones-nav-strong: #102f49;
    --leones-nav-active: #c62828;
}
```

Una página puede definir variables propias con nombres específicos de la página.

---

## 5.5. Responsive

El diseño debe ser responsive desde el principio.

La navegación tiene actualmente dos comportamientos:

```text
> 800 px  → navegación lateral
≤ 800 px  → menú lateral desplegable
```

El contenido debe seguir siendo utilizable sin depender de una anchura concreta.

No se debe resolver responsive mediante ocultación arbitraria del contenido.

---

# 6. JavaScript

## 6.1. Principio de degradación elegante

JavaScript añade comportamiento; **no debe ser necesario para leer el contenido principal**.

La página debe mostrar su información esencial sin JavaScript.

---

## 6.2. Navegación

`navigation.js` es responsable de:

- insertar la navegación común
- detectar la página actual
- marcar el enlace activo
- construir migas de pan
- crear el menú móvil
- gestionar apertura/cierre
- gestionar `Escape`
- gestionar el backdrop
- añadir el enlace de salto al contenido
- establecer `aria-current`

No es responsable de:

- construir el contenido de las páginas
- modificar textos de las páginas
- aplicar estilos de contenido
- ocultar secciones
- corregir errores de layout de páginas concretas

---

## 6.3. Accesibilidad

Los controles interactivos deben tener:

- nombre accesible
- estado accesible cuando proceda
- foco de teclado
- comportamiento con teclado

El menú móvil debe incluir al menos:

```html
<button
    type="button"
    aria-controls="leones-side"
    aria-expanded="false"
>
    Menú
</button>
```

Los enlaces de navegación deben poder identificarse como activos mediante `aria-current="page"`.

---

## 6.4. Código

JavaScript debe estar:

- modularizado cuando crezca
- documentado cuando la lógica no sea obvia
- sin variables globales innecesarias
- sin HTML gigantes incrustados sin estructura
- sin manipulación indiscriminada de estilos inline

---

# 7. Menús y navegación

## 7.1. Jerarquía

El menú debe representar la arquitectura real de LEONES, no una lista arbitraria de archivos.

Estructura conceptual:

```text
Inicio
Proyectos
    Atlas
    Pilares
    Arquitectura
    Diagramas
    Pila
    Operación
Aplicación
    Scripts
    Resultados
    Evaluación
    Recomendaciones
Manada
Prospección
Horizonte
Contacto
```

Si se incorpora una nueva sección, debe decidirse primero **dónde pertenece conceptualmente**.

---

## 7.2. Nombres canónicos

Cada página debe tener un nombre canónico.

No se deben crear duplicados con pequeñas variaciones ortográficas.

Si por compatibilidad se necesita un alias, el alias debe:

1. estar documentado;
2. redirigir a la página canónica;
3. no contener una segunda implementación del contenido.

Ejemplo establecido:

```text
proyectos.html → página canónica
proyecto.html  → alias de compatibilidad
```

---

## 7.3. Breadcrumbs

Las migas deben indicar:

```text
Inicio → sección → página
```

No deben sustituir al menú principal.

---

# 8. Identidad visual

## 8.1. Principio

La identidad visual debe ser reconocible pero discreta.

La web no debe convertirse en un escaparate gráfico que dificulte la lectura técnica.

---

## 8.2. Logos e iconografía

Los logos e iconos de LEONES deben reutilizar los recursos existentes en:

```text
web/assets/graphics/
web/assets/graphics/logos/
```

No se deben crear variantes visualmente incompatibles para cada página.

Los SVG son válidos y preferibles para **logos e iconografía** cuando exista el recurso vectorial correspondiente.

Los mapas, esquemas, flujos y diagramas técnicos quedan fuera de esta regla: **se mantienen en ASCII**.

---

## 8.3. Fotografías y fondos

No utilizar fotografías de fondo si compiten con la lectura o generan diferencias arbitrarias entre páginas.

La imagen debe aportar información o identidad; nunca ser decoración por defecto.

---

# 9. Esquemas y arquitectura

Los esquemas son parte del contenido técnico, no simple decoración.

## 9.1. Norma congelada: ASCII

Todos los mapas, esquemas, diagramas de arquitectura, flujos técnicos y representaciones de proceso de LEONES deben publicarse en **ASCII**.

No se deben sustituir por:

- SVG;
- Mermaid;
- imágenes rasterizadas;
- diagramas externos;
- librerías de diagramación.

Esta decisión existe para que el esquema sea legible directamente en el repositorio, accesible, versionable, estable y revisable mediante diff.

El ASCII es la **fuente canónica**. Una página web puede aplicar CSS al bloque de texto para mejorar su lectura, pero no debe convertirlo en otra representación gráfica.

Cada esquema debe:

- tener un propósito identificable;
- estar acompañado por explicación textual cuando sea necesario;
- poder entenderse sin recursos gráficos externos;
- indicar, cuando proceda, su estado: propuesta, actual, experimental o validada;
- mantenerse sincronizado con la arquitectura y la implementación.

Un esquema no sustituye a la explicación de la arquitectura.

---

# 10. Contenido y documentación

Cada página debe responder claramente:

1. **Qué es.**
2. **Por qué existe.**
3. **Qué objetivo tiene.**
4. **Cómo funciona.**
5. **En qué estado está.**
6. **Qué evolución se espera.**
7. **Dónde están las evidencias o recursos relacionados.**

Esto es especialmente importante para las secciones de arquitectura, Atlas, prospección, Manada, evaluación y recomendador.

La web es una interfaz de revisión del proyecto, no sólo un índice de enlaces.

---

# 11. Estados de las funcionalidades

No presentar como terminado algo que está en desarrollo.

Usar estados consistentes:

```text
🟢 TERMINADO / OPERATIVO
🟡 EN DESARROLLO
⚪ SIN EMPEZAR
```

El estado debe reflejar la situación real del proyecto y no sólo la existencia de una página.

---

# 12. Compatibilidad y código antiguo

Cuando se encuentre código antiguo:

1. identificar su función;
2. decidir si sigue siendo necesario;
3. migrarlo al sistema actual si procede;
4. eliminar duplicidades;
5. documentar cualquier compatibilidad que deba conservarse.

**No se deben seguir acumulando capas de compatibilidad indefinidamente.**

Una ruta antigua sólo se mantiene si tiene usuarios, enlaces externos o una razón técnica clara.

---

# 13. Prohibiciones

Queda prohibido introducir en la web nueva:

- HTML en una sola línea.
- CSS comprimido manualmente.
- JavaScript sin formato.
- Duplicación de navegación.
- CSS global para resolver un problema local.
- `!important` indiscriminado.
- Elementos que oculten contenido por defecto sin justificación.
- Dependencias de CSS antiguas sin documentar.
- Dos versiones de un mismo componente con nombres diferentes sin motivo.
- Redirecciones encadenadas.
- JavaScript necesario para leer el contenido principal.
- Fondos o animaciones que dificulten la revisión humana.
- Diagramas técnicos en formatos distintos de ASCII.

---

# 14. Formato automático

Prettier es parte del contrato de desarrollo.

Debe aplicarse a:

```text
web/**/*.html
web/**/*.css
web/**/*.js
```

La configuración del proyecto debe permanecer versionada.

Una modificación que deje HTML, CSS o JS sin formatear debe considerarse incompleta.

---

# 15. Proceso obligatorio para crear una página

Antes de crearla:

```text
1. Definir propósito
        ↓
2. Decidir dónde encaja en la navegación
        ↓
3. Elegir nombre canónico
        ↓
4. Crear HTML semántico
        ↓
5. Añadir CSS específico mínimo
        ↓
6. Integrar navegación común
        ↓
7. Añadir accesibilidad
        ↓
8. Formatear con Prettier
        ↓
9. Comprobar enlaces y recursos
        ↓
10. Revisar escritorio + móvil
        ↓
11. Documentar objetivo y estado
        ↓
12. Publicar
```

---

# 16. Proceso obligatorio para modificar una página existente

Antes de tocar código:

```text
IDENTIFICAR
    ↓
¿es un problema de contenido?
    ├── sí → HTML
    └── no
         ↓
¿es presentación?
    ├── sí → CSS de página
    └── no
         ↓
¿es interacción?
    ├── sí → JavaScript
    └── no
         ↓
¿afecta a toda la navegación?
    ├── sí → sistema común
    └── no → componente local
```

Nunca solucionar un problema global cambiando una página al azar.

Nunca solucionar un problema local modificando el CSS global si puede resolverse localmente.

---

# 17. Checklist antes de aceptar cambios

## HTML

- [ ] HTML5 correcto.
- [ ] `lang="es"`.
- [ ] `charset` y viewport.
- [ ] `title` específico.
- [ ] `description` específica.
- [ ] Un único `main`.
- [ ] `h1` claro.
- [ ] Jerarquía de encabezados correcta.
- [ ] HTML indentado.
- [ ] Sin HTML de una sola línea.

## CSS

- [ ] Responsabilidad clara.
- [ ] No invade páginas ajenas.
- [ ] No oculta contenido accidentalmente.
- [ ] Sin `!important` innecesarios.
- [ ] Responsive.
- [ ] Variables coherentes.

## JavaScript

- [ ] No es necesario para leer el contenido.
- [ ] Interacción accesible.
- [ ] Teclado.
- [ ] Estados ARIA.
- [ ] Sin manipulación global innecesaria.

## Navegación

- [ ] Aparece el menú común.
- [ ] Página activa correctamente marcada.
- [ ] Breadcrumb correcto.
- [ ] Enlaces funcionando.
- [ ] Menú móvil funcionando.
- [ ] `Escape` cierra el menú.
- [ ] `Saltar al contenido` funciona.

## Contenido

- [ ] Se explica qué es.
- [ ] Se explica por qué existe.
- [ ] Se explica objetivo.
- [ ] Se explica funcionamiento.
- [ ] Se indica estado.
- [ ] Se indica evolución prevista.
- [ ] Se enlazan evidencias relevantes.

## Esquemas

- [ ] Cada mapa/esquema/flujo técnico está en ASCII.
- [ ] No existe una representación gráfica paralela del mismo esquema.
- [ ] El esquema coincide con la documentación canónica.
- [ ] El esquema coincide con la implementación cuando describe el sistema actual.

## Publicación

- [ ] Prettier ejecutado.
- [ ] Enlaces internos comprobados.
- [ ] Recursos gráficos comprobados.
- [ ] Escritorio comprobado.
- [ ] Móvil comprobado.
- [ ] GitHub Actions sin errores.
- [ ] GitHub Pages actualizado.

---

# 18. Regla de oro

> **La web de LEONES debe ser más sencilla de leer que de construir, y más sencilla de mantener que de romper.**

Cuando exista una duda entre dos soluciones, se debe preferir la que:

1. tenga menos capas;
2. tenga una responsabilidad más clara;
3. sea más legible para un humano;
4. dependa menos de JavaScript;
5. tenga menos efectos globales;
6. pueda comprobarse automáticamente;
7. pueda explicarse en una frase.

---

## 19. Relación con la documentación del proyecto

Este documento complementa, y no sustituye, la documentación técnica general de LEONES.

- `README.md` → estado y entrada general del proyecto.
- `docs/ARCHITECTURE.md` → arquitectura del ecosistema.
- `docs/ROADMAP.md` → evolución prevista.
- `docs/DOCUMENTATION_PROTOCOL.md` → protocolo de documentación.
- `docs/WEB_DESIGN_SYSTEM.md` → **contrato de diseño y desarrollo de la web**.

**Para cualquier cambio de la web, este documento debe consultarse antes de modificar código.**
