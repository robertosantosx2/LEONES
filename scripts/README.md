# Scripts LEONES

Los scripts son la interfaz local mínima entre una persona y LEONES. Cada herramienta responde a una pregunta concreta y hace una sola cosa.

## Plataformas de referencia

LEONES está orientado prioritariamente a **Linux** y ofrece soporte explícito para estas tres plataformas:

| Plataforma | Estado | Instalación base orientativa |
|---|---|---|
| **Debian** | 🟢 Soporte explícito | `sudo apt update && sudo apt install python3 python3-venv python3-pip` |
| **Ubuntu** | 🟢 Soporte explícito | `sudo apt update && sudo apt install python3 python3-venv python3-pip` |
| **Red Hat Enterprise Linux (RHEL)** | 🟢 Soporte explícito | `sudo dnf install python3 python3-pip` |

Estas instrucciones son orientativas. Los scripts no deben asumir que `apt` o `dnf` están disponibles: deben funcionar, siempre que sea posible, con Python y la librería estándar, y detectar la distribución mediante `/etc/os-release` cuando necesiten adaptar instrucciones.

**Debian no es una variante secundaria de Ubuntu:** es una plataforma de referencia propia de LEONES. Ubuntu y RHEL tienen el mismo nivel de consideración dentro de esta matriz inicial.

Otras distribuciones Linux pueden funcionar, pero se consideran compatibilidad esperada hasta que existan pruebas reproducibles suficientes para incorporarlas como plataformas de referencia.

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
