# Integración visual

Los logos funcionales deben aparecer en las secciones que representan, manteniendo el león principal como identidad común.

Rutas desde las páginas de `web/`: `assets/graphics/logos/<fichero>.svg`.

El catálogo canónico de logos es `manifest.json`. **Todo fichero declarado en el manifiesto debe existir físicamente en este directorio.** No se deben documentar ni referenciar variantes que no estén presentes en el árbol del repositorio.

La identidad base es `../leones-logo-principal.svg`. Cada variante funcional reutiliza esa identidad y añade un distintivo de función.

Se recomienda un tamaño de 44–72 px en navegación y 80–128 px en cabeceras o tarjetas.

La comprobación de referencias locales de la web y de enlaces relativos de documentación se ejecuta mediante `scripts/validate_web_assets.py` y forma parte del control de calidad web.
