# ODS — Osmantic Deployment System

- **Proyecto:** ODS (Osmantic Deployment System)
- **Repositorio:** https://github.com/Osmantic/ODS
- **Tipo:** plataforma/instalador de stack de IA local y servidor privado.
- **Estado LEONES:** 🟢 fuente activa · 🟡 subproyecto de integración.
- **Revisión:** 2026-08-20

## Qué aporta

ODS convierte un equipo Linux, macOS o Windows/WSL en un stack de IA local integrado. Instala y conecta inferencia, Open WebUI, dashboard, voz, agentes, workflows, RAG/búsqueda, generación de imágenes, privacidad y observabilidad. La instalación detecta hardware y selecciona un modelo apropiado para el perfil detectado. citeturn0search0turn0search8

## Arquitectura relevante

La arquitectura se organiza alrededor de servicios Compose y helpers gestionados por el host. Incluye `llama-server`, Open WebUI, dashboard, dashboard API, LiteLLM, Whisper/Kokoro, SearXNG/Perplexica y componentes de agentes/automatización. El CLI `ods` gestiona el ciclo de vida del stack. citeturn0search2

ODS utiliza extensiones basadas en `manifest.yaml` + `compose.yaml`, permitiendo añadir servicios sin modificar el núcleo siempre que sea posible. citeturn0search9

## Instalación y operación

El instalador está diseñado para dejar un stack funcional con un solo comando. En Linux requiere Docker Compose v2+, `curl`, `git` y, según GPU, los runtimes correspondientes; el quickstart recomienda 40 GB o más de espacio libre para modelos e imágenes. citeturn0search3

El CLI permite consultar estado, servicios, logs, reiniciar, cambiar modos local/cloud/hybrid, cambiar modelos, activar extensiones y guardar/restaurar presets. citeturn0search0

## Hardware y modelos

ODS detecta GPU, memoria y plataforma y utiliza un catálogo versionado para seleccionar un GGUF instalable. También permite proporcionar un GGUF propio. El mecanismo de selección y rollback debe tratarse en LEONES como evidencia de comportamiento del instalador, no como benchmark independiente. citeturn0search0

## API e integración

ODS expone una API compatible con OpenAI para que aplicaciones Python/Node puedan apuntar al servidor local. Esto permite a LEONES integrarlo como **target de despliegue/servidor**, manteniendo separado el motor de decisión de LEONES. citeturn0search4

## Encaje en LEONES

```text
LEONES
  ├── Atlas / conocimiento
  ├── LLMFit → preselección hardware-aware
  ├── Router → tarea + restricciones + evidencia
  ├── Runtime Selector
  │     └── ODS → despliegue / stack local
  └── Benchmark → medición propia
```

ODS debe funcionar como **capa de despliegue e instalación**. LEONES conserva la decisión sobre modelo, runtime, tarea y benchmark.

## Integración prevista

1. Subproyecto ODS dentro del ecosistema LEONES.
2. Adaptador de instalación y estado.
3. Importación del perfil hardware y del modelo elegido por ODS.
4. Exposición de endpoints OpenAI-compatible al Router de LEONES.
5. Manifiesto reproducible con versión de ODS, plataforma, arquitectura, kernel, Docker, modelo, runtime y configuración.
6. Benchmark posterior al despliegue; ningún resultado externo pasa directamente a `measured`.

## Evidencia y límites

ODS puede detectar hardware, seleccionar modelos y desplegar un stack, pero su selección no sustituye a LLMFit ni las mediciones de LEONES. Los resultados deben distinguir instalación correcta, compatibilidad, rendimiento y utilidad de la tarea.

## Fuente primaria

urlODS en GitHubhttps://github.com/Osmantic/ODS
