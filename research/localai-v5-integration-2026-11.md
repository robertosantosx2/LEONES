# LocalAI 5.0 — investigación de integración en LEONES

**Fecha:** 2026-11-21. **Estado:** investigación documental incorporada; no instalado ni validado en hardware LEONES.  
**Release:** [LocalAI v5.0.0](https://github.com/mudler/LocalAI/releases/tag/v5.0.0), commit 1d08354, publicada el 18-11-2026.  
**Fuentes primarias:** [release notes](https://github.com/mudler/LocalAI/releases/tag/v5.0.0) · [anuncio oficial](https://localai.io/blog/localai-5-0/) · [Sandbox docs](https://localai.io/docs/addons/catalogue/work/sandbox/).

## 1. Dictamen

LocalAI 5.0 merece una línea de investigación propia como **runtime/proveedor local opcional y plataforma agentiva**. No debe sustituir el núcleo LEONES, ODS, TensorFold, llama.cpp, NEPENTHES ni REDIL.

Su valor para LEONES es comparar serving local con APIs OpenAI/Anthropic, modelos multimodales, chats persistentes, Projects/Files, agentes y add-ons, generación de documentos y ejecución de código en Sandbox. La hipótesis es: **LEONES gobierna y mide; LocalAI proporciona un servicio opcional**. Toda integración pasa por adaptador y conserva proveedores alternativos.

## 2. Capacidades de v5.0

La release presenta una evolución de servidor de inferencia a plataforma de trabajo local:

- Desktop para Linux x86-64/ARM64 y macOS Apple Silicon, que puede instalar/gestionar o conectar con un servidor.
- Projects y Files para contexto y almacenamiento de archivos.
- Chats persistentes y agentes residentes en servidor.
- Office mediante add-on.
- Sandbox para ejecución Python/Bash.
- Team/sharing y biblioteca de add-ons.
- APIs compatibles con OpenAI y Anthropic.
- Modelos de texto, visión, audio, imagen y vídeo según backend y modelo.

La presencia en el catálogo no demuestra que todas las combinaciones funcionen en cualquier hardware. Cada capacidad debe validarse en la versión y configuración fijadas.

## 3. Breaking changes y migración

La release reemplaza partes del runtime anterior de agentes/chats. Se retiran las rutas /api/agents, /api/agents/skills, /api/agents/git-repos y /api/conversations; las nuevas familias relevantes incluyen /api/chats/agents, /api/chats y /api/chats/skills.

En el primer arranque se convierten datos antiguos de agentes/chats almacenados en disco/base de datos. Las conversaciones guardadas sólo en navegador requieren importación explícita. Triggers, conectores MCP y bindings convertidos quedan desactivados hasta habilitación del operador.

**Regla LEONES:** no actualizar una instalación compartida ni automatizar migraciones en la primera prueba. Crear entorno desechable, fijar versión, respaldar datos, inspeccionar el informe de conversión y comprobar las nuevas APIs. Mantener pruebas de contrato para rutas antiguas/nuevas y registrar los 404 esperados.

## 4. Seguridad: Sandbox no equivale a add-ons

El Sandbox de trabajo puede apoyarse en KVM/Cloud Hypervisor o gVisor, según modalidad/configuración. Hay que verificar /dev/kvm o la configuración efectiva de gVisor. La documentación describe la red deshabilitada por defecto y un workspace montado para operaciones controladas.

Los add-ons normales no heredan automáticamente ese aislamiento: pueden ejecutarse como el usuario de sistema de LocalAI.

Gates de seguridad antes de cualquier uso agentivo:

1. Identificar proceso, UID/GID y permisos de cada herramienta/add-on.
2. Comprobar aislamiento real, mounts, capacidades, políticas de syscalls y límites CPU/RAM/disco.
3. Probar red, DNS, egress y acceso a loopback.
4. Probar traversal, symlinks, permisos, archivos sensibles y límites de workspace.
5. Verificar que credenciales no aparecen en prompts, logs, resultados o mounts.
6. Probar rollback, timeout y recuperación ante crash.
7. No ejecutar código no confiable fuera del Sandbox ni inferir aislamiento por el nombre de la función.

## 5. Encaje en LEONES

LEONES conserva políticas, intención, selección, gates, pinning y aceptación de evidencia. ODS puede desplegar/operar LocalAI sin convertirse en autoridad de medición. LocalAI aporta serving, APIs, modelos y capacidades agentivas. NEPENTHES captura sólo métricas/trazas realmente observables. REDIL podría tratarlo como servicio de un nodo con autenticación, cuotas, health checks y observabilidad. TensorFold y llama.cpp siguen como motores comparables.

## 6. Plan de investigación por gates

### L0 — compatibilidad estática (remoto)
Fijar release; revisar licencia, dependencias, APIs, instalación y matriz de backends; extraer contratos de health, modelos, chat, tools, Files y telemetría; mapear rutas nuevas/eliminadas; documentar procesos, permisos y riesgos.

**Aceptación:** ficha técnica, matriz de compatibilidad y riesgos con fuentes primarias. Sin instalación ni claims de rendimiento.

### L1 — adaptador LEONES (remoto)
Tras comprobar estructura y contratos existentes, diseñar un adaptador independiente (posible ubicación projects/leones-localai/) con discovery, health, catálogo de modelos/capacidades, chat compatible, tool calls trazables, version pinning, configuración y recibos. Files/Projects serán capacidades opcionales. Probar con servidor simulado.

**Aceptación:** pruebas deterministas del adaptador sin exigir LocalAI ni credenciales externas.

### L2 — Sandbox y agentes (revisión de seguridad)
Verificar KVM/gVisor, modalidad de aislamiento, límites, egress/loopback, mounts, rollback y separación de add-ons. Ejecutar sólo tareas benignas de laboratorio con permisos explícitos.

**Aceptación:** matriz de amenazas, pruebas de aislamiento y límites conocidos; no equivale a auditoría de seguridad completa.

### L3 — comparación de runtime (MSI, cuando esté disponible)
Empezar con modelo pequeño y contexto moderado; no lanzar varios servidores CUDA pesados a la vez. Medir carga, RAM/VRAM pico, TTFT, prefill, tokens/s, latencia por token, concurrencia, errores y overhead. Comparar LocalAI, llama.cpp directo y TensorFold con modelo, cuantización, contexto, prompt y protocolo idénticos. Conservar logs, manifests y recibos para NEPENTHES.

**Aceptación:** resultados MEASURED reproducibles, separados de claims upstream y estimaciones.

### L4 — agente y harness
Mapear capacidades a tareas A01–A10; comprobar registro de tool calls y grading de artefactos; comparar con DSH, Buddy y Hermes bajo tareas equivalentes; evaluar seguridad, recuperación, coste, latencia y calidad.

**Aceptación:** trazas completas y resultados conformes al contrato del benchmark agentivo.

## 7. Hardware de referencia y límites

El MSI LEONES tiene RTX 3050 Laptop de 4 GiB VRAM, aproximadamente 14 GiB RAM e Intel Core i7-12650H bajo Ubuntu. No inferir viabilidad por el tamaño del catálogo; evitar runtimes CUDA simultáneos; comenzar con modelo pequeño; observar RAM, swap y VRAM; no instalar Desktop/add-ons implícitamente; comprobar KVM/gVisor antes de atribuir aislamiento.

Esta investigación no autoriza instalación ni declara compatibilidad física.

## 8. Riesgos y decisiones pendientes

| Riesgo | Tratamiento |
|---|---|
| APIs agentivas incompatibles con versiones anteriores | Pinning y pruebas de contrato v5; migración aislada. |
| Add-ons fuera del Sandbox | Separar procesos/permisos; no asumir aislamiento heredado. |
| KVM/gVisor ausente o limitado | Gate de detección; documentar el modo real. |
| Observabilidad incompleta | NEPENTHES registra sólo métricas observables y declara huecos. |
| Overhead frente al backend directo | Benchmark A/B idéntico. |
| Duplicación con ODS/Magnitude | Separar despliegue, ejecución y medición. |
| Semántica API distinta pese a compatibilidad nominal | Probar streaming, tool calls, errores, tokens y cancelación. |

## 9. Resultado esperado

- **Integrar si se validan contratos:** adaptador, health y discovery de modelos.
- **Experimental y condicionado:** agentes, Files/Projects y Sandbox.
- **Mantener externo inicialmente:** Desktop y gestión de equipo.
- **No sustituir:** ODS, TensorFold, llama.cpp, NEPENTHES, REDIL ni contratos LEONES.

## Fuentes

- [LocalAI v5.0.0](https://github.com/mudler/LocalAI/releases/tag/v5.0.0)
- [Anuncio oficial LocalAI 5.0](https://localai.io/blog/localai-5-0/)
- [Sandbox add-on](https://localai.io/docs/addons/catalogue/work/sandbox/)
- [Repositorio LocalAI](https://github.com/mudler/LocalAI)

**Límite de evidencia:** análisis documental; no acredita instalación, compatibilidad de hardware, seguridad del Sandbox, rendimiento ni aceptación de producción.
