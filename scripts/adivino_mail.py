#!/usr/bin/env python3
"""Correo de ADIVINO.

Este módulo conecta el descubrimiento con el correo sin guardar direcciones,
contraseñas ni tokens en Git. Todo lo sensible llega mediante variables de
entorno/secrets del workflow.

El envío informa al responsable de que existe una fuente pendiente. La
respuesta humana debe contener exactamente ``OK LEONES`` para aprobarla.
Cualquier otra respuesta se conserva como no aprobada.
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Iterable

from adivino import Discovery


def send_discovery_email(discoveries: Iterable[Discovery]) -> None:
    """Envía un aviso SMTP para las fuentes nuevas pendientes."""
    items = list(discoveries)
    if not items:
        return

    host = os.environ["ADIVINO_SMTP_HOST"]
    port = int(os.environ.get("ADIVINO_SMTP_PORT", "587"))
    user = os.environ["ADIVINO_SMTP_USER"]
    password = os.environ["ADIVINO_SMTP_PASSWORD"]
    recipient = os.environ["ADIVINO_EMAIL_TO"]

    message = EmailMessage()
    message["From"] = user
    message["To"] = recipient
    message["Subject"] = f"ADIVINO — {len(items)} nuevo(s) descubrimiento(s)"

    lines = [
        "ADIVINO ha encontrado nuevas fuentes potencialmente útiles para LEONES.",
        "",
        "Para aprobar una fuente, responde exactamente: OK LEONES",
        "",
    ]
    for item in items:
        lines.extend(
            (
                f"• {item.name}",
                f"  {item.url}",
                f"  Tipo: {item.source_type}",
                f"  Motivo: {item.reason}",
                "",
            )
        )
    message.set_content("\n".join(lines))

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(message)


if __name__ == "__main__":
    raise SystemExit("Usa send_discovery_email() desde el adaptador del workflow.")
