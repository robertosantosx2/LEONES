# ODS ↔ LEONES

**Perfil:** Servidor de Stacks IA.

ODS (Osmantic Deployment System) es una plataforma local que despliega y conecta inferencia, Open WebUI, dashboard, agentes, workflows, RAG/search, voz, imagen y herramientas operativas. Su documentación actual describe Linux con NVIDIA/AMD/Intel Arc, macOS Apple Silicon y Windows/WSL; para LEONES interesa especialmente Linux.

## Qué aporta ODS

- instalador de una sola orden;
- detección de hardware y selección inicial de modelo;
- llama-server como ruta de inferencia local en Linux;
- Open WebUI;
- LiteLLM;
- embeddings/RAG;
- Whisper/Kokoro;
- Hermes Agent y n8n;
- ComfyUI;
- extensiones mediante manifests y Compose.

La arquitectura usa una capa base de Compose, overlays por acelerador y extensiones. El instalador se divide en fases y la detección de hardware gobierna decisiones posteriores.

## Qué NO hace LEONES

LEONES no reemplaza el instalador ni administra internamente los servicios de ODS. El contrato es:

```text
LEONES
  ├─ preflight
  ├─ consentimiento
  ├─ lanzamiento controlado
  ├─ captura de evidencia
  └─ benchmark independiente
          │
          ▼
        ODS
  ├─ instalación
  ├─ servicios
  ├─ modelos
  └─ runtime
```

## Instalación de referencia

La documentación oficial de ODS publica para Linux/macOS:

```bash
curl -fsSL https://install.osmantic.com/ods.sh | bash
```

También documenta la instalación desde el repositorio:

```bash
git clone https://github.com/Osmantic/ODS.git
cd ODS/ods
./install.sh
```

LEONES debe preferir una release/ref fijada en instalaciones reproducibles, no depender silenciosamente de `main`. ODS requiere Docker con Compose v2 en Linux y documenta `curl`/`git` y los runtimes de GPU cuando corresponda.

## Preflight LEONES

```text
OS → CPU/RAM → GPU/VRAM → disco → Docker/Compose → GPU runtime → red
```

El preflight devuelve una decisión estructurada:

- `ready`;
- `blocked`;
- `unknown`.

Nunca convierte `unknown` en `ready` por inferencia.

## Captura post-instalación

LEONES debe registrar, cuando esté disponible:

- versión/ref ODS;
- backend de inferencia;
- modelo y origen;
- fichero/artefacto de pesos cuando sea observable;
- cuantización declarada;
- contexto configurado;
- servicios activos;
- puertos locales;
- hardware observado;
- resultado `ods status`/`ods doctor`;
- benchmark LEONES.

En Linux, la documentación actual de ODS indica que llama-server suele exponerse en `localhost:11434` para instalaciones Docker y en `8080` dentro del contenedor; el valor real debe leerse de `.env`, no suponerse.

## Seguridad y privacidad

El modo local es la opción por defecto documentada. ODS también contempla modos cloud/hybrid, por lo que LEONES debe registrar el modo efectivo. El modo local no necesita cloud para funcionar.

LEONES no recopila prompts, conversaciones, secretos ni rutas personales. La publicación de un resultado en Atlas requiere consentimiento explícito.

## Uninstall/recovery

ODS documenta:

```bash
cd ~/ods
./ods-uninstall.sh --force
```

El procedimiento LEONES debe mostrar antes qué datos/modelos se conservarán o eliminarán y exigir confirmación antes de una acción destructiva.

## Encaje con Atlas

La integración alimenta únicamente hechos observados:

```text
ODS recommendation → reported/estimated
ODS configuration  → observed
LEONES benchmark   → measured
```

CABE, JGB, fit y recomendaciones posteriores siguen sus reglas propias y no se derivan de una única puntuación.

## Fuentes primarias

- ODS: https://github.com/Osmantic/ODS
- ODS Quick Start: https://github.com/Osmantic/ODS/blob/main/ods/QUICKSTART.md
- ODS Architecture: https://github.com/Osmantic/ODS/blob/main/ARCHITECTURE.md
