# Magnitude-LEONES — Asistente personal IA

## Objetivo

Usar Magnitude como integración de referencia para el perfil **Asistente personal IA**.

LEONES proporciona preflight, instalación, gobernanza, validación y benchmark. Magnitude proporciona el agente y su ejecución local.

## Capacidades relevantes

Magnitude integra agente local y modelos locales, perfilado de hardware, recomendación de modelos, descarga/configuración, ejecución local, skills y endpoints OpenAI-compatible. Su enfoque declara privacidad/offline para la ejecución local.

## Instalación

```bash
npm install -g @magnitudedev/cli
```

Después, en el proyecto del asistente:

```bash
magnitude
```

## Debian/Ubuntu y Red Hat/Rocky/RHEL

LEONES debe comprobar previamente Node.js/npm, arquitectura, hardware y almacenamiento. En Red Hat/Rocky/RHEL se instala Node.js/npm mediante el mecanismo soportado por la distribución y después el CLI de Magnitude.

## Flujo

1. Preflight.
2. Instalar CLI.
3. Capturar perfil hardware.
4. Capturar recomendación.
5. Confirmar descargas grandes.
6. Registrar modelo/Hugging Face/archivo/cuanti.
7. Validar agente y herramientas controladas.
8. Ejecutar benchmark independiente LEONES.
9. Registrar resultado.

## Skills

Cada skill debe catalogarse por origen, versión/ref, permisos, acceso a archivos, red y herramientas. LEONES no debe instalar skills de riesgo automáticamente.

## Datos

Separar `observed`, `recommended/configured`, `estimated` y `measured`. Nunca registrar prompts, archivos, código, conversaciones, secretos o API keys.

## Contrato externo solicitado

Se propone salida machine-readable para hardware, recomendación, modelo/Hugging Face, cuantización, memoria estimada, runtime/configuración y benchmark, diferenciando estimado de medido.

## Fases

MAG-0 investigación → MAG-1 contrato → MAG-2 preflight → MAG-3 instalación → MAG-4 selección → MAG-5 validación del agente → MAG-6 benchmark → MAG-7 telemetría consentida → MAG-8 Atlas → MAG-9 E2E.
