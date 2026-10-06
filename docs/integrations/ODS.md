# ODS-LEONES — Servidor de Stacks IA

## Objetivo

Usar ODS como integración de referencia para el perfil **Servidor de Stacks IA**.

LEONES es la capa de preflight, consentimiento, orquestación, validación y medición. ODS proporciona el stack de IA.

## Capacidades relevantes

ODS reúne inferencia local, Open WebUI, gateway, RAG/search, voz, agentes/workflows, generación de imágenes, privacidad y observabilidad. Entre los componentes documentados por el proyecto están llama-server, Open WebUI, LiteLLM, TEI, Qdrant, SearXNG/Perplexica, Whisper/Kokoro, Hermes Agent, n8n, APE, OpenCode, ComfyUI, Dashboard, Privacy Shield, Token Spy y Langfuse.

## Instalación

Instalador documentado por ODS:

```bash
curl -fsSL https://install.osmantic.com/ods.sh | bash
```

Modo auditable:

```bash
git clone https://github.com/Osmantic/ODS.git
cd ODS/ods
./install.sh
```

Para producción LEONES debe permitir fijar release/tag/commit auditado.

## Debian/Ubuntu

El preflight debe comprobar OS, arquitectura, CPU, RAM, GPU/VRAM, driver, almacenamiento y Docker/Compose antes de instalar.

## Red Hat/Rocky/RHEL

ODS declara soporte Linux y pruebas sobre Rocky Linux 9. LEONES debe validar previamente el runtime de contenedores y la aceleración disponible.

## Post-instalación

1. Capturar versión/ref.
2. Obtener estado/health.
3. Identificar modelo, cuantización y runtime.
4. Comprobar servicios y endpoints.
5. Ejecutar benchmark independiente LEONES.

## Datos

Separar estrictamente:

- `observed`: hardware/software detectado.
- `configured`: configuración instalada.
- `estimated`: predicción previa.
- `measured`: benchmark LEONES.

Nunca enviar contenido de usuario.

## Contrato externo solicitado a ODS

Se propone un contrato machine-readable equivalente a:

```text
ods status --json
ods doctor --json
```

con versión/ref, hardware, modelo, cuantización, runtime, servicios y health, sin secretos.

## Fases

ODS-0 investigación → ODS-1 contrato → ODS-2 preflight → ODS-3 instalación → ODS-4 health → ODS-5 benchmark → ODS-6 telemetría consentida → ODS-7 Atlas → ODS-8 E2E.


## De ajuste del modelo a capacidad real

ODS debe dejar de reducir la selección a qué modelo cabe en una GPU. La pregunta objetivo es:

> **¿Qué configuración de inferencia produce la mejor capacidad real en esta GPU, para este workload y esta política?**

El objeto de decisión es un **Inference Profile** que combina hardware, modelo, cuantización, runtime, kernel, contexto, KV cache, MTP/speculative decoding, visión, slots, reasoning effort, flags y evidencia.

La investigación externa de Bonsai 2 se incorpora como evidencia experimental externa, no como dependencia. Sus mediciones publicadas sirven para generar candidatos y diseñar experimentos; solo se convierten en evidencia MEASURED de LEONES tras reproducción física.

La frontera de ejecución queda:

    LEONES -> predicción / experimento / evidencia
         -> ODS -> ejecución / orquestación
         -> inferencia física -> medición -> LEONES
