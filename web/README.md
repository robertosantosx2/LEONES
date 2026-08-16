# LEONES Web — referencia obligatoria

## Objetivo

La web de LEONES prioriza, en este orden:

1. simplicidad técnica;
2. legibilidad;
3. funcionalidad;
4. accesibilidad básica;
5. mantenimiento sencillo.

La estética no debe introducir complejidad que no aporte una función clara.

## Arquitectura

```text
HTML semántico
    ↓
CSS compartido
    ↓
JavaScript solo cuando aporta comportamiento
```

La navegación es transversal. El contenido de cada página debe permanecer separado de la infraestructura interna.

## Regla para CSS específico

Antes de crear CSS específico para una página deben agotarse estas alternativas:

1. HTML semántico adecuado.
2. Elementos o clases existentes.
3. Extensión pequeña y reutilizable de `assets/css/site.css`.
4. Solo si existe una excepción conceptual real, CSS específico mínimo y documentado.

## HTML

- `<!doctype html>` y `lang="es"`.
- `charset` y `viewport`.
- título descriptivo y único.
- `meta description` cuando corresponda.
- encabezados en orden lógico.
- `header`, `main`, `section`, `article` y `footer` cuando aporten semántica.
- enlaces reales para navegación.
- código indentado y legible; nunca comprimido en una línea.

## CSS

`site.css` contiene el sistema visual común. `navigation.css` contiene exclusivamente la navegación. No duplicar reglas entre páginas.

## JavaScript

JavaScript resuelve comportamiento, no problemas que HTML o CSS puedan resolver de forma más simple. Los scripts deben ser externos y cargarse con `defer` cuando sea posible.

## Separación de infraestructura

La web documenta, explica y presenta LEONES. No debe convertirse en un paquete que el usuario tenga que descargar para ejecutar la infraestructura.

Los scripts locales son herramientas autónomas. El usuario descarga solo las herramientas necesarias para realizar pruebas en su propio equipo.

## Criterio de terminado

Una página está terminada cuando una persona puede abrirla, entender para qué sirve, navegar al siguiente paso y revisar su contenido sin conocer la arquitectura interna del proyecto.
