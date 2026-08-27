# Scripts LEONES

Los scripts son la interfaz local mínima entre una persona y LEONES. Cada herramienta responde a una pregunta concreta y hace una sola cosa.

## Norma de simplicidad

La regla obligatoria es: **mínimo código necesario, máxima claridad**.

El contrato completo está en [`../docs/SCRIPT_STYLE_CONTRACT.md`](../docs/SCRIPT_STYLE_CONTRACT.md). En resumen, todo script nuevo o modificado debe tener una responsabilidad clara, una interfaz comprensible, un docstring inicial, comentarios que expliquen las decisiones no obvias y ningún trabajo oculto.

La comprobación práctica es:

```bash
python scripts/check_script_quality.py
```

Durante la migración histórica el auditor informa sin bloquear. Cuando una familia de scripts haya sido limpiada, puede comprobarse con `--strict`.

## Documentación por fases

Los scripts que formen parte de una fase importante deben quedar trazados en su paquete documental. El cierre de fase sigue:

**implementar → validar → aceptar → documentar profusamente → enlazar → cerrar**.

- [`../docs/DOCUMENTATION_PROTOCOL.md`](../docs/DOCUMENTATION_PROTOCOL.md) — norma general.
- [`../docs/phases/README.md`](../docs/phases/README.md) — índice de fases.
- [`../docs/phases/2026-08-atlas-recommendation-pipeline/`](../docs/phases/2026-08-atlas-recommendation-pipeline/) — fase actual que incluye `atlas_recommendation_enrich.py`, todavía en validación.

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

`necesidad → hardware → modelo → runtime → inferencia → evaluación → informe → privacidad → publicación → estadísticas`

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
| `leones-infer.py` | ¿Cómo rinde una inferencia pequeña? | no evaluación |
| `leones-evaluacion.py` | ¿Puede completar tareas agentivas? | no publica |
| `leones-report.py` | ¿Cómo documento el resultado? | no publica |
| `leones-privacy.py` | ¿Qué puede salir de mi máquina? | no publica |
| `leones-publish.py` | ¿Quiero publicar el informe? | no mide |
| `leones-stats.py` | ¿Qué aprende el conjunto? | no modifica Atlas |

Los scripts antiguos o especializados se conservan hasta una migración explícita; no se duplican funciones sin motivo.
