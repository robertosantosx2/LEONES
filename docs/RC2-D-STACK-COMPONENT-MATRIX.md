# RC2-D — Matriz funcional ODS vs Magnitude

Esta matriz es la vista previa que LEONES debe presentar antes de pedir al usuario que elija stack. No sustituye la documentación oficial ni pretende congelar capacidades que puedan cambiar entre versiones.

| Área | ODS | Magnitude |
|---|---|---|
| Inferencia local | Sí; stack alrededor de llama-server y backends soportados | Sí; motor de inferencia local propio/tuneado |
| Perfilado hardware | Instalador perfila hardware y selecciona tier/modelo | Perfila chip, memoria y bandwidth |
| Recomendación de modelo | Sí, integrada en instalación/tier | Sí, con fit y estimación tok/s |
| Chat/UI | Open WebUI | Harness/UI propio y conexiones a harnesses |
| Dashboard/operación | Sí | Gestión de modelos/inferencia |
| Agentes | Hermes y opciones adicionales | Orientación principal a workloads agentic |
| Workflows | n8n y extensiones | Depende del harness conectado |
| RAG/search | Integrado en el stack | Depende del harness/stack conectado |
| Voz | Integrada como capacidad del stack | No es la función principal |
| Imagen | Integrada como extensión/capacidad del stack | No es la función principal |
| Privacidad/offline | Local por defecto; modos cloud/hybrid opcionales | Local/offline tras instalación/modelos |
| Modelos externos | Modelos gestionados/importados según soporte | GGUF compatibles fuera del catálogo |
| Instalación | Instalador de stack completo | CLI/setup orientado a inferencia local |
| Integración con agentes | Servicios y harnesses soportados por ODS | Integración directa con múltiples harnesses |

## Regla de presentación

LEONES debe mostrar esta comparación con la versión/ref que vaya a utilizar. Si una capacidad no está verificada para esa versión, debe aparecer como `no verificada`, no como `no disponible`.

Fuentes actuales consultadas para la matriz:

- ODS README/Quickstart y documentación de Hermes.
- Magnitude official product page.

La matriz es informativa; la decisión final pertenece al usuario y el plan de instalación debe conservar la procedencia de cada afirmación.
