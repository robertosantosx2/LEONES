# Buddy — fuente de conocimiento LEONES

**Fuente primaria:** https://github.com/juanje/buddy  
**Repositorio upstream:** `juanje/buddy`  
**Licencia declarada upstream:** GPL-3.0  
**Tipo:** asistente personal local / agent harness

## Resumen verificable

Buddy se presenta como una aplicación nativa de escritorio para un asistente personal con memoria persistente. La memoria se conserva como archivos Markdown locales dentro de un repositorio Git, con conocimiento del agente, datos del usuario y logs de sesiones.

La implementación descrita upstream usa Tauri v2 para la envoltura nativa, Svelte 5 para la interfaz y un worker Node.js/TypeScript que integra Pi SDK como runtime de agente. La arquitectura incorpora una capa de permisos por zonas y herramientas centradas en ficheros; el diseño evita Bash/shell para el agente.

## Valor para LEONES

Buddy representa un tercer punto de referencia distinto de DSH y Hermes:

- DSH: composición mediante plugins/eventos.
- Buddy: memoria personal persistente, Git/Markdown y file-first.
- Hermes: harness integrado en el ecosistema ODS.

Esto permite estudiar por separado cuánto aportan runtime, memoria, herramientas, permisos y UX sobre el mismo modelo.

## Integración estratégica

Buddy se incorpora a la matriz oficial de harnesses de referencia de LEONES y debe recibir un adaptador de trazas común.

Destinos prioritarios:

1. **ODS:** servicio/extensión aislada que consume el endpoint de modelo de ODS.
2. **Magnitude:** harness alternativo/cliente que puede compartir backend de modelo, sin fusionar el código interno de ambos proyectos.
3. **LEONES:** ejecución reproducible y comparación DSH/Buddy/Hermes.

## Límites de evidencia

Este documento distingue hechos observables en la documentación upstream de decisiones de integración LEONES. Los nombres concretos de endpoints, manifiestos o APIs de ODS/Magnitude deben verificarse contra la versión instalada antes de convertir los diseños en código de producción.

## Referencias

- Upstream: https://github.com/juanje/buddy
- Arquitectura: `docs/app-spec-tauri.md`
- Especificación funcional: `specs/SPEC.md`
- Progreso: `specs/PROGRESS.md`
