# OpenDots + OpenBot + Magnitude en LEONES

Estado: **integración preparada en rama; validación E2E real pendiente**. Esta guía complementa [OpenDots + Magnitude ICN](OPENDOTS-MAGNITUDE.md) y mantiene todos los cambios de integración en LEONES. No modifica los repositorios upstream ni la revisión fijada del subproyecto Magnitude.

## Decisión de arquitectura

Usar las capacidades OpenBot que **OpenDots ya integra**. No desplegar una segunda interfaz OpenBot independiente en esta primera fase.

```text
Usuario
  │
  ▼
OpenDots (UI, Dots, espacios, conversaciones y tareas)
  ├── OpenBot computer services (supervisor + contenedor aislado por Dot)
  │     └── navegador / archivos / terminal; permisos por Dot
  │
  └── TanStack AI → OPENAI_BASE_URL
                    │
                    ▼
          LEONES compatibility facade (127.0.0.1:10101)
                    │
                    ▼
          Magnitude ICN (127.0.0.1:8080)
                    │
                    ▼
          instancia de modelo en estado Ready
```

OpenDots ya consume el servicio de ordenador de OpenBot a través de `compose.computers.yml`, `compose.computers-app.yml` y `docs/COMPUTERS.md`. El Compose de OpenDots fija el código OpenBot usado para construir los servicios en `b6932d31a8d6e7896c15139dfc27a6c6911deb27`. Mantener esa revisión fijada para reproducibilidad; no usar `main` como dependencia mutable.

## Qué hace cada componente

- **OpenDots:** interfaz, Dots, espacios, páginas, conversaciones y tareas programadas.
- **OpenBot computer services:** ordenadores aislados por Dot, navegador persistente, archivos, terminal y acciones sujetas a permisos. No es el modelo de lenguaje.
- **Magnitude ICN:** inferencia. La revisión fijada por LEONES requiere traducir su contrato específico; por eso se usa la fachada de LEONES y no una conexión directa.
- **LEONES:** instaladores, configuración explícita, comprobaciones y pruebas de integración.

## Requisitos previos

- Node.js 24+ y npm para OpenDots.
- Docker Engine, Docker Compose v2 y BuildKit con soporte para contextos de build adicionales.
- Magnitude ICN en `127.0.0.1:8080`, con una instancia real en estado `Ready`.
- Fachada LEONES en `127.0.0.1:10101`.
- OpenDots con su `.env` propio. Las conversaciones requieren CopilotKit Intelligence: hosted, evaluación local compatible o self-hosted autorizado. Redirigir el LLM no sustituye Intelligence.
- Dos secretos diferentes y aleatorios (mínimo 24 caracteres) para `COMPUTER_SUPERVISOR_TOKEN` y `COMPUTER_TOKEN`.

## Preparar OpenDots y los ordenadores OpenBot

Desde el checkout OpenDots instalado por LEONES:

1. Configura `OPENAI_API_KEY=local`, `OPENAI_BASE_URL=http://127.0.0.1:10101/v1` y `OPENAI_MODEL=local`. La clave es un marcador para el cliente local, no una credencial remota.
2. Configura Intelligence según la guía oficial de OpenDots.
3. Configura `COMPUTER_SUPERVISOR_URL=http://127.0.0.1:4312`, `COMPUTER_SUPERVISOR_TOKEN`, `COMPUTER_TOKEN` y un `COMPUTER_NAMESPACE` estable.
4. Construye la imagen de ordenador y el supervisor con la revisión OpenBot fijada por OpenDots y arranca solo el supervisor:

```bash
docker compose -f compose.computers.yml build computer-image computer-supervisor
docker compose -f compose.computers.yml up -d computer-supervisor
```

5. Arranca OpenDots con `npm run dev`. En el panel **Computer** de un Dot, habilita el acceso y concede únicamente las capacidades necesarias. Browser, files y shell empiezan desactivados.

Para una primera ejecución con el mínimo tráfico externo, configura además `WEB_SEARCH_PROVIDER=disabled`, `COPILOTKIT_TELEMETRY_DISABLED=true` y `DO_NOT_TRACK=1`. Deja sin configurar voz y conectores externos mientras haces las pruebas iniciales. Esto no convierte CopilotKit Intelligence en local: verifica su endpoint y licencia por separado. La preflight avisa si detecta búsqueda/telemetría potencialmente externas, una clave de voz o si no puede comprobar el endpoint de Intelligence.

Para una aplicación dentro de Compose, sigue la variante documentada en [OpenDots Computer setup](https://github.com/CopilotKit/OpenDots/blob/main/docs/COMPUTERS.md); no reutilices el URL de loopback del host desde el contenedor.

## Comprobación sin efectos secundarios

Con ICN, instancia, proxy, supervisor y checkout OpenDots en marcha:

```bash
MAGNITUDE_MODEL_INSTANCE_ID='ID_REAL_READY' \
  bash scripts/integrations/opendots_openbot_magnitude_preflight.sh \
  /ruta/al/OpenDots
```

La preflight valida rutas/configuración, revisión fijada de OpenBot, salud del proxy, alias publicado, instancia Ready y salud del supervisor. No genera texto, no ejecuta comandos dentro del ordenador de un Dot, no cambia archivos y no imprime secretos.

Después ejecuta el smoke test de inferencia existente:

```bash
OPENAI_MODEL=local bash scripts/integrations/opendots_magnitude_smoke.sh
```

Y completa la aceptación manual que no puede sustituir una preflight:

- Conversación real de OpenDots usando Magnitude, con streaming.
- Una acción de navegador y una operación de archivo en el ordenador de prueba de un Dot.
- Confirmar que shell está denegado hasta habilitarlo explícitamente y que una acción no autorizada queda bloqueada/auditada.
- Reiniciar el supervisor y comprobar persistencia del perfil del navegador y archivos.
- Desconectar Magnitude y confirmar error visible, sin fallback remoto.
- Verificar memoria/hilos, voz y búsqueda por separado; son servicios distintos de la inferencia de texto.

## Límites y seguridad

- La configuración de `OPENAI_BASE_URL` solo redirige inferencia de texto. No hace locales por sí sola Intelligence, voz, búsqueda web, telemetría o canales externos.
- El supervisor OpenBot necesita acceso al socket de Docker para crear ordenadores. Mantén la API del supervisor en loopback en la modalidad local y no expongas el socket/API a la LAN.
- Cada ordenador comparte el kernel del host; el contenedor no sustituye un límite de seguridad fuerte. Shell habilitado implica riesgo de ejecutar programas y acceder a la red desde ese contenedor.
- El uso de modelo local no garantiza aislamiento de red. Para una instalación offline, deshabilita o audita búsqueda externa, telemetría, proveedores remotos y conexiones de Intelligence.
- No registrar prompts, contenido de archivos, tokens o secretos en los resultados de prueba.

## Estado de aceptación

| Prueba | Estado |
|---|---|
| Contrato proxy ↔ ICN con mocks | Pasada en la rama base de integración |
| Validación de sintaxis y configuración | En preparación en esta rama |
| Modelo Magnitude real + OpenDots | Pendiente |
| Navegador/archivos OpenBot desde un Dot real | Pendiente |
| Denegación de permisos y ausencia de fallback remoto | Pendiente |
| Auditoría de egress y servicios no locales | Pendiente |

No marcar esta integración como lista para producción hasta que se registren los resultados E2E reales.
