# Sistema de logos funcionales LEONES

Esta carpeta contiene las variantes funcionales del logo principal de LEONES para representar visualmente distintas funciones del ecosistema.

## Principio

Todas las variantes reutilizan `../leones-logo-principal.svg` como identidad común y añaden un distintivo funcional. El objetivo es conservar siempre reconocible la identidad de los dos leones.

## Fuente canónica

`manifest.json` es el catálogo canónico. Existe una regla estricta:

> **Si un logo aparece en el manifiesto o en esta documentación, su fichero debe existir físicamente en `web/assets/graphics/logos/`.**

Los logos funcionales actuales son:

- `leones-prospeccion.svg` — descubrimiento y vigilancia del ecosistema.
- `leones-router.svg` — recomendación de la mejor pila.
- `leones-atlas.svg` — conocimiento estructurado.
- `leones-hardware.svg` — diagnóstico de la máquina.
- `leones-modelos.svg` — modelos locales.
- `leones-inferencia.svg` — medición de rendimiento.
- `leones-agents.svg` — Agents / LOTB.
- `leones-evidencia.svg` — informes y evidencia.
- `leones-privacidad.svg` — control de privacidad.
- `leones-publicacion.svg` — publicación y difusión.
- `leones-manada.svg` — comunidad y contribución colectiva.
- `leones-stats.svg` — estadísticas y aprendizaje.
- `leones-herramientas.svg` — herramientas y scripts.
- `leones-arquitectura.svg` — arquitectura del ecosistema.
- `leones-acerca.svg` — información general del proyecto.

## Uso

Las variantes son SVG individuales y reutilizables. Cada una referencia el logo principal SVG y añade su distintivo funcional. No se deben introducir rutas a SVG funcionales que no estén creados en este directorio.

La comprobación automática de referencias locales de web y documentación se realiza con `scripts/validate_web_assets.py`.
