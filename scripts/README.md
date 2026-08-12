# Scripts LEONES

Los scripts son la interfaz local mínima entre una persona y LEONES. Cada herramienta responde a una pregunta concreta y hace una sola cosa.

## Flujo recomendado

`necesidad → hardware → modelo → runtime → inferencia → LOTB → informe → privacidad → publicación → estadísticas`

Puedes detenerte en cualquier punto. **No ejecutes un script porque existe: ejecútalo porque responde a tu siguiente pregunta.**

## Contrato de usuario

Cada script debe explicar claramente:

1. **Antes:** qué pregunta responde, qué hará, qué no hará, requisitos y datos que producirá.
2. **Durante:** pasos visibles, progreso y errores accionables; sin operaciones ocultas.
3. **Después:** significado, límites, siguiente paso recomendado y contribución opcional a la Manada.

## Contrato de datos

Cuando produzca información reutilizable, debe ofrecer JSON estructurado. Un resultado medido no equivale automáticamente a evidencia verificada.

## Privacidad

Ningún script publica por defecto. La publicación requiere una acción explícita. Las comprobaciones detectan patrones comunes pero no demuestran por sí solas anonimato.

Nunca publicar nombres, emails, rutas personales, UUID, MAC/IP, números de serie, credenciales, tokens, secretos ni contenido privado.

## Herramientas canónicas

| Herramienta | Pregunta | No hace |
|---|---|---|
| `leones-hardware.py` | ¿Qué máquina tengo? | no descarga ni ejecuta modelos |
| `leones-model.py` | ¿Qué modelo tengo? | no ejecuta ni descarga |
| `leones-runtime.py` | ¿Qué runtime local está disponible? | no instala nada |
| `leones-infer.py` | ¿Cómo rinde una inferencia pequeña? | no LOTB |
| `leones-lotb.py` | ¿Puede completar tareas agentivas? | no publica |
| `leones-report.py` | ¿Cómo documento el resultado? | no publica |
| `leones-privacy.py` | ¿Qué puede salir de mi máquina? | no publica |
| `leones-publish.py` | ¿Quiero publicar el informe? | no mide |
| `leones-stats.py` | ¿Qué aprende el conjunto? | no modifica Atlas |

Los scripts antiguos o especializados se conservan hasta una migración explícita; no se duplican funciones sin motivo.
