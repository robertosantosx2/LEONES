# LEONES — Checklist de migración y auditoría web

**Documento operativo derivado de `WEB_DESIGN_SYSTEM.md`.**

Este documento sirve para ejecutar la modernización de `web/` sin volver a introducir incompatibilidades.

## 1. Inventario

Antes de modificar una página:

- [ ] Identificar HTML canónico.
- [ ] Identificar aliases y redirecciones.
- [ ] Identificar CSS cargado.
- [ ] Identificar JavaScript cargado.
- [ ] Identificar imágenes, SVG y JSON utilizados.
- [ ] Identificar enlaces internos.
- [ ] Identificar dependencias heredadas.

## 2. HTML

Cada documento debe tener esta estructura conceptual:

```text
html
└── head
└── body
    ├── navegación común
    ├── header de página
    ├── main#main
    │   ├── sección introductoria
    │   └── secciones de contenido
    └── footer
```

Comprobar:

- [ ] `<!doctype html>`.
- [ ] `lang="es"`.
- [ ] charset.
- [ ] viewport.
- [ ] title específico.
- [ ] description específica.
- [ ] un único `main`.
- [ ] `main#main`.
- [ ] un `h1`.
- [ ] jerarquía de encabezados correcta.
- [ ] contenido visible sin JavaScript.
- [ ] HTML formateado por Prettier.

## 3. CSS

Para cada hoja:

- [ ] Tiene una responsabilidad explícita.
- [ ] Los selectores están acotados.
- [ ] No modifica accidentalmente otras páginas.
- [ ] No oculta contenido mediante reglas genéricas.
- [ ] No utiliza `display: none` sobre contenido por defecto salvo que sea un estado funcional justificado.
- [ ] No utiliza `!important` salvo excepción documentada.
- [ ] Responsive.
- [ ] Formateada por Prettier.

### Regla crítica

Nunca introducir en CSS de navegación reglas sobre contenido genérico como:

```css
main { ... }
.wrap { ... }
.card { ... }
section { ... }
```

## 4. JavaScript

- [ ] Sólo añade comportamiento.
- [ ] No construye el contenido principal.
- [ ] No es imprescindible para leer la página.
- [ ] Controles de teclado comprobados.
- [ ] ARIA comprobado.
- [ ] No hay estilos inline innecesarios.
- [ ] Formateado por Prettier.

## 5. Navegación

- [ ] Una única navegación común.
- [ ] Página actual marcada.
- [ ] Breadcrumb correcto.
- [ ] Saltar al contenido.
- [ ] Menú móvil.
- [ ] Escape.
- [ ] Foco.
- [ ] Todos los enlaces resuelven.

## 6. Recursos

- [ ] Todas las imágenes existen.
- [ ] Todos los SVG existen.
- [ ] No quedan referencias a carpetas antiguas sin justificación.
- [ ] No hay recursos duplicados con funciones equivalentes.
- [ ] Los recursos tienen nombres comprensibles.

## 7. Compatibilidad

Si existe una ruta antigua:

```text
ruta antigua → alias documentado → página canónica
```

No crear dos implementaciones del mismo contenido.

## 8. Contenido

Cada página debe explicar, cuando sea aplicable:

- [ ] qué es;
- [ ] por qué existe;
- [ ] objetivo;
- [ ] funcionamiento;
- [ ] estado actual;
- [ ] evolución prevista;
- [ ] evidencias y recursos.

## 9. Validación

Antes de aceptar una modificación:

- [ ] Prettier.
- [ ] enlaces internos.
- [ ] recursos.
- [ ] escritorio.
- [ ] móvil.
- [ ] GitHub Actions.
- [ ] GitHub Pages.
- [ ] revisión humana.

## 10. Orden de migración recomendado

```text
sistema de navegación
        ↓
CSS global
        ↓
páginas estructurales
        ↓
páginas de contenido
        ↓
páginas dinámicas
        ↓
aliases y compatibilidad
        ↓
validación completa
```

No se debe declarar terminada una migración mientras existan páginas que dependan de una generación antigua de navegación o CSS sin justificación documentada.
