# 🔮 ADIVINO — descubrimiento continuo con validación humana

ADIVINO es el mecanismo oficial de descubrimiento de nuevas fuentes para LEONES. Puede encontrar sitios, repositorios, datasets, benchmarks, runtimes, software, skills, agentes, documentación, hardware y otras fuentes útiles para aprender o medir.

## Principio

**ADIVINO descubre. Una persona valida. LEONES verifica.**

Un descubrimiento nunca entra directamente en el Atlas.

## Flujo

```text
FUENTES CONOCIDAS
      ↓
ADIVINO
      ↓
CANDIDATO
      ↓
NORMALIZACIÓN + DEDUPLICACIÓN
      ↓
pending_human
      ↓
📧 correo
      ↓
respuesta exacta: OK LEONES
      ↓
approved
      ↓
adaptador / extracción / medición
      ↓
evidencia + quality gates
      ↓
Atlas / Manada / recomendador
```

## Aprobación humana

La autorización operativa es exactamente:

```text
OK LEONES
```

Se ignoran mayúsculas/minúsculas y espacios exteriores. Cualquier otro texto mantiene el candidato pendiente.

Una aprobación solo autoriza a investigar la fuente: **no significa que la fuente sea fiable, correcta o verificada**.

## Correo

`adivino_mail.py` utiliza SMTP y obtiene toda la configuración sensible del entorno. Nunca se guarda una dirección, contraseña o token en Git.

Variables:

```text
ADIVINO_SMTP_HOST
ADIVINO_SMTP_PORT       # opcional; por defecto 587
ADIVINO_SMTP_USER
ADIVINO_SMTP_PASSWORD
ADIVINO_EMAIL_TO
```

El workflow deberá suministrarlas mediante GitHub Secrets.

El mensaje incluye nombre, URL, tipo y motivo del descubrimiento y explica que la aprobación debe hacerse respondiendo `OK LEONES`.

## Aprobación

`adivino_approve.py` procesa la respuesta y cambia únicamente candidatos `pending_human` a `approved` cuando la orden es válida. La aprobación no ejecuta extracción ni publicación.

Para una instalación con lectura automática del buzón, el adaptador de correo debe identificar de forma segura al remitente autorizado, relacionar la respuesta con el candidato y conservar fecha/mensaje origen. Nunca se debe interpretar un correo reenviado, una firma o una frase parecida como autorización.

## Estados

```text
pending_human → approved → validated → active
       │
       └──────────────→ rejected
```

## Seguridad

- Sin secretos en el repositorio.
- Sin publicación directa desde ADIVINO.
- Sin aprobación implícita.
- Sin promoción de datos sin los gates de LEONES.
- Los candidatos rechazados conservan el motivo para evitar redescubrimientos inútiles.
- Todo workflow futuro que escriba en `main` debe cumplir `docs/CI-WORKFLOW-RULES.md`.

## Fuentes de descubrimiento

La arquitectura admite GitHub, Hugging Face, arXiv, Semantic Scholar, PyPI, npm, RSS/Atom y webs/documentación enlazada. Las fuentes descubiertas a partir de enlaces también entran como candidatas.

## Activación

Hasta configurar los secretos SMTP, ADIVINO puede descubrir y almacenar candidatos, pero **no debe simular envíos de correo**. La activación real requiere configurar esos secretos en GitHub.

## Documentación relacionada

- `docs/SOURCE-DISCOVERY.md`
- `docs/CI-WORKFLOW-RULES.md`
- `scripts/adivino.py`
- `scripts/adivino_mail.py`
- `scripts/adivino_approve.py`
